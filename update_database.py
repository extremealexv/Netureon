    async def update_database(self, devices):
        """Update database with discovered devices and send notifications for new devices."""
        if not devices:
            return

        conn = None
        cur = None

        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()

            for ip, mac in devices:
                timestamp = datetime.now()

                # Check device status across all tables
                cur.execute("""
                    SELECT 
                        CASE 
                            WHEN EXISTS (SELECT 1 FROM known_devices WHERE mac_address = %s::macaddr) THEN 'known'
                            WHEN EXISTS (SELECT 1 FROM unknown_devices WHERE mac_address = %s::macaddr) THEN 'threat'
                            WHEN EXISTS (SELECT 1 FROM new_devices WHERE mac_address = %s::macaddr) THEN 'new'
                            ELSE 'unregistered'
                        END as device_status
                """, (mac, mac, mac))
                status = cur.fetchone()[0]

                # Log discovery
                cur.execute("""
                    INSERT INTO discovery_log (mac_address, ip_address, timestamp, is_known)
                    VALUES (%s::macaddr, %s::inet, %s, %s)
                """, (mac, ip, timestamp, status == 'known'))

                # Handle device based on its status
                if status == 'known':
                    cur.execute("""
                        UPDATE known_devices 
                        SET last_seen = %s, last_ip = %s::inet 
                        WHERE mac_address = %s::macaddr
                    """, (timestamp, ip, mac))
                elif status == 'threat':
                    cur.execute("""
                        UPDATE unknown_devices 
                        SET last_seen = %s, last_ip = %s 
                        WHERE mac_address::text = %s
                    """, (timestamp, ip, mac))
                elif status == 'new':
                    cur.execute("""
                        UPDATE new_devices 
                        SET last_seen = %s, last_ip = %s::inet
                        WHERE mac_address = %s::macaddr
                    """, (timestamp, ip, mac))
                else:  # unregistered
                    # Profile device
                    profiler = DeviceProfiler(mac_address=mac, ip_address=ip)
                    vendor = profiler.get_mac_vendor()
                    hostname = profiler.get_hostname()
                    open_ports = profiler.scan_open_ports()

                    notes = f"Vendor: {vendor}, Hostname: {hostname}"
                    if open_ports:
                        notes += f", Open Ports: {', '.join(map(str, open_ports))}"
                    else:
                        notes += ", No common ports open"

                    # Insert new device for review
                    cur.execute("""
                        INSERT INTO new_devices (
                            mac_address, first_seen, last_seen, last_ip, 
                            reviewed, device_name, device_type, notes
                        ) VALUES (%s::macaddr, %s, %s, %s::inet, FALSE, %s, %s, %s)
                    """, (mac, timestamp, timestamp, ip, hostname, vendor, notes))
                    
                    # Send notifications for new device
                    device_info = {
                        'hostname': hostname,
                        'mac_address': mac,
                        'ip_address': ip,
                        'vendor': vendor,
                        'first_seen': timestamp,
                        'open_ports': open_ports,
                        'notes': notes
                    }
                    
                    try:
                        await self.email_notifier.notify_new_device_detected(device_info)
                    except Exception as e:
                        logger.error(f"Failed to send email notification: {e}")
                    
                    try:
                        await self.telegram_notifier.notify_new_device_detected(device_info)
                    except Exception as e:
                        logger.error(f"Failed to send telegram notification: {e}")
                    
                    logger.info(f"New device discovered: {hostname} ({mac} at {ip})")

            conn.commit()

        except Exception as e:
            logger.error(f"Database update error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
