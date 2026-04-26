#!/bin/bash
# =============================================================================
# Start LitInkAI dev (tunnel mode)
# Connects to VPS dev services via SSH tunnel
# =============================================================================
# PREREQUISITE: Run tunnel-dev.sh FIRST in another terminal:
#   bash scripts/tunnel-dev.sh
# =============================================================================

set -e

echo "Starting LitInkAI dev (tunnel mode)..."

# Check if tunnel is running (match forwarded dev port; ssh args may appear before the host)
if ! pgrep -f "ssh .*5433:127.0.0.1:5433.*72.62.97.111" > /dev/null; then
    echo "❌ ERROR: SSH tunnel not running!"
    echo "Run this FIRST in another terminal and leave it open:"
    echo "  bash scripts/tunnel-dev.sh"
    exit 1
fi

echo "  ✅ SSH tunnel detected"

# Copy dev env
cp scripts/env.dev backend/.envs/.env.local
echo "  ✅ Using dev env file"

# Start API first so it is the only service that runs Alembic migrations.
# Starting api/celeryworker/celerybeat together can race on a fresh DB.
cd backend
docker compose -f local.yml \
    up --build -d api

echo "  ⏳ Waiting for API migrations/startup..."
for i in {1..60}; do
    if docker compose -f local.yml logs --no-color api 2>/dev/null | grep -Eq "Application startup complete|Uvicorn running"; then
        echo "  ✅ API started"
        break
    fi

    if docker compose -f local.yml logs --no-color api 2>/dev/null | grep -Eq "Traceback|ERROR|FAILED|Error:"; then
        echo "❌ API startup failed. Recent logs:"
        docker compose -f local.yml logs --no-color --tail=80 api
        exit 1
    fi

    if [ "$i" -eq 60 ]; then
        echo "❌ API did not finish startup within 120 seconds. Recent logs:"
        docker compose -f local.yml logs --no-color --tail=80 api
        exit 1
    fi

    sleep 2
done

# Start workers only after API migration/startup succeeds; workers skip Alembic.
docker compose -f local.yml \
    up --build -d celeryworker celerybeat

echo ""
echo "✅ Dev is running!"
echo "  Frontend: http://localhost:5173 (start separately: make frontend)"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "To see logs: docker compose -f backend/local.yml logs -f api"
