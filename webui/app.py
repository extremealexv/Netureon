from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

@app.route('/', methods=['GET', 'POST'])
def main_page():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    if request.method == 'POST':
        selected_devices = request.form.getlist('selected_devices')
        action = request.form.get('action')
        
        if not selected_devices:
            flash('Please select at least one device', 'warning')
            return redirect(url_for('main_page'))
            
        if action == 'block':
            # Move to unknown devices
            threat_level = request.form.get('threat_level', 'medium')
            notes = request.form.get('notes', '')
            
            for mac in selected_devices:
                # Get device info before deleting
                cur.execute("""
                    SELECT last_ip, device_name, last_seen, first_seen 
                    FROM known_devices 
                    WHERE mac_address = %s::macaddr
                """, (mac,))
                device = cur.fetchone()
                
                if device:
                    # Insert into unknown_devices
                    cur.execute("""
                        INSERT INTO unknown_devices 
                        (mac_address, last_ip, first_seen, last_seen, threat_level, notes)
                        VALUES (%s::macaddr, %s, %s, %s, %s, %s)
                    """, (
                        mac, device[0], device[3] or datetime.now(),
                        device[2] or datetime.now(), threat_level,
                        f"Moved from known devices. {notes if notes else ''}"
                    ))
                    
                    # Delete from known_devices
                    cur.execute("DELETE FROM known_devices WHERE mac_address = %s::macaddr", (mac,))
            
            flash(f'{len(selected_devices)} devices marked as unknown', 'warning')
            
        elif action == 'delete':
            # Remove devices
            for mac in selected_devices:
                cur.execute("DELETE FROM known_devices WHERE mac_address = %s", (mac,))
            
            flash(f'Removed {len(selected_devices)} devices', 'danger')
        
        conn.commit()
    
    # Get known devices with active status
    cur.execute("""
        SELECT k.device_name, k.mac_address, k.device_type, k.notes, k.last_seen, k.last_ip,
               EXISTS(
                   SELECT 1 FROM discovery_log d 
                   WHERE d.mac_address = k.mac_address 
                   AND d.timestamp > NOW() - INTERVAL '1 hour'
               ) as is_active
        FROM known_devices k
        ORDER BY k.last_seen DESC NULLS LAST
    """)
    known_hosts = cur.fetchall()
    
    # Get count of new devices
    cur.execute("SELECT COUNT(*) FROM new_devices WHERE reviewed = FALSE")
    new_device_count = cur.fetchone()[0]
    
    # Get count of unknown devices with recent activity
    cur.execute("""
        SELECT COUNT(*) FROM unknown_devices 
        WHERE last_seen > NOW() - INTERVAL '24 hours'
    """)
    active_threats = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return render_template('main.html', 
                         devices=known_hosts, 
                         new_device_count=new_device_count,
                         active_threats=active_threats,
                         now=datetime.now())



@app.route('/review', methods=['GET', 'POST'])
def review_page():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    if request.method == 'POST':
        selected_devices = request.form.getlist('selected_devices')
        action = request.form.get('action')
        
        if selected_devices:
            if action == 'approve':
                for mac in selected_devices:
                    # Move to known devices
                    cur.execute("""
                        WITH device AS (
                            SELECT device_name, mac_address::macaddr, device_type, last_seen, last_ip, notes
                            FROM new_devices
                            WHERE mac_address = %s
                        )
                        INSERT INTO known_devices 
                        (device_name, mac_address, device_type, last_seen, last_ip, notes)
                        SELECT * FROM device
                    """, (mac,))
                    cur.execute("DELETE FROM new_devices WHERE mac_address = %s", (mac,))
                flash(f'Added {len(selected_devices)} devices to known devices', 'success')
            
            elif action == 'block':
                threat_level = request.form.get('threat_level', 'medium')
                notes = request.form.get('notes', '')
                
                for mac in selected_devices:
                    # Move to unknown devices
                    cur.execute("""
                        WITH device AS (
                            SELECT mac_address::macaddr, last_ip, first_seen, last_seen
                            FROM new_devices
                            WHERE mac_address = %s
                        )
                        INSERT INTO unknown_devices 
                        (mac_address, last_ip, first_seen, last_seen, threat_level, notes)
                        SELECT mac_address, last_ip, first_seen, last_seen, %s, %s
                        FROM device
                    """, (mac, threat_level, notes))
                    cur.execute("DELETE FROM new_devices WHERE mac_address = %s", (mac,))
                flash(f'Marked {len(selected_devices)} devices as threats', 'warning')
            
            conn.commit()
        else:
            flash('Please select at least one device', 'warning')

    # Get new devices
    cur.execute("""
        SELECT device_name, mac_address, device_type, last_seen, last_ip, notes, reviewed
        FROM new_devices
        ORDER BY last_seen DESC
    """)
    new_devices = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('review.html', devices=new_devices)


