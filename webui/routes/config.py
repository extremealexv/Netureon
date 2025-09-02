"""Configuration routes for NetGuard."""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from webui.models.config import Configuration
from webui.models.database import db

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
        
        flash('Configuration updated successfully', 'success')
        return redirect(url_for('config.config'))

    # Get current settings
    settings = Configuration.get_all_settings()
    
    # Apply defaults for missing settings
    for key, default_value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = default_value

    return render_template('config.html', settings=settings)
