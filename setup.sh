#!/bin/bash

echo "🚀 Starting NetGuard setup..."

# Check Python installation
echo "🐍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$PYTHON_VERSION < 3.8" | bc -l) )); then
    echo "❌ Python 3.8 or higher is required. Found version $PYTHON_VERSION"
    exit 1
fi
echo "✅ Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv || {
        echo "❌ Failed to create virtual environment"
        exit 1
    }
else
    echo "✅ Virtual environment exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate || {
    echo "❌ Failed to activate virtual environment"
    exit 1
}

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt || {
    echo "❌ Failed to install dependencies"
    exit 1
}

# Database configuration
echo "🗄️ Database configuration..."

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Please enter PostgreSQL database credentials:"
    read -p "Database name (default: netguard): " db_name
    db_name=${db_name:-netguard}
    read -p "Database user: " db_user
    read -s -p "Database password: " db_password
    echo
    read -p "Database host (default: localhost): " db_host
    db_host=${db_host:-localhost}
    read -p "Database port (default: 5432): " db_port
    db_port=${db_port:-5432}
    
    # Email configuration
    echo -e "\n� Email notification configuration:"
    read -p "SMTP Server: " smtp_server
    read -p "SMTP Port (default: 587): " smtp_port
    smtp_port=${smtp_port:-587}
    read -p "SMTP User: " smtp_user
    read -s -p "SMTP Password: " smtp_password
    echo
    read -p "From Email: " email_from
    read -p "To Email: " email_to
    
    echo "Creating .env file..."
    cat > .env << EOL
# Database Configuration
DB_NAME=${db_name}
DB_USER=${db_user}
DB_PASSWORD=${db_password}
DB_HOST=${db_host}
DB_PORT=${db_port}

# Email Configuration
SMTP_SERVER=${smtp_server}
SMTP_PORT=${smtp_port}
SMTP_USER=${smtp_user}
SMTP_PASSWORD=${smtp_password}
EMAIL_FROM=${email_from}
EMAIL_TO=${email_to}

# Flask Configuration
FLASK_SECRET_KEY=$(openssl rand -hex 32)
EOL
else
    echo "✅ .env file exists"
fi

# Source the .env file
set -a
source .env
set +a

# Test database connection and create schema
echo "🔄 Testing database connection..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\q' 2>/dev/null || {
    echo "📝 Creating database..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME" || {
        echo "❌ Failed to create database"
        exit 1
    }
}

echo "📝 Creating database schema..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f schema.sql || {
    echo "❌ Failed to create schema"
    exit 1
}

# Create systemd services
echo "🔧 Creating systemd services..."
sudo tee /etc/systemd/system/netguard.service > /dev/null << EOL
[Unit]
Description=NetGuard Network Monitor
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin:$PATH
ExecStart=$(pwd)/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOL

sudo tee /etc/systemd/system/netguard-alerts.service > /dev/null << EOL
[Unit]
Description=NetGuard Alert Daemon
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin:$PATH
ExecStart=$(pwd)/venv/bin/python alert_daemon.py
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd and enable services
echo "🔄 Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable netguard.service
sudo systemctl enable netguard-alerts.service

# Test email configuration
echo "📧 Testing email configuration..."
python3 << EOL
import smtplib
from email.message import EmailMessage

try:
    msg = EmailMessage()
    msg.set_content("This is a test email from NetGuard setup.")
    msg["Subject"] = "NetGuard Setup Test"
    msg["From"] = "$EMAIL_FROM"
    msg["To"] = "$EMAIL_TO"

    with smtplib.SMTP("$SMTP_SERVER", $SMTP_PORT) as server:
        server.starttls()
        server.login("$SMTP_USER", "$SMTP_PASSWORD")
        server.send_message(msg)
    print("✅ Email test successful")
except Exception as e:
    print(f"❌ Email test failed: {str(e)}")
EOL

echo -e "\n✨ Setup complete! Services have been created and enabled."
echo "👉 To start the services, run:"
echo "   sudo systemctl start netguard"
echo "   sudo systemctl start netguard-alerts"
echo "👉 To view logs, run:"
echo "   sudo journalctl -u netguard -f"
echo "   sudo journalctl -u netguard-alerts -f"
