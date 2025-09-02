import asyncio
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.database import Database
from ..utils.telegram_notifier import TelegramNotifier

review = Blueprint('review', __name__)
notifier = TelegramNotifier()

@review.route('/review', methods=['GET', 'POST'])
def review_page():
    if request.method == 'POST':
        selected_devices = request.form.getlist('selected_devices')
        action = request.form.get('action')
        
        if selected_devices:
            if action == 'approve':
                handle_approve_action(selected_devices)
            elif action == 'block':
                handle_block_action(selected_devices)
        else:
            flash('Please select at least one device', 'warning')

    new_devices = Database.execute_query("""
        SELECT device_name, mac_address, device_type, last_seen, last_ip, notes, reviewed
        FROM new_devices
        ORDER BY last_seen DESC
    """)

    return render_template('review.html', devices=new_devices)

def handle_approve_action(selected_devices):
    for mac in selected_devices:
        # Get complete device info before removing from new_devices
        device_info = Database.execute_query_single("""
            SELECT device_name, mac_address, device_type, last_seen, last_ip, notes, first_seen
            FROM new_devices
            WHERE mac_address = %s
        """, (mac,))
        
        if device_info:
            device_data = {
                'device_name': device_info[0],
                'mac_address': device_info[1],
                'device_type': device_info[2],
                'last_seen': device_info[3],
                'last_ip': device_info[4],
                'notes': device_info[5]
            }
            
            # Send notification before database changes
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(notifier.notify_device_approved(device_data))
            finally:
                loop.close()
        
        queries = [
            ("""
                WITH input_mac AS (
                    SELECT %s::macaddr as addr
                ),
                device AS (
                    SELECT device_name, mac_address::macaddr, device_type, last_seen, last_ip, notes
                    FROM new_devices
                    WHERE mac_address::macaddr = (SELECT addr FROM input_mac)
                )
                INSERT INTO known_devices 
                (device_name, mac_address, device_type, last_seen, last_ip, notes)
                SELECT * FROM device
            """, (mac,)),
            ("DELETE FROM new_devices WHERE mac_address = %s", (mac,))
        ]
        Database.execute_transaction(queries)
            
    flash(f'Added {len(selected_devices)} devices to known devices', 'success')

def handle_block_action(selected_devices):
    threat_level = request.form.get('threat_level', 'medium')
    notes = request.form.get('notes', '')
    
    for mac in selected_devices:
        # Get device info before moving to unknown_devices
        device_info = Database.execute_query_single("""
            SELECT mac_address, last_ip
            FROM new_devices
            WHERE mac_address = %s
        """, (mac,))
        
        queries = [
            ("""
                WITH device AS (
                    SELECT mac_address::macaddr, last_ip, first_seen, last_seen
                    FROM new_devices
                    WHERE mac_address = %s
                )
                INSERT INTO unknown_devices 
                (mac_address, last_ip, first_seen, last_seen, threat_level, notes)
                SELECT mac_address, last_ip, first_seen, last_seen, %s, %s
                FROM device
            """, (mac, threat_level, notes)),
            ("DELETE FROM new_devices WHERE mac_address = %s", (mac,))
        ]
        
        Database.execute_transaction(queries)
        
        # Send notification
        if device_info:
            asyncio.run(notifier.notify_unknown_device(
                device_info[0],  # mac_address
                device_info[1],  # last_ip
                threat_level
            ))
        Database.execute_transaction(queries)
    flash(f'Marked {len(selected_devices)} devices as threats', 'warning')
