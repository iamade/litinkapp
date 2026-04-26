# LitInkAI

AI-powered book processing and interactive trailer generation platform.

**Stack:** FastAPI · React/Vite · PostgreSQL · Redis · RabbitMQ · Celery · MinIO · Traefik

---

## Table of Contents

- [First-Time Setup](#first-time-setup)
- [Branch Workflow](#branch-workflow)
- [Docker Services](#docker-services)
- [Service URLs](#service-urls)
- [Environment Configuration](#environment-configuration)
- [Makefile Commands](#makefile-commands)
- [Frontend (Local Dev)](#frontend-local-dev)
- [Stripe Dev Subscription Upgrade Guide](#stripe-dev-subscription-upgrade-guide)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Conventional Commits](#conventional-commits)

---

## First-Time Setup

Follow these steps from a clean clone to a running dev environment.

### 1. Clone & switch to dev branch

```bash
git clone https://github.com/iamade/litinkapp.git
cd litinkapp
git checkout dev_branch
```

### 2. Create the Docker network

The compose stack expects an external network named `litinkai_local_nw`.

```bash
docker network create litinkai_local_nw
```

### 3. Configure backend environment

```bash
cd backend/.envs
cp .env.example .env.local
```

Edit `backend/.envs/.env.local` and fill in the required values (see [Environment Configuration](#environment-configuration)).

### 4. Configure frontend environment

```bash
cd frontend
cp .env.example .env
```

Edit `frontend/.env` and set `VITE_API_URL=http://localhost:8000` (and any frontend API keys).

### 5. Start backend services

```bash
cd backend
make dev
```

This builds and starts all Docker containers (PostgreSQL, Redis, RabbitMQ, MinIO, Mailpit, Traefik, API, Celery worker/beat, Flower). Wait until `make logs` shows the API is ready.

### 6. Run database migrations

```bash
cd backend
make migrate
```

### 7. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs **locally** (not in Docker) during development.

### 8. Verify everything is running

Open these URLs in your browser:

| Service        | URL                              |
|----------------|----------------------------------|
| Frontend       | <http://localhost:5173>          |
| Backend API    | <http://localhost:8000>           |
| API Docs       | <http://localhost:8000/docs>      |
| MinIO Console  | <http://localhost:9001>           |
| Mailpit        | <http://localhost:8025>           |
| Flower         | <http://localhost:5555>           |
| Traefik        | <http://localhost:8080>          |
| RabbitMQ       | <http://localhost:15672>         |

You're ready to develop. 🎉

---

## Branch Workflow

```
feat/* → dev_branch → staging → main
```

| Branch         | Purpose                                       |
|----------------|-----------------------------------------------|
| `feat/*`       | Feature branches — always created from `dev_branch` |
| `dev_branch`   | Active development integration                 |
| `staging`      | QA testing (requires PR)                       |
| `main`         | Production — requires Ade + CQO approval        |

**Rules:**

- Never commit directly to `main` or `dev_branch`
- Create feature branches from `dev_branch`: `git checkout -b feat/KAN-XXX-description dev_branch`
- Merge to `staging` for QA testing
- Merge `staging` → `main` requires **both** Ade approval **and** CQO sign-off

---

## Docker Services

The backend runs via Docker Compose (`backend/local.yml`). All services run on the `litinkai_local_nw` network.

| Service         | Description                                    |
|-----------------|------------------------------------------------|
| **postgres**    | PostgreSQL (custom Dockerfile in `docker/local/postgres/`) |
| **redis**       | Redis 7 — Celery broker & result backend        |
| **rabbitmq**    | RabbitMQ with management plugin                 |
| **minio**       | S3-compatible object storage                    |
| **mailpit**     | SMTP sink + web UI for email testing            |
| **traefik**     | Reverse proxy / router                          |
| **api**         | FastAPI application (custom Dockerfile in `docker/local/fastapi/`) |
| **celeryworker**| Celery task worker                              |
| **celerybeat**  | Celery periodic task scheduler                  |
| **flower**      | Celery monitoring dashboard                     |

---

## Service URLs

| Service        | Port  | URL                              |
|----------------|-------|----------------------------------|
| Frontend       | 5173  | <http://localhost:5173>          |
| Backend API    | 8000  | <http://localhost:8000>           |
| API Docs       | 8000  | <http://localhost:8000/docs>      |
| MinIO Console  | 9001  | <http://localhost:9001>           |
| Mailpit        | 8025  | <http://localhost:8025>           |
| Flower         | 5555  | <http://localhost:5555>           |
| Traefik        | 8080  | <http://localhost:8080>          |
| RabbitMQ       | 15672 | <http://localhost:15672>         |

> **MinIO credentials:** `minioadmin` / `minioadmin` (dev only)

---

## Environment Configuration

### Backend — `backend/.envs/.env.local`

Copy from the example and edit:

```bash
cp backend/.envs/.env.example backend/.envs/.env.local
```

**Required env vars:**

| Variable              | Description                      |
|-----------------------|----------------------------------|
| `DATABASE_URL`        | PostgreSQL async connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL`           | Redis connection string           |
| `OPENAI_API_KEY`      | OpenAI API key                   |
| `JWT_SECRET_KEY`      | JWT signing secret               |
| `SIGNING_KEY`         | Token signing key                |
| `POSTGRES_USER`       | PostgreSQL username              |
| `POSTGRES_PASSWORD`   | PostgreSQL password              |
| `POSTGRES_DB`         | PostgreSQL database name          |
| `POSTGRES_HOST`       | PostgreSQL host (`postgres` inside Docker) |
| `POSTGRES_PORT`       | PostgreSQL port (`5432`)         |
| `CELERY_BROKER_URL`   | Celery broker URL                |
| `CELERY_RESULT_BACKEND`| Celery result backend            |

### Frontend — `frontend/.env`

Copy from the example and edit:

```bash
cp frontend/.env.example frontend/.env
```

**Key env vars:**

| Variable                        | Description                |
|---------------------------------|----------------------------|
| `VITE_API_URL`                  | Backend API URL (`http://localhost:8000`) |
| `VITE_OPENAI_API_KEY`           | OpenAI API key (frontend)   |
| `VITE_STRIPE_PUBLISHABLE_KEY`   | Stripe publishable key      |

---

## Makefile Commands

All backend Docker operations use `make` targets from `backend/Makefile`. **Do not run raw `docker compose` commands** — use the Makefile instead.

```bash
cd backend
```

| Command                        | Description                                        |
|--------------------------------|----------------------------------------------------|
| `make dev`                     | Start in dev mode (no debugger)                    |
| `make debug`                   | Start in dev mode **with** debugger (port 5678)    |
| `make down`                    | Stop all application containers                     |
| `make logs`                    | Follow API logs                                    |
| `make logs-all`                | Follow all service logs                             |
| `make migrate`                 | Run Alembic migrations (`alembic upgrade head`)    |
| `make makemigrations name="desc"` | Create a new auto-generated migration           |
| `make rebuild-dev`             | Rebuild dev images without cache                    |
| `make psql`                    | Open a psql shell in the Postgres container         |

> Run `make help` inside `backend/` to see all available targets.

---

## Frontend (Local Dev)

The frontend runs **outside Docker** for development:

```bash
cd frontend
npm install
npm run dev          # Vite dev server on :5173
npm run build        # Production build
npm run lint         # ESLint
```

The frontend proxies API requests to the backend via `VITE_API_URL` (set in `frontend/.env`).

---

## Stripe Dev Subscription Upgrade Guide

Use this guide to test subscription upgrades locally via Stripe test mode. **Do not manually edit `subscription_tier` in the database** — always use the Stripe checkout flow to avoid enum case mismatches.

### 1. Start the Stripe CLI listener

Before testing subscriptions, start the Stripe CLI to forward webhook events to your local backend:

```bash
stripe listen --forward-to localhost:8000/api/subscriptions/webhook
```

This prints a `whsec_...` webhook signing secret. Set it in your `backend/.envs/.env.local`:

```
STRIPE_WEBHOOK_SECRET=whsec_<from-stripe-listen-output>
```

Restart the backend after updating the env var.

### 2. Configure Stripe Price IDs

Ensure the following Stripe Price IDs are set in `backend/.envs/.env.local`:

| Env Var | Tier | Required |
|---------|------|----------|
| `STRIPE_FREE_PRICE_ID` | Free | No (default tier) |
| `STRIPE_BASIC_PRICE_ID` | Basic | Yes |
| `STRIPE_STANDARD_PRICE_ID` | Standard | Yes |
| `STRIPE_PREMIUM_PRICE_ID` | Premium | Yes |
| `STRIPE_PROFESSIONAL_PRICE_ID` | Professional | Yes |
| `STRIPE_ENTERPRISE_PRICE_ID` | Enterprise | Yes |
| `STRIPE_PRO_PRICE_ID` | Pro (legacy) | No |

Create Price IDs in the [Stripe Dashboard](https://dashboard.stripe.com/test/products) under **Test Mode**.

### 3. Trigger a subscription upgrade

Use the checkout API endpoint:

```bash
curl -X POST http://localhost:8000/api/subscriptions/checkout \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "professional",
    "success_url": "http://localhost:5173/settings?upgrade=success",
    "cancel_url": "http://localhost:5173/settings?upgrade=cancelled"
  }'
```

This returns a `checkout_url`. Open it in a browser.

### 4. Complete payment with test cards

Use these Stripe test card numbers (any future expiry, any CVC, any postal code):

| Card Number | Result |
|------------|--------|
| `4242 4242 4242 4242` | ✅ Succeeds |
| `4000 0025 0000 3155` | Requires 3DS authentication |
| `4000 0000 0000 9995` | ❌ Declines |

After payment, Stripe sends a `checkout.session.completed` webhook to your local backend, which activates the subscription in the database.

### 5. Verify the subscription

Check the user's subscription status via API or directly in the database:

```sql
SELECT tier, status FROM user_subscriptions WHERE user_id = '<your-user-uuid>' AND status = 'active';
```

Expected: `tier = 'professional'`, `status = 'active'` (lowercase values per KAN-244 enum normalization).

### Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Webhook not received | Stripe CLI not running | Start `stripe listen` before testing |
| `Invalid webhook signature` | `STRIPE_WEBHOOK_SECRET` mismatch | Copy `whsec_...` from `stripe listen` output |
| Subscription stays inactive | Webhook handler error | Check backend logs for webhook processing errors |
| `enum case mismatch` | Manual DB edit inserted uppercase values | Never edit `subscription_tier`/`subscription_status` directly — use Stripe checkout only |

---

## Testing

### Backend

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm test
```

---

## Project Structure

```
litinkapp/
├── backend/
│   ├── .envs/                    # Environment files (.env.example → .env.local)
│   ├── app/
│   │   ├── main.py               # FastAPI application entry point
│   │   ├── core/                 # Config, security, database, emails
│   │   ├── admin/                # Admin panel routes
│   │   ├── api/                  # API routes & services
│   │   ├── ai/                   # AI integration (OpenAI, etc.)
│   │   ├── auth/                 # Authentication & JWT
│   │   ├── audio/                # Audio generation
│   │   ├── audiobooks/           # Audiobook service
│   │   ├── badges/               # Badge system
│   │   ├── books/                # Book models, upload, processing
│   │   ├── credits/              # Credit system
│   │   ├── images/               # Image generation
│   │   ├── logs/                 # Application logging
│   │   ├── merges/               # Merge operations
│   │   ├── nfts/                  # NFT / Algorand integration
│   │   ├── plots/                # Plot generation
│   │   ├── projects/             # Project management
│   │   ├── promo/                # Promotional features
│   │   ├── quizzes/              # Quiz system
│   │   ├── subscriptions/        # Stripe subscriptions
│   │   ├── trailers/             # Trailer generation
│   │   ├── user_profile/         # User profile management
│   │   ├── videos/               # Video generation
│   │   └── tasks/                # Celery async tasks
│   ├── docker/
│   │   ├── local/                # Local Docker configs (Dockerfiles, Traefik)
│   │   └── production/          # Production Docker configs
│   ├── migrations/               # Alembic database migrations
│   ├── scripts/                  # Utility scripts
│   ├── tests/                    # Backend test suite
│   ├── local.yml                 # Docker Compose for local dev
│   ├── Makefile                  # Dev commands (use this!)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/           # React components (Admin, Audio, Dashboard, etc.)
│   │   ├── pages/                # Page-level components
│   │   ├── contexts/             # React context providers
│   │   ├── hooks/                # Custom React hooks
│   │   ├── lib/                  # Utilities, API client
│   │   ├── services/             # Service layer
│   │   ├── types/                # TypeScript type definitions
│   │   ├── utils/                # Utility functions
│   │   ├── App.tsx               # Root app component
│   │   └── main.tsx              # Entry point
│   ├── public/                   # Static assets
│   ├── .env.example              # Frontend env template
│   └── package.json
├── .gitignore
└── README.md                     # ← You are here
```

---

## Conventional Commits

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/) with a KAN ticket prefix.

### Format

```
<type>(<ticket>): <description>
```

### Types

| Type         | Use for                            |
|--------------|------------------------------------|
| `feat`       | New feature                        |
| `fix`        | Bug fix                            |
| `docs`       | Documentation changes              |
| `refactor`   | Code restructuring (no behavior change) |
| `test`       | Adding or updating tests           |
| `chore`      | Build, tooling, or infra changes   |
| `perf`       | Performance improvements           |
| `style`      | Formatting (no logic change)       |
| `ci`         | CI/CD pipeline changes             |

### Examples

```
feat(KAN-149): add trailer scene selection service
fix(KAN-143): prevent cross-script data bleeding in StoryboardContext
docs(KAN-200): consolidate README with unified dev setup
chore(KAN-155): update Makefile with rebuild-dev target
refactor(KAN-160): extract credit deduction into shared service
test(KAN-168): add integration tests for merge operations
```