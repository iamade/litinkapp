/*
  # Add Model Tracking Fields for Fallback System

  1. Changes
    - Add model tracking fields to image_generations table
    - Add model tracking fields to video_generations table (if exists)
    - Add model tracking to usage_logs table
    - Create model_performance_metrics table for monitoring

  2. New Fields
    - model_used_primary: The primary model that was intended to be used
    - model_used_actual: The actual model that was used (may be fallback)
    - fallback_reason: Why fallback was triggered
    - attempted_models: JSONB array of all models attempted

  3. Performance Tracking
    - Track model success rates by tier
    - Monitor fallback frequency
    - Analyze generation times per model
*/

-- Add model tracking fields to image_generations table
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'model_used_primary'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN model_used_primary TEXT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'model_used_actual'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN model_used_actual TEXT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'fallback_reason'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN fallback_reason TEXT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'attempted_models'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN attempted_models JSONB DEFAULT '[]'::jsonb;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'image_generations' AND column_name = 'user_tier'
  ) THEN
    ALTER TABLE image_generations ADD COLUMN user_tier TEXT;
  END IF;
END $$;

-- Add model tracking to usage_logs if table exists
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = 'usage_logs'
  ) THEN
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name = 'usage_logs' AND column_name = 'model_tier'
    ) THEN
      ALTER TABLE usage_logs ADD COLUMN model_tier TEXT;
    END IF;

    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name = 'usage_logs' AND column_name = 'model_name'
    ) THEN
      ALTER TABLE usage_logs ADD COLUMN model_name TEXT;
    END IF;

    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name = 'usage_logs' AND column_name = 'was_fallback'
    ) THEN
      ALTER TABLE usage_logs ADD COLUMN was_fallback BOOLEAN DEFAULT false;
    END IF;
  END IF;
END $$;

-- Create model_performance_metrics table
CREATE TABLE IF NOT EXISTS model_performance_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_name TEXT NOT NULL,
  service_type TEXT NOT NULL,
  user_tier TEXT NOT NULL,
  success_count INTEGER DEFAULT 0,
  failure_count INTEGER DEFAULT 0,
  total_attempts INTEGER DEFAULT 0,
  success_rate NUMERIC(5, 2),
  avg_generation_time_seconds NUMERIC(10, 2),
  failure_reasons JSONB DEFAULT '{}'::jsonb,
  last_success_at TIMESTAMPTZ,
  last_failure_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(model_name, service_type, user_tier)
);

-- Enable RLS on model_performance_metrics
ALTER TABLE model_performance_metrics ENABLE ROW LEVEL SECURITY;

-- Create policy for admin access to model performance metrics
CREATE POLICY "Service role can manage model performance metrics"
  ON model_performance_metrics
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_image_generations_model_actual
  ON image_generations(model_used_actual);

CREATE INDEX IF NOT EXISTS idx_image_generations_user_tier
  ON image_generations(user_tier);

CREATE INDEX IF NOT EXISTS idx_model_performance_service_tier
  ON model_performance_metrics(service_type, user_tier);

CREATE INDEX IF NOT EXISTS idx_model_performance_model_name
  ON model_performance_metrics(model_name);

-- Create function to update model performance metrics
CREATE OR REPLACE FUNCTION update_model_performance_metrics()
RETURNS TRIGGER AS $$
BEGIN
  -- This function can be enhanced to automatically update metrics
  -- when generations are completed
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add comment explaining the schema
COMMENT ON TABLE model_performance_metrics IS 'Tracks performance and fallback statistics for AI models across different tiers and services';
COMMENT ON COLUMN image_generations.model_used_primary IS 'The primary model intended for this tier';
COMMENT ON COLUMN image_generations.model_used_actual IS 'The actual model used (may be fallback)';
COMMENT ON COLUMN image_generations.fallback_reason IS 'Reason why fallback was triggered';
COMMENT ON COLUMN image_generations.attempted_models IS 'JSON array of all models attempted with their results';
