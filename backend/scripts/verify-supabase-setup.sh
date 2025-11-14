#!/bin/bash

# ============================================
# Verify Supabase Setup - Quick Diagnostics
# ============================================
# This script verifies all required components
# are in place for successful Supabase startup

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔍 Verifying Supabase Setup..."
echo ""

ISSUES_FOUND=0

# Check if we're in the backend directory
if [ ! -f "supabase/config.toml" ]; then
    echo -e "${RED}❌ Error: Please run this script from the backend directory${NC}"
    exit 1
fi

# 1. Check Docker
echo -e "${BLUE}1. Checking Docker...${NC}"
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}   ✓ Docker is running${NC}"
else
    echo -e "${RED}   ✗ Docker is not running${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 2. Check storage directory
echo -e "${BLUE}2. Checking storage directory...${NC}"
if [ -d "supabase/storage/books" ]; then
    echo -e "${GREEN}   ✓ Storage directory exists: supabase/storage/books${NC}"
else
    echo -e "${RED}   ✗ Storage directory missing: supabase/storage/books${NC}"
    echo -e "${YELLOW}   → Will be created automatically on startup${NC}"
fi

# 3. Check migrations directory
echo -e "${BLUE}3. Checking migrations...${NC}"
if [ -d "supabase/migrations" ]; then
    MIGRATION_COUNT=$(ls -1 supabase/migrations/*.sql 2>/dev/null | wc -l)
    echo -e "${GREEN}   ✓ Migrations directory exists (${MIGRATION_COUNT} migrations found)${NC}"

    # Verify key migrations exist
    if [ -f "supabase/migrations/20251113071543_20251113_071315_add_auth_columns_to_profiles.sql" ]; then
        echo -e "${GREEN}   ✓ Auth columns migration found${NC}"
    else
        echo -e "${RED}   ✗ Auth columns migration missing${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi

    if [ -f "supabase/migrations/20251113080000_create_initial_superadmin_user.sql" ]; then
        echo -e "${GREEN}   ✓ Superadmin migration found (correct order)${NC}"
    else
        echo -e "${RED}   ✗ Superadmin migration missing or incorrectly named${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
else
    echo -e "${RED}   ✗ Migrations directory missing${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 4. Check config.toml
echo -e "${BLUE}4. Checking config.toml...${NC}"
if [ -f "supabase/config.toml" ]; then
    echo -e "${GREEN}   ✓ Config file exists${NC}"

    # Check for storage bucket configuration
    if grep -q "storage.buckets.books" supabase/config.toml; then
        echo -e "${GREEN}   ✓ Storage bucket configured${NC}"
    else
        echo -e "${YELLOW}   ⚠ Storage bucket not configured${NC}"
    fi
else
    echo -e "${RED}   ✗ Config file missing${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 5. Check seed data
echo -e "${BLUE}5. Checking seed data...${NC}"
if [ -f "supabase/seed.sql" ]; then
    echo -e "${GREEN}   ✓ Seed file exists${NC}"
else
    echo -e "${YELLOW}   ⚠ Seed file missing (optional)${NC}"
fi

# 6. Check Docker network
echo -e "${BLUE}6. Checking Docker network...${NC}"
if docker network inspect litinkai_local_nw > /dev/null 2>&1; then
    echo -e "${GREEN}   ✓ Docker network exists: litinkai_local_nw${NC}"
else
    echo -e "${YELLOW}   ⚠ Docker network not created yet (will be created on startup)${NC}"
fi

# 7. Check if Supabase is already running
echo -e "${BLUE}7. Checking Supabase status...${NC}"
if docker ps | grep -q supabase; then
    echo -e "${GREEN}   ✓ Supabase containers are running${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep supabase
else
    echo -e "${YELLOW}   ⚠ Supabase is not running${NC}"
fi

# 8. Check port availability (only if Supabase not running)
if ! docker ps | grep -q supabase; then
    echo -e "${BLUE}8. Checking port availability...${NC}"
    PORTS=(54321 54322 54323 54324)
    for PORT in "${PORTS[@]}"; do
        if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${RED}   ✗ Port $PORT is already in use${NC}"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        else
            echo -e "${GREEN}   ✓ Port $PORT is available${NC}"
        fi
    done
fi

# 9. Check Docker resources
echo -e "${BLUE}9. Checking Docker resources...${NC}"
if [ "$(uname)" == "Darwin" ] || [ "$(uname)" == "Linux" ]; then
    DOCKER_MEM=$(docker info 2>/dev/null | grep "Total Memory" | awk '{print $3}')
    if [ ! -z "$DOCKER_MEM" ]; then
        echo -e "${GREEN}   ✓ Docker memory allocated: ${DOCKER_MEM}${NC}"
    fi
fi

# 10. Check startup script
echo -e "${BLUE}10. Checking startup script...${NC}"
if [ -f "scripts/start-supabase.sh" ]; then
    echo -e "${GREEN}   ✓ Startup script exists${NC}"

    # Check for enhanced features
    if grep -q "start_with_retry" scripts/start-supabase.sh; then
        echo -e "${GREEN}   ✓ Enhanced retry logic present${NC}"
    fi

    if grep -q "Pre-flight" scripts/start-supabase.sh; then
        echo -e "${GREEN}   ✓ Pre-flight checks present${NC}"
    fi
else
    echo -e "${RED}   ✗ Startup script missing${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Summary
echo ""
echo "=========================================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Your Supabase setup is ready. You can now run:"
    echo -e "${BLUE}  make supabase-start${NC}"
    echo ""
    echo "Or to start everything:"
    echo -e "${BLUE}  make all-up${NC}"
else
    echo -e "${YELLOW}⚠️  Found ${ISSUES_FOUND} issue(s)${NC}"
    echo ""
    echo "Please fix the issues above before starting Supabase."
    echo "Most issues will be auto-fixed by running:"
    echo -e "${BLUE}  make supabase-start${NC}"
    echo ""
    echo "For more help, see:"
    echo "  - SUPABASE_TROUBLESHOOTING.md"
    echo "  - SUPABASE_STARTUP_FIXES_APPLIED.md"
fi
echo "=========================================="
echo ""

exit $ISSUES_FOUND
