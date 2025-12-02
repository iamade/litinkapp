/*
  # Ensure Free Tier Subscriptions for All Users

  1. Purpose
    - Create free tier subscriptions for all existing users without subscriptions
    - Add database trigger to automatically create free subscriptions for new users
    - Make subscription_id nullable in usage_logs as fallback

  2. Changes
    - Insert free tier subscription records for users without subscriptions
    - Create trigger function to auto-create free subscriptions on user creation
    - Make usage_logs.subscription_id nullable to prevent failures

  3. Free Tier Defaults
    - tier: 'free'
    - status: 'active'
    - monthly_video_limit: 2
    - video_quality: '480p'
    - has_watermark: true
    - videos_generated_this_period: 0

  4. Benefits
    - Users automatically get free tier access immediately
    - No manual subscription creation needed
    - Prevents usage_logs constraint violations
    - Seamless user onboarding experience

  5. Notes
    - Idempotent: Safe to run multiple times
    - Uses auth.users table to find users without subscriptions
    - Trigger only fires for new users, not existing ones
*/

-- Step 1: Make subscription_id nullable in usage_logs (if not already)
DO $$
BEGIN
  ALTER TABLE usage_logs
    ALTER COLUMN subscription_id DROP NOT NULL;
EXCEPTION
  WHEN others THEN
    -- Column is already nullable or other error, continue
    NULL;
END $$;

-- Step 2: Create free tier subscriptions for existing users who don't have one
INSERT INTO user_subscriptions (
  user_id,
  tier,
  status,
  monthly_video_limit,
  video_quality,
  has_watermark,
  videos_generated_this_period,
  current_period_start,
  current_period_end,
  cancel_at_period_end,
  created_at,
  updated_at
)
SELECT 
  u.id as user_id,
  'free' as tier,
  'active' as status,
  2 as monthly_video_limit,
  '480p' as video_quality,
  true as has_watermark,
  0 as videos_generated_this_period,
  NOW() as current_period_start,
  NOW() + INTERVAL '1 month' as current_period_end,
  false as cancel_at_period_end,
  NOW() as created_at,
  NOW() as updated_at
FROM auth.users u
LEFT JOIN user_subscriptions us ON us.user_id = u.id
WHERE us.id IS NULL;

-- Step 3: Create trigger function to auto-create free subscriptions for new users
CREATE OR REPLACE FUNCTION create_free_subscription_for_new_user()
RETURNS TRIGGER AS $$
BEGIN
  -- Create a free tier subscription for the new user
  INSERT INTO user_subscriptions (
    user_id,
    tier,
    status,
    monthly_video_limit,
    video_quality,
    has_watermark,
    videos_generated_this_period,
    current_period_start,
    current_period_end,
    cancel_at_period_end,
    created_at,
    updated_at
  ) VALUES (
    NEW.id,
    'free',
    'active',
    2,
    '480p',
    true,
    0,
    NOW(),
    NOW() + INTERVAL '1 month',
    false,
    NOW(),
    NOW()
  )
  ON CONFLICT (user_id) DO NOTHING;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Step 4: Create trigger on auth.users table for new user signups
DROP TRIGGER IF EXISTS trigger_create_free_subscription_on_signup ON auth.users;

CREATE TRIGGER trigger_create_free_subscription_on_signup
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION create_free_subscription_for_new_user();

-- Step 5: Add comment explaining the trigger
COMMENT ON FUNCTION create_free_subscription_for_new_user() IS 
  'Automatically creates a free tier subscription for new users upon signup. This ensures all users have immediate access to free tier features without manual intervention.';
