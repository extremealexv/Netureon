import logging
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from ..models.database import Database
from ..utils.device_manager import DeviceManager  # Add this import

# Initialize logger for this module
logger = logging.getLogger(__name__)

unknown = Blueprint('unknown', __name__)

@unknown.route('/unknown', methods=['GET'])
def unknown_devices():
    """Handle unknown devices page."""
    try:
        # Updated query to get blocked devices from unknown_devices table
        unknown_devices = Database.execute_query("""
            SELECT 
                u.mac_address as mac,
                u.hostname,
                u.last_ip,
                u.first_seen,
                u.last_seen,
                COALESCE(COUNT(DISTINCT a.id), 0) as alert_count,
                CASE 
                    WHEN COUNT(DISTINCT a.id) > 10 THEN 'high'
                    WHEN COUNT(DISTINCT a.id) > 5 THEN 'medium'
                    ELSE 'low'
                END as threat_level,
                u.notes,
                STRING_AGG(DISTINCT a.alert_type, ', ') as alert_types,
                u.status
            FROM unknown_devices u
            LEFT JOIN alerts a ON a.device_mac = u.mac_address
            GROUP BY 
                u.mac_address, 
                u.hostname, 
                u.last_ip, 
                u.first_seen, 
                u.last_seen, 
                u.notes,
                u.status
            ORDER BY u.last_seen DESC
        """)

        if unknown_devices:
            devices = DeviceManager.format_device_list(unknown_devices)
            logger.debug(f"Found {len(devices)} unknown devices")
            logger.debug(f"Device details: {devices}")
            return render_template('unknown.html', devices=devices)
        else:
            logger.debug("No unknown devices found")
            return render_template('unknown.html', devices=[])

    except Exception as e:
        logger.error(f"Error loading unknown devices: {str(e)}")
        logger.exception("Full traceback:")
        flash(f'Error loading devices: {str(e)}', 'error')
        return render_template('unknown.html', devices=[])

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
                # Delete alerts first due to foreign key
                ("""
                    DELETE FROM alerts 
                    WHERE device_mac::macaddr = %(mac)s::macaddr
                """, {'mac': mac_clean}),
                
                # Then delete the device
                ("""
                    DELETE FROM new_devices 
                    WHERE mac_address = %(mac)s::macaddr
                    RETURNING 1
                """, {'mac': mac_clean})
            ]
            
            result = Database.execute_transaction(queries)
            if result:
                deleted += 1
                logger.info(f"Successfully deleted device {mac_clean}")
                
        except Exception as e:
            logger.error(f"Error deleting device {mac}: {str(e)}")
            flash(f'Error deleting device {mac}: {str(e)}', 'error')
            continue
    
    if deleted > 0:
        flash(f'Successfully removed {deleted} devices and related alerts', 'success')
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

@unknown.route('/unknown/delete', methods=['POST'])
def delete_device():
    """Delete a device from new_devices table."""
    try:
        data = request.json
        if not data or 'mac' not in data:
            return jsonify({'error': 'No MAC address specified'}), 400

        mac = data['mac'].strip().lower()
        
        # Log deletion attempt
        logger.info(f"Attempting to delete device: {mac}")

        # Delete device from new_devices
        result = Database.execute_query(
            "DELETE FROM new_devices WHERE mac_address = %s::macaddr",
            (mac,)
        )

        if result:
            logger.info(f"Device {mac} deleted successfully")
            return jsonify({
                'success': True,
                'message': f'Device {mac} deleted successfully'
            })
        else:
            logger.error(f"Device {mac} not found or couldn't be deleted")
            return jsonify({
                'error': f'Device {mac} not found or couldn\'t be deleted'
            }), 404

    except Exception as e:
        error_msg = f"Error deleting device {mac if 'mac' in locals() else 'unknown'}: {str(e)}"
        logger.error(error_msg)
        logger.exception("Delete device error details:")
        return jsonify({'error': error_msg}), 500
