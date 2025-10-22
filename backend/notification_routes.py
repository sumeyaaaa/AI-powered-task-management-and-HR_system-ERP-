from flask import Blueprint, request, jsonify, g, current_app
import os
from datetime import datetime
from supabase import create_client
import traceback
import jwt
from functools import wraps

# Create the main notifications blueprint
notification_bp = Blueprint('notifications', __name__)

def get_supabase_client():
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not supabase_url or not supabase_key:
            raise Exception("Supabase credentials not configured")
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"❌ get_supabase_client ERROR: {str(e)}")
        raise

def notifications_token_required(f):
    """Custom token decorator specifically for notifications that allows admin without employee_id"""
    @wraps(f)
    def decorated(*args, **kwargs):
        print(f"🔐 NOTIFICATIONS TOKEN CHECK for {f.__name__}")
        
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # Store user data in g
            g.user = data
            
            user_role = data.get('role')
            employee_id = data.get('employee_id')
            
            print(f"🔐 Notifications token - role: {user_role}, employee_id: {employee_id}")
            print(f"✅ NOTIFICATIONS ACCESS GRANTED to {user_role}")
            
            return f(*args, **kwargs)
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        except Exception as e:
            print(f"❌ Token validation error: {str(e)}")
            return jsonify({'error': 'Token validation failed'}), 401
        
    return decorated

def get_user_notification_target():
    """Get notification target for current user"""
    try:
        if not hasattr(g, 'user') or not g.user:
            return None
        
        user_role = g.user.get('role')
        employee_id = g.user.get('employee_id')
        
        # Admin users see all notifications
        if user_role in ['admin', 'superadmin']:
            return "admin"
        
        # Employee users need employee_id
        if employee_id:
            return str(employee_id)
        
        return None
        
    except Exception as e:
        print(f"❌ get_user_notification_target ERROR: {str(e)}")
        return None


