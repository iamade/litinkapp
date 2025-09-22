-- Add the 3 missing enum values
ALTER TYPE video_generation_status ADD VALUE 'audio_completed';
ALTER TYPE video_generation_status ADD VALUE 'images_completed'; 
ALTER TYPE video_generation_status ADD VALUE 'video_completed';