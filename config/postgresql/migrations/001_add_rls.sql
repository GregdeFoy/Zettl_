-- ============================================================================
-- Zettl RLS Migration - Add Row Level Security with Composite Primary Keys
-- ============================================================================
-- This migration:
-- 1. Adds user_id to all tables
-- 2. Migrates existing data to a single user (greg)
-- 3. Creates composite primary keys (user_id, id)
-- 4. Enables Row Level Security
-- 5. Creates policies and triggers for automatic user_id population
--
-- CRITICAL: Backup your database before running this!
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Verify Prerequisites
-- ============================================================================

-- Ensure we're in the right database
\echo 'Current database: '
SELECT current_database();

-- Check that users table exists (created by auth-service)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users') THEN
        RAISE EXCEPTION 'Users table does not exist. Ensure auth-service has initialized.';
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Add user_id Columns (Nullable Initially)
-- ============================================================================

\echo 'Adding user_id columns...'

ALTER TABLE notes ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
ALTER TABLE links ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
ALTER TABLE tags ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);

-- ============================================================================
-- STEP 3: Migrate Existing Data to User 1 (greg)
-- ============================================================================

\echo 'Migrating existing data to user_id 1...'

-- Find the first user (should be greg)
DO $$
DECLARE
    first_user_id INTEGER;
BEGIN
    SELECT id INTO first_user_id FROM users ORDER BY id LIMIT 1;
    
    IF first_user_id IS NULL THEN
        RAISE EXCEPTION 'No users found in users table. Create a user first.';
    END IF;
    
    RAISE NOTICE 'Migrating all data to user_id: %', first_user_id;
    
    -- Migrate data
    UPDATE notes SET user_id = first_user_id WHERE user_id IS NULL;
    UPDATE links SET user_id = first_user_id WHERE user_id IS NULL;
    UPDATE tags SET user_id = first_user_id WHERE user_id IS NULL;
END $$;

-- ============================================================================
-- STEP 4: Make user_id NOT NULL
-- ============================================================================

\echo 'Making user_id columns NOT NULL...'

ALTER TABLE notes ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE links ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE tags ALTER COLUMN user_id SET NOT NULL;

-- ============================================================================
-- STEP 5: Drop Foreign Keys FIRST (before dropping primary keys)
-- ============================================================================

\echo 'Dropping foreign key constraints...'

-- Drop foreign keys from links (these depend on notes primary key)
ALTER TABLE links DROP CONSTRAINT IF EXISTS links_source_id_fkey;
ALTER TABLE links DROP CONSTRAINT IF EXISTS links_target_id_fkey;

-- Drop foreign key from tags (depends on notes primary key)
ALTER TABLE tags DROP CONSTRAINT IF EXISTS tags_note_id_fkey;

-- Drop unique constraints
ALTER TABLE links DROP CONSTRAINT IF EXISTS links_source_id_target_id_key;
ALTER TABLE links DROP CONSTRAINT IF EXISTS unique_link;
ALTER TABLE tags DROP CONSTRAINT IF EXISTS tags_note_id_tag_key;
ALTER TABLE tags DROP CONSTRAINT IF EXISTS unique_tag;

-- ============================================================================
-- STEP 6: Now Drop Primary Keys (safe because FKs are gone)
-- ============================================================================

\echo 'Dropping old primary keys...'

ALTER TABLE notes DROP CONSTRAINT IF EXISTS notes_pkey;

-- ============================================================================
-- STEP 7: Create Composite Primary Keys
-- ============================================================================

\echo 'Creating composite primary keys...'

-- Notes: (user_id, id) is the primary key
ALTER TABLE notes ADD PRIMARY KEY (user_id, id);

-- Links: Keep serial id as primary key for simplicity
-- Tags: Keep serial id as primary key

-- ============================================================================
-- STEP 8: Recreate Foreign Keys with Composite References
-- ============================================================================

\echo 'Recreating foreign key constraints...'

-- Links: both source and target are in the same user's namespace
ALTER TABLE links 
    ADD CONSTRAINT links_source_fkey 
    FOREIGN KEY (user_id, source_id) 
    REFERENCES notes(user_id, id) 
    ON DELETE CASCADE;

ALTER TABLE links 
    ADD CONSTRAINT links_target_fkey 
    FOREIGN KEY (user_id, target_id) 
    REFERENCES notes(user_id, id) 
    ON DELETE CASCADE;

-- Links: Ensure uniqueness per user
ALTER TABLE links 
    ADD CONSTRAINT unique_link_per_user 
    UNIQUE(user_id, source_id, target_id);

-- Tags: reference the composite key
ALTER TABLE tags 
    ADD CONSTRAINT tags_note_fkey 
    FOREIGN KEY (user_id, note_id) 
    REFERENCES notes(user_id, id) 
    ON DELETE CASCADE;

-- Tags: Ensure uniqueness per user
ALTER TABLE tags 
    ADD CONSTRAINT unique_tag_per_user 
    UNIQUE(user_id, note_id, tag);

-- ============================================================================
-- STEP 9: Update Indexes for Performance
-- ============================================================================

\echo 'Updating indexes...'

-- Drop old indexes that no longer make sense
DROP INDEX IF EXISTS idx_notes_created_at;
DROP INDEX IF EXISTS idx_links_source;
DROP INDEX IF EXISTS idx_links_target;
DROP INDEX IF EXISTS idx_tags_note;

-- Create new composite indexes
CREATE INDEX idx_notes_user_created ON notes(user_id, created_at DESC);
CREATE INDEX idx_notes_user_id ON notes(user_id);

