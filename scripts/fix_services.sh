#!/bin/bash

# Get the actual user's home directory
REAL_USER=${SUDO_USER:-$USER}
USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
INSTALL_PATH="$USER_HOME/Netureon"

echo "Installing for user: $REAL_USER"
echo "Installation path: $INSTALL_PATH"

# Stop all services first
systemctl stop netureon.service netureon-alerts.service netureon_web.service netureon_scan.service netureon_scan.timer

# Fix virtual environment if needed
if [ ! -d "$INSTALL_PATH/.venv" ]; then
    echo "Creating virtual environment..."
    cd "$INSTALL_PATH" || exit 1
    # Create venv as the real user, not as root
    sudo -u "$REAL_USER" python3 -m venv .venv
    sudo -u "$REAL_USER" .venv/bin/pip install -r requirements.txt
fi

# Fix permissions on service files
chmod 644 /etc/systemd/system/netureon*.service
chmod 644 /etc/systemd/system/netureon*.timer

# Fix service file paths if needed
for service in /etc/systemd/system/netureon*.service; do
    # Update any hardcoded paths to use %h
    sed -i "s|/home/orangepi/Netureon|%h/Netureon|g" "$service"
    sed -i "s|/home/orangepi/NetGuard|%h/Netureon|g" "$service"
    # Update venv to .venv
    sed -i "s|/venv/|/.venv/|g" "$service"
done

# Reload systemd to pick up changes
systemctl daemon-reload

# Start services in correct order
systemctl start netureon_scan.timer
systemctl start netureon.service
systemctl start netureon-alerts.service
systemctl start netureon_web.service

# Check status
echo "Service Status:"
for service in netureon.service netureon-alerts.service netureon_web.service netureon_scan.service netureon_scan.timer; do
    echo -e "\n=== $service ==="
    systemctl status "$service" --no-pager
done
