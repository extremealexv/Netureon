from ..logging.logger import setup_logging
from ..config.settings import Settings
from device_profiler import DeviceProfiler
import psycopg2
import json

logger = setup_logging('netureon.handlers')

class DeviceHandler:
    def __init__(self):
        self.settings = Settings.get_instance()
        self.db_config = self.settings.get_db_config()
        self.profiler = DeviceProfiler()

    def check_for_unknown_devices(self):
        """Check and profile new devices."""
        logger.info("=== Starting device check cycle ===")
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    # Get only new devices without profiles
                    cursor.execute("""
                        SELECT DISTINCT ON (nd.mac_address)
                            nd.mac_address::text,
                            nd.last_ip::text,
                            nd.last_seen
                        FROM new_devices nd
                        LEFT JOIN device_profiles dp ON dp.mac_address = nd.mac_address
                        LEFT JOIN alerts a ON a.device_id = nd.mac_address 
                        WHERE dp.mac_address IS NULL
                        AND a.id IS NULL
                        AND nd.last_seen > NOW() - INTERVAL '5 minutes'
                    """)
                    
                    new_devices = cursor.fetchall()
                    return new_devices if new_devices else []
                    
        except Exception as e:
            logger.error(f"Error checking for unknown devices: {str(e)}")
            return []

    def store_device_profile(self, mac, profile):
        """Store device profile in database."""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE new_devices 
                        SET hostname = %s,
                            vendor = %s,
                            device_type = %s,
                            open_ports = %s::jsonb,
                            last_updated = NOW()
                        WHERE mac_address = %s::macaddr
                    """, (
                        profile.get('hostname', 'Unknown'),
                        profile.get('vendor', 'Unknown'),
                        profile.get('device_type', 'Unknown'),
                        json.dumps(profile.get('open_ports', [])),
                        mac
                    ))
                    conn.commit()
                    logger.info(f"Stored profile for device {mac}")
        except Exception as e:
            logger.error(f"Failed to store profile for {mac}: {e}")

    def profile_device(self, mac, ip, timestamp):
        """Profile a device and send notifications."""
        try:
            profile = self.profiler.profile_device(ip, mac)
            if profile:
                # Store profile
                self.store_device_profile(mac, profile)
                
                # Create alert with profile info
                details = f"""New device detected:
MAC: {mac}
IP: {ip}
Hostname: {profile.get('hostname', 'Unknown')}
Vendor: {profile.get('vendor', 'Unknown')}
Type: {profile.get('device_type', 'Unknown')}
Open Ports: {', '.join(f"{p['port']} ({p['service']})" for p in profile.get('open_ports', []))}"""

                alert_id = self.create_alert(mac, ip, details, timestamp)
                
                # Send notifications immediately
                if alert_id:
                    self.send_notifications(
                        alert_id, 
                        "NetGuard Alert: New Device Detected", 
                        details
                    )
                
                return alert_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error profiling device {mac}: {e}")
            return None

    def process_new_device(self, mac, ip, timestamp):
        """Process a newly detected device."""
        logger.info(f"=== Starting device processing for {mac} ({ip}) ===")
        
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    # First check if device already has an alert
                    cursor.execute("""
                        SELECT id FROM alerts 
                        WHERE device_id = %s::macaddr 
                        AND alert_type = 'new_device'
                        AND detected_at > NOW() - INTERVAL '1 hour'
                    """, (mac,))
                    
                    if cursor.fetchone():
                        logger.info(f"Device {mac} already has recent alert")
                        return None

                    # Profile device
                    logger.info(f"Starting device profiling for {mac}")
                    profile = self.profiler.profile_device(ip, mac)
                    
                    if profile:
                        logger.info(f"Profile results for {mac}:")
                        logger.info(f"  • Hostname: {profile.get('hostname', 'Unknown')}")
                        logger.info(f"  • Vendor: {profile.get('vendor', 'Unknown')}")
                        logger.info(f"  • Type: {profile.get('device_type', 'Unknown')}")
                        
                        # Store profile
                        cursor.execute("""
                            INSERT INTO device_profiles 
                            (mac_address, hostname, vendor, device_type, open_ports, last_updated)
                            VALUES (%s::macaddr, %s, %s, %s, %s::jsonb, NOW())
                            ON CONFLICT (mac_address) DO UPDATE SET
                                hostname = EXCLUDED.hostname,
                                vendor = EXCLUDED.vendor,
                                device_type = EXCLUDED.device_type,
                                open_ports = EXCLUDED.open_ports,
                                last_updated = NOW()
                        """, (
                            mac,
                            profile.get('hostname', 'Unknown'),
                            profile.get('vendor', 'Unknown'),
                            profile.get('device_type', 'Unknown'),
                            json.dumps(profile.get('open_ports', []))
                        ))
                        
                        # Create alert
                        details = f"""New device detected:
