/*
  # Add payment-related fields to books table

  1. Changes
    - Add stripe_checkout_session_id field to track Stripe sessions
    - Add stripe_payment_intent_id field to track payment intents
    - Add stripe_customer_id field to track Stripe customers
    - Add payment_status field to track payment status

  2. Security
    - No changes to RLS policies needed
*/

-- Add payment-related fields to books table
ALTER TABLE books ADD COLUMN IF NOT EXISTS stripe_checkout_session_id TEXT;
ALTER TABLE books ADD COLUMN IF NOT EXISTS stripe_payment_intent_id TEXT;
ALTER TABLE books ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
ALTER TABLE books ADD COLUMN IF NOT EXISTS payment_status TEXT DEFAULT 'unpaid';

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_books_stripe_checkout_session_id ON books(stripe_checkout_session_id);
CREATE INDEX IF NOT EXISTS idx_books_payment_status ON books(payment_status);