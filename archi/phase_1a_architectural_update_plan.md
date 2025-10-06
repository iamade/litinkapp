# Phase 1A Architectural Update - Database Migration Plan

## Overview
This document contains the complete SQL migration scripts for Phase 1A of the architectural update, focusing on database schema changes for enhanced script management and character integration.

## Migration Files Required

### 1. Script Status Enum and Scripts Table Updates

**File:** `20251004000001_create_script_status_enum.sql`

```sql
-- Create script_status enum type
CREATE TYPE script_status AS ENUM (
    'draft',
    'evaluated', 
    'approved',
    'rejected',
    'active'
);

-- Remove the unique constraint from scripts table
ALTER TABLE scripts DROP CONSTRAINT IF EXISTS scripts_chapter_id_user_id_script_style_key;

-- Add new columns to scripts table
ALTER TABLE scripts 
ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS status script_status DEFAULT 'draft',
ADD COLUMN IF NOT EXISTS evaluation_score INTEGER,
ADD COLUMN IF NOT EXISTS evaluation_feedback TEXT,
ADD COLUMN IF NOT EXISTS character_ids UUID[] DEFAULT '{}';

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_scripts_status ON scripts(status);
CREATE INDEX IF NOT EXISTS idx_scripts_version ON scripts(version);
CREATE INDEX IF NOT EXISTS idx_scripts_evaluation_score ON scripts(evaluation_score);
CREATE INDEX IF NOT EXISTS idx_scripts_character_ids ON scripts USING GIN(character_ids);

-- Update existing records to set default status
UPDATE scripts SET status = 'active' WHERE status IS NULL AND script IS NOT NULL;
```

### 2. Image Generations Table Update

**File:** `20251004000002_add_character_id_to_image_generations.sql`

```sql
-- Add character_id column to image_generations table
ALTER TABLE image_generations 
ADD COLUMN IF NOT EXISTS character_id UUID;

-- Add foreign key constraint with ON DELETE SET NULL
ALTER TABLE image_generations 
ADD CONSTRAINT fk_image_generations_character_id 
FOREIGN KEY (character_id) 
REFERENCES characters(id) 
ON DELETE SET NULL;

-- Create index for character_id
CREATE INDEX IF NOT EXISTS idx_image_generations_character_id ON image_generations(character_id);

-- Update RLS policy to include character-based access
DROP POLICY IF EXISTS "Users can view image generations for their videos" ON image_generations;
CREATE POLICY "Users can view their image generations" ON image_generations
    FOR SELECT USING (
        auth.uid() = user_id OR
        EXISTS (
            SELECT 1 FROM video_generations 
            WHERE video_generations.id = image_generations.video_generation_id 
            AND video_generations.user_id = auth.uid()
        )
    );
```

### 3. Audio Generations Table Update

**File:** `20251004000003_add_character_id_to_audio_generations.sql`

```sql
-- Add character_id column to audio_generations table
ALTER TABLE audio_generations 
ADD COLUMN IF NOT EXISTS character_id UUID;

-- Add foreign key constraint with ON DELETE SET NULL
ALTER TABLE audio_generations 
ADD CONSTRAINT fk_audio_generations_character_id 
FOREIGN KEY (character_id) 
REFERENCES characters(id) 
ON DELETE SET NULL;

-- Create index for character_id
CREATE INDEX IF NOT EXISTS idx_audio_generations_character_id ON audio_generations(character_id);

-- Update RLS policy to include character-based access
DROP POLICY IF EXISTS "Users can view audio generations for their videos" ON audio_generations;
CREATE POLICY "Users can view their audio generations" ON audio_generations
    FOR SELECT USING (
        auth.uid() = user_id OR
        EXISTS (
            SELECT 1 FROM video_generations 
            WHERE video_generations.id = audio_generations.video_generation_id 
            AND video_generations.user_id = auth.uid()
        )
    );
```

## Summary of Changes

### Tables Modified:
1. **scripts** - Major enhancements for versioning and evaluation
2. **image_generations** - Character association for images
3. **audio_generations** - Character association for audio

### New Features:
- **Script Versioning**: Track multiple versions of scripts with status management
- **Script Evaluation**: Score and feedback system for script quality assessment
- **Character Integration**: Link scripts, images, and audio to specific characters
- **Workflow Status**: Support for draft, evaluated, approved, rejected, and active states

### Performance Considerations:
- Added indexes for all new foreign keys and frequently queried columns
- Used GIN index for character_ids array for efficient array operations
- Maintained existing RLS policies while enhancing them for new access patterns

### Data Integrity:
- Foreign key constraints with proper ON DELETE behavior
- Default values for new columns to ensure backward compatibility
- Enum type for status to enforce valid values

## Migration Order
1. Create script_status enum type first
2. Update scripts table with new columns and remove constraint
3. Update image_generations table with character_id
4. Update audio_generations table with character_id

## Rollback Plan
Each migration file should include corresponding down migrations to rollback changes if needed.

## Testing Considerations
- Verify existing data integrity after migrations
- Test new foreign key constraints
- Validate RLS policies with new access patterns
- Ensure backward compatibility with existing application code