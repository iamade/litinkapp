-- Add script_story_type column to scripts table
-- Purpose: Store the script story type directly in the scripts table for easier access

-- Up Migration
BEGIN;

ALTER TABLE plot_overviews ADD COLUMN script_story_type TEXT;

-- COMMENT: Type of story (e.g., fiction, non-fiction, documentary, etc.) for the script
COMMENT ON COLUMN plot_overviews.script_story_type IS 'Type of story (e.g., fiction, non-fiction, documentary, etc.) for the script';

COMMIT;

-- Down Migration
BEGIN;

ALTER TABLE plot_overviews DROP COLUMN script_story_type;

COMMIT;

-- Add script_id column to image_generations table
ALTER TABLE image_generations ADD COLUMN script_id UUID;
ALTER TABLE image_generations ADD CONSTRAINT fk_image_generations_script_id FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE SET NULL;

-- Add script_id column to audio_generations table
ALTER TABLE audio_generations ADD COLUMN script_id UUID;
ALTER TABLE audio_generations ADD CONSTRAINT fk_audio_generations_script_id FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE SET NULL;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_image_generations_script_id ON image_generations(script_id);
CREATE INDEX IF NOT EXISTS idx_audio_generations_script_id ON audio_generations(script_id);