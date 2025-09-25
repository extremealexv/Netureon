#!/usr/bin/env python3
"""
Simple logging level update that creates a flag file for services to check.
This approach doesn't restart services but allows them to check for config changes.
"""

import sys
import os
import time
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netureon.config.logging_config import get_logging_level_from_db

def create_config_update_flag():
    """Create a flag file indicating configuration has been updated."""
    try:
        flag_dir = os.path.expanduser('~/Netureon')
        os.makedirs(flag_dir, exist_ok=True)
        
        flag_file = os.path.join(flag_dir, '.logging_config_updated')
        
        # Write current timestamp and logging level to flag file
        db_level = get_logging_level_from_db()
        level_name = logging.getLevelName(db_level)
        
        with open(flag_file, 'w') as f:
            f.write(f"{time.time()},{level_name}\n")
        
        print(f"✓ Created configuration update flag: {level_name}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create configuration flag: {e}")
        return False

def main():
    """Main function for simple config update notification."""
    print("Netureon Configuration Update Notifier")
    print("====================================")
    
    # Get current logging level from database
    try:
        db_level = get_logging_level_from_db()
        level_name = logging.getLevelName(db_level)
        print(f"Current database logging level: {level_name}")
    except Exception as e:
        print(f"Error reading logging level from database: {e}")
        return 1
    
    # Create flag file for services to check
    if create_config_update_flag():
        print("✓ Services will check for configuration updates on next cycle")
        print("  No service restart required")
    else:
        print("✗ Failed to notify services of configuration change")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())