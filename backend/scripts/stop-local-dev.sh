#!/bin/bash

# ============================================
# Stop Application Services Only
# ============================================
# This script stops only the application services
# Supabase services will continue running if they were started separately

set -e

echo "🛑 Stopping Litinkai Application Services..."
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

echo "💡 Useful commands:"
echo "   - Start app again:     make dev"
echo "   - Stop Supabase:       make supabase-stop"
echo "   - Stop everything:     make all-down"
echo ""
