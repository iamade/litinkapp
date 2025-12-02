/*
  # Fix Profiles Table RLS for Service Role Registration

  ## Problem
  The INSERT policy "Users can insert own profile" checks that auth.uid() = id.
  When the backend uses the service role key to create profiles during registration,
  auth.uid() returns NULL, causing the insert to fail with "Database error saving new user".

  ## Solution
  1. Keep the existing INSERT policy for user-initiated inserts
  2. Add a new INSERT policy that allows service_role to insert any profile
  3. This enables the backend to create user profiles during registration while maintaining security

  ## Security
  - Service role key is only available to backend (not exposed to frontend)
  - Users can still only insert their own profile when authenticated
  - All other RLS policies remain unchanged
*/

-- Drop the existing restrictive INSERT policy
DROP POLICY IF EXISTS "Users can insert own profile" ON public.profiles;

-- Create new INSERT policy that allows authenticated users to insert their own profile
-- OR allows service_role to insert any profile (for registration flow)
CREATE POLICY "Users can insert own profile or service role can insert any"
  ON public.profiles FOR INSERT
  TO authenticated
  WITH CHECK (
    auth.uid() = id OR
    auth.jwt()->>'role' = 'service_role'
  );

-- Add helpful comment
COMMENT ON POLICY "Users can insert own profile or service role can insert any" ON public.profiles IS 
  'Allows users to insert their own profile during self-registration, and allows service_role to create profiles during backend registration flow';
