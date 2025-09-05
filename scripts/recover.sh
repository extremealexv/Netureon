#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print status messages
status() {
    echo -e "${CYAN}ℹ️ $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then 
    error "Please run as root"
fi

# Configuration
BACKUP_DIR="/home/orangepi/NetGuard_backup_20250905"
NEW_DIR="/home/orangepi/Netureon"
USER="orangepi"

# Print plan
echo -e "${CYAN}🔄 Netureon Recovery Plan${NC}"
echo "=============================="
echo "This script will:"
echo "1. Clone new repository"
echo "2. Restore configuration"
echo "3. Install new services"
echo "4. Start services"
echo

# Confirm before proceeding
read -p "Do you want to proceed? (y/N) " confirm
if [[ ! $confirm =~ ^[yY]$ ]]; then
    status "Recovery cancelled"
    exit 0
fi

# Clone new repository
status "Cloning new repository..."
cd "/home/$USER"
su - "$USER" -c "git clone https://github.com/extremealexv/Netureon.git"

# Restore configuration
if [ -f "$BACKUP_DIR/.env" ]; then
    status "Restoring configuration..."
    cp "$BACKUP_DIR/.env" "$NEW_DIR/.env"
    success "Configuration restored"
fi

# Install new services
status "Installing service files..."

# Map of service files
declare -A service_files=(
    ["netureon.service"]="main service"
    ["netureon-alerts.service"]="alert daemon"
    ["netureon_web.service"]="web interface"
    ["netureon_scan.service"]="network scanner"
    ["netureon_scan.timer"]="scanner timer"
)

for service_file in "${!service_files[@]}"; do
    if [ -f "$NEW_DIR/$service_file" ]; then
        # Replace placeholders in service file
        sed "s|%i|$USER|g; s|%h|/home/$USER|g" \
            "$NEW_DIR/$service_file" > "/etc/systemd/system/$service_file"
        chmod 644 "/etc/systemd/system/$service_file"
        success "Installed $service_file (${service_files[$service_file]})"
    else
        warning "Service file $service_file not found"
    fi
done

# Setup new installation
status "Setting up new installation..."
cd "$NEW_DIR"
chmod +x setup.sh
su - "$USER" -c "cd $NEW_DIR && ./setup.sh"

# Reload systemd and start services
status "Reloading systemd and starting services..."
systemctl daemon-reload

services=(
    "netureon"
    "netureon-alerts"
    "netureon_web"
    "netureon_scan"
    "netureon_scan.timer"
)

for service in "${services[@]}"; do
    systemctl enable "$service"
    systemctl start "$service"
    if systemctl is-active --quiet "$service"; then
        success "$service started"
    else
        warning "Failed to start $service"
    fi
done

echo
success "Recovery completed!"
echo
echo "To verify the installation:"
echo "1. Check service status: systemctl status netureon"
echo "2. Check logs: journalctl -u netureon -f"
echo "3. Access web interface and verify functionality"
