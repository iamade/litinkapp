#!/bin/bash

# ============================================
# Stop Local Development Environment
# ============================================
# This script stops all local development services

set -e

echo "🛑 Stopping Litinkai Local Development Environment..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the backend directory
if [ ! -f "supabase/config.toml" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    exit 1
fi

# Stop application services
echo -e "${BLUE}🐳 Stopping application services...${NC}"
docker-compose -f local.yml down

echo ""
echo -e "${GREEN}✅ Application services stopped${NC}"
echo ""

# Stop Supabase local services
echo -e "${BLUE}🗄️  Stopping Supabase local services...${NC}"
cd supabase
supabase stop
cd ..

echo ""
echo -e "${GREEN}✅ Supabase services stopped${NC}"
echo ""

echo -e "${GREEN}🎉 All services stopped successfully!${NC}"
echo ""
echo "💡 To start again, run: ./scripts/start-local-dev.sh"
echo ""
