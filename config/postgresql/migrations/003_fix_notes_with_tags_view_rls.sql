-- ============================================================================
-- Fix notes_with_tags View to Respect Row Level Security
-- ============================================================================
-- The notes_with_tags view was bypassing RLS policies because:
-- 1. It wasn't created as a security_barrier view
-- 2. It was created before user_id columns were added
-- 3. It was owned by postgres (superuser), which bypasses RLS
--
-- This migration recreates the view with:
-- 1. user_id column included
-- 2. security_barrier = true to enforce RLS
-- 3. Owner changed to authenticated (non-superuser) to respect RLS
-- ============================================================================

BEGIN;

\echo 'Dropping and recreating notes_with_tags view with RLS support...'

-- Drop the existing view
DROP VIEW IF EXISTS public.notes_with_tags CASCADE;

-- Recreate the view with security_barrier and user_id support
CREATE VIEW public.notes_with_tags
WITH (security_barrier = true) AS
 SELECT
    n.user_id,
    n.id,
    n.content,
    n.created_at,
    COALESCE(string_agg((t.tag)::text, ','::text ORDER BY (t.tag)::text), ''::text) AS all_tags_str,
    COALESCE(array_agg(t.tag ORDER BY t.tag) FILTER (WHERE (t.tag IS NOT NULL)), (ARRAY[]::text[])::character varying[]) AS all_tags_array
   FROM (public.notes n
     LEFT JOIN public.tags t ON ((n.user_id = t.user_id) AND (n.id = t.note_id)))
  GROUP BY n.user_id, n.id, n.content, n.created_at
  ORDER BY n.created_at DESC;

-- Grant permissions to the view
GRANT SELECT ON public.notes_with_tags TO authenticated, "user";

-- CRITICAL: Change owner to authenticated role so RLS is enforced
-- If owned by postgres (superuser), RLS is bypassed
ALTER VIEW public.notes_with_tags OWNER TO authenticated;

\echo ''
\echo 'View recreation completed!'

-- Verify the view properties
\echo ''
\echo 'View details:'
\d+ notes_with_tags

COMMIT;

\echo ''
\echo '============================================================================'
\echo 'SUCCESS!'
\echo 'The notes_with_tags view now respects Row Level Security.'
\echo 'The todos command will now only show notes belonging to the authenticated user.'
\echo ''
\echo 'NEXT STEPS:'
\echo '1. Test with: zettl todos'
\echo '2. Verify other users cannot see your notes'
\echo '============================================================================'
