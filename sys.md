# System Manifesto — Handy Man (Kamigo) Platform
## Whole-Scan Audit Report
**Generated:** 2026-08-07  
**Scope:** Full repository deep-dive (backend, frontend, database, WebSocket, AI/NIM integration)

---

## 1. System Architecture & Tech Stack

### Overview
Handy Man (branded **Kamigo**) is a multi-role service marketplace platform connecting **Customers** who need work done with **Workers** (tradespeople) who can perform that work. The platform uses an AI-powered dispatch interview to extract structured job requests, then runs a semantic vector-matching engine (pgvector + NVIDIA NIM embeddings + LLM reranking) to pair jobs with the best-fit workers. A worker onboarding/vetting flow uses a second AI interview plus scenario-based testing to verify skills before a worker can accept jobs.

**Communication model:**
- **Frontend → Backend:** REST (FastAPI) + WebSocket (live notifications, chat)
- **Backend → AI:** NVIDIA NIM (`integrate.api.nvidia.com`) for Llama 3.1 chat, `nvidia/nv-embed-v1` embeddings, and `meta/llama-3.1-8b-instruct` reranking
- **Backend → Database:** PostgreSQL + PostGIS (geography) + pgvector (4096-d embeddings)
- **Frontend → Maps:** Leaflet + react-leaflet (OpenStreetMap tiles, Nominatim reverse geocoding)

### Database Schema
Core tables and relationships (defined in `backend/src/core/model.py`):

| Table | Purpose | Key Relations |
|---|---|---|
| `users` | Auth base. email/username unique, password hash, roles via M2M | → `user_roles` → `roles` |
| `roles` / `user_roles` | RBAC: customer (1), worker (2), admin (3) | Many-to-many with users |
| `booking_chats` | Customer AI-dispatch sessions. Stores `history` (JSON), `categories` (JSONB), `is_complete`, `is_job_request`, `problem_description` | `user_id` → users |
| `worker_interview_sessions` | Worker vetting chat. Tracks `stage`, `is_complete`, `is_rejected`, `profile` (JSONB), `add_skill_turns` (JSONB), scenario scores | `user_id` → users |
| `workers` (WorkerProfile) | Worker profile. One row per trade per user. Contains `job_category`, `category_tag`, `specialities` (PG array), `description_vector` (4096-d), `location` (Geography POINT), `worker_chat_id` (unique) | `user_id` → users |
| `worker_skills` | Independently matchable skill rows (BASELINE or SPECIALITY). Each has its own `embedding` (Vector 4096), scenario metadata, attachment flags | `worker_id` → workers |
| `jobs` | Operational job records. `status` (draft/pending/matched/completed/assigned), `categories` (JSONB), `description_vector`, `location`, `worker_id` (nullable), `booking_chat_id` (nullable FK) | `customer_id`, `worker_id` → users; `booking_chat_id` → booking_chats |
| `job_worker_matches` | Pre-computed matches. Tracks `match_score`, `match_rank`, `semantic_distance`, `is_interested`, `bid_amount`, `is_selected`, `is_rejected` | `job_id` → jobs, `worker_id` → workers, `matched_skill_id` → worker_skills |
| `bids` | Legacy bid table (appears unused by active matching flow; `JobWorkerMatch.bid_amount` is the live bid store) | `task_id` → service_tasks, `worker_id` → workers |
| `service_tasks` | Legacy task table; partially superseded by `jobs` | `customer_id` → users |
| `customer_chat_data` | Analytical/CRM copy of booking chat extraction results | `user_id` → users, `booking_chat_id` unique |

### State Management
**Frontend uses Zustand** (v4.5.4) with "Zlice" pattern (slice-composable stores):

