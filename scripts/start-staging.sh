#!/bin/bash
# Backward-compatible wrapper. Prefer: bash scripts/start-vps-staging.sh or make vps-staging
exec bash scripts/start-vps-staging.sh "$@"
