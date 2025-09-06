import asyncio
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from ..models.database import Database
from ..utils.telegram_notifier import TelegramNotifier
from device_profiler import DeviceProfiler

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

    db = Database()
    new_devices = db._execute_query_impl("""
        SELECT hostname, mac_address, vendor as device_type, 
               last_seen, last_ip, open_ports as notes, reviewed
        FROM new_devices
        WHERE reviewed = false
        ORDER BY last_seen DESC
    """)

    return render_template('review.html', devices=new_devices)

def handle_approve_action(selected_devices):
    """Handle the approval of new devices."""
    if not selected_devices:
        return
        
    try:
        # First, gather all device info
        device_infos = {}
        # Create a list of queries to fetch device info
        info_queries = [(
            """
            SELECT device_name, mac_address, device_type, last_seen, last_ip, notes, first_seen
            FROM new_devices
            WHERE mac_address = :mac
            """,
            {"mac": mac}
        ) for mac in selected_devices]
        
        # Execute all info queries in a single transaction
        results = Database.execute_transaction(info_queries)
        
        # Process the results
        for i, result in enumerate(results):
            info = result.fetchone()
            if info:
                mac = selected_devices[i]
                # Profile the device to get current information
                profiler = DeviceProfiler(info[1], info[4])  # mac_address, last_ip
                profile = profiler.profile()
                
                device_infos[mac] = {
                    'device_name': info[0],
                    'mac_address': info[1],
                    'device_type': info[2],
                    'last_seen': info[3],
                    'last_ip': info[4],
                    'notes': info[5],
                    'hostname': profile['hostname'],
                    'vendor': profile['vendor'],
                    'open_ports': ", ".join(map(str, profile['open_ports'])) if profile['open_ports'] else "None"
                }
        
        # Prepare all database operations
        all_queries = []
        for mac in selected_devices:
            if mac in device_infos:
                # First check if the device exists in known_devices
                device_info = device_infos[mac]
                all_queries.extend([
                    ("""
                        INSERT INTO known_devices 
                        (device_name, mac_address, device_type, last_seen, last_ip, notes, hostname, vendor, open_ports)
                        SELECT 
                            device_name, mac_address, device_type, last_seen, last_ip, notes,
                            :hostname, :vendor, :open_ports
                        FROM new_devices
                        WHERE mac_address = :mac
                        AND NOT EXISTS (
                            SELECT 1 FROM known_devices 
                            WHERE mac_address = :mac
                        )
                    """, {
                        "mac": mac,
                        "hostname": device_info['hostname'],
                        "vendor": device_info['vendor'],
                        "open_ports": device_info['open_ports']
                    }),
                    ("""
                        UPDATE known_devices 
                        SET last_seen = n.last_seen,
                            last_ip = n.last_ip,
                            device_name = COALESCE(n.device_name, known_devices.device_name),
                            device_type = COALESCE(n.device_type, known_devices.device_type),
                            notes = CASE 
                                WHEN n.notes IS NOT NULL AND known_devices.notes IS NOT NULL 
                                THEN known_devices.notes || E'\n' || n.notes
                                ELSE COALESCE(n.notes, known_devices.notes)
                            END,
                            hostname = :hostname,
                            vendor = :vendor,
                            open_ports = :open_ports
                        FROM new_devices n
                        WHERE known_devices.mac_address = :mac
                        AND n.mac_address = :mac
                    """, {
                        "mac": mac,
                        "hostname": device_info['hostname'],
                        "vendor": device_info['vendor'],
                        "open_ports": device_info['open_ports']
                    }),
                    ("""
                        DELETE FROM new_devices 
                        WHERE mac_address = :mac
                    """, {"mac": mac})
                ])
        
        # Execute all database operations in a single transaction
        if all_queries:
            Database.execute_transaction(all_queries)
            
            # Send notifications after successful database update
            for mac, device_data in device_infos.items():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(notifier.notify_device_approved(device_data))
                except Exception as e:
                    current_app.logger.error(f"Failed to send notification for {mac}: {e}")
                finally:
                    loop.close()
            
            flash(f'Added {len(selected_devices)} devices to known devices', 'success')
        else:
            flash('No valid devices to approve', 'warning')
            
    except Exception as e:
        current_app.logger.error(f"Error approving devices: {e}")
        flash('Error approving devices. Please check the logs.', 'error')
    
    return redirect(url_for('review.review_page'))

def handle_block_action(selected_devices):
    threat_level = request.form.get('threat_level', 'medium')
    notes = request.form.get('notes', '')
    
    for mac in selected_devices:
        # Get device info before moving to unknown_devices
        device_info = Database.execute_query_single("""
            SELECT mac_address, last_ip
            FROM new_devices
            WHERE mac_address = :mac
        """, {"mac": mac})
        
        queries = [
            ("""
                INSERT INTO unknown_devices 
                (mac_address, last_ip, first_seen, last_seen, threat_level, notes)
                SELECT mac_address, last_ip, first_seen, last_seen, :threat_level, :notes
                FROM new_devices
                WHERE mac_address = :mac
            """, {"mac": mac, "threat_level": threat_level, "notes": notes}),
            ("DELETE FROM new_devices WHERE mac_address = :mac", {"mac": mac})
        ]
        
        Database.execute_transaction(queries)
        
        # Send notification
        if device_info:
            asyncio.run(notifier.notify_unknown_device(
                device_info[0],  # mac_address
                device_info[1],  # last_ip
                threat_level
            ))
    flash(f'Marked {len(selected_devices)} devices as threats', 'warning')
