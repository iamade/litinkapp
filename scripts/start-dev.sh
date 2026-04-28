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

echo "Starting LitInkAI VPS dev tunnel backend..."

if ! pgrep -f "5433:127.0.0.1:5433.*72.62.97.111" > /dev/null; then
  echo "❌ ERROR: SSH dev tunnel not running. Run this FIRST in another terminal:"
  echo "  make tunnel-dev"
  exit 1
fi

[ -f "$REPO_ENV_FILE" ] || { echo "❌ Missing env file: $REPO_ENV_FILE"; exit 1; }
cp "$REPO_ENV_FILE" backend/.envs/.env.local
chmod 600 backend/.envs/.env.local

echo "  ✅ SSH dev tunnel detected"
echo "  ✅ Activated env: $REPO_ENV_FILE -> backend/.envs/.env.local"

cd backend
# --no-deps is intentional: VPS tunnel mode must not start local postgres/redis/minio.
ENV_FILE="$ENV_FILE" docker compose -f local.yml up --build -d --no-deps api
ENV_FILE="$ENV_FILE" docker compose -f local.yml up --build -d --no-deps celeryworker celerybeat

echo "✅ VPS dev backend is running against VPS dev DB/Redis/MinIO."
echo "Frontend: make frontend | Backend: http://localhost:8000 | Docs: http://localhost:8000/docs"
