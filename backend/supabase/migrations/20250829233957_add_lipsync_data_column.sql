-- Run these one by one in Supabase SQL editor:
ALTER TYPE video_generation_status ADD VALUE 'applying_lipsync';
ALTER TYPE video_generation_status ADD VALUE 'lipsync_completed'; 
ALTER TYPE video_generation_status ADD VALUE 'lipsync_failed';

-- Then add the column
ALTER TABLE video_generations ADD COLUMN lipsync_data JSONB;

-- Finally create the index
CREATE INDEX idx_video_generations_lipsync_status ON video_generations(generation_status);