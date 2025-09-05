# 🛡️ Netureon v1.3.1

Netureon is a comprehensive network monitoring and security solution designed to help system administrators maintain visibility and control over their local networks. Built with Python, Flask, and PostgreSQL, it provides real-time device detection, automated profiling, and security alerts.

## ✨ Key Features

### 🔍 Network Monitoring
- Real-time device discovery and tracking
- Automated MAC vendor identification
- DNS hostname resolution
- Port scanning and service detection
- Configurable scanning intervals
- Device profiling and categorization

### 🚨 Security Features
- Unknown device detection and alerts
- Multiple notification channels (Email, Telegram)
- Device blacklisting capabilities
- Connection history logging
- Automated threat assessment
- Real-time security alerts

### 💻 Web Interface
- Real-time network dashboard
- Device management interface
- Full configuration control
- System status monitoring
- Alert management
- Historical data visualization
- Mobile-responsive design

### 🔄 Integration & Automation
- Systemd service integration
- Configurable scanning schedules
- Automated device profiling
- Multiple notification channels
- Service monitoring

## 🚀 Quick Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 13 or higher
- Git (for repository cloning)
- SMTP server access (for notifications)

### Windows Setup
```powershell
# Clone the repository
git clone https://github.com/extremealexv/Netureon.git
cd Netureon

# Run the setup script
.\setup.ps1

# Start the services
Start-Service Netureon
Start-Service NetureonAlerts
```

### Linux Setup
```bash
# Clone the repository
git clone https://github.com/extremealexv/Netureon.git
cd Netureon

# Run the setup script
chmod +x setup.sh
./setup.sh

# Start the services
sudo systemctl start netureon
sudo systemctl start netureon-alerts
```

## 📖 Documentation
For detailed documentation about project architecture, configuration options, and advanced features, please see [Netureon.md](Netureon.md).

## � Quick Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 13 or higher
- Git (for installation)
- SMTP server (for email notifications)
- Telegram Bot (optional, for Telegram notifications)
- Root/Administrator access

### Linux Installation
```bash
# Clone the repository
git clone https://github.com/extremealexv/NetGuard.git
cd NetGuard

# Run the setup script
chmod +x setup.sh
./setup.sh

# Start the services
sudo systemctl start netguard_web
sudo systemctl start alert_daemon
sudo systemctl start netguard_scan.timer
```

### Windows Installation
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

## 🤖 Setting Up Telegram Notifications

To enable Telegram notifications, you'll need to create a Telegram bot and configure it in NetGuard:

1. Start a chat with [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot:
   ```
   /newbot
   ```
3. Follow the prompts:
   - Enter a name for your bot (e.g., "MyNetureon Bot")
   - Enter a username for your bot (must end in 'bot', e.g., "my_netureon_bot")
4. Save the API token BotFather gives you
5. Start a chat with your new bot and send it any message
6. Get your chat ID:
   ```
   # In your web browser, replace <YOUR_BOT_TOKEN> with your token
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
7. Look for the "id" field in the JSON response - this is your chat ID
8. Add these to your `.env` file:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```
9. Restart the alert daemon:
   ```bash
   # Linux
   sudo systemctl restart alert_daemon
   
   # Windows
   Restart-Service NetGuardAlerts
   ```

Test the setup by sending a test notification:
```python
# In the NetGuard directory
python -c "from webui.utils.telegram_notifier import send_telegram_message; send_telegram_message('🛡️ NetGuard test notification')"
```

## 🛠️ Project Structure
```
NetGuard/
├── webui/                 # Web interface components
│   ├── app.py            # Flask application
│   ├── models/           # Database models
│   ├── routes/           # Route handlers
│   ├── templates/        # HTML templates
│   ├── static/           # Static assets
│   └── utils/            # Utility modules
├── migrations/           # Database migrations
├── net_scan.py          # Network scanner
├── device_profiler.py   # Device profiling
├── alert_daemon.py      # Alert system
├── main.py             # Main entry point
├── setup.sh            # Linux setup script
├── setup.ps1           # Windows setup script
├── requirements.txt    # Python dependencies
└── .env.example       # Environment template

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

## � Maintenance

### Uninstalling
To remove NetGuard and all its components:

#### Windows
```powershell
# Run as Administrator
.\scripts\uninstall.ps1
```

#### Linux
```bash
# Run as root or with sudo
sudo ./scripts/uninstall.sh
```

The uninstall scripts will:
1. Stop and remove all services
2. Clean up program data and logs
3. Remove service configurations
4. Guide you through complete removal

## �🔒 Security
For security issues, please email aleksandr@vasilyev.tech instead of using the issue tracker.

---
Made with ❤️ by Alexander Vasilyev
