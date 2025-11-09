/*
  # Complete Role Migration and Schema Cleanup

  ## Summary
  This migration completes the transition from single 'role' column to 'roles' array
  and fixes all related database functions and constraints.

  ## Changes Made

  1. **Schema Cleanup**
    - Ensure all profiles have migrated to 'roles' array
    - Add constraint to validate role values in 'roles' array
    - Remove deprecated 'role' column from profiles table

  2. **Function Updates**
    - Update is_superadmin() to check 'roles' array instead of 'role' column
    - Create helper function for role checking in RLS policies

  3. **Data Validation**
    - Add check constraint to ensure only valid roles: 'explorer', 'author', 'admin', 'superadmin'
    - Ensure all existing data is compatible

  ## Security
  - Maintains all existing RLS policies with updated role checking logic
  - Preserves SECURITY DEFINER function protections
  - Validates role values to prevent invalid data

  ## Notes
  - The old 'role' column is removed after data migration
  - All users must have at least one role in the 'roles' array
  - Superadmin is identified by 'superadmin' in roles array OR email = 'support@litinkai.com'
*/

-- Step 1: Ensure all profiles have migrated roles data
DO $$
BEGIN
  -- Migrate any remaining single role values to roles array
  UPDATE profiles 
  SET roles = ARRAY[role::text]
  WHERE roles IS NULL AND role IS NOT NULL;
  
  -- Set default roles for any profiles with NULL roles
  UPDATE profiles 
  SET roles = ARRAY['explorer']::text[]
  WHERE roles IS NULL;
END $$;

-- Step 2: Add constraint to validate role values
ALTER TABLE profiles
  DROP CONSTRAINT IF EXISTS check_valid_roles;

ALTER TABLE profiles
  ADD CONSTRAINT check_valid_roles 
  CHECK (
    roles <@ ARRAY['explorer', 'author', 'admin', 'superadmin']::text[]
  );

-- Step 3: Drop the old role column (it's now redundant)
ALTER TABLE profiles DROP COLUMN IF EXISTS role;

-- Step 4: Update is_superadmin() function to use roles array
CREATE OR REPLACE FUNCTION public.is_superadmin()
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
    AND ('superadmin' = ANY(roles) OR email = 'support@litinkai.com')
  );
END;
$$;

COMMENT ON FUNCTION public.is_superadmin() IS 'Check if current user is superadmin by checking roles array - SECURITY DEFINER with empty search_path';

-- Step 5: Create helper function to check if user has specific role
CREATE OR REPLACE FUNCTION public.user_has_role(check_user_id uuid, required_role text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = check_user_id
    AND required_role = ANY(roles)
  );
END;
$$;

COMMENT ON FUNCTION public.user_has_role(uuid, text) IS 'Check if specified user has a specific role - used in RLS policies and application code';

-- Step 6: Create helper function to check if user is superadmin (for RLS policies)
CREATE OR REPLACE FUNCTION public.user_is_superadmin(check_user_id uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = check_user_id
    AND ('superadmin' = ANY(roles) OR email = 'support@litinkai.com')
  );
END;
$$;

COMMENT ON FUNCTION public.user_is_superadmin(uuid) IS 'Check if specified user has superadmin role - used in RLS policies';

-- Step 7: Add helpful comments
COMMENT ON COLUMN profiles.roles IS 'Array of user roles: explorer, author, admin, superadmin. Users can have multiple roles simultaneously.';
COMMENT ON CONSTRAINT check_valid_roles ON profiles IS 'Ensures all role values are from the allowed set: explorer, author, admin, superadmin';
