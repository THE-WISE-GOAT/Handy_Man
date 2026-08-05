#!/usr/bin/env python3
"""
Backfill description_vector on workers and/or jobs using nvidia/nv-embed-v1
(4096-dim).

Run AFTER the load scripts have inserted the seed rows.

    export NVIDIA_API_KEY=nvapi-...
    export DATABASE_URL=postgresql+psycopg://user:pass@host:5432/handyman

    python backfill_embeddings.py --table workers
    python backfill_embeddings.py --table jobs
    python backfill_embeddings.py --table both

Notes that matter for Handy_Man specifically:

  * input_type differs by table and this is NOT cosmetic. Worker profiles
    are the *stored* side of the index and use "passage"; customer job
    requests are the *query* side and use "query". nv-embed-v1 is trained
    asymmetrically, so embedding both sides as "passage" shifts every
    cosine distance and your Sigmoid score — 100/(1+e^(15*(d-0.87))) —
    lands in the wrong band. The whole scoring calibration assumes this.
    The table config below encodes it so it cannot be got wrong by hand.

  * Only rows that will ever be matched are embedded by default. For
    workers that means is_complete AND scenario_passed AND NOT is_rejected;
    for jobs it means is_job_request (a request for a driver or a tutor is
    never matched against a trade worker). Pass --all to override.

  * Safe to interrupt and re-run: it only selects rows where the vector is
    still NULL, and commits per batch.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from openai import OpenAI
from sqlalchemy import create_engine, text

MODEL = "nvidia/nv-embed-v1"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
EXPECTED_DIM = 4096
BATCH_SIZE = 16          # nv-embed rejects very large batches; 16 is safe
MAX_RETRIES = 5

# Per-table configuration. input_type is the load-bearing field here.
TABLES = {
    "workers": {
        "text_col": "job_description",
        "input_type": "passage",
        "matchable": "is_complete AND scenario_passed AND NOT is_rejected",
        "index": "idx_workers_vector_hnsw",
    },
    "jobs": {
        "text_col": "description",
        "input_type": "query",
        "matchable": "is_job_request",
        "index": "idx_jobs_vector_hnsw",
    },
}


def get_client() -> OpenAI:
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        sys.exit("NVIDIA_API_KEY is not set.")
    return OpenAI(base_url=NVIDIA_BASE_URL, api_key=key)


def embed_batch(client: OpenAI, texts: list[str], input_type: str) -> list[list[float]]:
    """Embed a batch, retrying with exponential backoff on transient errors."""
    delay = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.embeddings.create(
                model=MODEL,
                input=texts,
                encoding_format="float",
                extra_body={"input_type": input_type, "truncate": "END"},
            )
            vectors = [d.embedding for d in resp.data]
            for v in vectors:
                if len(v) != EXPECTED_DIM:
                    raise ValueError(
                        f"expected {EXPECTED_DIM} dims, got {len(v)} — "
                        "wrong model or the API changed"
                    )
            return vectors
        except Exception as exc:                      # noqa: BLE001
            if attempt == MAX_RETRIES:
                raise
            print(f"  batch failed ({exc}); retry {attempt}/{MAX_RETRIES} in {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def backfill(engine, client, table: str, embed_all: bool, limit: int,
             dry_run: bool) -> None:
    cfg = TABLES[table]
    text_col = cfg["text_col"]

    where = f"description_vector IS NULL AND {text_col} <> ''"
    if not embed_all:
        where += f" AND {cfg['matchable']}"

    with engine.connect() as conn:
        pending = conn.execute(
            text(f"SELECT count(*) FROM {table} WHERE {where}")
        ).scalar_one()

    print(f"[{table}] {pending} row(s) need an embedding "
          f"(input_type={cfg['input_type']}).")
    if dry_run or pending == 0:
        return

    target = min(pending, limit) if limit else pending
    done = 0

    while done < target:
        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    f"SELECT id, {text_col} AS body FROM {table} "
                    f"WHERE {where} ORDER BY id LIMIT :n"
                ),
                {"n": min(BATCH_SIZE, target - done)},
            ).all()

            if not rows:
                break

            vectors = embed_batch(client, [r.body for r in rows],
                                  cfg["input_type"])

            for row, vec in zip(rows, vectors):
                conn.execute(
                    text(
                        f"UPDATE {table} SET description_vector = "
                        f"CAST(:v AS vector) WHERE id = :id"
                    ),
                    {"v": "[" + ",".join(f"{x:.7g}" for x in vec) + "]",
                     "id": row.id},
                )

            done += len(rows)
            print(f"  [{table}] embedded {done}/{target}")

    print(
        f"\n[{table}] done. Build the vector index now:\n"
        f"  CREATE INDEX {cfg['index']} ON {table}\n"
        f"      USING hnsw (description_vector vector_cosine_ops)\n"
        f"      WITH (m = 16, ef_construction = 64);"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", choices=["workers", "jobs", "both"],
                    default="workers",
                    help="which side of the index to embed")
    ap.add_argument("--all", action="store_true",
                    help="embed every row, not just matchable ones")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after N rows per table (useful for a cost check)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report how many rows would be embedded, then exit")
    args = ap.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit("DATABASE_URL is not set.")

    engine = create_engine(db_url, future=True)
    client = None if args.dry_run else get_client()

    targets = ["workers", "jobs"] if args.table == "both" else [args.table]
    for t in targets:
        backfill(engine, client, t, args.all, args.limit, args.dry_run)

    if not args.dry_run:
        print(
            "\nSanity check once both sides are embedded — the top match for a\n"
            "job should be a worker of the SAME trade:\n"
            "\n"
            "  SELECT j.title,\n"
            "         j.categories->0->>'category' AS job_trade,\n"
            "         w.category_tag               AS worker_trade,\n"
            "         round((j.description_vector <=> w.description_vector)::numeric, 4)\n"
            "             AS cos_dist\n"
            "  FROM   jobs j\n"
            "  CROSS JOIN LATERAL (\n"
            "      SELECT w.category_tag, w.description_vector\n"
            "      FROM   workers w\n"
            "      WHERE  w.description_vector IS NOT NULL\n"
            "        AND  ST_DWithin(w.location, j.location, 20000)\n"
            "      ORDER  BY w.description_vector <=> j.description_vector\n"
            "      LIMIT  1\n"
            "  ) w\n"
            "  WHERE  j.is_job_request AND j.description_vector IS NOT NULL\n"
            "  LIMIT  20;\n"
            "\n"
            "If job_trade and worker_trade disagree often, the embedding is not\n"
            "carrying trade meaning and the taxonomy gate is doing all the work."
        )


if __name__ == "__main__":
    main()
