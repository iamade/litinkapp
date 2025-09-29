-- Create enum for subscription tiers
CREATE TYPE subscription_tier AS ENUM ('free', 'basic', 'pro');

-- Create enum for subscription status
CREATE TYPE subscription_status AS ENUM ('active', 'cancelled', 'expired', 'past_due', 'trialing');

-- Create user_subscriptions table
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tier subscription_tier NOT NULL DEFAULT 'free',
    status subscription_status NOT NULL DEFAULT 'active',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    stripe_price_id VARCHAR(255),
    
    -- Monthly limits based on tier
    monthly_video_limit INTEGER NOT NULL DEFAULT 2,
    video_quality VARCHAR(50) DEFAULT '480p',
    has_watermark BOOLEAN DEFAULT true,
    
    -- Usage tracking for current period
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    videos_generated_this_period INTEGER DEFAULT 0,
    
    -- Billing information
    next_billing_date TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT false,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint on user_id to ensure one subscription per user
    CONSTRAINT unique_user_subscription UNIQUE (user_id)
);

-- Create indexes for user_subscriptions
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_stripe_customer ON user_subscriptions(stripe_customer_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);

-- Create usage_logs table to track video generation usage
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subscription_id UUID NOT NULL REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    
    -- What was used
    resource_type VARCHAR(50) NOT NULL DEFAULT 'video_generation', -- Could be extended for other resources
    resource_id UUID, -- Reference to the video_generations table
    
    -- Usage details
    usage_count INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}', -- Store additional data like quality, duration, etc.
    
    -- When it was used
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    billing_period_start TIMESTAMP WITH TIME ZONE,
    billing_period_end TIMESTAMP WITH TIME ZONE
);

-- Create indexes for usage_logs
CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_subscription_id ON usage_logs(subscription_id);
CREATE INDEX idx_usage_logs_created_at ON usage_logs(created_at);
CREATE INDEX idx_usage_logs_resource ON usage_logs(resource_type, resource_id);

-- Create subscription_history table to track changes
CREATE TABLE IF NOT EXISTS subscription_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES user_subscriptions(id) ON DELETE SET NULL,
    
    -- Change details
    event_type VARCHAR(100) NOT NULL, -- 'created', 'upgraded', 'downgraded', 'cancelled', 'expired', 'reactivated'
    from_tier subscription_tier,
    to_tier subscription_tier,
    from_status subscription_status,
    to_status subscription_status,
    
    -- Stripe information
    stripe_event_id VARCHAR(255),
    stripe_invoice_id VARCHAR(255),
    
    -- Financial details
    amount_paid DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Additional context
    reason TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for subscription_history
CREATE INDEX idx_subscription_history_user_id ON subscription_history(user_id);
CREATE INDEX idx_subscription_history_subscription_id ON subscription_history(subscription_id);
CREATE INDEX idx_subscription_history_created_at ON subscription_history(created_at);
CREATE INDEX idx_subscription_history_event ON subscription_history(event_type);

-- Create subscription_tiers table for tier configuration
CREATE TABLE IF NOT EXISTS subscription_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier subscription_tier NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Pricing
    monthly_price DECIMAL(10, 2) NOT NULL,
    stripe_price_id VARCHAR(255),
    stripe_product_id VARCHAR(255),
    
    -- Limits and features
    monthly_video_limit INTEGER NOT NULL,
    video_quality VARCHAR(50) NOT NULL,
    has_watermark BOOLEAN NOT NULL DEFAULT false,
    max_video_duration INTEGER, -- in seconds
    priority_processing BOOLEAN DEFAULT false,
    
    -- Additional features as JSONB for flexibility
    features JSONB DEFAULT '{}',
    
    -- Display order
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default tier configurations
INSERT INTO subscription_tiers (tier, display_name, description, monthly_price, monthly_video_limit, video_quality, has_watermark, display_order, features)
VALUES 
    ('free', 'Free', 'Get started with basic features', 0.00, 2, '480p', true, 1, 
     '{"max_file_size_mb": 10, "support_level": "community", "export_formats": ["mp4"]}'::jsonb),
    
    ('basic', 'Basic', 'Perfect for casual creators', 19.00, 10, '720p', false, 2,
     '{"max_file_size_mb": 50, "support_level": "email", "export_formats": ["mp4", "webm"], "custom_voices": true}'::jsonb),
     
    ('pro', 'Pro', 'For professional content creators', 49.00, 50, '1080p', false, 3,
     '{"max_file_size_mb": 200, "support_level": "priority", "export_formats": ["mp4", "webm", "mov"], "custom_voices": true, "api_access": true, "team_collaboration": true}'::jsonb);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_user_subscriptions_updated_at BEFORE UPDATE
    ON user_subscriptions FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscription_tiers_updated_at BEFORE UPDATE
    ON subscription_tiers FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to check usage limits
