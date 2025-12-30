-- Fix User Registration - Add Missing Columns and Trigger
--
-- This migration fixes the user registration flow by:
-- 1. Adding all missing authentication-related columns to the profiles table
-- 2. Creating the trigger function to auto-create profiles when users register
-- 3. Creating the trigger on auth.users table

-- Step 1: Add missing columns to profiles table
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS account_status TEXT NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS security_question TEXT NOT NULL DEFAULT 'mother_maiden_name',
  ADD COLUMN IF NOT EXISTS security_answer TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS first_name VARCHAR NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS middle_name VARCHAR,
  ADD COLUMN IF NOT EXISTS last_name VARCHAR NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN NOT NULL DEFAULT FALSE;

-- Step 2: Add check constraints for valid values
ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS check_valid_account_status;
ALTER TABLE public.profiles
  ADD CONSTRAINT check_valid_account_status
    CHECK (account_status IN ('active','inactive','locked','pending'));

ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS check_valid_security_question;
ALTER TABLE public.profiles
  ADD CONSTRAINT check_valid_security_question
    CHECK (security_question IN ('mother_maiden_name','childhood_friend','favorite_color','birth_city'));

-- Step 3: Create trigger function to auto-create profiles
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO public.profiles (
    id,
    email,
    display_name,
    roles,
    email_verified,
    account_status,
    is_active,
    failed_login_attempts,
    security_question,
    security_answer,
    first_name,
    last_name,
    is_superuser,
    created_at,
    updated_at
  )
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)),
    ARRAY['explorer']::TEXT[],
    FALSE,
    'pending',
    FALSE,
    0,
    'mother_maiden_name',
    '',
    COALESCE(NEW.raw_user_meta_data->>'first_name', ''),
    COALESCE(NEW.raw_user_meta_data->>'last_name', ''),
    FALSE,
    NOW(),
    NOW()
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    first_name = COALESCE(EXCLUDED.first_name, profiles.first_name),
    last_name = COALESCE(EXCLUDED.last_name, profiles.last_name),
    updated_at = NOW();

  RETURN NEW;
END;
$$;

-- Step 4: Create trigger on auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Step 5: Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';
