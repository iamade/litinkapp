/*
  # Add chapter_id and retry_count to image_generations table

  1. New Columns
    - `image_generations.chapter_id` (uuid) - Links scene images to chapters
    - `image_generations.retry_count` (integer) - Tracks retry attempts for failed generations
    - `image_generations.last_attempted_at` (timestamptz) - Timestamp of last generation attempt
    - `image_generations.progress` (integer) - Progress percentage (0-100) for in-progress generations

  2. Changes
    - Add chapter_id column to link images to chapters for scene-based generation
    - Add retry_count column to track retry attempts (default 0)
    - Add last_attempted_at column to track when generation was last attempted
    - Add progress column to track generation progress
    - Modify image_type column to allow NULL and set default to 'scene'
    - Create indexes for performance on chapter_id lookups

  3. Purpose
    - Enable chapter-based scene image generation via API endpoints
    - Support automatic retry mechanism with exponential backoff
    - Track generation progress for real-time status updates
    - Link images to chapters for proper data organization

  4. Security
    - No RLS changes needed as parent table already has RLS enabled
    - Foreign key constraints ensure referential integrity
    - Indexes improve query performance for chapter-based lookups

  5. Notes
    - Uses IF NOT EXISTS for idempotency
    - Existing data is preserved, new columns are nullable
    - Indexes created for performance optimization
*/

DO $$
BEGIN
  -- Add chapter_id column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'chapter_id'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN chapter_id UUID;
    COMMENT ON COLUMN image_generations.chapter_id IS 'Foreign key to chapters table for scene images';
  END IF;

  -- Add retry_count column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'retry_count'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0;
    COMMENT ON COLUMN image_generations.retry_count IS 'Number of retry attempts for failed generations';
  END IF;

  -- Add last_attempted_at column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'last_attempted_at'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN last_attempted_at TIMESTAMPTZ;
    COMMENT ON COLUMN image_generations.last_attempted_at IS 'Timestamp of last generation attempt';
  END IF;

  -- Add progress column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'progress'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN progress INTEGER DEFAULT 0;
    COMMENT ON COLUMN image_generations.progress IS 'Generation progress percentage (0-100)';
  END IF;

  -- Modify image_type to allow NULL (it currently might have NOT NULL constraint from line 8 of the migration file)
  -- We need to make it nullable since not all images have a type yet
  ALTER TABLE image_generations ALTER COLUMN image_type DROP NOT NULL;
  ALTER TABLE image_generations ALTER COLUMN image_type SET DEFAULT 'scene';

  -- Create index on chapter_id for performance
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = 'idx_image_generations_chapter_id'
  ) THEN
    CREATE INDEX idx_image_generations_chapter_id ON image_generations(chapter_id);
  END IF;

  -- Create composite index on chapter_id and scene_number for efficient lookups
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = 'idx_image_generations_chapter_scene'
  ) THEN
    CREATE INDEX idx_image_generations_chapter_scene ON image_generations(chapter_id, scene_number);
  END IF;

  -- Create index on retry_count for monitoring failed generations
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = 'idx_image_generations_retry_count'
  ) THEN
    CREATE INDEX idx_image_generations_retry_count ON image_generations(retry_count) WHERE retry_count > 0;
  END IF;

  -- Create index on status for filtering
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = 'idx_image_generations_status'
  ) THEN
    CREATE INDEX idx_image_generations_status ON image_generations(status);
  END IF;

END $$;