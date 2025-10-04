-- Remove the unique constraint from scripts table
ALTER TABLE scripts DROP CONSTRAINT scripts_chapter_id_user_id_script_style_key;

-- Add new columns to scripts table (no DEFAULTs)
ALTER TABLE scripts ADD COLUMN version INTEGER;
ALTER TABLE scripts ADD COLUMN evaluation_score INTEGER;
ALTER TABLE scripts ADD COLUMN evaluation_feedback TEXT;
ALTER TABLE scripts ADD COLUMN character_ids UUID[];

-- Set default values
ALTER TABLE scripts ALTER COLUMN version SET DEFAULT 1;
ALTER TABLE scripts ALTER COLUMN status SET DEFAULT 'draft';
ALTER TABLE scripts ALTER COLUMN character_ids SET DEFAULT ARRAY[]::UUID[];

-- Add CHECK constraint for status values
ALTER TABLE scripts ADD CONSTRAINT scripts_status_check CHECK (status IN ('draft', 'evaluated', 'approved', 'rejected', 'active'));

-- Create indexes for new columns
CREATE INDEX idx_scripts_status ON scripts(status);
CREATE INDEX idx_scripts_version ON scripts(version);
CREATE INDEX idx_scripts_evaluation_score ON scripts(evaluation_score);
CREATE INDEX idx_scripts_character_ids ON scripts USING GIN(character_ids);

-- Update existing records to set default status
UPDATE scripts SET status = 'active' WHERE status IS NULL AND script IS NOT NULL;

-- Down migration
-- Drop indexes
DROP INDEX idx_scripts_character_ids;
DROP INDEX idx_scripts_evaluation_score;
DROP INDEX idx_scripts_version;
DROP INDEX idx_scripts_status;

-- Remove new columns and constraint
ALTER TABLE scripts DROP CONSTRAINT scripts_status_check;
ALTER TABLE scripts DROP COLUMN character_ids;
ALTER TABLE scripts DROP COLUMN evaluation_feedback;
ALTER TABLE scripts DROP COLUMN evaluation_score;
ALTER TABLE scripts DROP COLUMN status;
ALTER TABLE scripts DROP COLUMN version;

-- Restore unique constraint
ALTER TABLE scripts ADD CONSTRAINT scripts_chapter_id_user_id_script_style_key UNIQUE (chapter_id, user_id, script_style);