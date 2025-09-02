"""Email notification system for NetGuard."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from webui.models.config import Configuration


class EmailNotifier:
    """Handles sending email notifications."""

    def __init__(self):
        """Initialize email notifier with configuration."""
        self.enabled = Configuration.get_setting('enable_email_notifications') == 'true'
        self.smtp_server = Configuration.get_setting('smtp_server')
        self.smtp_port = int(Configuration.get_setting('smtp_port', '587'))
        self.smtp_username = Configuration.get_setting('smtp_username')
        self.smtp_password = Configuration.get_setting('smtp_password')
        self.from_address = Configuration.get_setting('smtp_from_address')
        self.to_address = Configuration.get_setting('smtp_to_address')

    def notify(self, subject: str, message: str) -> None:
        """Send an email notification."""
        if not self.enabled:
            return

        if not all([self.smtp_server, self.smtp_username, self.smtp_password,
                   self.from_address, self.to_address]):
            return

        msg = MIMEMultipart()
        msg['From'] = self.from_address
        msg['To'] = self.to_address
        msg['Subject'] = f'NetGuard Alert: {subject}'

        msg.attach(MIMEText(message, 'plain'))

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f'Failed to send email notification: {e}')

    async def notify_new_device_detected(self, device_info: dict) -> None:
        """Notify about new device detection."""
        subject = 'New Device Detected'
        message = (f"A new device has been detected on the network:\n\n"
                  f"MAC Address: {device_info.get('mac_address')}\n"
                  f"IP Address: {device_info.get('ip_address')}\n"
                  f"Hostname: {device_info.get('hostname')}\n"
                  f"Vendor: {device_info.get('vendor')}\n"
                  f"First Seen: {device_info.get('first_seen')}")
        self.notify(subject, message)

    async def notify_device_approved(self, device_info: dict) -> None:
        """Notify when a device is approved."""
        subject = 'Device Approved'
        message = (f"A device has been approved:\n\n"
                  f"MAC Address: {device_info.get('mac_address')}\n"
                  f"IP Address: {device_info.get('ip_address')}\n"
                  f"Hostname: {device_info.get('hostname')}\n"
                  f"Vendor: {device_info.get('vendor')}")
        self.notify(subject, message)

    async def notify_device_blocked(self, device_info: dict) -> None:
        """Notify when a device is blocked."""
        subject = 'Device Blocked'
        message = (f"A device has been blocked:\n\n"
                  f"MAC Address: {device_info.get('mac_address')}\n"
                  f"IP Address: {device_info.get('ip_address')}\n"
                  f"Hostname: {device_info.get('hostname')}\n"
                  f"Vendor: {device_info.get('vendor')}")
        self.notify(subject, message)

    async def notify_unknown_device(self, mac: str, ip: str, threat_level: str) -> None:
        """Notify about an unknown device."""
        subject = f'Unknown Device ({threat_level.title()} Risk)'
        message = (f"An unknown device has been detected:\n\n"
                  f"MAC Address: {mac}\n"
                  f"IP Address: {ip}\n"
                  f"Threat Level: {threat_level.title()}")
        self.notify(subject, message)

    async def notify_system_alert(self, alert_type: str, message: str) -> None:
        """Send a system alert."""
        subject = f'System Alert: {alert_type}'
        self.notify(subject, message)
