-- Add resolved_at column to alerts table
ALTER TABLE alerts ADD COLUMN resolved_at TIMESTAMP WITH TIME ZONE;

-- Update existing resolved alerts
UPDATE alerts SET resolved_at = NOW() WHERE is_resolved = true;
