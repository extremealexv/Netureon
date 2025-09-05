"""System information route handlers."""

import os
import sys
import platform
import psutil
import netifaces
import psycopg2
from flask import Blueprint, render_template
from sqlalchemy import text

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from version import __version__
from ..models.database import Database

bp = Blueprint('system', __name__)

def get_system_info():
    """Gather system information."""
    # OS Information
    os_info = {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python_version': sys.version,
    }
    
    # Network Information
    net_info = {}
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            net_info[iface] = {
                'ip': addrs[netifaces.AF_INET][0].get('addr', 'N/A'),
                'netmask': addrs[netifaces.AF_INET][0].get('netmask', 'N/A')
            }
            if netifaces.AF_LINK in addrs:
                net_info[iface]['mac'] = addrs[netifaces.AF_LINK][0].get('addr', 'N/A')
    
    # PostgreSQL Version
    db_version = "Unknown"
    try:
        from ..models.database import db
        result = db.session.execute(text('SELECT version();'))
        db_version = result.scalar()
    except Exception as e:
        db_version = f"Error: {str(e)}"
    
    # System Resources
    resources = {
        'cpu_count': psutil.cpu_count(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': {
            'total': psutil.virtual_memory().total,
            'available': psutil.virtual_memory().available,
            'percent': psutil.virtual_memory().percent
        },
        'disk': {
            'total': psutil.disk_usage('/').total,
            'used': psutil.disk_usage('/').used,
            'free': psutil.disk_usage('/').free,
            'percent': psutil.disk_usage('/').percent
        }
    }
    
    return {
        'os': os_info,
        'network': net_info,
        'database': db_version,
        'resources': resources,
        'version': __version__
    }

@bp.route('/system')
def system():
    """Display system information page."""
    try:
        system_info = get_system_info()
        return render_template('system.html', info=system_info)
    except Exception as e:
        return render_template('system.html', error=str(e))
