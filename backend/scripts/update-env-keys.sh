#!/bin/bash

# ============================================
# Update .env.local with Local Supabase Keys
# ============================================
# This script extracts the local Supabase API keys
# and updates your .env.local file automatically

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔑 Extracting Local Supabase Keys...${NC}"
echo ""

# Check if we're in the backend directory
if [ ! -f "supabase/config.toml" ]; then
    echo -e "${RED}❌ Error: Please run this script from the backend directory${NC}"
    exit 1
fi

# Check if .envs/.env.local exists
if [ ! -f ".envs/.env.local" ]; then
    echo -e "${RED}❌ Error: .envs/.env.local file not found${NC}"
    echo "   Please create it first from .envs/.env.example"
    exit 1
fi

# Check if Supabase is running
cd supabase
if ! supabase status > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Supabase is not running${NC}"
    echo "   Please start it first with: make supabase-start"
    cd ..
    exit 1
fi

# Extract keys from supabase status
echo -e "${BLUE}📋 Reading Supabase configuration...${NC}"

ANON_KEY=$(supabase status | grep "anon key:" | awk '{print $3}')
SERVICE_ROLE_KEY=$(supabase status | grep "service_role key:" | awk '{print $3}')
API_URL=$(supabase status | grep "API URL:" | awk '{print $3}')
DB_URL=$(supabase status | grep "DB URL:" | awk '{print $3}')

cd ..

# Validate that we got the keys
if [ -z "$ANON_KEY" ] || [ -z "$SERVICE_ROLE_KEY" ]; then
    echo -e "${RED}❌ Error: Could not extract keys from Supabase${NC}"
    echo "   Please check that Supabase is running properly"
    exit 1
fi

echo -e "${GREEN}✓ Keys extracted successfully${NC}"
echo ""

# Backup the original file
BACKUP_FILE=".envs/.env.local.backup.$(date +%Y%m%d_%H%M%S)"
cp .envs/.env.local "$BACKUP_FILE"
echo -e "${BLUE}💾 Backup created: $BACKUP_FILE${NC}"

# Update the .env.local file
echo -e "${BLUE}📝 Updating .env.local with local keys...${NC}"

# Use sed to replace the keys (works on both macOS and Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|^SUPABASE_URL=.*|SUPABASE_URL=$API_URL|g" .envs/.env.local
    sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=$DB_URL|g" .envs/.env.local
    sed -i '' "s|^SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$ANON_KEY|g" .envs/.env.local
    sed -i '' "s|^SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SERVICE_ROLE_KEY|g" .envs/.env.local
    sed -i '' "s|^SUPABASE_KEY=.*|SUPABASE_KEY=$ANON_KEY|g" .envs/.env.local
else
    # Linux
    sed -i "s|^SUPABASE_URL=.*|SUPABASE_URL=$API_URL|g" .envs/.env.local
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$DB_URL|g" .envs/.env.local
    sed -i "s|^SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$ANON_KEY|g" .envs/.env.local
    sed -i "s|^SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SERVICE_ROLE_KEY|g" .envs/.env.local
    sed -i "s|^SUPABASE_KEY=.*|SUPABASE_KEY=$ANON_KEY|g" .envs/.env.local
fi

echo ""
echo -e "${GREEN}✅ Successfully updated .env.local with local Supabase keys!${NC}"
echo ""
echo -e "${YELLOW}📊 Updated Configuration:${NC}"
echo "   SUPABASE_URL: $API_URL"
echo "   DATABASE_URL: $DB_URL"
echo "   SUPABASE_ANON_KEY: ${ANON_KEY:0:20}..."
echo "   SUPABASE_SERVICE_ROLE_KEY: ${SERVICE_ROLE_KEY:0:20}..."
echo ""
echo -e "${GREEN}🎉 Your environment is now configured for local development!${NC}"
echo ""
echo "📝 Next steps:"
echo "   1. Review .envs/.env.local to ensure all other values are correct"
echo "   2. Start your application with: make dev"
echo "   3. Access Supabase Studio: http://127.0.0.1:54323"
echo ""
echo "💡 Backup location: $BACKUP_FILE"
echo ""
