-- Add additional fields to merge_operations table for enhanced merge tracking
ALTER TABLE merge_operations ADD COLUMN input_sources JSONB;
ALTER TABLE merge_operations ADD COLUMN quality_tier TEXT;
ALTER TABLE merge_operations ADD COLUMN output_format TEXT;
ALTER TABLE merge_operations ADD COLUMN ffmpeg_params JSONB;
ALTER TABLE merge_operations ADD COLUMN merge_name TEXT;
ALTER TABLE merge_operations ADD COLUMN error_message TEXT;
ALTER TABLE merge_operations ADD COLUMN processing_stats JSONB;

-- Update existing records to have default values
UPDATE merge_operations
SET
    input_sources = '[]'::jsonb,
    quality_tier = 'web',
    output_format = 'mp4',
    ffmpeg_params = NULL,
    merge_name = 'Merge Operation',
    error_message = NULL,
    processing_stats = '{}'::jsonb
WHERE input_sources IS NULL;

-- Add comments for documentation
COMMENT ON COLUMN merge_operations.input_sources IS 'Array of input file sources for the merge operation';
COMMENT ON COLUMN merge_operations.quality_tier IS 'Quality tier for the merge output (web, medium, high, custom)';
COMMENT ON COLUMN merge_operations.output_format IS 'Output format for the merged file (mp4, webm, mov)';
COMMENT ON COLUMN merge_operations.ffmpeg_params IS 'Custom FFmpeg parameters for advanced processing';
COMMENT ON COLUMN merge_operations.merge_name IS 'User-defined name for the merge operation';
COMMENT ON COLUMN merge_operations.error_message IS 'Error message if the merge operation failed';
COMMENT ON COLUMN merge_operations.processing_stats IS 'Statistics and metadata from the merge processing';