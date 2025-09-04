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
        # Create or update the timer unit file
        timer_config = f"""[Unit]
Description=NetGuard Network Scanner Timer

[Timer]
OnBootSec=60
OnUnitActiveSec={interval_seconds}s

[Install]
WantedBy=timers.target
"""
        with open('/etc/systemd/system/netguard_scan.timer', 'w') as f:
            f.write(timer_config)

        # Reload systemd and restart the timer
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        subprocess.run(['sudo', 'systemctl', 'restart', 'netguard_scan.timer'], check=True)
        
        logger.info(f"Successfully updated scan interval to {interval_seconds} seconds")
    except Exception as e:
        logger.error(f"Failed to update scan timer: {e}")
        raise
