-- Add Tavus-related fields to existing learning_content table
-- This migration adds the missing fields needed for Tavus video generation tracking

-- Add new columns to learning_content table
ALTER TABLE learning_content ADD COLUMN tavus_video_id TEXT;
ALTER TABLE learning_content ADD COLUMN tavus_url TEXT;
ALTER TABLE learning_content ADD COLUMN tavus_response JSONB;
ALTER TABLE learning_content ADD COLUMN error_message TEXT;
ALTER TABLE learning_content ADD COLUMN generation_progress TEXT;
ALTER TABLE learning_content ADD COLUMN video_segments JSONB;
ALTER TABLE learning_content ADD COLUMN combined_video_url TEXT;

-- Set default values after adding columns
UPDATE learning_content SET generation_progress = '0/100' WHERE generation_progress IS NULL;
UPDATE learning_content SET video_segments = '[]' WHERE video_segments IS NULL;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_learning_content_tavus_video_id ON learning_content(tavus_video_id);
CREATE INDEX IF NOT EXISTS idx_learning_content_tavus_url ON learning_content(tavus_url);
CREATE INDEX IF NOT EXISTS idx_learning_content_generation_progress ON learning_content(generation_progress);

-- Add comments to explain the new fields
COMMENT ON COLUMN learning_content.tavus_video_id IS 'Tavus video ID for tracking video generation';
COMMENT ON COLUMN learning_content.tavus_url IS 'Tavus hosted URL for the video';
COMMENT ON COLUMN learning_content.tavus_response IS 'Full Tavus API response for debugging';
COMMENT ON COLUMN learning_content.error_message IS 'Detailed error message if generation fails';
COMMENT ON COLUMN learning_content.generation_progress IS 'Current generation progress (e.g., 37/100)';
COMMENT ON COLUMN learning_content.video_segments IS 'Array of video segment URLs to be combined';
COMMENT ON COLUMN learning_content.combined_video_url IS 'Final combined video URL after FFmpeg processing'; 