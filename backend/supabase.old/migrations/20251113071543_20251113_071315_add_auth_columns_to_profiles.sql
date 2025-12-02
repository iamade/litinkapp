-- 20251113_071315_add_auth_columns_to_profiles.sql

BEGIN;

-- Core auth/profile fields
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS account_status text NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS hashed_password text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS roles text[] NOT NULL DEFAULT ARRAY['explorer']::text[],
  ADD COLUMN IF NOT EXISTS failed_login_attempts integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_failed_login timestamptz NULL,
  ADD COLUMN IF NOT EXISTS otp text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS otp_expiry_time timestamptz NULL,
  ADD COLUMN IF NOT EXISTS display_name text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS security_question text NOT NULL DEFAULT 'mother_maiden_name',
  ADD COLUMN IF NOT EXISTS security_answer text NOT NULL DEFAULT '';

-- Validate enumerated values used by the app
ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS check_valid_account_status,
  ADD CONSTRAINT check_valid_account_status
    CHECK (account_status IN ('active','inactive','locked','pending'));

ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS check_valid_security_question,
  ADD CONSTRAINT check_valid_security_question
    CHECK (security_question IN ('mother_maiden_name','childhood_friend','favorite_color','birth_city'));

-- Maintain updated_at automatically
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_set_profiles_updated_at ON public.profiles;
CREATE TRIGGER trigger_set_profiles_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

-- Ask PostgREST to reload schema cache (Supabase REST)
NOTIFY pgrst, 'reload schema';

COMMIT;
