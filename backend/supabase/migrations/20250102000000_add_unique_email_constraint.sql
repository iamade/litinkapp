/*
  # Add Unique Email Constraint to Profiles

  ## Summary
  Adds a UNIQUE constraint on the profiles.email column to ensure data integrity
  and enable proper ON CONFLICT handling in INSERT statements.

  ## Changes Made

  1. **Add UNIQUE Constraint**
    - Add UNIQUE constraint on profiles.email column
    - Ensures no duplicate emails in profiles table
    - Enables ON CONFLICT (email) clauses in INSERT/UPSERT operations

  2. **Safety Checks**
    - Uses IF NOT EXISTS pattern for idempotency
    - Checks for existing duplicate emails before adding constraint
    - Provides informative notices if issues are found

  ## Security
  - No RLS policy changes needed
  - Maintains existing foreign key relationships
  - Data integrity enhancement

  ## Notes
  - This migration is idempotent and safe to run multiple times
  - If duplicate emails exist, the migration will report them but continue
  - The constraint name is: profiles_email_key
*/

DO $$
DECLARE
  duplicate_count INTEGER;
BEGIN
  -- Check if any duplicate emails exist
  SELECT COUNT(*) INTO duplicate_count
  FROM (
    SELECT email, COUNT(*) as cnt
    FROM public.profiles
    GROUP BY email
    HAVING COUNT(*) > 1
  ) duplicates;

  IF duplicate_count > 0 THEN
    RAISE NOTICE 'WARNING: Found % duplicate email(s) in profiles table', duplicate_count;
    RAISE NOTICE 'Please resolve duplicate emails before adding UNIQUE constraint';
    RAISE NOTICE 'Query to find duplicates: SELECT email, COUNT(*) FROM profiles GROUP BY email HAVING COUNT(*) > 1';
  END IF;

  -- Add UNIQUE constraint if it doesn't exist
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'profiles_email_key'
    AND conrelid = 'public.profiles'::regclass
  ) THEN
    -- Only add constraint if no duplicates exist
    IF duplicate_count = 0 THEN
      ALTER TABLE public.profiles
        ADD CONSTRAINT profiles_email_key UNIQUE (email);

      RAISE NOTICE 'Successfully added UNIQUE constraint on profiles.email';
    ELSE
      RAISE EXCEPTION 'Cannot add UNIQUE constraint: duplicate emails exist';
    END IF;
  ELSE
    RAISE NOTICE 'UNIQUE constraint profiles_email_key already exists';
  END IF;

END $$;

-- Add comment for documentation
COMMENT ON CONSTRAINT profiles_email_key ON public.profiles IS 'Ensures email addresses are unique across all profiles';
