from netguard.alerts.daemon import AlertDaemon
from netguard.logging.logger import setup_logging
import signal
import sys

logger = setup_logging('netureon')

def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    logger.info("Starting Netureon Alert Daemon...")
    try:
        daemon = AlertDaemon()
        daemon.run()
    except Exception as e:
        logger.error(f"Fatal error in alert daemon: {str(e)}")
        sys.exit(1)