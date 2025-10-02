-- Add retry tracking columns to video_generations table
-- This migration adds support for automatic retry logic and manual resume capability
-- Using idempotent pattern with IF NOT EXISTS checks for safe re-runs

-- Add retry_count column
ALTER TABLE video_generations 
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

-- Add last_retry_at column
ALTER TABLE video_generations 
ADD COLUMN IF NOT EXISTS last_retry_at TIMESTAMP WITH TIME ZONE;

-- Add can_resume column
ALTER TABLE video_generations 
ADD COLUMN IF NOT EXISTS can_resume BOOLEAN DEFAULT false;

-- Add helpful comments for each column
COMMENT ON COLUMN video_generations.retry_count IS 'Number of retry attempts for video generation failures';
COMMENT ON COLUMN video_generations.last_retry_at IS 'Timestamp of the last retry attempt';
COMMENT ON COLUMN video_generations.can_resume IS 'Indicates if manual retry/resume is available for this generation';

-- Create index for retry_count to optimize queries for retry logic
CREATE INDEX IF NOT EXISTS idx_video_generations_retry_count ON video_generations(retry_count);

-- Create index for can_resume to quickly find generations that can be manually resumed
CREATE INDEX IF NOT EXISTS idx_video_generations_can_resume ON video_generations(can_resume);