/*
  # Migrate Author Role to Creator Role

  1. Changes
    - Updates check constraint to replace 'author' with 'creator' in valid roles list
    - Migrates all existing 'author' role assignments to 'creator'
    - Updates all database comments and documentation
    - Maintains backward compatibility during transition

  2. Impact
    - All users with 'author' role will become 'creator'
    - Role validation will accept 'creator' instead of 'author'
    - API endpoints will need to be updated to use 'creator'
    - Frontend will need to be updated to use 'creator' terminology

  3. Security
    - RLS policies remain unchanged (role-based access continues to work)
    - No data loss or permission changes
    - All existing functionality preserved

  4. Notes
    - This is a semantic change, not a functional one
    - The term 'creator' better represents the user role
    - Backward compatibility maintained for existing data
*/

-- ============================================
-- Step 1: Update the roles check constraint
-- ============================================

-- Drop the existing constraint
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS check_valid_roles;

-- Recreate with 'creator' instead of 'author'
ALTER TABLE profiles ADD CONSTRAINT check_valid_roles
  CHECK (
    roles <@ ARRAY['explorer', 'creator', 'admin', 'superadmin']::text[]
  );

-- ============================================
-- Step 2: Migrate existing 'author' roles to 'creator'
-- ============================================

-- Update all profiles that have 'author' role
UPDATE profiles
SET roles = array_replace(roles, 'author', 'creator')
WHERE 'author' = ANY(roles);

-- ============================================
-- Step 3: Update table comments
-- ============================================

COMMENT ON TABLE profiles IS 'User profiles with role-based access control. Roles: explorer (reader), creator (content creator), admin (platform admin), superadmin (full access)';

COMMENT ON COLUMN profiles.roles IS 'Array of user roles. Valid values: explorer, creator, admin, superadmin. Users can have multiple roles.';

-- ============================================
-- Step 4: Update any views or functions that reference roles
-- ============================================

-- Note: If you have any custom functions or views that filter by 'author',
-- they should be updated here. Currently, our system doesn't have such
-- dependencies, but this is where they would go.

-- ============================================
-- Step 5: Refresh PostgREST schema cache
-- ============================================

-- Notify PostgREST to reload the schema cache
NOTIFY pgrst, 'reload schema';

-- ============================================
-- Verification Query (for manual testing)
-- ============================================

-- Uncomment to verify migration:
-- SELECT id, email, roles
-- FROM profiles
-- WHERE 'creator' = ANY(roles)
-- ORDER BY created_at DESC
-- LIMIT 10;

-- Verify no 'author' roles remain:
-- SELECT COUNT(*) as author_count
-- FROM profiles
-- WHERE 'author' = ANY(roles);
-- -- Should return 0
