# Handy_Man — seed data for `workers` and `jobs`

Two matched seed files: 1,200 worker profiles and 220 customer job requests,
built so the job requests can actually be matched against the worker profiles.

- `workers` (`core.model.WorkerProfile`) — the supply side, 1,200 rows
- `jobs` (`core.model.Job`) — the demand side, 220 rows

Regenerated 2026-08-04.

## Files

| File | Purpose |
|---|---|
| `workers_seed.csv` | 1,200 worker rows, ~1 MB, Postgres CSV-COPY dialect. |
| `jobs_seed.csv` | 220 customer job rows, ~215 KB, same dialect. |
| `load_workers.sql` | `\COPY` load: staging, casts, parent users, indexes, sanity queries. |
| `load_jobs.sql` | Same for jobs, plus the match-coverage queries. **Run after `load_workers.sql`.** |
| `backfill_embeddings.py` | Fills `description_vector` on either table via `nvidia/nv-embed-v1`. |
| `generate_workers.py` | Worker generator. Seeded (`SEED = 20260727`) — rerun for a byte-identical file. |
| `generate_jobs.py` | Job generator. Seeded (`SEED = 20260804`). Reads `workers_seed.csv` to stay matchable. |
| `verify_workers_csv.py` | Model constraints, types, `String(n)`, NOT NULL, domain rules, trade coherence. |
| `verify_jobs_csv.py` | Same for jobs, **plus cross-checks against `workers_seed.csv`**. |
| `verify_copy_semantics.py` | Re-parses `workers_seed.csv` under real `COPY FORMAT csv` rules and casts every field. |

## What was wrong with the samples

Both files you sent had the same failure mode. The 4,096-dim
`description_vector` values overflowed the CSV field limit and wrapped onto
their own physical lines, so vector fragments got parsed as data rows.

- `workers.csv`: 5 "rows" were really 3 workers. Rows 2 and 4 were vector
  spillover — `id = 0.053894043`, `stage = 0.001662254`. Plus 100+ trailing
  empty header columns and a stray `address` column not on the model.
- `jobs.csv`: 1.3 M characters, 25 logical rows, ragged field counts from 20
  to 27 against a 23-field header. The `categories` JSONB was mangled into
  mixed `'`/`"` quoting with `|` separators —
  `[{'tags'": ['"earthing-installation'"| ...` — which is not valid JSON and
  Postgres would reject outright.

That is the core reason vectors are left NULL here (see Embeddings below).

**Two data-quality issues in your live `jobs` table**, separate from this work:

1. `status` holds both `'PENDING'` and `'pending'`. Any `status == "PENDING"`
   filter silently misses the lowercase rows. Worth a one-off
   `UPDATE jobs SET status = upper(status)`.
2. Your row 1 "solar water" job is tagged `category: electrical` with
   earthing/surge tags. A solar hot-water job should route to plumbing or
   solar; as tagged, the taxonomy gate will send it to electricians.

## Workers data shape

1,200 rows across three outcomes:

- **947 matchable** — `is_complete`, `scenario_passed`, not rejected
- **~130 rejected** — completed the interview, failed the gate (all scored ≤ 75, with a written `rejection_reason`)
- **~120 in progress** — `is_complete = false`, stopped at one of ten interview stages, fields populated only up to the stage reached

Other properties worth knowing:

- **`user_id` is intentionally non-unique.** 973 distinct users across 1,200
  rows — 227 rows are a second or third trade for a user who already has a
  profile, matching your "one row per trade" comment on the column.
- **Scenario gate is respected.** Every `scenario_passed = true` row scores
  strictly above 75; no rejected row does. `verify_workers_csv.py` fails if
  that ever breaks.
- **32 trade categories.** Plumbing/electrical/carpentry/painting/masonry are
  common; elevator/bamboo-cane/soundproofing are rare. About 10% carry
  `is_custom_category = true`.
