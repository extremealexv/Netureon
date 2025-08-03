-- Safely migrate the alerts table
BEGIN;

-- Backup existing alerts if table exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alerts') THEN
        CREATE TABLE alerts_backup AS SELECT * FROM alerts;
    END IF;
END $$;

-- Drop existing alerts table if it exists
DROP TABLE IF EXISTS alerts;

-- Create new alerts table with updated schema
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(17) NOT NULL, -- This will store the MAC address
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    alert_type TEXT CHECK (alert_type IN ('new_device', 'unknown_device')),
    details TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('low', 'medium', 'high')) DEFAULT 'medium',
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_alerts_device ON alerts(device_id);
CREATE INDEX idx_alerts_type ON alerts(alert_type);
CREATE INDEX idx_alerts_resolved ON alerts(is_resolved);
CREATE INDEX idx_alerts_severity ON alerts(severity);

-- Migrate data from backup if it exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alerts_backup') THEN
        -- Insert old data with best-effort mapping
        INSERT INTO alerts (device_id, detected_at, alert_type, details, severity, is_resolved)
        SELECT 
            device_id,
            detected_at,
            alert_type,
            COALESCE(message, 'No details available') as details,
            'medium' as severity, -- Default all old alerts to medium severity
            TRUE as is_resolved  -- Mark old alerts as resolved
        FROM alerts_backup;

        -- Drop the backup table
        DROP TABLE alerts_backup;
    END IF;
END $$;

-- Add a unique constraint to prevent duplicate unresolved alerts for the same device/type
CREATE UNIQUE INDEX idx_unique_unresolved_alert 
ON alerts (device_id, alert_type) 
WHERE NOT is_resolved;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON alerts TO netguard_app;
GRANT USAGE, SELECT ON SEQUENCE alerts_id_seq TO netguard_app;

COMMIT;
