/*
  # Add Email Verification System

  1. New Columns
    - `email_verified` (boolean) - Tracks if user's email has been verified
    - `email_verified_at` (timestamptz) - Timestamp of when email was verified
    - `verification_token_sent_at` (timestamptz) - Timestamp of last verification email sent

  2. Changes
    - Add email_verified column with default false for all users
    - Add email_verified_at column to track verification time
    - Add verification_token_sent_at for rate limiting resend requests
    - Create index on email_verified for efficient filtering
    - Set existing users to unverified to require email verification
    - Add trigger to update email_verified_at when email_verified changes to true

  3. Security
    - Maintains existing RLS policies
    - Adds validation to ensure email_verified_at only set when email_verified is true

  4. Notes
    - All existing users will need to verify their emails
    - New users will be unverified by default
    - Supports Supabase Auth email verification flow
*/

-- Add email verification columns
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS email_verified boolean DEFAULT false NOT NULL,
  ADD COLUMN IF NOT EXISTS email_verified_at timestamptz,
  ADD COLUMN IF NOT EXISTS verification_token_sent_at timestamptz;

-- Set all existing users to unverified
UPDATE profiles
SET email_verified = false,
    email_verified_at = NULL
WHERE email_verified IS NULL;

-- Create index for efficient filtering of unverified users
CREATE INDEX IF NOT EXISTS idx_profiles_email_verified ON profiles(email_verified);
CREATE INDEX IF NOT EXISTS idx_profiles_email_verified_at ON profiles(email_verified_at) WHERE email_verified = true;

-- Create trigger function to auto-set email_verified_at timestamp
CREATE OR REPLACE FUNCTION set_email_verified_at()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.email_verified = true AND OLD.email_verified = false THEN
    NEW.email_verified_at = now();
  ELSIF NEW.email_verified = false THEN
    NEW.email_verified_at = NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update email_verified_at
DROP TRIGGER IF EXISTS trigger_set_email_verified_at ON profiles;
CREATE TRIGGER trigger_set_email_verified_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW
  EXECUTE FUNCTION set_email_verified_at();

-- Add constraint to ensure email_verified_at is only set when verified
ALTER TABLE profiles
  ADD CONSTRAINT check_email_verified_at 
  CHECK (
    (email_verified = true AND email_verified_at IS NOT NULL) OR
    (email_verified = false AND email_verified_at IS NULL) OR
    (email_verified IS NULL)
  );

-- Create function to check if user can request verification email (rate limiting)
CREATE OR REPLACE FUNCTION can_request_verification_email(user_id uuid)
RETURNS boolean AS $$
DECLARE
  last_sent timestamptz;
BEGIN
  SELECT verification_token_sent_at INTO last_sent
  FROM profiles
  WHERE id = user_id;
  
  -- Allow if never sent or if more than 5 minutes have passed
  RETURN last_sent IS NULL OR (now() - last_sent) > interval '5 minutes';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to update verification token sent timestamp
CREATE OR REPLACE FUNCTION update_verification_token_sent(user_id uuid)
RETURNS void AS $$
BEGIN
  UPDATE profiles
  SET verification_token_sent_at = now()
  WHERE id = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add helpful comments
COMMENT ON COLUMN profiles.email_verified IS 'Whether the user has verified their email address';
COMMENT ON COLUMN profiles.email_verified_at IS 'Timestamp when the email was verified';
COMMENT ON COLUMN profiles.verification_token_sent_at IS 'Timestamp of last verification email sent (for rate limiting)';
COMMENT ON FUNCTION can_request_verification_email(uuid) IS 'Check if user can request a new verification email (5 minute cooldown)';
COMMENT ON FUNCTION update_verification_token_sent(uuid) IS 'Update the timestamp of when verification email was sent';
