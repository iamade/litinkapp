#!/bin/bash
set -o errexit
set -o nounset
set -o pipefail

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "Database migrations complete."

# Use Render's PORT env var, fallback to 8000 for local
PORT="${PORT:-8000}"

exec gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT} \
  --timeout 120 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --forwarded-allow-ips '*'
