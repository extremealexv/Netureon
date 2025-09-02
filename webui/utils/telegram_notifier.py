"""Telegram notification module for NetGuard."""

import asyncio
import logging
import sys
from telegram import Bot
from telegram.error import TelegramError
from ..config.config import Config

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram notification handler for NetGuard."""
    
    def __init__(self):
        """Initialize the Telegram notifier."""
        self.bot_token = Config.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = Config.get('TELEGRAM_CHAT_ID')
        self.bot = None
        self._loop = None
        
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured")
            return
            
        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not configured")
            return
            
        try:
            self.bot = Bot(token=self.bot_token)
            # Verify the chat_id format
            self.chat_id = str(self.chat_id)
            if not self.chat_id.startswith('-') and not self.chat_id.isdigit():
                logger.error(f"Invalid TELEGRAM_CHAT_ID format: {self.chat_id}")
                self.bot = None
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {str(e)}")
            self.bot = None

    async def send_message(self, message: str) -> bool:
        """
        Send a message through Telegram.
        
        Args:
            message: The message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not self.bot:
            logger.error("Telegram bot not configured. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config.")
            return False
            
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False

    def _ensure_event_loop(self):
        """Ensure there's a running event loop or create a new one."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def notify(self, message: str) -> None:
        """
        Synchronous wrapper for sending messages.
        
        Args:
            message: The message to send
        """
        if not self.bot:
            logger.warning("Telegram bot not configured, skipping notification")
            return
            
        loop = self._ensure_event_loop()
        try:
            loop.run_until_complete(self.send_message(message))
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
        finally:
            try:
                # Clean up any remaining tasks
                pending = asyncio.all_tasks(loop)
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass

    async def notify_new_device(self, device_name: str, mac: str, ip: str) -> None:
        """
        Send notification about new device detection.
        
        Args:
            device_name: Name of the device if available
            mac: MAC address of the device
            ip: IP address of the device
        """
        message = (
            f"🆕 <b>New Device Detected</b>\n\n"
            f"Name: {device_name or 'Unknown'}\n"
            f"MAC: <code>{mac}</code>\n"
            f"IP: <code>{ip}</code>"
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
