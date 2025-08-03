-- Convert all MAC address columns to macaddr type
ALTER TABLE known_devices ALTER COLUMN mac_address TYPE macaddr USING mac_address::macaddr;
ALTER TABLE discovery_log ALTER COLUMN mac_address TYPE macaddr USING mac_address::macaddr;
ALTER TABLE alerts ALTER COLUMN device_id TYPE macaddr USING device_id::macaddr;
ALTER TABLE new_devices ALTER COLUMN mac_address TYPE macaddr USING mac_address::macaddr;
ALTER TABLE unknown_devices ALTER COLUMN mac_address TYPE macaddr USING mac_address::macaddr;
