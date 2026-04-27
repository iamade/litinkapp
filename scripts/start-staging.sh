#!/bin/bash
# Start staging with VPS tunnel
# PREREQUISITE: bash scripts/tunnel-staging.sh in another terminal

echo "Starting LitInkAI staging (tunnel mode)..."

# Check tunnel (match forwarded staging port; ssh args may appear before the host)
pgrep -f "ssh .*5432:127.0.0.1:5432.*72.62.97.111" > /dev/null || { echo "❌ Run tunnel-staging.sh first and leave it open!"; exit 1; }

# Use VPS staging tunnel env. Preserve any pre-existing local env once so the
# tunnel workflow does not destroy the user's normal local setup.
if [ -f backend/.envs/.env.local ] && [ ! -f backend/.envs/.env.local.before-vps-tunnel ]; then
    cp backend/.envs/.env.local backend/.envs/.env.local.before-vps-tunnel
    echo "✅ Backed up existing local env to backend/.envs/.env.local.before-vps-tunnel"
fi
cp scripts/env.staging backend/.envs/.env.local

# Start only backend + frontend (tunnel to VPS for DB/redis/minio)
cd backend
docker compose -f local.yml -f local-tunnel.yml up --build -d

echo "✅ Staging running: http://localhost:5173"
