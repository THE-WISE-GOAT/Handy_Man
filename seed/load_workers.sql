-- =====================================================================
--  Handy_Man — load workers_seed.csv into public.workers
--  Target: PostgreSQL + PostGIS + pgvector
--
--  Run with:   psql "$DATABASE_URL" -f load_workers.sql
--  (\COPY is a psql client command — it reads the CSV from YOUR machine,
--   not the server's filesystem, so it works against remote/managed DBs.)
--
--  Adjust the path on the \COPY line below if the CSV is elsewhere.
-- =====================================================================

\set ON_ERROR_STOP on

BEGIN;

-- ---------------------------------------------------------------------
-- 0. Prerequisites
-- ---------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------
-- 1. Staging table
--
--    Loaded as text first, then cast. This keeps \COPY from choking on
--    the EWKT geography literal and lets the array/boolean casts happen
--    explicitly where you can see them.
--
--    Staging comes BEFORE the users insert on purpose: the parent user
--    ids are then derived from the data itself rather than hardcoded, so
--    regenerating the CSV with a different row count can never leave this
--    script out of step with it.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS workers_stage;

CREATE TEMP TABLE workers_stage (
    id                             integer,
    user_id                        integer,
    worker_chat_id                 integer,
    stage                          text,
    is_complete                    boolean,
    is_rejected                    boolean,
    rejection_reason               text,
    job_category                   text,
    category_tag                   text,
    is_custom_category             boolean,
    specialities                   text[],
    specialized_tools_or_equipment text[],
    years_experience               integer,
    license_or_certification       text,
    job_description                text,
    emergency_available            boolean,
    has_verified_specialty         boolean,
    scenario_passed                boolean,
    scenario_score                 integer,
    description_vector             text,     -- always NULL in the seed
    phone_number                   text,
    address_text                   text,
    latitude                       double precision,
    longitude                      double precision,
    location                       text      -- 'SRID=4326;POINT(lon lat)'
);

\COPY workers_stage FROM 'workers_seed.csv' WITH (FORMAT csv, HEADER true, NULL '')

-- ---------------------------------------------------------------------
-- 1b. Id offsets — DO NOT SKIP
--
--    The seed numbers its rows from 1, and your database already has real
--    data in that range (as of the dump: 36 users, 20 workers with
--    worker_chat_id 1-25, 3 jobs, 106 booking_chats). Loading as-is is a
--    hard failure, not a merge:
--
--      workers.id             20 collisions -> workers_pkey violation
--      workers.worker_chat_id 20 collisions -> ix_workers_worker_chat_id
--      jobs.id                 3 collisions -> jobs_pkey violation
--
--    And two SILENT problems, which are worse — ON CONFLICT DO NOTHING
--    swallows them and the load "succeeds" with wrong data:
--      users.id         36 overlaps -> seed workers get attached to YOUR
--                       real user accounts instead of seed ones
--      booking_chats.id 51 overlaps -> seed jobs point at unrelated real
--                       chat transcripts
--
--    So every id is shifted above your live data. The offset is computed
--    from the database at load time and rounded up to a clean multiple of
--    1000, so it stays correct as your real data grows and the seeded rows
--    stay visually obvious (ids 1001+ are seed, below 1000 is real).
--
--    The offsets are recorded in a permanent table because load_jobs.sql
--    must apply the SAME user offset — otherwise jobs reference worker
--    users that don't exist.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS seed_id_offsets (
    name  text PRIMARY KEY,
    value integer NOT NULL
);

-- Re-run guard. Because the offset is derived from the CURRENT max id, a
-- second run would compute a HIGHER offset and happily insert a duplicate
-- 1,200 rows rather than erroring. That is the one failure mode this
-- script cannot detect after the fact, so refuse up front.
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM users
    WHERE  email LIKE 'seed.worker%@handyman.test';
    IF n > 0 THEN
        RAISE EXCEPTION
          'seed data already loaded (% seed worker users found). '
          'To reload, first run the cleanup block in POSTGRES_RUNBOOK.md.', n;
    END IF;
END $$;

TRUNCATE seed_id_offsets;

