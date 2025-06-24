-- Add new statuses to the book_status enum to support background processing
BEGIN;
ALTER TYPE book_status ADD VALUE 'QUEUED';
COMMIT;

-- Now that the enum value is committed, we can use it
ALTER TABLE books ALTER COLUMN status SET DEFAULT 'QUEUED'; 