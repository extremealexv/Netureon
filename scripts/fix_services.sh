#!/bin/bash

# Stop all services first
systemctl stop netureon.service netureon-alerts.service netureon_web.service netureon_scan.service netureon_scan.timer

# Fix virtual environment if needed
if [ ! -d "$HOME/Netureon/.venv" ]; then
    echo "Creating virtual environment..."
    cd "$HOME/Netureon"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
fi

# Fix permissions
chmod 644 /etc/systemd/system/netureon*.service
chmod 644 /etc/systemd/system/netureon*.timer

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
