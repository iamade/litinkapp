-- Add missing columns to existing image_generations table
ALTER TABLE image_generations ADD COLUMN image_type VARCHAR(50);
ALTER TABLE image_generations ADD COLUMN character_name VARCHAR(255);

-- Update existing records
UPDATE image_generations SET image_type = 'scene' WHERE image_type IS NULL;

-- Create new indexes for the updated columns
CREATE INDEX IF NOT EXISTS idx_image_generations_type ON image_generations(image_type);
CREATE INDEX IF NOT EXISTS idx_image_generations_character ON image_generations(character_name);

-- Add image_data column to video_generations table
ALTER TABLE video_generations ADD COLUMN image_data JSONB;