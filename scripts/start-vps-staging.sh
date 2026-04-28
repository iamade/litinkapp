#!/bin/bash
# =============================================================================
# Start LitInkAI local backend against VPS staging tunneled services.
# PREREQUISITE: Run in another terminal and leave open:
#   make tunnel-staging
# Uses canonical env: backend/.envs/.env.vps-staging
# =============================================================================
set -euo pipefail

ENV_FILE=${ENV_FILE:-./.envs/.env.vps-staging}
REPO_ENV_FILE="backend/${ENV_FILE#./}"

if [ "$ENV_FILE" = "./.envs/.env.local" ] || [ "$ENV_FILE" = ".envs/.env.local" ]; then
  echo "❌ Refusing to use backend/.envs/.env.local for VPS tunnel mode."
  echo "Use backend/.envs/.env.vps-staging for VPS staging."
  exit 1
fi

echo "Starting LitInkAI VPS staging tunnel backend..."
if ! pgrep -f "ssh .*5432:127.0.0.1:5432.*72.62.97.111" > /dev/null; then
  echo "❌ ERROR: SSH staging tunnel not running. Run: make tunnel-staging"
  exit 1
fi
[ -f "$REPO_ENV_FILE" ] || { echo "❌ Missing env file: $REPO_ENV_FILE"; exit 1; }
cp "$REPO_ENV_FILE" backend/.envs/.env.local
chmod 600 backend/.envs/.env.local

echo "  ✅ SSH tunnel detected"
echo "  ✅ Activated env: $REPO_ENV_FILE -> backend/.envs/.env.local"
cd backend
ENV_FILE="$ENV_FILE" docker compose -f local.yml up --build -d api

echo "  ⏳ Waiting for API startup..."
for i in {1..60}; do
  logs=$(ENV_FILE="$ENV_FILE" docker compose -f local.yml logs --no-color --tail=120 api 2>/dev/null || true)
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
ENV_FILE="$ENV_FILE" docker compose -f local.yml up --build -d celeryworker celerybeat

echo "✅ VPS staging backend is running against VPS staging DB/Redis/MinIO."
echo "Frontend: make frontend | Backend: http://localhost:8000 | Docs: http://localhost:8000/docs"
