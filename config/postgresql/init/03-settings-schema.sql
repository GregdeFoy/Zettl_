\c zettl;

-- Store user settings (API keys, preferences)
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    claude_api_key TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rename existing api_keys table to cli_tokens for better clarity
-- First check if api_keys exists and cli_tokens doesn't
DO $$
BEGIN
    -- Check if api_keys exists and cli_tokens doesn't
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'api_keys' AND table_schema = 'public')
       AND NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'cli_tokens' AND table_schema = 'public') THEN
        -- Rename the table
        ALTER TABLE api_keys RENAME TO cli_tokens;

        -- Add token column for storing plaintext token (shown once)
        ALTER TABLE cli_tokens ADD COLUMN IF NOT EXISTS token VARCHAR(255);

        -- Add token_hash column for secure storage if it doesn't exist
        ALTER TABLE cli_tokens ADD COLUMN IF NOT EXISTS token_hash VARCHAR(255);

        -- Rename key_hash to token_hash if key_hash exists
        IF EXISTS (SELECT FROM information_schema.columns
                   WHERE table_name = 'cli_tokens' AND column_name = 'key_hash') THEN
            ALTER TABLE cli_tokens RENAME COLUMN key_hash TO token_hash;
        END IF;

        -- Add is_active column for soft deletes
        ALTER TABLE cli_tokens ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

        -- Update constraint names
        ALTER INDEX IF EXISTS api_keys_pkey RENAME TO cli_tokens_pkey;
    END IF;

    -- If cli_tokens doesn't exist at all, create it
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'cli_tokens' AND table_schema = 'public') THEN
        CREATE TABLE cli_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            token VARCHAR(255),
            token_hash VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT true,
            permissions JSONB DEFAULT '[]'
        );
    END IF;
END $$;

-- Create indexes for cli_tokens
CREATE INDEX IF NOT EXISTS idx_cli_tokens_hash ON cli_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_cli_tokens_user ON cli_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_cli_tokens_active ON cli_tokens(is_active) WHERE is_active = true;

-- Grant permissions on new tables
GRANT ALL PRIVILEGES ON user_settings TO zettl_auth;
GRANT ALL PRIVILEGES ON cli_tokens TO zettl_auth;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO zettl_auth;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for user_settings
DROP TRIGGER IF EXISTS update_user_settings_updated_at ON user_settings;
CREATE TRIGGER update_user_settings_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
