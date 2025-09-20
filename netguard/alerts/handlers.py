from ..logging.logger import setup_logging
from ..config.settings import Settings
from device_profiler import DeviceProfiler
import json
import psycopg2

logger = setup_logging('netureon.handlers')

class DeviceHandler:
    def __init__(self):
        self.db_config = Settings.get_db_config()
        self.profiler = DeviceProfiler()

    def process_new_device(self, mac, ip, timestamp):
        """Process a newly detected device."""
        logger.info(f"\nProcessing device: MAC={mac}, IP={ip}")
        
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    # Profile device
                    profile = self.profiler.profile_device(ip, mac)
                    if not profile:
                        logger.error(f"Failed to profile device {mac}")
                        return False

                    # Store profile and create alert
                    self._store_device_profile(cursor, mac, ip, profile)
                    alert_id = self._create_alert(cursor, mac, ip, profile, timestamp)
                    
                    conn.commit()
                    return alert_id

        except Exception as e:
            logger.error(f"Error processing device {mac}: {str(e)}")
            return False