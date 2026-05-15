#!/bin/bash
# SSH tunnel for dev services on VPS
# Run BEFORE starting local Docker: bash scripts/tunnel-dev.sh

echo "Starting dev tunnel..."
echo "Dev tunnel active when this command stays open. Press Ctrl+C to stop."

ssh -N -o ExitOnForwardFailure=yes \
  -L 5433:127.0.0.1:5433 \
  -L 6380:127.0.0.1:6380 \
  -L 9010:127.0.0.1:9010 \
  -L 9011:127.0.0.1:9011 \
  root@72.62.97.111
