-- Add vendor, hostname, and open_ports columns to device tables
ALTER TABLE known_devices
ADD COLUMN vendor VARCHAR(100),
ADD COLUMN hostname VARCHAR(200),
ADD COLUMN open_ports TEXT;

ALTER TABLE new_devices
ADD COLUMN vendor VARCHAR(100),
ADD COLUMN hostname VARCHAR(200),
ADD COLUMN open_ports TEXT;

ALTER TABLE unknown_devices
ADD COLUMN vendor VARCHAR(100),
ADD COLUMN hostname VARCHAR(200),
ADD COLUMN open_ports TEXT;

COMMENT ON COLUMN known_devices.vendor IS 'MAC address vendor/manufacturer';
COMMENT ON COLUMN known_devices.hostname IS 'Device hostname if discoverable';
COMMENT ON COLUMN known_devices.open_ports IS 'List of detected open ports';

COMMENT ON COLUMN new_devices.vendor IS 'MAC address vendor/manufacturer';
COMMENT ON COLUMN new_devices.hostname IS 'Device hostname if discoverable';
COMMENT ON COLUMN new_devices.open_ports IS 'List of detected open ports';

COMMENT ON COLUMN unknown_devices.vendor IS 'MAC address vendor/manufacturer';
COMMENT ON COLUMN unknown_devices.hostname IS 'Device hostname if discoverable';
COMMENT ON COLUMN unknown_devices.open_ports IS 'List of detected open ports';