- **Customer:** `useCustomerDashboardData` composes `bookingsZlice`, `postingsZlice`, `moreZlice`
- **Worker:** `useWorkerDashboardData` composes `workspaceZlice`, `scheduledZlice`, `meZlice`, `micsZlice`
- **Auth:** `AuthContext` (React Context) manages token, user profile, role checks, login/logout
- **Routing state:** Each dashboard board (`dash1board`, `dash2board`, etc.) maintains its own `slots` state object that maps `{main, bottom, sidebar}` to view slugs, enabling the multi-pane "FixFast" layout

**Key global state flows:**
1. Customer creates job via AI chat → `booking_chats` created → `jobs` upserted → `matching_manager.create_matches_for_job()` populates `job_worker_matches` → WebSocket alerts sent to matched workers
2. Worker receives `NEW_JOB_NOTIFICATION` via WS → views matched jobs → expresses interest / places bid → customer sees bid in real-time → customer books worker → `job.status = "assigned"`, `job.worker_id` set
3. Worker onboarding: `worker_interview_sessions` → AI extraction → `worker_profiles` + `worker_skills` created → admin approves → worker becomes matchable

---

## 2. Current Flow & Routing

### User Journeys

#### Customer Journey
1. **Auth:** Sign up / log in → JWT token stored in `localStorage`
2. **AI Dispatch:** Customer opens dashboard → starts `/dispatch/session` → AI chat extracts problem description, categories, location → session marked `is_complete`
3. **Job Finalization:** Customer reviews/edit description → calls `/dispatch/{id}/complete` → backend creates `Job` record, generates embedding, runs matching engine → workers receive WebSocket `NEW_JOB_NOTIFICATION`
4. **Manage Postings:** Customer views active pending jobs → selects job → sees matched workers on map + list → opens chat with workers → receives bids → books worker → job status becomes `assigned`
5. **Assigned Jobs:** Customer views assigned worker details, schedule, location

#### Worker Journey
1. **Auth / Onboarding:** Worker logs in → if not onboarded, redirected to `/worker/me/MeInterview` → starts AI interview → completes scenario test (if required) → submits application for admin review
2. **Admin Approval:** Admin reviews application in `/admin/applications/WorkerApplications` → approves/rejects → worker `WorkerProfile.stage = "approved"`
3. **Job Discovery:** Worker dashboard fetches `/jobs/for-worker` → sees matched jobs → expresses interest or places bid
4. **Assignment & Chat:** Worker gets assigned → communicates with customer via `/dispatch/{booking_chat_id}/message` (human chat) → sees job location on map

### Critical Files

