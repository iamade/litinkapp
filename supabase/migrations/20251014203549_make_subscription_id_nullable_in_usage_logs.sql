/*
  # Make subscription_id nullable in usage_logs table

  1. Changes
    - Alter `usage_logs` table to make `subscription_id` nullable
    - This allows recording usage for users without an active subscription

  2. Reason
    - Users may use image generation features before subscribing
    - Free tier users don't have subscriptions but still need usage tracking
    - Prevents NOT NULL constraint violations when recording usage

  3. Notes
    - Existing data is preserved
    - No data migration needed
    - This is a safe operation that won't affect existing records
*/

-- Make subscription_id nullable in usage_logs table
ALTER TABLE usage_logs
  ALTER COLUMN subscription_id DROP NOT NULL;
