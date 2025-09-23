from flask import Blueprint, render_template, request, redirect, url_for, flash
from webui.models.database import Database
from webui.utils.device_utils import DeviceManager
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/', methods=['GET', 'POST'])
def main_page():
    if request.method == 'POST':
        selected_devices = request.form.getlist('selected_devices')
        action = request.form.get('action')
        
        if not selected_devices:
            flash('Please select at least one device', 'warning')
            return redirect(url_for('main.main_page'))
            
        if action == 'block':
            handle_block_action(selected_devices)
        elif action == 'delete':
            handle_delete_action(selected_devices)
    
    known_hosts = Database.execute_query("""
        SELECT 
            k.hostname,
            k.mac_address,
            k.vendor,
            k.device_type,
            k.last_ip,
            k.first_seen,
            k.last_seen,
            COALESCE(k.risk_level, 'medium') as risk_level,
            k.notes,
            k.open_ports,
            EXISTS(
                SELECT 1 FROM alerts a 
                WHERE a.device_mac = k.mac_address 
                AND COALESCE(a.status, 'new') = 'new'
            ) as has_alerts
        FROM known_devices k
        ORDER BY k.last_seen DESC
    """)
    
    new_device_count = Database.execute_query(
        "SELECT COUNT(*) FROM new_devices WHERE reviewed = FALSE"
    )[0][0]
    
    active_threats = Database.execute_query("""
        SELECT COUNT(*) FROM unknown_devices 
        WHERE last_seen > NOW() - INTERVAL '24 hours'
    """)[0][0]
    
    return render_template('main.html', 
                         devices=known_hosts, 
                         new_device_count=new_device_count,
                         active_threats=active_threats,
                         now=datetime.now())

def handle_block_action(selected_devices):
    threat_level = request.form.get('threat_level', 'medium')
    notes = request.form.get('notes', '')
    
    for mac in selected_devices:
        try:
            device = Database.execute_query("""
                WITH mac_addr AS (
                    SELECT %s::macaddr AS addr
                )
                SELECT last_ip::text, device_name, last_seen, first_seen 
                FROM known_devices 
                WHERE mac_address::macaddr = (SELECT addr FROM mac_addr)
            """, (mac,))[0]
            
            # Move to unknown devices and delete from known devices
            queries = [
                ("""
                    INSERT INTO unknown_devices 
                    (mac_address, last_ip, first_seen, last_seen, threat_level, notes)
                    VALUES (%s::macaddr, %s::inet, %s, %s, %s, %s)
                """, (
                    mac, device[0], device[3] or datetime.now(),
                    device[2] or datetime.now(), threat_level,
                    f"Moved from known devices. {notes if notes else ''}"
                )),
                ("""
                    DELETE FROM known_devices 
                    WHERE mac_address::macaddr = %s::macaddr
                """, (mac,))
            ]
            Database.execute_transaction(queries)
            
        except Exception as e:
            flash(f'Error processing device {mac}: {str(e)}', 'error')
            continue
    
    flash(f'{len(selected_devices)} devices marked as unknown', 'warning')

def handle_delete_action(selected_devices):
    deleted = 0
    for mac in selected_devices:
        try:
            mac_clean = mac.strip().lower()
            # Delete from known_devices and cleanup related data
            queries = [
                # Remove any existing alerts
                ("""
                    DELETE FROM alerts 
                    WHERE device_mac = %s::macaddr
                """, (mac_clean,)),
                # Remove from discovery_log
                ("""
                    DELETE FROM discovery_log 
                    WHERE mac_address = %s::macaddr
                """, (mac_clean,)),
                # Finally remove from known_devices
                ("""
                    DELETE FROM known_devices 
                    WHERE mac_address = %s::macaddr
                """, (mac_clean,))
            ]
            
            # Execute all cleanup in a single transaction
            Database.execute_transaction(queries)
            deleted += 1
            
        except Exception as e:
            flash(f'Error deleting device {mac}: {str(e)}', 'error')
            continue
    
    if deleted > 0:
        flash(f'Removed {deleted} devices and cleaned up related data', 'danger')
    else:
        flash('No devices were removed. Please check the MAC addresses.', 'warning')
