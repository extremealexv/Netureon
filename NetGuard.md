# 📘 NetGuard Project Summary
**Version:** 1.0  
**Last Updated:** August 3, 2025  
**Author:** Alexander Vasilyev

---

## 🛠️ Purpose
NetGuard is a comprehensive local network monitoring and management system built with Flask and PostgreSQL. It provides real-time device detection, automated profiling, and alert notifications for network administrators. The system helps maintain network security by tracking known devices and promptly alerting about new connections.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- PostgreSQL 13 or higher
- Git (for installation)
- Linux/Unix for systemd services (optional)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/extremealexv/NetGuard.git
   cd NetGuard
   ```

2. Set up the environment:
   - Windows: `.\setup.ps1`
   - Linux/Unix: `./setup.sh`

3. Configure database:
   ```bash
   psql -U postgres -f schema.sql
   ```

4. Update `.env` with your credentials:
   ```
   DB_NAME=netguard
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   ```

5. Start the services:
   - Development: `python webui/app.py`
   - Production: Enable systemd services (see Services section)

---

## 🗂️ Core Components

### ✅ Web Interface (`webui/app.py`)
- **Dashboard Features:**
  - Real-time device status monitoring
  - Device review and classification
  - Historical connection logs
  - Alert management interface

- **Routes:**
  - `/` - Main dashboard with known devices
  - `/review` - New device review interface
  - `/api/devices` - JSON API for device data
  - `/api/alerts` - JSON API for alert status

- **Templates:**
  - `main.html` - Dashboard layout
  - `review.html` - Device review interface

### 📡 Network Scanner (`net_scan.py`)
- **Scanning Features:**
  - ARP-based device discovery via Scapy
  - Automatic subnet detection
  - MAC and IP address logging
  - Integration with device profiler

- **Database Operations:**
  - Real-time discovery logging
  - New device detection
  - Known device status updates

- **Performance:**
  - Non-blocking async operations
  - Configurable scan intervals
  - Low network overhead

### 🔍 Device Profiler (`device_profiler.py`)
- **Device Information:**
  - MAC vendor lookup via macvendors.com API
  - DNS hostname resolution
  - Port scanning (common ports)
  - Device type inference

- **Methods:**
  - `get_mac_vendor()`: Vendor identification
  - `get_hostname()`: DNS resolution
  - `scan_open_ports()`: Service detection
  - `profile_device()`: Complete device analysis

---

## 🛎️ Alert System

### ⚙️ PostgreSQL Trigger
- **Trigger Function:**
  ```sql
  CREATE TRIGGER new_device_alert
  AFTER INSERT ON new_devices
  FOR EACH ROW
  EXECUTE FUNCTION insert_alert();
  ```
- Automatically creates alerts for new device detection
- Stores alert metadata including device information
- Prevents duplicate alerts via constraint checks

### 🔔 Alert Daemon (`alert_daemon.py`)
- **Notification Channels:**
  - 📧 Email Alerts:
    - SMTP server configuration
    - HTML-formatted device reports
    - Customizable templates
  - 📱 Telegram Integration:
    - Real-time bot notifications
    - Interactive command support
    - Rich message formatting

- **Features:**
  - Asynchronous notification processing
  - Rate limiting to prevent spam
  - Retry mechanism for failed notifications
  - Alert priority levels
  - Customizable notification templates

---

## 💾 Database Schema

### Tables
| Table Name      | Primary Key | Key Fields              | Description                              |
|-----------------|-------------|-------------------------|------------------------------------------|
| `known_devices` | `id`        | `mac_address` (unique)  | Authorized devices with metadata         |
| `new_devices`   | `id`        | `mac_address` (unique)  | Newly discovered devices pending review  |
| `discovery_log` | `id`        | `timestamp, mac_address`| Historical log of all discovered devices |
| `alerts`        | `id`        | `created_at, status`    | Triggered notifications from new devices |

### Key Relationships
- `new_devices` → `known_devices`: Promotion flow
- `discovery_log` → `known_devices`: Device history tracking
- `alerts` → `new_devices`: Alert source tracking

### Indexes
- `idx_mac_address` on all device tables
- `idx_timestamp` on `discovery_log`
- `idx_status` on `alerts`

---

## 🧪 Production Deployment

### Systemd Services
| Service/Timer           | Restart Policy | Dependencies | Description                    |
|------------------------|----------------|--------------|--------------------------------|
| `netguard_web.service` | `on-failure`   | PostgreSQL   | Flask web interface           |
| `netguard_scan.timer`  | N/A            | None         | 30-second scan scheduler      |
| `alert_daemon.service` | `always`       | PostgreSQL   | Alert notification service    |

### Service Configuration
```ini
[Unit]
Description=NetGuard Web Interface
After=network.target postgresql.service

[Service]
User=netguard
WorkingDirectory=/opt/netguard
ExecStart=/opt/netguard/venv/bin/python webui/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

---

## 🔐 Configuration

### Environment Variables (`.env`)
```ini
# Database Configuration
DB_NAME=netguard
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Alert Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Web Interface
FLASK_SECRET_KEY=your_random_secret_key
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### Security Considerations
- Use strong passwords and different credentials for production
- Enable SSL/TLS for database connections
- Run services with minimal privileges
- Configure firewall rules for web interface
- Regularly update dependencies for security patches

---

## 📊 Monitoring & Maintenance

### Log Files
- Application logs: `/var/log/netguard/app.log`
- Scanner logs: `/var/log/netguard/scanner.log`
- Alert logs: `/var/log/netguard/alerts.log`

### Backup Strategy
1. Daily database backups:
   ```bash
   pg_dump netguard > /backup/netguard_$(date +%Y%m%d).sql
   ```
2. Configuration backup:
   ```bash
   cp /opt/netguard/.env /backup/env_$(date +%Y%m%d)
   ```

### Health Checks
- Database connections
- Scanner operation
- Alert system responsiveness
- Web interface availability  
