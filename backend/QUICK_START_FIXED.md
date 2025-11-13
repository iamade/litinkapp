# Quick Start - Database Migrations Fixed ✅

## What Was Fixed

The database migration error **"column 'role' does not exist"** has been resolved.

**The Problem:**
- Migrations tried to migrate data from a `role` column that never existed
- The database schema has always used `roles` (array) not `role` (single)

**The Solution:**
- Added conditional checks to only migrate if the old column exists
- Made all migrations more robust and idempotent
- No changes to the final database schema

---

## How to Start Your Database Now

### Method 1: Using Make Commands (Recommended)

```bash
cd backend

# Start everything (Supabase + Application)
make all-up

# Or start just Supabase
make supabase-start

# Or start just your application (after Supabase is running)
make dev
```

### Method 2: Step by Step

```bash
cd backend

# 1. Stop any existing instances
make supabase-stop

# 2. Start fresh
make supabase-start

# 3. Wait for migrations to complete (should succeed now!)

# 4. Access Supabase Studio
open http://127.0.0.1:54323
```

---

## Expected Output

When you run `make all-up` or `make supabase-start`, you should now see:

```
🚀 Starting Supabase Local Services...

📡 Creating Docker network...
Network already exists
🗄️  Starting Supabase local services...
Starting database...
Initialising schema...
Seeding globals from roles.sql...
Applying migration 20250101000000_create_initial_schema.sql...
Applying migration 20251010185047_20251010183000_remove_scripts_unique_constraint.sql...
Applying migration 20251013085142_fix_usage_logs_insert_policy.sql...
...
(all migrations should complete successfully)
...
✅ Supabase services started successfully!

📊 Supabase Local Services:
   Studio URL:    http://127.0.0.1:54323
   API URL:       http://127.0.0.1:54321
   DB URL:        postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

**No more errors about "column 'role' does not exist"!** ✅

---

## Verify Everything Works

### 1. Check Supabase Studio

Open http://127.0.0.1:54323 and verify:
- ✅ All tables are created
- ✅ `profiles` table has `roles` column (TEXT array)
- ✅ No single `role` column exists
- ✅ RLS policies are enabled

### 2. Run SQL Validation

In Supabase Studio SQL Editor, run:

```sql
-- Should return 'roles' column info
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'profiles' AND column_name = 'roles';

-- Should return 0 (no single 'role' column)
SELECT COUNT(*)
FROM information_schema.columns
WHERE table_name = 'profiles' AND column_name = 'role';

-- Should show RLS is enabled
SELECT rowsecurity FROM pg_tables WHERE tablename = 'profiles';
```

### 3. Test Your Application

```bash
# Start your frontend
cd ../  # Go to project root
npm run dev

# Your app should now connect to the database successfully!
```

---

## Common Issues & Solutions

### Issue: "Docker is not running"
**Solution:**
```bash
# Start Docker Desktop
# Then run: make supabase-start
```

### Issue: "Port already in use"
**Solution:**
```bash
# Stop existing Supabase instance
make supabase-stop

# Wait a few seconds
sleep 5

# Try again
make supabase-start
```

### Issue: Still seeing migration errors
**Solution:**
```bash
# Reset everything and start fresh
make supabase-stop
cd supabase
supabase db reset  # WARNING: Deletes all data
cd ..
make supabase-start
```

---

## What Changed in the Codebase

### Modified Files:

1. **backend/supabase/migrations/20251017150420_20251017150000_complete_role_migration_and_cleanup.sql**
   - Added conditional checks for column existence
   - Migration now safely handles databases with or without the old 'role' column

2. **backend/supabase/migrations/20251015075825_add_multi_role_system_and_ownership_tracking.sql**
   - Made constraint addition idempotent
   - Won't fail if constraint already exists

### New Files:

1. **backend/validate_migration_syntax.sh**
   - Validates migration syntax without running them
   - Useful for pre-deployment checks

2. **backend/MIGRATION_FIX_APPLIED.md**
   - Complete documentation of the fix
   - Technical details and impact analysis

---

## Database Schema Summary

After all migrations, your `profiles` table will have:

```sql
CREATE TABLE profiles (
  id UUID PRIMARY KEY,
  email TEXT NOT NULL,
  display_name TEXT,
  avatar_url TEXT,
  bio TEXT,
  roles TEXT[] NOT NULL DEFAULT ARRAY['explorer'],  -- ✅ Array, not single value
  preferred_mode TEXT DEFAULT 'explorer',
  onboarding_completed JSONB DEFAULT '{}',
  email_verified BOOLEAN DEFAULT FALSE,
  email_verified_at TIMESTAMPTZ,
  verification_token_sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  -- Constraints
  CHECK (array_length(roles, 1) > 0),
  CHECK (roles <@ ARRAY['explorer', 'author', 'admin', 'superadmin'])
);
```

**Key Points:**
- ✅ `roles` is a TEXT array (can hold multiple roles)
- ✅ Valid roles: 'explorer', 'author', 'admin', 'superadmin'
- ✅ Default role for new users: 'explorer'
- ✅ Users must have at least one role
- ✅ No single `role` column exists or is needed

---

## Next Steps

1. ✅ **Start your database:** `make all-up`
2. ✅ **Verify it works:** Check http://127.0.0.1:54323
3. ✅ **Run your app:** `npm run dev`
4. ✅ **Build for production:** `npm run build`

---

## Need Help?

If you encounter any issues:

1. **Check the detailed documentation:** `backend/MIGRATION_FIX_APPLIED.md`
2. **View logs:** `make supabase-logs`
3. **Validate migrations:** `./backend/validate_migration_syntax.sh`
4. **Reset if needed:** `make supabase-stop` then `make supabase-start`

---

**Status: ✅ Ready to Use!**

Your database migrations are now fixed and ready to run successfully.
