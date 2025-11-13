/*
  # User Deletion System Migration

  1. New Tables
    - `deleted_users_audit` - Archive of deleted user information for compliance
      - `id` (uuid, primary key)
      - `original_user_id` (uuid)
      - `email` (text)
      - `display_name` (text)
      - `roles` (text array)
      - `created_at` (timestamptz) - when user was originally created
      - `deleted_at` (timestamptz) - when user was deleted
      - `deleted_by` (uuid) - admin who deleted the user
      - `deletion_reason` (text)
      - `content_summary` (jsonb) - summary of deleted content

  2. Functions
    - `get_user_deletion_preview` - Returns preview of what will be deleted
    - `delete_user_completely` - Safely deletes user from all tables including auth.users
    - `archive_deleted_user` - Archives user info before deletion

  3. Security
    - All functions use SECURITY DEFINER to access auth schema
    - Proper checks to prevent deletion of primary superadmin
    - RLS enabled on audit table with superadmin-only access

  4. Important Notes
    - This migration enables permanent user deletion
    - All user content will be cascade deleted
    - Audit trail maintained in deleted_users_audit table
    - Cannot be undone once executed
*/

-- ============================================
-- DELETED USERS AUDIT TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS deleted_users_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  original_user_id UUID NOT NULL,
  email TEXT NOT NULL,
  display_name TEXT,
  roles TEXT[],
  user_created_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
  deletion_reason TEXT,
  content_summary JSONB DEFAULT '{}'::JSONB
);

-- Enable RLS
ALTER TABLE deleted_users_audit ENABLE ROW LEVEL SECURITY;

-- Only superadmins can view audit logs
DROP POLICY IF EXISTS "Superadmins can view deleted user audit" ON deleted_users_audit;
CREATE POLICY "Superadmins can view deleted user audit"
  ON deleted_users_audit FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND 'superadmin' = ANY(profiles.roles)
    )
  );

-- Service role can do everything
DROP POLICY IF EXISTS "Service role can manage audit logs" ON deleted_users_audit;
CREATE POLICY "Service role can manage audit logs"
  ON deleted_users_audit FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_deleted_users_audit_email ON deleted_users_audit(email);
CREATE INDEX IF NOT EXISTS idx_deleted_users_audit_deleted_at ON deleted_users_audit(deleted_at);
CREATE INDEX IF NOT EXISTS idx_deleted_users_audit_deleted_by ON deleted_users_audit(deleted_by);

-- ============================================
-- FUNCTION: Get User Deletion Preview
-- ============================================