| File | Purpose |
|---|---|
| `backend/src/core/main.py` | FastAPI app factory. CORS, router includes, lifespan (PostGIS/pgvector init), alias routes (`/register`, `/signup`, `/login`) |
| `backend/src/core/model.py` | SQLAlchemy ORM schema. All core tables: User, Role, BookingChat, WorkerProfile, WorkerSkill, Job, JobWorkerMatch, etc. |
| `backend/src/core/schema.py` | Pydantic request/response schemas for all routers |
| `backend/src/core/oauth2.py` | JWT creation/verification, `get_current_user` dependency |
| `backend/src/core/router/job_router.py` | Job CRUD, bidding (`/jobs/{id}/bid`), booking (`/jobs/{id}/book`), worker-matched-jobs query |
| `backend/src/core/router/chat_customer.py` | Customer dispatch AI chat, session management, completion pipeline, matching trigger, human message broadcast |
| `backend/src/core/router/chat_worker.py` | Worker interview AI chat, scenario grading, add-skill flow, skill listing |
| `backend/src/core/router/socket.py` | WebSocket endpoints for workers (`/ws/worker/{id}`, `/ws/{id}`) and customers (`/ws/booking/{id}`) |
| `backend/src/core/manager.py` | `ConnectionManager` — global WebSocket connection registry for workers and customers |
| `backend/src/core/matching_manager.py` | Vector search (pgvector cosine distance), LLM reranking (NVIDIA Llama), match creation for both job→worker and worker→job directions |
| `backend/src/core/job_manager.py` | Job CRUD helpers, upsert logic, worker location queries |
| `backend/src/core/worker_profile_helper.py` | Skill upsert helpers (`upsert_baseline_skill`, `upsert_speciality_skill`), profile field sync |
| `backend/src/ai/customer_chat_analyser_nvidia.py` | Customer dispatch AI: system prompt, extraction logic, category matching, embedding calls |
| `backend/src/ai/worker_chat_analyser_nvidia.py` | Worker interview AI: vetting prompt, scenario generation/evaluation, profile extraction, add-skill prompts |
| `backend/src/core/router/worker_onboarding.py` | Worker registration state machine: initialize, submit, admin approve/reject, profile update |
| `frontend/shared/context/AuthContext.jsx` | Global auth state, token management, role detection, login/logout |
| `frontend/shared/api/client.js` | Centralized fetch wrapper with auth headers, error normalization |
| `frontend/shared/config/viewRoutes.js` | Route maps for customer/worker/admin sections and views |
| `frontend/user_app/src/App.jsx` | Root route config, role-based layout routing |
| `frontend/user_app/src/app/AppLayout.jsx` | Dashboard shell: navbar, profile dropdown, worker-applicant check |
| `frontend/user_app/src/components/customer-dashboard/dash1board.jsx` | Customer main dashboard: AI chat, job creation/editing, active posts, map picker |
| `frontend/user_app/src/components/customer-dashboard/dash2board.jsx` | Customer postings dashboard: biddings engine, live map, matched workers, booking modal |
| `frontend/user_app/src/components/worker-dashboard/dash1worker.jsx` | Worker workspace: matched jobs, bidding, job details, chat |
| `frontend/user_app/src/components/worker-dashboard/dash3worker.jsx` | Worker "Me" dashboard: AI interview terminal, extraction/submission, profile, status |

---

## 3. UI/UX & Frontend Polish (The "Minor Changes")

### Visual Consistency
- **Massive inline-style usage:** Almost every card, button, and modal in `dash1board.jsx`, `dash2board.jsx`, `dash1worker.jsx`, `dash3worker.jsx` uses hardcoded inline `style={{}}` objects. This bypasses the CSS variable system in `global.css` and creates visual drift between components that were meant to share the same design tokens.
- **Inconsistent button treatments:** Primary actions use `#FF6B1A` hardcoded inline, while secondary/ghost actions mix `var(--k-line)`, `rgba(245,245,247,0.14)`, and `#333`. The navbar and auth pages use the `ind-` prefixed CSS classes; the dashboard boards do not.
- **Padding/margin inconsistencies:** Dashboard cards use `padding: "16px"`, `"15px"`, `"12px"`, `"24px"` interchangeably. The map modal in `dash1board.jsx` uses `padding: "20px"` while the booking modal in `dash2board.jsx` uses `padding: "24px"`.
- **Typography drift:** Some panels use `fontFamily: "Courier New"` for job titles (`dash1board.jsx:1100`), while the rest of the app uses `"Inter", "Segoe UI", "Roboto"`. This creates a jarring visual disconnect in the active posts list.
- **Color token mismatch:** Several inline styles hardcode `#0D0D0D` for text-on-orange buttons instead of using `var(--ind-ink)` or `var(--k-ink)`. In light mode, `#0D0D0D` is correct, but in dark mode it creates low-contrast orange-on-charcoal text in some places.

### Typography & Copy
- **Mixed casing / shouting:** 
  - `dash1board.jsx:535` — `DEsCRIPTION:` (mixed case, typo)
  - `dash1board.jsx:562` — `AttACHMENTs` (mixed case)
  - `dash1board.jsx:803` — `UsER INFo` (mixed case)
  - `dash1board.jsx:911` — `EmERGENcY ToGGLE` (mixed case)
  - `dash1board.jsx:1005` — `<- Post Job` (arrow prefix inconsistent with other buttons)
