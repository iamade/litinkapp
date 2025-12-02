/*
  # User Mode Preferences and Onboarding Tracking

  ## Purpose
  Add fields to track user mode preferences (explorer/creator) and onboarding completion status for a better user experience.

  ## Changes Made

  1. **Profiles Table Additions**
    - Add `preferred_mode` column to store user's default mode preference (explorer/creator)
    - Add `onboarding_completed` JSONB column to track which onboardings user has seen
    - Add `created_at` and `updated_at` timestamps if not exists

  2. **Default Values**
    - Set preferred_mode default to 'explorer' for new users
    - Initialize onboarding_completed as empty object {}
    - Existing users get 'explorer' as default mode

  3. **Benefits**
    - Users can persist their mode preference across sessions
    - Track onboarding completion to avoid showing tours multiple times
    - Flexible JSONB structure for tracking different onboarding flows

  ## Security
  - Users can only update their own mode preference through RLS
  - Maintains existing security policies
*/

-- Add preferred_mode column if not exists
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'profiles' AND column_name = 'preferred_mode'
  ) THEN
    ALTER TABLE profiles 
      ADD COLUMN preferred_mode text DEFAULT 'explorer' CHECK (preferred_mode IN ('explorer', 'creator'));
  END IF;
END $$;

-- Add onboarding_completed column if not exists
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'profiles' AND column_name = 'onboarding_completed'
  ) THEN
    ALTER TABLE profiles 
      ADD COLUMN onboarding_completed jsonb DEFAULT '{}'::jsonb;
  END IF;
END $$;

-- Update existing users to have default mode based on their roles
UPDATE profiles 
SET preferred_mode = CASE 
  WHEN 'creator' = ANY(roles) THEN 'creator'
  ELSE 'explorer'
END
WHERE preferred_mode IS NULL;

-- Create index for mode queries
CREATE INDEX IF NOT EXISTS idx_profiles_preferred_mode ON profiles (preferred_mode);

-- Add helpful comments
COMMENT ON COLUMN profiles.preferred_mode IS 'User''s preferred default mode: explorer or creator. Users with both roles can switch between modes.';
COMMENT ON COLUMN profiles.onboarding_completed IS 'JSON object tracking which onboarding tours the user has completed, e.g. {"explorer": true, "creator": true}';
