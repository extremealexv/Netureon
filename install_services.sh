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

# Create necessary directories
INSTALL_DIR="/home/${REAL_USER}/Netureon"
VENV_DIR="${INSTALL_DIR}/.venv"
CONFIG_DIR="/etc/netguard"

status "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# Create environment file for service configuration
cat > "${CONFIG_DIR}/netguard.conf" << EOL
# Netureon Service Configuration
NETUREON_USER=${REAL_USER}
NETUREON_HOME=${INSTALL_DIR}
NETUREON_SCAN_INTERVAL=900  # Scan interval in seconds (default: 15 minutes)
NETUREON_MAX_MEMORY=512M    # Maximum memory for scan service
NETUREON_CPU_QUOTA=50%      # CPU quota for scan service
EOL

# Set up Python virtual environment
status "Setting up Python virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Install Python dependencies
status "Installing Python dependencies..."
pip install -r "${SCRIPT_DIR}/requirements.txt"

# Copy files to installation directory
status "Installing Netureon files..."
cp -r "${SCRIPT_DIR}"/* "$INSTALL_DIR/"
chown -R "${REAL_USER}:${REAL_USER}" "$INSTALL_DIR"
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
    sed "s|/home/orangepi/NetGuard|${INSTALL_DIR}|g; s|/home/orangepi/Netureon|${INSTALL_DIR}|g" \
        "${SCRIPT_DIR}/${service}" > "/etc/systemd/system/${service}" || \
        error "Failed to install $service"
        
    # Set correct permissions
    chmod 644 "/etc/systemd/system/${service}" || \
        error "Failed to set permissions for $service"
}

# Install systemd services
install_service "alert_daemon.service" "Alert Daemon"
install_service "netureon_web.service" "Web Interface"
install_service "netureon_scan.service" "Network Scanner"
install_service "netureon_scan.timer" "Network Scanner Timer"

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
start_service "netureon_web.service"
start_service "netureon_scan.timer"

status "✨ Installation complete!"
status "Service status commands:"
echo "  sudo systemctl status alert_daemon.service"
echo "  sudo systemctl status netureon_web.service"
echo "  sudo systemctl status netureon_scan.service"
echo "  sudo systemctl status netureon_scan.timer"

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
