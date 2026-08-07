-- =====================================================================
--  Handy_Man — load jobs_seed.csv into public.jobs
--  Target: PostgreSQL + PostGIS + pgvector
--
--  Run AFTER load_workers.sql:
--      psql "$DATABASE_URL" -f load_workers.sql
--      psql "$DATABASE_URL" -f load_jobs.sql
--
--  Order matters. jobs.worker_id references worker user ids that
--  load_workers.sql creates, so running this first will fail the FK.
-- =====================================================================

\set ON_ERROR_STOP on

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------
-- 1. Staging table
--
--    Text/native types first, then cast on insert. categories and
--    attachments stage as jsonb directly — if any value in the CSV were
--    malformed JSON, \COPY fails HERE with a line number rather than
--    silently loading garbage. That is deliberate: your original
--    jobs.csv had categories written with mixed ' and " quoting plus |
--    separators, which is not valid JSON and would have to be caught
--    somewhere.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS jobs_stage;

CREATE TEMP TABLE jobs_stage (
    id                 integer,
    customer_id        integer,
    booking_chat_id    integer,
    worker_id          integer,
    title              text,
    description        text,
    status             text,
    is_job_request     boolean,
    categories         jsonb,
    contact_name       text,
    contact_phone      text,
    mode               text,
    attachments        jsonb,
    address_text       text,
    latitude           double precision,
    longitude          double precision,
    location           text,      -- 'SRID=4326;POINT(lon lat)'
    description_vector text,      -- always NULL in the seed
    created_at         timestamp,
    updated_at         timestamp
);

\COPY jobs_stage FROM 'jobs_seed.csv' WITH (FORMAT csv, HEADER true, NULL '')

-- ---------------------------------------------------------------------
-- 1b. Id offsets — must match load_workers.sql
--
--    load_workers.sql shifted every seeded id above your live data and
--    recorded the offsets in seed_id_offsets. This script MUST reuse the
--    same 'users' offset, or jobs.worker_id will point at users that were
--    never created and the FK fails.
--
--    That is why load_workers.sql has to run first, and why this fails
--    loudly rather than guessing an offset of its own.
-- ---------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'seed_id_offsets') THEN
        RAISE EXCEPTION
          'seed_id_offsets is missing — run load_workers.sql first';
    END IF;
END $$;

UPDATE jobs_stage SET
    id              = id              + (SELECT value FROM seed_id_offsets WHERE name = 'jobs'),
    customer_id     = customer_id     + (SELECT value FROM seed_id_offsets WHERE name = 'users'),
    worker_id       = worker_id       + (SELECT value FROM seed_id_offsets WHERE name = 'users'),
    booking_chat_id = booking_chat_id + (SELECT value FROM seed_id_offsets WHERE name = 'booking_chats');

-- ---------------------------------------------------------------------
-- 2. Parent customer users
--
--    jobs.customer_id is FK -> users.id. Customer ids in the seed start
--    above the highest worker user id so the two files never collide on
--    users.id; ids are derived from the staged data so this cannot drift.
--
--    Columns verified against backend/src/core/model.py: users has NO
--    `role` column (roles go through user_roles), and password/username
--    are NOT NULL. The password below is a fixed bcrypt hash of
--    'seedpassword' — throwaway local accounts only.
-- ---------------------------------------------------------------------
INSERT INTO users (id, email, password, username, "firstName", "lastName")
SELECT  DISTINCT
        customer_id,
        'seed.customer' || customer_id || '@handyman.test',
        '$2b$12$Ii0Sh4W5X5nCsHrJ4a0hQeQZ5ZfW1oJgqzq7dQFtV6Hn3cB2VzKcy',
        'seed_customer_' || customer_id,
        'Seed',
        'Customer ' || customer_id
FROM    jobs_stage
ON CONFLICT (id) DO NOTHING;

-- Same silent-skip assertion as load_workers.sql: every customer parent
-- must be a seed account, never one of your real users.
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n
    FROM  (SELECT DISTINCT customer_id FROM jobs_stage) s
    JOIN  users u ON u.id = s.customer_id
    WHERE u.email NOT LIKE 'seed.customer%@handyman.test';
    IF n > 0 THEN
        RAISE EXCEPTION
          '% staged customer_id(s) resolve to non-seed users — '
          'the id offset is wrong; aborting', n;
    END IF;
END $$;