INSERT INTO seed_id_offsets (name, value)
SELECT 'users',          (COALESCE((SELECT max(id) FROM users), 0) / 1000 + 1) * 1000
UNION ALL
SELECT 'workers',        (COALESCE((SELECT max(id) FROM workers), 0) / 1000 + 1) * 1000
UNION ALL
SELECT 'worker_chat',    (COALESCE((SELECT max(worker_chat_id) FROM workers), 0) / 1000 + 1) * 1000
UNION ALL
SELECT 'jobs',           (COALESCE((SELECT max(id) FROM jobs), 0) / 1000 + 1) * 1000
UNION ALL
SELECT 'booking_chats',  (COALESCE((SELECT max(id) FROM booking_chats), 0) / 1000 + 1) * 1000;

\echo 'Id offsets chosen (seeded rows will start above your live data):'
SELECT name, value FROM seed_id_offsets ORDER BY name;

-- Apply them in place, so every statement below can ignore the issue.
UPDATE workers_stage SET
    id             = id             + (SELECT value FROM seed_id_offsets WHERE name = 'workers'),
    user_id        = user_id        + (SELECT value FROM seed_id_offsets WHERE name = 'users'),
    worker_chat_id = worker_chat_id + (SELECT value FROM seed_id_offsets WHERE name = 'worker_chat');

-- ---------------------------------------------------------------------
-- 2. Parent users
--
--    workers.user_id is FK -> users.id ON DELETE CASCADE, so the parent
--    rows must exist first. The ids come straight from the staged data,
--    so this stays correct no matter how the CSV is regenerated.
--
--    Columns verified against your actual schema (backend/src/core/model.py
--    and handy_man_db_dump.sql):
--      users(id, email NOT NULL UNIQUE, password NOT NULL,
--            username NOT NULL UNIQUE, "firstName", "lastName",
--            is_active DEFAULT true, created_at DEFAULT now())
--
--    There is NO `role` column — roles are a many-to-many through
--    user_roles, handled in step 3.
--
--    The password is a fixed bcrypt hash of the string 'seedpassword'.
--    These are throwaway local seed accounts; do not load this into any
--    environment reachable from the internet.
-- ---------------------------------------------------------------------
INSERT INTO users (id, email, password, username, "firstName", "lastName")
SELECT  DISTINCT
        user_id,
        'seed.worker' || user_id || '@handyman.test',
        '$2b$12$Ii0Sh4W5X5nCsHrJ4a0hQeQZ5ZfW1oJgqzq7dQFtV6Hn3cB2VzKcy',
        'seed_worker_' || user_id,
        'Seed',
        'Worker ' || user_id
FROM    workers_stage
ON CONFLICT (id) DO NOTHING;

-- Assert every parent user is genuinely a SEED user. ON CONFLICT DO NOTHING
-- is silent by design: if an offset were ever wrong and a staged user_id
-- landed on one of your real accounts, the insert would skip, the FK below
-- would still succeed, and 1,200 seeded workers would quietly attach
-- themselves to real people. Catch that here instead.
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n
    FROM  (SELECT DISTINCT user_id FROM workers_stage) s
    JOIN  users u ON u.id = s.user_id
    WHERE u.email NOT LIKE 'seed.worker%@handyman.test';
    IF n > 0 THEN
        RAISE EXCEPTION
          '% staged worker user_id(s) resolve to non-seed users — '
          'the id offset is wrong; aborting rather than attaching seed '
          'workers to real accounts', n;
    END IF;
END $$;

-- ---------------------------------------------------------------------
-- 3. Give them the worker role
--
--    Your User model has no role column; it goes through the user_roles
--    join table. Without this, every seeded worker exists but has no role,
--    and any endpoint gated on the worker role will ignore them.
-- ---------------------------------------------------------------------
INSERT INTO roles (name)
SELECT 'worker'
WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'worker');

