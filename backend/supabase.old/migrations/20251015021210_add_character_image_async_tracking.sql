/*
  # Add Character Image Async Tracking Columns

  1. New Columns
    - `characters.image_generation_task_id` (text) - Tracks the Celery task ID for the latest image generation
    - `characters.image_generation_status` (text) - Current status of image generation (pending, generating, completed, failed)
    - `image_generations.character_id` (uuid) - Foreign key linking to characters table for character images

  2. Changes
    - Add tracking columns to characters table for async image generation status
    - Add character_id foreign key to image_generations table to link character images to character records
    - Create indexes on new columns for query performance
    - Set default values for status tracking

  3. Purpose
    - Enable unified async image generation flow using Celery tasks
    - Allow tracking of character image generation status in real-time
    - Link image generation records to character records for complete audit trail
    - Support both character images (linked to characters) and scene images (standalone)

  4. Security
    - Foreign key has ON DELETE SET NULL for safe deletion handling
    - No RLS changes needed as parent tables already have RLS enabled

  5. Notes
    - Uses IF NOT EXISTS for idempotency
    - All operations wrapped in PL/pgSQL block for transaction safety
    - Indexes created for performance optimization on foreign keys and status queries
*/

DO $$
BEGIN
  -- Add image_generation_task_id to characters table
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'characters' AND column_name = 'image_generation_task_id'
  ) THEN
    ALTER TABLE characters ADD COLUMN image_generation_task_id TEXT;
    COMMENT ON COLUMN characters.image_generation_task_id IS 'Celery task ID for the latest character image generation';
  END IF;

  -- Add image_generation_status to characters table
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'characters' AND column_name = 'image_generation_status'
  ) THEN
    ALTER TABLE characters ADD COLUMN image_generation_status TEXT DEFAULT 'none';
    COMMENT ON COLUMN characters.image_generation_status IS 'Status of character image generation: none, pending, generating, completed, failed';
  END IF;

  -- Add character_id to image_generations table
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'character_id'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN character_id UUID;
    COMMENT ON COLUMN image_generations.character_id IS 'Foreign key to characters table for character images (null for scene images)';
  END IF;

  -- Add foreign key constraint for image_generations.character_id
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'fk_image_generations_character_id'
  ) THEN
    ALTER TABLE image_generations ADD CONSTRAINT fk_image_generations_character_id
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL;
  END IF;

  -- Create index on image_generations.character_id for performance
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = 'idx_image_generations_character_id'
  ) THEN
    CREATE INDEX idx_image_generations_character_id ON image_generations(character_id);
  END IF;

  -- Create index on characters.image_generation_status for filtering
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = 'idx_characters_image_generation_status'
  ) THEN
    CREATE INDEX idx_characters_image_generation_status ON characters(image_generation_status);
  END IF;

  -- Create index on characters.image_generation_task_id for task lookups
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = 'idx_characters_image_generation_task_id'
  ) THEN
    CREATE INDEX idx_characters_image_generation_task_id ON characters(image_generation_task_id);
  END IF;

END $$;
