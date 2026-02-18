#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail

python << END
import sys
import time
from urllib.parse import urlparse

MAX_WAIT_SECONDS = 60
RETRY_INTERVAL = 5
start_time = time.time()

# Parse DATABASE_URL to extract connection params
import os
db_url = os.environ.get("DATABASE_URL", "")

# Convert asyncpg URL to psycopg-compatible URL
db_url_sync = db_url.replace("postgresql+asyncpg://", "postgresql://")

def check_database():
    import psycopg
    try:
        psycopg.connect(db_url_sync)
        return True
    except psycopg.OperationalError as error:
        elapsed = int(time.time() - start_time)
        sys.stderr.write(f"Database connection attempt failed after {elapsed} seconds: {error}\n")
        return False

while True:
    if check_database():
        break

    if time.time() - start_time > MAX_WAIT_SECONDS:
        sys.stderr.write("Error: Database connection could not be established after 60 seconds\n")
        sys.exit(1)

    sys.stderr.write(f"Waiting {RETRY_INTERVAL} seconds before retrying... \n")
    time.sleep(RETRY_INTERVAL)
END

echo >&2 'PostgreSQL is ready to accept connections'

alembic upgrade head || exit 1

exec "$@"
