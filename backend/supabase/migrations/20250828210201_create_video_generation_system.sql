-- Create ENUM types first
CREATE TYPE video_generation_status AS ENUM (
    'pending', 
    'generating_audio', 
    'generating_images', 
    'generating_video', 
    'combining', 
    'completed', 
    'failed'
);

CREATE TYPE video_quality_tier AS ENUM (
    'basic',      -- Veo 2
    'standard',   -- Kling V1.0
    'standard_2', -- Veo 3 Standard
    'pro',        -- Veo 3 Fast
    'master'      -- Kling V2.1
);

CREATE TYPE audio_type AS ENUM (
    'narrator',
    'character',
    'sound_effects',
    'background_music'
);

-- Scripts table for persisting generated scripts
CREATE TABLE IF NOT EXISTS scripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    script_style VARCHAR(50) NOT NULL DEFAULT 'cinematic_movie',
    script TEXT NOT NULL,
    scene_descriptions JSONB DEFAULT '[]',
    characters JSONB DEFAULT '[]',
    character_details TEXT,
    metadata JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'ready',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure one script per user per chapter per style
    UNIQUE(chapter_id, user_id, script_style)
);

-- Video generations table
CREATE TABLE IF NOT EXISTS video_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
    script_id UUID REFERENCES scripts(id) ON DELETE SET NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    generation_status video_generation_status DEFAULT 'pending',
    quality_tier video_quality_tier DEFAULT 'basic',
    video_url TEXT,
    subtitle_url TEXT,
    thumbnail_url TEXT,
    duration_seconds DECIMAL,
    file_size_bytes BIGINT,
    script_data JSONB,
    audio_files JSONB DEFAULT '[]',
    image_files JSONB DEFAULT '[]',
    video_segments JSONB DEFAULT '[]',
    progress_log JSONB DEFAULT '[]',
    error_message TEXT,
    processing_time_seconds DECIMAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Audio generations tracking
CREATE TABLE IF NOT EXISTS audio_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_generation_id UUID REFERENCES video_generations(id) ON DELETE CASCADE,
    audio_type audio_type NOT NULL,
    scene_id VARCHAR(50),
    character_name VARCHAR(100),
    text_content TEXT,
    voice_id VARCHAR(100),
    audio_url TEXT,
    duration_seconds DECIMAL,
    file_size_bytes BIGINT,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Image generations tracking
CREATE TABLE IF NOT EXISTS image_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_generation_id UUID REFERENCES video_generations(id) ON DELETE CASCADE,
    scene_id VARCHAR(50),
    shot_index INTEGER DEFAULT 0,
    scene_description TEXT,
    image_prompt TEXT,
    image_url TEXT,
    thumbnail_url TEXT,
    width INTEGER,
    height INTEGER,
    file_size_bytes BIGINT,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    generation_time_seconds DECIMAL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Video segments tracking
CREATE TABLE IF NOT EXISTS video_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_generation_id UUID REFERENCES video_generations(id) ON DELETE CASCADE,
    scene_id VARCHAR(50),
    segment_index INTEGER NOT NULL,
    video_url TEXT,
    thumbnail_url TEXT,
    duration_seconds DECIMAL,
    width INTEGER,
    height INTEGER,
    file_size_bytes BIGINT,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    processing_service VARCHAR(50), -- 'veo2', 'kling', 'veo3', etc.
    processing_model VARCHAR(100),
    generation_time_seconds DECIMAL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_scripts_chapter_user ON scripts(chapter_id, user_id);
CREATE INDEX idx_scripts_style ON scripts(script_style);
CREATE INDEX idx_video_generations_user ON video_generations(user_id);
CREATE INDEX idx_video_generations_chapter ON video_generations(chapter_id);
CREATE INDEX idx_video_generations_script ON video_generations(script_id);
CREATE INDEX idx_video_generations_status ON video_generations(generation_status);

-- Row Level Security (RLS) policies
ALTER TABLE scripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audio_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_segments ENABLE ROW LEVEL SECURITY;

-- Scripts policies
CREATE POLICY "Users can manage their own scripts" ON scripts
    FOR ALL USING (auth.uid() = user_id);

-- Video generations policies
CREATE POLICY "Users can manage their own video generations" ON video_generations
    FOR ALL USING (auth.uid() = user_id);

-- Audio generations policies (inherit from video_generations)
CREATE POLICY "Users can view audio generations for their videos" ON audio_generations
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM video_generations 
            WHERE video_generations.id = audio_generations.video_generation_id 
            AND video_generations.user_id = auth.uid()
        )
    );

-- Similar policies for image_generations and video_segments
CREATE POLICY "Users can view image generations for their videos" ON image_generations
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM video_generations 
            WHERE video_generations.id = image_generations.video_generation_id 
            AND video_generations.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view video segments for their videos" ON video_segments
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM video_generations 
            WHERE video_generations.id = video_segments.video_generation_id 
            AND video_generations.user_id = auth.uid()
        )
    );