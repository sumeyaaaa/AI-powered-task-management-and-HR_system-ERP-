import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from config import config
from auth import AuthManager
import os
import io


class EmployeeManager:
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
        self.auth_manager = AuthManager()

    def upload_employee_photo(self, employee_id: str, photo_file) -> dict:
        """Upload employee photo"""
        try:
            files = {'photo': photo_file}
            response = requests.post(
                f"{self.backend_url}/api/employees/{employee_id}/upload-photo",
                files=files,
                headers=self.auth_manager.get_auth_headers(),
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def remove_employee_photo(self, employee_id: str) -> dict:
        """Remove employee photo"""
        try:
            response = requests.delete(
                f"{self.backend_url}/api/employees/{employee_id}/remove-photo",
                headers=self.auth_manager.get_auth_headers(),
                timeout=15
            )
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def upload_employee_jd(self, employee_id: str, jd_file) -> dict:
        """Upload employee job description"""
        try:
            files = {'jd': jd_file}
            response = requests.post(
                f"{self.backend_url}/api/employees/{employee_id}/upload-jd",
                files=files,
                headers=self.auth_manager.get_auth_headers(),
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def remove_employee_jd(self, employee_id: str) -> dict:
        """Remove employee job description"""
        try:
            response = requests.delete(
                f"{self.backend_url}/api/employees/{employee_id}/remove-jd",
                headers=self.auth_manager.get_auth_headers(),
                timeout=15
            )
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def download_employee_jd(self, employee_id: str) -> dict:
        """Download employee job description"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/employees/{employee_id}/download-jd",
                headers=self.auth_manager.get_auth_headers(),
                timeout=30
            )
            if response.status_code == 200:
                return {
                    'success': True,
                    'content': response.content,
                    'content_type': response.headers.get('content-type', 'application/octet-stream'),
                    'filename': response.headers.get('content-disposition', '').split('filename=')[-1].strip('"')
                }
            else:
                return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
    def update_employee_jd_link(self, employee_id: str, jd_link: str) -> dict:
        """Update employee job description link"""
        try:
            response = requests.put(
                f"{self.backend_url}/api/employees/{employee_id}/jd-link",
                json={'job_description_url': jd_link},
                headers=self.auth_manager.get_auth_headers(),
                timeout=15
            )
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
    def get_employees(self, show_inactive=False):
        """Fetch employees from backend with better error handling"""
        try:
            # Test backend connection first
            health_response = requests.get(
                f"{self.backend_url}/api/health",
                timeout=5
            )
            
            if health_response.status_code != 200:
                st.error("❌ Backend server is not responding properly")
                return []

            # Now fetch employees
            response = requests.get(
                f"{self.backend_url}/api/employee/profile",  # Use the working endpoint
                headers=self.auth_manager.get_auth_headers(),
                timeout=15  # Increased timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                employees = data.get('employees', []) if data.get('success') else []
                
                if not show_inactive:
                    employees = [e for e in employees if e.get('is_active', True)]
                    
                return employees
            else:
                st.error(f"❌ HTTP error {response.status_code}")
                if response.status_code == 404:
                    st.error("Employee endpoint not found. Using fallback method.")
                    return self._get_employees_fallback()
                return []
            
        except requests.exceptions.ConnectionError:
            st.error("🚫 Cannot connect to backend server. Please ensure the backend is running on localhost:5000")
            return []
        except requests.exceptions.Timeout:
            st.error("⏰ Backend request timed out. The server might be overloaded.")
            return []
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")
            return []

    def _get_employees_fallback(self):
        """Fallback method if main endpoint fails"""
        try:
            # Try alternative endpoints
            endpoints = [
                f"{self.backend_url}/api/employees",
                f"{self.backend_url}/api/admin/employees"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(
                        endpoint,
                        headers=self.auth_manager.get_auth_headers(),
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data.get('employees', []) if data.get('success') else []
                except:
                    continue
            return []
        except:
            return []

    def create_employee(self, employee_data: dict):
        """Create new employee via backend"""
        try:
            # Try multiple endpoints
            endpoints = [
                f"{self.backend_url}/api/employees",
                f"{self.backend_url}/api/admin/employees"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.post(
                        endpoint,
                        json=employee_data,
                        headers=self.auth_manager.get_auth_headers(),
                        timeout=15
                    )
                    if response.status_code != 404:  # If not "not found", use this response
                        return response.json()
                except requests.exceptions.ConnectionError:
                    continue
                except requests.exceptions.Timeout:
                    continue
            
            return {'success': False, 'error': 'All endpoints failed - backend may be down'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def update_employee(self, employee_id: str, update_data: dict):
        """Update employee via backend"""
        try:
            # Try multiple endpoints
            endpoints = [
                f"{self.backend_url}/api/employees/{employee_id}",
                f"{self.backend_url}/api/admin/employees/{employee_id}"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.put(
                        endpoint,
                        json=update_data,
                        headers=self.auth_manager.get_auth_headers(),
                        timeout=15
                    )
                    if response.status_code != 404:
                        return response.json()
                except requests.exceptions.ConnectionError:
                    continue
                except requests.exceptions.Timeout:
                    continue
            
            return {'success': False, 'error': 'All endpoints failed - backend may be down'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def delete_employee(self, employee_id: str):
        """Soft delete employee (set inactive)"""
        try:
            # For soft delete, use update to set is_active to False
            update_data = {
                'is_active': False,
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }
            return self.update_employee(employee_id, update_data)
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def permanent_delete_employee(self, employee_id: str):
        """Permanently delete employee via backend"""
        try:
            # Try permanent delete endpoint
            response = requests.delete(
                f"{self.backend_url}/api/employees/{employee_id}/permanent",
                headers=self.auth_manager.get_auth_headers(),
                timeout=20
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Fallback to soft delete
                st.warning("⚠️ Permanent delete not available. Using soft delete instead.")
                return self.delete_employee(employee_id)
                
        except requests.exceptions.ConnectionError:
            st.error("🚫 Cannot connect to backend for permanent deletion")
            return {'success': False, 'error': 'Backend connection failed'}
        except requests.exceptions.Timeout:
            st.warning("⏰ Permanent delete timed out. Using soft delete instead.")
            return self.delete_employee(employee_id)
        except Exception as e:
            st.warning(f"⚠️ Permanent delete failed: {e}. Using soft delete instead.")
            return self.delete_employee(employee_id)

    def reset_employee_password(self, employee_id: str):
        """Reset employee password to default (admin only)"""
        try:
            response = requests.post(
                f"{self.backend_url}/api/employees/{employee_id}/reset-password",
                headers=self.auth_manager.get_auth_headers(),
                timeout=15
            )
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Helper function to safely handle None values
def safe_strip(value):
    """Safely strip a string, handling None values"""
    if value is None:
        return ""
    return str(value).strip()

def safe_split(value):
    """Safely split a string into list, handling None values"""
    if value is None or value == "":
        return []
    return [item.strip() for item in str(value).split(',') if item.strip()]

def safe_json_load(value):
    """Safely load JSON data"""
    if value is None or value == "":
        return {}
    try:
        import json
        return json.loads(value)
    except:
        return {}

@st.cache_data(ttl=300)
def get_employee_manager():
    """Get cached employee manager instance"""
    return EmployeeManager(config.BACKEND_URL)

def get_all_employees():
    """Get all employees using the employee manager"""
    emp_manager = get_employee_manager()
    return emp_manager.get_employees(show_inactive=True)

def show_employee_management():
    """Main employee management function"""
    st.title("👥 Employee Management")
    
    # Tab interface for different views
    tab1, tab2, tab3 = st.tabs(["📋 Employee List", "➕ Add New Employee", "📊 Employee Analytics"])
    
    with tab1:
        show_employee_list()
    
    with tab2:
        show_add_employee_form()
    
    with tab3:
        show_employee_analytics()


def show_employee_jd_management(employee):
    """Show JD management section"""
    emp_manager = get_employee_manager()
    
    st.subheader(f"📄 Job Description Management: {employee['name']}")
    
    # Back button at the top
    if st.button("← Back to Employee List"):
        if hasattr(st.session_state, 'managing_jd'):
            del st.session_state.managing_jd
        st.rerun()
    
    show_employee_jd_section(employee)

def show_employee_list():
    """Display list of employees with management options"""
    try:
        emp_manager = get_employee_manager()
        employees = emp_manager.get_employees(show_inactive=True)
        
        if not employees:
            st.info("No employees found in the system.")
            return
        
        # Check if we're in JD management mode FIRST
        if hasattr(st.session_state, 'managing_jd'):
            employee = st.session_state.managing_jd
            show_employee_jd_management(employee)
            return
            
        # Check if we're in detail view mode FIRST
        if hasattr(st.session_state, 'viewing_employee_detail'):
            show_employee_detail_view(st.session_state.viewing_employee_detail)
            return
            
        # Check if we're in edit mode or photo mode
        if hasattr(st.session_state, 'editing_employee'):
            show_edit_employee_form(st.session_state.editing_employee)
            return
            
        if hasattr(st.session_state, 'managing_photo'):
            employee = st.session_state.managing_photo
            st.subheader(f"📷 Manage Photo for {employee['name']}")
            show_employee_photo_section(employee)
            
            if st.button("← Back to List"):
                del st.session_state.managing_photo
                st.rerun()
            return

        # Display employee list
        st.subheader("👥 All Employees")
        
        # Show statistics
        active_count = len([e for e in employees if e.get('is_active', True)])
        inactive_count = len([e for e in employees if not e.get('is_active', True)])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Employees", len(employees))
        with col2:
            st.metric("Active Employees", active_count)
        with col3:
            st.metric("Inactive Employees", inactive_count)
        
        st.markdown("---")
        
        # Display each employee
        for employee in employees:
            with st.expander(f"👤 {employee['name']} - {employee['role']}", expanded=False):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Display employee photo
                    photo_url = employee.get('photo_url')
                    if photo_url:
                        st.image(photo_url, width=120, caption=employee['name'])
                    else:
                        st.image("https://via.placeholder.com/120x120.png?text=No+Photo", 
                                width=120, caption="No Photo")
                
                with col2:
                    # Employee details
                    st.write(f"**Email:** {employee['email']}")
                    st.write(f"**Department:** {employee.get('department', 'N/A')}")
                    st.write(f"**Title:** {employee.get('title', 'N/A')}")
                    status = "🟢 Active" if employee.get('is_active', True) else "🔴 Inactive"
                    st.write(f"**Status:** {status}")
                    
                    # JD status
                    job_description_url = employee.get('job_description_url')
                    if job_description_url:
                        st.write("**JD:** 📎 Attached")
                    else:
                        st.write("**JD:** ❌ Not attached")
                    
                    # Action buttons - Now with 6 columns for the new JD button
                    col_act1, col_act2, col_act3, col_act4, col_act5, col_act6 = st.columns(6)
                    
                    with col_act1:
                        if st.button("📋 Details", key=f"detail_{employee['id']}"):
                            st.session_state.viewing_employee_detail = employee
                            st.rerun()
                    
                    with col_act2:
                        if st.button("✏️ Edit", key=f"edit_{employee['id']}"):
                            st.session_state.editing_employee = employee
                            st.rerun()
                    
                    with col_act3:
                        if st.button("📷 Photo", key=f"photo_{employee['id']}"):
                            st.session_state.managing_photo = employee
                            st.rerun()

                    with col_act4:
                        if st.button("📄 JD", key=f"jd_{employee['id']}"):
                            st.session_state.managing_jd = employee
                            st.rerun()
                    
                    with col_act5:
                        if employee.get('is_active', True):
                            if st.button("🗑️ Deactivate", key=f"deactivate_{employee['id']}"):
                                with st.spinner("Deactivating employee..."):
                                    result = emp_manager.delete_employee(employee['id'])
                                if result.get('success'):
                                    st.success("Employee deactivated successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to deactivate: {result.get('error', 'Unknown error')}")
                        else:
                            if st.button("✅ Activate", key=f"activate_{employee['id']}"):
                                update_data = {
                                    'is_active': True,
                                    'updated_at': datetime.utcnow().isoformat() + 'Z'
                                }
                                with st.spinner("Activating employee..."):
                                    result = emp_manager.update_employee(employee['id'], update_data)
                                if result.get('success'):
                                    st.success("Employee activated successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to activate: {result.get('error', 'Unknown error')}")
                    
                    with col_act6:
                        if st.button("🔥 Delete", key=f"perm_delete_{employee['id']}", type="secondary"):
                            st.session_state.deleting_employee = employee
                            st.rerun()
        
        # Handle deletion confirmation
        if hasattr(st.session_state, 'deleting_employee'):
            employee = st.session_state.deleting_employee
            st.warning(f"🚨 Are you sure you want to permanently delete {employee['name']}? This action cannot be undone!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm Permanent Delete", type="primary"):
                    with st.spinner("Deleting employee..."):
                        result = emp_manager.permanent_delete_employee(employee['id'])
                    if result.get('success'):
                        st.error("Employee permanently deleted!")
                        del st.session_state.deleting_employee
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {result.get('error', 'Unknown error')}")
            with col2:
                if st.button("❌ Cancel"):
                    del st.session_state.deleting_employee
                    st.rerun()
                
    except Exception as e:
        st.error(f"Error loading employees: {str(e)}")
      
def show_employee_detail_view(employee):
    """Show detailed employee information without editing options"""
    emp_manager = get_employee_manager()
    
    # Back button at the top
    if st.button("← Back to Employee List"):
        if hasattr(st.session_state, 'viewing_employee_detail'):
            del st.session_state.viewing_employee_detail
        st.rerun()
    
    st.subheader(f"👤 Employee Details: {employee['name']}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display employee photo
        photo_url = employee.get('photo_url')
        if photo_url:
            st.image(photo_url, width=200, caption=employee['name'])
        else:
            st.image("https://via.placeholder.com/200x200.png?text=No+Photo", 
                    width=200, caption="No Photo")
        
        st.markdown("---")
        st.write(f"**Email:** {employee['email']}")
        st.write(f"**Role:** {employee.get('role', 'N/A')}")
        st.write(f"**Department:** {employee.get('department', 'N/A')}")
        st.write(f"**Title:** {employee.get('title', 'N/A')}")
        st.write(f"**Location:** {employee.get('location', 'N/A')}")
        st.write(f"**Experience:** {employee.get('experience_years', 0)} years")
        st.write(f"**Status:** {'🟢 Active' if employee.get('is_active', True) else '🔴 Inactive'}")

        # JD Information
        job_description_url = employee.get('job_description_url')
        if job_description_url:
            st.markdown("---")
            st.write("**Job Description:** ✅ Linked")
            st.markdown(f"[🔗 Open JD in Google Drive]({job_description_url})", unsafe_allow_html=True)
        else:
            st.markdown("---")
            st.write("**Job Description:** ❌ Not Linked")
        
        if employee.get('linkedin_url'):
            st.markdown(f"**LinkedIn:** [{employee['linkedin_url']}]({employee['linkedin_url']})")
        
        if employee.get('telegram_chat_id'):
            st.write(f"**Telegram Chat ID:** {employee['telegram_chat_id']}")

    with col2:
        st.markdown("### Professional Information")
        
        st.write("**Bio:**")
        bio = employee.get('bio', 'No bio provided.')
        st.info(bio if bio else 'No bio provided.')
        
        st.write("**Skills:**")
        skills = employee.get('skills', [])
        if skills:
            for skill in skills:
                st.markdown(f"- {skill}")
        else:
            st.write("No skills listed.")
        
        st.write("**Strengths:**")
        strengths = employee.get('strengths', [])
        if strengths:
            for strength in strengths:
                st.markdown(f"- {strength}")
        else:
            st.write("No strengths listed.")
        
        st.write("**Area of Development:**")
        area_dev = employee.get('area_of_development', 'Not specified')
        st.write(area_dev)
    
    # Employment details
    st.markdown("---")
    st.markdown("### Employment Details")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"**Employee ID:** `{employee.get('id', 'Unknown')}`")
        st.write(f"**Employee Since:** {employee.get('created_at', 'Unknown')[:10]}")
    with col2:
        st.write(f"**Last Updated:** {employee.get('updated_at', 'Unknown')[:10]}")
    with col3:
        # Quick actions
        if st.button("✏️ Edit Employee", use_container_width=True):
            st.session_state.editing_employee = employee
            del st.session_state.viewing_employee_detail
            st.rerun()
    
    # Also add a back button at the bottom
    st.markdown("---")
    if st.button("← Back to List", key="bottom_back_detail"):
        if hasattr(st.session_state, 'viewing_employee_detail'):
            del st.session_state.viewing_employee_detail
        st.rerun()
            
def show_edit_employee_form(employee):
    """Edit employee form with photo section and password reset"""
    emp_manager = get_employee_manager()
    
    # Back button at the top
    if st.button("← Back to Employee List"):
        if hasattr(st.session_state, 'editing_employee'):
            del st.session_state.editing_employee
        st.rerun()
    
    st.subheader(f"✏️ Edit Employee: {employee['name']}")
    
    # Photo section at the top
    show_employee_photo_section(employee)
    st.markdown("---")
    
    # JD section
    show_employee_jd_section(employee)
    st.markdown("---")
    
    with st.form(f"edit_employee_{employee['id']}"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name*", value=employee.get('name', ''))
            email = st.text_input("Email*", value=employee.get('email', ''))
            role = st.text_input("Role*", value=employee.get('role', ''))
            department = st.text_input("Department", value=employee.get('department', ''))
        
        with col2:
            title = st.text_input("Title", value=employee.get('title', ''))
            location = st.text_input("Location", value=employee.get('location', ''))
            experience_years = st.number_input("Experience (years)", 
                                            value=employee.get('experience_years', 0),
                                            min_value=0, max_value=50)
            is_active = st.checkbox("Active Employee", value=employee.get('is_active', True))
        
        # Additional fields
        linkedin_url = st.text_input("LinkedIn URL", value=employee.get('linkedin_url', ''))
        telegram_chat_id = st.text_input("Telegram Chat ID", value=employee.get('telegram_chat_id', ''))
        area_of_development = st.text_area("Area of Development", 
                                        value=employee.get('area_of_development', ''))
        bio = st.text_area("Bio", value=employee.get('bio', ''))
        
        # Skills and strengths
        skills = st.text_area("Skills (comma-separated)", 
                            value=", ".join(employee.get('skills', [])))
        strengths = st.text_area("Strengths (comma-separated)", 
                               value=", ".join(employee.get('strengths', [])))
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            update_btn = st.form_submit_button("💾 Update Employee", use_container_width=True)
        with col_btn2:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if update_btn:
            if not name or not email or not role:
                st.error("Please fill in all required fields (marked with *)")
                return
            
            # Prepare update data
            update_data = {
                'name': safe_strip(name),
                'email': safe_strip(email).lower(),
                'role': safe_strip(role),
                'department': safe_strip(department),
                'title': safe_strip(title),
                'location': safe_strip(location),
                'experience_years': experience_years,
                'linkedin_url': safe_strip(linkedin_url),
                'telegram_chat_id': safe_strip(telegram_chat_id),
                'area_of_development': safe_strip(area_of_development),
                'bio': safe_strip(bio),
                'skills': safe_split(skills),
                'strengths': safe_split(strengths),
                'is_active': is_active
            }
            
            # Remove empty values
            update_data = {k: v for k, v in update_data.items() if v not in [None, '', []]}
            
            with st.spinner("Updating employee..."):
                result = emp_manager.update_employee(employee['id'], update_data)
            
            if result.get('success'):
                st.success("✅ Employee updated successfully!")
                if hasattr(st.session_state, 'editing_employee'):
                    del st.session_state.editing_employee
                st.rerun()
            else:
                st.error(f"❌ Failed to update employee: {result.get('error', 'Unknown error')}")
        
        if cancel_btn:
            if hasattr(st.session_state, 'editing_employee'):
                del st.session_state.editing_employee
            st.rerun()
    
    # Password Reset Section (Outside the form so it works independently)
    st.markdown("---")
    st.subheader("🔐 Password Management")
    
    if st.session_state.get('user_role') == 'superadmin':
        st.write("**Admin Action:** Reset employee password to default")
        
        if st.button("🔄 Reset Password", key=f"reset_pw_edit_{employee['id']}", type="secondary"):
            with st.spinner("Resetting password..."):
                result = emp_manager.reset_employee_password(employee['id'])
            
            if result.get('success'):
                st.success("✅ Password reset successfully!")
                default_passwords = result.get('default_passwords', [employee['id'], '1234'])
                st.info(f"""
                **New Login Credentials:**
                - Use either: 
                  - Employee ID: `{default_passwords[0]}`
                  - Or: `{default_passwords[1]}`
                - Employee should change password after first login
                """)
            else:
                st.error(f"❌ Failed to reset password: {result.get('error', 'Unknown error')}")
    else:
        st.info("Only administrators can reset employee passwords.")
    
    # Also add a back button at the bottom
    st.markdown("---")
    if st.button("← Back to List", key="bottom_back_button"):
        if hasattr(st.session_state, 'editing_employee'):
            del st.session_state.editing_employee
        st.rerun()

    

def show_employee_jd_section(employee):
    """Show job description section with Google Drive links"""
    emp_manager = get_employee_manager()
    
    st.subheader("📄 Job Description Management")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display current JD status
        job_description_url = employee.get('job_description_url')
        if job_description_url:
            st.success("✅ JD Linked")
            st.info("Job description is available via Google Drive")
            
            # Open Google Drive link button
            st.markdown(f"[🔗 Open JD in Google Drive]({job_description_url})", unsafe_allow_html=True)
            
            # Show current link
            st.text_area("Current JD Link", value=job_description_url, height=60, disabled=True, key=f"current_jd_{employee['id']}")
        else:
            st.warning("❌ No JD Linked")
            st.info("Add a Google Drive link to the job description")
    
    with col2:
        # Google Drive link input
        st.write("**Update Google Drive JD Link**")
        gdrive_link = st.text_input(
            "Paste Google Drive Shareable Link",
            value=job_description_url or "",
            placeholder="https://drive.google.com/file/d/.../view?usp=sharing",
            key=f"gdrive_jd_{employee['id']}"
        )
        
        # Instructions for getting shareable link
        with st.expander("ℹ️ How to get Google Drive Shareable Link"):
            st.markdown("""
            1. Upload your JD file to Google Drive
            2. Right-click the file and select "Share"
            3. Click "Copy link"
            4. Ensure link sharing is set to "Anyone with the link can view"
            5. Paste the link above
            """)
        
        # Action buttons
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("💾 Save JD Link", key=f"save_jd_link_{employee['id']}", type="primary", use_container_width=True):
                if gdrive_link:
                    # Use the dedicated JD link update method
                    with st.spinner("Saving JD link..."):
                        result = emp_manager.update_employee_jd_link(employee['id'], gdrive_link)
                    
                    if result.get('success'):
                        st.success("✅ Google Drive JD link saved successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to save JD link: {result.get('error', 'Unknown error')}")
                else:
                    st.error("❌ Please provide a Google Drive link")
        
        with col_btn2:
            # Update existing link button
            if job_description_url and gdrive_link != job_description_url:
                if st.button("🔄 Update Link", key=f"update_jd_link_{employee['id']}", use_container_width=True):
                    with st.spinner("Updating JD link..."):
                        result = emp_manager.update_employee_jd_link(employee['id'], gdrive_link)
                    
                    if result.get('success'):
                        st.success("✅ JD link updated successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to update JD link: {result.get('error', 'Unknown error')}")
        
        with col_btn3:
            # Remove JD link button if exists
            if job_description_url:
                if st.button("🗑️ Delete JD Link", key=f"delete_jd_link_{employee['id']}", type="secondary", use_container_width=True):
                    with st.spinner("Deleting JD link..."):
                        result = emp_manager.update_employee_jd_link(employee['id'], "")
                    
                    if result.get('success'):
                        st.success("✅ JD link deleted successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to delete JD link: {result.get('error', 'Unknown error')}")
        
        # Validation message
        if gdrive_link and not gdrive_link.startswith('https://drive.google.com/'):
            st.warning("⚠️ This doesn't look like a Google Drive link. Please make sure it's a valid Google Drive shareable link.")


def show_add_employee_form():
    """Form to add new employee with all fields"""
    emp_manager = get_employee_manager()
    
    st.subheader("➕ Add New Employee")
    
    with st.form("add_employee_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name*", placeholder="John Doe")
            email = st.text_input("Email Address*", placeholder="john.doe@company.com")
            role = st.text_input("Role*", placeholder="QA Engineer")
            department = st.text_input("Department", placeholder="Engineering")
            title = st.text_input("Job Title", placeholder="Senior QA Engineer")
            experience_years = st.number_input("Years of Experience", min_value=0, max_value=50, value=0)
            location = st.text_input("Location", placeholder="City, Country")
            
        with col2:
            linkedin_url = st.text_input("LinkedIn URL", placeholder="https://linkedin.com/in/username")
            telegram_chat_id = st.text_input("Telegram Chat ID", placeholder="123456789")
            area_of_development = st.text_input("Area of Development", placeholder="Software Development, Marketing, etc.")
            skills = st.text_area("Skills (comma-separated)", placeholder="Python, Testing, Automation, ...")
            strengths = st.text_area("Strengths (comma-separated)", placeholder="Leadership, Communication, Problem-solving, ...")
            bio = st.text_area("Bio", placeholder="Brief professional description...")
        
        submitted = st.form_submit_button("Create Employee")
        
        if submitted:
            if not name or not email or not role:
                st.error("Please fill in all required fields (marked with *)")
                return
            
            # Use safe_strip to handle empty fields
            employee_data = {
                'name': safe_strip(name),
                'email': safe_strip(email).lower(),
                'role': safe_strip(role),
                'department': safe_strip(department),
                'title': safe_strip(title),
                'experience_years': experience_years,
                'location': safe_strip(location),
                'linkedin_url': safe_strip(linkedin_url),
                'telegram_chat_id': safe_strip(telegram_chat_id),
                'area_of_development': safe_strip(area_of_development),
                'bio': safe_strip(bio),
                'skills': safe_split(skills),
                'strengths': safe_split(strengths)
            }
            
            # Remove empty strings and None values
            employee_data = {k: v for k, v in employee_data.items() if v not in [None, '', []]}
            
            with st.spinner("Creating employee..."):
                result = emp_manager.create_employee(employee_data)
            
            if result.get('success'):
                employee = result.get('employee', {})
                st.success(f"✅ Employee **{name}** created successfully!")
                st.balloons()
                
                # Show login information for employee
                login_info = result.get('login_info', {})
                default_passwords = login_info.get('default_passwords', [str(employee.get('id', 'N/A')), '1234'])
                
                st.info(f"""
                **Employee Login Information:**
                - **Email:** `{email}`
                - **Default Passwords:** 
                  - Employee ID: `{default_passwords[0]}`
                  - Or use: `{default_passwords[1]}`
                - **Note:** Employee should change password after first login
                """)
                
                st.rerun()
            else:
                error_msg = result.get('error', 'Unknown error')
                st.error(f"❌ Failed to create employee: {error_msg}")

def show_employee_analytics():
    """Show employee analytics and statistics"""
    st.subheader("📊 Employee Analytics")
    
    emp_manager = get_employee_manager()
    employees = emp_manager.get_employees(show_inactive=True)
    
    if not employees:
        st.info("No employee data available for analytics.")
        return
    
    # Basic statistics
    total_employees = len(employees)
    active_employees = len([e for e in employees if e.get('is_active', True)])
    inactive_employees = total_employees - active_employees
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Employees", total_employees)
    with col2:
        st.metric("Active Employees", active_employees)
    with col3:
        st.metric("Inactive Employees", inactive_employees)
    with col4:
        # FIX: Handle None values in experience_years
        experience_values = []
        for e in employees:
            exp = e.get('experience_years')
            # Convert None to 0, and ensure it's a number
            if exp is None:
                experience_values.append(0)
            else:
                try:
                    experience_values.append(float(exp))
                except (TypeError, ValueError):
                    experience_values.append(0)
        
        avg_experience = sum(experience_values) / max(len(experience_values), 1)
        st.metric("Avg Experience", f"{avg_experience:.1f} years")
    
    st.markdown("---")
    
    # Department distribution
    st.subheader("Department Distribution")
    departments = {}
    for emp in employees:
        dept = emp.get('department', 'Not Specified')
        departments[dept] = departments.get(dept, 0) + 1
    
    if departments:
        dept_df = pd.DataFrame(list(departments.items()), columns=['Department', 'Count'])
        st.bar_chart(dept_df.set_index('Department'))
    else:
        st.info("No department data available.")
    
    # Role distribution
    st.subheader("Role Distribution")
    roles = {}
    for emp in employees:
        role = emp.get('role', 'Not Specified')
        roles[role] = roles.get(role, 0) + 1
    
    if roles:
        role_df = pd.DataFrame(list(roles.items()), columns=['Role', 'Count'])
        st.bar_chart(role_df.set_index('Role'))

def show_employee_photo_section(employee):
    """Show photo section for employee management"""
    emp_manager = get_employee_manager()
    
    st.subheader("📷 Employee Photo")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display current photo
        photo_url = employee.get('photo_url')
        if photo_url:
            st.image(photo_url, width=150, caption="Current Photo")
        else:
            st.image("https://via.placeholder.com/150x150.png?text=No+Photo", 
                    width=150, caption="No Photo Available")
    
    with col2:
        # Photo upload
        uploaded_file = st.file_uploader(
            "Upload new photo", 
            type=['png', 'jpg', 'jpeg', 'gif', 'webp'],
            key=f"photo_upload_{employee['id']}"
        )
        
        if uploaded_file is not None:
            # Check file size
            if uploaded_file.size > 5 * 1024 * 1024:
                st.error("File too large. Maximum size is 5MB.")
            else:
                # Show preview
                st.image(uploaded_file, width=100, caption="Preview")
                
                if st.button("Upload Photo", key=f"upload_btn_{employee['id']}"):
                    with st.spinner("Uploading photo..."):
                        result = emp_manager.upload_employee_photo(employee['id'], uploaded_file)
                    
                    if result.get('success'):
                        st.success("✅ Photo uploaded successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to upload photo: {result.get('error', 'Unknown error')}")
        
        # Remove photo button
        if photo_url:
            if st.button("Remove Photo", key=f"remove_btn_{employee['id']}", type="secondary"):
                with st.spinner("Removing photo..."):
                    result = emp_manager.remove_employee_photo(employee['id'])
                
                if result.get('success'):
                    st.success("✅ Photo removed successfully!")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to remove photo: {result.get('error', 'Unknown error')}")
        
        st.info("**Supported formats:** PNG, JPG, JPEG, GIF, WebP (max 5MB)")


# Photo upload frontend functions (for compatibility)
def upload_employee_photo_frontend(employee_id, uploaded_file):
    """Frontend function to upload employee photo (compatibility wrapper)"""
    emp_manager = get_employee_manager()
    result = emp_manager.upload_employee_photo(employee_id, uploaded_file)
    return result.get('success', False)

def remove_employee_photo_frontend(employee_id):
    """Frontend function to remove employee photo (compatibility wrapper)"""
    emp_manager = get_employee_manager()
    result = emp_manager.remove_employee_photo(employee_id)
    return result.get('success', False)

