# main.py

"""
NetGuard: Main entry point for network security tools.
Version 1.2.1
"""

from version import __version__, VERSION_INFO
import logging
import sys

def check_version():
    """Check Python version compatibility."""
    if sys.version_info < (3, 8):
        logging.error("Python 3.8 or higher is required")
        sys.exit(1)
    logging.info(f"NetGuard version {__version__}")
    return True

def main():
    """Main entry point for NetGuard."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Version check
    check_version()
    
    # Display startup message
    print(f"🛡️ NetGuard {__version__} is running")
    print("✨ Network monitoring and security management system")

if __name__ == "__main__":
    main()
