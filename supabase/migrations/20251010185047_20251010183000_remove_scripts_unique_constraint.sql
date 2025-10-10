/*
  # Remove unique constraint from scripts table

  1. Changes
    - Drop the unique constraint on (chapter_id, user_id, script_style)
    - This allows users to generate multiple scripts with the same style for the same chapter

  2. Rationale
    - Users should be able to regenerate scripts if they don't like the first result
    - Each script is uniquely identified by its primary key (id)
    - The created_at timestamp distinguishes between different generations

  3. Security
    - No RLS changes needed
    - Existing policies remain in effect
*/

DO $$
BEGIN
  -- Drop the unique constraint if it exists
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'scripts_chapter_id_user_id_script_style_key'
      AND table_name = 'scripts'
  ) THEN
    ALTER TABLE scripts DROP CONSTRAINT scripts_chapter_id_user_id_script_style_key;
    RAISE NOTICE 'Removed unique constraint from scripts table';
  END IF;
END $$;
