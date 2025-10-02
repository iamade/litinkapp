--- Add preview_url field to merge_operations table for storing preview video URLs
ALTER TABLE merge_operations ADD COLUMN preview_url TEXT;

-- Add comment for documentation
COMMENT ON COLUMN merge_operations.preview_url IS 'URL of the generated preview video clip (first 10 seconds of merged output)';