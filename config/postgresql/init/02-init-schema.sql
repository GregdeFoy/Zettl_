\c zettl;

-- Create the main tables for Zettl in public schema
CREATE TABLE IF NOT EXISTS public.notes (
    id VARCHAR(10) PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.links (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(10) REFERENCES public.notes(id) ON DELETE CASCADE,
    target_id VARCHAR(10) REFERENCES public.notes(id) ON DELETE CASCADE,
    context TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, target_id)
);

CREATE TABLE IF NOT EXISTS public.tags (
    id SERIAL PRIMARY KEY,
    note_id VARCHAR(10) REFERENCES public.notes(id) ON DELETE CASCADE,
    tag VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(note_id, tag)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON public.notes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_links_source ON public.links(source_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON public.links(target_id);
CREATE INDEX IF NOT EXISTS idx_tags_note_id ON public.tags(note_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON public.tags(tag);
CREATE INDEX IF NOT EXISTS idx_notes_content_gin ON public.notes USING gin(to_tsvector('english', content));

-- Grant permissions on public schema
GRANT USAGE ON SCHEMA public TO web_anon, authenticated, zettl_auth;

-- Permissions for web_anon (read-only access)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO web_anon;

-- Permissions for authenticated users (full access to zettl tables)
GRANT SELECT, INSERT, UPDATE, DELETE ON public.notes, public.links, public.tags TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Permissions for auth service (full access)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO zettl_auth;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO zettl_auth;
