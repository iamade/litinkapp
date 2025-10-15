#!/bin/bash

# Quick start script for Celery workers
# Usage: ./start_celery.sh

set -e

echo "========================================="
echo "Starting Celery Workers for Scene Generation"
echo "========================================="
echo ""

# Check if we're in the backend directory
if [ ! -f "app/main.py" ]; then
    echo "ERROR: Please run this script from the backend directory"
    echo "  cd /tmp/cc-agent/50548081/project/backend"
    echo "  ./start_celery.sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found"
    echo "Make sure you have Redis and database credentials configured"
fi

# Check if Docker is available
if command -v docker-compose &> /dev/null; then
    echo "✓ Docker Compose found"
    echo ""
    echo "Starting services with Docker Compose..."
    echo "This will start: API, Redis, Celery Worker, Flower"
    echo ""
    
    docker-compose up -d
    
    echo ""
    echo "========================================="
    echo "Services Started Successfully!"
    echo "========================================="
    echo ""
    echo "Service URLs:"
    echo "  - API:    http://localhost:8000"
    echo "  - Flower: http://localhost:5555"
    echo ""
    echo "View logs:"
    echo "  - All:    docker-compose logs -f"
    echo "  - Celery: docker-compose logs -f celery"
    echo "  - API:    docker-compose logs -f api"
    echo ""
    echo "Stop services:"
    echo "  docker-compose down"
    echo ""
    
elif command -v celery &> /dev/null; then
    echo "✓ Celery command found"
    echo ""
    echo "Starting Celery worker manually..."
    echo "Make sure Redis is running on localhost:6379"
    echo ""
    
    # Check if Redis is accessible
    if command -v redis-cli &> /dev/null; then
        if redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
            echo "✓ Redis is running"
        else
            echo "WARNING: Cannot connect to Redis on localhost:6379"
            echo "Start Redis first with: docker run -d -p 6379:6379 redis:7-alpine"
        fi
    fi
    
    echo ""
    echo "Starting Celery worker..."
    celery -A app.tasks.celery_app worker --loglevel=info
    
else
    echo "ERROR: Neither Docker Compose nor Celery found"
    echo ""
    echo "Install with:"
    echo "  pip install celery[redis]"
    echo ""
    echo "Or use Docker:"
    echo "  docker-compose up -d"
    exit 1
fi
