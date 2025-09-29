
-- Add missing columns to image_generations table
ALTER TABLE image_generations 
ADD COLUMN IF NOT EXISTS prompt TEXT,
ADD COLUMN IF NOT EXISTS model_id VARCHAR(100) DEFAULT 'gen4_image',
ADD COLUMN IF NOT EXISTS aspect_ratio VARCHAR(20) DEFAULT '16:9',
ADD COLUMN IF NOT EXISTS style VARCHAR(50),
ADD COLUMN IF NOT EXISTS service_provider VARCHAR(50) DEFAULT 'modelslab_v7';

-- Update existing records
UPDATE image_generations 
SET prompt = COALESCE(image_prompt, scene_description, 'Generated image'),
    model_id = 'gen4_image',
    service_provider = 'modelslab_v7',
    aspect_ratio = CASE 
        WHEN image_type = 'character' THEN '3:4'
        WHEN image_type = 'scene' THEN '16:9'
        ELSE '16:9'
    END
WHERE prompt IS NULL;