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

echo "Starting LitInkAI VPS staging tunnel backend..."

if ! pgrep -f "5432:127.0.0.1:5432.*72.62.97.111" > /dev/null; then
  echo "❌ ERROR: SSH staging tunnel not running. Run this FIRST in another terminal:"
  echo "  make tunnel-staging"
  exit 1
fi

[ -f "$REPO_ENV_FILE" ] || { echo "❌ Missing env file: $REPO_ENV_FILE"; exit 1; }
cp "$REPO_ENV_FILE" backend/.envs/.env.local
chmod 600 backend/.envs/.env.local

echo "  ✅ SSH staging tunnel detected"
echo "  ✅ Activated env: $REPO_ENV_FILE -> backend/.envs/.env.local"

cd backend
# --no-deps is intentional: VPS tunnel mode must not start local postgres/redis/minio.
ENV_FILE="$ENV_FILE" docker compose -f local.yml up --build -d --no-deps api
ENV_FILE="$ENV_FILE" docker compose -f local.yml up --build -d --no-deps celeryworker celerybeat

echo "✅ VPS staging backend is running against VPS staging DB/Redis/MinIO."
echo "Frontend: make frontend | Backend: http://localhost:8000 | Docs: http://localhost:8000/docs"
