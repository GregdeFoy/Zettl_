-- ============================================================================
-- Zettl Chat Schema - MCP Server Support
-- ============================================================================
-- This creates tables for storing chat conversations and messages
-- Follows the same RLS pattern as notes, links, and tags
-- ============================================================================

\c zettl;

-- ============================================================================
-- STEP 1: Create conversations Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.conversations (
    id VARCHAR(20) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    context_note_ids TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, id)
);

-- ============================================================================
-- STEP 2: Create messages Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.messages (
    id VARCHAR(20) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id VARCHAR(20) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, id),
    FOREIGN KEY (user_id, conversation_id) REFERENCES conversations(user_id, id) ON DELETE CASCADE
);

-- ============================================================================
-- STEP 3: Create Indexes for Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_conversations_user_created ON conversations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

CREATE INDEX IF NOT EXISTS idx_messages_user_conversation ON messages(user_id, conversation_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);

-- ============================================================================
-- STEP 4: Create Triggers for Auto-Setting user_id
-- ============================================================================

-- Conversations trigger
DROP TRIGGER IF EXISTS conversations_set_user_id ON conversations;
CREATE TRIGGER conversations_set_user_id
  BEFORE INSERT ON conversations
  FOR EACH ROW
  EXECUTE FUNCTION set_user_id();

-- Messages trigger
DROP TRIGGER IF EXISTS messages_set_user_id ON messages;
CREATE TRIGGER messages_set_user_id
  BEFORE INSERT ON messages
  FOR EACH ROW
  EXECUTE FUNCTION set_user_id();

-- ============================================================================
-- STEP 5: Create Trigger for Auto-Updating updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE conversations
  SET updated_at = CURRENT_TIMESTAMP
  WHERE user_id = NEW.user_id AND id = NEW.conversation_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS messages_update_conversation ON messages;
CREATE TRIGGER messages_update_conversation
  AFTER INSERT ON messages
  FOR EACH ROW
  EXECUTE FUNCTION update_conversation_timestamp();

-- ============================================================================
-- STEP 6: Enable Row Level Security
-- ============================================================================

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 7: Create RLS Policies
-- ============================================================================

-- Conversations policies
DROP POLICY IF EXISTS conversations_policy ON conversations;
CREATE POLICY conversations_policy ON conversations
  FOR ALL
  TO authenticated
  USING (user_id = auth.user_id())
  WITH CHECK (user_id = auth.user_id());

-- Messages policies
DROP POLICY IF EXISTS messages_policy ON messages;
CREATE POLICY messages_policy ON messages
  FOR ALL
  TO authenticated
  USING (user_id = auth.user_id())
  WITH CHECK (user_id = auth.user_id());

-- ============================================================================
-- STEP 8: Grant Permissions
-- ============================================================================

-- Authenticated users get full access to their own data
GRANT SELECT, INSERT, UPDATE, DELETE ON conversations, messages TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Auth service gets full access
GRANT ALL PRIVILEGES ON conversations, messages TO zettl_auth;

-- web_anon gets no access
REVOKE ALL ON conversations, messages FROM web_anon;

-- ============================================================================
-- STEP 9: Verification
-- ============================================================================

\echo 'Chat schema created successfully!'
\echo ''
\echo 'Table: conversations'
\d conversations

\echo ''
\echo 'Table: messages'
\d messages

\echo ''
\echo 'RLS Status:'
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE tablename IN ('conversations', 'messages');
