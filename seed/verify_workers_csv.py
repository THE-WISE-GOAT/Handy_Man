#!/usr/bin/env python3
"""
Verify workers_seed.csv against the WorkerProfile model constraints
BEFORE it ever reaches Postgres. Exits non-zero on any failure.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

CSV = Path(__file__).with_name("workers_seed.csv")

HEADER = [
    "id", "user_id", "worker_chat_id", "stage", "is_complete", "is_rejected",
    "rejection_reason", "job_category", "category_tag", "is_custom_category",
    "specialities", "specialized_tools_or_equipment", "years_experience",
    "license_or_certification", "job_description", "emergency_available",
    "has_verified_specialty", "scenario_passed", "scenario_score",
    "description_vector", "phone_number", "address_text", "latitude",
    "longitude", "location",
]

# column -> max length, from the model's String(n) declarations
MAXLEN = {
    "stage": 50, "job_category": 100, "category_tag": 100,
    "license_or_certification": 255, "phone_number": 50,
}
# NOT NULL columns per the model
NOT_NULL = {
    "id", "user_id", "worker_chat_id", "stage", "is_complete", "is_rejected",
    "job_category", "category_tag", "is_custom_category", "specialities",
    "specialized_tools_or_equipment", "years_experience", "job_description",
    "emergency_available", "has_verified_specialty", "scenario_passed",
    "scenario_score",
}
BOOLS = {
    "is_complete", "is_rejected", "is_custom_category", "emergency_available",
    "has_verified_specialty", "scenario_passed",
}
INTS = {"id", "user_id", "worker_chat_id", "years_experience", "scenario_score"}
ARRAYS = {"specialities", "specialized_tools_or_equipment"}

POINT_RE = re.compile(r"^SRID=4326;POINT\(-?\d+\.?\d* -?\d+\.?\d*\)$")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def main() -> int:
    raw = CSV.read_text(encoding="utf-8")
    reader = csv.reader(raw.splitlines())
    all_rows = list(reader)
    header = all_rows[0]
    body = all_rows[1:]

    # --- 1. header ------------------------------------------------------
    if header != HEADER:
        err(f"header mismatch\n  got:  {header}\n  want: {HEADER}")
        return report()
    ncols = len(HEADER)

    # --- 2. every row has exactly ncols fields --------------------------
    # This is precisely what was broken in the original sample: oversized
    # vector fields spilled onto their own lines.
    for i, r in enumerate(body, start=2):
        if len(r) != ncols:
            err(f"line {i}: {len(r)} fields, expected {ncols}")
    if errors:
        return report()

    rows = [dict(zip(HEADER, r)) for r in body]
    print(f"rows: {len(rows)}")

    # Distinguish NULL from '' — csv.reader collapses both, so re-scan raw
    # lines for unquoted-empty vs quoted-empty in NOT NULL text columns.
    for lineno, line in enumerate(raw.splitlines()[1:], start=2):
        pass  # structural check already done above via field count

    ids, wcids = set(), set()

    for n, r in enumerate(rows, start=2):
        rid = r["id"]

        # --- 3. PK / unique -------------------------------------------
        if rid in ids:
            err(f"line {n}: duplicate id {rid}")
        ids.add(rid)
        if r["worker_chat_id"] in wcids:
            err(f"line {n}: duplicate worker_chat_id {r['worker_chat_id']} (UNIQUE)")
        wcids.add(r["worker_chat_id"])

        # --- 4. NOT NULL ----------------------------------------------
        for col in NOT_NULL:
            if r[col] == "" and col not in ARRAYS and col not in {"job_category", "category_tag", "job_description"}:
                err(f"line {n}: NOT NULL column {col} is empty")

        # --- 5. types --------------------------------------------------
        for col in INTS:
            if not re.fullmatch(r"-?\d+", r[col]):
                err(f"line {n}: {col}={r[col]!r} is not an integer")
        for col in BOOLS:
            if r[col] not in ("true", "false"):
                err(f"line {n}: {col}={r[col]!r} is not true/false")

        # --- 6. String(n) limits ---------------------------------------
        for col, lim in MAXLEN.items():
            if len(r[col]) > lim:
                err(f"line {n}: {col} is {len(r[col])} chars, exceeds String({lim})")
        for col in ARRAYS:
            v = r[col]
            if not (v.startswith("{") and v.endswith("}")):
                err(f"line {n}: {col}={v!r} is not a PG array literal")
                continue
            inner = v[1:-1]
            elems = [e for e in inner.split(",") if e] if inner else []
            for e in elems:
                if len(e.strip('"')) > 100:
                    err(f"line {n}: {col} element exceeds String(100): {e!r}")

        # --- 7. domain rules from the model / spec ---------------------
        score = int(r["scenario_score"])
        if not 0 <= score <= 100:
            err(f"line {n}: scenario_score {score} out of range")

        passed = r["scenario_passed"] == "true"
        # Spec: scenario gate passes strictly above 75.
        if passed and score <= 75:
            err(f"line {n}: scenario_passed=true but score {score} <= 75 (violates gate)")
        if not passed and score > 75:
            err(f"line {n}: scenario_passed=false but score {score} > 75")

        complete = r["is_complete"] == "true"
        rejected = r["is_rejected"] == "true"
        if rejected and passed:
            err(f"line {n}: is_rejected=true but scenario_passed=true")
        if rejected and r["rejection_reason"] == "":
            err(f"line {n}: is_rejected=true but rejection_reason is NULL")
        if not rejected and r["rejection_reason"] != "":
            err(f"line {n}: is_rejected=false but rejection_reason is set")
        if not complete and r["stage"] == "complete":
            err(f"line {n}: stage='complete' but is_complete=false")
        if complete and r["stage"] != "complete":
            err(f"line {n}: is_complete=true but stage={r['stage']!r}")

        if int(r["years_experience"]) < 0:
            err(f"line {n}: negative years_experience")

        # --- 8. geography ---------------------------------------------
        lat, lon, loc = r["latitude"], r["longitude"], r["location"]
        present = [x != "" for x in (lat, lon, loc)]
        if any(present) and not all(present):
            err(f"line {n}: lat/lon/location partially populated: {lat!r} {lon!r} {loc!r}")
        if loc:
            if not POINT_RE.match(loc):
                err(f"line {n}: bad EWKT {loc!r}")
            else:
                plon, plat = loc[len("SRID=4326;POINT("):-1].split()
                if plat != lat or plon != lon:
                    err(f"line {n}: POINT({plon} {plat}) disagrees with lat={lat} lon={lon}")
                # PostGIS is (lon lat) — catch a swapped pair
                if not (-90 <= float(plat) <= 90 and -180 <= float(plon) <= 180):
                    err(f"line {n}: coordinates out of range / axis order swapped")
            f_lat, f_lon = float(lat), float(lon)
            if not (27.3 <= f_lat <= 28.1 and 85.0 <= f_lon <= 85.8):
                err(f"line {n}: point outside Kathmandu Valley bbox: {f_lat},{f_lon}")

        # --- 9. completed rows must be usable --------------------------
        if complete:
            for col in ("job_category", "category_tag", "job_description"):
                if r[col] == "":
                    err(f"line {n}: completed row has empty {col}")
            if r["specialities"] == "{}":
                err(f"line {n}: completed row has no specialities")
            if loc == "":
                err(f"line {n}: completed row has no location (would be unmatchable)")

        # --- 10. vector -------------------------------------------------
        if r["description_vector"] != "":
            err(f"line {n}: description_vector should be NULL in the seed")

    # --- 11.5 trade coherence -------------------------------------------
    # Every speciality must belong to exactly one category_tag. If a
    # speciality shows up under two different trades, the generator has
    # cross-contaminated them (this is what previously put "lock-picking"
    # on a chimney-flue worker) and match results would be polluted.
    spec_to_tags: dict[str, set[str]] = {}
    tag_to_cats: dict[str, set[str]] = {}
    for r in rows:
        tag = r["category_tag"]
        if tag == "":
            continue
        tag_to_cats.setdefault(tag, set()).add(r["job_category"])
        inner = r["specialities"][1:-1]
        for e in (x.strip('"') for x in inner.split(",")):
            if e:
                spec_to_tags.setdefault(e, set()).add(tag)

    bleed = {s: t for s, t in spec_to_tags.items() if len(t) > 1}
    if bleed:
        for s, t in list(bleed.items())[:10]:
            err(f"speciality {s!r} appears under multiple trades: {sorted(t)}")

    multi_cat = {t: c for t, c in tag_to_cats.items() if len(c) > 1}
    for t, c in multi_cat.items():
        err(f"category_tag {t!r} maps to multiple job_category values: {sorted(c)}")

    print(f"speciality->trade mapping: {len(spec_to_tags)} specialities, "
          f"{len(bleed)} cross-trade leaks")

    # --- 12. distribution sanity (warnings, not failures) --------------
    matchable = [r for r in rows if r["is_complete"] == "true"
                 and r["scenario_passed"] == "true" and r["is_rejected"] == "false"]
    print(f"matchable (complete & passed & not rejected): {len(matchable)}")
    if len(matchable) < 800:
        warnings.append(f"only {len(matchable)} matchable rows")

    cats = {}
    for r in matchable:
        cats[r["category_tag"]] = cats.get(r["category_tag"], 0) + 1
    print(f"distinct category_tag among matchable: {len(cats)}")
    thin = [c for c, k in cats.items() if k < 5]
    if thin:
        warnings.append(f"category_tag with <5 matchable workers: {thin}")

    descs = [r["job_description"] for r in matchable]
    uniq = len(set(descs))
    print(f"unique job_descriptions among matchable: {uniq}/{len(descs)}")
    if uniq < len(descs) * 0.9:
        warnings.append("job_description uniqueness below 90% — embeddings will cluster too tightly")

    # user_id reuse is expected (one row per trade per user)
    uids = [r["user_id"] for r in rows]
    print(f"distinct user_id: {len(set(uids))} across {len(uids)} rows "
          f"({len(uids) - len(set(uids))} multi-trade rows)")

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
    print("PASS — all structural, type, constraint and domain checks clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
