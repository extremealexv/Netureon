-- Add additional fields to discovery_log table
ALTER TABLE discovery_log 
ADD COLUMN IF NOT EXISTS hostname VARCHAR(255),
ADD COLUMN IF NOT EXISTS vendor VARCHAR(255);

-- Create index for faster activity lookups
CREATE INDEX IF NOT EXISTS idx_discovery_log_timestamp 
ON discovery_log (timestamp);
