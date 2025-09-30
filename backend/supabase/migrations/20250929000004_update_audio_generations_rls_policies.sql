-- Update audio_generations RLS policies to match image_generations pattern
-- Add foreign key constraint for user_id
ALTER TABLE audio_generations ADD CONSTRAINT fk_audio_generations_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id);

-- Drop the old policy that only checks via video_generations
DROP POLICY "Users can view audio generations for their videos" ON audio_generations;

-- Create new SELECT policy that allows direct user_id access and video-based access
CREATE POLICY "Users can view their audio generations" ON audio_generations
    FOR SELECT USING (
        auth.uid() = user_id OR
        EXISTS (
            SELECT 1 FROM video_generations
            WHERE video_generations.id = audio_generations.video_generation_id
            AND video_generations.user_id = auth.uid()
        )
    );

-- Create INSERT policy for direct user_id check
CREATE POLICY "Users can insert their own audio generations" ON audio_generations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Note: UPDATE and DELETE policies rely on the SELECT policy for security
-- since RLS applies to all operations when policies are defined