CREATE OR REPLACE FUNCTION check_usage_limit(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_subscription RECORD;
BEGIN
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id
    AND status = 'active';
    
    IF NOT FOUND THEN
        -- No active subscription, use free tier limits
        SELECT * INTO v_subscription
        FROM subscription_tiers
        WHERE tier = 'free';
        RETURN true; -- Allow free tier by default
    END IF;
    
    -- Check if within limits
    RETURN v_subscription.videos_generated_this_period < v_subscription.monthly_video_limit;
END;
$$ LANGUAGE plpgsql;

-- Create function to increment usage
CREATE OR REPLACE FUNCTION increment_usage(p_user_id UUID, p_resource_id UUID DEFAULT NULL)
RETURNS VOID AS $$
DECLARE
    v_subscription RECORD;
BEGIN
    -- Get current subscription
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id
    AND status = 'active'
    FOR UPDATE;
    
    IF FOUND THEN
        -- Increment usage counter
        UPDATE user_subscriptions
        SET videos_generated_this_period = videos_generated_this_period + 1,
            updated_at = NOW()
        WHERE id = v_subscription.id;
        
        -- Log usage
        INSERT INTO usage_logs (
            user_id,
            subscription_id,
            resource_type,
            resource_id,
            billing_period_start,
            billing_period_end
        ) VALUES (
            p_user_id,
            v_subscription.id,
            'video_generation',
            p_resource_id,
            v_subscription.current_period_start,
            v_subscription.current_period_end
        );
    ELSE
        -- Create free subscription if none exists
        INSERT INTO user_subscriptions (
            user_id,
            tier,
            status,
            monthly_video_limit,
            videos_generated_this_period,
            current_period_start,
            current_period_end
        ) VALUES (
            p_user_id,
            'free',
            'active',
            2,
            1,
            NOW(),
            NOW() + INTERVAL '30 days'
        )
        ON CONFLICT (user_id) DO UPDATE
        SET videos_generated_this_period = user_subscriptions.videos_generated_this_period + 1;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function to reset monthly usage (to be called by cron job or webhook)
CREATE OR REPLACE FUNCTION reset_monthly_usage()
RETURNS INTEGER AS $$
DECLARE
    rows_updated INTEGER;
BEGIN
    UPDATE user_subscriptions
    SET videos_generated_this_period = 0,
        current_period_start = NOW(),
        current_period_end = NOW() + INTERVAL '30 days',
        updated_at = NOW()
    WHERE current_period_end <= NOW()
    AND status = 'active';
    
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    RETURN rows_updated;
END;
$$ LANGUAGE plpgsql;

-- Create RLS policies
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_tiers ENABLE ROW LEVEL SECURITY;

-- Users can only view their own subscription
CREATE POLICY "Users can view own subscription" ON user_subscriptions
    FOR SELECT USING (auth.uid() = user_id);

-- Users can only view their own usage logs
CREATE POLICY "Users can view own usage logs" ON usage_logs
    FOR SELECT USING (auth.uid() = user_id);

-- Users can only view their own subscription history
CREATE POLICY "Users can view own subscription history" ON subscription_history
    FOR SELECT USING (auth.uid() = user_id);

-- Everyone can view subscription tiers (public information)
CREATE POLICY "Everyone can view subscription tiers" ON subscription_tiers
    FOR SELECT USING (is_active = true);

-- Service role can manage all subscription data
CREATE POLICY "Service role full access to subscriptions" ON user_subscriptions
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role full access to usage logs" ON usage_logs
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role full access to subscription history" ON subscription_history
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role full access to subscription tiers" ON subscription_tiers
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');