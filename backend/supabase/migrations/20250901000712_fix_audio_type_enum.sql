
-- Drop the existing enum constraint temporarily
ALTER TABLE audio_generations 
ALTER COLUMN audio_type TYPE TEXT;

-- Recreate enum with all needed values
DROP TYPE IF EXISTS audio_type CASCADE;
CREATE TYPE audio_type AS ENUM (
    'narrator',
    'character', 
    'sound_effect',
    'background_music',
    'music',
    'sfx'
);

-- Apply the enum back to the column
ALTER TABLE audio_generations 
ALTER COLUMN audio_type TYPE audio_type USING audio_type::audio_type;