<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Netureon - Network Security Monitoring System

## Architecture Overview
Netureon is a multi-service network monitoring system with three core components:
- **Scanner Service** (`net_scan.py`): ARP-based network discovery using scapy, runs as systemd service
- **Web Interface** (`webui/`): Flask application with SQLAlchemy ORM for device management  
- **Alert Daemon** (`netureon/alerts/`): Notification system with email/Telegram support

## Key Patterns & Conventions

### Database Architecture
- PostgreSQL with device lifecycle tracking: `known_devices` → `new_devices` → `unknown_devices`
- Raw scan data in `discovery_log` table for historical analysis
- Use `webui/models/database.py` Database class for queries, not direct ORM for scanner
- Migrations in `migrations/` directory with sequential numbering (001_, 002_, etc.)

### Service Management
- Services run as separate systemd units: `netureon.service` (scanner), `netureon_web.service` (web UI)
- Scanner uses `sdnotify` for systemd watchdog integration and health monitoring
- Environment variables in `.env` files for database configuration
- Use virtual environments (`.venv/`) for all Python execution

### Device Profiling Workflow
1. ARP scan discovers MAC/IP pairs
2. `DeviceProfiler` enriches with vendor lookup, hostname resolution, port scanning
3. Unknown devices trigger alerts via `AlertDaemon`
4. Web UI provides review interface for device classification

### Development Patterns
- Structured logging with `RotatingFileHandler` in `~/Netureon/logs/`
- Configuration centralized in `netureon/config/settings.py`
- Database connections use psycopg2 with connection pooling
- Alert system uses observer pattern with pluggable notifiers

### Common Commands
- Run scanner: `sudo systemctl start netureon.service`
- Web interface: `python webui/app.py` (runs on port 5000)
- Database migrations: Use numbered SQL files in `migrations/`
- Setup: `./setup.sh` for Linux, `setup.ps1` for Windows

When adding features, maintain the service separation and use the existing database patterns for device state management.
