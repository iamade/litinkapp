#!/bin/bash

# ============================================
# Start Local Development Environment
# ============================================
# This script starts the complete local development stack:
# 1. Supabase local services (DB, Auth, Storage, Studio, Inbucket)
# 2. Application services (API, Redis, RabbitMQ, Celery, etc.)

set -e

echo "🚀 Starting Litinkai Local Development Environment..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the backend directory
if [ ! -f "supabase/config.toml" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create network if it doesn't exist
echo -e "${BLUE}📡 Creating Docker network...${NC}"
docker network create litinkai_local_nw 2>/dev/null || echo "Network already exists"

# Start Supabase local services
echo -e "${BLUE}🗄️  Starting Supabase local services...${NC}"
cd supabase
supabase start || {
    echo "❌ Failed to start Supabase. Trying to stop and restart..."
    supabase stop
    supabase start
}
cd ..

echo ""
echo -e "${GREEN}✅ Supabase services started successfully!${NC}"
echo ""

# Display Supabase connection info
echo -e "${YELLOW}📊 Supabase Local Dashboard:${NC}"
echo "   Studio URL:    http://127.0.0.1:54323"
echo "   Inbucket URL:  http://127.0.0.1:54324 (Email testing)"
echo "   API URL:       http://127.0.0.1:54321"
echo "   DB URL:        postgresql://postgres:postgres@127.0.0.1:54322/postgres"
echo ""

# Wait a moment for Supabase to fully initialize
echo "⏳ Waiting for Supabase to fully initialize..."
sleep 5

# Start application services
echo -e "${BLUE}🐳 Starting application services...${NC}"
docker-compose -f local.yml up -d

echo ""
echo -e "${GREEN}✅ Application services started successfully!${NC}"
echo ""

# Display application URLs
echo -e "${YELLOW}🌐 Application URLs:${NC}"
echo "   API:           http://localhost:8000"
echo "   API Health:    http://localhost:8000/health"
echo "   Traefik:       http://localhost:8080"
echo "   Mailpit:       http://localhost:8025"
echo "   RabbitMQ:      http://localhost:15672 (guest/guest)"
echo "   Flower:        http://localhost:5555"
echo ""

echo -e "${YELLOW}👤 Test Users (all passwords: password123):${NC}"
echo "   superadmin@litinkai.local - Superadmin"
echo "   admin@litinkai.local      - Admin"
echo "   creator@litinkai.local    - Creator"
echo "   user@litinkai.local       - Regular User"
echo "   premium@litinkai.local    - Premium User"
echo ""

echo -e "${GREEN}🎉 Local development environment is ready!${NC}"
echo ""
echo "📝 Useful commands:"
echo "   - View logs:           docker-compose -f local.yml logs -f"
echo "   - Stop services:       ./scripts/stop-local-dev.sh"
echo "   - Reset database:      ./scripts/reset-local-db.sh"
echo "   - Restart Supabase:    cd supabase && supabase restart && cd .."
echo ""
