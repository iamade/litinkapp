# Migration SQL Syntax Fix - Summary

## Problem
The initial schema migration file `20250101000000_create_initial_schema.sql` contained invalid PostgreSQL syntax that was causing the Supabase startup to fail with the error:

```
ERROR: syntax error at or near "NOT" (SQLSTATE 42601)
At statement: 13
-- Profiles policies
CREATE POLICY IF NOT EXISTS "Users can view own profile"
                 ^
```

## Root Cause
PostgreSQL **does not support** the `IF NOT EXISTS` clause with `CREATE POLICY` statements. This syntax is simply not valid in any PostgreSQL version.

## Solution Applied
Replaced all 29 instances of:
```sql
CREATE POLICY IF NOT EXISTS "policy_name"
  ON table_name ...
```

With the correct idempotent pattern:
```sql
DROP POLICY IF EXISTS "policy_name" ON table_name;
CREATE POLICY "policy_name"
  ON table_name ...
```

## Tables Fixed
The following tables had their RLS policies corrected:
- ✅ profiles (3 policies)
- ✅ books (5 policies)
- ✅ chapters (2 policies)
- ✅ plot_overviews (2 policies)
- ✅ characters (2 policies)
- ✅ scripts (2 policies)
- ✅ video_generations (2 policies)
- ✅ image_generations (2 policies)
- ✅ audio_generations (2 policies)
- ✅ subscription_tiers (2 policies)
- ✅ user_subscriptions (2 policies)
- ✅ usage_logs (3 policies)

**Total: 29 policies fixed**

## Testing Instructions
To verify the fix works:

1. **Stop any running Supabase instance:**
   ```bash
   cd backend
   make supabase-stop
   ```

2. **Start Supabase with the fixed migration:**
   ```bash
   make supabase-start
   ```

3. **Or start everything together:**
   ```bash
   make all-up
   ```

4. **Verify the database schema:**
   - Open Supabase Studio at http://127.0.0.1:54323
   - Check that all tables exist with proper RLS policies
   - Verify no migration errors in the logs

## Why This Fix Works
- `DROP POLICY IF EXISTS` safely removes any existing policy
- `CREATE POLICY` then creates it fresh with correct settings
- This pattern is idempotent - can be run multiple times safely
- PostgreSQL has supported `DROP POLICY IF EXISTS` since version 9.6
- This is the recommended approach for PostgreSQL migrations

## Migration File Location
`backend/supabase/migrations/20250101000000_create_initial_schema.sql`

## Validation Results
- ✅ All invalid `CREATE POLICY IF NOT EXISTS` statements removed
- ✅ All policies now use valid `DROP POLICY IF EXISTS` + `CREATE POLICY` pattern
- ✅ 0 occurrences of invalid syntax remaining
- ✅ Migration file maintains idempotency
- ✅ All RLS security policies preserved

The migration should now run successfully!