-- Every seeded worker_id must resolve to a seed WORKER user created by
-- load_workers.sql. If load_workers.sql was run against a different offset,
-- this catches it before the FK does.
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n
    FROM  (SELECT DISTINCT worker_id FROM jobs_stage WHERE worker_id IS NOT NULL) s
    LEFT  JOIN users u ON u.id = s.worker_id
    WHERE u.id IS NULL OR u.email NOT LIKE 'seed.worker%@handyman.test';
    IF n > 0 THEN
        RAISE EXCEPTION
          '% staged worker_id(s) do not resolve to seed worker users — '
          'run load_workers.sql first, or the offsets are out of step', n;
    END IF;
END $$;

INSERT INTO roles (name)
SELECT 'customer'
WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'customer');

INSERT INTO user_roles (user_id, role_id)
SELECT DISTINCT j.customer_id, r.id
FROM   jobs_stage j
CROSS  JOIN (SELECT id FROM roles WHERE name = 'customer') r
ON CONFLICT (user_id, role_id) DO NOTHING;

-- Fail loudly if a customer id landed on an existing worker. Silent
-- overlap would mean one users row acting as both sides of a job.
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n
    FROM   jobs_stage j
    JOIN   workers w ON w.user_id = j.customer_id;
    IF n > 0 THEN
        RAISE EXCEPTION
          'customer_id overlaps worker user_id on % row(s) — '
          'raise CUSTOMER_ID_BASE in generate_jobs.py and regenerate', n;
    END IF;
END $$;

-- ---------------------------------------------------------------------
-- 3. Booking chats
--
--    jobs.booking_chat_id is a UNIQUE FK -> booking_chats(id), so these
--    parents are NOT optional: ~92% of seeded jobs reference one, and
--    without this step every one of those rows fails the FK.
--
--    Real DDL (from your dump):
--      booking_chats(id, user_id NOT NULL, history json NOT NULL,
--                    is_complete NOT NULL DEFAULT false,
--                    is_job_request NOT NULL DEFAULT false,
--                    categories jsonb, problem_description text)
--
--    `history` is NOT NULL, so a minimal two-turn transcript is
--    synthesised from the job's own title and description. That keeps the
--    chat consistent with the job rather than inserting an empty array —
--    if you ever replay these chats through the analyser, they read as
--    real conversations.
-- ---------------------------------------------------------------------
INSERT INTO booking_chats (
    id, user_id, history, is_complete, is_job_request,
    categories, problem_description
)
SELECT  booking_chat_id,
        customer_id,
        json_build_array(
            json_build_object('role', 'assistant',
                              'content', 'Hi! What do you need help with today?'),
            json_build_object('role', 'user',
                              'content', description)
        ),
        true,
        is_job_request,
        categories,
        description
FROM    jobs_stage
WHERE   booking_chat_id IS NOT NULL
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('booking_chats', 'id'),
    (SELECT COALESCE(MAX(id), 1) FROM booking_chats)
);

-- ---------------------------------------------------------------------
-- 4. Insert into the real table
-- ---------------------------------------------------------------------
INSERT INTO jobs (
    id, customer_id, booking_chat_id, worker_id, title, description,
    status, is_job_request, categories, contact_name, contact_phone,
    mode, attachments, address_text, latitude, longitude, location,
    description_vector, created_at, updated_at
)
SELECT
    id, customer_id, booking_chat_id, worker_id, title, description,
    status, is_job_request, categories, contact_name, contact_phone,
    mode, attachments, address_text, latitude, longitude,
    location::geography(Point, 4326),
    NULL::vector(4096),
    created_at, updated_at
FROM jobs_stage;

-- ---------------------------------------------------------------------
-- 5. Resync the identity sequence
-- ---------------------------------------------------------------------
SELECT setval(
    pg_get_serial_sequence('jobs', 'id'),
    (SELECT COALESCE(MAX(id), 1) FROM jobs)
);

SELECT setval(
    pg_get_serial_sequence('users', 'id'),
    (SELECT COALESCE(MAX(id), 1) FROM users)
);

COMMIT;

-- ---------------------------------------------------------------------
-- 6. Indexes
-- ---------------------------------------------------------------------
-- Your migrations already ship `idx_jobs_location` as GiST. A second GiST
-- index over the same column doubles write cost and buys nothing, so only
-- create one if the migration's is somehow missing.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE  tablename = 'jobs' AND indexdef ILIKE '%gist%location%'
    ) THEN
        CREATE INDEX idx_jobs_location_gist ON jobs USING GIST (location);
    END IF;
END $$;

-- The dispatcher's hot path: open service requests awaiting a match.
CREATE INDEX IF NOT EXISTS idx_jobs_open_requests
    ON jobs (status)
    WHERE is_job_request AND worker_id IS NULL;

