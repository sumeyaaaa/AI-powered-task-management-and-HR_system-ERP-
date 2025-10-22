import streamlit as st
import requests
from config import config
import time

class AuthManager:
    def __init__(self):
        self.backend_url = config.BACKEND_URL
        self.token = None
        self.user_data = None

    def login(self, email: str, password: str) -> bool:
        """Unified login for both admin and employees"""
        try:
            response = requests.post(
                f"{self.backend_url}/api/auth/login",
                json={'email': email, 'password': password},
                timeout=10
            )
            
            print(f"Login response: {response.status_code} - {response.text}")  # Debug
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    self.token = data['token']
                    self.user_data = data.get('user', {})
                    
                    # Store in session state
                    st.session_state.token = self.token
                    st.session_state.user_data = self.user_data
                    st.session_state.authenticated = True
                    st.session_state.user_role = self.user_data.get('role', 'employee')
                    
                    return True
                else:
                    st.error(f"❌ {data.get('error', 'Login failed')}")
            else:
                st.error(f"❌ HTTP error {response.status_code}")
                st.write(f"Response: {response.text}")  # Debug info
                
            return False
            
        except Exception as e:
            st.error(f"❌ Error: {e}")
            return False

    def get_auth_headers(self):
        """Get headers with authentication token - FIXED METHOD"""
        if st.session_state.get('token'):
            return {'Authorization': f'Bearer {st.session_state.token}'}
        return {}

    def change_password(self, current_password: str, new_password: str) -> bool:
        """Change password for current user"""
        try:
            response = requests.post(
                f"{self.backend_url}/api/auth/change-password",
                json={
                    'current_password': current_password,
                    'new_password': new_password
                },
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return True
                else:
                    st.error(f"❌ {data.get('error', 'Password change failed')}")
            else:
                st.error(f"❌ HTTP error {response.status_code}")
                
            return False
            
        except Exception as e:
            st.error(f"❌ Error: {e}")
            return False

    def get_profile(self):
        """Get user profile - returns different data based on role"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/employee/profile",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    if st.session_state.user_role == 'employee':
                        return data.get('employee')  # Single employee object
                    else:
                        return data.get('employees', [])  # List of employees
            return None
            
        except Exception as e:
            st.error(f"❌ Failed to fetch profile: {e}")
            return None

    def is_admin(self):
        """Check if current user is admin"""
        return st.session_state.get('user_role') == 'superadmin'

    def is_employee(self):
        """Check if current user is employee"""
        return st.session_state.get('user_role') == 'employee'

    def logout(self):
        """Clear authentication state"""
        self.token = None
        self.user_data = None
        st.session_state.clear()

def initialize_auth():
    """Initialize authentication state in session"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'token' not in st.session_state:
        st.session_state.token = None  # FIXED: Changed from st.session_s-tate.token
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None

def require_auth(role=None):
    """Decorator to require authentication (optionally specific role)"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            auth_manager = AuthManager()
            
            if not st.session_state.get('authenticated'):
                st.warning("🔒 Please log in to access this page.")
                if st.button("🔐 Go to Login"):
                    st.session_state.page = "Login"
                    st.rerun()
                st.stop()
            
            if role and st.session_state.get('user_role') != role:
                st.error(f"🔐 {role.capitalize()} access required for this page.")
                st.stop()
                
            return func(*args, **kwargs)
        return wrapper
    return decorator