/*
  # Add script_story_type and script_id columns

  1. New Columns
    - `plot_overviews.script_story_type` (text) - Type of story for the plot overview
    - `scripts.script_story_type` (text) - Type of story for the script
    - `image_generations.script_id` (uuid) - Foreign key to scripts table
    - `audio_generations.script_id` (uuid) - Foreign key to scripts table

  2. Changes
    - Add script_story_type to plot_overviews and scripts tables for easier story type tracking
    - Add script_id foreign keys to image_generations and audio_generations for better relational integrity
    - Create indexes on script_id columns for performance optimization

  3. Notes
    - Uses IF NOT EXISTS for idempotency
    - All operations wrapped in a single transaction
    - Foreign keys have ON DELETE SET NULL for safe deletion
*/

DO $$
BEGIN
  -- Add script_story_type to plot_overviews if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'plot_overviews' AND column_name = 'script_story_type'
  ) THEN
    ALTER TABLE plot_overviews ADD COLUMN script_story_type TEXT;
    COMMENT ON COLUMN plot_overviews.script_story_type IS 'Type of story (e.g., fiction, non-fiction, documentary, etc.) for the plot overview';
  END IF;

  -- Add script_story_type to scripts if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'scripts' AND column_name = 'script_story_type'
  ) THEN
    ALTER TABLE scripts ADD COLUMN script_story_type TEXT;
    COMMENT ON COLUMN scripts.script_story_type IS 'Type of story (e.g., fiction, non-fiction, documentary, etc.) for the script';
  END IF;

  -- Add script_id to image_generations if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'script_id'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN script_id UUID;
  END IF;

  -- Add foreign key constraint for image_generations.script_id if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'fk_image_generations_script_id'
  ) THEN
    ALTER TABLE image_generations ADD CONSTRAINT fk_image_generations_script_id
    FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE SET NULL;
  END IF;

  -- Add script_id to audio_generations if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'audio_generations' AND column_name = 'script_id'
  ) THEN
    ALTER TABLE audio_generations ADD COLUMN script_id UUID;
  END IF;

  -- Add foreign key constraint for audio_generations.script_id if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'fk_audio_generations_script_id'
  ) THEN
    ALTER TABLE audio_generations ADD CONSTRAINT fk_audio_generations_script_id
    FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE SET NULL;
  END IF;

  -- Create indexes for performance
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = 'idx_image_generations_script_id'
  ) THEN
    CREATE INDEX idx_image_generations_script_id ON image_generations(script_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = 'idx_audio_generations_script_id'
  ) THEN
    CREATE INDEX idx_audio_generations_script_id ON audio_generations(script_id);
  END IF;
END $$;
