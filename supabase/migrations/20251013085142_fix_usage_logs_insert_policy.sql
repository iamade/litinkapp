/*
  # Fix usage_logs RLS policy

  1. Changes
    - Add INSERT policy for authenticated users to insert their own usage logs
    - Keep existing SELECT policy for users to view own logs
    - Keep service_role full access

  2. Security
    - Users can only insert logs with their own user_id
    - Users can only view their own logs
    - Service role has full access
*/

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can insert own usage logs" ON usage_logs;

-- Add policy for users to insert their own usage logs
CREATE POLICY "Users can insert own usage logs"
  ON usage_logs
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);
