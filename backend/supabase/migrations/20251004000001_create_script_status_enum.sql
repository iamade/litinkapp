-- First update existing data
UPDATE scripts SET status = 'draft' WHERE status = 'ready';

-- Add the check constraint
ALTER TABLE scripts ADD CONSTRAINT scripts_status_check 
    CHECK (status IN ('draft', 'evaluated', 'approved', 'rejected', 'active', 'ready'));

-- Set the default value
ALTER TABLE scripts ALTER COLUMN status SET DEFAULT 'draft';