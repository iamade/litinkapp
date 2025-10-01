-- Add merge_failed_at column to video_generations table for tracking merge task failures
ALTER TABLE video_generations ADD COLUMN merge_failed_at TIMESTAMPTZ;

-- Add comment for documentation
COMMENT ON COLUMN video_generations.merge_failed_at IS 'Timestamp when the video merge task failed, used for error tracking and retry logic';