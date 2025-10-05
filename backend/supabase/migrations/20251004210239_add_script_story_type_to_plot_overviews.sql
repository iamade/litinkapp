-- Migration: Add script_story_type column to plot_overviews table
-- Purpose: Enables Phase 1B non-fiction content handling by supporting story type metadata
-- Up Migration
BEGIN;

ALTER TABLE plot_overviews
ADD COLUMN script_story_type TEXT;

-- COMMENT: Type of story (e.g., fiction, non-fiction, documentary, etc.) for Phase 1B content handling

COMMIT;

-- Down Migration
BEGIN;

ALTER TABLE plot_overviews
DROP COLUMN script_story_type;

COMMIT;