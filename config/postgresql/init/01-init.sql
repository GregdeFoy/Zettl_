-- Create Zettl schema and tables
CREATE SCHEMA IF NOT EXISTS public;

-- Create notes table
CREATE TABLE IF NOT EXISTS notes (
    id VARCHAR(10) PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create links table
CREATE TABLE IF NOT EXISTS links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id VARCHAR(10) NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_id VARCHAR(10) NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    context TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, target_id)
);

-- Create tags table
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id VARCHAR(10) NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(note_id, tag)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_id);
CREATE INDEX IF NOT EXISTS idx_tags_note ON tags(note_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger to notes table
DROP TRIGGER IF EXISTS update_notes_modified ON notes;
CREATE TRIGGER update_notes_modified 
    BEFORE UPDATE ON notes 
    FOR EACH ROW 
    EXECUTE FUNCTION update_modified_column();

-- Grant permissions for PostgREST
GRANT USAGE ON SCHEMA public TO anon, web_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
GRANT ALL ON ALL TABLES IN SCHEMA public TO web_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO web_user;
