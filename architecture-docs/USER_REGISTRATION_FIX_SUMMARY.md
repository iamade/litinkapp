# User Registration Fix Summary

## Problem Identified

The user registration was failing with the error:
```json
{"detail":"Database error saving new user"}
```

Additionally, Supabase Security Advisor was reporting:
```
Function `public.add_role_to_user` has a role mutable search_path
```

## Root Causes

### 1. RLS Policy Issue (Primary Cause)
The profiles table had an INSERT policy that required:
```sql
WITH CHECK (auth.uid() = id)
```

When the backend uses the **service role key** to create user profiles during registration, `auth.uid()` returns `NULL` because the service role doesn't have a user context. This caused all profile insertions to fail.

### 2. Data Format Issue
The registration endpoint was sending:
```python
"verification_token_sent_at": "now()"  # String literal, not a timestamp
```

PostgreSQL expected a proper timestamp value, not the string "now()".

### 3. Security Vulnerability
All SECURITY DEFINER functions lacked the `SET search_path = ''` setting, making them vulnerable to search path manipulation attacks.

## Solutions Applied

### Migration 1: Fix RLS Policy for Registration
**File:** `20251017140000_fix_profiles_rls_for_registration.sql`

**Changes:**
- Dropped the restrictive INSERT policy
- Created a new policy that allows:
  - Authenticated users to insert their own profile (`auth.uid() = id`)
  - Service role to insert any profile (`auth.jwt()->>'role' = 'service_role'`)

**Result:** Backend can now create user profiles during registration using the service role key.

### Migration 2: Fix SECURITY DEFINER Functions
**File:** `20251017140100_fix_security_definer_search_path.sql`

**Functions Fixed:**
1. `add_role_to_user` - Add SET search_path = '', use public.profiles
2. `remove_role_from_user` - Add SET search_path = '', use public.profiles
3. `can_request_verification_email` - Add SET search_path = '', use public.profiles
4. `update_verification_token_sent` - Add SET search_path = '', use public.profiles
5. `is_superadmin` - Add SET search_path = '', use public.profiles
6. `set_email_verified_at` - Add SET search_path = '' (trigger function)

**Result:** All functions now meet Supabase security requirements and are protected against search path attacks.

### Code Fix: Registration Endpoint
**File:** `backend/app/api/v1/auth.py`

**Changes:**
```python
# Before
from datetime import timedelta
"verification_token_sent_at": "now()"

# After
from datetime import timedelta, datetime, timezone
"verification_token_sent_at": datetime.now(timezone.utc).isoformat()
```

**Result:** Proper timestamp is now sent to the database.

## Verification

### Database State After Fixes

1. **RLS Policy:**
```sql
Policy: "Users can insert own profile or service role can insert any"
WITH CHECK: ((auth.uid() = id) OR ((auth.jwt() ->> 'role') = 'service_role'))
```

2. **SECURITY DEFINER Functions:**
All 6 functions now have `search_path=""` set:
- ✅ add_role_to_user
- ✅ remove_role_from_user
- ✅ can_request_verification_email
- ✅ update_verification_token_sent
- ✅ is_superadmin
- ✅ set_email_verified_at

## Testing User Registration

The registration flow should now work correctly:

1. User submits registration form
2. Backend calls Supabase Auth to create auth.users record
3. Supabase sends verification email
4. Backend creates profile in public.profiles table (using service role)
5. User receives verification email
6. User clicks verification link
7. Email is marked as verified

## Next Steps

1. **Test Registration:**
   - Try registering a new user
   - Verify no "Database error saving new user" occurs
   - Check that profile is created in profiles table

2. **Verify Security:**
   - Check Supabase Security Advisor dashboard
   - Confirm no more "mutable search_path" warnings
   - Verify all functions show "SECURITY DEFINER with search_path=''"

3. **Test Email Verification:**
   - Register a new user
   - Check email for verification link
   - Click link and verify email gets marked as verified
   - Try logging in before and after verification

## Important Notes

### Why Service Role Can Insert Profiles

The service role key is:
- Only available to the backend (never exposed to frontend)
- Used in trusted server-side code
- Required for the registration flow where we create profiles for newly registered users
- Protected by environment variables

This is a standard pattern in Supabase applications where the backend needs to perform administrative tasks during user registration.

### Security Considerations

1. **Service role key must remain secret** - Never expose it to the frontend
2. **RLS still protects data** - Users can only read/update their own profiles
3. **Search path is secured** - All SECURITY DEFINER functions use empty search_path
4. **Email verification required** - Users must verify email before full access

## Troubleshooting

If registration still fails:

1. **Check backend logs** for detailed error messages
2. **Verify environment variables** are set correctly:
   - SUPABASE_URL
   - SUPABASE_SERVICE_ROLE_KEY (not anon key!)
3. **Check Supabase logs** in the dashboard
4. **Verify migrations applied** by checking the profiles table policies
5. **Test with curl** to isolate frontend vs backend issues

### Test with curl:
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

## Summary

✅ **Fixed RLS policy** to allow service role insertions
✅ **Fixed SECURITY DEFINER functions** to use empty search_path
✅ **Fixed data formatting** in registration endpoint
✅ **Eliminated security vulnerabilities** reported by Supabase

User registration should now work correctly without database errors!
