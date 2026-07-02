# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

**Authoritative project context**: read `litinkai-documentations/CONTEXT.md` first — that file is the source of truth; this AGENTS.md is a quick-load summary + per-folder conventions.

## Overview

LitInkAI is an AI-powered book processing and interactive trailer/video generation platform. Books are uploaded, processed into scripts, then audio/images/video are generated asynchronously via Celery tasks.

**Stack:** FastAPI · React/Vite/TypeScript · PostgreSQL · Redis · RabbitMQ · Celery · MinIO · Traefik

---

## Development Commands

### Backend (Docker — always use `make` from `backend/`)

```bash
cd backend
make dev                          # Start all containers (no debugger)
make debug                        # Start with debugpy on port 5678
make down                         # Stop mac-dev containers
make logs                         # Tail API logs
make logs-all                     # Tail all service logs
make migrate                      # Run alembic upgrade head
make makemigrations name="desc"   # Generate new migration
make psql                         # Open psql shell in postgres container
make rebuild-dev                  # Force rebuild without cache
```

All containers run under the `-p mac-dev` project name. Never run raw `docker compose` — use `make` to avoid project-name conflicts with VPS tunnel containers.

### Frontend (local, outside Docker)

```bash
npm --prefix frontend install
make frontend        # Vite dev server at http://localhost:5173
make frontend-down   # Stop Vite listeners on 5173/5174 before restarting
npm --prefix frontend run build
npm --prefix frontend run lint
```

### Running tests

```bash
# Backend — from inside the repo root or backend/
cd backend && pytest
# Single test file:
pytest tests/test_subscription_tiers.py
# Single test:
pytest tests/test_subscription_tiers.py::TestSubscriptionTierConfig::test_tier_prices_ascending
```

### Stripe webhook forwarding (required for subscription testing)

```bash
make stripe-listen
# Copy the whsec_... secret into backend/.envs/.env.local as STRIPE_WEBHOOK_SECRET
```

---

## Architecture

### Backend — `backend/app/`

- **`main.py`** — FastAPI entry point; mounts `/uploads`, registers `api_router`, runs startup health checks for DB/Celery/Redis.
- **`core/`** — config (env resolution), database (async SQLAlchemy engine), security (JWT), logging, emails.
- **`api/routes/`** — one sub-package per feature (auth, books, chapters, characters, plots, subscriptions, merge, image-generations, projects, credits, audiobooks, trailers, …). All collected via `api/routes/__init__.py` under the `/api/v1` prefix.
- **`api/services/`** — service layer used by routes: `subscription.py` (SubscriptionManager with TIER_LIMITS), `video.py`, `plot.py`, etc.
- **`tasks/`** — Celery task modules: `image_tasks.py`, `audio_tasks.py`, `video_tasks.py`, `merge_tasks.py`, `lipsync_tasks.py`, `plot_tasks.py`, `ai_tasks.py`, `embedding_tasks.py`, `credit_tasks.py`. Celery app configured in `tasks/celery_app.py`.
- **`videos/`** — `VideoGeneration`, `AudioGeneration`, `ImageGeneration` models + `association_integrity.py` (shot ID parsing).
- **`credits/`** — `CreditService` (reserve → confirm/release pattern), `CreditTransaction`, `CreditGrant` via promo module, `constants.py` (per-operation costs).
- **`subscriptions/`** — `UserSubscription` model, Stripe webhook handler.
- **`promo/`** — `CreditGrant` model (grants with expiry), promo code redemption. Credits live here; `CreditService` reads `CreditGrant`.
- **`auth/`** — `User` model, JWT cookie-based auth, roles: `author`, `explorer`, `creator`, `superadmin`.

### Frontend — `frontend/src/`

- **`lib/api.ts`** — base `apiClient` (cookie-based auth, auto token refresh, 402 → insufficient-credits event dispatch). API base: `http://localhost:8000/api/v1` in dev, `https://api.litinkai.com/api/v1` in prod.
- **`contexts/`** — `AuthContext` (user/login/logout/roles), `VideoGenerationContext`, `StoryboardContext`, `ScriptSelectionContext`, `ThemeContext`.
- **`hooks/useVideoGenerationStatus.ts`** — polling hook; returns `startPolling/stopPolling/isComplete/isFailed/progress`.
- **`services/videoGenerationPolling.ts`** — 2–5s polling intervals.
- **`pages/ProjectView.tsx`** — main workspace; use `useVideoGenerationStatus` directly for full control (not `VideoGenerationContext`).

### Async task pipeline (video generation)

