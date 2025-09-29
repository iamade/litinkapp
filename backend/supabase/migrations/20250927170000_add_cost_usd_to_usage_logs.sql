-- Add cost_usd column to usage_logs table
ALTER TABLE usage_logs ADD COLUMN cost_usd DECIMAL(10, 6) DEFAULT 0.0;