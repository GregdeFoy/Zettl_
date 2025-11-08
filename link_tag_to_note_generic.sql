-- Generic script to link all notes with a specific tag to a target note
-- Usage: Replace 'YOUR_TAG' and 'TARGET_NOTE_ID' with actual values

-- Configuration variables (modify these)
-- Example: 'blackbird' and 'bb'
\set tag_name 'YOUR_TAG'
\set target_note 'TARGET_NOTE_ID'
\set user_id 1

-- Disable RLS and triggers
SET row_security TO off;
ALTER TABLE links DISABLE TRIGGER ALL;

-- Insert the links (skip if already exists)
INSERT INTO links (source_id, target_id, user_id)
SELECT :'target_note', note_id, :user_id
FROM tags
WHERE tag = :'tag_name'
  AND note_id <> :'target_note'
ON CONFLICT (user_id, source_id, target_id) DO NOTHING;

-- Re-enable triggers
ALTER TABLE links ENABLE TRIGGER ALL;

-- Show results
SELECT 'Linking complete!' as status,
       :'tag_name' as tag_used,
       :'target_note' as linked_to_note,
       COUNT(*) as total_links
FROM links
WHERE source_id = :'target_note'
  AND target_id IN (
    SELECT note_id FROM tags WHERE tag = :'tag_name'
  );