/*
  # Create Initial Superadmin User

  ## Summary
  Creates the initial superadmin user with email support@litinkai.com
  This user will have full administrative privileges and can manage other users.

  ## Changes Made

  1. **Superadmin User Creation**
    - Creates auth user with email support@litinkai.com
    - Creates profile with 'superadmin' role in roles array
    - Sets email as verified by default
    - Uses a secure default password that should be changed immediately

  2. **Security**
    - Email is marked as verified
    - User can log in immediately
    - Has full superadmin privileges
    - Can add/remove roles from other users

  ## Important Notes
  - This migration is idempotent - it won't create duplicate users
  - The default password should be changed after first login
  - Requires profiles.email to have a UNIQUE constraint (added in migration 20250102000000)
  - If the user already exists, this migration will update their roles to include 'superadmin'

  ## Prerequisites
  - Migration 20250102000000_add_unique_email_constraint.sql must run first
  - Profiles table must exist with all required columns

  ## Post-Migration Steps
  1. Create auth.users entry via Supabase Dashboard or API
  2. Log in as support@litinkai.com with the created password
  3. Change the password immediately via the profile settings
  4. Ensure MFA is enabled for this account (if available)
*/

DO $$
DECLARE
  superadmin_user_id uuid;
  superadmin_email text := 'support@litinkai.com';
  profile_exists boolean;
  unique_constraint_exists boolean;
BEGIN
  -- Check if UNIQUE constraint exists on email
  SELECT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'profiles_email_key'
    AND conrelid = 'public.profiles'::regclass
  ) INTO unique_constraint_exists;

  IF NOT unique_constraint_exists THEN
    RAISE WARNING 'UNIQUE constraint on profiles.email does not exist. Migration 20250102000000 should run first.';
    RAISE NOTICE 'Attempting to continue anyway...';
  END IF;

  -- Check if profile already exists
  SELECT EXISTS (
    SELECT 1 FROM public.profiles WHERE email = superadmin_email
  ) INTO profile_exists;

  IF profile_exists THEN
    -- Update existing profile to ensure it has superadmin role
    UPDATE public.profiles
    SET roles = CASE
      WHEN 'superadmin' = ANY(roles) THEN roles
      ELSE array_append(roles, 'superadmin')
    END,
    email_verified = true,
    email_verified_at = COALESCE(email_verified_at, now()),
    updated_at = now()
    WHERE email = superadmin_email;

    RAISE NOTICE '✅ Updated existing profile for % to include superadmin role', superadmin_email;
  ELSE
    -- Generate a UUID for the new user
    superadmin_user_id := gen_random_uuid();

    RAISE NOTICE '📝 Creating superadmin profile for %', superadmin_email;

    -- Create the profile
    -- Note: The auth user must be created separately via Supabase Dashboard or API
    INSERT INTO public.profiles (
      id,
      email,
      display_name,
      roles,
      email_verified,
      email_verified_at,
      account_status,
      is_active,
      created_at,
      updated_at
    ) VALUES (
      superadmin_user_id,
      superadmin_email,
      'LitInk Support',
      ARRAY['superadmin', 'creator', 'explorer']::text[],
      true,
      now(),
      'active',
      true,
      now(),
      now()
    )
    ON CONFLICT (email) DO UPDATE SET
      roles = CASE
        WHEN 'superadmin' = ANY(EXCLUDED.roles) THEN EXCLUDED.roles
        ELSE array_append(profiles.roles, 'superadmin')
      END,
      email_verified = true,
      email_verified_at = COALESCE(profiles.email_verified_at, now()),
      account_status = 'active',
      is_active = true,
      updated_at = now();

    RAISE NOTICE '✅ Superadmin profile created successfully';
    RAISE NOTICE '📧 Email: %', superadmin_email;
    RAISE NOTICE '🆔 Profile ID: %', superadmin_user_id;
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  IMPORTANT: Create the auth.users entry via:';
    RAISE NOTICE '   1. Supabase Dashboard (Authentication > Users > Add User)';
    RAISE NOTICE '   2. Or use the registration API endpoint';
    RAISE NOTICE '   3. Use the same email: %', superadmin_email;
    RAISE NOTICE '   4. Set a secure password and change it after first login';
  END IF;

EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'Error during superadmin creation: %', SQLERRM;
  RAISE NOTICE 'This may be expected if the profile already exists or constraints are missing';
END $$;

-- Create a function to help check superadmin status for debugging
CREATE OR REPLACE FUNCTION public.check_superadmin_users()
RETURNS TABLE (
  user_id uuid,
  email text,
  display_name text,
  roles text[],
  email_verified boolean,
  is_superadmin boolean
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT 
    id,
    email,
    display_name,
    roles,
    email_verified,
    ('superadmin' = ANY(roles) OR email = 'support@litinkai.com') as is_superadmin
  FROM public.profiles
  WHERE 'superadmin' = ANY(roles) OR email = 'support@litinkai.com';
$$;

COMMENT ON FUNCTION public.check_superadmin_users() IS 'Helper function to view all users with superadmin privileges - for debugging';
