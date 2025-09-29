-- Add updated_at column to image_generations table
ALTER TABLE image_generations ADD COLUMN updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;