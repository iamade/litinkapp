#!/bin/bash
# =============================================================================
# Start LitInkAI local backend against VPS dev tunneled services.
# Does NOT overwrite backend/.envs/.env.local.
# =============================================================================
# PREREQUISITE: Run tunnel-dev.sh FIRST in another terminal:
#   bash scripts/tunnel-dev.sh
#
# Env source of truth for tunnel mode:
#   backend/.envs/.env.local.vps-dev
# Override with:
#   ENV_FILE=./.envs/your-file make vps-dev
# =============================================================================

set -e

ENV_FILE=${ENV_FILE:-./.envs/.env.local.vps-dev}
REPO_ENV_FILE="backend/${ENV_FILE#./}"

if [ "$ENV_FILE" = "./.envs/.env.local" ] || [ "$ENV_FILE" = ".envs/.env.local" ]; then
    echo "❌ Refusing to use backend/.envs/.env.local for VPS tunnel mode."
    echo "Use backend/.envs/.env.local.vps-dev so your normal local env is preserved."
    exit 1
fi

echo "Starting LitInkAI VPS dev tunnel backend..."

# Check if tunnel is running (match forwarded dev port; ssh args may appear before the host)
if ! pgrep -f "ssh .*5433:127.0.0.1:5433.*72.62.97.111" > /dev/null; then
    echo "❌ ERROR: SSH tunnel not running!"
    echo "Run this FIRST in another terminal and leave it open:"
    echo "  bash scripts/tunnel-dev.sh"
    exit 1
fi

echo "  ✅ SSH tunnel detected"

if [ ! -f "$REPO_ENV_FILE" ]; then
    echo "❌ Missing VPS dev env file: $REPO_ENV_FILE"
    echo "Create it from scripts/env.vps-dev.example or your confirmed dev env values."
    echo "Do not use backend/.envs/.env.local; that is reserved for normal local dev."
    exit 1
fi

echo "  ✅ Using VPS dev env file: $REPO_ENV_FILE"

# Start API first so it is the only service that runs Alembic migrations.
# Starting api/celeryworker/celerybeat together can race on a fresh DB.
cd backend
ENV_FILE="$ENV_FILE" docker compose -f local.yml \
    up --build -d api

echo "  ⏳ Waiting for API migrations/startup..."
for i in {1..60}; do
    if ENV_FILE="$ENV_FILE" docker compose -f local.yml logs --no-color api 2>/dev/null | grep -Eq "Application startup complete"; then
        echo "  ✅ API started"
        break
    fi

    if ENV_FILE="$ENV_FILE" docker compose -f local.yml logs --no-color api 2>/dev/null | grep -Eq "Traceback|ERROR|FAILED|Error:"; then
        echo "❌ API startup failed. Recent logs:"
        ENV_FILE="$ENV_FILE" docker compose -f local.yml logs --no-color --tail=80 api
        exit 1
    fi

    if [ "$i" -eq 60 ]; then
        echo "❌ API did not finish startup within 120 seconds. Recent logs:"
        ENV_FILE="$ENV_FILE" docker compose -f local.yml logs --no-color --tail=80 api
        exit 1
    fi

    sleep 2
done

# Start workers only after API migration/startup succeeds; workers skip Alembic.
ENV_FILE="$ENV_FILE" docker compose -f local.yml \
    up --build -d celeryworker celerybeat

echo ""
echo "✅ VPS dev backend is running!"
echo "  Frontend: http://localhost:5173 (start separately: make frontend)"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "To see logs: cd backend && ENV_FILE=$ENV_FILE docker compose -f local.yml logs -f api"
