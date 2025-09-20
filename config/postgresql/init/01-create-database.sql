-- Create zettl database if it doesn't exist
CREATE DATABASE zettl;

-- Switch to zettl database
\c zettl;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS zettl;

-- Create roles
DO $$ 
BEGIN
    -- Create roles for PostgREST
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'web_anon') THEN
        CREATE ROLE web_anon NOLOGIN;
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticator') THEN
        CREATE ROLE authenticator NOINHERIT LOGIN PASSWORD 'authenticator_pass';
        GRANT web_anon TO authenticator;
        GRANT authenticated TO authenticator;
    END IF;
    
    -- Create auth service user
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'zettl_auth') THEN
        CREATE ROLE zettl_auth LOGIN;
    END IF;
END $$;

-- Set password for zettl_auth from file
DO $$
DECLARE
    auth_password text;
BEGIN
    -- Read password from file (this is handled by Docker init)
    auth_password := current_setting('zettl.auth_password', true);
    IF auth_password IS NOT NULL THEN
        EXECUTE format('ALTER ROLE zettl_auth PASSWORD %L', auth_password);
    END IF;
END $$;
