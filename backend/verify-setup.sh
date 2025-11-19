#!/bin/bash

# Verification script for local development setup
# Run this after completing the setup to verify everything is configured correctly

echo "================================"
echo "Litinkai Setup Verification"
echo "================================"
echo ""

ERRORS=0

# Check 1: .env.local exists
echo "✓ Checking .env.local file..."
if [ -f ".envs/.env.local" ]; then
    echo "  ✅ .env.local exists"
    
    # Check for critical variables
    if grep -q "DEBUG=" ".envs/.env.local"; then
        echo "  ✅ DEBUG variable found"
    else
        echo "  ❌ DEBUG variable missing"
        ERRORS=$((ERRORS + 1))
    fi
    
    if grep -q "ENVIRONMENT=" ".envs/.env.local"; then
        echo "  ✅ ENVIRONMENT variable found"
    else
        echo "  ❌ ENVIRONMENT variable missing"
        ERRORS=$((ERRORS + 1))
    fi
    
    if grep -q "SUPABASE_URL=" ".envs/.env.local"; then
        echo "  ✅ SUPABASE_URL found"
    else
        echo "  ❌ SUPABASE_URL missing"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  ❌ .env.local NOT FOUND"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check 2: Migration file exists
echo "✓ Checking migration file..."
if [ -f "supabase/migrations/20251119000000_migrate_author_to_creator_role.sql" ]; then
    echo "  ✅ Author to Creator migration exists"
else
    echo "  ❌ Migration file NOT FOUND"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check 3: Docker network
echo "✓ Checking Docker network..."
if docker network inspect litinkai_local_nw > /dev/null 2>&1; then
    echo "  ✅ Docker network exists"
else
    echo "  ⚠️  Docker network doesn't exist (run: docker network create litinkai_local_nw)"
fi
echo ""

# Check 4: Supabase CLI
echo "✓ Checking Supabase CLI..."
if command -v supabase > /dev/null 2>&1; then
    echo "  ✅ Supabase CLI installed"
    cd supabase
    if supabase status > /dev/null 2>&1; then
        echo "  ✅ Supabase is running"
    else
        echo "  ⚠️  Supabase not running (run: make supabase-start)"
    fi
    cd ..
else
    echo "  ⚠️  Supabase CLI not installed"
fi
echo ""

# Check 5: Docker
echo "✓ Checking Docker..."
if command -v docker > /dev/null 2>&1; then
    echo "  ✅ Docker installed"
    if docker info > /dev/null 2>&1; then
        echo "  ✅ Docker is running"
    else
        echo "  ❌ Docker not running"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  ❌ Docker not installed"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check 6: Code changes
echo "✓ Checking code changes..."
if grep -q "redis://redis:6379" "app/core/config.py"; then
    echo "  ✅ Redis URL updated in config.py"
else
    echo "  ❌ Redis URL still uses localhost"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "creator" "app/api/v1/admin.py"; then
    echo "  ✅ Creator role found in admin.py"
else
    echo "  ❌ Creator role not found in admin.py"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Summary
echo "================================"
if [ $ERRORS -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED!"
    echo ""
    echo "You're ready to start development!"
    echo ""
    echo "Next steps:"
    echo "  1. make supabase-start (if not running)"
    echo "  2. ./scripts/update-env-keys.sh"
    echo "  3. make dev"
else
    echo "❌ $ERRORS ERRORS FOUND"
    echo ""
    echo "Please fix the errors above before starting development."
    echo "See SETUP_COMPLETE_NOVEMBER_2024.md for help."
fi
echo "================================"
