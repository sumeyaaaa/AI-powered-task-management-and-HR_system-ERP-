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

import os
from datetime import datetime, timedelta


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


def create_enhanced_task_notification(task_id, notification_type, message, assigned_by=None, note_preview=None, attached_to=None, attached_to_multiple=None, old_progress=None, new_progress=None):
    """CORRECTED notification function that properly includes attached employees for notes"""
    try:
        supabase = get_supabase_client()
        
        # Get task details
        task_result = supabase.table("action_plans").select("task_description, assigned_to, assigned_to_multiple").eq("id", task_id).execute()
        if not task_result.data:
            print(f"❌ Task {task_id} not found for notification")
            return
        
        task = task_result.data[0]
        
        # Get admin employees (including superadmin from environment)
        admin_employees = get_admin_employees()
        admin_employee_ids = [admin['id'] for admin in admin_employees]
        
        # Get current user's role and info
        current_user_role = g.user.get('role') if hasattr(g, 'user') and g.user else None
        current_user_employee_id = g.user.get('employee_id') if hasattr(g, 'user') and g.user else None
        current_user_name = "Unknown"
        
        if current_user_employee_id:
            employee_result = supabase.table("employees").select("name").eq("id", current_user_employee_id).execute()
            if employee_result.data:
                current_user_name = employee_result.data[0].get('name', 'Unknown')
        else:
            current_user_name = g.user.get('name', 'Unknown')

        print(f"🔍 Task {task_id} - Current user: {current_user_name} (role: {current_user_role})")

        # ========== CORRECTED NOTIFICATION LOGIC ==========
        recipients = set()
        
        # Get all assigned employees for the task
        assigned_employees = set()
        if task.get('assigned_to'):
            assigned_employees.add(task['assigned_to'])
        if task.get('assigned_to_multiple'):
            assigned_employees.update(task['assigned_to_multiple'])
        
        # Get attached employees from function parameters
        attached_employees = set()
        if attached_to:
            attached_employees.add(attached_to)
        if attached_to_multiple:
            attached_employees.update(attached_to_multiple)
        
        print(f"🔍 Assigned employees: {assigned_employees}")
        print(f"🔍 Attached employees: {attached_employees}")
        print(f"🔍 Notification type: {notification_type}")

        # ========== SEPARATE NOTIFICATION TYPES ==========
        
        # 1. PROGRESS UPDATES (Separate notification)
        if notification_type == "progress_updated":
            # Always notify the opposite side
            if current_user_role == 'employee':
                # Employee updates progress: Notify all admin users
                recipients.update(admin_employee_ids)
                print("📊 Employee progress update - notifying admins")
            elif current_user_role in ['admin', 'superadmin']:
                # Admin updates progress: Notify all assigned employees
                recipients.update(assigned_employees)
                print("📊 Admin progress update - notifying assigned employees")
            
            # Remove current user from recipients (no self-notifications)
            if current_user_employee_id and current_user_employee_id in recipients:
                recipients.remove(current_user_employee_id)
                
            # Create progress notification
            if recipients:
                progress_message = f"📊 Progress updated"
                if old_progress is not None and new_progress is not None:
                    progress_message = f"📊 Progress updated from {old_progress}% to {new_progress}% on task: {task['task_description'][:50]}..."
                elif new_progress is not None:
                    progress_message = f"📊 Progress updated to {new_progress}% on task: {task['task_description'][:50]}..."
                
                create_single_notification(
                    supabase, task_id, "progress_updated", progress_message, recipients,
                    task, current_user_name, current_user_role, None,  # No note preview for progress
                    attached_to, attached_to_multiple, is_note=False
                )
            
            # Return after progress notification - don't create additional notifications
            return

        # 2. NOTES & MESSAGES (Separate notification) - FIXED TO INCLUDE ATTACHED EMPLOYEES
        elif notification_type == "note_added":
            if current_user_role in ['admin', 'superadmin']:
                # Admin adds note: Notify all assigned employees + attached employees (excluding admin)
                recipients.update(assigned_employees)
                recipients.update(attached_employees)  # ADDED: Include attached employees
                print("📝 Admin added note - notifying assigned employees AND attached employees")
                
            elif current_user_role == 'employee':
                # Employee adds note: Notify all admin users + attached employees (excluding employee)
                recipients.update(admin_employee_ids)
                recipients.update(attached_employees)  # ADDED: Include attached employees
                print("📝 Employee added note - notifying admins AND attached employees")
            
            # Remove current user from recipients (no self-notifications)
            if current_user_employee_id and current_user_employee_id in recipients:
                recipients.remove(current_user_employee_id)
                
            # Create note notification
            if recipients:
                note_message = f"📝 Note added to task: {task['task_description'][:50]}..."
                create_single_notification(
                    supabase, task_id, "note_added", note_message, recipients,
                    task, current_user_name, current_user_role, note_preview,
                    attached_to, attached_to_multiple, is_note=True
                )
            return

        # 3. FILE UPLOADS & ATTACHMENTS
        elif notification_type == "file_uploaded":
            if current_user_role in ['admin', 'superadmin']:
                # Admin uploads file: Notify all assigned employees + attached employees (excluding admin)
                recipients.update(assigned_employees)
                recipients.update(attached_employees)  # Include attached employees
                print("📎 Admin uploaded file - notifying assigned employees AND attached employees")
                
            elif current_user_role == 'employee':
                # Employee uploads file: Notify all admin users + attached employees (excluding employee)
                recipients.update(admin_employee_ids)
                recipients.update(attached_employees)  # Include attached employees
                print("📎 Employee uploaded file - notifying admins AND attached employees")
        
        # 4. TASK ASSIGNMENTS & UPDATES
        elif notification_type == "task_assigned":
            # Task assigned/created: Notify all assigned employees + attached employees (excluding assigner)
            recipients.update(assigned_employees)
            recipients.update(attached_employees)  # Include attached employees
            print("📋 Task assigned - notifying assigned employees AND attached employees")
            
        elif notification_type == "task_status_changed":
            # Task status changed: Notify opposite side + attached employees
            if current_user_role in ['admin', 'superadmin']:
                # Admin changed status: Notify assigned employees + attached employees
                recipients.update(assigned_employees)
                recipients.update(attached_employees)  # Include attached employees
            else:
                # Employee changed status: Notify admins + attached employees
                recipients.update(admin_employee_ids)
                recipients.update(attached_employees)  # Include attached employees
            print(f"🔄 Task status changed by {current_user_role} - notifying opposite side AND attached employees")
        
        elif notification_type == "task_updated":
            # General task updates: Notify opposite side + attached employees
            if current_user_role in ['admin', 'superadmin']:
                recipients.update(assigned_employees)
                recipients.update(attached_employees)  # Include attached employees
            else:
                recipients.update(admin_employee_ids)
                recipients.update(attached_employees)  # Include attached employees
            print(f"📝 Task updated by {current_user_role} - notifying opposite side AND attached employees")
        
        else:
            print(f"⚠️ Unknown notification type: {notification_type}")
            return

        # CRITICAL: Remove the current user from recipients for ALL notification types
        if current_user_employee_id and current_user_employee_id in recipients:
            recipients.remove(current_user_employee_id)

        print(f"🎯 Final recipients for {notification_type}: {recipients}")

        # Create notifications for non-progress/note types
        if recipients:
            # Format message based on notification type
            final_message = message
            if notification_type == "file_uploaded":
                final_message = f"📎 {message}"
            elif notification_type == "task_status_changed":
                final_message = f"🔄 {message}"
            elif notification_type == "task_assigned":
                final_message = f"📋 {message}"
            elif notification_type == "task_updated":
                final_message = f"✏️ {message}"
            
            # Create the notification
            create_single_notification(
                supabase, task_id, notification_type, final_message, recipients,
                task, current_user_name, current_user_role, note_preview,
                attached_to, attached_to_multiple, is_note=(notification_type == "note_added")
            )
        else:
            print("⚠️ No recipients to notify")
                
    except Exception as e:
        print(f"⚠️ Failed to create notification: {e}")
        traceback.print_exc()

