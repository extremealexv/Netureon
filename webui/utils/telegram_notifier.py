"""Telegram notification module for NetGuard."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
import httpx
from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from ..config.config import Config

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram notification handler for NetGuard."""
    
    def __init__(self):
        """Initialize the Telegram notifier."""
        from webui.models.config import Configuration
        self.enabled = Configuration.get_setting('enable_telegram_notifications') == 'true'
        self.bot_token = Config.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = Config.get('TELEGRAM_CHAT_ID')
        self._bot = None
        self._loop = None
        
        if not self.enabled:
            logger.info("Telegram notifications are disabled")
            return
            
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured")
            return
            
        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not configured")
            return
            
        try:
            # Verify the chat_id format
            self.chat_id = str(self.chat_id)
            if not self.chat_id.startswith('-') and not self.chat_id.isdigit():
                logger.error(f"Invalid TELEGRAM_CHAT_ID format: {self.chat_id}")
                return
        except Exception as e:
            logger.error(f"Failed to initialize Telegram notifier: {str(e)}")

    @asynccontextmanager
    async def get_bot(self):
        """Get a bot instance with proper connection pooling."""
        request = HTTPXRequest(
            connection_pool_size=8,
            read_timeout=30,
            write_timeout=30,
            connect_timeout=30,
            pool_timeout=3.0
        )
        bot = Bot(token=self.bot_token, request=request)
        try:
            yield bot
        finally:
            await request.shutdown()

    async def send_message(self, message: str) -> bool:
        """
        Send a message through Telegram.
        
        Args:
            message: The message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not self.bot_token or not self.chat_id:
            logger.error("Telegram bot not configured. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config.")
            return False
            
        try:
            async with self.get_bot() as bot:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML
                )
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {str(e)}")
            return False

    def notify(self, message: str) -> None:
        """
        Synchronous wrapper for sending messages.
        
        Args:
            message: The message to send
        """
        # Refresh enabled state in case it was changed
        from webui.models.config import Configuration
        self.enabled = Configuration.get_setting('enable_telegram_notifications') == 'true'
        
        if not self.enabled:
            logger.debug("Telegram notifications are disabled")
            return
        try:
            asyncio.run(self.send_message(message))
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")

    async def notify_new_device_detected(self, device_info: dict) -> None:
        """
        Send notification about newly detected device during network scan.
        
        Args:
            device_info: Dictionary containing device information
        """
        message = (
            f"🔍 <b>New Device Detected on Network</b>\n\n"
            f"Name: {device_info.get('hostname') or 'Unknown'}\n"
            f"MAC: <code>{device_info.get('mac')}</code>\n"
            f"IP: <code>{device_info.get('ip')}</code>\n"
            f"Vendor: {device_info.get('vendor') or 'Unknown'}\n"
            f"First Seen: {device_info.get('first_seen')}\n"
            f"Open Ports: {device_info.get('open_ports', 'No ports scanned')}"
        )
        await self.send_message(message)

    async def notify_device_approved(self, device_info: dict) -> None:
        """
        Send notification when a device is approved and added to known devices.
        
        Args:
            device_info: Dictionary containing device information
        """
        message = (
            f"✅ <b>Device Added to Known Devices</b>\n\n"
            f"Name: {device_info.get('device_name') or 'Unknown'}\n"
            f"MAC: <code>{device_info.get('mac_address')}</code>\n"
            f"IP: <code>{device_info.get('last_ip')}</code>\n"
            f"Type: {device_info.get('device_type') or 'Unknown'}\n"
            f"Added: {device_info.get('last_seen')}\n"
            f"Notes: {device_info.get('notes') or 'No notes'}"
        )
        await self.send_message(message)

    async def notify_device_blocked(self, device_info: dict) -> None:
        """
        Send notification when a device is marked as unknown/threat.
        
        Args:
            device_info: Dictionary containing device information
        """
        threat_emoji = {
            'low': '⚠️',
            'medium': '🚨',
            'high': '🔥'
        }.get(device_info.get('threat_level', '').lower(), '⚠️')
        
        message = (
            f"{threat_emoji} <b>Device Marked as Security Threat</b>\n\n"
            f"MAC: <code>{device_info.get('mac_address')}</code>\n"
            f"IP: <code>{device_info.get('last_ip')}</code>\n"
            f"Threat Level: {device_info.get('threat_level', 'medium').upper()}\n"
            f"First Seen: {device_info.get('first_seen')}\n"
            f"Last Seen: {device_info.get('last_seen')}\n"
            f"Notes: {device_info.get('notes') or 'No notes provided'}"
        )
        await self.send_message(message)

    async def notify_unknown_device(self, mac: str, ip: str, threat_level: str) -> None:
        """
        Send notification about unknown device detection.
        
        Args:
            mac: MAC address of the device
            ip: IP address of the device
            threat_level: Assessed threat level (low/medium/high)
        """
        threat_emoji = {
            'low': '⚠️',
            'medium': '🚨',
            'high': '🔥'
        }.get(threat_level.lower(), '⚠️')
        
        message = (
            f"{threat_emoji} <b>Unknown Device Alert</b>\n\n"
            f"Threat Level: {threat_level.upper()}\n"
            f"MAC: <code>{mac}</code>\n"
            f"IP: <code>{ip}</code>"
        )
        await self.send_message(message)

    async def notify_system_alert(self, alert_type: str, message: str) -> None:
        """
        Send system-related notifications.
        
        Args:
            alert_type: Type of the alert (e.g., 'CPU', 'Memory', 'Disk')
            message: Alert message
        """
        alert_message = (
            f"⚡ <b>System Alert: {alert_type}</b>\n\n"
            f"{message}"
        )
        await self.send_message(alert_message)
