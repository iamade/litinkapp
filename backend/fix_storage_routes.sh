#!/bin/bash
# Fix routes that need BOTH session (database) and supabase_client (storage)

# Books routes - needs both for storage operations
echo "Fixing books/routes.py - adding back supabase_client for storage..."
sed -i '' 's/session: AsyncSession = Depends(get_session),  # For storage/supabase_client: Client = Depends(get_supabase),  # For storage/g' app/api/routes/books/routes.py

# AI routes - check if it needs supabase
echo "Checking ai/routes.py..."
if grep -q "supabase_client" app/api/routes/ai/routes.py; then
    echo "AI routes still uses supabase_client in function bodies - needs manual review"
fi

# NFTs and Badges - simple table operations, can be fully SQLAlchemy
echo "NFTs and Badges routes need full refactor (table operations -> SQLAlchemy)"

echo "✅ Partial fix complete. Some files need manual refactoring."
