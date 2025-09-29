CREATE POLICY "Users can insert their own image generations" ON image_generations
    FOR INSERT WITH CHECK (auth.uid() = user_id);