# Testing User Registration After Fixes

## Quick Start

### Option 1: Automated Test Script
```bash
cd backend
python test_registration_fix.py
```

### Option 2: Manual Testing with curl
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "display_name": "Test User",
    "roles": ["explorer"]
  }'
```

### Option 3: Frontend Testing
1. Start your frontend application
2. Navigate to the registration page
3. Fill in the registration form
4. Submit and watch for errors

## Expected Results

### ✅ Successful Registration
```json
{
  "id": "uuid-here",
  "email": "test@example.com",
  "display_name": "Test User",
  "roles": ["explorer"],
  "email_verified": false,
  "email_verified_at": null,
  "created_at": "2025-10-17T...",
  "updated_at": "2025-10-17T...",
  "is_active": true,
  "is_verified": false
}
```

**Status Code:** 201 Created

### ❌ Old Error (Should No Longer Occur)
```json
{
  "detail": "Database error saving new user. Please try again."
}
```

**Status Code:** 400 Bad Request

## Verifying Fixes Applied

### 1. Check RLS Policy
Run this SQL in Supabase SQL Editor:
```sql
SELECT policyname, cmd, with_check
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'profiles' AND cmd = 'INSERT';
```

**Expected Output:**
```
policyname: "Users can insert own profile or service role can insert any"
cmd: "INSERT"
with_check: "((auth.uid() = id) OR ((auth.jwt() ->> 'role'::text) = 'service_role'::text))"
```

### 2. Check Security Functions
Run this SQL in Supabase SQL Editor:
```sql
SELECT
  p.proname as function_name,
  CASE WHEN p.prosecdef THEN 'SECURITY DEFINER' ELSE 'SECURITY INVOKER' END as security,
  (SELECT setting FROM unnest(p.proconfig) setting WHERE setting LIKE 'search_path=%') as search_path
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
  AND p.proname IN ('add_role_to_user', 'remove_role_from_user',
                    'can_request_verification_email', 'update_verification_token_sent',
                    'is_superadmin', 'set_email_verified_at')
ORDER BY p.proname;
```

**Expected Output:**
All functions should show:
- `security: "SECURITY DEFINER"`
- `search_path: "search_path=\"\""`

### 3. Check Migrations Applied
In Supabase Dashboard:
1. Go to Database → Migrations
2. Look for these migrations:
   - `20251017140000_fix_profiles_rls_for_registration`
   - `20251017140100_fix_security_definer_search_path`
3. Verify both show as "Applied"

## Troubleshooting

### Issue: "Database error saving new user" Still Occurs

**Cause:** Migrations not applied to database

**Solution:**
```bash
# If using Supabase CLI locally
cd backend/supabase
supabase db push

# If using hosted Supabase
# Apply migrations via Supabase Dashboard → Database → Migrations
```

### Issue: "Connection refused" or "Network error"

**Cause:** Backend not running

**Solution:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Issue: "Email already registered"

**Cause:** Test email already exists

**Solution:**
- Use a different email address
- Or delete the test user from Supabase dashboard
- Or use a unique email like: `test+${Date.now()}@example.com`

### Issue: "Invalid service role key"

**Cause:** Wrong environment variable

**Solution:**
1. Check `backend/.env` file
2. Verify `SUPABASE_SERVICE_ROLE_KEY` is set (NOT the anon key)
3. Get the correct key from Supabase Dashboard → Settings → API
4. Look for "service_role" secret key (starts with `eyJ...`)

## Complete Registration Flow Test

### Step 1: Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "SecurePass123!",
    "display_name": "Test User",
    "roles": ["explorer"]
  }'
```

**Expected:** Status 201, user created

### Step 2: Check Email
- Check your email inbox for verification link
- Click the verification link
- Should redirect to your app with success message

### Step 3: Verify in Database
```sql
SELECT id, email, email_verified, email_verified_at
FROM public.profiles
WHERE email = 'testuser@example.com';
```

**Expected:** `email_verified = true`, `email_verified_at` has timestamp

### Step 4: Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "SecurePass123!"
  }'
```

**Expected:** Status 200, access token returned

## Security Advisor Check

After applying fixes, check Supabase Security Advisor:

1. Go to Supabase Dashboard
2. Navigate to Database → Reports
3. Click on "Security Advisor" tab
4. Look for "Function Search Path Mutable" warnings
5. **Expected:** No warnings for our functions

## Success Criteria

✅ Registration endpoint returns 201 Created
✅ User profile created in profiles table
✅ Verification email sent
✅ RLS policy allows service role inserts
✅ All SECURITY DEFINER functions have search_path=""
✅ No security warnings in Supabase dashboard
✅ Login works after email verification

## Additional Tests

### Test Email Verification Rate Limiting
```bash
# Try resending verification email multiple times quickly
curl -X POST http://localhost:8000/api/v1/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com"}'
```

**Expected:** After 5 minutes cooldown, should get 429 error

### Test Role Management
```bash
# This should work after user is authenticated
# Add author role to user
curl -X POST http://localhost:8000/api/v1/users/me/roles \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"role": "author"}'
```

**Expected:** User now has ["explorer", "author"] roles

## Notes

- Email verification is **required** before login
- Default role is "explorer" for new users
- Users can have multiple roles simultaneously
- Service role key must be kept secret (backend only)
- All profile operations are protected by RLS

## Support

If issues persist:
1. Check backend logs for detailed errors
2. Check Supabase logs in dashboard
3. Verify all environment variables are set
4. Confirm migrations are applied
5. Review the USER_REGISTRATION_FIX_SUMMARY.md document