@app.route('/unknown', methods=['GET', 'POST'])
def unknown_devices():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        if request.method == 'POST':
            selected_devices = request.form.getlist('selected_devices')
            action = request.form.get('action')
            
            if not selected_devices:
                flash('Please select at least one device', 'warning')
                return redirect(url_for('unknown_devices'))
            
            if action == 'update_threat':
                threat_level = request.form.get('threat_level', 'medium')
                notes = request.form.get('notes', '')
                
                updated = 0
                for mac in selected_devices:
                    try:
                        cur.execute("""
                            UPDATE unknown_devices 
                            SET threat_level = %s,
                                notes = CASE 
                                    WHEN notes IS NULL OR notes = '' THEN %s
                                    ELSE notes || '. ' || %s
                                END
                            WHERE mac_address::text = %s
                        """, (threat_level, notes, notes, mac))
                        updated += cur.rowcount
                    except psycopg2.Error as e:
                        flash(f'Error updating device {mac}: {str(e)}', 'error')
                
                conn.commit()
                if updated > 0:
                    flash(f'Updated threat level for {updated} devices', 'info')
                
            elif action == 'delete':
                deleted = 0
                for mac in selected_devices:
                    try:
                        # First try exact match
                        cur.execute("""
                            DELETE FROM unknown_devices 
                            WHERE mac_address::text = %s 
                            OR mac_address::text = %s::macaddr::text
                        """, (mac, mac))
                        if cur.rowcount == 0:
                            # If no exact match, try to standardize the MAC format
                            mac_clean = mac.replace('-', ':').lower()
                            cur.execute("""
                                DELETE FROM unknown_devices 
                                WHERE mac_address::text = %s 
                                OR mac_address::text = %s::macaddr::text
                                OR REPLACE(mac_address::text, '-', ':') = %s
                            """, (mac_clean, mac_clean, mac_clean))
                        deleted += cur.rowcount
                    except psycopg2.Error as e:
                        # Check if it's an invalid input syntax error
                        if "invalid input syntax for type macaddr" in str(e):
                            flash(f'Invalid MAC address format for device {mac}', 'error')
                        else:
                            flash(f'Error deleting device {mac}: {str(e)}', 'error')
                        continue
                
                if deleted > 0:
                    conn.commit()
                    flash(f'Successfully removed {deleted} devices', 'success')
                else:
                    flash('No devices were removed. Please check the MAC addresses.', 'warning')
                
            elif action == 'approve':
                notes = request.form.get('notes', '')
                moved = 0
                
                for mac in selected_devices:
                    try:
                        # Get device info
                        cur.execute("""
                            SELECT last_ip, first_seen, last_seen
                            FROM unknown_devices 
                            WHERE mac_address::text = %s
                        """, (mac,))
                        device = cur.fetchone()
                        
                        if device:
                            # Move to known devices
                            cur.execute("""
                                INSERT INTO known_devices 
                                (mac_address, last_ip, first_seen, last_seen, notes)
                                VALUES (%s::macaddr, %s, %s, %s, %s)
                            """, (
                                mac, device[0], device[1],
                                device[2], f"Moved from unknown devices. {notes if notes else ''}"
                            ))
                            
                            # Delete from unknown devices only if insert was successful
                            cur.execute("DELETE FROM unknown_devices WHERE mac_address::text = %s", (mac,))
                            moved += 1
                    except psycopg2.Error as e:
                        flash(f'Error moving device {mac}: {str(e)}', 'error')
                        conn.rollback()  # Rollback the failed transaction
                        continue
                
                conn.commit()
                if moved > 0:
                    flash(f'Moved {moved} devices to known devices', 'success')
        
        # Get unknown devices with their detection count and fix any invalid MAC addresses
        cur.execute("""
            WITH unknown_devices_formatted AS (
                -- First format all MAC addresses consistently
                SELECT 
                    id,
                    CASE 
                        WHEN mac_address IS NULL THEN NULL
                        ELSE LOWER(REPLACE(mac_address::macaddr::text, '-', ':'))
                    END as mac_address,
                    last_ip,
                    first_seen,
                    last_seen,
                    threat_level,
                    notes
                FROM unknown_devices
            )
            SELECT 
                COALESCE(ud.mac_address, '') as mac,
                COALESCE(ud.last_ip::text, 'Unknown') as last_ip,
                COALESCE(TO_CHAR(ud.first_seen, 'YYYY-MM-DD HH24:MI:SS'), 'Never') as first_seen,
                COALESCE(TO_CHAR(ud.last_seen, 'YYYY-MM-DD HH24:MI:SS'), 'Never') as last_seen,
                COALESCE(ud.threat_level, 'medium') as threat_level,
                COALESCE(ud.notes, '') as notes,
                (
                    SELECT COUNT(*) 
                    FROM discovery_log dl
                    WHERE dl.mac_address::macaddr = ud.mac_address::macaddr
                ) as detection_count,
                'Unknown' as hostname
            FROM unknown_devices_formatted ud
            WHERE ud.mac_address IS NOT NULL  -- Skip any null MAC addresses
            ORDER BY 
                CASE ud.threat_level
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                ud.last_seen DESC NULLS LAST
        """)
        unknown_devices = cur.fetchall()
        
        # Debug: Print raw data from database
        print("Raw data from database:")
        for dev in unknown_devices:
            print(f"MAC: '{dev[0]}', IP: '{dev[1]}', First: '{dev[2]}', Last: '{dev[3]}', Threat: '{dev[4]}', Notes: '{dev[5]}'")
        
        devices = []
        for dev in unknown_devices:
            mac = dev[0].strip() if dev[0] else ''  # Remove any whitespace
            if not mac:  # Skip entries with empty MACs
                continue
                
            device = {
                'mac': mac,
                'last_ip': dev[1],
                'first_seen': dev[2],
                'last_seen': dev[3],
                'threat_level': dev[4],
                'notes': dev[5] if dev[5] else 'No notes',
                'detection_count': dev[6],
                'hostname': dev[7]
            }
            devices.append(device)
        
    except psycopg2.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        devices = []
        
    finally:
        cur.close()
        conn.close()
    
    # Debug: Print what we're sending to the template
    print("\nDevices being sent to template:")
    for device in devices:
        print(f"Device: {device}")
    
    return render_template('unknown.html', devices=devices)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
