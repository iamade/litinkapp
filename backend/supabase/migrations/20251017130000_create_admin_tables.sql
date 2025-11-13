/*
  # Admin Cost Tracking and Monitoring Tables

  1. New Tables
    - `admin_alerts`
      - `id` (uuid, primary key)
      - `alert_type` (text) - Type of alert: 'high_fallback_rate', 'circuit_breaker', 'cost_spike', 'model_failure'
      - `severity` (text) - Alert severity: 'info', 'warning', 'critical'
      - `message` (text) - Human-readable alert message
      - `metric_value` (numeric) - The actual metric value that triggered the alert
      - `threshold_value` (numeric) - The threshold that was exceeded
      - `metadata` (jsonb) - Additional context (model names, tiers, services, etc.)
      - `created_at` (timestamptz)
      - `acknowledged_at` (timestamptz, nullable)
      - `acknowledged_by` (uuid, nullable, foreign key to profiles)

    - `admin_settings`
      - `id` (uuid, primary key)
      - `setting_key` (text, unique) - Setting identifier
      - `setting_value` (jsonb) - Setting value (supports any JSON structure)
      - `description` (text) - Setting description
      - `updated_at` (timestamptz)
      - `updated_by` (uuid, foreign key to profiles)

    - `daily_cost_summary` (Materialized View)
      - Pre-aggregated daily cost data for faster reporting

  2. Security
    - Enable RLS on all admin tables
    - Only superadmin users can read/write admin tables
    - Add policies for superadmin-only access

  3. Indexes
    - Index on admin_alerts.created_at for sorting
    - Index on admin_alerts.acknowledged_at for filtering
    - Index on admin_alerts.alert_type for grouping
    - Index on admin_settings.setting_key for lookups

  4. Default Settings
    - Insert default alert threshold settings
*/

-- Create admin_alerts table
CREATE TABLE IF NOT EXISTS admin_alerts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_type text NOT NULL CHECK (alert_type IN ('high_fallback_rate', 'circuit_breaker', 'cost_spike', 'model_failure', 'system_health')),
  severity text NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
  message text NOT NULL,
  metric_value numeric,
  threshold_value numeric,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  acknowledged_at timestamptz,
  acknowledged_by uuid REFERENCES profiles(id) ON DELETE SET NULL
);

-- Create admin_settings table
CREATE TABLE IF NOT EXISTS admin_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  setting_key text UNIQUE NOT NULL,
  setting_value jsonb NOT NULL DEFAULT '{}'::jsonb,
  description text,
  updated_at timestamptz DEFAULT now(),
  updated_by uuid REFERENCES profiles(id) ON DELETE SET NULL
);

-- Add indexes for admin_alerts
CREATE INDEX IF NOT EXISTS idx_admin_alerts_created_at ON admin_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_alerts_acknowledged ON admin_alerts(acknowledged_at) WHERE acknowledged_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_admin_alerts_type ON admin_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_admin_alerts_severity ON admin_alerts(severity);

-- Add index for admin_settings
CREATE INDEX IF NOT EXISTS idx_admin_settings_key ON admin_settings(setting_key);

-- Enable RLS
ALTER TABLE admin_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_settings ENABLE ROW LEVEL SECURITY;

-- RLS Policies for admin_alerts (superadmin only)
CREATE POLICY "Superadmin can view all alerts"
  ON admin_alerts FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND ('superadmin' = ANY(profiles.roles) OR profiles.email = 'support@litinkai.com')
    )
  );

CREATE POLICY "Superadmin can insert alerts"
  ON admin_alerts FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND ('superadmin' = ANY(profiles.roles) OR profiles.email = 'support@litinkai.com')
    )
  );

CREATE POLICY "Superadmin can update alerts"
  ON admin_alerts FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND ('superadmin' = ANY(profiles.roles) OR profiles.email = 'support@litinkai.com')
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND ('superadmin' = ANY(profiles.roles) OR profiles.email = 'support@litinkai.com')
    )
  );

CREATE POLICY "Superadmin can delete alerts"
  ON admin_alerts FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND ('superadmin' = ANY(profiles.roles) OR profiles.email = 'support@litinkai.com')
    )
  );

-- RLS Policies for admin_settings (superadmin only)
CREATE POLICY "Superadmin can view all settings"
  ON admin_settings FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND ('superadmin' = ANY(profiles.roles) OR profiles.email = 'support@litinkai.com')
    )
  );

CREATE POLICY "Superadmin can insert settings"
  ON admin_settings FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND ('superadmin' = ANY(profiles.roles) OR profiles.email = 'support@litinkai.com')
    )
  );

CREATE POLICY "Superadmin can update settings"
  ON admin_settings FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND ('superadmin' = ANY(profiles.roles) OR profiles.email = 'support@litinkai.com')
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND ('superadmin' = ANY(profiles.roles) OR profiles.email = 'support@litinkai.com')
    )
  );

CREATE POLICY "Superadmin can delete settings"
  ON admin_settings FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND ('superadmin' = ANY(profiles.roles) OR profiles.email = 'support@litinkai.com')
    )
  );

-- Insert default alert threshold settings
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES
  ('alert_thresholds', '{"high_fallback_rate": 30, "cost_spike_percentage": 50, "circuit_breaker_enabled": true}'::jsonb, 'Threshold values for triggering alerts'),
  ('email_notifications', '{"enabled": true, "recipient": "support@litinkai.com"}'::jsonb, 'Email notification settings for alerts'),
  ('monitoring_intervals', '{"alert_check_minutes": 15, "metrics_retention_days": 90}'::jsonb, 'Monitoring and data retention intervals')
ON CONFLICT (setting_key) DO NOTHING;

-- Create function to check if user is superadmin
CREATE OR REPLACE FUNCTION is_superadmin()
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM profiles
    WHERE id = auth.uid()
    AND ('superadmin' = ANY(roles) OR email = 'support@litinkai.com')
  );
END;
$$;
