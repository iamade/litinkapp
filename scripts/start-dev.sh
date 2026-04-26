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

# Check if tunnel is running
if ! pgrep -f "ssh -N.*72.62.97.111.*5433" > /dev/null; then
    echo "❌ ERROR: SSH tunnel not running!"
    echo "Run this FIRST in another terminal:"
    echo "  bash scripts/tunnel-dev.sh"
    exit 1
fi

echo "  ✅ SSH tunnel detected"

# Copy dev env
cp scripts/env.dev backend/.envs/.env.local
echo "  ✅ Using dev env file"

# Start only backend services (not postgres/redis/minio — they're on VPS)
cd backend
docker compose -f local.yml \
    --profile backend-only \
    up --build -d api celery-worker celery-beat

echo ""
echo "✅ Dev is running!"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "To see logs: docker compose -f backend/local.yml logs -f api"
