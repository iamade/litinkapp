#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail

python << END
import sys
import time
import psycopg

MAX_WAIT_SECONDS = 30
RETRY_INTERVAL = 5
start_time = time.time()

def check_database():
    try:
        psycopg.connect(
            dbname="${POSTGRES_DB}",
            user="${POSTGRES_USER}",
            password="${POSTGRES_PASSWORD}",
            host="${POSTGRES_HOST}",
            port="${POSTGRES_PORT}",
        )
        return True
    except psycopg.OperationalError as error:
        elapsed = int(time.time() - start_time)
        sys.stderr.write(f"Database connection attempt failed after {elapsed} seconds: {error}\n")
        return False

while True:
    if check_database():
        break
        
    if time.time() - start_time > MAX_WAIT_SECONDS:
        sys.stderr.write("Error: Database connection could not be established after 30 seconds\n")
        sys.exit(1)
    
    sys.stderr.write(f"Waiting {RETRY_INTERVAL} seconds before retrying... \n")
    time.sleep(RETRY_INTERVAL)
END

echo >&2 'PostgreSQL is ready to accept connections'

alembic upgrade head

# If called with an explicit command (e.g., /start.sh), run it
# Otherwise, use environment detection to start the appropriate mode
if [ $# -gt 0 ]; then
    exec "$@"
fi

# Debug output
echo "=== ENVIRONMENT DEBUG ==="
echo "DEBUG variable: '${DEBUG:-not set}'"
echo "ENVIRONMENT variable: '${ENVIRONMENT:-not set}'"
echo "=========================="

# Environment-based startup logic:
# 1. If DEBUG=true AND ENVIRONMENT=development -> Development WITH debugger
# 2. If DEBUG=false AND ENVIRONMENT=development -> Development WITHOUT debugger  
# 3. If ENVIRONMENT=production -> Production mode (ignore DEBUG)

if [ "${ENVIRONMENT:-development}" = "production" ]; then
    echo "🚀 Starting in PRODUCTION mode..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
elif [ "${DEBUG:-false}" = "true" ] && [ "${ENVIRONMENT:-development}" = "development" ]; then
    echo "🐛 Starting in DEVELOPMENT mode WITH debugger..."
    exec python -Xfrozen_modules=off -m debugpy --wait-for-client --listen 0.0.0.0:5678 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
elif [ "${DEBUG:-false}" = "false" ] && [ "${ENVIRONMENT:-development}" = "development" ]; then
    echo "🔄 Starting in DEVELOPMENT mode WITHOUT debugger..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "❌ Invalid configuration: DEBUG='${DEBUG:-not set}', ENVIRONMENT='${ENVIRONMENT:-not set}'"
    echo "Valid combinations:"
    echo "  DEBUG=true, ENVIRONMENT=development -> Development with debugger"
    echo "  DEBUG=false, ENVIRONMENT=development -> Development without debugger"
    echo "  ENVIRONMENT=production -> Production"
    exit 1
fi

