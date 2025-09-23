import logging
from flask import Blueprint, render_template, request, jsonify, flash
from ..models.database import Database
from ..alerts.notifier import Notifier

# Initialize logger
logger = logging.getLogger(__name__)

review = Blueprint('review', __name__)

@review.route('/review')
def review_page():
    """Display the review page for new devices."""
    try:
        # Get new devices pending review
        new_devices = Database.execute_query("""
            SELECT 
                mac_address,
                hostname,
                last_ip,
                first_seen,
                last_seen,
                vendor,
                device_type,
                notes
            FROM new_devices 
            WHERE reviewed = FALSE
            ORDER BY first_seen DESC
        """)
        
        return render_template('review.html', devices=new_devices or [])
        
    except Exception as e:
        logger.error(f"Error loading review page: {str(e)}")
        flash("Error loading review page", "error")
        return render_template('review.html', devices=[])

@review.route('/review/approve', methods=['POST'])
def approve_devices():
    """Approve selected devices and move them to known devices."""
    try:
        data = request.json
        if not data or 'devices' not in data:
            return jsonify({'error': 'No devices specified'}), 400

        approved = 0
        approved_devices = []

        logger.info(f"Attempting to approve devices: {data['devices']}")

        for mac in data['devices']:
            try:
                mac_clean = mac.strip().lower()
                
                # Get device details for notification
                device_info = Database.execute_query("""
                    SELECT hostname, vendor, device_type, last_ip 
                    FROM new_devices 
                    WHERE mac_address = %s::macaddr
                """, (mac_clean,))

                # Move device to known_devices
                result = Database.execute_transaction([
                    ("""
                        INSERT INTO known_devices (
                            mac_address, hostname, vendor, last_ip, 
                            first_seen, last_seen, notes
                        )
                        SELECT 
                            mac_address, hostname, vendor, last_ip,
                            first_seen, last_seen, %s as notes
                        FROM new_devices
                        WHERE mac_address = %s::macaddr
                        ON CONFLICT (mac_address) DO UPDATE
                        SET last_ip = EXCLUDED.last_ip,
                            last_seen = EXCLUDED.last_seen,
                            notes = COALESCE(EXCLUDED.notes, known_devices.notes)
                    """, (data.get('notes'), mac_clean)),
                    
                    ("""
                        DELETE FROM new_devices 
                        WHERE mac_address = %s::macaddr
                    """, (mac_clean,))
                ])

                if result:
                    approved += 1
                    logger.info(f"Device {mac_clean} approved successfully")
                    if device_info:
                        device_detail = device_info[0]
                        approved_devices.append({
                            'name': device_detail['hostname'] or 'Unknown device',
                            'mac': mac_clean,
                            'ip': device_detail['last_ip'],
                            'vendor': device_detail['vendor']
                        })
                
            except Exception as e:
                logger.error(f"Error approving device {mac}: {str(e)}")
                continue

        # Send notifications about approved devices
        if approved > 0:
            try:
                notifier = Notifier()
                message = "The following devices have been approved:\n\n"
                for device in approved_devices:
                    message += f"• {device['name']} ({device['mac']})\n"
                    message += f"  IP: {device['ip']}\n"
                    message += f"  Vendor: {device['vendor']}\n\n"
                
                notifier.send_notification(
                    subject="Devices Approved",
                    message=message,
                    notification_type="info"
                )
                logger.info(f"Approval notifications sent for {approved} devices")
            except Exception as e:
                logger.error(f"Error sending notifications: {str(e)}")

        return jsonify({
            'success': True,
            'message': f'Successfully approved {approved} devices'
        })
            
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
        blocked_devices = []
        notification_error = None

        for mac in data['devices']:
            try:
                mac_clean = mac.strip().lower()
                
                # First get device details for notification
                device_info = Database.execute_query("""
                    SELECT hostname, vendor, device_type, last_ip 
                    FROM new_devices 
                    WHERE mac_address = %s::macaddr
                """, (mac_clean,))
                
                queries = [
                    # Move device to unknown_devices with proper JSONB casting
                    ("""
                        INSERT INTO unknown_devices (
                            mac_address, hostname, vendor, device_type,
                            last_ip, first_seen, last_seen,
                            notes, status, open_ports, threat_level
                        )
                        SELECT 
                            mac_address, hostname, vendor, device_type,
                            last_ip, first_seen, last_seen,
                            COALESCE(%s, notes) as notes,
                            'blocked'::text as status,
                            CASE 
                                WHEN open_ports IS NULL THEN '[]'::jsonb
                                WHEN open_ports::text = '' THEN '[]'::jsonb
                                ELSE open_ports::jsonb
                            END as open_ports,
                            %s::text as threat_level
                        FROM new_devices
                        WHERE mac_address = %s::macaddr
                        ON CONFLICT (mac_address) DO UPDATE
                        SET last_ip = EXCLUDED.last_ip,
                            last_seen = EXCLUDED.last_seen,
                            notes = COALESCE(EXCLUDED.notes, unknown_devices.notes),
                            status = 'blocked'::text,
                            threat_level = EXCLUDED.threat_level
                    """, (data.get('notes'), data.get('risk_level', 'medium'), mac_clean)),
                    
                    # Remove from new_devices
                    ("""
                        DELETE FROM new_devices 
                        WHERE mac_address = %s::macaddr
                    """, (mac_clean,))
                ]
                
                result = Database.execute_transaction(queries)
                if result:
                    blocked += 1
                    if device_info:
                        device_detail = device_info[0]
                        blocked_devices.append({
                            'name': device_detail['hostname'] or 'Unknown device',
                            'mac': mac_clean,
                            'ip': device_detail['last_ip'],
                            'vendor': device_detail['vendor']
                        })
                    logger.info(f"Device {mac_clean} blocked successfully")
                
            except Exception as e:
                logger.error(f"Error blocking device {mac}: {str(e)}")
                continue

        if blocked > 0:
            # Send notification about blocked devices
            try:
                notifier = Notifier()
                message = "The following devices have been blocked:\n\n"
                for device in blocked_devices:
                    message += f"• {device['name']} ({device['mac']})\n"
                    message += f"  IP: {device['ip']}\n"
                    message += f"  Vendor: {device['vendor']}\n\n"
                
                notifier.send_notification(
                    subject="Devices Blocked",
                    message=message,
                    notification_type="warning"
                )
            except Exception as e:
                logger.warning(f"Failed to send block notification: {str(e)}")
                notification_error = str(e)

            return jsonify({
                'success': True,
                'message': f'Successfully blocked {blocked} devices',
                'devices': blocked_devices,
                'notification_error': notification_error
            })
        else:
            return jsonify({
                'error': 'No devices were blocked. Please check the logs.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in block_devices: {str(e)}")
        return jsonify({'error': str(e)}), 500

@review.route('/review/test-notifications')
def test_notifications():
    """Test notification settings."""
    try:
        notifier = Notifier()
        status = notifier.test_notification_settings()
        
        # Try sending a test message if settings are configured
        if (status['telegram']['configured'] or status['email']['configured']):
            try:
                notifier.send_notification(
                    "Test Notification",
                    "This is a test notification from NetGuard.",
                    "info"
                )
                status['test_message'] = 'Test message sent successfully'
            except Exception as e:
                status['test_message'] = f'Error sending test message: {str(e)}'
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
