#!/bin/bash
set -e

# Debug output
echo "=== ENVIRONMENT DEBUG ==="
echo "DEBUG variable: '$DEBUG'"
echo "ENVIRONMENT variable: '$ENVIRONMENT'"
echo "=========================="

# Your desired logic:
# 1. If DEBUG=true AND ENVIRONMENT=development -> Development WITH debugger
# 2. If DEBUG=false AND ENVIRONMENT=development -> Development WITHOUT debugger  
# 3. If DEBUG=false AND ENVIRONMENT=production -> Production mode

if [ "$DEBUG" = "true" ] && [ "$ENVIRONMENT" = "development" ]; then
    echo "🐛 Starting in DEVELOPMENT mode WITH debugger..."
    exec python -Xfrozen_modules=off -m debugpy --wait-for-client --listen 0.0.0.0:5678 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
elif [ "$DEBUG" = "false" ] && [ "$ENVIRONMENT" = "development" ]; then
    echo "🔄 Starting in DEVELOPMENT mode WITHOUT debugger..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
elif [ "$DEBUG" = "false" ] && [ "$ENVIRONMENT" = "production" ]; then
    echo "🚀 Starting in PRODUCTION mode..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
else
    echo "❌ Invalid configuration: DEBUG='$DEBUG', ENVIRONMENT='$ENVIRONMENT'"
    echo "Valid combinations:"
    echo "  DEBUG=true, ENVIRONMENT=development -> Development with debugger"
    echo "  DEBUG=false, ENVIRONMENT=development -> Development without debugger"
    echo "  DEBUG=false, ENVIRONMENT=production -> Production"
    exit 1
fi

# #!/bin/bash
# set -e

# if [ "$ENVIRONMENT" = "development" ]; then
#     echo "Starting in development mode with debugger..."
#     exec python -Xfrozen_modules=off -m debugpy --wait-for-client --listen 0.0.0.0:5678 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# else
#     echo "Starting in production mode..."
#     exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
# fi