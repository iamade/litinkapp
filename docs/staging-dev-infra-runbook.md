# Staging / VPS Dev Infrastructure Runbook

This runbook documents the expected local/VPS staging services, compose files, environment variables, QA setup evidence, and guardrails used by LitInkAI staging/dev infrastructure. It is intended to prevent setup drift and to make staging recreation auditable.

## Scope and branch discipline

All infrastructure changes that touch tracked repository files must use the normal branch flow:

```text
feature/fix/docs branch -> dev_branch -> staging
```

Do not edit `staging` directly. Do not merge to `main` without Ade approval and LC/CQO signoff. Do not change production/Render configuration as part of staging/VPS work unless a separate approved production ticket explicitly requires it.

Recommended ticket/branch pattern:

```text
KAN-### short description
infra/kan-###-short-description
fix/kan-###-short-description
docs/kan-###-short-description
```

## Required services

A complete local/VPS staging stack needs the following services.

| Service | Purpose | Notes |
| --- | --- | --- |
| Postgres + pgvector | Primary relational database plus vector extension support | Dev/VPS DB should use a pgvector-capable image such as `pgvector/pgvector:pg16` when vector extension creation is required. Do not recreate or replace staging/prod DB containers without approval. |
| Redis | Celery broker/result backend and app cache support | Required before backend/celery startup. |
| MinIO | Canonical internal app media/object storage | Internal service URL should stay private to containers. Do not pass local/private MinIO URLs to external providers. |
| Backend API | FastAPI application | Runs auth, subscription, generation APIs, activation endpoints, and queues async tasks. |
| Celery worker | Async generation/email/task execution | Required for image/video/audio tasks and activation email delivery through `send_email_task`. Restart after email/provider env changes. |
| Celery beat | Periodic tasks | Runs scheduled credit reconciliation/reservation cleanup tasks. |
| Frontend | Vite/React app | Provides login/register/resend activation UI and project QA flows. |
| Mailpit | Staging/dev email capture for activation QA | Use private UI bind only by default: `127.0.0.1:8025`. SMTP is internal as `mailpit:1025`. |
| Provider-readable storage (S3/R2/CDN) | External HTTPS media path for provider inputs | Required for KAN-87/KAN-263 continuity frames. Must produce public/provider-readable HTTPS URLs while keeping canonical/internal URLs separate. |

## Compose file matrix

| File | Role | Use |
| --- | --- | --- |
| `docker-compose.yml` | Main local/VPS compose stack | Base app services. Currently includes backend, celery, frontend, Postgres, Redis, MinIO. |
| `docker-compose.dev.yml` | Dev override | Use only when the host/dev workflow requires dev-specific ports/env. |
| `docker-compose.mailpit.yml` | KAN-264 Mailpit override | Adds Mailpit and points backend/celery email config to `mailpit:1025`; binds UI to `127.0.0.1:8025`. |
| `backend/local.yml` | Legacy/backend-local stack | Contains a Mailpit service but is not the active root compose stack unless explicitly used. Do not assume it is running. |
| `backend/production.yml` | Backend production-oriented compose | Do not use as a staging mutation path unless separately approved. |
| `docker-compose.dev.full.yml` | VPS/dev full-stack compose | Dev-only changes must stay scoped here and must not be mixed into unrelated tickets. |

Common commands:

```bash
# Base staging/dev stack with Mailpit
docker compose -f docker-compose.yml -f docker-compose.mailpit.yml up -d mailpit backend celery-worker celery-beat

# Dev override path
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.mailpit.yml --env-file .env.dev up -d mailpit backend celery-worker celery-beat

# Validate compose without mutating runtime
docker compose -f docker-compose.yml -f docker-compose.mailpit.yml config

docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.mailpit.yml --env-file .env.dev config
```

## Activation email / Mailpit configuration

Activation email is queued by the backend and sent by Celery:

```text
registration/resend API -> send_activation_email(...) -> send_email_task -> SMTP
```

Relevant endpoints:

```text
POST /api/v1/auth/resend-activation-link
GET  /api/v1/auth/activate/{token}
```

Relevant frontend route:

```text
/auth/activate/{token}
```

Required/expected environment variables for staging Mailpit activation QA:

| Variable | Expected staging/dev value | Notes |
| --- | --- | --- |
| `ENVIRONMENT` | non-production, usually `development` | Non-production email config uses SMTP host/port directly. |
| `SMTP_HOST` | `mailpit` | Container DNS name when `docker-compose.mailpit.yml` is included. |
| `SMTP_PORT` | `1025` | Mailpit SMTP port. |
| `MAIL_FROM` | validator-safe sender such as `noreply@litinkai.com` | Avoid invalid local-only sender domains. |
| `MAIL_FROM_NAME` | `Litink AI` | Display sender. |
| `FRONTEND_URL` | PSQ-accessible frontend URL if safe; otherwise current localhost fallback must be documented | If left as localhost, PSQ can extract the token from Mailpit and call the API activation endpoint directly. |
| `API_BASE_URL` | API base used by app/runtime | Useful for generated action URLs and diagnostics. |
| `ACTIVATION_TOKEN_EXPIRATION_MINUTES` | current default may be short | Do not change TTL unless immediate resend+activation fails and Ade/LC approve under a tracked ticket. |

Mailpit access:

```text
SMTP: mailpit:1025 inside compose network
UI:   127.0.0.1:8025 on host only
```

SSH tunnel pattern:

```bash
ssh -N -L 8025:127.0.0.1:8025 <staging-user>@<staging-host>
```

Then open:

```text
http://127.0.0.1:8025
```

Do not publicly expose Mailpit UI or SMTP by default. Public `:8025` exposure requires explicit Ade approval, firewall/IP allowlisting, and time-boxing.

