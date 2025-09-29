-- Add script_name column to scripts table
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS script_name VARCHAR(255);