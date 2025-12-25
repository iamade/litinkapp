#!/bin/bash

set -o errexit

set -o nounset

set -o pipefail

if [ "${DEBUG}" = "true" ]; then
    echo "Starting in DEBUG mode with debugpy..."
    exec python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "Starting in normal mode..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi