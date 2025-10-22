import streamlit as st
import requests
from datetime import datetime
from config import config

class NotificationManager:
    def __init__(self, backend_url: str):
        self.backend_url = backend_url

    def get_auth_headers(self):
        """Get headers with authentication token"""
        if st.session_state.get('token'):
            return {'Authorization': f'Bearer {st.session_state.token}'}
        return {}

    def _safe_request(self, method, url, **kwargs):
        """Safe request handler"""
        try:
            headers = self.get_auth_headers()
            kwargs['headers'] = headers
            kwargs['timeout'] = 15
            
            response = method(url, **kwargs)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                error_data = response.json()
                return {
                    'success': False, 
                    'error': f'Bad request: {error_data.get("error", "Unknown error")}'
                }
            elif response.status_code == 401:
                return {'success': False, 'error': 'Authentication failed. Please log in again.'}
            elif response.status_code == 500:
                return {'success': False, 'error': 'Server error. Please try again later.'}
            else:
                return {'success': False, 'error': f'Request failed with status {response.status_code}'}
                
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Cannot connect to server. Please check your connection.'}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timed out. Please try again.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_notifications(self):
        """Get notifications for current user"""
        return self._safe_request(
            requests.get, 
            f"{self.backend_url}/api/notifications"
        )

    def get_notification_count(self):
        """Get unread notification count"""
        return self._safe_request(
            requests.get,
            f"{self.backend_url}/api/notifications/count"
        )

    def mark_notification_read(self, notification_id: str):
        return self._safe_request(
            requests.put,
            f"{self.backend_url}/api/notifications/{notification_id}/read"
        )

    def mark_all_notifications_read(self):
        return self._safe_request(
            requests.put,
            f"{self.backend_url}/api/notifications/read-all"
        )

    def delete_notification(self, notification_id: str):
        return self._safe_request(
            requests.delete,
            f"{self.backend_url}/api/notifications/{notification_id}"
        )

    # IMPROVEMENT: Add method to get task details
    def get_task_details(self, task_id: str):
        """Get task details for notification navigation"""
        return self._safe_request(
            requests.get,
            f"{self.backend_url}/api/tasks/{task_id}"
        )

@st.cache_data(ttl=300)
def get_notification_manager():
    return NotificationManager(config.BACKEND_URL)

def show_notifications_page():
    """Main notifications page for both admin and employee"""
    st.title("🔔 Notifications")
    
    # Check authentication first
    if not st.session_state.get('authenticated'):
        st.error("Please log in to view notifications")
        return
    
    notification_manager = get_notification_manager()
    
    # Debug section for admins (collapsed by default)
    if st.session_state.get('user_role') in ['admin', 'superadmin']:
        with st.expander("🔧 Debug Tools (Admin Only)", expanded=False):
            st.info("Use these tools to diagnose notification issues")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("Check Debug Info", use_container_width=True):
                    result = notification_manager.debug_notifications()
                    if result.get('success'):
                        st.success("✅ Debug endpoint working")
                        st.json(result.get('debug_info', {}))
                    else:
                        st.error(f"❌ Debug failed: {result.get('error')}")
            with col2:
                if st.button("Test Data", use_container_width=True):
                    result = notification_manager.test_notifications_data()
                    if result.get('success'):
                        count = result.get('notifications_count', 0)
                        st.success(f"✅ Data working - {count} notifications")
                    else:
                        st.error(f"❌ Data failed: {result.get('error')}")
            with col3:
                if st.button("Test g.user", use_container_width=True):
                    result = notification_manager.test_g_user()
                    if result.get('success'):
                        st.success("✅ g.user test working")
                        st.json(result)
                    else:
                        st.error(f"❌ g.user failed: {result.get('error')}")
            with col4:
                if st.button("Admin Test", use_container_width=True):
                    result = notification_manager.admin_test_notifications()
                    if result.get('success'):
                        count = result.get('total', 0)
                        unread = result.get('unread_count', 0)
                        st.success(f"✅ Admin test - {count} notifications, {unread} unread")
                    else:
                        st.error(f"❌ Admin test failed: {result.get('error')}")
    
    # Main notifications loading
    with st.spinner("Loading notifications..."):
        result = notification_manager.get_notifications()
    
    if not result.get('success'):
        error_msg = result.get('error', 'Unknown error')
        st.error(f"❌ Failed to load notifications: {error_msg}")
        
        if st.button("🔄 Retry", use_container_width=True):
            st.rerun()
        return
    
    notifications = result.get('notifications', [])
    unread_count = result.get('unread_count', 0)
    
    # Header with actions
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if unread_count > 0:
            st.subheader(f"📬 You have {unread_count} unread notification(s)")
        else:
            st.subheader("📭 All caught up!")
    
    with col2:
        if unread_count > 0 and st.button("📭 Mark All Read", use_container_width=True, type="primary"):
            mark_result = notification_manager.mark_all_notifications_read()
            if mark_result.get('success'):
                st.toast("✅ All notifications marked as read!")
                st.rerun()
            else:
                st.error(f"❌ Failed: {mark_result.get('error')}")
    
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    if not notifications:
        st.info("🎉 No notifications found. You're all caught up!")
        return
    
    # Display notifications
    for notification in notifications:
        show_notification_card(notification, notification_manager)

def show_notification_card(notification, task_manager):
    """Display a single notification card with task navigation and delete button"""
    with st.container():
        col1, col2, col3 = st.columns([4, 1, 1])
        
        with col1:
            # Make the notification message clickable for task navigation
            message = notification.get('message', 'No message')
            meta = notification.get('meta', {})
            task_id = meta.get('task_id')
            
            if task_id:
                # Create a clickable button that navigates to the task
                if st.button(
                    f"📋 {message}", 
                    key=f"nav_{notification['id']}",
                    use_container_width=True,
                    help=f"Click to view task: {meta.get('task_description', 'Unknown task')}"
                ):
                    # Store the task ID in session state to navigate to it
                    st.session_state['current_task_id'] = task_id
                    # Clear any existing notification navigation state
                    if 'current_task_id' in st.session_state:
                        del st.session_state['current_task_id']
                    st.session_state['current_task_id'] = task_id
                    st.success(f"🎯 Navigating to task...")
                    # Use switch_page for better navigation
                    try:
                        st.switch_page("task_management.py")
                    except:
                        st.rerun()
            else:
                # Non-task notification (just display the message)
                st.write(f"**{message}**")
            
            # Notification metadata
            if meta.get('task_description'):
                st.caption(f"Task: {meta['task_description']}")
            if meta.get('assigned_by'):
                st.caption(f"Assigned by: {meta['assigned_by']}")
            if meta.get('added_by'):
                st.caption(f"Added by: {meta['added_by']}")
            if meta.get('note_preview'):
                st.caption(f"Note: {meta['note_preview']}")
            
            # Timestamp
            created_at = notification.get('created_at', '')
            if created_at:
                try:
                    created_time = datetime.fromisoformat(created_at.replace('Z', ''))
                    time_ago = datetime.utcnow() - created_time
                    if time_ago.days > 0:
                        time_text = f"{time_ago.days}d ago"
                    elif time_ago.seconds > 3600:
                        time_text = f"{time_ago.seconds // 3600}h ago"
                    else:
                        time_text = f"{time_ago.seconds // 60}m ago"
                    st.caption(f"🕒 {time_text}")
                except:
                    st.caption(f"🕒 {created_at[:16]}")
        
        with col2:
            # Mark as read button for unread notifications
            if not notification.get('is_read', False):
                if st.button("✓ Read", key=f"read_{notification['id']}", use_container_width=True):
                    result = task_manager.mark_notification_read(notification['id'])
                    if result.get('success'):
                        st.toast("✅ Notification marked as read!", icon="✅")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to mark as read: {result.get('error')}")
            else:
                st.caption("✅ Read")
        
        with col3:
            # Delete notification button
            if st.button("🗑️", key=f"delete_{notification['id']}", use_container_width=True):
                result = task_manager.delete_notification(notification['id'])
                if result.get('success'):
                    st.toast("🗑️ Notification deleted!", icon="🗑️")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete: {result.get('error')}")
        
        st.markdown("---")

