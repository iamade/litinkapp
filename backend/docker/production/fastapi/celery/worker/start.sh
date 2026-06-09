#!/bin/bash
set -o errexit
set -o nounset
set -o pipefail

exec celery \
  -A app.tasks.celery_app \
  worker \
  -Q ${CELERY_TASK_DEFAULT_QUEUE:-litink_tasks} \
  --concurrency=2 \
  --max-memory-per-child=400000 \
  --loglevel=info
