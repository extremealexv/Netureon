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
    
    if request.method == 'POST':
        selected_devices = request.form.getlist('selected_devices')
        action = request.form.get('action')
        
        if not selected_devices:
            flash('Please select at least one device', 'warning')
            return redirect(url_for('unknown_devices'))
        
        if action == 'update_threat':
            threat_level = request.form.get('threat_level', 'medium')
            notes = request.form.get('notes', '')
            
            for mac in selected_devices:
                cur.execute("""
                    UPDATE unknown_devices 
                    SET threat_level = %s,
                        notes = CASE 
                            WHEN notes IS NULL OR notes = '' THEN %s
                            ELSE notes || '. ' || %s
                        END
                    WHERE mac_address = %s
                """, (threat_level, notes, notes, mac))
            
            flash(f'Updated threat level for {len(selected_devices)} devices', 'info')
            
        elif action == 'delete':
            for mac in selected_devices:
                cur.execute("DELETE FROM unknown_devices WHERE mac_address = %s", (mac,))
            flash(f'Removed {len(selected_devices)} devices', 'success')
            
        elif action == 'approve':
            notes = request.form.get('notes', '')
            
            for mac in selected_devices:
                # Get device info
                cur.execute("""
                    SELECT last_ip, first_seen, last_seen
                    FROM unknown_devices 
                    WHERE mac_address = %s::macaddr
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
                    
                    # Delete from unknown devices
                    cur.execute("DELETE FROM unknown_devices WHERE mac_address = %s::macaddr", (mac,))
            
            flash(f'Moved {len(selected_devices)} devices to known devices', 'success')
        
        conn.commit()
    
    # Get unknown devices with their detection count
    cur.execute("""
        SELECT 
            ud.mac_address,
            ud.last_ip,
            ud.first_seen,
            ud.last_seen,
            ud.threat_level,
            ud.notes,
            (
                SELECT COUNT(*) 
                FROM discovery_log 
                WHERE mac_address = ud.mac_address
            ) as detection_count,
            'Unknown' as hostname
        FROM unknown_devices ud
        ORDER BY 
            CASE ud.threat_level
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
            END,
            ud.last_seen DESC
    """)
    unknown_devices = cur.fetchall()
    
    cur.close()
    conn.close()
    
    devices = [
        {
            'mac': dev[0],
            'last_ip': dev[1],
            'first_seen': dev[2],
            'last_seen': dev[3],
            'threat_level': dev[4],
            'notes': dev[5],
            'detection_count': dev[6],
            'hostname': dev[7]
        }
        for dev in unknown_devices
    ]
    
    return render_template('unknown.html', devices=devices)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
