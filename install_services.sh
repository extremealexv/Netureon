#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colorized status messages
status() {
    echo -e "${GREEN}$1${NC}"
}

error() {
    echo -e "${RED}Error: $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}Warning: $1${NC}"
}

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then 
    error "Please run as root"
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Get current user (the one who sudo'ed)
REAL_USER=$(who am i | awk '{print $1}')
if [ -z "$REAL_USER" ]; then
    REAL_USER=${SUDO_USER:-${USER}}
fi

# Create config directory if it doesn't exist
mkdir -p /etc/netguard

# Create environment file for service configuration
cat > /etc/netguard/netguard.conf << EOL
# NetGuard Service Configuration
NETGUARD_USER=${REAL_USER}
NETGUARD_HOME=${SCRIPT_DIR}
NETGUARD_SCAN_INTERVAL=900  # Scan interval in seconds (default: 15 minutes)
NETGUARD_MAX_MEMORY=512M    # Maximum memory for scan service
NETGUARD_CPU_QUOTA=50%      # CPU quota for scan service
EOL

# Source the configuration
source /etc/netguard/netguard.conf

# Setup Python environment
status "Setting up Python environment..."
sudo -u "$NETGUARD_USER" python3 "$SCRIPT_DIR/setup.py" || error "Failed to setup Python environment"

# Function to install and configure a service
install_service() {
    local service=$1
    local description=$2
    
    status "Installing $description..."
    
    # Replace variables in service file
    sed "s|%i|$NETGUARD_USER|g; s|%h/NetGuard|$NETGUARD_HOME|g" \
        "$SCRIPT_DIR/$service" > "/etc/systemd/system/$service" || \
        error "Failed to install $service"
        
    # Set correct permissions
    chmod 644 "/etc/systemd/system/$service" || \
        error "Failed to set permissions for $service"
}

# Install systemd services
install_service "alert_daemon.service" "Alert Daemon"
install_service "netguard_web.service" "Web Interface"
install_service "netguard_scan.service" "Network Scanner"
install_service "netguard_scan.timer" "Network Scanner Timer"

# Update timer configuration with custom interval if specified
if [ -n "$NETGUARD_SCAN_INTERVAL" ]; then
    sed -i "s|OnUnitActiveSec=.*|OnUnitActiveSec=${NETGUARD_SCAN_INTERVAL}s|" \
        /etc/systemd/system/netguard_scan.timer
fi

# Reload systemd
status "Reloading systemd configuration..."
systemctl daemon-reload || error "Failed to reload systemd configuration"

# Function to enable and start a service
start_service() {
    local service=$1
    status "Enabling and starting $service..."
    systemctl enable "$service" || warning "Failed to enable $service"
    systemctl restart "$service" || warning "Failed to start $service"
}

# Enable and start services
start_service "alert_daemon.service"
start_service "netguard_web.service"
start_service "netguard_scan.service"
start_service "netguard_scan.timer"

# Print status information
status "Installation complete! Services are now running."
echo
echo "Service Status Commands:"
echo "  systemctl status alert_daemon.service"
echo "  systemctl status netguard_web.service"
echo "  systemctl status netguard_scan.service"
echo "  systemctl status netguard_scan.timer"
echo
echo "View Logs:"
echo "  journalctl -u alert_daemon.service -f"
echo "  journalctl -u netguard_web.service -f"
echo "  journalctl -u netguard_scan.service -f"
echo
echo "Configuration:"
echo "  Service settings can be modified in /etc/netguard/netguard.conf"
echo "  After changing settings, run 'sudo systemctl daemon-reload' and restart affected services"
