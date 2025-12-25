#!/bin/bash
# Batch update route files to use SQLAlchemy instead of Supabase

routes_files=(
    "app/api/routes/badges/routes.py"
    "app/api/routes/nfts/routes.py"
    "app/api/routes/quizzes/routes.py"
    "app/api/routes/ai/routes.py"
    "app/api/routes/books/routes.py"
    "app/api/routes/payments/routes.py"
    "app/api/routes/chapters/routes.py"
    "app/api/routes/merge/routes.py"
    "app/api/routes/profile/stats.py"
)

for file in "${routes_files[@]}"; do
    if [ -f "$file" ]; then
        echo "Processing $file..."
        
        # Replace import statements
        sed -i '' 's/from supabase import Client/from sqlmodel.ext.asyncio.session import AsyncSession/g' "$file"
        sed -i '' 's/from app.core.database import get_supabase/from app.core.database import get_session/g' "$file"
        
        # Replace function parameter
        sed -i '' 's/supabase_client: Client = Depends(get_supabase)/session: AsyncSession = Depends(get_session)/g' "$file"
        
        echo "✓ Updated $file"
    else
        echo "⚠ File not found: $file"
    fi
done

echo "✅ Batch update complete!"