def get_admin_employees():
    """Get all admin employee IDs, including superadmin from environment"""
    supabase = get_supabase_client()
    
    # First, get all admins and superadmins from the database
    result = supabase.table("employees").select("id, email, name, role").in_("role", ["admin", "superadmin"]).execute()
    
    admin_employees = []
    if result.data:
        admin_employees = result.data
    
    # If no admins found in database, use the superadmin from environment
    if not admin_employees:
        superadmin_email = os.getenv('SUPERADMIN_EMAIL')
        if superadmin_email:
            print(f"🔧 Using SUPERADMIN_EMAIL from environment: {superadmin_email}")
            # Create a placeholder admin employee using the superadmin email
            admin_employees = [{
                'id': 'superadmin-default',
                'email': superadmin_email,
                'name': 'System Superadmin',
                'role': 'superadmin'
            }]
    
    print(f"🔧 Admin employees found: {len(admin_employees)}")
    return admin_employees

def create_single_notification(supabase, task_id, notification_type, message, recipients, task, current_user_name, current_user_role, note_preview, attached_to, attached_to_multiple, is_note=False, assigned_by=None):
    """Helper function to create a single notification"""
    for recipient in recipients:
        if recipient:  # Ensure recipient is not None
            # DEDUPLICATION: Check for recent duplicate notification (last 2 minutes)
            duplicate_check = supabase.table("notifications").select("id").eq("meta->>task_id", task_id).eq("meta->>type", notification_type).eq("to_employee", recipient).gte("created_at", (datetime.utcnow() - timedelta(minutes=2)).isoformat()).execute()
            
            if duplicate_check.data:
                print(f"⏭️  Skipping duplicate notification for task {task_id}, type {notification_type}")
                continue

            # Remove double emoji formatting since it's already done in the calling function
            final_message = message

            notification_data = {
                "to_employee": recipient,
                "channel": "in_app",
                "message": final_message,
                "meta": {
                    "task_id": task_id,
                    "task_description": task['task_description'][:100], 
                    "type": notification_type,
                    "assigned_by": assigned_by,
                    "added_by": current_user_name,
                    "user_role": current_user_role,
                    "note_preview": note_preview if is_note else None,  # Only include note preview for note notifications
                    "specially_attached": True if attached_to or attached_to_multiple else False,
                    "attached_to": attached_to,
                    "attached_to_multiple": attached_to_multiple,
                    "timestamp": datetime.utcnow().isoformat(),
                    "is_note_notification": is_note,
                    "is_attachment_notification": not is_note and notification_type == "file_uploaded"
                },
                "priority": "normal",
                "created_at": datetime.utcnow().isoformat(),
                "is_read": False
            }
            
            try:
                result = supabase.table("notifications").insert(notification_data).execute()
                if result.data:
                    print(f"✅ Notification created for {recipient}: {final_message}")
                else:
                    print(f"❌ Failed to create notification for {recipient}")
            except Exception as e:
                print(f"❌ Error creating notification for {recipient}: {e}")
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
    
def get_notification_flow_debug():
    """Debug function to check notification flow"""
    current_user_role = g.user.get('role') if hasattr(g, 'user') and g.user else None
    current_user_employee_id = g.user.get('employee_id') if hasattr(g, 'user') and g.user else None
    
    return {
        'current_user_role': current_user_role,
        'current_user_employee_id': current_user_employee_id,
        'admin_employee_id': get_admin_employee_id(),
        'timestamp': datetime.utcnow().isoformat()
    }

@notification_bp.route('/api/notifications/debug-flow', methods=['GET'])
@notifications_token_required
def debug_notification_flow():
    """Debug notification flow"""
    return jsonify({
        'success': True,
        'flow_info': get_notification_flow_debug()
    })