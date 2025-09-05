#!/bin/bash

# Health check script for NetGuard services
# This script checks the status of all NetGuard components

check_service() {
    local service=$1
    echo -n "Checking $service... "
    if systemctl is-active --quiet "$service"; then
        echo "✅ Running"
        return 0
    else
        echo "❌ Not running"
        return 1
    fi
}

check_web_interface() {
    local host=${FLASK_HOST:-0.0.0.0}
    local port=${FLASK_PORT:-5000}
    echo -n "Checking web interface... "
    if curl -s "http://$host:$port/system" > /dev/null; then
        echo "✅ Accessible"
        return 0
    else
        echo "❌ Not accessible"
        return 1
    fi
}

check_database() {
    echo -n "Checking database connection... "
    if PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
        echo "✅ Connected"
        return 0
    else
        echo "❌ Connection failed"
        return 1
    fi
}

# Source environment variables
source .env

# Print header
echo "🛡️ NetGuard Health Check"
echo "======================="
echo

# Check services
check_service "netguard_web"
check_service "alert_daemon"
check_service "netguard_scan.timer"

# Check components
check_database
check_web_interface

# Check disk space
echo -n "Checking disk space... "
SPACE=$(df -h /opt/netguard | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$SPACE" -lt 90 ]; then
    echo "✅ OK ($SPACE% used)"
else
    echo "⚠️ Warning: $SPACE% used"
fi

# Check log files
echo -n "Checking log files... "
LOG_SIZE=$(du -sh /var/log/netguard 2>/dev/null | cut -f1)
if [ $? -eq 0 ]; then
    echo "✅ Size: $LOG_SIZE"
else
    echo "⚠️ Cannot access log files"
fi