## Provider-readable continuity-frame storage

KAN-87/KAN-263 selected-scoped continuity requires app-generated continuity frames to be available to external providers through a proven HTTPS URL. Canonical/internal media URLs and provider-safe URLs must remain separate.

Relevant concepts:

| Field / concept | Meaning |
| --- | --- |
| `extracted_frame_url` | Canonical/internal extracted last-frame URL. May be local/MinIO and provider-unsafe. |
| `upscaled_frame_url` | Canonical/internal upscaled continuity frame URL. May be local/MinIO and provider-unsafe. |
| `provider_extracted_frame_url` | HTTPS provider-readable extracted frame URL. |
| `provider_upscaled_frame_url` | HTTPS provider-readable upscaled frame URL. |
| `continuity_frame_provider_url` | Provider-bound continuity frame URL used for suggested-shot generation. |
| `provider_persisted_*` | Audit fields for direct provider-readable persistence/copy path. |

Required env vars for direct S3-compatible provider-readable persistence:

| Variable | Requirement |
| --- | --- |
| `S3_ACCESS_KEY` | Required if using S3-compatible provider persistence. |
| `S3_SECRET_KEY` | Required if using S3-compatible provider persistence. |
| `S3_BUCKET_NAME` | Required bucket/container name. |
| `S3_ENDPOINT` or `S3_REGION` | Required destination configuration. |
| Provider public URL behavior | Returned object URL must be HTTPS and publicly/provider-readable. |

Other media variables to audit carefully:

| Variable | Notes |
| --- | --- |
| `MINIO_ENDPOINT` | Internal container endpoint, e.g. `http://minio:9000`. Safe for internal downloads only. |
| `MINIO_PUBLIC_URL` | Canonical app/public URL; may be localhost in staging/dev and must not be sent to external providers. |
| `MINIO_PROVIDER_PUBLIC_URL` | Only set if it is a proven HTTPS provider-readable base for the actual object paths. |
| `MODELSLAB_MEDIA_PUBLIC_URL` | Must not be raw HTTP/IP/private. Provider guard should reject unsafe values. |

Guardrails:

- Do not pass `localhost`, `minio`, private IPs, raw HTTP/IP media URLs, or local MinIO URLs to ModelsLab/upscale/provider paths.
- Do not globally rewrite `/litink-dev/...` paths to an R2 `/generations/...` host unless that exact path shape is proven fetchable; previous probes showed provider-owned `/generations/...` can work while app `/litink-dev/...` paths 404.
- If provider-readable persistence is unavailable, fail closed before provider spend.

## Fresh Free-tier QA setup checklist

Use this process when PSQ needs clean Free-tier evidence.

1. Create a new QA account through normal app/API registration.
2. Before activation, capture DB snapshots:
   - `user`: id, email, display name, `is_active`, `account_status`, activation-token presence/expiry, created/updated timestamps, roles.
   - `user_subscriptions`: confirm 0 rows and no Stripe IDs.
   - `credit_grants`: confirm exactly the default `free_tier` grant unless Ade explicitly approves promo redemption.
   - `credit_transactions`: capture zero/baseline state.
3. Use the normal resend path if needed:

```bash
curl -sS -X POST \
  "$API_BASE_URL/api/v1/auth/resend-activation-link" \
  -H 'Content-Type: application/json' \
  -d '{"email":"qa-free-tier@example.com"}'
```

4. Open Mailpit through the private tunnel and verify:
   - recipient is the QA email;
   - subject is activation-related, e.g. `Activate your Account`;
   - activation URL/token is present.
5. Activate through the frontend link if `FRONTEND_URL` is PSQ-accessible. If it remains localhost, extract the token and call:

```bash
curl -sS "$API_BASE_URL/api/v1/auth/activate/<token>"
```

6. After activation, capture DB snapshots:
   - `user.is_active=true`;
   - `account_status=active`;
   - activation token fields cleared;
   - `user_subscriptions=0`;
   - no Stripe IDs;
   - `free_tier` grant unchanged until QA spend begins.
7. During QA, capture credit transaction before/after evidence for generated assets. Credit-based behavior is the desired control path; do not use old monthly-rate-limit assumptions as Free-tier evidence.

## Do not mutate without explicit approval

Do not mutate any of the following without an explicit tracked approval from Ade/LC:

- staging/prod secrets;
- Render/prod config;
- production databases or production compose/runtime files;
- user-local env files such as developer `.env.local` files;
- account subscription tiers or `user_subscriptions` rows;
- Stripe IDs or subscription history rows;
- credit grants/transactions except through normal app flows;
- activation state by direct DB update;
- provider media URL guards or fail-closed behavior;
- global MinIO/R2/CDN rewrite settings.

Manual DB corrections, if ever approved, must be labeled as QA-enablement or data repair, must include before/after evidence, and must not be represented as normal app behavior.

## Useful evidence artifacts

For infra/setup changes, preserve logs under a ticket-specific artifact directory, for example:

```text
artifacts/kan-264/compose_config_<timestamp>.log
artifacts/kan-264/deploy_staging_<timestamp>.log
artifacts/kan-264/free_account_resend_activation_<timestamp>.log
artifacts/kan-264/activation_<timestamp>.log
```

For KAN-87/KAN-263 provider-readiness probes, preserve:

```text
artifacts/kan-263/env_probe_<commit>_<timestamp>.log
artifacts/kan-263/no_provider_readiness_probe_<commit>_<timestamp>.log
```

Evidence should show exact branch/head, service start times, selected env values with secrets redacted, endpoint responses, DB before/after state, and whether any provider spend occurred.
