#!/bin/bash
# =============================================================================
# Start LitInkAI local backend against VPS dev tunneled services.
# PREREQUISITE: Run in another terminal and leave open:
#   make tunnel-dev
# Uses canonical env: backend/.envs/.env.vps-dev
# =============================================================================
set -euo pipefail

ENV_FILE=${ENV_FILE:-./.envs/.env.vps-dev}
REPO_ENV_FILE="backend/${ENV_FILE#./}"

if [ "$ENV_FILE" = "./.envs/.env.local" ] || [ "$ENV_FILE" = ".envs/.env.local" ]; then
  echo "❌ Refusing to use backend/.envs/.env.local for VPS tunnel mode."
  echo "Use backend/.envs/.env.vps-dev for VPS dev."
  exit 1
fi

echo "Starting LitInkAI VPS dev tunnel backend..."
if ! pgrep -f "ssh .*5433:127.0.0.1:5433.*72.62.97.111" > /dev/null; then
  echo "❌ ERROR: SSH dev tunnel not running. Run: make tunnel-dev"
  exit 1
fi
[ -f "$REPO_ENV_FILE" ] || { echo "❌ Missing env file: $REPO_ENV_FILE"; exit 1; }
# db-url-routing-fix 2026-05-21 (Change 2): no longer copy the tunnel env over
# backend/.envs/.env.local. local.yml reads ${ENV_FILE} directly and config.py
# now honours ENV_FILE too, so .env.local stays a stable "Mac native" file and
# is never clobbered by a tunnel run.

echo "  ✅ SSH tunnel detected"
echo "  ✅ Activated env: $REPO_ENV_FILE (via ENV_FILE=$ENV_FILE)"
cd backend
# --no-deps is intentional: VPS tunnel mode must not start local postgres/redis/minio/mailpit/rabbitmq/traefik.
ENV_FILE="$ENV_FILE" docker compose -p vps-dev -f local.yml up --build -d --no-deps api

echo "  ⏳ Waiting for API startup..."
for i in {1..60}; do
  logs=$(ENV_FILE="$ENV_FILE" docker compose -p vps-dev -f local.yml logs --no-color --tail=120 api 2>/dev/null || true)
  if echo "$logs" | grep -Eq "Application startup complete|Uvicorn running"; then
    echo "  ✅ API started"
    break
  fi
  if echo "$logs" | grep -Eq "Traceback|FAILED|ValueError|ModuleNotFoundError"; then
    echo "❌ API startup failed. Recent logs:"
    echo "$logs"
    exit 1
  fi
  if [ "$i" -eq 60 ]; then
    echo "❌ API did not finish startup within 120 seconds. Recent logs:"
    echo "$logs"
    exit 1
  fi
  sleep 2
done
ENV_FILE="$ENV_FILE" docker compose -p vps-dev -f local.yml up --build -d --no-deps celeryworker celerybeat

echo "✅ VPS dev backend is running against VPS dev DB/Redis/MinIO."
echo "Frontend: make frontend | Backend: http://localhost:8000 | Docs: http://localhost:8000/docs"
