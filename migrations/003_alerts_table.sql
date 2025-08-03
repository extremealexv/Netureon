-- Safely migrate the alerts tab        -- Migrate data from backup if it exists and has required columns
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alerts_backup') 
       AND EXISTS (
           SELECT 1 
           FROM information_schema.columns 
           WHERE table_name = 'alerts_backup' 
           AND column_name IN ('device_id', 'detected_at', 'alert_type')
       ) 
    THENBEGIN;

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
        -- Check what columns exist in the backup
        CREATE TEMP TABLE column_check AS
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'alerts_backup';
        
        -- Insert old data with dynamic column mapping
        DO $inner$ 
        BEGIN
            -- Check if message column exists
            IF EXISTS (SELECT 1 FROM column_check WHERE column_name = 'message') THEN
                INSERT INTO alerts (device_id, detected_at, alert_type, details, severity, is_resolved)
                SELECT 
                    device_id,
                    detected_at,
                    alert_type,
                    message as details,
                    'medium' as severity,
                    TRUE as is_resolved
                FROM alerts_backup;
            -- If no message column but has details column    
            ELSIF EXISTS (SELECT 1 FROM column_check WHERE column_name = 'details') THEN
                INSERT INTO alerts (device_id, detected_at, alert_type, details, severity, is_resolved)
                SELECT 
                    device_id,
                    detected_at,
                    alert_type,
                    details,
                    'medium' as severity,
                    TRUE as is_resolved
                FROM alerts_backup;
            -- Otherwise just use a placeholder for details
            ELSE
                INSERT INTO alerts (device_id, detected_at, alert_type, details, severity, is_resolved)
                SELECT 
                    device_id,
                    detected_at,
                    alert_type,
                    'Migrated alert - no details available' as details,
                    'medium' as severity,
                    TRUE as is_resolved
                FROM alerts_backup;
            END IF;
        END $inner$;
        
        DROP TABLE column_check;

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
