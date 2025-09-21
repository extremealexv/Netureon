import asyncio
from flask import Blueprint, render_template, request, flash, jsonify, current_app
from ..models.database import Database
import logging

logger = logging.getLogger(__name__)
review = Blueprint('review', __name__)

@review.route('/review')
def review_page():
    """Display the review page with new devices."""
    try:
        new_devices = Database.execute_query("""
            SELECT 
                hostname,
                mac_address,
                vendor,
                device_type,
                last_ip,
                first_seen,
                last_seen,
                COALESCE(reviewed, false) as status,
                notes,
                CASE 
                    WHEN open_ports IS NULL THEN '[]'::jsonb
                    WHEN open_ports::text = '' THEN '[]'::jsonb
                    ELSE open_ports::jsonb
                END as open_ports
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

@review.route('/review/approve', methods=['POST'])
def approve_devices():
    """Approve selected devices and move them to known devices."""
    try:
        data = request.json
        if not data or 'devices' not in data:
            return jsonify({'error': 'No devices specified'}), 400

        approved = 0
        for mac in data['devices']:
            try:
                mac_clean = mac.strip().lower()
                queries = [
                    # Get device info from new_devices
                    ("""
                        SELECT hostname, vendor, device_type, last_ip, open_ports, notes
                        FROM new_devices
                        WHERE mac_address = %s::macaddr
                    """, (mac_clean,)),
                    
                    # Insert into known_devices
                    ("""
                        INSERT INTO known_devices (
                            mac_address, hostname, vendor, device_type, 
                            last_ip, first_seen, last_seen, risk_level,
                            notes, open_ports
                        )
                        SELECT 
                            mac_address, hostname, vendor, device_type,
                            last_ip, first_seen, last_seen, 
                            %s as risk_level,
                            COALESCE(%s, notes) as notes,
                            open_ports
                        FROM new_devices
                        WHERE mac_address = %s::macaddr
                    """, (
                        request.json.get('risk_level', 'medium'),
                        request.json.get('notes'),
                        mac_clean
                    )),
                    
                    # Delete from new_devices
                    ("""
                        DELETE FROM new_devices 
                        WHERE mac_address = %s::macaddr
                    """, (mac_clean,))
                ]
                
                result = Database.execute_transaction(queries)
                if result:
                    approved += 1
                    logger.info(f"Device {mac_clean} approved successfully")
                
            except Exception as e:
                logger.error(f"Error approving device {mac}: {str(e)}")
                continue

        if approved > 0:
            return jsonify({
                'success': True,
                'message': f'Successfully approved {approved} devices'
            })
        else:
            return jsonify({
                'error': 'No devices were approved. Please check the logs.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in approve_devices: {str(e)}")
        return jsonify({'error': str(e)}), 500

@review.route('/review/block', methods=['POST'])
def block_devices():
    """Block selected devices and move them to unknown devices."""
    try:
        data = request.json
        if not data or 'devices' not in data:
            return jsonify({'error': 'No devices specified'}), 400

        blocked = 0
        for mac in data['devices']:
            try:
                mac_clean = mac.strip().lower()
                queries = [
                    # Move device to unknown_devices
                    ("""
                        INSERT INTO unknown_devices (
                            mac_address, hostname, vendor, device_type,
                            last_ip, first_seen, last_seen,
                            notes, status, open_ports
                        )
                        SELECT 
                            mac_address, hostname, vendor, device_type,
                            last_ip, first_seen, last_seen,
                            COALESCE(%s, notes) as notes,
                            'blocked' as status,
                            open_ports
                        FROM new_devices
                        WHERE mac_address = %s::macaddr
                        ON CONFLICT (mac_address) DO UPDATE
                        SET last_ip = EXCLUDED.last_ip,
                            last_seen = EXCLUDED.last_seen,
                            notes = COALESCE(EXCLUDED.notes, unknown_devices.notes),
                            status = 'blocked'
                    """, (data.get('notes'), mac_clean)),
                    
                    # Remove from new_devices
                    ("""
                        DELETE FROM new_devices 
                        WHERE mac_address = %s::macaddr
                    """, (mac_clean,))
                ]
                
                result = Database.execute_transaction(queries)
                if result:
                    blocked += 1
                    logger.info(f"Device {mac_clean} blocked successfully")
                
            except Exception as e:
                logger.error(f"Error blocking device {mac}: {str(e)}")
                continue

        if blocked > 0:
            return jsonify({
                'success': True,
                'message': f'Successfully blocked {blocked} devices'
            })
        else:
            return jsonify({
                'error': 'No devices were blocked. Please check the logs.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in block_devices: {str(e)}")
        return jsonify({'error': str(e)}), 500
