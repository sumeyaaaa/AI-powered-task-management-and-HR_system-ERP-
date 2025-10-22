import streamlit as st
from auth import AuthManager, initialize_auth
import streamlit as st
import os
import requests
import pandas as pd
from datetime import datetime
from config import config
from auth import AuthManager, initialize_auth, require_auth
from task_management import show_task_management
from auth import initialize_auth
from notification_management import show_notifications_page, show_notification_badge

# Initialize authentication at the very beginning
initialize_auth()
# Page configuration
st.set_page_config(
    page_title="LeanChem ERP System",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Initialize authentication
    initialize_auth()
    
    # Initialize page state
    if 'page' not in st.session_state:
        st.session_state.page = "Home"
    
    # Initialize task selection state
    if 'selected_task_id' not in st.session_state:
        st.session_state.selected_task_id = None
    
    # Initialize force refresh state
    if 'force_task_refresh' not in st.session_state:
        st.session_state.force_task_refresh = False
    
    # Sidebar logo and info
   # Build the full path to the image
    image_path = os.path.join(os.path.dirname(__file__), "..", "image", "photo_2025-09-25_16-18-26.jpg")

    # Display in sidebar
    st.sidebar.image(image_path, width=150)
    st.sidebar.markdown("---")
    
    # Show appropriate page based on authentication and role
    if not st.session_state.get('authenticated'):
        show_public_pages()
    else:
        show_authenticated_interface()

def show_public_pages():
    """Show pages for non-authenticated users"""
    if st.session_state.page == "Home":
        show_home_page()
    elif st.session_state.page == "Login":
        show_login_page()

def show_authenticated_interface():
    """Show appropriate interface based on user role"""
    auth_manager = AuthManager()
    
    # Sidebar user info
    user_data = st.session_state.get('user_data', {})
    st.sidebar.write(f"👋 Welcome, **{user_data.get('name', 'User')}**")
    st.sidebar.write(f"**Role:** {user_data.get('role', 'Employee').title()}")
    st.sidebar.write(f"**Email:** {user_data.get('email', '')}")
    st.sidebar.markdown("---")
    
    # Role-based navigation
    if auth_manager.is_admin():
        show_admin_interface()
    else:
        show_employee_interface()

# Update the admin interface
def show_admin_interface():
    """Admin dashboard and navigation"""
    st.sidebar.title("Admin Navigation")
    
    # Define pages
    pages = ["Dashboard", "Employee Management", "Task Management", "Notifications", "Logout"]
    
    # Check if we're navigating from a notification with a specific task
    if st.session_state.get('selected_task_id'):
        # Force selection to Task Management when we have a selected task
        st.session_state.page = "Task Management"
    
    # Create radio buttons for navigation
    page = st.sidebar.radio("Go to", pages, index=pages.index(st.session_state.page) if st.session_state.page in pages else 0)
    
    # Update session state
    st.session_state.page = page
    
    # Show the selected page
    if page == "Dashboard":
        show_admin_dashboard()
    elif page == "Employee Management":
        show_employee_management()
    elif page == "Task Management": 
        show_task_management_with_navigation()
    elif page == "Notifications":
        show_notifications_page()
    elif page == "Logout":
        auth_manager = AuthManager()
        auth_manager.logout()
        st.session_state.page = "Home"
        st.rerun()

# Update the employee interface
def show_employee_interface():
    """Employee dashboard and navigation"""
    st.sidebar.title("Employee Navigation")
    
    # Define pages
    pages = ["My Profile", "Task Management", "Notifications", "Change Password", "Logout"]
    
    # Check if we're navigating from a notification with a specific task
    if st.session_state.get('selected_task_id'):
        # Force selection to Task Management when we have a selected task
        st.session_state.page = "Task Management"
    
    # Create radio buttons for navigation
    page = st.sidebar.radio("Go to", pages, index=pages.index(st.session_state.page) if st.session_state.page in pages else 0)
    
    # Update session state
    st.session_state.page = page
    
    # Show the selected page
    if page == "My Profile":
        show_employee_profile()
    elif page == "Task Management":
        show_task_management_with_navigation()
    elif page == "Notifications":
        show_notifications_page()
    elif page == "Change Password":
        show_change_password()
    elif page == "Logout":
        auth_manager = AuthManager()
        auth_manager.logout()
        st.session_state.page = "Home"
        st.rerun()

def show_task_management_with_navigation():
    """Enhanced task management that handles navigation from notifications"""
    
    # Check if we're navigating from a notification with a specific task
    selected_task_id = st.session_state.get('selected_task_id')
    if selected_task_id:
        st.success(f"🔍 Navigated to task: {selected_task_id}")
        
        # You can add additional logic here to automatically expand or highlight the task
        # For example, you might want to store this ID and use it in the task management component
        # to automatically expand the relevant task
        
        # Clear the selection after showing the message (optional)
        # del st.session_state.selected_task_id
    
    # Show the main task management interface
    show_task_management()
    
    # Clear the force refresh flag after loading
    if st.session_state.get('force_task_refresh'):
        st.session_state.force_task_refresh = False

def show_home_page():
    """Public home page"""
    st.title("🏢 Welcome to LeanChem ERP System")
    st.markdown("""
    ## Unified Business Management Platform
    
    This system provides comprehensive management tools for your organization:
    
    ### For Administrators:
    - 👥 Complete employee management
    - 📊 Business analytics and reporting
    - ⚙️ System configuration
    
    ### For Employees:
    - 👤 Personal profile management
    - 🔐 Secure password management
    - 📋 Access to company resources
    
    ### Getting Started:
    Use the login button below to access your account.
    """)
    
    if st.button("🔐 Login to System", type="primary", use_container_width=True):
        st.session_state.page = "Login"
        st.rerun()

def show_login_page():
    """Unified login page for both admin and employees"""
    st.title("🔐 System Login")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info("**Login Credentials:**\n- **Admins:** Use your admin credentials\n- **Employees:** Use your company email and password")
        
        with st.form("login_form"):
            email = st.text_input("📧 Email Address", placeholder="your.email@company.com")
            password = st.text_input("🔑 Password", type="password")
            login_btn = st.form_submit_button("🚀 Login to System", use_container_width=True)
        
        if login_btn:
            if not email or not password:
                st.error("Please enter both email and password")
            else:
                auth_manager = AuthManager()
                if auth_manager.login(email, password):
                    user_role = st.session_state.get('user_role', 'employee')
                    st.success(f"✅ Login successful! Welcome {user_role.title()}!")
                    st.balloons()
                    st.session_state.page = "Dashboard"
                    st.rerun()
        
        st.markdown("---")
        if st.button("← Back to Home"):
            st.session_state.page = "Home"
            st.rerun()

# ADMIN PAGES
@require_auth('superadmin')
def show_admin_dashboard():
    """Admin dashboard"""
    st.title("📊 Admin Dashboard")
    st.write(f"Welcome back, **System Administrator**!")
    
    # Quick stats
    auth_manager = AuthManager()
    employees = auth_manager.get_profile() or []
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_employees = len(employees)
        st.metric("Total Employees", total_employees)
    
    with col2:
        active_employees = len([e for e in employees if e.get('is_active', True)])
        st.metric("Active Employees", active_employees)
    
    with col3:
        departments = len(set(e.get('department', '') for e in employees if e.get('department')))
        st.metric("Departments", departments)
    
    with col4:
        # Fix: Handle None values in experience_years
        experience_values = [e.get('experience_years', 0) or 0 for e in employees]
        avg_experience = sum(experience_values) / max(total_employees, 1)
        st.metric("Avg Experience", f"{avg_experience:.1f} years")
    
    # Recent activity
    st.subheader("📈 Recent Activity")
    if employees:
        recent_employees = sorted(employees, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
        
        for emp in recent_employees:
            status = "🟢" if emp.get('is_active', True) else "🔴"
            st.write(f"{status} **{emp.get('name', 'Unknown')}** - {emp.get('role', 'No role')} - *{emp.get('created_at', '')[:10]}*")
    else:
        st.info("No employees found in the system.")

@require_auth('superadmin')
def show_employee_management():
    """Employee management page (admin only)"""
    st.title("👥 Employee Management")
    
    # Import employee management components
    from employee_management import show_employee_management as show_emp_mgmt
    show_emp_mgmt()

@require_auth('superadmin')
def show_system_settings():
    """System settings page (admin only)"""
    st.title("⚙️ System Settings")
    st.info("System configuration and administration tools")
    
    tab1, tab2, tab3 = st.tabs(["User Management", "Security", "Backup"])
    
    with tab1:
        st.subheader("User Management")
        st.write("Administrator tools for user management")
        
    with tab2:
        st.subheader("Security Settings")
        st.write("System security configuration")
        
    with tab3:
        st.subheader("Backup & Restore")
        st.write("Data backup and restoration tools")

@require_auth('employee')
def show_employee_profile():
    """Employee profile page with photo upload at the bottom"""
    st.title("👤 My Employee Profile")
    
    auth_manager = AuthManager()
    employee = auth_manager.get_profile()
    
    if not employee:
        st.error("Failed to load your profile. Please try again.")
        return
    
    # Display profile information first (without photo upload section)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader(employee.get('name', 'Employee'))
        
        # Display current photo only (no upload controls here)
        photo_url = employee.get('photo_url')
        if photo_url:
            st.image(photo_url, width=150, caption="Your Photo")
        else:
            st.image("https://via.placeholder.com/150x150.png?text=No+Photo", 
                    width=150, caption="No Photo Available")
        
        st.markdown("---")
        st.write(f"**Email:** {employee.get('email', 'Not provided')}")
        st.write(f"**Role:** {employee.get('role', 'Not specified')}")
        st.write(f"**Department:** {employee.get('department', 'Not specified')}")
        st.write(f"**Title:** {employee.get('title', 'Not specified')}")
        st.write(f"**Location:** {employee.get('location', 'Not specified')}")
        st.write(f"**Experience:** {employee.get('experience_years', 0)} years")
        
        if employee.get('linkedin_url'):
            st.markdown(f"**LinkedIn:** [View Profile]({employee['linkedin_url']})")
        
        st.write(f"**Status:** {'🟢 Active' if employee.get('is_active', True) else '🔴 Inactive'}")

    with col2:
        st.markdown("### Professional Details")
        
        st.markdown("#### Bio")
        bio = employee.get('bio', 'No bio provided yet.')
        st.info(bio if bio else 'No bio provided yet.')
        
        st.markdown("#### 🛠️ Skills")
        skills = employee.get('skills', [])
        if skills:
            for skill in skills:
                st.markdown(f"- {skill}")
        else:
            st.write("No skills listed yet.")
        
        st.markdown("#### 💪 Strengths")
        strengths = employee.get('strengths', [])
        if strengths:
            for strength in strengths:
                st.markdown(f"- {strength}")
        else:
            st.write("No strengths listed yet.")
        
        st.markdown("#### 📈 Area of Development")
        development_area = employee.get('area_of_development', '')
        if development_area:
            st.info(development_area)
        else:
            st.write("No development area specified.")
    
    # Employment details
    st.markdown("---")
    st.markdown("### Employment Details")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"**Employee Since:** {employee.get('created_at', 'Unknown')[:10]}")
    with col2:
        st.write(f"**Last Updated:** {employee.get('updated_at', 'Unknown')[:10]}")
    with col3:
        st.write(f"**Employee ID:** `{employee.get('id', 'Unknown')}`")
    
    # Photo upload section moved to the bottom
    st.markdown("---")
    st.markdown("## 📷 Profile Photo Management")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Show current photo again for context
        photo_url = employee.get('photo_url')
        if photo_url:
            st.image(photo_url, width=200, caption="Current Photo")
        else:
            st.image("https://via.placeholder.com/200x200.png?text=No+Photo", 
                    width=200, caption="No Photo Available")
    
    with col2:
        st.markdown("### Update Your Profile Photo")
        
        uploaded_file = st.file_uploader(
            "Choose a new photo", 
            type=['png', 'jpg', 'jpeg', 'gif', 'webp'],
            key="photo_uploader",
            help="Supported formats: PNG, JPG, JPEG, GIF, WebP (max 5MB)"
        )
        
        if uploaded_file is not None:
            # Show preview
            st.image(uploaded_file, width=150, caption="Preview")
            
            # Check file size (5MB limit)
            if uploaded_file.size > 5 * 1024 * 1024:
                st.error("❌ File too large. Maximum size is 5MB.")
            else:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("📤 Upload New Photo", type="primary", use_container_width=True):
                        with st.spinner("Uploading photo..."):
                            result = upload_employee_photo_frontend(employee['id'], uploaded_file)
                        if result['success']:
                            st.success("✅ Photo uploaded successfully!")
                            st.balloons()
                            st.rerun()
                        else:
                            error_msg = result.get('error', 'Unknown error occurred')
                            st.error(f"❌ Failed to upload photo: {error_msg}")
                            # Show debug info for admins
                            if st.session_state.get('user_role') == 'superadmin':
                                st.warning(f"Debug info: {result}")
                
                with col_btn2:
                    if st.button("🔄 Cancel Upload", use_container_width=True):
                        st.rerun()
        
        # Remove photo button if photo exists
        if photo_url:
            st.markdown("---")
            st.markdown("### Remove Current Photo")
            if st.button("🗑️ Remove Photo", type="secondary"):
                with st.spinner("Removing photo..."):
                    result = remove_employee_photo_frontend(employee['id'])
                if result['success']:
                    st.success("✅ Photo removed successfully!")
                    st.rerun()
                else:
                    error_msg = result.get('error', 'Unknown error occurred')
                    st.error(f"❌ Failed to remove photo: {error_msg}")
        
        st.info("""
        **Photo Guidelines:**
        - Maximum file size: 5MB
        - Supported formats: PNG, JPG, JPEG, GIF, WebP
        - Recommended: Square images work best
        - For best results: Use a clear headshot
        """)

def upload_employee_photo_frontend(employee_id, uploaded_file):
    """Frontend function to upload employee photo with better error handling"""
    try:
        # Get the token from session state
        token = st.session_state.get('token')
        if not token:
            return {'success': False, 'error': 'Authentication token not found'}
        
        # Prepare the request
        url = f"{config.BACKEND_URL}/api/employees/{employee_id}/upload-photo"
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        # Prepare file data
        files = {
            'photo': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
        }
        
        # Send the request with timeout
        response = requests.post(url, headers=headers, files=files, timeout=30)
        
        # Debug logging
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            try:
                error_detail = response.json()
                return {'success': False, 'error': f"Server error {response.status_code}: {error_detail.get('error', 'Unknown error')}"}
            except:
                return {'success': False, 'error': f"HTTP error {response.status_code}: {response.text}"}
            
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'Cannot connect to backend server. Please ensure the backend is running.'}
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Upload request timed out. Please try again.'}
    except Exception as e:
        print(f"Error uploading photo: {e}")
        return {'success': False, 'error': f'Upload failed: {str(e)}'}

