class DeviceManager:
    @staticmethod
    def format_device_list(devices):
        """Format device data for template rendering"""
        formatted = []
        for device in devices:
            if not device[0] or device[0] == 'no_mac':
                continue
            formatted.append({
                'mac': device[0].strip(),
                'last_ip': device[1],
                'first_seen': device[2],
                'last_seen': device[3],
                'threat_level': device[4],
                'notes': device[5] if device[5] else 'No notes',
                'detection_count': device[6] if len(device) > 6 else 0,
                'hostname': device[7] if len(device) > 7 else 'Unknown'
            })
        return formatted
