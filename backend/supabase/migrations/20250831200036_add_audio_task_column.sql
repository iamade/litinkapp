-- Add task tracking columns to video_generations table
ALTER TABLE video_generations 
ADD COLUMN audio_task_id TEXT,
ADD COLUMN task_metadata JSONB;

-- Add index for performance on task lookups
CREATE INDEX idx_video_generations_audio_task ON video_generations(audio_task_id);

-- Add index for task metadata queries (optional but useful)
CREATE INDEX idx_video_generations_task_metadata ON video_generations USING GIN(task_metadata);ai