- **Awkward button labels:** 
  - `dash1board.jsx:396` — `+ Create Job Manually` (good)
  - `dash1board.jsx:911` — `EmERGENcY ToGGLE` (does nothing, just `console.log`)
  - `dash2board.jsx:390` — `book >` (lowercase, inconsistent with `Book` elsewhere)
  - `dash2board.jsx:209` — `View All bids` (lowercase "bids")
  - `dash1worker.jsx:359` — `I'm Interested` (contraction in UI; fine but inconsistent with `Interested ✓` used elsewhere)
- **Placeholder confusion:** 
  - `dash1board.jsx:440` — `"Instruct AI..."` is ambiguous; better: `"Describe the problem..."` or `"Tell the AI what needs fixing..."`

### Unhandled States
- **No loading skeletons:** While fetching jobs or bids, the UI shows nothing or a raw string like `"Loading…"`. No skeleton cards or shimmer placeholders.
- **Empty states:**
  - `dash1board.jsx:1072` — `"No active pending jobs found in your database instance."` is technically accurate but UX-poor; should be a friendly empty state with an illustration or icon.
  - `dash2board.jsx:317` — `"No bids received yet."` is fine but lacks a CTA or context.
  - Worker matched jobs (`dash1worker.jsx:255`) — `"No matched jobs yet. New opportunities will appear here."` is acceptable.
- **Error boundaries:** `main.jsx` wraps the app in a class-based `ErrorBoundary` that renders a raw stack trace. No user-friendly fallback UI, no "Report issue" CTA.
- **WebSocket disconnection UI:** No visual indicator when the WS connection drops. The chat just silently stops receiving messages.

---

## 4. Code Quality & Bug Hunt

### Dead Code
- **Commented-out router:** `backend/src/core/router/chat_worker.py:948-1009` — Entire commented-out `list_worker_skills` endpoint. Dead code that should be removed.
- **Unused imports:**
  - `backend/src/core/main.py:5` — `from sqlalchemy import text` (used once in lifespan, fine)
  - `backend/src/core/router/job_router.py:9` — `import logging` (used), `import httpx` (used)
  - `backend/src/core/router/chat_customer.py:31` — `import math` (only used in `/validate-vectors` endpoint; fine but that endpoint is debug-only)
- **Legacy `bids` table:** The `bids` table and `BidStatus` enum exist but the active flow uses `JobWorkerMatch.bid_amount`. The `bids` table is dead weight and may confuse future developers.
- **`Service_tasks` model:** Marked with `# needs to work on it` comments. Legacy/unfinished.
- **Console.logs in production code:**
  - `frontend/user_app/src/app/AppLayout.jsx:111,115,119,124` — `console.log("[Join as Worker]...")` 
  - `frontend/user_app/src/components/worker-dashboard/dash1worker.jsx:84` — `console.error("Failed to place bid:", error)`
  - `frontend/shared/api/client.js:107,116,158` — `console.log` and `console.error` on every API request/response. Should use a logger with levels.

### Performance
- **Inline style object recreation:** Every render of `dash1board.jsx`, `dash2board.jsx`, etc. creates thousands of new style objects. This prevents React from memoizing effectively and causes unnecessary re-renders.
- **Map re-initialization:** `dash1board.jsx` and `dash3worker.jsx` both dynamically inject Leaflet CSS/JS and create new map instances on every `isMapOpen` toggle. The cleanup (`map.remove()`) exists but the script/CSS injection is not idempotent (checks `document.getElementById` for CSS but not for script, so multiple toggles could append duplicate script tags).
- **Unnecessary re-renders in chat boxes:** Chat messages are rendered as `.map()` over arrays without `React.memo` or key optimization beyond `msg.id`. When `chatMessages` updates, the entire chat box re-renders.
- **API polling on focus:** `dash2board.jsx:130` — `window.addEventListener('focus', ...)` triggers `fetchPendingJobs()` on every window focus. This is aggressive and could hammer the backend during development.
- **Zustand selector granularity:** Components destructure large objects from Zustand stores (e.g., `useCustomerDashboardData()` returns 30+ fields). Any change to any field causes all consuming components to re-render. No selector memoization.

