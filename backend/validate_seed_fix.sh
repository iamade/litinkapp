#!/bin/bash

# ============================================
# Validate Seed Data Fix
# ============================================
# This script validates that the seed data fix was applied correctly

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Validating Seed Data Fix...${NC}"
echo ""

# Check if we're in the backend directory
if [ ! -f "supabase/config.toml" ]; then
    echo -e "${RED}❌ Error: Please run this script from the backend directory${NC}"
    exit 1
fi

# Check if migration file exists
MIGRATION_FILE="supabase/migrations/20251113225537_add_seed_compatibility_columns.sql"
if [ -f "$MIGRATION_FILE" ]; then
    echo -e "${GREEN}✅ Migration file exists${NC}"
else
    echo -e "${RED}❌ Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

# Check if seed file was updated
if grep -q "Create Sample Plot Overviews" supabase/seed.sql; then
    echo -e "${GREEN}✅ Seed file includes plot_overviews section${NC}"
else
    echo -e "${RED}❌ Seed file missing plot_overviews section${NC}"
    exit 1
fi

# Check if characters INSERT includes required columns
if grep -q "plot_overview_id," supabase/seed.sql; then
    echo -e "${GREEN}✅ Characters section includes plot_overview_id${NC}"
else
    echo -e "${RED}❌ Characters section missing plot_overview_id${NC}"
    exit 1
fi

# Count migrations
MIGRATION_COUNT=$(ls -1 supabase/migrations/*.sql 2>/dev/null | wc -l)
echo -e "${GREEN}✅ Found $MIGRATION_COUNT migration files${NC}"

echo ""
echo -e "${GREEN}🎉 All validation checks passed!${NC}"
echo ""

echo -e "${YELLOW}📝 Next steps:${NC}"
echo "   1. Stop Supabase: cd supabase && supabase stop && cd .."
echo "   2. Start Supabase: cd supabase && supabase start && cd .."
echo "   3. Check output for success message"
echo "   4. Open Supabase Studio: http://127.0.0.1:54323"
echo "   5. Verify data in tables: profiles, books, characters, scripts"
echo ""

echo -e "${YELLOW}🔑 Test login credentials:${NC}"
echo "   Email: superadmin@litinkai.local"
echo "   Password: password123"
echo ""

echo -e "${YELLOW}📚 Documentation:${NC}"
echo "   Quick Start: QUICK_START_SEED_FIX.md"
echo "   Full Details: SEED_DATA_FIX_SUMMARY.md"
echo ""