-- GIN over categories makes tag containment queries indexable, e.g.
--   WHERE categories @> '[{"category":"plumbing"}]'
CREATE INDEX IF NOT EXISTS idx_jobs_categories_gin
    ON jobs USING GIN (categories jsonb_path_ops);

-- Vector index only after backfilling description_vector.
--   CREATE INDEX idx_jobs_vector_hnsw
--       ON jobs USING hnsw (description_vector vector_cosine_ops)
--       WITH (m = 16, ef_construction = 64);

ANALYZE jobs;

-- ---------------------------------------------------------------------
-- 7. Sanity checks
--
--    Scoped to seeded rows. Your 3 pre-existing jobs would otherwise
--    pollute every figure here — one of them has a lowercase 'pending'
--    status, and their NULL locations would show up as false zeros in the
--    match-coverage query below.
-- ---------------------------------------------------------------------
SELECT
    count(*)                                       AS total_jobs,
    count(*) FILTER (WHERE id >  (SELECT value FROM seed_id_offsets
                                  WHERE name = 'jobs')) AS seeded,
    count(*) FILTER (WHERE id <= (SELECT value FROM seed_id_offsets
                                  WHERE name = 'jobs')) AS pre_existing
FROM jobs;
-- expect: seeded = 220, pre_existing = 3

SELECT status, count(*) FROM jobs
WHERE  id > (SELECT value FROM seed_id_offsets WHERE name = 'jobs')
GROUP  BY status ORDER BY 2 DESC;
-- expect: PENDING 95, ASSIGNED 38, COMPLETED 37, MATCHED 27, CANCELLED 23

SELECT
    count(*) FILTER (WHERE is_job_request)                     AS service_requests,
    count(*) FILTER (WHERE NOT is_job_request)                 AS non_service,
    count(*) FILTER (WHERE worker_id IS NOT NULL)              AS assigned,
    count(*) FILTER (WHERE description_vector IS NULL)         AS needs_embedding,
    count(*) FILTER (WHERE jsonb_array_length(attachments) > 0) AS with_attachments
FROM   jobs
WHERE  id > (SELECT value FROM seed_id_offsets WHERE name = 'jobs');
-- expect: service_requests 203, non_service 17, needs_embedding 220

-- The real test of this seed data: for each open service request, how
-- many matchable workers of the same trade sit inside the 20 km radius?
-- A zero anywhere means ST_DWithin returns an empty candidate set and
-- that job can never be matched.
WITH open_jobs AS (
    SELECT j.id,
           j.location,
           c->>'category' AS tag
    FROM   jobs j
    CROSS JOIN LATERAL jsonb_array_elements(j.categories) AS c
    WHERE  j.is_job_request
      AND  j.worker_id IS NULL
      AND  j.id > (SELECT value FROM seed_id_offsets WHERE name = 'jobs')
)
SELECT
    min(n)                              AS min_candidates,
    round(avg(n), 1)                    AS avg_candidates,
    max(n)                              AS max_candidates,
    count(*) FILTER (WHERE n = 0)       AS jobs_with_no_candidates
FROM (
    SELECT o.id,
           count(w.id) AS n
    FROM   open_jobs o
    LEFT JOIN workers w
           ON w.category_tag = o.tag
          AND w.is_complete AND w.scenario_passed AND NOT w.is_rejected
          AND ST_DWithin(w.location, o.location, 20000)
    GROUP BY o.id
) t;
-- expect: min 6, avg 34.5, max 65, jobs_with_no_candidates 0
-- (128 open jobs. The min is 6 here, not the 1 that verify_jobs_csv.py
--  reports — the verifier covers all 203 service jobs including assigned
--  ones, and the single thin case, job 209 home-theatre, is assigned.)
-- jobs_with_no_candidates MUST be 0 — anything else is unmatchable data.

-- Trades customers are asking for that no worker covers. Should be empty;
-- any row here is a gap in the supply side of the marketplace.
SELECT c->>'category' AS requested_trade, count(*) AS jobs
FROM   jobs j
CROSS JOIN LATERAL jsonb_array_elements(j.categories) AS c
WHERE  j.is_job_request
  AND  j.id > (SELECT value FROM seed_id_offsets WHERE name = 'jobs')
  AND  NOT EXISTS (
           SELECT 1 FROM workers w
           WHERE  w.category_tag = c->>'category'
             AND  w.is_complete AND w.scenario_passed AND NOT w.is_rejected
       )
GROUP BY 1
ORDER BY 2 DESC;
