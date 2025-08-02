-- 1. Table for known/trusted devices
CREATE TABLE known_devices (
    id SERIAL PRIMARY KEY,
    mac_address VARCHAR(17) UNIQUE NOT NULL,
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
    mac_address VARCHAR(17) NOT NULL,
    ip_address INET,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    is_known BOOLEAN NOT NULL DEFAULT FALSE
);

-- Optional index for faster lookup by MAC address
CREATE INDEX idx_discovery_mac ON discovery_log(mac_address);

-- 3. Table for newly discovered devices pending review
CREATE TABLE new_devices (
    id SERIAL PRIMARY KEY,
    mac_address VARCHAR(17) UNIQUE NOT NULL,
    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP,
    last_ip INET,
    reviewed BOOLEAN NOT NULL DEFAULT FALSE
);