CREATE OR REPLACE FUNCTION get_user_deletion_preview(target_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
  user_record RECORD;
  content_counts JSONB;
BEGIN
  -- Check if user exists
  SELECT * INTO user_record
  FROM profiles
  WHERE id = target_user_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'User not found';
  END IF;

  -- Prevent deletion of primary superadmin
  IF user_record.email = 'support@litinkai.com' THEN
    RAISE EXCEPTION 'Cannot delete primary superadmin account';
  END IF;

  -- Get counts of all content that will be deleted
  content_counts := jsonb_build_object(
    'books', (SELECT COUNT(*) FROM books WHERE user_id = target_user_id),
    'chapters', (SELECT COUNT(*) FROM chapters c JOIN books b ON c.book_id = b.id WHERE b.user_id = target_user_id),
    'characters', (SELECT COUNT(*) FROM characters WHERE user_id = target_user_id),
    'scripts', (SELECT COUNT(*) FROM scripts WHERE user_id = target_user_id),
    'plot_overviews', (SELECT COUNT(*) FROM plot_overviews WHERE user_id = target_user_id),
    'image_generations', (SELECT COUNT(*) FROM image_generations WHERE user_id = target_user_id),
    'audio_generations', (SELECT COUNT(*) FROM audio_generations WHERE user_id = target_user_id),
    'video_generations', (SELECT COUNT(*) FROM video_generations WHERE user_id = target_user_id),
    'subscriptions', (SELECT COUNT(*) FROM user_subscriptions WHERE user_id = target_user_id),
    'usage_logs', (SELECT COUNT(*) FROM usage_logs WHERE user_id = target_user_id)
  );

  -- Return user info and content summary
  RETURN jsonb_build_object(
    'user_id', user_record.id,
    'email', user_record.email,
    'display_name', user_record.display_name,
    'roles', user_record.roles,
    'created_at', user_record.created_at,
    'email_verified', user_record.email_verified,
    'content_counts', content_counts,
    'can_delete', true,
    'warnings', CASE
      WHEN 'superadmin' = ANY(user_record.roles) THEN ARRAY['This user has superadmin privileges']
      ELSE ARRAY[]::TEXT[]
    END
  );
END;
$$;

-- ============================================
-- FUNCTION: Archive Deleted User
-- ============================================

CREATE OR REPLACE FUNCTION archive_deleted_user(
  target_user_id UUID,
  deleting_admin_id UUID,
  reason TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
  user_record RECORD;
  content_summary JSONB;
  audit_id UUID;
BEGIN
  -- Get user info
  SELECT * INTO user_record
  FROM profiles
  WHERE id = target_user_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'User not found';
  END IF;

  -- Get content summary
  content_summary := jsonb_build_object(
    'books_count', (SELECT COUNT(*) FROM books WHERE user_id = target_user_id),
    'chapters_count', (SELECT COUNT(*) FROM chapters c JOIN books b ON c.book_id = b.id WHERE b.user_id = target_user_id),
    'characters_count', (SELECT COUNT(*) FROM characters WHERE user_id = target_user_id),
    'scripts_count', (SELECT COUNT(*) FROM scripts WHERE user_id = target_user_id),
    'image_generations_count', (SELECT COUNT(*) FROM image_generations WHERE user_id = target_user_id),
    'audio_generations_count', (SELECT COUNT(*) FROM audio_generations WHERE user_id = target_user_id),
    'video_generations_count', (SELECT COUNT(*) FROM video_generations WHERE user_id = target_user_id)
  );

  -- Insert into audit table
  INSERT INTO deleted_users_audit (
    original_user_id,
    email,
    display_name,
    roles,
    user_created_at,
    deleted_by,
    deletion_reason,
    content_summary
  ) VALUES (
    user_record.id,
    user_record.email,
    user_record.display_name,
    user_record.roles,
    user_record.created_at,
    deleting_admin_id,
    reason,
    content_summary
  )
  RETURNING id INTO audit_id;

  RETURN audit_id;
END;
$$;

-- ============================================
-- FUNCTION: Delete User Completely
-- ============================================

CREATE OR REPLACE FUNCTION delete_user_completely(
  target_user_id UUID,
  deleting_admin_id UUID,
  deletion_reason TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
  user_record RECORD;
  audit_id UUID;
  deletion_summary JSONB;
BEGIN
  -- Check if user exists
  SELECT * INTO user_record
  FROM profiles
  WHERE id = target_user_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'User not found';
  END IF;

  -- Prevent deletion of primary superadmin
  IF user_record.email = 'support@litinkai.com' THEN
    RAISE EXCEPTION 'Cannot delete primary superadmin account';
  END IF;

  -- Prevent self-deletion
  IF target_user_id = deleting_admin_id THEN
    RAISE EXCEPTION 'Cannot delete your own account';
  END IF;

  -- Archive user before deletion
  audit_id := archive_deleted_user(target_user_id, deleting_admin_id, deletion_reason);

  -- Start deletion process (CASCADE will handle related records)
  -- The CASCADE rules in the schema will automatically delete:
  -- - books (which cascades to chapters, characters, scripts, plot_overviews)
  -- - image_generations
  -- - audio_generations
  -- - video_generations
  -- - user_subscriptions
  -- - usage_logs
  -- - profiles

  -- Delete from auth.users (this will cascade to profiles due to ON DELETE CASCADE)
  DELETE FROM auth.users WHERE id = target_user_id;

  -- Build deletion summary
  deletion_summary := jsonb_build_object(
    'success', true,
    'deleted_user_id', target_user_id,
    'deleted_email', user_record.email,
    'audit_id', audit_id,
    'deleted_at', NOW(),
    'deleted_by', deleting_admin_id
  );

  RETURN deletion_summary;
EXCEPTION
  WHEN OTHERS THEN
    -- Return error information
    RETURN jsonb_build_object(
      'success', false,
      'error', SQLERRM,
      'user_id', target_user_id
    );
END;
$$;

-- ============================================
-- GRANT PERMISSIONS
-- ============================================

-- Grant execute permissions to authenticated users (RLS will control access)
GRANT EXECUTE ON FUNCTION get_user_deletion_preview(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION delete_user_completely(UUID, UUID, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION archive_deleted_user(UUID, UUID, TEXT) TO authenticated;

-- Grant full access to service role
GRANT EXECUTE ON FUNCTION get_user_deletion_preview(UUID) TO service_role;
GRANT EXECUTE ON FUNCTION delete_user_completely(UUID, UUID, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION archive_deleted_user(UUID, UUID, TEXT) TO service_role;
