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

# Print header
echo -e "${CYAN}🗑️ NetGuard Uninstallation Script${NC}"
echo -e "${CYAN}============================${NC}"
echo

# Ask for confirmation
echo -e "${YELLOW}⚠️ WARNING: This will remove all NetGuard services and their data${NC}"
echo "The following actions will be performed:"
echo "1. Stop all NetGuard services"
echo "2. Remove systemd services"
echo "3. Remove service configurations"
echo "4. Clean up program data"
echo
read -p "Do you want to proceed? (y/N) " confirm
if [[ ! $confirm =~ ^[yY]$ ]]; then
    status "Uninstallation cancelled"
    exit 0
fi

# Stop services
status "Stopping NetGuard services..."
services=(
    "netguard"
    "netguard-alerts"
    "netguard_web"
    "netguard_scan.timer"
    "netguard_scan"
)

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        systemctl stop "$service" && \
            success "$service service stopped" || \
            warning "Failed to stop $service service"
    fi
done

# Disable services
status "Disabling services..."
for service in "${services[@]}"; do
    if systemctl is-enabled --quiet "$service" 2>/dev/null; then
        systemctl disable "$service" && \
            success "$service service disabled" || \
            warning "Failed to disable $service service"
    fi
done

# Remove service files
status "Removing service files..."
for service in "${services[@]}"; do
    if [ -f "/etc/systemd/system/$service.service" ]; then
        rm "/etc/systemd/system/$service.service" && \
            success "$service.service removed" || \
            warning "Failed to remove $service.service"
    fi
done

# Remove timer if exists
if [ -f "/etc/systemd/system/netguard_scan.timer" ]; then
    rm "/etc/systemd/system/netguard_scan.timer" && \
        success "netguard_scan.timer removed" || \
        warning "Failed to remove netguard_scan.timer"
fi

# Reload systemd
status "Reloading systemd configuration..."
systemctl daemon-reload && \
    success "Systemd configuration reloaded" || \
    warning "Failed to reload systemd configuration"

# Clean up program data
if [ -d "/var/lib/netguard" ]; then
    status "Removing program data..."
    rm -rf "/var/lib/netguard" && \
        success "Program data removed" || \
        warning "Failed to remove program data"
fi

# Clean up configuration
if [ -d "/etc/netguard" ]; then
    status "Removing configuration files..."
    rm -rf "/etc/netguard" && \
        success "Configuration files removed" || \
        warning "Failed to remove configuration files"
fi

# Clean up logs
if [ -d "/var/log/netguard" ]; then
    status "Removing log files..."
    rm -rf "/var/log/netguard" && \
        success "Log files removed" || \
        warning "Failed to remove log files"
fi

echo
success "Uninstallation complete!"
echo "To complete the removal:"
echo "1. Delete the NetGuard directory"
echo "2. Remove the virtual environment if created"
echo "3. Optionally remove the PostgreSQL database"
echo
echo "Database can be removed using:"
echo "psql -h <host> -U <user> -c 'DROP DATABASE netguard;'"

# Remind about remaining files
if [ -f ".env" ]; then
    warning "Local .env file still exists"
fi
