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
    """Main entry point for Netureon CLI."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Version check
    check_version()
    
    # Display startup message
    print(f"🛡️ Netureon {__version__}")
    print("✨ Network monitoring and security management system")
    print("\nThis is the CLI entry point. For network monitoring, use:")
    print("sudo systemctl start netureon.service")

if __name__ == "__main__":
    main()
