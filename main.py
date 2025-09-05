# main.py

"""
Netureon: Main entry point for network security tools.
Version 1.3.1
"""

import logging
import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from version import __version__, VERSION_INFO

def check_version():
    """Check Python version compatibility."""
    if sys.version_info < (3, 8):
        logging.error("Python 3.8 or higher is required")
        sys.exit(1)
    logging.info(f"Netureon version {__version__}")
    return True

def main():
    """Main entry point for Netureon."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Version check
    check_version()
    
    # Display startup message
    print(f"🛡️ Netureon {__version__} is running")
    print("✨ Network monitoring and security management system")
    
    try:
        # Import scanner after logging is configured
        from net_scan import NetworkScanner
        scanner = NetworkScanner()
        scanner.start_monitoring()
    except KeyboardInterrupt:
        logging.info("Shutting down Netureon...")
    except Exception as e:
        logging.error(f"Error in main loop: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
