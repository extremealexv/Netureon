#!/bin/bash

# This script updates the NetGuard scan timer
# It should be called with the interval in seconds as the first argument

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <interval_seconds>"
    exit 1
fi

INTERVAL=$1

# Create timer unit file
cat > /etc/systemd/system/netguard_scan.timer << EOL
[Unit]
Description=NetGuard Network Scanner Timer

[Timer]
OnBootSec=60
OnUnitActiveSec=${INTERVAL}s
AccuracySec=1s

[Install]
WantedBy=timers.target
EOL

# Set correct permissions
chmod 644 /etc/systemd/system/netguard_scan.timer

# Reload systemd and restart timer
systemctl daemon-reload
systemctl restart netguard_scan.timer

echo "Timer updated successfully"
