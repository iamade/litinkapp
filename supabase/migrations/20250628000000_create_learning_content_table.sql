-- Create learning_content table for storing AI-generated audio and video content
CREATE TABLE IF NOT EXISTS learning_content (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    content_type TEXT NOT NULL CHECK (content_type IN ('audio_narration', 'realistic_video')),
    content_url TEXT,
    script TEXT,
    duration INTEGER DEFAULT 180,
    status TEXT DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_learning_content_chapter_id ON learning_content(chapter_id);
CREATE INDEX IF NOT EXISTS idx_learning_content_book_id ON learning_content(book_id);
CREATE INDEX IF NOT EXISTS idx_learning_content_user_id ON learning_content(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_content_type ON learning_content(content_type);
CREATE INDEX IF NOT EXISTS idx_learning_content_status ON learning_content(status);

-- Enable RLS (Row Level Security)
ALTER TABLE learning_content ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can view their own learning content" ON learning_content
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own learning content" ON learning_content
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own learning content" ON learning_content
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own learning content" ON learning_content
    FOR DELETE USING (auth.uid() = user_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_learning_content_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_learning_content_updated_at
    BEFORE UPDATE ON learning_content
    FOR EACH ROW
    EXECUTE FUNCTION update_learning_content_updated_at(); 