### State & Socket Leaks
- **WebSocket cleanup is correct but fragile:** `socket.py` properly disconnects on `WebSocketDisconnect`. However, the frontend does not explicitly close WS connections on route unmount in all cases. `dash2board.jsx:176` has `return () => useCustomerDashboardData.getState().disconnectCustomerChat()` — good. But `dash1worker.jsx:136,188` has duplicate `useEffect` cleanup blocks for `disconnectWorkerChat`.
- **Duplicate useEffect blocks:** `dash1worker.jsx:139-170` and `dash1worker.jsx:165-188` are near-identical effects that both connect worker chat and both return cleanup. This means `connectWorkerChat` is called twice on every `activeJob` change, and `disconnectWorkerChat` is called twice on unmount.
- **Zustand store persistence:** No `persist` middleware is used. If the user refreshes, chat state is lost. The auth token is in `localStorage` but dashboard state is ephemeral.

---

## 5. Security & Vulnerability Scan

### Authentication & JWT
- **JWT extraction from token is correct:** `oauth2.py:44-63` properly decodes the JWT and extracts `user_id` from the payload. Routes use `Depends(get_current_user)` which queries the DB for the user — user ID is NOT trusted from client payload.
- **WebSocket auth:** `socket.py:28-31` properly verifies the JWT before accepting the WebSocket connection. The token is passed as a query parameter (`?token=...`), which is acceptable but means it may be logged in proxy/load balancer logs. Consider using a header or initial message.
- **No token refresh mechanism:** JWT expires in 60 minutes (configurable). There is no refresh token flow. Users are silently logged out when the token expires (frontend checks `hasTokenExpired` on boot).
- **Role enforcement:** 
  - `worker_onboarding.py:315` — Admin endpoints check `_is_admin(current_user)` correctly.
  - `user.py:95` — Admin-only user listing checks `_is_admin`.
  - **However:** `user.py:59-81` — `/become-worker` allows ANY authenticated user to self-promote to the Worker role with no approval. This is a business logic flaw: a customer can become a worker instantly, bypassing the entire interview/vetting pipeline.

### Injection Risks
- **SQLAlchemy ORM usage is safe:** All queries use SQLAlchemy ORM or parameterized `select()` statements. No raw SQL concatenation in application code.
- **One raw SQL call:** `database.py:16-19` — `connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))` runs at module import time. This is safe because it's a DDL statement with no user input, but running DB-modifying statements at import time is an anti-pattern.
- **PostGIS geography construction:** `matching_manager.py:57-59` uses `func.ST_SetSRID(func.ST_MakePoint(float(lon), float(lat)), 4326)` — safe, uses SQLAlchemy functions.
- **Category ILIKE escaping:** `matching_manager.py:146-152` properly escapes `%` and `_` in `job_category` before using ILIKE. Good.
- **LLM prompt injection:** The AI prompts (`customer_chat_analyser_nvidia.py`, `worker_chat_analyser_nvidia.py`) do not appear to sanitize user input before injecting it into prompts. A malicious user could craft input that manipulates the LLM's behavior (e.g., extracting system prompts, ignoring instructions). This is low-severity for an internal MVP but should be flagged.

### CORS & Environment
- **CORS is permissive:** `main.py:47-62` allows `localhost:5173`, `5174`, `3000` and `127.0.0.1` variants. `allow_methods=["*"]`, `allow_headers=["*"]`, `expose_headers=["*"]`. For production, this should be locked to the actual deployment origins.
- **No hardcoded secrets in frontend:** `frontend/shared/config/api.js` uses `import.meta.env.VITE_API_URL` — safe.
- **Backend `.env` not committed:** `.env` is in `.gitignore`. `.env.example` exists with placeholder values. Good.
- **Debug prints in production code:** `config.py:7` — `print(f"--- Alembic Debug: ...")` runs on import. Should use `logging.debug()`.

