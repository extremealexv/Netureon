"""Email notification system for Netureon."""
import smtplib
from email.mime.text import MIMEText
import logging
from ..models.config import Config


class EmailNotifier:
    """Handles sending email notifications."""

    def __init__(self):
        """Initialize email notifier with configuration."""
        self.logger = logging.getLogger('netureon')
        self.config = Config.get_email_config()
        
        if not self.config:
            self.logger.error("Email configuration not found in database")
            return

    def send_email(self, subject, body):
        """Send email using configuration from database"""
        if not self.config:
            self.logger.error("Email not configured - skipping notification")
            return False

        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['email_to']

            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls()
            server.login(self.config['smtp_user'], self.config['smtp_password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info("Email sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            return False

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
