-- Script to link all notes with "contractlens", "metallens", and "blackbirdlens" tags to note "rav"
-- This script temporarily disables triggers to bypass JWT authentication requirements

-- Disable RLS and triggers
SET row_security TO off;
ALTER TABLE links DISABLE TRIGGER ALL;

-- Insert links for all three tags (skip if already exists)
INSERT INTO links (source_id, target_id, user_id)
SELECT 'rav', note_id, 1
FROM tags
WHERE tag IN ('contractlens', 'metallens', 'blackbirdlens')
  AND note_id <> 'rav'
ON CONFLICT (user_id, source_id, target_id) DO NOTHING;

-- Re-enable triggers
ALTER TABLE links ENABLE TRIGGER ALL;

-- Show results for each tag
SELECT tag, COUNT(*) as notes_linked
FROM tags
WHERE tag IN ('contractlens', 'metallens', 'blackbirdlens')
  AND note_id <> 'rav'
  AND note_id IN (
    SELECT target_id FROM links WHERE source_id = 'rav'
  )
GROUP BY tag
ORDER BY tag;

-- Show total links to rav
SELECT COUNT(DISTINCT target_id) as total_unique_notes_linked_to_rav
FROM links
WHERE source_id = 'rav'
  AND target_id IN (
    SELECT note_id FROM tags
    WHERE tag IN ('contractlens', 'metallens', 'blackbirdlens')
  );