1. API route triggers Celery task → returns `video_generation_id`
2. `video_tasks.py` drives status transitions: `PENDING → GENERATING_AUDIO → GENERATING_IMAGES → GENERATING_VIDEO → MERGING_AUDIO → APPLYING_LIPSYNC → COMBINING → COMPLETED`
3. Frontend polls status via `useVideoGenerationStatus`
4. Credits are reserved before the task and confirmed/released on completion/failure

### Credit system

Effective balance = `CreditGrant.credits_remaining` (sum across non-expired grants) minus pending `CreditTransaction` reservations.
Flow: `reserve_credits()` → do work → `confirm_deduction()` or `release_reservation()`.
A Celery Beat job (`credit_tasks`) releases zombie reservations every 10 min and reconciles failures every 15 min.

---

## Critical Pitfalls

### SQLModel field naming
- `metadata` is reserved by SQLAlchemy — never use it as a field name.
- `ImageGeneration` uses `meta` (JSONB). `AudioGeneration` uses `audio_metadata`. `VideoGeneration` uses `task_meta`.

### PostgreSQL enums (case sensitivity)
- All `pg.ENUM()` columns must include `values_callable=lambda e: [m.value for m in e]` to store lowercase values.
- Never manually `UPDATE` `subscription_tier` or `subscription_status` in the DB — always use the Stripe checkout flow to avoid case mismatches.

### Raw SQL in video_tasks.py
- Uses `text()` — column names must exactly match DB schema (not ORM aliases).
- `task_meta` not `task_metadata`; `error_message` is a real column.

### ORM object access
- SQLModel query results are ORM objects — use dot notation (`script.id`, `script.script_style`), not dict access.

### Environment files
- Docker containers use `.envs/.env.docker` (service-name hosts: `postgres`, `redis`, `minio`).
- Native/Mac dev uses `.envs/.env.local` (localhost ports).
- Override via `ENV_FILE=./path` or `APP_ENV=<name>` env vars.

---

## Branch & Commit Conventions

Branch flow: `feat/* → dev_branch → staging → main`

- Feature branches always start from `dev_branch`
- `main` requires Ade + CQO approval — never force-push

Commit format: `<type>(KAN-XXX): <description>`
Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `style`, `ci`

---

## Service URLs (local dev)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/api/v1/docs |
| MinIO Console | http://localhost:9001 (minioadmin/minioadmin) |
| Mailpit | http://localhost:8025 |
| Flower | http://localhost:5555 |
| RabbitMQ | http://localhost:15672 |

---

## Test user credentials (mac-dev) — REUSE existing accounts, do NOT register fresh unless testing registration

**Current status (2026-06-13):** Database was reset on this date. **No active test users exist.** Future Codex sessions should reuse credentials below as they are created, or register new ones following the guidelines below.

### Quick start: Register a test user on Mac dev

When you need an account for testing:

1. **Check if users already exist:** Query the database:
   ```bash
   docker compose -p mac-dev exec -T postgres psql -U adesegun -d litinkai -c \
     "SELECT email, is_active, created_at FROM \"user\" ORDER BY created_at DESC LIMIT 10;"
   ```
   If any rows have `is_active = true`, use one of those (credentials below).

2. **If no active users exist, register a new one** via the API:
   ```bash
   curl -sS -X POST http://localhost:8000/api/v1/auth/register \
     -H 'Content-Type: application/json' \
     -d '{"email":"<your-test-email>@litinkai.test","password":"Test1234!"}'
   ```
   Expected: `201` with user payload including `is_active: false` (activation pending).

3. **Bypass activation email** (mac-dev email pipeline is broken per KAN-367):
   ```bash
   # Get the user ID from the registration response or:
   docker compose -p mac-dev exec -T postgres psql -U adesegun -d litinkai -c \
     "SELECT id, email FROM \"user\" WHERE email='<email>' LIMIT 1;"

   # Activate directly in DB:
   docker compose -p mac-dev exec -T postgres psql -U adesegun -d litinkai -c \
     "UPDATE \"user\" SET is_active=true WHERE email='<email>';"
   ```

4. **Log in at http://localhost:5173** with your email + `Test1234!`

5. **Document the credential** below (append a row to the table).

### Database credentials (for direct access via psql)

| Variable | Value |
|---|---|
| User | `adesegun` |
| Password | `1234` |
| Database | `litinkai` |
| Host (inside Docker) | `postgres` |
| Port | `5432` |

From Mac:
```bash
docker compose -p mac-dev exec -T postgres psql -U adesegun -d litinkai
```

### Test users created — append new rows below

