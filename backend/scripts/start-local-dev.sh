#!/bin/bash

# ============================================
# Start Application Services Only
# ============================================
# This script starts only the application services (API, Redis, RabbitMQ, Celery, etc.)
# You must start Supabase separately first using: make supabase-start

set -e

echo "🚀 Starting Litinkai Application Services..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Check if Supabase is running
echo -e "${BLUE}🔍 Checking if Supabase is running...${NC}"
cd supabase
if ! supabase status > /dev/null 2>&1; then
    echo ""
    echo -e "${RED}❌ Error: Supabase is not running!${NC}"
    echo ""
    echo "Please start Supabase first:"
    echo "   make supabase-start"
    echo ""
    echo "Or if you want to start everything together:"
    echo "   make all-up"
    echo ""
    cd ..
    exit 1
fi
cd ..

echo -e "${GREEN}✅ Supabase is running${NC}"
echo ""

# Create network if it doesn't exist
echo -e "${BLUE}📡 Creating Docker network...${NC}"
docker network create litinkai_local_nw 2>/dev/null || echo "Network already exists"

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

echo -e "${GREEN}🎉 Application services are ready!${NC}"
echo ""
echo "📝 Useful commands:"
echo "   - View logs:           docker-compose -f local.yml logs -f"
echo "   - Stop app services:   make down"
echo "   - Stop Supabase:       make supabase-stop"
echo "   - Reset database:      make supabase-reset"
echo "   - Supabase Studio:     http://127.0.0.1:54323"
echo ""