### Business Logic Flaws
- **Worker can accept already-assigned jobs:** `job_router.py:254-299` — `express_interest_in_job` checks if an active `JobWorkerMatch` exists but does NOT check if `job.status` is already `"assigned"` or `"completed"`. A worker could express interest on a job that has already been booked by another worker.
- **No bid amount validation:** `job_router.py:331` — `bid_amount = payload.get("bid_amount")` with no minimum/maximum validation. A worker could bid `0` or a negative number, or an unreasonably large number.
- **No duplicate bid prevention:** A worker can call `/jobs/{id}/bid` multiple times, overwriting their own bid. This may be intentional (update bid) but lacks any confirmation or audit trail.
- **Customer can book without payment:** `job_router.py:390-491` — `/jobs/{id}/book` assigns the worker and sets `job.status = "assigned"` with no payment verification. The button says "Proceed to Payment Opt" (`dash2board.jsx:1208`) but the actual endpoint does not process payment. This is likely a placeholder, but the system treats the job as fully assigned without any money changing hands.
- **Self-booking:** A worker could potentially book themselves if they have both a worker profile and a customer account, but the route checks `job.customer_id != current_user.id` for the customer side and requires an active match for the worker side, so direct self-booking is blocked.
- **Race condition in match creation:** `matching_manager.py:336-428` — `create_matches_for_job` does not use DB-level locks. If two matching runs happen concurrently (e.g., two customers posting similar jobs), duplicate or inconsistent `JobWorkerMatch` records could be created.

---

## 6. Actionable Suggestions & Roadmap

### High Priority (Fix Before Deployment)

| # | Issue | Location | Recommendation |
|---|---|---|---|
| 1 | **Self-promotion to worker bypasses vetting** | `backend/src/core/router/user.py:59-81` | Remove or restrict `/become-worker`. If self-signup is needed, require admin approval or at least redirect to the onboarding flow. |
| 2 | **No payment processing** | `job_router.py:390-491`, `dash2board.jsx:1208` | Either implement payment gateway integration or clearly mark the flow as "demo/book without payment" and prevent the customer from seeing the worker's contact details until payment is confirmed. |
| 3 | **Worker can express interest on assigned jobs** | `job_router.py:254-299` | Add `job.status != "assigned"` and `job.status != "completed"` guard to `express_interest_in_job`. |
| 4 | **Aggressive API polling on window focus** | `dash2board.jsx:130-133` | Replace with WebSocket-based live updates or debounce the focus handler to at most once per 30 seconds. |
| 5 | **Duplicate useEffect blocks in worker dashboard** | `dash1worker.jsx:139-170, 165-188` | Merge into a single `useEffect` with proper cleanup. |
| 6 | **CORS too permissive for production** | `main.py:47-62` | Lock `allow_origins` to actual production domains. Remove wildcard methods/headers if possible. |
| 7 | **No refresh token flow** | `oauth2.py`, `AuthContext.jsx` | Implement refresh tokens or at least a "session expiring soon" warning with a graceful re-login flow. |
| 8 | **LLM prompt injection surface** | `customer_chat_analyser_nvidia.py`, `worker_chat_analyser_nvidia.py` | Sanitize or delimit user input before injecting into LLM prompts. Use system/user message separation strictly. |

### Medium Priority (Polish Before Presentation)

