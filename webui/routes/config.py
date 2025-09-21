"""Configuration routes for Netureon."""
from flask import Blueprint, render_template, request, flash, redirect, url_for
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
    'scanning_enabled': 'true'
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
        # Update all settings
        for key in DEFAULT_SETTINGS.keys():
            if key in ['scanning_enabled', 'enable_email_notifications', 'enable_telegram_notifications']:
                # Handle checkbox fields - they only appear in form data when checked
                value = 'true' if key in request.form else 'false'
            else:
                value = request.form.get(key, DEFAULT_SETTINGS[key])
            Configuration.set_setting(key, value)

            # Handle scanning interval updates
            if key == 'scanning_interval':
                interval = request.form.get('scanning_interval', '300')
                try:
                    interval = int(interval)
                    if interval < 60:
                        flash('Scanning interval must be at least 60 seconds', 'error')
                    else:
                        if update_scan_timer(interval):
                            db.execute_query(
                                "UPDATE configuration SET value = %s WHERE key = 'scanning_interval'",
                                (str(interval),)
                            )
                            flash('Scanning interval updated successfully', 'success')
                        else:
                            flash('Failed to update scanning interval', 'error')
                except ValueError:
                    flash('Invalid scanning interval value', 'error')
                    return redirect(url_for('config.config'))
                except Exception as e:
                    flash(f'Failed to update scanning interval: {str(e)}', 'error')
                    return redirect(url_for('config.config'))
        
        # Handle logging level
        logging_level = request.form.get('logging_level', 'INFO')
        try:
            if hasattr(logging, logging_level):
                db.execute_query(
                    "UPDATE configuration SET value = %s WHERE key = 'logging_level'",
                    (logging_level,)
                )
                # Reconfigure logging across all modules
                if configure_logging():
                    flash(f'Logging level updated to {logging_level}', 'success')
                else:
                    flash('Failed to apply logging level changes', 'error')
            else:
                flash(f'Invalid logging level: {logging_level}', 'error')
        except Exception as e:
            flash(f'Failed to update logging level: {str(e)}', 'error')
            
        return redirect(url_for('config.config'))

    # Get current settings
    settings = Configuration.get_all_settings()
    
    # Apply defaults for missing settings
    for key, default_value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = default_value

    return render_template('config.html', settings=settings)
