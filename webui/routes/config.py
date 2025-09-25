"""Configuration routes for Netureon."""
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from webui.models.config import Configuration
from webui.models.database import db
from ..utils.logging_manager import configure_logging
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

config_bp = Blueprint('config', __name__)

DEFAULT_SETTINGS = {
    'smtp_server': '',
    'smtp_port': '587',
    'smtp_username': '',
    'smtp_password': '',
    'smtp_from_address': '',
    'smtp_to_address': '',
    'telegram_bot_token': '',
    'telegram_chat_id': '',
    'enable_email_notifications': 'false',
    'enable_telegram_notifications': 'false',
    'scanning_interval': '300',  # 5 minutes default
    'scanning_enabled': 'true',
    'logging_level': 'INFO'  # Default logging level
}

def update_scan_timer(interval):
    """Update the scanning interval."""
    try:
        script_path = Path(__file__).parent.parent.parent / 'update_timer.sh'
        result = subprocess.run(
            ['sudo', str(script_path), str(interval)],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Scan timer updated successfully to {interval} seconds")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to update scan timer: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error updating scan timer: {str(e)}")
        return False

@config_bp.route('/config', methods=['GET', 'POST'])
def config():
    """Handle configuration page."""
    if request.method == 'POST':
        # Update all settings except special ones
        for key in DEFAULT_SETTINGS.keys():
            if key in ['scanning_interval', 'logging_level']:
                # Skip special handling keys
                continue
            
            if key in ['scanning_enabled', 'enable_email_notifications', 'enable_telegram_notifications']:
                # Handle checkbox fields - they only appear in form data when checked
                value = 'true' if key in request.form else 'false'
            else:
                value = request.form.get(key, DEFAULT_SETTINGS[key])
            Configuration.set_setting(key, value)

        # Handle scanning interval updates specifically
        interval = request.form.get('scanning_interval', '300')
        try:
            interval = int(interval)
            if interval < 60:
                flash('Scanning interval must be at least 60 seconds', 'error')
            else:
                # Use ORM method instead of raw database query
                Configuration.set_setting('scanning_interval', str(interval))
                if update_scan_timer(interval):
                    flash('Scanning interval updated successfully', 'success')
                else:
                    flash('Failed to update system timer (settings saved)', 'warning')
        except ValueError:
            flash('Invalid scanning interval value', 'error')
            return redirect(url_for('config.config'))
        except Exception as e:
            logger.error(f"Failed to update scanning interval: {str(e)}")
            flash(f'Failed to update scanning interval: {str(e)}', 'error')
            return redirect(url_for('config.config'))
        
        # Handle logging level specifically
        logging_level = request.form.get('logging_level', 'INFO')
        try:
            if hasattr(logging, logging_level):
                # Use ORM method to set logging level
                Configuration.set_setting('logging_level', logging_level)
                
                # Reconfigure logging across all modules
                if configure_logging(current_app):
                    flash(f'Logging level updated to {logging_level}', 'success')
                    logger.info(f"Logging level changed to {logging_level}")
                    
                    # Try to reconfigure logging for running services
                    try:
                        script_path = Path(__file__).parent.parent.parent / 'scripts' / 'reconfigure_logging.py'
                        if script_path.exists():
                            import subprocess
                            result = subprocess.run(
                                ['python', str(script_path)],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            if result.returncode == 0:
                                logger.info("Successfully notified running services of logging level change")
                            else:
                                logger.warning(f"Could not notify running services: {result.stderr}")
                        else:
                            logger.info("Logging reconfiguration script not found, services may need restart")
                    except Exception as script_error:
                        logger.warning(f"Could not run logging reconfiguration script: {script_error}")
                else:
                    flash('Failed to apply logging level changes', 'error')
            else:
                flash(f'Invalid logging level: {logging_level}', 'error')
        except Exception as e:
            logger.error(f"Failed to update logging level: {str(e)}")
            flash(f'Failed to update logging level: {str(e)}', 'error')
            
        return redirect(url_for('config.config'))

    # Get current settings with app context
    with current_app.app_context():
        settings = Configuration.get_all_settings()
    
    # Apply defaults for missing settings
    for key, default_value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = default_value

    return render_template('config.html', settings=settings)
