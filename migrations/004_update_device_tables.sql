-- Add new columns to known_devices
ALTER TABLE known_devices 
ADD COLUMN IF NOT EXISTS hostname VARCHAR(255),
ADD COLUMN IF NOT EXISTS vendor VARCHAR(255),
ADD COLUMN IF NOT EXISTS open_ports jsonb,
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'inactive';

-- Add new columns to new_devices
ALTER TABLE new_devices 
ADD COLUMN IF NOT EXISTS hostname VARCHAR(255),
ADD COLUMN IF NOT EXISTS vendor VARCHAR(255),
ADD COLUMN IF NOT EXISTS open_ports jsonb;

-- Add index for status on known_devices
CREATE INDEX IF NOT EXISTS idx_known_devices_status ON known_devices(status);

-- Update existing records
UPDATE known_devices SET status = 'inactive' WHERE status IS NULL;
