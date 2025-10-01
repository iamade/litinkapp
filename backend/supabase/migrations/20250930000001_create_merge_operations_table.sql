-- Create enum for merge_status
CREATE TYPE "public"."merge_status" AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED');

-- Create merge_operations table
CREATE TABLE merge_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    video_file_url TEXT,
    audio_file_url TEXT,
    merge_status "public"."merge_status" DEFAULT 'PENDING',
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    output_file_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_merge_operations_user_id ON merge_operations(user_id);
CREATE INDEX idx_merge_operations_status ON merge_operations(merge_status);