| # | Issue | Location | Recommendation |
|---|---|---|---|
| 9 | **Massive inline-style debt** | All `dash*board.jsx` files | Extract shared styles into CSS modules or styled-components. Use the existing CSS variables (`--k-orange-ink`, `--k-raise`, etc.) instead of hardcoded hex values. |
| 10 | **Mixed casing in UI labels** | `dash1board.jsx` | Fix `DEsCRIPTION`, `AttACHMENTs`, `EmERGENcY ToGGLE` → proper title case. |
| 11 | **No loading skeletons** | All dashboard boards | Add skeleton placeholders for jobs, bids, and worker cards during data fetches. |
| 12 | **Console.logs in production** | `AppLayout.jsx`, `client.js`, `dash1worker.jsx` | Replace with a leveled logger (`loglevel` or similar) that can be silenced in production builds. |
| 13 | **Dead commented-out code** | `chat_worker.py:948-1009` | Remove the commented-out `list_worker_skills` endpoint. |
| 14 | **Legacy `bids` table** | `model.py:96-113` | Drop or archive the `bids` table. All active bidding uses `JobWorkerMatch.bid_amount`. |
| 15 | **Map script injection not idempotent** | `dash1board.jsx:151-158`, `dash3worker.jsx:168-175` | Check if the Leaflet script element already exists in DOM before appending. |
| 16 | **Zustand store selector granularity** | All `use*DashboardData` hooks | Use `useStore` with selectors (e.g., `useCustomerDashboardData(state => state.chatMessages)`) to prevent unnecessary re-renders. |

### Low Priority (Technical Debt)

| # | Issue | Location | Recommendation |
|---|---|---|---|
| 17 | **Database extension creation at import time** | `database.py:16-19` | Move `CREATE EXTENSION` calls into the FastAPI lifespan (they already exist in `main.py:31-36` — the `database.py` block is redundant and should be removed). |
| 18 | **Debug print in config** | `configuration/config.py:7` | Replace `print` with `logging.getLogger(__name__).debug(...)`. |
| 19 | **No TypeScript / strict prop types** | All frontend components | Consider migrating critical shared components to TypeScript or at least adding `PropTypes`. |
| 20 | **No error boundary per route** | `main.jsx` | Split the single `ErrorBoundary` into route-level boundaries so one failing dashboard doesn't crash the entire app. |
| 21 | **Worker profile `worker_chat_id` uniqueness** | `model.py:168` | `worker_chat_id` is unique, but a user can have multiple `WorkerProfile` rows (one per trade). Ensure the UI and API handle this correctly when a user switches between trades. |
| 22 | **Missing rate limiting** | All routers | Add rate limiting (e.g., `slowapi`) to AI chat endpoints to prevent abuse of expensive LLM calls. |
| 23 | **No input length validation on chat messages** | `chat_customer.py`, `chat_worker.py` | Pydantic schemas enforce `max_length=2000`, but the frontend should also enforce this to avoid unnecessary API calls. |
| 24 | **Hardcoded Nominatim User-Agent** | `job_router.py:22`, `chat_customer.py:192`, `chat_worker.py:284` | `"WorkerVerificationApp/1.0 (contact: admin@yourdomain.com)"` uses a placeholder domain. Update to a real contact or use a dedicated geocoding service with an API key. |

---

## Appendix: Architecture Diagram (Textual)

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Customer   │     │   Worker    │     │     Admin        │
│  Frontend   │     │  Frontend   │     │   Frontend       │
│  (Vite 5173)│     │ (Vite 5174)│     │  (same/dual)     │
└──────┬──────┘     └──────┬──────┘     └────────┬─────────┘
       │                    │                     │
       └────────────────────┼─────────────────────┘
                            │
                     ┌──────▼──────┐
                     │   FastAPI   │
                     │  Backend    │
                     │  (8000)     │
                     └──────┬──────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
      ┌─────▼─────┐  ┌──────▼──────┐  ┌────▼─────┐
      │ PostgreSQL│  │ NVIDIA NIM  │  │ WebSocket│
      │ + PostGIS │  │  Llama 3.1  │  │  Manager │
      │ + pgvector│  │  Embeddings │  │ (live WS)│
      └───────────┘  └─────────────┘  └──────────┘
```

**End of Report**