MAC: {mac}
IP: {ip}
First Seen: {timestamp}
Hostname: {profile.get('hostname', 'Unknown')}
Vendor: {profile.get('vendor', 'Unknown')}
Type: {profile.get('device_type', 'Unknown')}
Open Ports: {', '.join(str(p['port']) for p in profile.get('open_ports', []))}"""

                        cursor.execute("""
                            INSERT INTO alerts 
                            (device_id, alert_type, detected_at, details, severity)
                            VALUES (%s::macaddr, 'new_device', NOW(), %s, 'medium')
                            RETURNING id
                        """, (mac, details))
                        
                        alert_id = cursor.fetchone()[0]
                        conn.commit()
                        
                        logger.info(f"Created alert {alert_id} for device {mac}")
                        return alert_id
                    else:
                        logger.error(f"Failed to profile device {mac}")
                        return None

        except Exception as e:
            logger.error(f"Error processing device {mac}: {str(e)}")
            return None

    def _store_profile(self, cursor, mac, profile):
        """Store or update device profile in the database."""
        cursor.execute("""
            INSERT INTO device_profiles 
            (mac_address, hostname, vendor, device_type, open_ports, last_updated)
            VALUES (%s::macaddr, %s, %s, %s, %s::jsonb, NOW())
            ON CONFLICT (mac_address) DO UPDATE SET
                hostname = EXCLUDED.hostname,
                vendor = EXCLUDED.vendor,
                device_type = EXCLUDED.device_type,
                open_ports = EXCLUDED.open_ports,
                last_updated = NOW()
        """, (
            mac,
            profile.get('hostname', 'Unknown'),
            profile.get('vendor', 'Unknown'),
            profile.get('device_type', 'Unknown'),
            json.dumps(profile.get('open_ports', []))
        ))

    def _create_alert(self, cursor, mac, ip, profile, timestamp):
        """Create an alert for the detected device."""
        details = f"""New device detected:
MAC: {mac}
IP: {ip}
First Seen: {timestamp}
Hostname: {profile.get('hostname', 'Unknown')}
Vendor: {profile.get('vendor', 'Unknown')}
Type: {profile.get('device_type', 'Unknown')}
Open Ports: {', '.join(str(p['port']) for p in profile.get('open_ports', []))}"""

        cursor.execute("""
            INSERT INTO alerts 
            (device_id, alert_type, detected_at, details, severity)
            VALUES (%s::macaddr, 'new_device', NOW(), %s, 'medium')
            RETURNING id
        """, (mac, details))
        
        return cursor.fetchone()[0]

    def get_alert(self, alert_id):
        """Get alert details by ID."""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            device_id,
                            alert_type,
                            detected_at,
                            details,
                            severity
                        FROM alerts 
                        WHERE id = %s
                    """, (alert_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'id': alert_id,
                            'device_id': row[0],
                            'type': row[1],
                            'timestamp': row[2],
                            'details': row[3],
                            'severity': row[4]
                        }
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting alert {alert_id}: {str(e)}")
            return None

    def update_alert_status(self, alert_id, email_sent, telegram_sent):
        """Update alert status after sending notifications."""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE alerts 
                        SET is_resolved = true,
                            resolved_at = NOW(),
                            resolution_notes = %s
                        WHERE id = %s
                    """, (
                        f"Notifications sent - Email: {'✓' if email_sent else '✗'}, "
                        f"Telegram: {'✓' if telegram_sent else '✗'}",
                        alert_id
                    ))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Error updating alert {alert_id}: {str(e)}")