"""Utility functions for managing systemd services."""
import subprocess
import logging

logger = logging.getLogger(__name__)

def update_scan_timer(interval_seconds):
    """Update the netguard_scan timer interval.
    
    Args:
        interval_seconds (int): The new interval in seconds
    """
    try:
        import os
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'update_timer.sh')
        
        # Run the update script using sudo
        subprocess.run(['sudo', script_path, str(interval_seconds)], check=True)
        
        logger.info(f"Successfully updated scan interval to {interval_seconds} seconds")
    except Exception as e:
        logger.error(f"Failed to update scan timer: {e}")
        raise
