-- Remove password storage from profiles
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

-- Create trigger to auto-create profiles
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, email, created_at, updated_at)
  VALUES (NEW.id, NEW.email, NOW(), NOW())
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
