-- Add chapter_id column to audio_generations table for chapter-specific audio
ALTER TABLE audio_generations ADD COLUMN chapter_id UUID;

-- Add index for chapter_id
CREATE INDEX idx_audio_generations_chapter_id ON audio_generations(chapter_id);