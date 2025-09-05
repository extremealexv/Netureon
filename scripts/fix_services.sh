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
# Create/update virtual environment
echo "Setting up Python environment..."
cd "$INSTALL_PATH" || exit 1

# Remove existing venv if it's broken
if [ -d ".venv" ]; then
    echo "Removing existing virtual environment..."
    sudo -u "$REAL_USER" rm -rf .venv
fi

# Ensure python3-venv is installed
if ! dpkg -l | grep -q python3-venv; then
    echo "Installing python3-venv..."
    apt-get update && apt-get install -y python3-venv
fi

# Create fresh virtual environment
echo "Creating virtual environment..."
sudo -u "$REAL_USER" python3 -m venv .venv
if [ ! -f ".venv/bin/python" ]; then
    echo "❌ Failed to create virtual environment"
    exit 1
fi

# Function to run pip commands as the real user with full path
pip_install() {
    sudo -u "$REAL_USER" bash -c "
        export PATH=\"$INSTALL_PATH/.venv/bin:\$PATH\"
        export VIRTUAL_ENV=\"$INSTALL_PATH/.venv\"
        export PYTHONPATH=\"$INSTALL_PATH\"
        $INSTALL_PATH/.venv/bin/pip $*
    "
}

# Install/upgrade packages
echo "Installing required packages..."
pip_install install --upgrade pip
pip_install install --upgrade setuptools wheel
pip_install install --upgrade "psycopg2-binary python-dotenv flask requests psutil netifaces"
pip_install install -r requirements.txt

# Verify installation
echo "Verifying Python packages..."
if ! sudo -u "$REAL_USER" bash -c "
    export PATH=\"$INSTALL_PATH/.venv/bin:\$PATH\"
    export VIRTUAL_ENV=\"$INSTALL_PATH/.venv\"
    export PYTHONPATH=\"$INSTALL_PATH\"
    $INSTALL_PATH/.venv/bin/python -c 'import psycopg2, dotenv'
"; then
    echo "❌ Failed to verify package installation"
    exit 1
fi

# Verify critical packages
echo "Verifying installation..."
if ! sudo -u "$REAL_USER" .venv/bin/python -c "import psycopg2, dotenv" 2>/dev/null; then
    echo "❌ Failed to install required packages. Please check pip output above."
    exit 1
fi

# Copy environment file if it doesn't exist
if [ ! -f "$INSTALL_PATH/.env" ] && [ -f "$INSTALL_PATH/.env.example" ]; then
    echo "Creating .env file from example..."
    sudo -u "$REAL_USER" cp "$INSTALL_PATH/.env.example" "$INSTALL_PATH/.env"
    echo "⚠️ Please edit $INSTALL_PATH/.env to set your configuration"
fi

# Fix permissions on service files
chmod 644 /etc/systemd/system/netureon*.service
chmod 644 /etc/systemd/system/netureon*.timer

# Fix service file paths and user
for service in /etc/systemd/system/netureon*.service; do
    # Replace %h and %i with actual values
    sed -i "s|User=%i|User=$REAL_USER|g" "$service"
    sed -i "s|%h/Netureon|$INSTALL_PATH|g" "$service"
    sed -i "s|/home/[^/]*/NetGuard|$INSTALL_PATH|g" "$service"
    # Update venv to .venv
    sed -i "s|/venv/|/.venv/|g" "$service"
    # Fix any remaining root paths
    sed -i "s|/root/Netureon|$INSTALL_PATH|g" "$service"
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
