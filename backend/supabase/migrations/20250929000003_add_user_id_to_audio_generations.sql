-- Add user_id column to audio_generations table
ALTER TABLE audio_generations
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add index for user_id
CREATE INDEX IF NOT EXISTS idx_audio_generations_user_id ON audio_generations(user_id);

-- Update existing records to set user_id from related video_generations
UPDATE audio_generations
SET user_id = video_generations.user_id
FROM video_generations
WHERE audio_generations.video_generation_id = video_generations.id
AND audio_generations.user_id IS NULL;