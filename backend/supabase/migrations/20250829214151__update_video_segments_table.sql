-- Add only the missing columns to existing video_segments table
ALTER TABLE video_segments ADD COLUMN scene_description TEXT;
ALTER TABLE video_segments ADD COLUMN source_image_url TEXT;
ALTER TABLE video_segments ADD COLUMN fps INTEGER;
ALTER TABLE video_segments ADD COLUMN generation_method VARCHAR(50);
ALTER TABLE video_segments ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Update existing records to have default values for newly added columns
-- This section was causing the syntax error. Each update needs its own WHERE clause.
UPDATE video_segments SET fps = 24 WHERE fps IS NULL;
UPDATE video_segments SET generation_method = 'image_to_video' WHERE generation_method IS NULL;
UPDATE video_segments SET updated_at = NOW() WHERE updated_at IS NULL;

-- Set default values for new columns for future inserts
ALTER TABLE video_segments ALTER COLUMN fps SET DEFAULT 24;
-- If you also want defaults for generation_method and updated_at for new rows:
-- ALTER TABLE video_segments ALTER COLUMN generation_method SET DEFAULT 'image_to_video';
-- ALTER TABLE video_segments ALTER COLUMN updated_at SET DEFAULT NOW();

-- Create additional indexes for new columns
CREATE INDEX IF NOT EXISTS idx_video_segments_generation_method ON video_segments(generation_method);

-- Add video_data column to video_generations table
ALTER TABLE video_generations ADD COLUMN video_data JSONB;

-- Update the status column to accommodate new status values
ALTER TABLE video_segments ALTER COLUMN status TYPE VARCHAR(50);
