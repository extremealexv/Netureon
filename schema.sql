-- 1. Table for known/trusted devices
CREATE TABLE known_devices (
    id SERIAL PRIMARY KEY,
    mac_address macaddr UNIQUE NOT NULL,
    device_name VARCHAR(100),
    device_type VARCHAR(50),
    notes TEXT,
    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP,
    last_ip INET
);

-- 2. Table for logging all discovery events
CREATE TABLE discovery_log (
    id SERIAL PRIMARY KEY,
    mac_address macaddr NOT NULL,
    ip_address INET,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    is_known BOOLEAN NOT NULL DEFAULT FALSE
);

-- Create index for faster lookup by MAC address
CREATE INDEX idx_discovery_mac ON discovery_log(mac_address);
CREATE INDEX idx_discovery_time ON discovery_log(timestamp);

-- 3. Table for newly discovered devices pending review
CREATE TABLE new_devices (
    id SERIAL PRIMARY KEY,
    mac_address macaddr UNIQUE NOT NULL,
    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP,
    last_ip INET,
    reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    device_name VARCHAR(100),
    device_type VARCHAR(50),
    notes TEXT
);

-- Create index for faster new device lookups
CREATE INDEX idx_new_devices_mac ON new_devices(mac_address);
CREATE INDEX idx_new_devices_reviewed ON new_devices(reviewed);

-- 4. Table for unknown/threat devices
CREATE TABLE unknown_devices (
    id SERIAL PRIMARY KEY,
    mac_address macaddr UNIQUE NOT NULL,
    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP,
    last_ip INET,
    threat_level TEXT CHECK (threat_level IN ('low', 'medium', 'high')) DEFAULT 'medium',
    notes TEXT
);

-- Create index for faster threat lookups
CREATE INDEX idx_unknown_devices_mac ON unknown_devices(mac_address);
CREATE INDEX idx_unknown_devices_threat ON unknown_devices(threat_level);

-- 5. Table for alerts and notifications
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    device_id macaddr NOT NULL,
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    alert_type TEXT CHECK (alert_type IN ('new_device', 'unknown_device')),
    details TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('low', 'medium', 'high')) DEFAULT 'medium',
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT
);

-- Create indexes for better alert performance
CREATE INDEX idx_alerts_device ON alerts(device_id);
CREATE INDEX idx_alerts_type ON alerts(alert_type);
CREATE INDEX idx_alerts_resolved ON alerts(is_resolved);
CREATE INDEX idx_alerts_severity ON alerts(severity);

-- 6. Create composite indexes for common queries
CREATE INDEX idx_discovery_mac_time ON discovery_log(mac_address, timestamp);
CREATE INDEX idx_alerts_device_type ON alerts(device_id, alert_type) WHERE NOT is_resolved;
CREATE INDEX idx_device_last_seen ON known_devices(last_seen DESC NULLS LAST);
CREATE INDEX idx_unknown_last_seen ON unknown_devices(last_seen DESC NULLS LAST);

-- Add comments for documentation
COMMENT ON TABLE known_devices IS 'Stores information about authorized network devices';
COMMENT ON TABLE discovery_log IS 'Historical record of device appearances on the network';
COMMENT ON TABLE new_devices IS 'Newly discovered devices pending admin review';
COMMENT ON TABLE unknown_devices IS 'Potentially suspicious or unauthorized devices';
COMMENT ON TABLE alerts IS 'System alerts and notifications for device activity';

COMMENT ON COLUMN alerts.device_id IS 'MAC address of the device that triggered the alert';
COMMENT ON COLUMN alerts.alert_type IS 'Type of alert: new_device for first appearances, unknown_device for suspicious activity';
COMMENT ON COLUMN alerts.severity IS 'Alert severity level: low, medium, or high';
COMMENT ON COLUMN alerts.resolution_notes IS 'Notes added when resolving/acknowledging an alert';
