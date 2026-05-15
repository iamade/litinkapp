#!/bin/bash
# Backward-compatible wrapper. Prefer: bash scripts/start-vps-dev.sh
# This intentionally does not overwrite backend/.envs/.env.local.
exec bash scripts/start-vps-dev.sh "$@"
