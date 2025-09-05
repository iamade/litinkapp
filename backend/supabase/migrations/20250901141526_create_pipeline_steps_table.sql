-- Add resume capability to video_generations table
ALTER TABLE video_generations 
ADD COLUMN IF NOT EXISTS pipeline_state JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS failed_at_step TEXT,
ADD COLUMN IF NOT EXISTS can_resume BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

-- Create pipeline_steps table to track individual step status
CREATE TABLE IF NOT EXISTS pipeline_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_generation_id UUID REFERENCES video_generations(id) ON DELETE CASCADE,
    step_name TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed, skipped
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    step_data JSONB DEFAULT '{}',
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(video_generation_id, step_name)
);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_video_gen_id ON pipeline_steps(video_generation_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_status ON pipeline_steps(status);