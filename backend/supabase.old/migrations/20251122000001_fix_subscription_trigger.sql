-- Fix the subscription trigger function to use the correct search path
-- This resolves the "relation 'user_subscriptions' does not exist" error

CREATE OR REPLACE FUNCTION public.create_free_subscription_for_new_user()
RETURNS TRIGGER
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
  -- Create a free tier subscription for the new user
  INSERT INTO public.user_subscriptions (
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
$$;

-- Notify PostgREST to reload schema
NOTIFY pgrst, 'reload schema';
