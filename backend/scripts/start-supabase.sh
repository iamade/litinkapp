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
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the backend directory
if [ ! -f "supabase/config.toml" ]; then
    echo -e "${RED}❌ Error: Please run this script from the backend directory${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Create network if it doesn't exist
echo -e "${BLUE}📡 Creating Docker network...${NC}"
docker network create litinkai_local_nw 2>/dev/null || echo "Network already exists"

# Function to check migration order
check_migrations() {
    echo -e "${BLUE}🔍 Checking migration files...${NC}"

    # Check if unique constraint migration exists
    if [ ! -f "supabase/migrations/20250102000000_add_unique_email_constraint.sql" ]; then
        echo -e "${YELLOW}⚠️  Warning: Unique constraint migration not found${NC}"
        echo "   This may cause issues with superadmin creation"
    else
        echo -e "${GREEN}✓ Unique constraint migration found${NC}"
    fi

    # Check if superadmin migration exists
    if [ ! -f "supabase/migrations/20251017150504_20251017150100_create_initial_superadmin_user.sql" ]; then
        echo -e "${YELLOW}⚠️  Warning: Superadmin creation migration not found${NC}"
    else
        echo -e "${GREEN}✓ Superadmin creation migration found${NC}"
    fi

    echo ""
}

# Run migration checks
check_migrations

# Start Supabase local services
echo -e "${BLUE}🗄️  Starting Supabase local services...${NC}"
echo -e "${YELLOW}   This will run all migrations and seed data...${NC}"
echo ""

cd supabase

# Try to start Supabase
if supabase start; then
    echo -e "${GREEN}✅ Supabase started successfully${NC}"
    START_SUCCESS=true
else
    echo -e "${RED}❌ Failed to start Supabase on first attempt${NC}"
    echo -e "${YELLOW}🔄 Attempting to stop and restart...${NC}"
    supabase stop

    if supabase start; then
        echo -e "${GREEN}✅ Supabase started successfully on second attempt${NC}"
        START_SUCCESS=true
    else
        echo -e "${RED}❌ Failed to start Supabase after retry${NC}"
        echo ""
        echo -e "${YELLOW}💡 Troubleshooting tips:${NC}"
        echo "   1. Check Docker is running: docker ps"
        echo "   2. Check Docker resources (RAM/CPU)"
        echo "   3. Try: supabase stop && supabase start --debug"
        echo "   4. Check logs: docker logs <container-name>"
        echo "   5. Reset database: make supabase-reset (WARNING: deletes data)"
        echo ""
        cd ..
        exit 1
    fi
fi

cd ..

echo ""
echo -e "${GREEN}✅ Supabase services started successfully!${NC}"
echo ""

# Verify database setup
echo -e "${BLUE}🔍 Verifying database setup...${NC}"
cd supabase

# Check if superadmin profile exists
SUPERADMIN_CHECK=$(supabase db execute "SELECT email FROM public.profiles WHERE 'superadmin' = ANY(roles) LIMIT 1;" 2>/dev/null || echo "")

if [[ $SUPERADMIN_CHECK == *"support@litinkai.com"* ]]; then
    echo -e "${GREEN}✓ Superadmin profile exists${NC}"
else
    echo -e "${YELLOW}⚠️  Superadmin profile not found or not verified${NC}"
    echo "   This is normal on first run. Check migration logs above."
fi

# Check if unique constraint exists
CONSTRAINT_CHECK=$(supabase db execute "SELECT COUNT(*) FROM pg_constraint WHERE conname = 'profiles_email_key';" 2>/dev/null || echo "")

if [[ $CONSTRAINT_CHECK == *"1"* ]]; then
    echo -e "${GREEN}✓ Email unique constraint exists${NC}"
else
    echo -e "${YELLOW}⚠️  Email unique constraint not found${NC}"
    echo "   Migration may not have run successfully."
fi

cd ..
echo ""

# Display Supabase connection info
echo -e "${YELLOW}📊 Supabase Local Services:${NC}"
echo "   Studio URL:    http://127.0.0.1:54323"
echo "   Inbucket URL:  http://127.0.0.1:54324 (Email testing)"
echo "   API URL:       http://127.0.0.1:54321"
echo "   DB URL:        postgresql://postgres:postgres@127.0.0.1:54322/postgres"
echo ""

# Get the actual keys from supabase status
echo -e "${YELLOW}🔑 Connection Details:${NC}"
cd supabase
supabase status
cd ..

echo ""
echo -e "${GREEN}🎉 Supabase is ready!${NC}"
echo ""
echo "📝 Next steps:"
echo "   1. Create the superadmin auth user (if not already done):"
echo "      - Open Studio: http://127.0.0.1:54323"
echo "      - Go to Authentication > Users > Add User"
echo "      - Email: support@litinkai.com"
echo "      - Set a secure password"
echo ""
echo "   2. Copy the ANON_KEY and SERVICE_ROLE_KEY from above"
echo "   3. Update your backend/.envs/.env.local file with these values"
echo "   4. Start your application with: make dev"
echo ""
echo "💡 Useful commands:"
echo "   - Check status:      cd supabase && supabase status && cd .."
echo "   - Stop Supabase:     make supabase-stop"
echo "   - Reset database:    make supabase-reset"
echo "   - View migrations:   cd supabase && supabase migration list && cd .."
echo ""
