#!/bin/bash

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Setup Python environment
echo "Setting up Python environment..."
sudo -u orangepi python3 "$SCRIPT_DIR/setup.py"

# Install systemd services
echo "Installing systemd services..."
cp "$SCRIPT_DIR/alert_daemon.service" /etc/systemd/system/
cp "$SCRIPT_DIR/netguard_web.service" /etc/systemd/system/
cp "$SCRIPT_DIR/netguard_scan.service" /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable and start services
systemctl enable alert_daemon.service
systemctl enable netguard_web.service
systemctl enable netguard_scan.service

systemctl restart alert_daemon.service
systemctl restart netguard_web.service
systemctl restart netguard_scan.service

echo "Installation complete. Services are now running."
echo "You can check their status with:"
echo "  systemctl status alert_daemon.service"
echo "  systemctl status netguard_web.service"
echo "  systemctl status netguard_scan.service"