CREATE INDEX idx_links_user_source ON links(user_id, source_id);
CREATE INDEX idx_links_user_target ON links(user_id, target_id);
CREATE INDEX idx_links_user_id ON links(user_id);

CREATE INDEX idx_tags_user_note ON tags(user_id, note_id);
CREATE INDEX idx_tags_user_tag ON tags(user_id, tag);
CREATE INDEX idx_tags_user_id ON tags(user_id);

-- Keep the full-text search index (still useful)
-- It already exists: idx_notes_content_gin

-- ============================================================================
-- STEP 10: Create auth Schema and Helper Function
-- ============================================================================

\echo 'Creating auth schema and helper function...'

-- Create auth schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS auth;

-- Grant usage to authenticated role
GRANT USAGE ON SCHEMA auth TO authenticated;

-- Function to extract user_id from JWT claims
CREATE OR REPLACE FUNCTION auth.user_id() 
RETURNS INTEGER AS $$
  SELECT NULLIF(
    current_setting('request.jwt.claims', true)::json->>'sub',
    ''
  )::INTEGER;
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

-- ============================================================================
-- STEP 11: Create Trigger Function to Auto-Set user_id
-- ============================================================================

\echo 'Creating trigger function...'

CREATE OR REPLACE FUNCTION set_user_id()
RETURNS TRIGGER AS $$
BEGIN
  -- Get user_id from JWT, if not present, raise error
  NEW.user_id := auth.user_id();
  
  IF NEW.user_id IS NULL THEN
    RAISE EXCEPTION 'Cannot determine user_id from JWT. Authentication required.';
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- STEP 12: Create Triggers on All Tables
-- ============================================================================

\echo 'Creating triggers...'

-- Notes trigger
DROP TRIGGER IF EXISTS notes_set_user_id ON notes;
CREATE TRIGGER notes_set_user_id 
  BEFORE INSERT ON notes
  FOR EACH ROW 
  EXECUTE FUNCTION set_user_id();

-- Links trigger
DROP TRIGGER IF EXISTS links_set_user_id ON links;
CREATE TRIGGER links_set_user_id 
  BEFORE INSERT ON links
  FOR EACH ROW 
  EXECUTE FUNCTION set_user_id();

-- Tags trigger
DROP TRIGGER IF EXISTS tags_set_user_id ON tags;
CREATE TRIGGER tags_set_user_id 
  BEFORE INSERT ON tags
  FOR EACH ROW 
  EXECUTE FUNCTION set_user_id();

-- ============================================================================
-- STEP 13: Enable Row Level Security
-- ============================================================================

\echo 'Enabling Row Level Security...'

ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE links ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 14: Create RLS Policies
-- ============================================================================

\echo 'Creating RLS policies...'

-- Notes policies
DROP POLICY IF EXISTS notes_policy ON notes;
CREATE POLICY notes_policy ON notes
  FOR ALL
  TO authenticated
  USING (user_id = auth.user_id())
  WITH CHECK (user_id = auth.user_id());

-- Links policies
DROP POLICY IF EXISTS links_policy ON links;
CREATE POLICY links_policy ON links
  FOR ALL
  TO authenticated
  USING (user_id = auth.user_id())
  WITH CHECK (user_id = auth.user_id());

-- Tags policies
DROP POLICY IF EXISTS tags_policy ON tags;
CREATE POLICY tags_policy ON tags
  FOR ALL
  TO authenticated
  USING (user_id = auth.user_id())
  WITH CHECK (user_id = auth.user_id());

-- ============================================================================
-- STEP 15: Update Role Permissions
-- ============================================================================

\echo 'Updating role permissions...'

-- Authenticated users need access to auth schema
GRANT USAGE ON SCHEMA auth TO authenticated;
GRANT EXECUTE ON FUNCTION auth.user_id() TO authenticated;

-- Ensure authenticated role still has necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON notes, links, tags TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- web_anon should have NO access after RLS (or read-only if you want public notes)
-- For now, remove all permissions to ensure security
REVOKE ALL ON notes, links, tags FROM web_anon;

-- ============================================================================
-- STEP 16: Verification Queries
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'MIGRATION COMPLETED SUCCESSFULLY!'
\echo '============================================================================'
\echo ''

-- Show updated table structures
\echo 'Table: notes'
\d notes

\echo ''
\echo 'Table: links'
\d links

\echo ''
\echo 'Table: tags'
\d tags

\echo ''
\echo 'Data verification:'

-- Count records by user
SELECT 'notes' as table_name, user_id, COUNT(*) as count 
FROM notes GROUP BY user_id
UNION ALL
SELECT 'links', user_id, COUNT(*) 
FROM links GROUP BY user_id
UNION ALL
SELECT 'tags', user_id, COUNT(*) 
FROM tags GROUP BY user_id
ORDER BY table_name, user_id;

\echo ''
\echo 'RLS Status:'

-- Check RLS is enabled
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename IN ('notes', 'links', 'tags');

\echo ''
\echo 'Policies:'

-- Show policies
SELECT schemaname, tablename, policyname, roles, cmd
FROM pg_policies 
WHERE tablename IN ('notes', 'links', 'tags');

COMMIT;

\echo ''
\echo '============================================================================'
\echo 'NEXT STEPS:'
\echo '1. Restart PostgREST: docker-compose restart postgrest'
\echo '2. Test with authenticated requests'
\echo '3. Verify Python client still works'
\echo '============================================================================'
