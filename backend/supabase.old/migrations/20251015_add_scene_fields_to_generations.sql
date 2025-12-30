-- migration: add scene fields to image_generations
BEGIN;

ALTER TABLE image_generations
  ADD COLUMN IF NOT EXISTS chapter_id uuid,
  ADD COLUMN IF NOT EXISTS script_id uuid,
  ADD COLUMN IF NOT EXISTS scene_number integer,
  ADD COLUMN IF NOT EXISTS image_type text NOT NULL DEFAULT 'scene',
  ADD COLUMN IF NOT EXISTS retry_count integer NOT NULL DEFAULT 0;

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_image_generations_chapter_id ON image_generations (chapter_id);
CREATE INDEX IF NOT EXISTS idx_image_generations_scene_number_meta ON image_generations ((metadata ->> 'scene_number'));
CREATE INDEX IF NOT EXISTS idx_image_generations_image_type ON image_generations (image_type);

COMMIT;

-- Rollback
-- To rollback, run the following:
-- ALTER TABLE image_generations DROP COLUMN IF EXISTS chapter_id;
-- ALTER TABLE image_generations DROP COLUMN IF EXISTS script_id;
-- ALTER TABLE image_generations DROP COLUMN IF EXISTS scene_number;
-- ALTER TABLE image_generations DROP COLUMN IF EXISTS image_type;
-- ALTER TABLE image_generations DROP COLUMN IF EXISTS retry_count;
-- DROP INDEX IF EXISTS idx_image_generations_chapter_id;
-- DROP INDEX IF EXISTS idx_image_generations_scene_number_meta;
-- DROP INDEX IF EXISTS idx_image_generations_image_type;