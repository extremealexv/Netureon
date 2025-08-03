-- Fix alerts table device_id type to be consistent with other MAC address columns
ALTER TABLE alerts ALTER COLUMN device_id TYPE macaddr USING device_id::macaddr;