- **213 specialities with zero cross-trade leakage.** Each speciality belongs
  to exactly one trade. This is enforced, not assumed — an earlier version put
  `lock-picking` on a chimney specialist and `microwave-repair` on a pool
  technician, which would have polluted every match result in those trades.
- **947 unique job descriptions**, built from per-niche vocabulary with
  shuffled sentence order. Near-identical text would collapse the
  cosine-distance spread your Sigmoid depends on and every worker would score
  the same.
- **Locations** cluster around 22 real Kathmandu Valley neighborhoods with
  gaussian scatter, so the 20 km filter genuinely discriminates rather than
  matching everyone or no one.

## Jobs data shape

220 rows written from the **customer's** point of view.

- **203 service requests** (`is_job_request = true`) across 30 trades, plus
  **17 non-service requests** — drivers, tutors, movers, event help — with
  `is_job_request = false` and `categories = NULL`, mirroring the rows in your
  live table. These exist so the matching path is exercised against records it
  must correctly *ignore*.
- **Status mix** follows your real vocabulary (uppercase): ~95 `PENDING`,
  27 `MATCHED`, 38 `ASSIGNED`, 37 `COMPLETED`, 23 `CANCELLED`. `mode` is
  `express` / `regular`, roughly evenly split.
- **220/220 unique descriptions**, 225–600 chars, assembled from four layers:
  symptom, impact, trade-scoped detail, and the ask, with shuffled order.
- **`worker_id` is coherent with `status`.** NULL unless `ASSIGNED` or
  `COMPLETED`, and where set, the worker genuinely practises that trade and is
  usually within 20 km. A plumbing job assigned to an electrician would make
  the file useless for testing the match path.
- **`categories` JSONB** uses the same tags as `workers_seed.csv` — verified,
  zero unknown tags or specialities.
- **Attachments** on 143 rows as `[{"url","type"}]`, weighted toward urgent and
  visually obvious faults.

### Why job text reads nothing like worker text

This is the most important property of the pair, and the easiest to get wrong.

Worker descriptions are in the **provider's voice** — capabilities: *"traces
hidden leaks behind walls and under slabs, then repairs the failed section."*
Job descriptions are in the **customer's voice** — symptoms: *"water is pooling
in the cabinet under the kitchen sink and the cabinet base has swollen and gone
soft."*

They deliberately share little vocabulary (median overlap ~34% on common
tokens, and most of that is ordinary English). If both sides used the same
phrasing, cosine similarity would look excellent while actually measuring
string overlap, and you would learn nothing about whether nv-embed understands
that *"my sink is leaking"* means *plumber*. `verify_jobs_csv.py` warns if the
overlap climbs above 35%.

### Match coverage

Every open service request has candidates. Measured against the 947 matchable
workers at a 20 km radius:

- **minimum 1** candidate, **median 34**, maximum 65
- zero jobs with an empty candidate set

One job (`home-theatre`) has a single candidate. Realistic for a rare trade,
but thin if you want to test *ranking* within it.

## Format notes

Written for `COPY ... WITH (FORMAT csv, HEADER true, NULL '')`:

- Arrays as `{a,b,c}` literals, elements quoted only when needed
- JSONB as compact JSON, CSV-quoted with doubled inner quotes
- Booleans as `true` / `false`
- **Unquoted empty = NULL; quoted `""` = empty string.** This distinction is
  load-bearing — in-progress worker rows need `''` in NOT NULL text columns
  like `job_category`, not NULL. Python's `csv` module cannot express the
  difference, which is why both generators format fields by hand.
- `location` as `SRID=4326;POINT(lon lat)` — **longitude first**, per PostGIS
  axis order. A swapped pair puts Kathmandu in the Indian Ocean and every
  `ST_DWithin` returns nothing.
- `latitude` / `longitude` always agree with the `location` point

## Loading

Order matters — `jobs.worker_id` references users that the workers load
creates.

```bash
psql "$DATABASE_URL" -f load_workers.sql
psql "$DATABASE_URL" -f load_jobs.sql
```

Two things to check before you run them:

1. **The `users` inserts are a guess at your `User` model.** Both
   `workers.user_id` and `jobs.customer_id` are FKs to `users.id`, so parents
   must exist first. The scripts insert `(id, email, role)` — edit that to
   match your real NOT NULL columns. Worker ids are 1–973 and customer ids
   start at 974, derived from the staged data rather than hardcoded, so
   regenerating either CSV cannot leave the loaders out of step.
2. **`booking_chats`** — if you have that table, uncomment step 3 of
   `load_jobs.sql`. `jobs.booking_chat_id` is a UNIQUE FK.

Both scripts resync the identity sequences at the end. Skipping that would
make the next ORM insert collide on `id = 1`.

`load_jobs.sql` finishes with the query that matters most: for every open
service request, how many matchable workers of the same trade sit inside 20 km.
Any zero there means a job that can never be matched.

## Embeddings

`description_vector` is NULL in both files. Random vectors would have made
them ~40 MB and, worse, made your matching meaningless — cosine distance
against noise produces arbitrary scores, so you'd be testing that pgvector
stores numbers, not that the ranking works.

```bash
export NVIDIA_API_KEY=nvapi-...
export DATABASE_URL=postgresql+psycopg://user:pass@host:5432/handyman

python backfill_embeddings.py --table both --dry-run   # count first
python backfill_embeddings.py --table both --limit 32  # cost check
python backfill_embeddings.py --table both             # ~1,150 rows
```

**`input_type` differs by table and this is not cosmetic.** Workers embed as
`"passage"` (the stored side of the index); jobs embed as `"query"`.
nv-embed-v1 is trained asymmetrically, so embedding both sides the same way
shifts every cosine distance and your Sigmoid — `100/(1+e^(15*(d-0.87)))` —
lands in the wrong band. The script encodes this per table so it can't be got
wrong by hand.

It embeds only matchable rows by default (`--all` overrides) and is safe to
interrupt and re-run, since it only selects rows where the vector is still
NULL. After the backfill it prints a query that shows, for a sample of jobs,
whether the nearest worker by cosine distance is actually of the right trade —
if those disagree often, the embedding isn't carrying trade meaning and your
taxonomy gate is doing all the work.

Build the HNSW indexes after the backfill, not before:

```sql
CREATE INDEX idx_workers_vector_hnsw ON workers
    USING hnsw (description_vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

> **Known blocker from your 2026-08-03 eval work:** pgvector cannot build an
> HNSW index above 2,000 dimensions, so a `vector(4096)` column will reject
> this statement. Until the embedding is reduced or the column changed, vector
> search falls back to a sequential scan. That is a schema decision, not
> something the seed data can work around.

## Regenerating

```bash
python generate_workers.py     # edit N_ROWS first for a different count
python verify_workers_csv.py
python verify_copy_semantics.py

python generate_jobs.py        # reads workers_seed.csv — run it second
python verify_jobs_csv.py
```

`generate_jobs.py` reads `workers_seed.csv` to pick assignable workers and to
place customer ids above the worker id range, so **always regenerate jobs after
workers**. All verifiers exit non-zero on failure, so they drop straight into
CI or a pre-commit hook.

## Caveats

- `home-theatre` has fewer than 5 matchable workers. Fine for realism, thin if
  you want to test ranking *within* that trade — raise `N_ROWS` or reweight the
  custom-trade share in `generate_workers.py`.
- Trade content is written to be plausible and semantically distinct, not to be
  verified professional practice. It's seed data.
- No real Postgres was available to round-trip these files, so
  `verify_copy_semantics.py` emulates `COPY`'s parsing and casting rules
  instead. It's faithful to the documented behaviour, but a real
  `psql -f load_workers.sql` against a scratch database is still worth running
  once.
- Column sets follow the `WorkerProfile` and `Job` models you pasted. Your
  earlier audit noted the spec calls for 1:N `WorkerExpertise` rows with
  per-skill embeddings instead of one vector per profile — if you migrate to
  that, `workers_seed.csv` needs resplitting, one row per skill.