def show_notification_details(notification, notification_manager):
    """Show detailed notification information"""
    meta = notification.get('meta', {})
    created_at = notification.get('created_at', '')
    
    st.subheader("Detailed Information")
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Notification Details:**")
        st.write(f"**ID:** {notification.get('id')}")
        st.write(f"**Message:** {notification.get('message')}")
        st.write(f"**Type:** {meta.get('type', 'Unknown')}")
        st.write(f"**Priority:** {notification.get('priority', 'normal').title()}")
        st.write(f"**Channel:** {notification.get('channel', 'in_app')}")
        
        # IMPROVEMENT: Show who triggered the notification
        if meta.get('added_by'):
            st.write(f"**Triggered by:** {meta['added_by']}")
        elif meta.get('assigned_by'):
            st.write(f"**Assigned by:** {meta['assigned_by']}")
        
        if created_at:
            try:
                created_time = datetime.fromisoformat(created_at.replace('Z', ''))
                st.write(f"**Created:** {created_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            except:
                st.write(f"**Created:** {created_at}")
        
        if notification.get('read_at'):
            try:
                read_time = datetime.fromisoformat(notification['read_at'].replace('Z', ''))
                st.write(f"**Read:** {read_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            except:
                st.write(f"**Read:** {notification['read_at']}")
    
    with col2:
        st.write("**Task & Attachment Details:**")
        
        # Task information
        task_id = meta.get('task_id')
        if task_id:
            st.write(f"**Task ID:** `{task_id}`")
            
            # Quick task details button
            if st.button("🔄 Load Task Details", key=f"load_task_{notification['id']}"):
                with st.spinner("Loading task details..."):
                    task_result = notification_manager.get_task_details(task_id)
                
                if task_result.get('success'):
                    task = task_result.get('task', {})
                    st.success("✅ Task details loaded!")
                    st.write(f"**Description:** {task.get('task_description', 'N/A')}")
                    st.write(f"**Status:** {task.get('status', 'N/A').replace('_', ' ').title()}")
                    st.write(f"**Priority:** {task.get('priority', 'N/A').title()}")
                    
                    # Show assigned employee if available
                    if task.get('employees'):
                        emp = task['employees']
                        st.write(f"**Assigned To:** {emp.get('name', 'N/A')} ({emp.get('role', 'N/A')})")
                else:
                    st.error("❌ Unable to load task details")
        else:
            st.info("No task associated with this notification")
        
        # Enhanced attachment information
        if meta.get('attached_specifically'):
            st.success("🔔 **Special Attachment**")
            st.write("This notification was specifically attached to you")
        
        if meta.get('attached_to') or meta.get('attached_to_multiple'):
            st.write("**Attachment Targets:**")
            if meta.get('attached_to'):
                st.write(f"- Specifically attached to: {meta.get('attached_to')}")
            if meta.get('attached_to_multiple'):
                st.write(f"- Multiple attachments: {len(meta['attached_to_multiple'])} employees")
    
    # Show full note if available
    if meta.get('note_preview'):
        st.subheader("Full Note Content")
        st.info(meta.get('note_preview'))
    
    # Close detail view button
    if st.button("Close Details", key=f"close_{notification['id']}"):
        st.session_state[f"show_detail_{notification['id']}"] = False
        st.rerun()

def get_relative_time(timestamp):
    """Convert timestamp to relative time string"""
    try:
        if 'T' in timestamp:
            created_time = datetime.fromisoformat(timestamp.replace('Z', ''))
        else:
            created_time = datetime.fromisoformat(timestamp)
        
        now = datetime.utcnow()
        diff = now - created_time
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    except:
        return timestamp[:16]

def show_notification_badge():
    """Show notification badge in sidebar"""
    try:
        notification_manager = get_notification_manager()
        count_data = notification_manager.get_notification_count()
        
        if count_data.get('success'):
            unread_count = count_data.get('unread_count', 0)
            if unread_count > 0:
                st.sidebar.markdown(
                    f"🔔 **Notifications** • **{unread_count}** unread",
                    help=f"You have {unread_count} unread notifications"
                )
            else:
                st.sidebar.markdown("🔔 **Notifications**")
        else:
            st.sidebar.markdown("🔔 **Notifications**")
    except Exception as e:
        st.sidebar.markdown("🔔 **Notifications**")

def main():
    """Main function for testing the notifications page"""
    st.set_page_config(page_title="Notifications", page_icon="🔔", layout="wide")
    
    # Check authentication
    if not st.session_state.get('authenticated'):
        st.error("Please log in to view notifications")
        return
    
    show_notifications_page()

if __name__ == "__main__":
    main()