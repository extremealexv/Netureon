-- Increase hostname length limits
ALTER TABLE known_devices ALTER COLUMN device_name TYPE VARCHAR(255);
ALTER TABLE new_devices ALTER COLUMN device_name TYPE VARCHAR(255);
ALTER TABLE known_devices ALTER COLUMN device_type TYPE VARCHAR(100);
ALTER TABLE new_devices ALTER COLUMN device_type TYPE VARCHAR(100);
