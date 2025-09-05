#!/bin/bash

#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to # Install new services
status "Installing service files..."

# Map of old to new service files
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
doneges
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
OLD_DIR="/home/orangepi/NetGuard"
NEW_DIR="/home/orangepi/Netureon"
OLD_DB="netguard"
NEW_DB="netguard"  # Keeping the same database name
USER="orangepi"

# Print migration plan
echo -e "${CYAN}🔄 Netureon Migration Plan${NC}"
echo "=============================="
echo "This script will:"
echo "1. Stop current services"
echo "2. Backup current database"
echo "3. Backup configuration"
echo "4. Remove old services"
echo "5. Clone new repository"
echo "6. Restore configuration"
echo "7. Install new services"
echo "8. Migrate database"
echo "9. Start new services"
echo

# Confirm before proceeding
read -p "Do you want to proceed? (y/N) " confirm
if [[ ! $confirm =~ ^[yY]$ ]]; then
    status "Migration cancelled"
    exit 0
fi

# Stop services
status "Stopping services..."
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
            success "$service stopped" || \
            warning "Failed to stop $service"
    fi
done

# Backup database
status "Backing up database..."
BACKUP_DIR="/var/backups/netureon_migration"
mkdir -p "$BACKUP_DIR"
chown postgres:postgres "$BACKUP_DIR"

# Load database credentials from .env
source "$OLD_DIR/.env"

# Create backup
BACKUP_FILE="$BACKUP_DIR/${OLD_DB}_backup_$(date +%Y%m%d).sql"
if PGPASSWORD="$DB_PASSWORD" su - postgres -c "pg_dump -h $DB_HOST -U $DB_USER $OLD_DB > $BACKUP_FILE"; then
    chown "$USER:$USER" "$BACKUP_FILE"
    success "Database backed up to $BACKUP_FILE"
else
    error "Database backup failed"
fi

# Backup configuration
status "Backing up configuration..."
if [ -f "$OLD_DIR/.env" ]; then
    cp "$OLD_DIR/.env" "$BACKUP_DIR/.env.backup"
    success "Configuration backed up"
fi

# Remove old services
status "Removing old services..."
for service in "${services[@]}"; do
    if [ -f "/etc/systemd/system/$service.service" ]; then
        systemctl disable "$service"
        rm "/etc/systemd/system/$service.service"
        success "Removed $service"
    fi
done

# Clone new repository
status "Cloning new repository..."
cd "/home/$USER"
mv "$OLD_DIR" "${OLD_DIR}_backup_$(date +%Y%m%d)"
su - "$USER" -c "git clone https://github.com/extremealexv/Netureon.git"

# Restore configuration
if [ -f "$BACKUP_DIR/.env.backup" ]; then
    status "Restoring configuration..."
    cp "$BACKUP_DIR/.env.backup" "$NEW_DIR/.env"
    success "Configuration restored"
    
    # Update database name in config
    sed -i "s/DB_NAME=$OLD_DB/DB_NAME=$NEW_DB/" "$NEW_DIR/.env"
fi

# Since we're keeping the same database, we just need to verify connection
status "Verifying database connection..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$OLD_DB" -c "SELECT 1" > /dev/null 2>&1; then
    success "Database connection verified"
else
    error "Database connection failed"
fi

# Setup new installation
status "Setting up new installation..."
cd "$NEW_DIR"
chmod +x setup.sh
su - "$USER" -c "cd $NEW_DIR && ./setup.sh"

# Start new services
status "Starting services..."
systemctl daemon-reload
services=(
    "netureon"
    "netureon-alerts"
    "netureon_web"
    "netureon_scan.timer"
    "netureon_scan"
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
success "Migration completed!"
echo
echo "The old installation has been backed up to ${OLD_DIR}_backup_$(date +%Y%m%d)"
echo "The old database has been backed up to $BACKUP_DIR/${OLD_DB}_backup_$(date +%Y%m%d).sql"
echo
echo "To verify the installation:"
echo "1. Check service status: systemctl status netureon"
echo "2. Check logs: journalctl -u netureon -f"
echo "3. Access web interface and verify functionality"
echo
echo "If everything is working correctly, you can remove the old backup with:"
echo "rm -rf ${OLD_DIR}_backup_$(date +%Y%m%d)"
echo "dropdb $OLD_DB  # This will remove the old database"
