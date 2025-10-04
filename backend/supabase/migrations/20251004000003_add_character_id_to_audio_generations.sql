-- Add character_id column to audio_generations table
ALTER TABLE audio_generations ADD COLUMN character_id UUID;

-- Add foreign key constraint with ON DELETE SET NULL
ALTER TABLE audio_generations
ADD CONSTRAINT fk_audio_generations_character_id
FOREIGN KEY (character_id)
REFERENCES characters(id)
ON DELETE SET NULL;

-- Create index for character_id
CREATE INDEX idx_audio_generations_character_id ON audio_generations(character_id);

-- Down migration
-- Drop index
DROP INDEX idx_audio_generations_character_id;

-- Drop foreign key constraint
ALTER TABLE audio_generations DROP CONSTRAINT fk_audio_generations_character_id;

-- Remove column
ALTER TABLE audio_generations DROP COLUMN character_id;