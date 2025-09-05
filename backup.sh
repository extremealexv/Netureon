#!/bin/bash

# Backup script for NetGuard
# This script creates backups of the database and configuration

# Get the current date
DATE=$(date +%Y%m%d)

# Set backup directory
BACKUP_DIR="/var/backups/netguard"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Source environment variables
source .env

# Backup database
echo "📦 Creating database backup..."
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > "$BACKUP_DIR/netguard_db_$DATE.sql"

# Backup configuration
echo "📝 Backing up configuration..."
cp .env "$BACKUP_DIR/env_$DATE.backup"

# Cleanup old backups (keep last 30 days)
echo "🧹 Cleaning up old backups..."
find "$BACKUP_DIR" -name "netguard_db_*.sql" -mtime +30 -delete
find "$BACKUP_DIR" -name "env_*.backup" -mtime +30 -delete

echo "✅ Backup completed successfully!"
echo "Backup location: $BACKUP_DIR"
