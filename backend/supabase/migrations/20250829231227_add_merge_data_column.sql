-- Add merge_data column to video_generations table
ALTER TABLE video_generations ADD COLUMN merge_data JSONB;

-- Update video generation status enum to include merging_audio (if using ENUM)
-- ALTER TYPE video_generation_status ADD VALUE IF NOT EXISTS 'merging_audio';

-- Create index for faster merge status queries
CREATE INDEX IF NOT EXISTS idx_video_generations_merge_status ON video_generations(generation_status);