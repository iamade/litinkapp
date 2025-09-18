-- Add missing service_used column to scripts table (no default, let code set explicitly)
ALTER TABLE scripts 
ADD COLUMN IF NOT EXISTS service_used VARCHAR(50);

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_scripts_service_used ON scripts(service_used);