# KAN-264 staging Mailpit activation QA path

This branch adds an optional Docker Compose override that enables Mailpit for Free-tier account activation QA without touching production/Render settings.

## What it changes

- Adds `docker-compose.mailpit.yml`.
- Adds a `mailpit` service on the existing compose network.
- Configures backend/Celery containers to send mail through SMTP `mailpit:1025` when the override is included.
- Binds the Mailpit UI privately to `127.0.0.1:8025:8025` so it can be reached by local browser, SSH tunnel, or a private proxy only.
- Persists captured messages in the `litink-mailpit-data` Docker volume.

## Start with the current compose stack

From the repo root on the staging/dev host:

```bash
docker compose -f docker-compose.yml -f docker-compose.mailpit.yml up -d mailpit backend celery-worker celery-beat
```

If the host uses the dev port override, include it too:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.mailpit.yml --env-file .env.dev up -d mailpit backend celery-worker celery-beat
```

SMTP is not published on the host. Containers send to:

```text
SMTP_HOST=mailpit
SMTP_PORT=1025
```

## Access Mailpit UI

Local on host:

```text
http://127.0.0.1:8025
```

SSH tunnel from workstation:

```bash
ssh -N -L 8025:127.0.0.1:8025 <staging-user>@<staging-host>
```

Then open `http://127.0.0.1:8025` locally.

## Verify activation resend path

The backend already exposes:

- `POST /api/v1/auth/resend-activation-link`
- `GET /api/v1/auth/activate/{token}`

No account DB mutation or provider rerun is required by this change. For QA, use an existing inactive/free-tier test account or create a normal test signup through the application flow, then request resend:

```bash
curl -sS -X POST \
  "$API_BASE_URL/api/v1/auth/resend-activation-link" \
  -H 'Content-Type: application/json' \
  -d '{"email":"qa-free-tier@example.com"}'
```

Open Mailpit, inspect the activation email, and follow/copy the activation link.

## Guardrails

- Do not include this override in production/Render deployment.
- Do not publish Mailpit SMTP or UI publicly.
- Do not mutate account rows manually; exercise normal signup/resend/activate paths only.
