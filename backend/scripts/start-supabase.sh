#!/bin/bash

# ============================================
# Start Supabase Local Services Only
# ============================================
# This script starts only the Supabase local services
# Use this before starting your application services

set -e

echo "🚀 Starting Supabase Local Services..."
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
echo -e "${YELLOW}📊 Supabase Local Services:${NC}"
echo "   Studio URL:    http://127.0.0.1:54323"
echo "   Inbucket URL:  http://127.0.0.1:54324 (Email testing)"
echo "   API URL:       http://127.0.0.1:54321"
echo "   DB URL:        postgresql://postgres:postgres@127.0.0.1:54322/postgres"
echo ""

# Get the actual keys from supabase status
echo -e "${YELLOW}🔑 Getting connection details...${NC}"
cd supabase
supabase status
cd ..

echo ""
echo -e "${GREEN}🎉 Supabase is ready!${NC}"
echo ""
echo "📝 Next steps:"
echo "   1. Copy the ANON_KEY and SERVICE_ROLE_KEY from above"
echo "   2. Update your backend/.envs/.env.local file with these values"
echo "   3. Start your application with: make dev"
echo ""
echo "💡 Useful commands:"
echo "   - Check status:      cd supabase && supabase status && cd .."
echo "   - Stop Supabase:     make supabase-stop"
echo "   - Reset database:    make supabase-reset"
echo ""
