/*
  # Populate and Automate Subscription History Tracking

  1. Purpose
    - Create subscription_history table for audit trail
    - Populate subscription_history with records for all current subscriptions
    - Create database triggers to automatically track all future subscription changes
    - Ensure complete audit trail of subscription lifecycle events

  2. Changes
    - Create subscription_history table
    - Insert initial "created" events for all existing subscriptions
    - Create trigger function to log subscription INSERT/UPDATE/DELETE events
    - Add trigger on user_subscriptions table for automatic tracking

  3. Event Types Tracked
    - 'created': New subscription created (free tier signup, paid upgrade)
    - 'upgraded': Tier increased (free -> basic -> pro -> premium)
    - 'downgraded': Tier decreased
    - 'status_changed': Status updated (active, cancelled, past_due, etc)
    - 'cancelled': Subscription cancelled
    - 'reactivated': Cancelled subscription reactivated
    - 'renewed': Subscription renewed for new period

  4. History Record Contains
    - user_id: User identifier
    - subscription_id: Link to user_subscriptions record
    - event_type: Type of change
    - from_tier/to_tier: Tier transition
    - from_status/to_status: Status transition
    - reason: Human-readable explanation
    - metadata: Additional context (stripe events, pricing, etc)

  5. Benefits
    - Complete subscription audit trail
    - Track user subscription journey
    - Support billing disputes and analytics
    - Monitor churn and upgrades
    - Compliance and reporting

  6. Notes
    - Idempotent: Safe to run multiple times
    - Uses ON CONFLICT to prevent duplicate history records
    - Trigger captures all changes automatically
*/

-- Step 0: Create subscription_history table if it doesn't exist
CREATE TABLE IF NOT EXISTS subscription_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  subscription_id UUID REFERENCES user_subscriptions(id) ON DELETE SET NULL,
  event_type VARCHAR(50) NOT NULL,
  from_tier subscription_tier,
  to_tier subscription_tier,
  from_status subscription_status,
  to_status subscription_status,
  reason TEXT,
  metadata JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE subscription_history ENABLE ROW LEVEL SECURITY;

-- Users can view their own subscription history
DROP POLICY IF EXISTS "Users can view own subscription history" ON subscription_history;
CREATE POLICY "Users can view own subscription history"
  ON subscription_history FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Service role can manage all history
DROP POLICY IF EXISTS "Service role can manage all subscription history" ON subscription_history;
CREATE POLICY "Service role can manage all subscription history"
  ON subscription_history FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_subscription_history_user_id ON subscription_history(user_id);
