/*
  # Add PENDING_PAYMENT status to book_status enum

  1. Changes
    - Add PENDING_PAYMENT value to book_status enum
    - This status will be used for books that require payment before processing

  2. Security
    - No changes to RLS policies needed
*/

-- Add new status to the book_status enum
ALTER TYPE book_status ADD VALUE 'PENDING_PAYMENT';