INSERT INTO user_roles (user_id, role_id)
SELECT DISTINCT s.user_id, r.id
FROM   workers_stage s
CROSS  JOIN (SELECT id FROM roles WHERE name = 'worker') r
ON CONFLICT (user_id, role_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- 4. Insert into the real table
--
--    location is cast from EWKT. Note PostGIS POINT order is (lon lat) —
--    longitude first. The seed already writes it that way.
-- ---------------------------------------------------------------------
INSERT INTO workers (
    id, user_id, worker_chat_id, stage, is_complete, is_rejected,
    rejection_reason, job_category, category_tag, is_custom_category,
    specialities, specialized_tools_or_equipment, years_experience,
    license_or_certification, job_description, emergency_available,
    has_verified_specialty, scenario_passed, scenario_score,
    description_vector, phone_number, address_text, latitude, longitude,
    location
)
SELECT
    id, user_id, worker_chat_id, stage, is_complete, is_rejected,
    rejection_reason, job_category, category_tag, is_custom_category,
    specialities, specialized_tools_or_equipment, years_experience,
    license_or_certification, job_description, emergency_available,
    has_verified_specialty, scenario_passed, scenario_score,
    NULL::vector(4096),
    phone_number, address_text, latitude, longitude,
    location::geography(Point, 4326)
FROM workers_stage;

-- ---------------------------------------------------------------------
-- 5. Resync the identity sequence
--
--    Explicit ids were supplied, so the sequence still thinks it is at 1
--    and the next ORM insert would collide. This fixes that.
-- ---------------------------------------------------------------------
SELECT setval(
    pg_get_serial_sequence('workers', 'id'),
    (SELECT COALESCE(MAX(id), 1) FROM workers)
);

-- Do the same for users if you inserted them above.
SELECT setval(
    pg_get_serial_sequence('users', 'id'),
    (SELECT COALESCE(MAX(id), 1) FROM users)
);

COMMIT;

-- ---------------------------------------------------------------------
-- 6. Indexes for the matching path
--
--    Built AFTER load — much faster than maintaining them during insert.
--
--    Your migrations already create `idx_workers_location` as GiST, which
--    is what makes ST_DWithin use the spatial index instead of scanning
--    every worker. Do NOT add a second GiST index over the same column —
--    it doubles write cost and buys nothing. The block below only creates
--    it if the migration one is somehow absent.
-- ---------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE  tablename = 'workers' AND indexdef ILIKE '%gist%location%'
    ) THEN
        CREATE INDEX idx_workers_location_gist ON workers USING GIST (location);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_workers_matchable
    ON workers (category_tag)
    WHERE is_complete AND scenario_passed AND NOT is_rejected;

-- Vector index: create this only AFTER backfilling description_vector.
-- An HNSW index over an all-NULL column is pointless, and building it
-- before the backfill just slows the backfill down.
--
--   CREATE INDEX idx_workers_vector_hnsw
--       ON workers USING hnsw (description_vector vector_cosine_ops)
--       WITH (m = 16, ef_construction = 64);

ANALYZE workers;

-- ---------------------------------------------------------------------
-- 7. Sanity checks
--
--    Seeded rows are split out from your pre-existing ones. Counting them
--    together would not match the figures verify_workers_csv.py reports,
--    and you would not be able to tell a load problem from your own data.
-- ---------------------------------------------------------------------
SELECT
    count(*)                                          AS total_workers,
    count(*) FILTER (WHERE id >  (SELECT value FROM seed_id_offsets
                                  WHERE name = 'workers'))  AS seeded,
    count(*) FILTER (WHERE id <= (SELECT value FROM seed_id_offsets
                                  WHERE name = 'workers'))  AS pre_existing
FROM workers;
-- expect: seeded = 1200, pre_existing = your original count (20 per the dump)

SELECT
    count(*) FILTER (WHERE is_complete AND scenario_passed AND NOT is_rejected) AS matchable,
    count(*) FILTER (WHERE is_rejected)                                          AS rejected,
    count(*) FILTER (WHERE NOT is_complete)                                      AS in_progress,
    count(*) FILTER (WHERE description_vector IS NULL)                           AS needs_embedding
FROM   workers
WHERE  id > (SELECT value FROM seed_id_offsets WHERE name = 'workers');
-- expect: matchable 947, rejected ~130, needs_embedding 1200

-- How many matchable workers fall inside a 20 km radius of central
-- Kathmandu? This is the canonical radius per the project spec.
SELECT count(*) AS within_20km
FROM   workers
WHERE  is_complete AND scenario_passed AND NOT is_rejected
  AND  ST_DWithin(
           location,
           ST_SetSRID(ST_MakePoint(85.3240, 27.7172), 4326)::geography,
           20000
       );
