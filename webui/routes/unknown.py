from flask import Blueprint, render_template, request, redirect, url_for, flash
from webui.models.database import Database
from webui.utils.device_utils import DeviceManager

unknown = Blueprint('unknown', __name__)

@unknown.route('/unknown', methods=['GET', 'POST'])
def unknown_devices():
    if request.method == 'POST':
        handle_post_request()
    
    try:
        unknown_devices = Database.execute_query("""
            WITH unknown_devices_formatted AS (
                SELECT 
                    id,
                    mac_address,
                    COALESCE(
                        LOWER(REPLACE(mac_address::macaddr::text, '-', ':')), 
                        'no_mac'
                    ) as formatted_mac,
                    last_ip,
                    first_seen,
                    last_seen,
                    threat_level,
                    notes
                FROM unknown_devices
            )
            SELECT 
                formatted_mac as mac,
                COALESCE(last_ip::text, 'Unknown') as last_ip,
                COALESCE(TO_CHAR(first_seen, 'YYYY-MM-DD HH24:MI:SS'), 'Never') as first_seen,
                COALESCE(TO_CHAR(last_seen, 'YYYY-MM-DD HH24:MI:SS'), 'Never') as last_seen,
                COALESCE(threat_level, 'medium') as threat_level,
                COALESCE(notes, '') as notes,
                (
                    SELECT COUNT(*) 
                    FROM discovery_log dl
                    WHERE dl.mac_address::macaddr = udf.mac_address::macaddr
                ) as detection_count,
                'Unknown' as hostname
            FROM unknown_devices_formatted udf
            WHERE mac_address IS NOT NULL
            ORDER BY 
                CASE threat_level
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                last_seen DESC NULLS LAST
        """)
        
        devices = DeviceManager.format_device_list(unknown_devices)
        
    except Exception as e:
        flash(f'Database error: {str(e)}', 'error')
        devices = []
    
    return render_template('unknown.html', devices=devices)

def handle_post_request():
    selected_devices = request.form.getlist('selected_devices')
    action = request.form.get('action')
    
    if not selected_devices:
        flash('Please select at least one device', 'warning')
        return redirect(url_for('unknown.unknown_devices'))
    
    if action == 'update':
        handle_update_action(selected_devices)
    elif action == 'delete':
        handle_delete_action(selected_devices)
    elif action == 'approve':
        handle_approve_action(selected_devices)

def handle_update_action(selected_devices):
    threat_level = request.form.get('threat_level', 'medium')
    notes = request.form.get('notes', '')
    
    updated = 0
    for mac in selected_devices:
        try:
            updated += Database.execute_query("""
                UPDATE unknown_devices 
                SET threat_level = %s,
                    notes = CASE 
                        WHEN notes IS NULL OR notes = '' THEN %s
                        ELSE notes || '. ' || %s
                    END
                WHERE mac_address::text = %s
                RETURNING 1
            """, (threat_level, notes, notes, mac))[0][0]
        except Exception as e:
            flash(f'Error updating device {mac}: {str(e)}', 'error')
    
    if updated > 0:
        flash(f'Updated threat level for {updated} devices', 'info')

def handle_delete_action(selected_devices):
    deleted = 0
    for mac in selected_devices:
        try:
            mac_clean = mac.strip().lower()
            queries = [
                # Remove from discovery_log
                ("""
                    DELETE FROM discovery_log 
                    WHERE mac_address::macaddr = %s::macaddr
                """, (mac_clean,)),
                # Remove any existing alerts
                ("""
                    DELETE FROM alerts 
                    WHERE device_id::macaddr = %s::macaddr
                """, (mac_clean,)),
                # Finally remove from unknown_devices
                ("""
                    DELETE FROM unknown_devices 
                    WHERE mac_address = %s::macaddr
                    RETURNING 1
                """, (mac_clean,))
            ]
            
            # Execute all queries in a transaction
            result = Database.execute_transaction(queries)
            if result:
                deleted += 1
                
        except Exception as e:
            flash(f'Error deleting device {mac}: {str(e)}', 'error')
            continue
    
    if deleted > 0:
        flash(f'Successfully removed {deleted} devices and cleaned up related data', 'success')
    else:
        flash('No devices were removed. Please check the MAC addresses.', 'warning')

def handle_approve_action(selected_devices):
    notes = request.form.get('notes', '')
    moved = 0
    
    for mac in selected_devices:
        try:
            device = Database.execute_query("""
                SELECT last_ip, first_seen, last_seen
                FROM unknown_devices 
                WHERE mac_address = %s::macaddr
            """, (mac,))[0]
            
            queries = [
                ("""
                    INSERT INTO known_devices 
                    (mac_address, last_ip, first_seen, last_seen, notes)
                    VALUES (%s::macaddr, %s, %s, %s, %s)
                """, (
                    mac, device[0], device[1],
                    device[2], f"Moved from unknown devices. {notes if notes else ''}"
                )),
                ("DELETE FROM unknown_devices WHERE mac_address = %s::macaddr", (mac,))
            ]
            Database.execute_transaction(queries)
            moved += 1
        except Exception as e:
            flash(f'Error moving device {mac}: {str(e)}', 'error')
            continue
    
    if moved > 0:
        flash(f'Moved {moved} devices to known devices', 'success')
