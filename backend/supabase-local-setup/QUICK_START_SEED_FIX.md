# Quick Start: Testing the Seed Data Fix

## What Was Fixed

Your Supabase database was failing to start because the seed data file was trying to insert data into columns that didn't exist. This has been fixed by:

1. ✅ Adding missing columns to the database schema
2. ✅ Adding plot_overviews data to the seed file
3. ✅ Updating character and script data with proper foreign keys
4. ✅ Creating automatic column synchronization triggers

## How to Test the Fix

### Step 1: Stop Any Running Services

```bash
cd backend
make supabase-stop
make down
```

### Step 2: Start Supabase with the New Migration

```bash
cd backend
make supabase-start
```

This will:
- Start Supabase local services
- Apply all migrations including the new compatibility migration
- Load the updated seed data
- Create 5 test users, 3 books, 4 chapters, 3 plot overviews, 4 characters, and 1 script

### Step 3: Verify Success

You should see output like:

```
✅ Seed data created successfully!
📧 Test Users:
   - superadmin@litinkai.local (password: password123)
   - admin@litinkai.local (password: password123)
   - creator@litinkai.local (password: password123)
   - user@litinkai.local (password: password123)
   - premium@litinkai.local (password: password123)
📚 Sample books and chapters have been created
📖 Sample plot overviews have been created
🎭 Sample characters have been created
📝 Sample scripts have been created
💳 Subscriptions assigned to all test users
```

### Step 4: Check Supabase Studio

Open your browser to: http://127.0.0.1:54323

Login with credentials shown in the terminal, then verify:

1. **Profiles table**: Should have 5 users
2. **Books table**: Should have 3 sample books
3. **Chapters table**: Should have 4 chapters
4. **Plot_overviews table**: Should have 3 plot overviews (NEW!)
5. **Characters table**: Should have 4 characters
6. **Scripts table**: Should have 1 sample script

### Step 5: Start Your Application (Optional)

```bash
cd backend
make dev
```

This starts:
- FastAPI backend
- Redis
- Celery workers

Your API will be available at: http://localhost:8000

## What If It Still Fails?

### Error: "supabase: command not found"

The Supabase CLI needs to be installed. From your error message, it seems you're running this from a different environment. Try:

```bash
# On macOS
brew install supabase/tap/supabase

# On Linux/WSL
curl -fsSL https://raw.githubusercontent.com/supabase/cli/main/install.sh | bash

# Or using npm
npm install -g supabase
```

### Error: "Docker is not running"

Make sure Docker Desktop is running:

```bash
docker ps
```

Should show running containers.

### Error: Migration still fails

Check the migration order:

```bash
ls -la backend/supabase/migrations/
```

The new migration `20251113225537_add_seed_compatibility_columns.sql` should be near the end.

### Manual Reset Method

If the automatic reset isn't working:

```bash
cd backend/supabase
supabase stop
supabase start
```

## Files Changed

### New Files
1. `backend/supabase/migrations/20251113225537_add_seed_compatibility_columns.sql`
   - Migration that adds compatibility columns

2. `backend/SEED_DATA_FIX_SUMMARY.md`
   - Comprehensive documentation of changes

3. `backend/QUICK_START_SEED_FIX.md` (this file)
   - Quick testing guide

### Modified Files
1. `backend/supabase/seed.sql`
   - Added plot_overviews section
   - Updated characters with proper foreign keys
   - Fixed section numbering

## Test Users for Development

All test users have password: `password123`

| Email | Role | Subscription | Use Case |
|-------|------|-------------|----------|
| superadmin@litinkai.local | Superadmin | Pro | Admin panel testing |
| admin@litinkai.local | Admin | Pro | Admin features |
| creator@litinkai.local | Creator | Basic | Content creation |
| user@litinkai.local | User | Free | Basic user experience |
| premium@litinkai.local | Premium | Pro | Premium features |

## Sample Data Created

### Books
1. **The AI Chronicles** (sci-fi, by creator)
2. **Space Adventures** (sci-fi, by creator)
3. **Mystery in the Mansion** (mystery, by premium user)

### Characters
1. **ARIA** - AI protagonist (The AI Chronicles)
2. **Dr. Sarah Chen** - Supporting character (The AI Chronicles)
3. **Captain Marcus Steel** - Space commander (Space Adventures)
4. **Lady Catherine Blackwood** - Detective (Mystery in the Mansion)

## Next Steps

After verifying the fix works:

1. ✅ Test user registration and login
2. ✅ Test book upload functionality
3. ✅ Test character generation
4. ✅ Test script generation
5. ✅ Test the full content pipeline

## Need Help?

Check these resources:

- **Full fix details**: `backend/SEED_DATA_FIX_SUMMARY.md`
- **Migration file**: `backend/supabase/migrations/20251113225537_add_seed_compatibility_columns.sql`
- **Seed data**: `backend/supabase/seed.sql`
- **Supabase status**: Run `cd backend/supabase && supabase status`

## Success Indicators

✅ No error messages during startup
✅ See "Seed data created successfully!" message
✅ 5 test users visible in Supabase Studio
✅ Books, characters, and scripts visible in their tables
✅ Application starts without database errors

---

**Note**: The fix maintains full backward compatibility. Your application code doesn't need any changes. The migration simply adds the columns that the seed data was expecting.
