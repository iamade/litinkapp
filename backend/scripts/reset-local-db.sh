#!/bin/bash

# ============================================
# Reset Local Database
# ============================================
# This script resets the local Supabase database
# WARNING: This will delete all local data!

set -e

echo "⚠️  WARNING: This will reset your local database and delete all data!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "❌ Reset cancelled"
    exit 1
fi

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

echo -e "${BLUE}🔄 Resetting local database...${NC}"
echo ""

cd supabase

# Reset the database (this will re-run all migrations and seed data)
supabase db reset

cd ..

echo ""
echo -e "${GREEN}✅ Database reset successfully!${NC}"
echo ""

echo -e "${YELLOW}📊 Database Status:${NC}"
echo "   - All migrations have been re-applied"
echo "   - Seed data has been loaded"
echo "   - Test users are available"
echo ""

echo -e "${YELLOW}👤 Test Users (all passwords: password123):${NC}"
echo "   superadmin@litinkai.local - Superadmin"
echo "   admin@litinkai.local      - Admin"
echo "   creator@litinkai.local    - Creator"
echo "   user@litinkai.local       - Regular User"
echo "   premium@litinkai.local    - Premium User"
echo ""

echo -e "${GREEN}🎉 Ready for testing!${NC}"
echo ""
