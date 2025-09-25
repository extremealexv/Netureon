#!/usr/bin/env python3
"""
Reconfigure logging levels for running Netureon services.
This script updates the logging level for all running components.
"""

import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netureon.config.logging_config import get_logging_level_from_db, reconfigure_existing_loggers

def restart_systemd_services():
    """Restart systemd services to apply new logging configuration."""
    services = [
        'netureon.service',
        'netureon_web.service', 
        'netureon-alerts.service'
    ]
    
    restarted_services = []
    
    for service in services:
        try:
            # Check if service is active first
            result = os.system(f'systemctl is-active --quiet {service}')
            if result == 0:  # Service is active
                print(f"Restarting {service}...")
                restart_result = os.system(f'sudo systemctl restart {service}')
                if restart_result == 0:
                    restarted_services.append(service)
                    print(f"✓ Successfully restarted {service}")
                else:
                    print(f"✗ Failed to restart {service}")
            else:
                print(f"- {service} is not running, skipping")
                
        except Exception as e:
            print(f"✗ Error restarting {service}: {e}")
    
    return restarted_services

def main():
    """Main function to reconfigure logging for all Netureon components."""
    print("Netureon Logging Reconfiguration Tool")
    print("=====================================")
    
    # Get current logging level from database
    try:
        db_level = get_logging_level_from_db()
        level_name = logging.getLevelName(db_level)
        print(f"Current database logging level: {level_name}")
    except Exception as e:
        print(f"Error reading logging level from database: {e}")
        return 1
    
    # Reconfigure current process loggers
    try:
        if reconfigure_existing_loggers():
            print("✓ Reconfigured loggers in current process")
        else:
            print("✗ Failed to reconfigure loggers in current process")
    except Exception as e:
        print(f"✗ Error reconfiguring current process loggers: {e}")
    
    # Restart systemd services to apply new logging configuration
    print("\nRestarting Netureon services to apply new logging level...")
    
    try:
        restarted_services = restart_systemd_services()
        
        if restarted_services:
            print(f"✓ Successfully restarted {len(restarted_services)} services: {', '.join(restarted_services)}")
        else:
            print("! No services were restarted")
            
    except Exception as e:
        print(f"✗ Error restarting services: {e}")
        print("  You may need to manually restart the services:")
        print("    sudo systemctl restart netureon.service")
        print("    sudo systemctl restart netureon_web.service") 
        print("    sudo systemctl restart netureon-alerts.service")
    
    print(f"\nLogging level update complete: {level_name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())