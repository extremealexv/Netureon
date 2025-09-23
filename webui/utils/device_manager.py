from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DeviceManager:
    """Utility class for managing device data."""

    @staticmethod
    def format_device_list(devices):
        """Format device list for display."""
        try:
            formatted_devices = []
            for device in devices:
                formatted_device = {
                    'mac': device['mac'],
                    'hostname': device['hostname'] or 'Unknown Device',
                    'last_ip': device['last_ip'],
                    'first_seen': DeviceManager._format_datetime(device['first_seen']),
                    'last_seen': DeviceManager._format_datetime(device['last_seen']),
                    'alert_count': device['alert_count'],
                    'threat_level': device.get('threat_level', 'low'),
                    'notes': device.get('notes', ''),
                    'alert_types': device.get('alert_types', '')
                }
                formatted_devices.append(formatted_device)
            return formatted_devices
        except Exception as e:
            logger.error(f"Error formatting device list: {str(e)}")
            return []

    @staticmethod
    def _format_datetime(dt):
        """Format datetime for display."""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError:
                return dt
        return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'Unknown'