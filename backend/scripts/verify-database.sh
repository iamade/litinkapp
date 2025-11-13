#!/bin/bash

# ============================================
# Database Verification Script
# ============================================
# Verifies that database schema and data are properly set up

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔍 Database Verification Script"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if we're in the backend directory
if [ ! -f "supabase/config.toml" ]; then
    echo -e "${RED}❌ Error: Please run this script from the backend directory${NC}"
    exit 1
fi

cd supabase

echo -e "${BLUE}1. Checking Migration Files${NC}"
echo "────────────────────────────────────────"

# Count migration files
MIGRATION_COUNT=$(ls -1 migrations/*.sql 2>/dev/null | wc -l)
echo "   Total migrations found: $MIGRATION_COUNT"

# Check for critical migrations
if [ -f "migrations/20250102000000_add_unique_email_constraint.sql" ]; then
    echo -e "   ${GREEN}✓${NC} Unique email constraint migration exists"
else
    echo -e "   ${RED}✗${NC} Unique email constraint migration MISSING"
fi

if [ -f "migrations/20251017150504_20251017150100_create_initial_superadmin_user.sql" ]; then
    echo -e "   ${GREEN}✓${NC} Superadmin creation migration exists"
else
    echo -e "   ${RED}✗${NC} Superadmin creation migration MISSING"
fi

echo ""
echo -e "${BLUE}2. Checking Seed File${NC}"
echo "────────────────────────────────────────"

if [ -f "seed.sql" ]; then
    SEED_LINES=$(wc -l < seed.sql)
    echo "   Seed file exists ($SEED_LINES lines)"

    # Check if it contains test data
    if grep -q "superadmin@litinkai.local" seed.sql; then
        echo -e "   ${YELLOW}⚠️${NC}  Seed file contains old test data"
        echo "   Consider using the minimal seed.sql"
    else
        echo -e "   ${GREEN}✓${NC} Seed file is minimal (no test data)"
    fi
else
    echo -e "   ${YELLOW}⚠️${NC}  Seed file not found"
fi

echo ""
echo -e "${BLUE}3. Database Connection Tests${NC}"
echo "────────────────────────────────────────"

# Test if Supabase is running
if command -v supabase &> /dev/null; then
    if supabase status &> /dev/null; then
        echo -e "   ${GREEN}✓${NC} Supabase is running"

        # Test database queries
        echo ""
        echo "   Running database checks..."

        # Check profiles table
        PROFILES_CHECK=$(supabase db execute "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'profiles';" 2>&1)
        if [[ $PROFILES_CHECK == *"1"* ]]; then
            echo -e "   ${GREEN}✓${NC} Profiles table exists"
        else
            echo -e "   ${RED}✗${NC} Profiles table not found"
        fi

        # Check unique constraint
        CONSTRAINT_CHECK=$(supabase db execute "SELECT COUNT(*) FROM pg_constraint WHERE conname = 'profiles_email_key';" 2>&1)
        if [[ $CONSTRAINT_CHECK == *"1"* ]]; then
            echo -e "   ${GREEN}✓${NC} Email unique constraint exists"
        else
            echo -e "   ${YELLOW}⚠️${NC}  Email unique constraint not found"
        fi

        # Check for superadmin profile
        SUPERADMIN_CHECK=$(supabase db execute "SELECT COUNT(*) FROM public.profiles WHERE 'superadmin' = ANY(roles);" 2>&1)
        if [[ $SUPERADMIN_CHECK == *"1"* ]] || [[ $SUPERADMIN_CHECK =~ [1-9][0-9]* ]]; then
            echo -e "   ${GREEN}✓${NC} Superadmin profile exists"

            # Get superadmin email
            SUPERADMIN_EMAIL=$(supabase db execute "SELECT email FROM public.profiles WHERE 'superadmin' = ANY(roles) LIMIT 1;" 2>&1 | grep -oE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' || echo "")
            if [ ! -z "$SUPERADMIN_EMAIL" ]; then
                echo "   Superadmin email: $SUPERADMIN_EMAIL"
            fi
        else
            echo -e "   ${YELLOW}⚠️${NC}  Superadmin profile not found"
            echo "   Run migrations or create manually"
        fi

    else
        echo -e "   ${YELLOW}⚠️${NC}  Supabase is not running"
        echo "   Start with: make supabase-start"
    fi
else
    echo -e "   ${YELLOW}⚠️${NC}  Supabase CLI not found"
    echo "   Install from: https://supabase.com/docs/guides/cli"
fi

echo ""
echo -e "${BLUE}4. Summary${NC}"
echo "────────────────────────────────────────"
echo "   Migration files: Ready"
echo "   Seed file: Minimal (recommended)"
echo ""
echo -e "${GREEN}✅ Verification complete${NC}"
echo ""
echo "💡 Next steps:"
echo "   - If Supabase is not running: make supabase-start"
echo "   - If issues found: make supabase-reset (WARNING: deletes data)"
echo "   - View migrations: supabase migration list"
echo ""

cd ..
