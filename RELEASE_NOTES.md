# Netureon v1.3.1 Release Notes

## 🚀 New Features

### Scanning System Improvements
- Added configurable scanning intervals via web interface
- Implemented systemd timer for reliable scanning scheduling
- Enhanced device profiling with more detailed information
- Added network interface detection and configuration
- Improved duplicate device handling

### Configuration Management
- Added web-based configuration interface
- Implemented real-time configuration updates
- Added configuration validation and error handling
- Created centralized configuration management
- Added support for Telegram notifications

### Web Interface Enhancements
- Added system information dashboard
- Improved device management interface
- Enhanced configuration controls
- Added real-time status updates
- Improved error handling and user feedback
- **NEW**: Consistent UI design across all pages
- **NEW**: Activity indicators showing device status (active/inactive)
- **NEW**: Enhanced device cards with visual status indicators

## 🔧 Technical Improvements

### Code Quality
- Improved error handling across all components
- Enhanced logging system implementation
- Added comprehensive type hints
- Improved code documentation
- Added configuration validation
- **NEW**: Fixed database column mismatches and schema consistency
- **NEW**: Unified alert notification system

### Performance & Reliability
- Optimized network scanning process
- Improved database operations efficiency
- Enhanced service management
- Added proper error recovery
- Improved systemd integration
- **NEW**: Eliminated duplicate notifications
- **NEW**: Better JSON API support for web interface actions

## 🐛 Bug Fixes
- Fixed scanning interval configuration issues
- Improved service restart handling
- Enhanced error handling in network scanning
- Fixed configuration persistence issues
- Improved database connection reliability
- **NEW**: Fixed device card styling and status badge issues
- **NEW**: Resolved unknown device processing errors
- **NEW**: Fixed database column name inconsistencies
- **NEW**: Corrected duplicate notification issues

## 🎨 UI/UX Improvements
- **NEW**: Consistent page layouts across Known Devices, Review, and Unknown pages
- **NEW**: Activity status indicators with green (active) and gray (inactive) badges
- **NEW**: Clean white device cards with colored status elements only
- **NEW**: Responsive design that works on mobile devices
- **NEW**: Unified CSS framework for consistent styling

## 📝 Notes
- Requires Python 3.8 or higher
- **Updated**: All NetGuard references changed to Netureon
- **Updated**: Service names updated to netureon-* convention
- **Updated**: Database name changed from netguard to netureon
- PostgreSQL 13 or higher recommended
- Database schema updated for better device tracking
- Added support for both Windows and Linux installations

## 🔜 Coming Soon
- Enhanced threat detection
- Improved device fingerprinting
- Network topology mapping
- Advanced alert rules
- API improvements

## 📝 Notes
- Requires Python 3.8 or higher
- Database schema remains compatible with v1.0.3
- Configuration files from v1.0.3 are fully compatible

## 🔜 Coming Soon
- Enhanced device profiling
- Improved threat detection
- Extended API capabilities
- Web interface improvements
