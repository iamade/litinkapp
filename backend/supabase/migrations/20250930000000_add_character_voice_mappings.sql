-- Add character_voice_mappings column to video_generations table
ALTER TABLE video_generations ADD COLUMN character_voice_mappings JSONB;