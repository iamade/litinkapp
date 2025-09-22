-- Create new migration file
-- filepath: /Users/adesegunkoiki/My_app_projects/People-Protocol-apps/litinkapp/backend/supabase/migrations/20250905144500_add_audio_model_columns.sql

-- Add missing columns to audio_generations table for V7 compatibility
ALTER TABLE audio_generations 
ADD COLUMN IF NOT EXISTS model_id VARCHAR(100) DEFAULT 'eleven_multilingual_v2',
ADD COLUMN IF NOT EXISTS voice_model VARCHAR(100),
ADD COLUMN IF NOT EXISTS audio_format VARCHAR(20) DEFAULT 'mp3',
ADD COLUMN IF NOT EXISTS generation_time_seconds FLOAT,
ADD COLUMN IF NOT EXISTS audio_length_seconds FLOAT,
ADD COLUMN IF NOT EXISTS service_provider VARCHAR(50) DEFAULT 'modelslab_v7';

-- Update existing records with default values
UPDATE audio_generations 
SET model_id = 'eleven_multilingual_v2',
    service_provider = 'modelslab_v7',
    audio_format = 'mp3'
WHERE model_id IS NULL;

-- Also add index for better performance
CREATE INDEX IF NOT EXISTS idx_audio_generations_model_id ON audio_generations(model_id);
CREATE INDEX IF NOT EXISTS idx_audio_generations_service ON audio_generations(service_provider);