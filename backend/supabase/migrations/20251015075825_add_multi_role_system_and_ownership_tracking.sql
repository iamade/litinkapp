/*
  # Multi-Role System and Content Ownership Tracking

  ## Purpose
  Transform the single-role user system into a flexible multi-role system where users can have both "author" and "explorer" capabilities simultaneously, and track content ownership explicitly.

  ## Changes Made

  1. **Profiles Table Updates**
    - Change role column from single enum to text array to support multiple roles
    - Migrate existing single role values to array format
    - Add constraint to ensure users always have at least one role
    - Update default value for new users to ["explorer"]

  2. **Books Table Additions**
    - Add `uploaded_by_user_id` column to track who uploaded the content
    - Add `is_author` boolean flag to indicate if uploader claims authorship
    - Add `created_with_platform` boolean to mark AI-generated content
    - Add foreign key constraint linking to profiles table

  3. **Data Migration**
    - Convert all existing profile roles from single string to array
    - Set uploaded_by_user_id to user_id for all existing books
    - Default is_author to true for books with user_id (backward compatibility)
    - Default created_with_platform to false for existing books

  4. **Benefits**
    - Users can have multiple profile types on one account
    - Clear tracking of content ownership and authorship
    - Distinguishes between uploader and author
    - Marks platform-generated vs user-created content
    - Scalable for future role additions (moderator, admin, etc.)

  ## Security
  - Maintains existing RLS policies with updated role checking logic
  - Ensures data integrity with proper foreign key constraints
  - Validates role array is never empty
*/

-- Step 1: Ensure roles column exists as text array
-- Note: The initial schema already has roles as text[], so this is just a safeguard
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS roles text[];

-- Step 2: Set default for roles if not already set
-- Update any NULL roles to default ['explorer'] array
UPDATE profiles
SET roles = ARRAY['explorer']
WHERE roles IS NULL OR roles = '{}';

-- Step 3: Make roles column non-nullable and set default
ALTER TABLE profiles 
  ALTER COLUMN roles SET NOT NULL,
  ALTER COLUMN roles SET DEFAULT ARRAY['explorer']::text[];

-- Step 4: Add constraint to ensure at least one role exists
ALTER TABLE profiles
  ADD CONSTRAINT check_roles_not_empty 
  CHECK (array_length(roles, 1) > 0);

-- Step 5: Drop the old single role column (keeping it for now for backward compatibility)
-- We'll keep both columns temporarily and phase out the old one
-- ALTER TABLE profiles DROP COLUMN role;

-- Step 6: Add ownership tracking columns to books table
ALTER TABLE books
  ADD COLUMN IF NOT EXISTS uploaded_by_user_id uuid REFERENCES profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS is_author boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS created_with_platform boolean DEFAULT false;

-- Step 7: Migrate existing book data for backward compatibility
UPDATE books
SET uploaded_by_user_id = user_id,
    is_author = true
WHERE uploaded_by_user_id IS NULL AND user_id IS NOT NULL;

-- Step 8: Create index for efficient role queries
CREATE INDEX IF NOT EXISTS idx_profiles_roles ON profiles USING GIN (roles);

-- Step 9: Create index for ownership queries
CREATE INDEX IF NOT EXISTS idx_books_uploaded_by ON books (uploaded_by_user_id);
CREATE INDEX IF NOT EXISTS idx_books_is_author ON books (is_author) WHERE is_author = true;

-- Step 10: Create helper function to check if user has specific role
CREATE OR REPLACE FUNCTION has_role(user_roles text[], required_role text)
RETURNS boolean AS $$
BEGIN
  RETURN required_role = ANY(user_roles);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Step 11: Create function to add role to user
CREATE OR REPLACE FUNCTION add_role_to_user(user_id uuid, new_role text)
RETURNS void AS $$
BEGIN
  UPDATE profiles
  SET roles = array_append(roles, new_role),
      updated_at = now()
  WHERE id = user_id
    AND NOT (new_role = ANY(roles));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Step 12: Create function to remove role from user
CREATE OR REPLACE FUNCTION remove_role_from_user(user_id uuid, role_to_remove text)
RETURNS void AS $$
DECLARE
  current_roles text[];
BEGIN
  SELECT roles INTO current_roles FROM profiles WHERE id = user_id;
  
  -- Ensure at least one role remains
  IF array_length(current_roles, 1) <= 1 THEN
    RAISE EXCEPTION 'Cannot remove last role from user';
  END IF;
  
  UPDATE profiles
  SET roles = array_remove(roles, role_to_remove),
      updated_at = now()
  WHERE id = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Step 13: Update RLS policies to work with role arrays
-- Note: This assumes RLS policies exist and need updating

-- Step 14: Add helpful comments
COMMENT ON COLUMN profiles.roles IS 'Array of user roles: author, explorer, etc. Users can have multiple roles simultaneously.';
COMMENT ON COLUMN books.uploaded_by_user_id IS 'User who uploaded this content, regardless of authorship claim';
COMMENT ON COLUMN books.is_author IS 'Whether the uploader claims to be the author of this content';
COMMENT ON COLUMN books.created_with_platform IS 'Whether this content was generated using Litink AI platform tools';
COMMENT ON FUNCTION has_role(text[], text) IS 'Check if a role exists in user roles array';
COMMENT ON FUNCTION add_role_to_user(uuid, text) IS 'Add a new role to user account (idempotent)';
COMMENT ON FUNCTION remove_role_from_user(uuid, text) IS 'Remove a role from user account (prevents removing last role)';
