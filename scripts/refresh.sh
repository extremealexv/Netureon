#!/bin/bash

# Color definitions
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 Refreshing Netureon from Git...${NC}"

# Application directory
APP_DIR="/home/orangepi/Netureon"

# Change to application directory
cd "$APP_DIR" || {
    echo -e "${YELLOW}❌ Could not change to $APP_DIR${NC}"
    exit 1
}

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull

# Activate virtual environment
source .venv/bin/activate || {
    echo -e "${YELLOW}❌ Could not activate virtual environment${NC}"
    exit 1
}

# Update dependencies
echo "📦 Updating dependencies..."
pip install -r requirements.txt

# Check if database migrations are needed
if [ -f "schema_update.sql" ]; then
    echo "🗃️ Applying database updates..."
    source .env
    PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f schema_update.sql
fi

# Restart services
echo "🔄 Restarting services..."
sudo systemctl restart netureon
sudo systemctl restart netureon-alerts
sudo systemctl restart netureon_web
sudo systemctl restart netureon_scan.timer

# Check service status
echo -e "\n📊 Service Status:"
services=("netureon" "netureon-alerts" "netureon_web" "netureon_scan.timer")
for service in "${services[@]}"; do
    status=$(systemctl is-active "$service")
    if [ "$status" = "active" ]; then
        echo -e "${GREEN}✅ $service: Active${NC}"
    else
        echo -e "${YELLOW}⚠️ $service: $status${NC}"
    fi
done

echo -e "\n✨ Refresh complete!"
echo "To view logs:"
echo "journalctl -u netureon -f"
echo "journalctl -u netureon-alerts -f"
echo "journalctl -u netureon_web -f"
