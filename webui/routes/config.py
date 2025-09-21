"""Configuration routes for Netureon."""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from webui.models.config import Configuration
from webui.models.database import db
from ..utils.logging_manager import configure_logging
import logging

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
                from ..utils.systemd_utils import update_scan_timer
                try:
                    interval = int(value)
                    update_scan_timer(interval)
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
