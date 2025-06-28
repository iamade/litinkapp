-- Migration: Add original_file_storage_path column to books table
ALTER TABLE books ADD COLUMN original_file_storage_path TEXT;

-- Add index for faster lookups
CREATE INDEX idx_books_original_file_storage_path ON books(original_file_storage_path); 