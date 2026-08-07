# Getting the seed data into Postgres

A stepwise runbook for loading `workers_seed.csv` (1,200 rows) and `jobs_seed.csv`
(220 rows) into your `handy_man_db`. Written against **your actual schema**, read
from `backend/src/core/model.py`, `backend/migration/versions/`, and
`handy_man_db_dump.sql` — not against a guess.

Every step says what it does, what can go wrong, and how to tell whether it
worked. Run them in order. If a step's check fails, stop there; the later steps
assume the earlier ones succeeded.

---

## Step 0 — Understand what you are about to load

Before touching the database, know the shape of the thing.

The two CSVs are not standalone. They form a small dependency graph, and that
graph is exactly why the load order matters:

```
users  ──┬──> workers        (workers.user_id      FK, ON DELETE CASCADE)
         ├──> jobs.customer_id (FK, ON DELETE CASCADE)
         ├──> jobs.worker_id   (FK, ON DELETE SET NULL)
         └──> booking_chats.user_id (FK, ON DELETE CASCADE)

booking_chats ──> jobs.booking_chat_id  (FK UNIQUE, ON DELETE SET NULL)
roles ──> user_roles <── users
```

Neither CSV contains `users` rows. Both load scripts *derive* the parent users
from the staged data — `workers_seed.csv` supplies worker `user_id`s and
`jobs_seed.csv` supplies customer ids, in disjoint ranges so one `users.id` can
never be both sides of a job.

So the real load order is:

1. `users` (from workers) → `roles` / `user_roles` → `workers`
2. `users` (from jobs) → `booking_chats` → `jobs`

`load_workers.sql` does (1). `load_jobs.sql` does (2). **Workers first, always.**
Run jobs first and the script aborts, because the worker users its `worker_id`
column references don't exist yet.

### Your database already has data in the seed's id range

This is the thing that would have broken the load, so it's worth being explicit.
The seed numbers its rows from 1. Your live database (per the dump) holds 36
users, 20 workers, 3 jobs and 106 booking_chats — all low ids. Loading as-is is
not a merge, it's a crash:

| Collision | Count | Result |
|---|---|---|
| `workers.id` | 20 | `workers_pkey` violation — load aborts |
| `workers.worker_chat_id` | 20 | `ix_workers_worker_chat_id` violation |
| `jobs.id` | 3 | `jobs_pkey` violation |

And two *silent* ones, which are worse, because `ON CONFLICT DO NOTHING`
swallows them and the load appears to succeed with wrong data:

| Overlap | Count | Result |
|---|---|---|
| `users.id` | 36 | seeded workers attach to **your real user accounts** |
| `booking_chats.id` | 51 | seeded jobs point at **unrelated real transcripts** |

`load_workers.sql` therefore shifts every seeded id above your live data before
inserting anything. The offset is computed from the database at load time and
rounded up to a clean multiple of 1000, so it stays correct as your real data
grows, and seeded rows stay visually obvious — **ids under 1000 are real, 1000+
is seed.** With your current data every offset comes out at 1000.

The offsets are stored in a small `seed_id_offsets` table because
`load_jobs.sql` has to reuse the *same* `users` offset; it raises an exception if
that table is missing. Both scripts also assert after inserting that every parent
user is genuinely a seed account, so a wrong offset fails loudly instead of
silently attaching seed data to real people.

`load_workers.sql` additionally refuses to run twice. Because the offset derives
from the current max id, a second run would compute a *higher* offset and cheerfully
insert a duplicate 1,200 rows — the one failure mode that can't be detected after
the fact.

---

## Step 1 — Bring the database up

Your `docker-compose.yml` builds a custom image: `postgis/postgis:16-3.4` with
`postgresql-16-pgvector` layered on top. You need both extensions — PostGIS for
the `geography(Point,4326)` columns, pgvector for `vector(4096)`.

```bash
cd C:\Code\Handy_man\Handy_Man
docker compose up -d db
```

Wait for the healthcheck to pass rather than guessing:

```bash
docker compose ps db
```