def remove_employee_photo_frontend(employee_id):
    """Frontend function to remove employee photo with better error handling"""
    try:
        # Get the token from session state
        token = st.session_state.get('token')
        if not token:
            return {'success': False, 'error': 'Authentication token not found'}
        
        # Prepare the request
        url = f"{config.BACKEND_URL}/api/employees/{employee_id}/remove-photo"
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        # Send the request with timeout
        response = requests.delete(url, headers=headers, timeout=15)
        
        # Debug logging
        print(f"Remove response status: {response.status_code}")
        print(f"Remove response text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            try:
                error_detail = response.json()
                return {'success': False, 'error': f"Server error {response.status_code}: {error_detail.get('error', 'Unknown error')}"}
            except:
                return {'success': False, 'error': f"HTTP error {response.status_code}: {response.text}"}
            
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'Cannot connect to backend server. Please ensure the backend is running.'}
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Remove request timed out. Please try again.'}
    except Exception as e:
        print(f"Error removing photo: {e}")
        return {'success': False, 'error': f'Remove failed: {str(e)}'}

@require_auth()
def show_change_password():
    """Change password page (for both admin and employees)"""
    st.title("🔐 Change Password")
    st.markdown("---")
    
    user_data = st.session_state.get('user_data', {})
    user_role = user_data.get('role', 'employee').title()
    
    st.warning(f"""
    **Password Requirements for {user_role}:**
    - Minimum 8 characters
    - Include letters and numbers
    - Avoid using easily guessable information
    """)
    
    with st.form("change_password_form"):
        st.subheader("Update Your Password")
        
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        submitted = st.form_submit_button("🔄 Update Password")
        
        if submitted:
            if not current_password or not new_password or not confirm_password:
                st.error("Please fill in all password fields")
            elif new_password != confirm_password:
                st.error("New passwords do not match")
            elif len(new_password) < 8:
                st.error("New password must be at least 8 characters long")
            elif new_password == current_password:
                st.error("New password must be different from current password")
            else:
                auth_manager = AuthManager()
                with st.spinner("Updating password..."):
                    success = auth_manager.change_password(current_password, new_password)
                
                if success:
                    st.success("✅ Password updated successfully!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Failed to update password. Please check your current password.")

if __name__ == "__main__":
    main()