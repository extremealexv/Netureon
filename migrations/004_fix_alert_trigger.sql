-- Fix for alerts trigger function to include required fields
DO $$ 
BEGIN
    -- Drop all triggers that use the insert_alert function
    DROP TRIGGER IF EXISTS discovery_alert_trigger ON discovery_log;
    DROP TRIGGER IF EXISTS new_device_alert ON new_devices;
    
    -- Now we can safely drop the function
    DROP FUNCTION IF EXISTS insert_alert();
END $$;

-- Create updated trigger function
CREATE OR REPLACE FUNCTION insert_alert() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO alerts (device_id, detected_at, alert_type, details, severity)
    VALUES (
        NEW.mac_address, 
        CURRENT_TIMESTAMP,
        CASE 
            WHEN NOT NEW.is_known THEN 'unknown_device'
            ELSE 'new_device'
        END,
        CASE 
            WHEN NOT NEW.is_known THEN 'Unknown device detected: ' || NEW.mac_address || ' at ' || NEW.ip_address::text
            ELSE 'New device detected: ' || NEW.mac_address || ' at ' || NEW.ip_address::text
        END,
        'medium'
    )
    ON CONFLICT (device_id, alert_type) WHERE NOT is_resolved 
    DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate the trigger
CREATE TRIGGER discovery_alert_trigger
    AFTER INSERT ON discovery_log
    FOR EACH ROW
    EXECUTE FUNCTION insert_alert();