You want `STATUS` to read `Up (healthy)`, not `Up (health: starting)`. On a first
run the image has to build (the `apt-get install` layer), which takes a couple of
minutes; after that it's cached.

**Check:**

```bash
docker exec -it handy_man_db psql -U postgres -d handy_man_db -c "SELECT version();"
```

If this hangs or refuses, the container is up but Postgres inside it isn't ready
yet. Give it 20 seconds.

---

## Step 2 — Verify the extensions actually exist

This is the step people skip, and it's the one that bites. The image *can*
install pgvector without the database *having* the extension enabled — those are
different things. A `CREATE EXTENSION` has to run inside your specific database.

```bash
docker exec -it handy_man_db psql -U postgres -d handy_man_db -c \
  "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS vector;"

docker exec -it handy_man_db psql -U postgres -d handy_man_db -c \
  "SELECT extname, extversion FROM pg_extension ORDER BY 1;"
```

**Expected:**

```
 extname | extversion
---------+------------
 plpgsql | 1.0
 postgis | 3.4.x
 vector  | 0.x.x
```

If `vector` is missing, the pgvector package didn't install. Rebuild without
cache: `docker compose build --no-cache db`.

Both load scripts start with `CREATE EXTENSION IF NOT EXISTS` too, so this is
belt and braces — but doing it separately means you find out *now* rather than
inside a failing transaction.

---

## Step 3 — Bring the schema to head

Your dump was taken at Alembic revision `86e44906ed03`. Your migration directory
head is `51d7d30a9ffb`. That's six revisions of drift — the dump predates
`worker_skills`, `matched_count`/`interested_count` on `jobs`, and the drop of
`worker_expertises`.

Meaning: **do not restore `handy_man_db_dump.sql` and expect a current schema.**
Migrate instead.

```bash
cd C:\Code\Handy_man\Handy_Man
alembic current          # what the DB thinks it is
alembic heads            # what the code says the latest is
alembic upgrade head
```

Your `alembic.ini` points `script_location` at `%(here)s/backend/migration`, so
run this from the repo root, not from `backend/`.

**Check:**

```bash
alembic current
```

should now print `51d7d30a9ffb (head)`.

Then confirm the tables the seed needs are really there:

```sql
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
  AND  table_name IN ('users','roles','user_roles','workers','jobs','booking_chats')
ORDER  BY 1;
```

All six must come back. If `booking_chats` is missing, `load_jobs.sql` step 3
will fail.

> **A note on the merge revision.** Your graph has two roots
> (`cf5b90d465ce` and `bd63e89c8028`, a no-op "temp fix") merged at
> `c6b01677d72c`. That's fine and it resolves, but it means `alembic downgrade`
> is not a clean single path. If you need to reset, drop and recreate the
> database rather than downgrading.

---

## Step 4 — Understand the CSV format before loading it

Two things about these files will bite you if you edit them by hand.

### 4a. Empty means NULL — but only if unquoted

Under `COPY ... WITH (FORMAT csv, NULL '')`:

| CSV text | Loads as |
|---|---|
| `a,,b` | `NULL` |
| `a,"",b` | `''` (empty string) |

