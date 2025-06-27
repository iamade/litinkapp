-- Add columns for book processing status tracking
ALTER TABLE books ADD COLUMN error_message TEXT;
ALTER TABLE books ADD COLUMN progress INTEGER DEFAULT 0;
ALTER TABLE books ADD COLUMN total_steps INTEGER DEFAULT 4;
ALTER TABLE books ADD COLUMN progress_message TEXT; 