#!/bin/bash
set -o errexit
set -o nounset
set -o pipefail

mkdir -p /tmp
chmod 777 /tmp

exec celery \
  -A app.tasks.celery_app \
  beat \
  --scheduler celery.beat.PersistentScheduler \
  --schedule /tmp/celerybeat-schedule \
  --loglevel=info