This distinction is load-bearing. In-progress worker interview rows need `''` in
NOT NULL text columns (they have no data yet but the column can't be NULL);
genuinely absent values need `NULL`. Python's `csv` module cannot express both —
it writes the same thing for `None` and `""`. That's why `generate_workers.py`
and `generate_jobs.py` format every field by hand through a `fmt()` helper
instead of using `csv.writer`.

If you open these files in Excel and save, Excel will normalise the quoting and
silently destroy the distinction. **Edit the generator, regenerate the CSV.**
Never hand-edit.

### 4b. PostGIS points are (longitude latitude)

The `location` column is written as EWKT:

```
SRID=4326;POINT(85.3240 27.7172)
```

Longitude first. Swap them and Kathmandu lands in the Indian Ocean, every
`ST_DWithin` returns an empty set, and the matcher silently finds nobody — no
error, just zero results. `verify_*.py` check axis order and a Kathmandu Valley
bounding box for exactly this reason.

### 4c. Vectors are NULL on purpose

`description_vector` is empty in both files. Random 4,096-dim vectors would make
your Sigmoid scoring produce confident, meaningless numbers. Step 8 fills them
with real embeddings.

---

## Step 5 — Verify the CSVs before touching the database

Cheaper to fail here than mid-transaction.

```bash
cd C:\Code\Handy_man\Handy_Man\seed
python verify_workers_csv.py
python verify_jobs_csv.py
```

Both must print `PASS` and exit 0. `verify_jobs_csv.py` also cross-checks the
jobs against the workers file: every job's trade must exist in the worker
taxonomy, and every job must have at least one matchable worker of that trade
inside 20 km. Current expected output:

```
rows: 220
service jobs: 203, non-service: 17
taxonomy alignment: 0 unknown tags, 0 unknown specialities
candidates within 20.0 km: min 1, median 34, max 65
job/worker vocabulary overlap: median 34.3%, max 52.9%
unique descriptions: 220/220
PASS
```

One warning is expected and benign: job 209 (`home-theatre`) has only one
candidate. That trade is genuinely rare in the worker file.

---

## Step 6 — Load the workers

`\COPY` is a **psql client command**, not SQL. It reads the file from *your*
machine and streams it over the connection, which is why it works even though
Postgres is inside a container and can't see your filesystem. (`COPY` without the
backslash reads from the *server's* disk and would fail here.)

Run psql from the `seed/` directory so the relative CSV path resolves:

```bash
cd C:\Code\Handy_man\Handy_Man\seed

psql "postgresql://postgres:YOUR_PASSWORD@localhost:5432/handy_man_db" -f load_workers.sql
```

If `psql` isn't on your PATH on Windows, run it inside the container instead and
pipe the script in:

```bash
docker exec -i handy_man_db psql -U postgres -d handy_man_db < load_workers.sql
```

⚠ **The `docker exec` form breaks `\COPY`** — the client is now inside the
container and `workers_seed.csv` isn't there. Copy the files in first:

```bash
docker cp workers_seed.csv handy_man_db:/tmp/
docker cp jobs_seed.csv    handy_man_db:/tmp/
docker exec -it handy_man_db bash -c "cd /tmp && psql -U postgres -d handy_man_db" 
```

then `\i` the scripts from there. Installing the psql client locally is less
fiddly if you'll do this more than once.

### What `load_workers.sql` does, in order

1. `CREATE EXTENSION` (idempotent)
2. Creates a **TEMP staging table** typed loosely (text for `location`) and
   `\COPY`s into it. Staging first means a malformed row fails at `\COPY` with a
   line number, instead of half-loading into your real table.
3. Inserts parent `users` — `(id, email, password, username, "firstName",
   "lastName")`. Note the quoted camelCase columns; unquoted, Postgres folds them
   to lowercase and you get "column firstname does not exist".
4. Inserts the `worker` role and the `user_roles` rows. Your `User` model has
   **no `role` column** — roles are many-to-many. Skip this and every seeded
   worker exists but is invisible to any role-gated endpoint.
5. Inserts into `workers`, casting `location::geography(Point,4326)`.
6. `setval()` on both identity sequences.
7. Commits, then builds indexes.

### Why sequences must be resynced

The CSV supplies explicit `id` values. `nextval()` was never called, so the
sequence still sits at 1. The next insert your API does would try `id = 1`,
collide, and raise a duplicate key error. Step 6 fixes this:

```sql
SELECT setval(pg_get_serial_sequence('workers','id'),
              (SELECT COALESCE(MAX(id),1) FROM workers));
```

This is the single most common seed-data bug. If you ever load data by hand, do
this too.

### Why indexes come after the load

Building a GiST index once over 1,200 finished rows is much faster than
maintaining it across 1,200 individual inserts.

**Check:**

```sql
SELECT count(*) AS total FROM workers;
-- 1220  (1200 seeded + your 20 existing)

SELECT count(*) FILTER (WHERE is_complete AND scenario_passed AND NOT is_rejected) AS matchable,
       count(*) FILTER (WHERE is_rejected)                                          AS rejected,
       count(*) FILTER (WHERE description_vector IS NULL)                           AS needs_embedding
FROM   workers
WHERE  id > 1000;   -- seeded rows only
-- matchable 947 | rejected ~130 | needs_embedding 1200

SELECT count(DISTINCT user_id) FROM workers WHERE id > 1000;  -- 973
```

Note the counts are of *seeded* rows — filter on `id > 1000` to exclude your real
data, or the numbers won't match what the verifier reported.

`user_id` is deliberately non-unique: a user can complete several interviews, one
row per trade. Your model comment says exactly this. 1,200 worker rows across 973
users is correct, not a bug.

---

## Step 7 — Load the jobs

```bash
psql "postgresql://postgres:YOUR_PASSWORD@localhost:5432/handy_man_db" -f load_jobs.sql
```

Same structure, three differences worth knowing about.

**Staging types `categories` and `attachments` as `jsonb` directly.** If any
value were malformed JSON, `\COPY` fails immediately with a line number. This is
deliberate: your original `jobs.csv` had `categories` written with mixed `'` and
`"` quoting and `|` separators — not valid JSON — and that needed to fail loudly
somewhere.

**Both columns are `jsonb NOT NULL`** in your real DDL. The 17 non-service rows
(drivers, tutors, movers) therefore carry `[]`, not NULL. Your *live* table has
NULLs in those positions, but that data predates the constraint. `[]` still reads
as "no trade" to the matcher.

**`booking_chats` parents are created.** `jobs.booking_chat_id` is a UNIQUE FK and
201 of 220 jobs reference one. `booking_chats.history` is `json NOT NULL`, so the
script synthesises a minimal two-turn transcript from the job's own description —
consistent with the job rather than an empty stub, so these replay sensibly
through the analyser if you ever need them to.

There's also a guard that raises an exception if any `customer_id` collides with
a worker `user_id`. Silent overlap would mean one `users` row acting as both
customer and worker on the same job.

**Check:**

```sql
SELECT count(*) FROM jobs WHERE id > 1000;     -- 220
SELECT status, count(*) FROM jobs WHERE id > 1000 GROUP BY 1 ORDER BY 2 DESC;
-- PENDING 95 | ASSIGNED 38 | COMPLETED 37 | MATCHED 27 | CANCELLED 23
```

The script's last query is the one that actually matters — for every **open**
service request (128 of them; the rest already have a worker), how many matchable
workers of the same trade sit inside 20 km:

```
 min_candidates | avg_candidates | max_candidates | jobs_with_no_candidates
----------------+----------------+----------------+-------------------------
              6 |           34.5 |             65 |                       0
```

`jobs_with_no_candidates` **must be 0**. Anything else means `ST_DWithin` returns
an empty set for that job and it can never be matched, regardless of how good
your embeddings are.

(The `min` here is 6, while `verify_jobs_csv.py` reports 1. Not a contradiction —
the verifier covers all 203 service jobs, and the one thin case, job 209
`home-theatre`, is already assigned, so this query filters it out.)

---

## Step 8 — Backfill the embeddings

Everything so far was structural. This is the step that makes the data useful.

```bash
export NVIDIA_API_KEY=nvapi-...
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/handy_man_db"

python backfill_embeddings.py --table both --all
```

Start with a dry run and a small batch:

```bash
python backfill_embeddings.py --table workers --limit 20 --dry-run
```

### The one thing you must not get wrong

`nvidia/nv-embed-v1` is an asymmetric model. It takes an `input_type` parameter,
and the two sides of a search are embedded differently:

| Table | Column | `input_type` |
|---|---|---|
| `workers` | `job_description` | `passage` |
| `jobs` | `description` | `query` |

Workers are the *stored corpus*; jobs are the *thing being looked up*. Embed both
as `passage` and every cosine distance shifts — your Sigmoid
`100 / (1 + e^(15·(d − 0.87)))` then sits in the wrong band and scores become
meaningless while still looking plausible. That's the worst kind of bug: no error,
just quietly wrong numbers.

`backfill_embeddings.py` encodes this in a per-table config so it can't be got
wrong by hand.

**Check:**

```sql
SELECT count(*) FILTER (WHERE description_vector IS NULL) AS missing FROM workers;
SELECT count(*) FILTER (WHERE description_vector IS NULL) AS missing FROM jobs;
-- both 0
```

Sanity-check the distances themselves — a same-trade pair should be clearly
closer than a wrong-trade pair:

```sql
WITH j AS (SELECT description_vector v FROM jobs
           WHERE categories @> '[{"category":"plumbing"}]' LIMIT 1)
SELECT w.category_tag,
       round((w.description_vector <=> j.v)::numeric, 4) AS cosine_distance
FROM   workers w, j
WHERE  w.description_vector IS NOT NULL
ORDER  BY 2
LIMIT  10;
```

The top rows should be `plumbing`. If electricians and painters are interleaved
at similar distances, the embedding step went wrong — check `input_type` first.

---

## Step 9 — The 4096-dimension index problem

You will want an HNSW index. You cannot have one:

```sql
CREATE INDEX idx_workers_vector_hnsw
    ON workers USING hnsw (description_vector vector_cosine_ops);
-- ERROR: column cannot have more than 2000 dimensions for hnsw index
```

pgvector caps HNSW at **2,000 dimensions** and IVFFlat at 2,000 as well. Your
vectors are 4,096. There is no flag that lifts this.

At 1,200 workers a sequential scan is genuinely fine — it's roughly 20 MB of
vector data and completes in tens of milliseconds. The problem is that it grows
linearly, so this is a real scaling ceiling, not a cosmetic one.

Three ways out, in order of how much they cost you:

1. **Do nothing yet.** Seq scan at this size is acceptable. Revisit past ~50k rows.
2. **Reduce dimensions.** Store a 1,024-dim projection alongside the full vector,
   index that, use it to fetch the top ~200 candidates, then rerank exactly with
   the 4,096-dim column. This is the standard two-stage retrieval pattern and it
   keeps final scores identical.
3. **Switch models.** An embedding model that outputs ≤2,000 dims would be
   indexable directly, at the cost of re-embedding everything and recalibrating
   your Sigmoid.

Whichever you choose, the trade + distance gates run *before* the vector
comparison, so the candidate set the vector search sees is already small. That's
what makes option 1 viable for now.

---

## Step 10 — End-to-end verification

Prove the whole pipeline, not just the pieces.

```sql
-- 1. Nothing orphaned
SELECT count(*) FROM workers w LEFT JOIN users u ON u.id = w.user_id WHERE u.id IS NULL;
SELECT count(*) FROM jobs j    LEFT JOIN users u ON u.id = j.customer_id WHERE u.id IS NULL;
-- both 0

-- 2. Roles landed
SELECT r.name, count(*) FROM user_roles ur JOIN roles r ON r.id = ur.role_id
WHERE  ur.user_id > 1000 GROUP BY 1;
-- worker ~973, customer ~78

-- 3. No seeded row landed on your real data
SELECT count(*) FROM workers WHERE id <= 1000;  -- 20, your originals, untouched
SELECT count(*) FROM users
WHERE  id > 1000 AND email NOT LIKE 'seed.%@handyman.test';  -- must be 0

-- 4. Sequences are past the seeded ids
SELECT 'users' t, last_value FROM users_id_seq
UNION ALL SELECT 'workers', last_value FROM workers_id_seq
UNION ALL SELECT 'jobs',    last_value FROM jobs_id_seq
UNION ALL SELECT 'booking_chats', last_value FROM booking_chats_id_seq;

-- 5. Spatial index is actually used
EXPLAIN ANALYZE
SELECT id FROM workers
WHERE ST_DWithin(location,
                 ST_SetSRID(ST_MakePoint(85.3240, 27.7172), 4326)::geography,
                 20000);
-- want "Index Scan using idx_workers_location" — a Seq Scan means the GiST
-- index isn't being used, usually because ANALYZE hasn't run
```

Then run one real match through your actual `find_help` path and eyeball the
top five. Structural correctness is necessary but it isn't the goal; the goal is
that a plumbing complaint returns plumbers.

---

## Two bugs in your existing data

Both are in the rows already in your `jobs` table, not in the seed.

**Mixed-case status.** You have both `'PENDING'` and `'pending'`. Any
`WHERE status = 'PENDING'` silently misses the lowercase rows.

```sql
SELECT status, count(*) FROM jobs GROUP BY 1;   -- confirm first
UPDATE jobs SET status = upper(status) WHERE status <> upper(status);
```

Consider a CHECK constraint so it can't recur:

```sql
ALTER TABLE jobs ADD CONSTRAINT jobs_status_upper
    CHECK (status = upper(status));
```

**Miscategorised solar job.** Your row 1 "solar water" job is tagged
`category: electrical` with earthing/surge tags. The taxonomy gate will route it
to electricians. If solar hot water is plumbing work in your taxonomy, retag it —
otherwise it's a permanent false negative that looks like a matching bug.

---

## If you need to start over

```bash
docker compose down -v          # -v drops the volume, i.e. all data
docker compose up -d db
alembic upgrade head
psql "$DATABASE_URL" -f load_workers.sql
psql "$DATABASE_URL" -f load_jobs.sql
python backfill_embeddings.py --table both --all
```

To wipe just the seed rows without touching your real data — this is also what
you must run before re-loading, since `load_workers.sql` refuses to run twice.
Seeded rows are identifiable by the `id > 1000` offset and the seed email
pattern, so this can't touch your 36 real users or 20 real workers:

```sql
BEGIN;
DELETE FROM jobs          WHERE customer_id IN
       (SELECT id FROM users WHERE email LIKE 'seed.%@handyman.test');
DELETE FROM booking_chats WHERE user_id IN
       (SELECT id FROM users WHERE email LIKE 'seed.%@handyman.test');
DELETE FROM workers       WHERE user_id IN
       (SELECT id FROM users WHERE email LIKE 'seed.%@handyman.test');
DELETE FROM users         WHERE email LIKE 'seed.%@handyman.test';
DROP TABLE IF EXISTS seed_id_offsets;
COMMIT;
```

Check you removed what you meant to:

```sql
SELECT count(*) FROM users WHERE email LIKE 'seed.%@handyman.test';  -- 0
SELECT count(*) FROM users;     -- back to 36
SELECT count(*) FROM workers;   -- back to 20
```

Then re-run the `setval()` calls, or the sequences stay high.

---

## Regenerating the data

The generators are deterministic — same seed, same bytes.

```bash
python generate_workers.py     # SEED = 20260727
python generate_jobs.py        # SEED = 20260804 — reads workers_seed.csv
python verify_workers_csv.py
python verify_jobs_csv.py
```

**Workers first, always.** `generate_jobs.py` reads `workers_seed.csv` to pick
assignable workers and to place customer ids above the worker id range. Regenerate
jobs against a stale workers file and you get jobs assigned to workers that no
longer exist.

Want more rows? Change `N_ROWS` in `generate_workers.py` or `N_JOBS` in
`generate_jobs.py` and regenerate both. Don't hand-edit the CSVs — see step 4a.

---

## Quick reference

| Thing | Value |
|---|---|
| Container | `handy_man_db` |
| Database | `handy_man_db`, user `postgres`, port 5432 |
| Alembic head | `51d7d30a9ffb` (dump is at `86e44906ed03`, six behind) |
| Worker rows | 1,200 seeded (947 matchable, 973 distinct users) + 20 live |
| Job rows | 220 seeded (203 service, 17 non-service) + 3 live |
| Id offset | +1000 on every seeded id; under 1000 is your real data |
| Match radius | 20 km |
| Vector dims | 4,096 (above pgvector's 2,000 HNSW limit) |
| `input_type` | workers `passage`, jobs `query` |
| Scenario gate | `scenario_score > 75` |