| Email | Password | Active? | Onboarding | Created | Last used | Notes |
|---|---|---|---|---|---|---|
| *(none — database was reset 2026-06-13)* | — | — | — | — | — | — |
| kan367-retest-v3-20260613b@example.com | Test1234! (ends 234!) | Yes | Author/Creator, Writer, Just me, Other, Video+Movies | 2026-06-13 | 2026-06-13 | KAN-367 v3 Mac retest. Username `golden_canvas_4040`. Project "Mobydick" `3ec8d2bd-5269-4227-b956-f50900e995ae`, 137 chapters extracted with B1/B3 FAIL. 299 credits remaining. **Use @example.com — `.litinkai.test` TLD silently drops the activation email in mac-dev SMTP path (HTTP 201 returns but no Mailpit delivery).** |
| tobi-kan393-retest@example.com | Test1234! | Yes | Creator, Writer, Just me, Other, Video creation | 2026-06-23 | 2026-06-23 | KAN-393/398 Mac retest. Username `bright_story_5478`. Created by Tobi via browser registration. Project `62ca2057-213a-499f-a229-64f591dbc35f` (text prompt, no book upload). 298 credits remaining. DB activated manually. |

**How to add a row:** When a Codex session creates a NEW user on mac-dev, append the row + save this file. Single-writer Codex only (Ade approves before merge). Email + last-4 of password OK; never paste full secrets.

### Known issues & workarounds

**Issue: Activation emails never arrive despite API success response**
- **Cause:** Celery email-send task fails silently or SMTP config drift (bug E4 sibling per `litinkai-use` SKILL)
- **Workaround:** Activate users directly via DB (`UPDATE "user" SET is_active=true WHERE email='...'`)
- **Ticket:** KAN-367 (reported 2026-06-12, routed to Tobi for DevOps triage; not yet fixed)

**Issue: `role "adesegun" does not exist` or `database "litinkai" does not exist`**
- **Cause:** Database not fully initialized (Postgres container started but migration not run)
- **Fix:** Wait ~15 seconds after `make dev`, or check `docker compose -p mac-dev logs api` for migration errors
- **If still broken:** Run `make down && docker volume rm mac-dev_litinkai_local_db && make dev` to reset

**Issue: "Your account is not activated" on login with a newly registered user**
- **Expected state:** User registered but `is_active=false` pending email activation
- **Fix:** Use the workaround above (activate via DB)

---

## Augment 2026-06-04 — Operating rules (tier rollout)

### Stack — full canonical line
FastAPI + SQLAlchemy + Alembic + uvicorn + Celery/Redis + Postgres + pgvector + MinIO/R2 + React 18.3 + Vite + TypeScript + Tailwind 3.4 + Zustand. **NOT Django.** If you see "Django" anywhere — including in agent recommendations or stale tickets — flag and correct.

### Branch ownership
- `dev` — owned by **COS** (VPS coding agent)
- `staging` — owned by **PSQ** (VPS QA)
- `main` — owned by **Ade** (sole prod-merge gate); Codex COO + LC approval upstream of that

### Local dev (Mac)
- `make dev` — full stack via Docker Compose (the existing `backend/` Makefile docs above stand)
- `make tunnel-dev`, `make tunnel-staging` — branch-agnostic SSH port-forward to the corresponding VPS worktree
- **Branch rule:** `make vps-staging` requires `git checkout staging` first; `make vps-prod` requires `git checkout main`. Don't bypass.

### Supervisor scope inside this repo
- **Codex + Gemini are READ-ONLY here.** They never modify source. They write recommendations to `litinkai-documentations/supervisor-outputs/<agent>-cycle-YYYY-MM-DD-HHMM.md`.
- **VPS agents** (COS, PSQ, LC) already live on the VPS — no SSH needed from Mac; the **branch is the access**.

### Token leak risk
- Never paste `.env` values into Discord. Reference env var by NAME (`GH_ALL_REPO_PAT`, `STRIPE_WEBHOOK_SECRET`, etc.).
- Use `${ENV_VAR}` shell interpolation in commands.

### Sprint 2 pointer
**Sprint 2 = 8 bug-fix tickets**, paste-ready list at:
`litinkai-documentations/litinkai-knowledge/litinkai plans/master/sprint2-8-bug-fix-list-2026-06-04.md`

These supersede the prior MVP-slice ordering (those tickets demote to Sprint 4). MVP video tab stays incomplete until A1, A4, A7+F2, A6, A5+A20, A16, A10+A11, F1 land.

### GH push policy
**Never `git push` from a Codex session.** Queue push intent at `litinkai-documentations/dispatch-reports/gh-queue.md`, then ping `#tobi-vps-coordination` for Tobi to execute the push.

### Tier system pointer
Global rules: `~/.Codex/AGENTS.md`. Personal/uncommitted overrides: `Codex.local.md` at this repo root (gitignored).
