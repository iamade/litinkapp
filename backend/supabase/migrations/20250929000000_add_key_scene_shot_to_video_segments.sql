-- Add key_scene_shot_url column to video_segments table for sequential video generation
ALTER TABLE video_segments ADD COLUMN key_scene_shot_url TEXT;

-- Add comment for documentation
COMMENT ON COLUMN video_segments.key_scene_shot_url IS 'URL of the last frame extracted from this video segment, used as starting image for next scene';

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_video_segments_key_scene_shot ON video_segments(key_scene_shot_url);