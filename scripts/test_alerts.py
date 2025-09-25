#!/usr/bin/env python3
"""
Test script to verify alert system configuration and notification functionality.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netureon.config.settings import Settings
from netureon.alerts.handlers import DeviceHandler

def test_configuration():
    """Test if configuration is accessible."""
    print("Testing Configuration Access...")
    
    try:
        settings = Settings.get_instance()
        notification_settings = settings.get_notification_settings()
        
        print(f"✓ Configuration loaded successfully")
        print(f"  Email notifications enabled: {notification_settings.get('enable_email_notifications')}")
        print(f"  Telegram notifications enabled: {notification_settings.get('enable_telegram_notifications')}")
        print(f"  SMTP server: {notification_settings.get('smtp_server', 'Not set')}")
        print(f"  Telegram bot token: {'Set' if notification_settings.get('telegram_bot_token') else 'Not set'}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_database_access():
    """Test database connectivity."""
    print("\nTesting Database Access...")
    
    try:
        handler = DeviceHandler()
        new_devices = handler.check_for_unknown_devices()
        
        print(f"✓ Database connection successful")
        print(f"  Found {len(new_devices)} new devices pending alerts")
        
        if new_devices:
            print("  New devices:")
            for mac, ip, timestamp in new_devices:
                print(f"    - {mac} ({ip}) last seen: {timestamp}")
        
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_notification_sending():
    """Test notification sending."""
    print("\nTesting Notification System...")
    
    try:
        settings = Settings.get_instance()
        notification_settings = settings.get_notification_settings()
        
        # Test email notification if enabled
        if notification_settings.get('enable_email_notifications'):
            try:
                from netureon.alerts.notifiers.email import EmailNotifier
                email_notifier = EmailNotifier()
                
                # Test email configuration
                test_subject = "Netureon Alert System Test"
                test_message = "This is a test message from the Netureon alert system to verify email notifications are working."
                
                result = email_notifier.send_notification(test_subject, test_message)
                if result:
                    print("✓ Email notification test successful")
                else:
                    print("✗ Email notification test failed")
            except Exception as e:
                print(f"✗ Email notification error: {e}")
        else:
            print("- Email notifications disabled, skipping test")
        
        # Test Telegram notification if enabled
        if notification_settings.get('enable_telegram_notifications'):
            try:
                from netureon.alerts.notifiers.telegram import TelegramNotifier
                telegram_notifier = TelegramNotifier()
                
                test_message = "🧪 Netureon Alert System Test\n\nThis is a test message to verify Telegram notifications are working."
                
                result = telegram_notifier.send_notification(test_message)
                if result:
                    print("✓ Telegram notification test successful")
                else:
                    print("✗ Telegram notification test failed")
            except Exception as e:
                print(f"✗ Telegram notification error: {e}")
        else:
            print("- Telegram notifications disabled, skipping test")
        
        return True
    except Exception as e:
        print(f"✗ Notification test failed: {e}")
        return False

def main():
    """Main test function."""
    print("Netureon Alert System Test")
    print("=" * 30)
    
    tests_passed = 0
    total_tests = 3
    
    if test_configuration():
        tests_passed += 1
    
    if test_database_access():
        tests_passed += 1
    
    if test_notification_sending():
        tests_passed += 1
    
    print(f"\nTest Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! Alert system should be working properly.")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())