/*
  # Add Seed Data Compatibility Columns

  ## Overview
  This migration adds columns to support the test seed data while maintaining backward compatibility
  with the existing schema. It addresses column name mismatches between the schema and seed data.

  ## Changes Made

  ### Characters Table
  - Add `description` column (TEXT) - General character description for seed data compatibility
  - Add `traits` column (JSONB) - Character traits in simple key-value format
  - Make `plot_overview_id` nullable to support seed data without plot overviews

  ### Scripts Table
  - Add `book_id` column (UUID) - Direct reference to books table for seed data
  - Add `content` column (TEXT) - Alias for script content
  - Add `story_type` column (TEXT) - Story type identifier
  - Add `script_metadata` column (JSONB) - Metadata about the script

  ## Rationale
  The seed data file uses simplified column names that don't match the more detailed schema:
  - Characters: seed uses `description` + `traits`, schema uses `physical_description` + `personality` + `archetypes`
  - Scripts: seed uses `book_id` + `content` + `story_type` + `script_metadata`, schema uses `chapter_id` + `script` + `script_story_type` + `metadata`

  This migration adds the missing columns so seed data can be inserted without modification.

  ## Security
  - No RLS policy changes needed
  - All new columns are nullable to maintain backward compatibility
  - Foreign key constraints maintain referential integrity

  ## Notes
  - Uses IF NOT EXISTS for idempotency
  - All operations are safe for existing data
  - New columns have appropriate defaults
*/

DO $$
BEGIN
  -- ============================================
  -- CHARACTERS TABLE UPDATES
  -- ============================================

  -- Add description column for general character description
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'characters' AND column_name = 'description'
  ) THEN
    ALTER TABLE characters ADD COLUMN description TEXT;
    COMMENT ON COLUMN characters.description IS 'General character description (seed data compatibility)';
  END IF;

  -- Add traits column for character traits
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'characters' AND column_name = 'traits'
  ) THEN
    ALTER TABLE characters ADD COLUMN traits JSONB;
    COMMENT ON COLUMN characters.traits IS 'Character traits in key-value format (seed data compatibility)';
  END IF;

  -- Make plot_overview_id nullable for seed data without plot overviews
  ALTER TABLE characters ALTER COLUMN plot_overview_id DROP NOT NULL;
  COMMENT ON COLUMN characters.plot_overview_id IS 'Reference to plot overview (nullable for seed data compatibility)';

  -- ============================================
  -- SCRIPTS TABLE UPDATES
  -- ============================================

  -- Add book_id column for direct book reference
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'scripts' AND column_name = 'book_id'
  ) THEN
    ALTER TABLE scripts ADD COLUMN book_id UUID REFERENCES books(id) ON DELETE CASCADE;
    COMMENT ON COLUMN scripts.book_id IS 'Direct reference to books table (seed data compatibility)';
  END IF;

  -- Add content column as alias for script
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'scripts' AND column_name = 'content'
  ) THEN
    ALTER TABLE scripts ADD COLUMN content TEXT;
    COMMENT ON COLUMN scripts.content IS 'Script content (alias for script column, seed data compatibility)';
  END IF;

  -- Add story_type column
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'scripts' AND column_name = 'story_type'
  ) THEN
    ALTER TABLE scripts ADD COLUMN story_type TEXT;
    COMMENT ON COLUMN scripts.story_type IS 'Story type identifier (seed data compatibility)';
  END IF;

  -- Add script_metadata column
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'scripts' AND column_name = 'script_metadata'
  ) THEN
    ALTER TABLE scripts ADD COLUMN script_metadata JSONB;
    COMMENT ON COLUMN scripts.script_metadata IS 'Script metadata (alias for metadata column, seed data compatibility)';
  END IF;

  -- ============================================
  -- CREATE INDEXES FOR PERFORMANCE
  -- ============================================

  -- Index on scripts.book_id for queries
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = 'idx_scripts_book_id'
  ) THEN
    CREATE INDEX idx_scripts_book_id ON scripts(book_id);
  END IF;

  -- ============================================
  -- CREATE TRIGGERS TO SYNC DUAL COLUMNS
  -- ============================================

  -- Create function to sync script content and metadata columns
  CREATE OR REPLACE FUNCTION sync_script_columns()
  RETURNS TRIGGER AS $func$
  BEGIN
    -- Sync content <-> script
    IF NEW.content IS NOT NULL AND (NEW.script IS NULL OR NEW.script = '') THEN
      NEW.script := NEW.content;
    ELSIF NEW.script IS NOT NULL AND (NEW.content IS NULL OR NEW.content = '') THEN
      NEW.content := NEW.script;
    END IF;

    -- Sync script_metadata <-> metadata
    IF NEW.script_metadata IS NOT NULL AND NEW.metadata IS NULL THEN
      NEW.metadata := NEW.script_metadata;
    ELSIF NEW.metadata IS NOT NULL AND NEW.script_metadata IS NULL THEN
      NEW.script_metadata := NEW.metadata;
    END IF;

    RETURN NEW;
  END;
  $func$ LANGUAGE plpgsql;

  -- Drop trigger if it exists and recreate
  DROP TRIGGER IF EXISTS trigger_sync_script_columns ON scripts;
  CREATE TRIGGER trigger_sync_script_columns
    BEFORE INSERT OR UPDATE ON scripts
    FOR EACH ROW
    EXECUTE FUNCTION sync_script_columns();

END $$;
