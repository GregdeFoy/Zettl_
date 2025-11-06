-- Fix the notes_with_tags view to work properly with PostgREST and RLS
-- The issue is that the view needs proper permissions and shouldn't have security_barrier

BEGIN;

-- Drop the existing view
DROP VIEW IF EXISTS public.notes_with_tags CASCADE;

-- Check if RLS is enabled and recreate view accordingly
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'notes'
        AND column_name = 'user_id'
    ) THEN
        -- RLS version - without security_barrier as it causes issues with PostgREST
        EXECUTE '
            CREATE VIEW public.notes_with_tags AS
            SELECT
                n.user_id,
                n.id,
                n.content,
                n.created_at,
                n.modified_at,
                string_agg(t.tag::text, '',''::text ORDER BY t.tag) AS all_tags_str,
                COALESCE(
                    array_agg(t.tag ORDER BY t.tag) FILTER (WHERE t.tag IS NOT NULL),
                    ARRAY[]::varchar[]
                ) AS all_tags_array
            FROM public.notes n
            LEFT JOIN public.tags t ON n.user_id = t.user_id AND n.id = t.note_id
            GROUP BY n.user_id, n.id, n.content, n.created_at, n.modified_at
        ';
    ELSE
        -- Non-RLS version
        EXECUTE '
            CREATE VIEW public.notes_with_tags AS
            SELECT
                n.id,
                n.content,
                n.created_at,
                n.modified_at,
                string_agg(t.tag::text, '',''::text ORDER BY t.tag) AS all_tags_str,
                COALESCE(
                    array_agg(t.tag ORDER BY t.tag) FILTER (WHERE t.tag IS NOT NULL),
                    ARRAY[]::varchar[]
                ) AS all_tags_array
            FROM public.notes n
            LEFT JOIN public.tags t ON n.id = t.note_id
            GROUP BY n.id, n.content, n.created_at, n.modified_at
        ';
    END IF;
END $$;

-- Set owner to postgres to avoid RLS complications
ALTER VIEW public.notes_with_tags OWNER TO postgres;

-- Grant proper permissions
GRANT SELECT ON public.notes_with_tags TO authenticator;
GRANT SELECT ON public.notes_with_tags TO authenticated;
GRANT SELECT ON public.notes_with_tags TO web_anon;

-- Ensure the authenticator role can inherit permissions
ALTER ROLE authenticator INHERIT;

COMMIT;

\echo 'View fixed! The todos command should now work correctly.'