-- Add script_story_type to plot_overviews and scripts safely (no-op if table/column missing)
ALTER TABLE IF EXISTS plot_overviews ADD COLUMN script_story_type TEXT;
COMMENT ON COLUMN plot_overviews.script_story_type IS
  'Type of story (e.g., fiction, non-fiction, documentary, etc.) for the script';

ALTER TABLE IF EXISTS scripts
  ADD COLUMN script_story_type TEXT;
COMMENT ON COLUMN scripts.script_story_type IS
  'Type of story (e.g., fiction, non-fiction, documentary, etc.) for the script';

COMMIT;

-- Down migration: remove columns (safe: only if exist)

ALTER TABLE IF EXISTS scripts DROP COLUMN IF EXISTS script_story_type;
ALTER TABLE IF EXISTS plot_overviews DROP COLUMN IF EXISTS script_story_type;
COMMIT;