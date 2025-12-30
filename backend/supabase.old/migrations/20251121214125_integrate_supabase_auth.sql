-- Remove password storage from profiles (Supabase Auth handles it)
ALTER TABLE profiles DROP COLUMN IF EXISTS hashed_password;

-- Remove OTP columns (not needed for now)
ALTER TABLE profiles DROP COLUMN IF EXISTS otp;
ALTER TABLE profiles DROP COLUMN IF EXISTS otp_expiry_time;

-- Keep these columns (custom features)
-- ✓ failed_login_attempts
-- ✓ last_failed_login
-- ✓ security_question
-- ✓ security_answer
-- ✓ account_status
-- ✓ is_active

-- Create trigger to auto-create profiles with ALL required NOT NULL fields
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
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
    ARRAY['explorer']::text[],
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

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create trigger
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Notify PostgREST to reload schema
NOTIFY pgrst, 'reload schema';
