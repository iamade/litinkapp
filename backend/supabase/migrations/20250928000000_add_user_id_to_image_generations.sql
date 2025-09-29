-- Add user_id column to image_generations table for standalone image support
ALTER TABLE image_generations ADD COLUMN user_id UUID;
ALTER TABLE image_generations ADD CONSTRAINT fk_image_generations_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id);

-- Update existing records to have user_id from their video_generation
UPDATE image_generations
SET user_id = video_generations.user_id
FROM video_generations
WHERE image_generations.video_generation_id = video_generations.id
AND image_generations.user_id IS NULL;

-- Create index for user_id
CREATE INDEX IF NOT EXISTS idx_image_generations_user_id ON image_generations(user_id);

-- Update RLS policies to handle standalone images
DROP POLICY IF EXISTS "Users can view image generations for their videos" ON image_generations;
CREATE POLICY "Users can view their image generations" ON image_generations
    FOR SELECT USING (
        auth.uid() = user_id OR
        EXISTS (
            SELECT 1 FROM video_generations
            WHERE video_generations.id = image_generations.video_generation_id
            AND video_generations.user_id = auth.uid()
        )
    );