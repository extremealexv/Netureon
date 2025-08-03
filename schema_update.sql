-- Add unknown_devices table
CREATE TABLE IF NOT EXISTS unknown_devices (
    id SERIAL PRIMARY KEY,
    mac_address MACADDR UNIQUE NOT NULL,
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    last_ip INET,
    notes TEXT,
    threat_level TEXT CHECK (threat_level IN ('low', 'medium', 'high')) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add alert type to alerts table if not exists
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='alerts' AND column_name='alert_type') THEN
        ALTER TABLE alerts ADD COLUMN alert_type TEXT CHECK (alert_type IN ('new_device', 'unknown_device'));
    END IF;
END $$;
