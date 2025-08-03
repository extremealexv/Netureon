# 🛡️ NetGuard

NetGuard is a comprehensive network monitoring and security solution designed to help system administrators maintain visibility and control over their local networks. Built with Python, Flask, and PostgreSQL, it provides real-time device detection, automated profiling, and security alerts.

## ✨ Key Features

### 🔍 Network Monitoring
- Real-time device discovery and tracking
- Automated MAC vendor identification
- DNS hostname resolution
- Port scanning and service detection
- Device profiling and categorization

### 🚨 Security Features
- Unknown device detection and alerts
- Email notifications for security events
- Device blacklisting capabilities
- Connection history logging
- Automated threat assessment

### 💻 Web Interface
- Real-time network dashboard
- Device management interface
- Alert configuration and monitoring
- Historical data visualization
- Mobile-responsive design

### 🔄 Integration & Automation
- REST API for external integration
- Automated device profiling
- Configurable alert rules
- Email notification system
- Service monitoring capabilities

## 🚀 Quick Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 13 or higher
- Git (for repository cloning)
- SMTP server access (for notifications)

### Windows Setup
```powershell
# Clone the repository
git clone https://github.com/extremealexv/NetGuard.git
cd NetGuard

# Run the setup script
.\setup.ps1

# Start the services
Start-Service NetGuard
Start-Service NetGuardAlerts
```

### Linux Setup
```bash
# Clone the repository
git clone https://github.com/extremealexv/NetGuard.git
cd NetGuard

# Run the setup script
chmod +x setup.sh
./setup.sh

# Start the services
sudo systemctl start netguard
sudo systemctl start netguard-alerts
```

## 📖 Documentation
For detailed documentation about project architecture, configuration options, and advanced features, please see [NetGuard.md](NetGuard.md).

## 🛠️ Development

### Project Structure
```
NetGuard/
├── webui/                 # Web interface components
│   ├── app.py            # Flask application
│   ├── models/           # Database models
│   ├── routes/           # Route handlers
│   ├── templates/        # HTML templates
│   └── static/           # Static assets
├── net_scan.py           # Network scanner
├── device_profiler.py    # Device profiling
├── alert_daemon.py       # Alert system
└── main.py              # Main application entry
```

### Setting Up Development Environment
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   .\venv\Scripts\Activate   # Windows
   ```

2. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   - Copy `.env.example` to `.env`
   - Update settings for your environment

4. Start development server:
   ```bash
   python webui/app.py
   ```

### Running Tests
```bash
python -m pytest tests/
```

## 📄 License
MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 🆘 Support
For support, please:
1. Check the [documentation](NetGuard.md)
2. Search for existing issues
3. Open a new issue if needed

## 🔒 Security
For security issues, please email security@netguard.local instead of using the issue tracker.

---
Made with ❤️ by Alexander Vasilyev