CREATE INDEX IF NOT EXISTS idx_subscription_history_subscription_id ON subscription_history(subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscription_history_event_type ON subscription_history(event_type);
CREATE INDEX IF NOT EXISTS idx_subscription_history_created_at ON subscription_history(created_at DESC);

-- Step 1: Populate subscription_history with initial records for existing subscriptions
INSERT INTO subscription_history (
  user_id,
  subscription_id,
  event_type,
  from_tier,
  to_tier,
  from_status,
  to_status,
  reason,
  metadata,
  created_at
)
SELECT 
  us.user_id,
  us.id as subscription_id,
  'created' as event_type,
  NULL as from_tier,
  us.tier as to_tier,
  NULL as from_status,
  us.status as to_status,
  CASE 
    WHEN us.tier = 'free' THEN 'Initial free tier subscription created during user signup'
    ELSE 'Subscription created'
  END as reason,
  jsonb_build_object(
    'monthly_video_limit', us.monthly_video_limit,
    'video_quality', us.video_quality,
    'has_watermark', us.has_watermark,
    'stripe_customer_id', us.stripe_customer_id,
    'stripe_subscription_id', us.stripe_subscription_id,
    'source', 'historical_backfill'
  ) as metadata,
  us.created_at
FROM user_subscriptions us
LEFT JOIN subscription_history sh 
  ON sh.subscription_id = us.id AND sh.event_type = 'created'
WHERE sh.id IS NULL;

-- Step 2: Create trigger function to automatically track subscription changes
CREATE OR REPLACE FUNCTION track_subscription_changes()
RETURNS TRIGGER AS $$
DECLARE
  event_type_val VARCHAR(50);
  reason_val TEXT;
BEGIN
  -- Handle INSERT (new subscription)
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO subscription_history (
      user_id,
      subscription_id,
      event_type,
      from_tier,
      to_tier,
      from_status,
      to_status,
      reason,
      metadata,
      created_at
    ) VALUES (
      NEW.user_id,
      NEW.id,
      'created',
      NULL,
      NEW.tier,
      NULL,
      NEW.status,
      CASE 
        WHEN NEW.tier = 'free' THEN 'Free tier subscription created'
        ELSE 'Paid subscription created'
      END,
      jsonb_build_object(
        'monthly_video_limit', NEW.monthly_video_limit,
        'video_quality', NEW.video_quality,
        'has_watermark', NEW.has_watermark,
        'stripe_customer_id', NEW.stripe_customer_id,
        'stripe_subscription_id', NEW.stripe_subscription_id
      ),
      NOW()
    );
    RETURN NEW;
  END IF;

  -- Handle UPDATE (tier change, status change, etc)
  IF (TG_OP = 'UPDATE') THEN
    -- Determine event type based on what changed
    IF (OLD.tier != NEW.tier) THEN
      -- Tier changed
      IF (NEW.tier::text > OLD.tier::text) THEN
        event_type_val := 'upgraded';
        reason_val := format('Upgraded from %s to %s tier', OLD.tier, NEW.tier);
      ELSE
        event_type_val := 'downgraded';
        reason_val := format('Downgraded from %s to %s tier', OLD.tier, NEW.tier);
      END IF;
    ELSIF (OLD.status != NEW.status) THEN
      -- Status changed
      event_type_val := 'status_changed';
      IF (NEW.status = 'cancelled') THEN
        event_type_val := 'cancelled';
        reason_val := format('Subscription cancelled (was %s)', OLD.status);
      ELSIF (OLD.status = 'cancelled' AND NEW.status = 'active') THEN
        event_type_val := 'reactivated';
        reason_val := 'Cancelled subscription reactivated';
      ELSE
        reason_val := format('Status changed from %s to %s', OLD.status, NEW.status);
      END IF;
    ELSIF (OLD.current_period_start != NEW.current_period_start) THEN
      -- Billing period renewed
      event_type_val := 'renewed';
      reason_val := format('Subscription renewed for new billing period');
    ELSE
      -- Other changes (limits, features, etc)
      event_type_val := 'updated';
      reason_val := 'Subscription details updated';
    END IF;

    -- Insert history record
    INSERT INTO subscription_history (
      user_id,
      subscription_id,
      event_type,
      from_tier,
      to_tier,
      from_status,
      to_status,
      reason,
      metadata,
      created_at
    ) VALUES (
      NEW.user_id,
      NEW.id,
      event_type_val,
      OLD.tier,
      NEW.tier,
      OLD.status,
      NEW.status,
      reason_val,
      jsonb_build_object(
        'old_monthly_video_limit', OLD.monthly_video_limit,
        'new_monthly_video_limit', NEW.monthly_video_limit,
        'old_video_quality', OLD.video_quality,
        'new_video_quality', NEW.video_quality,
        'old_has_watermark', OLD.has_watermark,
        'new_has_watermark', NEW.has_watermark,
        'stripe_customer_id', NEW.stripe_customer_id,
        'stripe_subscription_id', NEW.stripe_subscription_id,
        'old_current_period_start', OLD.current_period_start,
        'new_current_period_start', NEW.current_period_start
      ),
      NOW()
    );
    RETURN NEW;
  END IF;

  -- Handle DELETE (subscription deleted - rare but possible)
  IF (TG_OP = 'DELETE') THEN
    INSERT INTO subscription_history (
      user_id,
      subscription_id,
      event_type,
      from_tier,
      to_tier,
      from_status,
      to_status,
      reason,
      metadata,
      created_at
    ) VALUES (
      OLD.user_id,
      OLD.id,
      'deleted',
      OLD.tier,
      NULL,
      OLD.status,
      NULL,
      'Subscription record deleted',
      jsonb_build_object(
        'monthly_video_limit', OLD.monthly_video_limit,
        'video_quality', OLD.video_quality,
        'has_watermark', OLD.has_watermark,
        'stripe_customer_id', OLD.stripe_customer_id,
        'stripe_subscription_id', OLD.stripe_subscription_id
      ),
      NOW()
    );
    RETURN OLD;
  END IF;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Step 3: Create trigger on user_subscriptions table
DROP TRIGGER IF EXISTS trigger_track_subscription_changes ON user_subscriptions;

CREATE TRIGGER trigger_track_subscription_changes
  AFTER INSERT OR UPDATE OR DELETE ON user_subscriptions
  FOR EACH ROW
  EXECUTE FUNCTION track_subscription_changes();

-- Step 4: Add helpful comments
COMMENT ON FUNCTION track_subscription_changes() IS 
  'Automatically tracks all subscription changes (create, update, delete) to subscription_history table. Captures tier changes, status changes, renewals, and all subscription lifecycle events for audit trail and analytics.';

COMMENT ON TABLE subscription_history IS 
  'Complete audit log of all subscription changes. Tracks user subscription journey including upgrades, downgrades, cancellations, renewals, and status changes. Used for analytics, billing disputes, compliance, and customer support.';
