#!/bin/bash
# Start staging with VPS tunnel
# PREREQUISITE: bash scripts/tunnel-staging.sh in another terminal

echo "Starting LitInkAI staging (tunnel mode)..."

# Check tunnel
pgrep -f "ssh -N.*72.62.97.111.*5432" > /dev/null || { echo "❌ Run tunnel-staging.sh first!"; exit 1; }

# Use staging env
cp scripts/env.staging backend/.envs/.env.local

# Start only backend + frontend (tunnel to VPS for DB/redis/minio)
cd backend
docker compose -f local.yml -f local-tunnel.yml up --build -d

echo "✅ Staging running: http://localhost:5173"
