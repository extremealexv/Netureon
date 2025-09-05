#!/bin/bash

# Ensure we're running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get the actual user who invoked sudo
if [ -z "$SUDO_USER" ]; then
    echo "This script must be run with sudo"
    exit 1
fi

REAL_USER="$SUDO_USER"
USER_HOME=$(eval echo ~"$REAL_USER")
INSTALL_PATH="$USER_HOME/Netureon"

echo "Installing for user: $REAL_USER"
echo "Installation path: $INSTALL_PATH"

# Verify the installation path exists
if [ ! -d "$INSTALL_PATH" ]; then
    echo "❌ Installation directory $INSTALL_PATH does not exist"
    exit 1
fi

# Change to installation directory
cd "$INSTALL_PATH" || exit 1

# Install/upgrade packages
echo "Installing required packages..."
# First upgrade pip
sudo -u "$REAL_USER" bash -c "
    source .venv/bin/activate
    pip install --upgrade pip
"

# Install required packages
sudo -u "$REAL_USER" bash -c "
    source .venv/bin/activate
    pip install --upgrade setuptools wheel
    pip install --upgrade psycopg2-binary python-dotenv flask requests psutil netifaces
    pip install -r requirements.txt
"ER=${SUDO_USER:-$USER}
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

# Fix virtual environment permissions and recreate
if [ -d ".venv" ]; then
    echo "Cleaning up existing virtual environment..."
    # Change ownership to root temporarily to remove
    chown -R root:root .venv
    rm -rf .venv
fi

# Ensure python3-venv is installed
if ! dpkg -l | grep -q python3-venv; then
    echo "Installing python3-venv..."
    apt-get update && apt-get install -y python3-venv
fi

# Create fresh virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv
if [ ! -f ".venv/bin/python" ]; then
    echo "❌ Failed to create virtual environment"
    exit 1
fi

# Fix permissions on the new virtual environment
chown -R "$REAL_USER:$REAL_USER" .venv

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
