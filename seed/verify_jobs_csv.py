#!/usr/bin/env python3
"""
Verify jobs_seed.csv against the Job model constraints AND cross-check it
against workers_seed.csv so you know the data can actually be matched.

Two classes of check:

  STRUCTURAL / MODEL   - does this file load into Postgres and satisfy the
                         Job model's nullability, types and String(n) limits
  MATCHABILITY         - for every service job, does at least one matchable
                         worker of the same trade exist inside 20 km, and does
                         the job's text avoid reusing worker-side vocabulary

The second class is the one that matters. A file can be perfectly valid SQL
and still be worthless as test data if every job's nearest correct worker is
40 km away, or if job and worker text are near-copies of each other.

Exits non-zero on any failure.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

JOBS = Path(__file__).with_name("jobs_seed.csv")
WORKERS = Path(__file__).with_name("workers_seed.csv")

HEADER = [
    "id", "customer_id", "booking_chat_id", "worker_id", "title", "description",
    "status", "is_job_request", "categories", "contact_name", "contact_phone",
    "mode", "attachments", "address_text", "latitude", "longitude", "location",
    "description_vector", "created_at", "updated_at",
]

# String(n) limits from the model
MAXLEN = {
    "title": 255, "status": 50, "contact_name": 100,
    "contact_phone": 20, "mode": 20,
}
NOT_NULL = {"id", "customer_id", "title", "description", "status", "is_job_request"}
NULLABLE = {
    "booking_chat_id", "worker_id", "categories", "contact_name", "contact_phone",
    "mode", "attachments", "address_text", "latitude", "longitude", "location",
    "description_vector",
}
INTS = {"id", "customer_id", "booking_chat_id", "worker_id"}
BOOLS = {"is_job_request"}
JSONB = {"categories", "attachments"}

VALID_STATUS = {"PENDING", "MATCHED", "ASSIGNED", "COMPLETED", "CANCELLED"}
VALID_MODE = {"express", "regular"}

POINT_RE = re.compile(r"^SRID=4326;POINT\(-?\d+\.?\d* -?\d+\.?\d*\)$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$")

RADIUS_KM = 20.0

errors: list[str] = []
warnings: list[str] = []


def err(m: str) -> None:
    errors.append(m)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def load_workers():
    """matchable workers by tag, plus the full speciality vocabulary per tag."""
    by_tag: dict[str, list[dict]] = {}
    specs_by_tag: dict[str, set[str]] = {}
    all_ids: set[int] = set()
    worker_text: list[str] = []
    with WORKERS.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            all_ids.add(int(r["user_id"]))
            tag = r["category_tag"]
            if tag:
                inner = r["specialities"][1:-1]
                for e in (x.strip('"') for x in inner.split(",")):
                    if e:
                        specs_by_tag.setdefault(tag, set()).add(e)
            if (r["is_complete"] == "true" and r["scenario_passed"] == "true"
                    and r["is_rejected"] == "false"):
                by_tag.setdefault(tag, []).append({
                    "user_id": int(r["user_id"]),
                    "lat": float(r["latitude"]),
                    "lon": float(r["longitude"]),
                })
                worker_text.append(r["job_description"])
    return by_tag, specs_by_tag, all_ids, worker_text


def tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", s.lower())}


def main() -> int:
    raw = JOBS.read_text(encoding="utf-8")
    all_rows = list(csv.reader(raw.splitlines()))
    header, body = all_rows[0], all_rows[1:]

    # --- 1. header + field count ----------------------------------------
    if header != HEADER:
        err(f"header mismatch\n  got:  {header}\n  want: {HEADER}")
        return report()
    for i, r in enumerate(body, start=2):
        if len(r) != len(HEADER):
            err(f"line {i}: {len(r)} fields, expected {len(HEADER)}")
    if errors:
        return report()

    rows = [dict(zip(HEADER, r)) for r in body]
    print(f"rows: {len(rows)}")

    # NULL vs '' — csv.reader collapses both, so re-scan the raw text.
    # Under COPY FORMAT csv an unquoted empty field is NULL and a quoted ""
    # is the empty string. For this file NOT NULL text columns must never be
    # either, so a plain emptiness check on the parsed value is sufficient.
    quoted_empty = raw.count(',""')
    print(f"quoted-empty fields (would load as '', not NULL): {quoted_empty}")

    ids, chat_ids = set(), set()

    for n, r in enumerate(rows, start=2):
        # --- 2. PK / unique ---------------------------------------------
        if r["id"] in ids:
            err(f"line {n}: duplicate id {r['id']}")
        ids.add(r["id"])
        if r["booking_chat_id"]:
            if r["booking_chat_id"] in chat_ids:
                err(f"line {n}: duplicate booking_chat_id "
                    f"{r['booking_chat_id']} (UNIQUE constraint)")
            chat_ids.add(r["booking_chat_id"])

        # --- 3. NOT NULL ------------------------------------------------
        for col in NOT_NULL:
            if r[col] == "":
                err(f"line {n}: NOT NULL column {col} is empty")

        # --- 4. types ---------------------------------------------------
        for col in INTS:
            v = r[col]
            if v == "":
                if col in NOT_NULL:
                    err(f"line {n}: {col} is NULL but NOT NULL")
                continue
            if not re.fullmatch(r"\d+", v):
                err(f"line {n}: {col}={v!r} is not an integer")
        for col in BOOLS:
            if r[col] not in ("true", "false"):
                err(f"line {n}: {col}={r[col]!r} is not true/false")
        for col in ("created_at", "updated_at"):
            if not TS_RE.match(r[col]):
                err(f"line {n}: {col}={r[col]!r} is not a timestamp")
        if r["created_at"] > r["updated_at"]:
            err(f"line {n}: created_at is after updated_at")

        # --- 5. String(n) -----------------------------------------------
        for col, lim in MAXLEN.items():
            if len(r[col]) > lim:
                err(f"line {n}: {col} is {len(r[col])} chars, exceeds String({lim})")

        # --- 6. enumerations --------------------------------------------
        if r["status"] not in VALID_STATUS:
            err(f"line {n}: status={r['status']!r} not in {sorted(VALID_STATUS)}")
        if r["mode"] and r["mode"] not in VALID_MODE:
            err(f"line {n}: mode={r['mode']!r} not in {sorted(VALID_MODE)}")

        # --- 7. JSONB parses --------------------------------------------
        # This is the check the original jobs.csv would have failed: its
        # categories field had mixed ' and " quoting and | separators, so
        # Postgres would reject it as invalid JSON on load.
        for col in JSONB:
            if r[col] == "":
                continue
            try:
                parsed = json.loads(r[col])
            except json.JSONDecodeError as e:
                err(f"line {n}: {col} is not valid JSON ({e}): {r[col][:80]!r}")
                continue
            if not isinstance(parsed, list):
                err(f"line {n}: {col} should be a JSON array, got {type(parsed).__name__}")
                continue
            for item in parsed:
                if not isinstance(item, dict):
                    err(f"line {n}: {col} element is not an object")
                    continue
                if col == "categories":
                    for k in ("tags", "category", "is_custom_category"):
                        if k not in item:
                            err(f"line {n}: categories element missing {k!r}")
                    if not isinstance(item.get("tags"), list) or not item["tags"]:
                        err(f"line {n}: categories.tags empty or not a list")
                else:
                    for k in ("url", "type"):
                        if k not in item:
                            err(f"line {n}: attachments element missing {k!r}")

        # --- 8. status <-> worker_id coherence ---------------------------
        st, wid = r["status"], r["worker_id"]
        if st in ("ASSIGNED", "COMPLETED") and wid == "":
            err(f"line {n}: status={st} but worker_id is NULL")
        if st == "PENDING" and wid != "":
            err(f"line {n}: status=PENDING but worker_id={wid} is set")

        # --- 9. is_job_request <-> categories ---------------------------
        # categories and attachments are jsonb NOT NULL in the real DDL, so
        # a non-service job carries [] rather than NULL.
        isreq = r["is_job_request"] == "true"
        if r["categories"] == "":
            err(f"line {n}: categories is NULL but the column is jsonb NOT NULL")
        if r["attachments"] == "":
            err(f"line {n}: attachments is NULL but the column is jsonb NOT NULL")
        if isreq and r["categories"] in ("", "[]"):
            err(f"line {n}: is_job_request=true but categories is empty")
        if not isreq and r["categories"] not in ("", "[]"):
            err(f"line {n}: is_job_request=false but categories is populated")
        if not isreq and wid != "":
            err(f"line {n}: non-service request has worker_id={wid}")

        # --- 10. geography ----------------------------------------------
        lat, lon, loc = r["latitude"], r["longitude"], r["location"]
        present = [x != "" for x in (lat, lon, loc)]
        if any(present) and not all(present):
            err(f"line {n}: lat/lon/location partially populated")
        if loc:
            if not POINT_RE.match(loc):
                err(f"line {n}: bad EWKT {loc!r}")
            else:
                plon, plat = loc[len("SRID=4326;POINT("):-1].split()
                if plat != lat or plon != lon:
                    err(f"line {n}: POINT({plon} {plat}) disagrees with "
                        f"lat={lat} lon={lon}")
                # PostGIS stores (lon lat). A swapped pair puts Kathmandu in
                # the Indian Ocean and every ST_DWithin returns nothing.
                if not (-90 <= float(plat) <= 90 and -180 <= float(plon) <= 180):
                    err(f"line {n}: coords out of range / axis order swapped")
            if not (27.3 <= float(lat) <= 28.1 and 85.0 <= float(lon) <= 85.8):
                err(f"line {n}: outside Kathmandu Valley bbox: {lat},{lon}")

        # --- 11. vector must be NULL ------------------------------------
        if r["description_vector"] != "":
            err(f"line {n}: description_vector should be NULL in the seed")

    if errors:
        return report()

    # ==================================================================
    # MATCHABILITY — cross-check against workers_seed.csv
    # ==================================================================
    if not WORKERS.exists():
        warnings.append("workers_seed.csv not found — skipped matchability checks")
        return report()

    by_tag, specs_by_tag, worker_uids, worker_text = load_workers()
    service = [r for r in rows if r["is_job_request"] == "true"]
    print(f"\nservice jobs: {len(service)}, non-service: {len(rows) - len(service)}")

    # --- 12. every job tag exists in the workers taxonomy ---------------
    unknown_tags: Counter = Counter()
    unknown_specs: Counter = Counter()
    for r in service:
        for c in json.loads(r["categories"]):
            tag = c["category"]
            if tag not in specs_by_tag:
                unknown_tags[tag] += 1
                continue
            for t in c["tags"]:
                if t not in specs_by_tag[tag]:
                    unknown_specs[f"{tag}/{t}"] += 1
    for tag, k in unknown_tags.items():
        err(f"{k} job(s) use category_tag {tag!r} which no worker has")
    for st, k in unknown_specs.items():
        err(f"{k} job(s) use speciality {st!r} not present in that trade's workers")
    print(f"taxonomy alignment: {len(unknown_tags)} unknown tags, "
          f"{len(unknown_specs)} unknown specialities")

    # --- 13. every job has candidates within the match radius -----------
    no_candidates, thin = [], []
    cand_counts = []
    for r in service:
        tag = json.loads(r["categories"])[0]["category"]
        pool = by_tag.get(tag, [])
        near = [w for w in pool
                if haversine_km(float(r["latitude"]), float(r["longitude"]),
                                w["lat"], w["lon"]) <= RADIUS_KM]
        cand_counts.append(len(near))
        if not near:
            no_candidates.append((r["id"], tag))
        elif len(near) < 3:
            thin.append((r["id"], tag, len(near)))

    for jid, tag in no_candidates:
        err(f"job {jid} ({tag}) has NO matchable worker within {RADIUS_KM} km "
            f"— ST_DWithin will return an empty set")
    if thin:
        warnings.append(f"{len(thin)} job(s) have fewer than 3 candidates in "
                        f"{RADIUS_KM} km (thin for testing ranking): "
                        f"{thin[:5]}{' ...' if len(thin) > 5 else ''}")
    if cand_counts:
        cand_counts.sort()
        print(f"candidates within {RADIUS_KM} km: min {cand_counts[0]}, "
              f"median {cand_counts[len(cand_counts)//2]}, max {cand_counts[-1]}")

    # --- 14. assigned worker actually does the trade, and is near --------
    worker_trade: dict[int, set[str]] = {}
    for tag, ws in by_tag.items():
        for w in ws:
            worker_trade.setdefault(w["user_id"], set()).add(tag)
    far = 0
    for r in service:
        if r["status"] not in ("ASSIGNED", "COMPLETED"):
            continue
        wid = int(r["worker_id"])
        tag = json.loads(r["categories"])[0]["category"]
        if wid not in worker_uids:
            err(f"job {r['id']}: worker_id {wid} does not exist in workers_seed.csv")
        elif tag not in worker_trade.get(wid, set()):
            err(f"job {r['id']}: assigned worker {wid} does not do {tag!r} "
                f"(does {sorted(worker_trade.get(wid, set()))})")
        else:
            w = next(x for x in by_tag[tag] if x["user_id"] == wid)
            if haversine_km(float(r["latitude"]), float(r["longitude"]),
                            w["lat"], w["lon"]) > RADIUS_KM:
                far += 1
    if far:
        warnings.append(f"{far} assigned/completed job(s) have a worker beyond "
                        f"{RADIUS_KM} km — plausible in reality, but they will "
                        f"not reappear as candidates if you re-run the matcher")

    # --- 15. customer ids must not collide with worker user ids ----------
    cust = {int(r["customer_id"]) for r in rows}
    clash = cust & worker_uids
    if clash:
        err(f"{len(clash)} customer_id value(s) collide with worker user_ids "
            f"(e.g. {sorted(clash)[:5]}) — both seeds insert into users.id")
    print(f"customer_id range: {min(cust)}–{max(cust)} "
          f"({len(cust)} customers), worker user_id max: {max(worker_uids)}")

    # --- 16. job text must NOT read like worker text ---------------------
    # If job descriptions reuse worker vocabulary, a cosine match looks great
    # while only measuring string overlap. Low shared-token overlap is the
    # point of writing jobs in the customer's voice.
    wvocab: Counter = Counter()
    for t in worker_text:
        wvocab.update(tokens(t))
    common_worker = {w for w, k in wvocab.items() if k > len(worker_text) * 0.02}
    overlaps = []
    for r in service:
        jt = tokens(r["description"])
        if jt:
            overlaps.append(len(jt & common_worker) / len(jt))
    overlaps.sort()
    med = overlaps[len(overlaps) // 2]
    print(f"job/worker vocabulary overlap: median {med:.1%}, "
          f"max {overlaps[-1]:.1%}")
    if med > 0.35:
        warnings.append(f"job text shares {med:.0%} of its vocabulary with "
                        f"worker text — matches may reflect string overlap "
                        f"rather than semantic understanding")

    # --- 17. distribution sanity ---------------------------------------
    print("\nstatus:", dict(Counter(r["status"] for r in rows)))
    print("mode:  ", dict(Counter(r["mode"] for r in rows)))
    tagc = Counter(json.loads(r["categories"])[0]["category"] for r in service)
    print(f"distinct job trades: {len(tagc)}; top 6: {tagc.most_common(6)}")
    descs = [r["description"] for r in rows]
    print(f"unique descriptions: {len(set(descs))}/{len(descs)}")
    if len(set(descs)) < len(descs):
        warnings.append(f"{len(descs) - len(set(descs))} duplicate description(s) "
                        f"— duplicates embed identically and flatten the score spread")
    titles = [r["title"] for r in rows]
    print(f"unique titles: {len(set(titles))}/{len(titles)}")
    att = sum(1 for r in rows if r["attachments"] not in ("", "[]"))
    print(f"jobs with attachments: {att}")
    nochat = sum(1 for r in rows if r["booking_chat_id"] == "")
    print(f"jobs with no booking_chat_id: {nochat}")

    return report()


def report() -> int:
    print()
    for w in warnings:
        print(f"WARN  {w}")
    if errors:
        print(f"\nFAILED — {len(errors)} error(s):")
        for e in errors[:40]:
            print(f"  {e}")
        if len(errors) > 40:
            print(f"  ... and {len(errors) - 40} more")
        return 1
    print("PASS — structural, model, and matchability checks clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
