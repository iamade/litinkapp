-- Ensure book_status enum has all required values
-- First, let's check what values currently exist and add missing ones

-- Add 'published' if it doesn't exist (it should exist from the original migration)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'published' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'book_status')
    ) THEN
        ALTER TYPE book_status ADD VALUE 'published';
    END IF;
END $$;

-- Add 'QUEUED' if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'QUEUED' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'book_status')
    ) THEN
        ALTER TYPE book_status ADD VALUE 'QUEUED';
    END IF;
END $$;

-- Add 'failed' if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'failed' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'book_status')
    ) THEN
        ALTER TYPE book_status ADD VALUE 'failed';
    END IF;
END $$;

-- Verify the enum has all required values
-- This will show us what values are currently available
SELECT enumlabel FROM pg_enum 
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'book_status')
ORDER BY enumsortorder; 