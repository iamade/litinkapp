-- Fix audio_generations table schema
ALTER TABLE audio_generations 
ADD COLUMN IF NOT EXISTS duration FLOAT,
ADD COLUMN IF NOT EXISTS generation_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS sequence_order INTEGER;

-- Update existing records
UPDATE audio_generations SET generation_status = 'completed' WHERE generation_status IS NULL AND audio_url IS NOT NULL;
UPDATE audio_generations SET generation_status = 'failed' WHERE generation_status IS NULL AND audio_url IS NULL;