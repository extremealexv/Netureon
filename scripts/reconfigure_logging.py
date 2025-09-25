#!/usr/bin/env python3
"""
Reconfigure logging levels for running Netureon services.
This script updates the logging level for all running components.
"""

import sys
import os
import signal
import psutil
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netureon.config.logging_config import get_logging_level_from_db, reconfigure_existing_loggers

def send_signal_to_processes(process_names, signal_num):
    """Send a signal to processes by name."""
    updated_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if any of the target process names are in the command line
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            
            for process_name in process_names:
                if process_name in cmdline:
                    proc.send_signal(signal_num)
                    updated_processes.append((proc.info['pid'], cmdline))
                    print(f"Sent signal {signal_num} to PID {proc.info['pid']}: {cmdline}")
                    break
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    return updated_processes

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
    
    # Try to signal running Netureon processes to reload their logging configuration
    # Note: This requires implementing signal handlers in the actual services
    process_names = [
        'net_scan.py',
        'webui/app.py',
        'alert_daemon.py'
    ]
    
    print("\nLooking for running Netureon processes...")
    
    # Send SIGUSR1 (user-defined signal) to tell processes to reload logging config
    # This would require the processes to implement the signal handler
    try:
        updated_processes = send_signal_to_processes(process_names, signal.SIGUSR1)
        
        if updated_processes:
            print(f"✓ Sent logging reload signal to {len(updated_processes)} processes")
        else:
            print("! No running Netureon processes found")
            print("  Services may need to be restarted to apply new logging level")
            
    except Exception as e:
        print(f"✗ Error signaling processes: {e}")
        print("  Services may need to be restarted to apply new logging level")
    
    print(f"\nLogging level update complete: {level_name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())