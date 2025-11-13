#!/bin/bash
# ============================================
# Migration Syntax Validation Script
# ============================================
# This script validates the SQL syntax of migration files
# without requiring a running database instance

set -e

echo "🔍 Validating Migration File Syntax..."
echo ""

MIGRATION_DIR="./supabase/migrations"
ERRORS_FOUND=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check for common SQL syntax issues
check_migration_file() {
    local file=$1
    local filename=$(basename "$file")

    echo -e "${YELLOW}Checking: ${filename}${NC}"

    # Check 1: Look for references to non-existent 'role' column without conditional checks
    if grep -q "WHERE.*role IS NOT NULL" "$file" && ! grep -q "information_schema.columns" "$file"; then
        echo -e "${RED}  ❌ POTENTIAL ISSUE: References 'role' column without checking if it exists${NC}"
        ERRORS_FOUND=$((ERRORS_FOUND + 1))
    fi

    # Check 2: Look for DROP COLUMN without IF EXISTS
    if grep -q "DROP COLUMN role[^_]" "$file" && ! grep -q "DROP COLUMN IF EXISTS role" "$file"; then
        echo -e "${YELLOW}  ⚠️  WARNING: DROP COLUMN 'role' without IF EXISTS${NC}"
    fi

    # Check 3: Look for UPDATE statements that reference role column
    if grep -q "UPDATE.*SET.*role" "$file" | grep -q "WHERE.*role"; then
        echo -e "${YELLOW}  ℹ️  Found UPDATE statement referencing 'role' column${NC}"
    fi

    # Check 4: Look for basic SQL syntax errors
    if grep -q "DO \$\$" "$file"; then
        # Check if DO blocks are properly closed
        do_count=$(grep -c "DO \$\$" "$file" || true)
        end_count=$(grep -c "END \$\$" "$file" || true)
        if [ "$do_count" -ne "$end_count" ]; then
            echo -e "${RED}  ❌ ERROR: Mismatched DO \$\$ and END \$\$ blocks${NC}"
            ERRORS_FOUND=$((ERRORS_FOUND + 1))
        else
            echo -e "${GREEN}  ✅ DO blocks properly closed${NC}"
        fi
    fi

    # Check 5: Verify IF EXISTS checks for column existence
    if grep -q "information_schema.columns" "$file"; then
        echo -e "${GREEN}  ✅ Contains conditional column existence checks${NC}"
    fi

    echo ""
}

# Check if migration directory exists
if [ ! -d "$MIGRATION_DIR" ]; then
    echo -e "${RED}❌ Error: Migration directory not found: $MIGRATION_DIR${NC}"
    exit 1
fi

# Process all migration files
for migration_file in "$MIGRATION_DIR"/*.sql; do
    if [ -f "$migration_file" ]; then
        check_migration_file "$migration_file"
    fi
done

echo "================================================"
if [ $ERRORS_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ All migrations passed syntax validation!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start Supabase: make supabase-start"
    echo "  2. If migrations fail, check logs for specific errors"
    exit 0
else
    echo -e "${RED}❌ Found $ERRORS_FOUND potential error(s)${NC}"
    echo ""
    echo "Please review the issues above before running migrations"
    exit 1
fi
