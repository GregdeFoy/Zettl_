-- Migration: Add hidden_buttons column to user_settings table
-- Run this script if you're getting JSON errors when saving button preferences

\c zettl;

-- Add hidden_buttons column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'user_settings'
        AND column_name = 'hidden_buttons'
    ) THEN
        ALTER TABLE user_settings ADD COLUMN hidden_buttons JSONB DEFAULT '[]';
        RAISE NOTICE 'Added hidden_buttons column to user_settings table';
    ELSE
        RAISE NOTICE 'Column hidden_buttons already exists';
    END IF;
END $$;
