-- Add script_story_type column to scripts table
-- Purpose: Store the script story type directly in the scripts table for easier access
-- Up Migration
BEGIN;

ALTER TABLE plot_overview ADD COLUMN script_story_type TEXT;

-- COMMENT: Type of story (e.g., fiction, non-fiction, documentary, etc.) for the script
COMMENT ON COLUMN plot_overview.script_story_type IS 'Type of story (e.g., fiction, non-fiction, documentary, etc.) for the script';

COMMIT;

-- Down Migration
BEGIN;

ALTER TABLE plot_overview DROP COLUMN script_story_type;

COMMIT;