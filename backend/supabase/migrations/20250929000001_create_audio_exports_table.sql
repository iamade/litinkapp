-- Create audio_exports table for chapter audio mixing
CREATE TABLE IF NOT EXISTS audio_exports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL,
    export_format TEXT DEFAULT 'mp3',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    download_url TEXT,
    audio_files JSONB, -- Array of audio file IDs included in the export
    mix_settings JSONB DEFAULT '{}', -- Mixing settings like volumes, effects
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_audio_exports_user_id ON audio_exports(user_id);
CREATE INDEX IF NOT EXISTS idx_audio_exports_chapter_id ON audio_exports(chapter_id);
CREATE INDEX IF NOT EXISTS idx_audio_exports_status ON audio_exports(status);