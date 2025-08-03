-- Remove automatic alert trigger as we're handling alerts through the daemon
DO $$ 
BEGIN
    -- Drop the trigger from discovery_log table
    DROP TRIGGER IF EXISTS discovery_alert_trigger ON discovery_log;
    
    -- Drop the trigger function since we won't need it anymore
    DROP FUNCTION IF EXISTS insert_alert();
    
    -- Clean up duplicate alerts, keeping only the earliest alert for each device/type combination
    WITH DuplicateAlerts AS (
        SELECT id,
        ROW_NUMBER() OVER (
            PARTITION BY device_id, alert_type 
            ORDER BY detected_at ASC
        ) as rn
        FROM alerts
    )
    DELETE FROM alerts 
    WHERE id IN (
        SELECT id 
        FROM DuplicateAlerts 
        WHERE rn > 1
    );
END $$;