def create_enhanced_task_notification(task_id, notification_type, message, assigned_by=None, note_preview=None, attached_to=None, attached_to_multiple=None):
    """Enhanced notification function that handles employee attachments with added_by field"""
    try:
        supabase = get_supabase_client()
        
        # Get task details
        task_result = supabase.table("action_plans").select("task_description, assigned_to, assigned_to_multiple").eq("id", task_id).execute()
        if not task_result.data:
            return
        
        task = task_result.data[0]
        
        # Get admin employee ID
        admin_employee_id = get_admin_employee_id()
        
        # Get current user's name for added_by field
        current_user_name = "Unknown"
        if hasattr(g, 'user') and g.user:
            user_employee_id = g.user.get('employee_id')
            if user_employee_id:
                employee_result = supabase.table("employees").select("name").eq("id", user_employee_id).execute()
                if employee_result.data:
                    current_user_name = employee_result.data[0].get('name', 'Unknown')
            else:
                current_user_name = g.user.get('name', 'Unknown')
        
        # Determine recipients based on notification type
        recipients = set()
        
        if notification_type in ["task_assigned", "task_updated", "note_added", "file_uploaded"]:
            # For note_added with attachments, prioritize attached employees
            if notification_type == "note_added" and (attached_to or attached_to_multiple):
                if attached_to:
                    recipients.add(attached_to)
                if attached_to_multiple:
                    recipients.update(attached_to_multiple)
                
                # Also notify admin if employee added the note
                current_user_role = g.user.get('role') if hasattr(g, 'user') and g.user else None
                if current_user_role == 'employee' and admin_employee_id:
                    recipients.add(admin_employee_id)
            else:
                # Default behavior for other notifications
                if task.get('assigned_to'):
                    recipients.add(task['assigned_to'])
                if task.get('assigned_to_multiple'):
                    recipients.update(task['assigned_to_multiple'])
                
                # If employee made the update, notify admin
                current_user_role = g.user.get('role') if hasattr(g, 'user') and g.user else None
                if current_user_role == 'employee' and admin_employee_id:
                    recipients.add(admin_employee_id)
        
        # Create notifications for all recipients
        for recipient in recipients:
            if recipient:  # Ensure recipient is not None
                notification_data = {
                    "to_employee": recipient,
                    "channel": "in_app",
                    "message": message,
                    "meta": {
                        "task_id": task_id,  # This is crucial for navigation
                        "task_description": task['task_description'][:100], 
                        "type": notification_type,
                        "assigned_by": assigned_by,
                        "added_by": current_user_name,
                        "note_preview": note_preview,
                        "specially_attached": True if attached_to or attached_to_multiple else False,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "priority": "normal",
                    "created_at": datetime.utcnow().isoformat(),
                    "is_read": False
                }
                supabase.table("notifications").insert(notification_data).execute()
                print(f"📨 Notification sent to {recipient}: {message} (added_by: {current_user_name})")
                
    except Exception as e:
        print(f"⚠️ Failed to create notification: {e}")

        
# ===== MAIN NOTIFICATIONS ENDPOINT - FIXED =====
@notification_bp.route('/api/notifications', methods=['GET'])
@notifications_token_required  # ← THIS IS THE KEY FIX
def get_notifications():
    """Get notifications for current user - FIXED VERSION"""
    try:
        print("🚀 MAIN NOTIFICATIONS ENDPOINT CALLED")
        
        supabase = get_supabase_client()
        user_target = get_user_notification_target()
        
        print(f"🎯 User target: {user_target}")
        print(f"🔍 g.user: {g.user}")
        
        if not user_target:
            return jsonify({
                'success': False, 
                'error': 'Could not identify user for notifications'
            }), 400
        
        # Admin sees all notifications, employees see only theirs
        if user_target == "admin":
            print("👑 Admin - fetching ALL notifications")
            result = supabase.table("notifications").select("*").order("created_at", desc=True).execute()
        else:
            print(f"👤 Employee - fetching notifications for: {user_target}")
            result = supabase.table("notifications").select("*").eq("to_employee", user_target).order("created_at", desc=True).execute()
        
        notifications = result.data if result.data else []
        unread_count = len([n for n in notifications if not n.get('is_read', False)])
        
        print(f"✅ SUCCESS - {len(notifications)} notifications, {unread_count} unread")
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'unread_count': unread_count,
            'total': len(notifications),
            'user_type': 'admin' if user_target == 'admin' else 'employee'
        })
        
    except Exception as e:
        print(f"❌ get_notifications ERROR: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== ALL OTHER ENDPOINTS =====
@notification_bp.route('/api/notifications/<notification_id>/read', methods=['PUT'])
@notifications_token_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        supabase = get_supabase_client()
        user_target = get_user_notification_target()
        
        if not user_target:
            return jsonify({'success': False, 'error': 'Could not identify user'}), 400
        
        if user_target == "admin":
            notification_result = supabase.table("notifications").select("*").eq("id", notification_id).execute()
        else:
            notification_result = supabase.table("notifications").select("*").eq("id", notification_id).eq("to_employee", user_target).execute()
        
        if not notification_result.data:
            return jsonify({'success': False, 'error': 'Notification not found or not authorized'}), 404
        
        update_data = {
            "is_read": True,
            "read_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("notifications").update(update_data).eq("id", notification_id).execute()
        
        if result.data:
            return jsonify({
                'success': True,
                'message': 'Notification marked as read',
                'notification': result.data[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update notification'}), 500
            
    except Exception as e:
        print(f"❌ mark_notification_read ERROR: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@notification_bp.route('/api/notifications/read-all', methods=['PUT'])
@notifications_token_required
def mark_all_notifications_read():
    """Mark all notifications as read for current user"""
    try:
        supabase = get_supabase_client()
        user_target = get_user_notification_target()
        
        if not user_target:
            return jsonify({'success': False, 'error': 'Could not identify user'}), 400
        
        update_data = {
            "is_read": True,
            "read_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if user_target == "admin":
            result = supabase.table("notifications").update(update_data).eq("is_read", False).execute()
        else:
            result = supabase.table("notifications").update(update_data).eq("to_employee", user_target).eq("is_read", False).execute()
        
        return jsonify({
            'success': True,
            'message': f'Marked {len(result.data) if result.data else 0} notifications as read'
        })
            
    except Exception as e:
        print(f"❌ mark_all_notifications_read ERROR: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@notification_bp.route('/api/notifications/count', methods=['GET'])
@notifications_token_required
def get_notification_count():
    """Get unread notification count for current user"""
    try:
        supabase = get_supabase_client()
        user_target = get_user_notification_target()
        
        if not user_target:
            return jsonify({'success': False, 'error': 'Could not identify user'}), 400
        
        if user_target == "admin":
            result = supabase.table("notifications").select("id", count="exact").eq("is_read", False).execute()
        else:
            result = supabase.table("notifications").select("id", count="exact").eq("to_employee", user_target).eq("is_read", False).execute()
        
        unread_count = result.count if hasattr(result, 'count') else 0
        
        return jsonify({
            'success': True,
            'unread_count': unread_count
        })
        
    except Exception as e:
        print(f"❌ get_notification_count ERROR: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@notification_bp.route('/api/notifications/<notification_id>', methods=['DELETE'])
@notifications_token_required
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        supabase = get_supabase_client()
        user_target = get_user_notification_target()
        
        if not user_target:
            return jsonify({'success': False, 'error': 'Could not identify user'}), 400
        
        if user_target == "admin":
            notification_result = supabase.table("notifications").select("*").eq("id", notification_id).execute()
        else:
            notification_result = supabase.table("notifications").select("*").eq("id", notification_id).eq("to_employee", user_target).execute()
        
        if not notification_result.data:
            return jsonify({'success': False, 'error': 'Notification not found or not authorized'}), 404
        
        result = supabase.table("notifications").delete().eq("id", notification_id).execute()
        
        if result.data:
            return jsonify({
                'success': True,
                'message': 'Notification deleted'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete notification'}), 500
            
    except Exception as e:
        print(f"❌ delete_notification ERROR: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== DEBUG ENDPOINTS =====
@notification_bp.route('/api/notifications/debug', methods=['GET'])
@notifications_token_required
def debug_notifications():
    """Debug endpoint for notifications"""
    user_target = get_user_notification_target()
    
    debug_info = {
        'g_user': getattr(g, 'user', 'Not set'),
        'user_target': user_target,
        'user_role': g.user.get('role') if hasattr(g, 'user') and g.user else 'No role',
        'user_email': g.user.get('email') if hasattr(g, 'user') and g.user else 'No email',
        'employee_id': g.user.get('employee_id') if hasattr(g, 'user') and g.user else 'No employee_id',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return jsonify({
        'success': True,
        'debug_info': debug_info
    })

@notification_bp.route('/api/notifications/test-g-user', methods=['GET'])
@notifications_token_required
def test_g_user():
    """Test g.user directly"""
    response = {
        'success': True,
        'g_user': getattr(g, 'user', 'Not set'),
        'g_user_keys': list(g.user.keys()) if hasattr(g, 'user') and g.user else 'No keys'
    }
    
    return jsonify(response)

@notification_bp.route('/api/notifications/test-query', methods=['GET'])
@notifications_token_required
def test_notifications_query():
    """Test the actual Supabase query"""
    try:
        supabase = get_supabase_client()
        
        admin_result = supabase.table("notifications").select("*").order("created_at", desc=True).execute()
        employee_result = supabase.table("notifications").select("*").eq("to_employee", "dummy").order("created_at", desc=True).execute()
        
        return jsonify({
            'success': True,
            'admin_query_count': len(admin_result.data) if admin_result.data else 0,
            'employee_query_count': len(employee_result.data) if employee_result.data else 0
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== NON-AUTH ENDPOINTS =====
@notification_bp.route('/api/notifications/health', methods=['GET'])
def notification_health_check():
    return jsonify({
        'success': True,
        'message': 'Notifications API is working',
        'timestamp': datetime.utcnow().isoformat()
    })

@notification_bp.route('/api/notifications/test-data', methods=['GET'])
def test_notifications_data():
    """Test if notifications table has data"""
    try:
        supabase = get_supabase_client()
        result = supabase.table("notifications").select("*").execute()
        
        return jsonify({
            'success': True,
            'notifications_count': len(result.data) if result.data else 0,
            'sample_data': result.data[:3] if result.data else []
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@notification_bp.route('/api/notifications/admin-test', methods=['GET'])
def admin_test_notifications():
    """Test endpoint for admin notifications without auth restrictions"""
    try:
        supabase = get_supabase_client()
        
        # Manually set admin user context
        g.user = {
            'email': 'admin@leanchem.com',
            'role': 'superadmin', 
            'employee_id': '6562d78f-de15-41ae-b88a-faf808c32a2a'
        }
        
        result = supabase.table("notifications").select("*").order("created_at", desc=True).execute()
        notifications = result.data if result.data else []
        unread_count = len([n for n in notifications if not n.get('is_read', False)])
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'unread_count': unread_count,
            'total': len(notifications)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500