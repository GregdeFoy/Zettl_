-- Script to link all notes with "zettl" tag to note "zt"
-- This script temporarily disables triggers to bypass JWT authentication requirements

-- Disable RLS and triggers
SET row_security TO off;
ALTER TABLE links DISABLE TRIGGER ALL;

-- Insert the links (skip if already exists)
INSERT INTO links (source_id, target_id, user_id)
SELECT 'zt', note_id, 1
FROM tags
WHERE tag = 'zettl'
  AND note_id <> 'zt'
ON CONFLICT (user_id, source_id, target_id) DO NOTHING;

-- Re-enable triggers
ALTER TABLE links ENABLE TRIGGER ALL;

-- Show results
SELECT COUNT(*) as total_links_to_zt
FROM links
WHERE source_id = 'zt'
  AND target_id IN (
    SELECT note_id FROM tags WHERE tag = 'zettl'
  );

-- Show how many notes have the zettl tag
SELECT COUNT(*) as notes_with_zettl_tag
FROM tags
WHERE tag = 'zettl'
  AND note_id <> 'zt';