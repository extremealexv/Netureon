import asyncio
from flask import Blueprint, render_template, request, flash, jsonify, current_app
from ..models.database import Database
from device_profiler import DeviceProfiler
import logging

logger = logging.getLogger(__name__)
review = Blueprint('review', __name__)

@review.route('/review')
def review_page():
    """Display the review page with new devices."""
    try:
        # Get new devices from database
        new_devices = Database.execute_query("""
            SELECT 
                mac_address, 
                hostname, 
                vendor, 
                device_type,
                last_ip,
                first_seen,
                last_seen,
                COALESCE(reviewed, false) as status,
                notes,
                open_ports
            FROM new_devices
            ORDER BY first_seen DESC
        """)

        return render_template(
            'review.html',
            devices=new_devices if new_devices else []
        )
    except Exception as e:
        logger.error(f"Error loading review page: {str(e)}")
        flash('Error loading devices. Please check the logs.', 'error')
        return render_template('review.html', devices=[])
