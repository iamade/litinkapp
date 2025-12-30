# Seed Data Schema Fix - Summary

## Problem Description

The Supabase local database was failing to start due to schema mismatches between the database migrations and the seed data file. The errors indicated missing columns:

1. **Characters table error**: `column "description" of relation "characters" does not exist`
2. **Scripts table error**: `column "book_id" of relation "scripts" does not exist`

## Root Cause Analysis

The database schema and seed data were using different column naming conventions:

### Characters Table Mismatch
- **Schema columns**: `physical_description`, `personality`, `archetypes`, `plot_overview_id` (NOT NULL)
- **Seed data columns**: `description`, `traits` (simple format)
- **Missing requirement**: Seed data didn't include required `plot_overview_id` and `user_id`

### Scripts Table Mismatch
- **Schema columns**: `chapter_id`, `script`, `script_story_type`, `metadata`
- **Seed data columns**: `book_id`, `content`, `story_type`, `script_metadata`

## Solution Implemented

### 1. New Migration File: `20251113225537_add_seed_compatibility_columns.sql`

This migration adds backward-compatible columns to support both the application schema and seed data:

#### Characters Table Changes:
- ✅ Added `description` column (TEXT, nullable)
- ✅ Added `traits` column (JSONB, nullable)
- ✅ Made `plot_overview_id` nullable to support seed data without plot overviews

#### Scripts Table Changes:
- ✅ Added `book_id` column (UUID, references books table)
- ✅ Added `content` column (TEXT, nullable)
- ✅ Added `story_type` column (TEXT, nullable)
- ✅ Added `script_metadata` column (JSONB, nullable)

#### Synchronization Features:
- ✅ Created trigger function `sync_script_columns()` to keep dual columns in sync
- ✅ Auto-syncs `content` ↔ `script` columns
- ✅ Auto-syncs `script_metadata` ↔ `metadata` columns
- ✅ Added performance indexes on new columns

### 2. Updated Seed Data File: `supabase/seed.sql`

#### Added Plot Overviews Section (NEW):
```sql
-- Section 6: Create Sample Plot Overviews
-- Creates 3 plot overviews for the sample books
```

#### Updated Characters Section:
- Now includes `plot_overview_id` references
- Includes `user_id` for all characters
- Maintains simplified `description` and `traits` columns
- Properly links to plot overviews

#### Updated Scripts Section:
- Renumbered to section 8
- Maintains existing structure with both `book_id` and `chapter_id`

## Files Modified

1. **Created**: `backend/supabase/migrations/20251113225537_add_seed_compatibility_columns.sql`
   - Adds compatibility columns
   - Creates sync triggers
   - Adds performance indexes

2. **Modified**: `backend/supabase/seed.sql`
   - Added plot_overviews section
   - Updated characters with required foreign keys
   - Updated section numbering
   - Enhanced success message

## Testing Instructions

### Option 1: Using Supabase CLI (If Available)
```bash
cd backend/supabase
supabase db reset
```

### Option 2: Using Make Commands
```bash
cd backend
make supabase-stop
make supabase-start
```

### Expected Results

After applying the fix, you should see:

1. ✅ All migrations apply successfully
2. ✅ Seed data loads without errors
3. ✅ Test users created (5 users with different roles)
4. ✅ Sample books created (3 books)
5. ✅ Sample chapters created (4 chapters)
6. ✅ Sample plot overviews created (3 plot overviews)
7. ✅ Sample characters created (4 characters)
8. ✅ Sample scripts created (1 script)
9. ✅ Subscriptions assigned to all test users

### Test Users Available

All users have the password: `password123`

- `superadmin@litinkai.local` - Superadmin with Pro subscription
- `admin@litinkai.local` - Admin with Pro subscription
- `creator@litinkai.local` - Creator with Basic subscription
- `user@litinkai.local` - Regular user with Free subscription
- `premium@litinkai.local` - Premium user with Pro subscription

## Benefits of This Approach

1. **Backward Compatibility**: Existing application code continues to work
2. **Seed Data Support**: Test data can use simplified column names
3. **Automatic Synchronization**: Trigger keeps dual columns in sync
4. **No Breaking Changes**: All changes are additive (new nullable columns)
5. **Performance**: Indexes added for efficient queries on new columns
6. **Flexibility**: Supports both detailed schema and simple seed data format

## Future Considerations

1. **Column Consolidation**: Consider standardizing on one naming convention
2. **Seed Data Enhancement**: Add more comprehensive test data
3. **Schema Documentation**: Update API docs to reflect available columns
4. **Application Updates**: Gradually migrate code to use primary columns

## Notes

- The migration uses `IF NOT EXISTS` for all operations, making it safe to re-run
- All new columns are nullable to avoid breaking existing data
- The trigger function handles null values gracefully
- Foreign key constraints maintain referential integrity
- RLS policies don't need changes as they inherit from parent tables

## Technical Details

### Trigger Function Logic
```sql
-- When content is set but script is empty, copy content to script
-- When script is set but content is empty, copy script to content
-- Same logic applies to script_metadata and metadata
```

### Index Strategy
- `idx_scripts_book_id` - For queries filtering by book_id
- Existing indexes remain in place
- Composite indexes not needed for seed data queries

## Verification Steps

After reset, verify in Supabase Studio (http://127.0.0.1:54323):

1. Check `profiles` table has 5 test users
2. Check `user_subscriptions` table has 5 active subscriptions
3. Check `books` table has 3 sample books
4. Check `chapters` table has 4 chapters
5. Check `plot_overviews` table has 3 entries
6. Check `characters` table has 4 characters with proper foreign keys
7. Check `scripts` table has 1 sample script

## Troubleshooting

If you still encounter errors:

1. **Check migration order**: Ensure new migration is last in alphabetical/timestamp order
2. **Verify Docker is running**: `docker ps` should show Supabase containers
3. **Check logs**: `cd backend/supabase && supabase status`
4. **Manual reset**: Stop and remove all containers, restart fresh
5. **Verify seed.sql syntax**: Check for SQL syntax errors in the file

## Support

For issues or questions:
- Check logs: `backend/scripts/view-local-logs.sh`
- Review migration files in `backend/supabase/migrations/`
- Consult `backend/supabase-local-setup/` documentation
