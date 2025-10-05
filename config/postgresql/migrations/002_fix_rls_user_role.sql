-- ============================================================================
-- Fix RLS Policies to Include 'user' Role
-- ============================================================================
-- The auth-service creates JWTs with role='user', but the RLS policies
-- only allowed role='authenticated'. This migration fixes that.
-- ============================================================================

BEGIN;

\echo 'Updating RLS policies to include user role...'

-- Drop existing policies
DROP POLICY IF EXISTS notes_policy ON notes;
DROP POLICY IF EXISTS links_policy ON links;
DROP POLICY IF EXISTS tags_policy ON tags;

-- Recreate policies for both authenticated and user roles
CREATE POLICY notes_policy ON notes
  FOR ALL
  TO authenticated, "user"
  USING (user_id = auth.user_id())
  WITH CHECK (user_id = auth.user_id());

CREATE POLICY links_policy ON links
  FOR ALL
  TO authenticated, "user"
  USING (user_id = auth.user_id())
  WITH CHECK (user_id = auth.user_id());

CREATE POLICY tags_policy ON tags
  FOR ALL
  TO authenticated, "user"
  USING (user_id = auth.user_id())
  WITH CHECK (user_id = auth.user_id());

-- Grant execute permission on auth.user_id() to user role
GRANT EXECUTE ON FUNCTION auth.user_id() TO "user";

\echo ''
\echo 'Updated policies:'
SELECT schemaname, tablename, policyname, roles
FROM pg_policies
WHERE tablename IN ('notes', 'links', 'tags');

COMMIT;

\echo ''
\echo '============================================================================'
\echo 'RLS policies updated successfully!'
\echo 'Both authenticated and user roles can now access the tables.'
\echo '============================================================================'
