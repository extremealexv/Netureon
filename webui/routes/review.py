import logging
from flask import Blueprint, render_template, request, flash, jsonify, current_app
from ..models.database import Database
from ..alerts.notifier import Notifier

review = Blueprint('review', __name__)
logger = logging.getLogger(__name__)

def notify_new_device(device_info):
    """Send notification about new device detection."""
    try:
        notifier = Notifier()
        
        # Prepare notification message
        device_name = device_info['hostname'] or 'Unknown device'
        message = f"New device detected:\n\n"
        message += f"• Name: {device_name}\n"
        message += f"• MAC: {device_info['mac_address']}\n"
        message += f"• IP: {device_info['last_ip']}\n"
        message += f"• Vendor: {device_info['vendor'] or 'Unknown'}\n"
        
        if device_info['open_ports'] and device_info['open_ports'] != '[]':
            message += f"• Open ports detected\n"
        
        # Send notification
        notifier.send_notification(
            subject="New Device Detected",
            message=message,
            notification_type="warning"
        )
        logger.info(f"New device notification sent for {device_info['mac_address']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send new device notification: {str(e)}")
        return False

@review.route('/review')
def review_page():
    """Display the review page with new devices."""
    try:
        # Get new devices and send notifications for each unnotified device
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
                END as open_ports,
                notification_sent
            FROM new_devices
            ORDER BY first_seen DESC
        """)

        # Send notifications for new unnotified devices
        if new_devices:
            for device in new_devices:
                if not device.get('notification_sent'):
                    if notify_new_device(device):
                        # Update notification status
                        Database.execute_query("""
                            UPDATE new_devices 
                            SET notification_sent = true 
                            WHERE mac_address = %s::macaddr
                        """, (device['mac_address'],))

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
        approved_devices = []

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
                            notes, status, open_ports
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
                            END as open_ports
                        FROM new_devices
                        WHERE mac_address = %s::macaddr
                        ON CONFLICT (mac_address) DO UPDATE
                        SET last_ip = EXCLUDED.last_ip,
                            last_seen = EXCLUDED.last_seen,
                            notes = COALESCE(EXCLUDED.notes, unknown_devices.notes),
                            status = 'blocked'::text
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
