#!/bin/bash
# SSH tunnel for staging services on VPS
# Run BEFORE starting local Docker: ssh -N -f scripts/tunnel-staging.sh

ssh -N \
  -L 5432:127.0.0.1:5432 \
  -L 6379:127.0.0.1:6379 \
  -L 9000:127.0.0.1:9000 \
  -L 9001:127.0.0.1:9001 \
  root@72.62.97.111

echo "Staging tunnel active. Press Ctrl+C to stop."
