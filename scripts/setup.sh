#!/bin/bash
# =============================================================================
# LitInkAI — Mac Local Dev Setup (Tunnel Mode)
# =============================================================================
# This connects your local code to VPS staging/dev services via SSH tunnel.
# Use this when you want to see PSQ's test data from the staging/dev stacks.
#
# USAGE:
#   1. ./scripts/setup-staging.sh    # First time only
#   2. ./scripts/start-staging.sh    # Start staging dev environment
#   3. ./scripts/start-dev.sh         # Start dev environment
#   4. ./scripts/stop-tunnel.sh       # Stop tunnels when done
# =============================================================================

set -e

echo "============================================"
echo "LitInkAI — Mac Tunnel Mode Setup"
echo "============================================"
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Run this from the litinkapp directory: cd ~/My_app_projects/People-Protocol-apps/litinkapp"
    exit 1
fi

# Create scripts directory if it doesn't exist
mkdir -p scripts

echo "📦 Cloning staging and dev_branch..."
git fetch --all
git branch -r | grep -q "origin/staging" && echo "  ✅ staging branch exists" || git checkout -b staging origin/staging
echo ""

echo "============================================"
echo "✅ Setup complete!"
echo ""
echo "TO USE STAGING:"
echo "  1. bash scripts/tunnel-staging.sh   # In one terminal — keep running"
echo "  2. bash scripts/start-staging.sh     # In another terminal"
echo ""
echo "TO USE DEV:"
echo "  1. bash scripts/tunnel-dev.sh        # In one terminal — keep running"
echo "  2. bash scripts/start-dev.sh         # In another terminal"
echo ""
echo "TO STOP:"
echo "  pkill -f 'ssh -N.*72.62.97.111'     # Kill tunnels"
echo "  docker compose -f backend/local.yml down  # Stop containers"
echo "============================================"
