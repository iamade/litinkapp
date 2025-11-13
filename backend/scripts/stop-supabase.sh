#!/bin/bash

# ============================================
# Stop Supabase Local Services Only
# ============================================
# This script stops only the Supabase local services
# Your application services will continue running if they were started separately

set -e

echo "🛑 Stopping Supabase Local Services..."
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

# Stop Supabase local services
echo -e "${BLUE}🗄️  Stopping Supabase local services...${NC}"
cd supabase
supabase stop
cd ..

echo ""
echo -e "${GREEN}✅ Supabase services stopped${NC}"
echo ""

echo "💡 To start Supabase again, run: make supabase-start"
echo ""
