-- Script to link all notes with "blackbirdrates" tag to note "br"
-- Running as superuser to bypass RLS

-- First, check what we have
SELECT 'Notes with blackbirdrates tag:' as info;
SELECT user_id, note_id FROM tags WHERE tag = 'blackbirdrates';

SELECT 'Note br exists for users:' as info;
SELECT user_id, id FROM notes WHERE id = 'br';

-- Create links from note "br" to all notes with "blackbirdrates" tag
-- Using superuser privileges to bypass RLS
SET SESSION AUTHORIZATION postgres;
SET row_security TO off;

INSERT INTO links (source_id, target_id, user_id, context)
SELECT DISTINCT
    'br' as source_id,
    t.note_id as target_id,
    t.user_id,
    'BlackbirdRates collection' as context
FROM tags t
WHERE t.tag = 'blackbirdrates'
  AND t.note_id != 'br'  -- Don't link to itself
  AND EXISTS (
    -- Ensure note "br" exists for this user
    SELECT 1 FROM notes n
    WHERE n.id = 'br' AND n.user_id = t.user_id
  )
ON CONFLICT (user_id, source_id, target_id) DO NOTHING;

-- Show results
SELECT 'Links created:' as info;
SELECT COUNT(*) as links_created
FROM links
WHERE source_id = 'br'
  AND target_id IN (
    SELECT note_id FROM tags WHERE tag = 'blackbirdrates'
  );

-- Show detailed links
SELECT 'Link details:' as info;
SELECT user_id, source_id, target_id, context
FROM links
WHERE source_id = 'br'
  AND target_id IN (
    SELECT note_id FROM tags WHERE tag = 'blackbirdrates'
  );

-- Reset security settings
RESET row_security;
RESET SESSION AUTHORIZATION;