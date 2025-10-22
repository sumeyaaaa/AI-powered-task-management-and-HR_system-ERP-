import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from config import config
from auth import AuthManager
import json
import time
import threading


def reset_navigation_state():
    """Reset navigation-related session state"""
    keys_to_clear = ['current_task_id', 'notification_navigation']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.toast("🔄 Navigation reset", icon="🔄")

def clear_task_navigation():
    """Clear task navigation state specifically"""
    if 'current_task_id' in st.session_state:
        del st.session_state['current_task_id']
    st.toast("🔄 Navigation cleared", icon="🔧")


class TaskManager:
    def __init__(self, backend_url: str, token=None):
        self.backend_url = backend_url
        self.auth_manager = AuthManager()
        self.token = token

    def get_auth_headers(self):
        """Get headers with authentication token - FIXED METHOD"""
        if st.session_state.get('token'):
            return {'Authorization': f'Bearer {st.session_state.token}'}
        return {}

    def _safe_json_response(self, response):
        """Safely parse JSON response, handling errors - IMPROVED VERSION"""
        try:
            # Check if response is valid
            if response.status_code == 404:
                return {'success': False, 'error': 'Endpoint not found (404)'}
            if response.status_code == 500:
                return {'success': False, 'error': 'Server error (500)'}
            
            # Check if response has content
            if not response.text or response.text.strip() == '':
                return {'success': False, 'error': 'Empty response from server'}
            
            # Try to parse as JSON
            data = response.json()
            return data
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"📄 Response text: {response.text[:500]}...")
            
            # If it's HTML, it's probably a 404/500 error page
            if '<!DOCTYPE html>' in response.text or '<html' in response.text.lower():
                return {
                    'success': False, 
                    'error': f'Server returned HTML error page (status {response.status_code})',
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': False, 
                    'error': f'Invalid JSON response: {str(e)}',
                    'raw_response': response.text[:500],
                    'status_code': response.status_code
                }

    def get_task_dashboard(self):
        try:
            print(f"📊 Fetching dashboard from: {self.backend_url}/api/tasks/dashboard")
            response = requests.get(
                f"{self.backend_url}/api/tasks/dashboard", 
                headers=self.get_auth_headers(), 
                timeout=15
            )
            print(f"📥 Dashboard response status: {response.status_code}")
            return self._safe_json_response(response)
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timed out after 15 seconds'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Cannot connect to server'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_goals(self):
        """Get all company goals - FIXED VERSION"""
        try:
            print(f"🎯 Fetching goals from: {self.backend_url}/api/tasks/goals")
            response = requests.get(
                f"{self.backend_url}/api/tasks/goals", 
                headers=self.get_auth_headers(), 
                timeout=15
            )
            print(f"📥 Goals response status: {response.status_code}")
            return self._safe_json_response(response)
        except Exception as e:
            print(f"❌ Error getting goals: {e}")
            return {'success': False, 'error': str(e)}

    def create_goal_classify_only(self, goal_data: dict):
        try:
            print(f"📤 Sending goal classification to: {self.backend_url}/api/tasks/goals/classify-only")
            response = requests.post(
                f"{self.backend_url}/api/tasks/goals/classify-only",
                json=goal_data,
                headers=self.get_auth_headers(),
                timeout=400
            )
            print(f"📥 Response status: {response.status_code}")
            if response.status_code != 200:
                return {'success': False, 'error': f"Request failed with status {response.status_code}"}
            return response.json()
        except requests.exceptions.Timeout:
            return {'success': False, 'error': "Request timed out after 30 seconds"}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def test_auth(self):
        try:
            response = requests.get(f"{self.backend_url}/api/debug/auth", headers=self.get_auth_headers(), timeout=10)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def test_connection(self):
        try:
            response = requests.get(f"{self.backend_url}/api/debug/auth-test", timeout=10)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_task_detail(self, task_id: str):
        try:
            response = requests.get(f"{self.backend_url}/api/tasks/{task_id}", headers=self.get_auth_headers(), timeout=15)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_employee_recommendations(self, task_id: str):
        """Get employee recommendations for a task - FIXED to use GET"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/tasks/{task_id}/employee-recommendations",
                headers=self.get_auth_headers(),
                timeout=15
            )
            return self._safe_json_response(response)
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
    def get_goal_detail(self, goal_id: str):
        try:
            response = requests.get(f"{self.backend_url}/api/tasks/goals/{goal_id}", headers=self.get_auth_headers(), timeout=15)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def create_task(self, task_data: dict):
        try:
            response = requests.post(f"{self.backend_url}/api/tasks", json=task_data, headers=self.get_auth_headers(), timeout=15)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def update_task(self, task_id: str, update_data: dict):
        try:
            response = requests.put(f"{self.backend_url}/api/tasks/{task_id}", json=update_data, headers=self.get_auth_headers(), timeout=15)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_employee_tasks(self, employee_id: str):
        try:
            response = requests.get(f"{self.backend_url}/api/tasks/employee/{employee_id}", headers=self.get_auth_headers(), timeout=15)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def upload_task_file(self, task_id: str, file, notes: str = ""):
        try:
            files = {'file': (file.name, file.getvalue(), file.type)}
            data = {'notes': notes}
            response = requests.post(f"{self.backend_url}/api/tasks/{task_id}/upload-file", files=files, data=data, headers=self.get_auth_headers(), timeout=30)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_task_attachments(self, task_id: str):
        """Get task attachments - FIXED VERSION"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/tasks/{task_id}/attachments", 
                headers=self.get_auth_headers(), 
                timeout=15
            )
            # FIX: Use safe JSON response handler
            return self._safe_json_response(response)
        except Exception as e:
            # FIX: Always return a dictionary
            return {'success': False, 'error': str(e), 'attachments': [], 'total': 0}

    def get_task_notes(self, task_id: str):
        """Get task notes - FIXED VERSION with proper error handling"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/tasks/{task_id}/notes", 
                headers=self.get_auth_headers(), 
                timeout=15
            )
            # Use the safe JSON response handler
            return self._safe_json_response(response)
        except Exception as e:
            # Always return a dictionary, never None
            return {'success': False, 'error': str(e), 'notes': [], 'total': 0}

    def add_task_note(self, task_id: str, notes: str, progress: int = None):
        try:
            data = {'notes': notes, 'progress': progress}
            response = requests.post(f"{self.backend_url}/api/tasks/{task_id}/add-note", json=data, headers=self.get_auth_headers(), timeout=15)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def delete_task_attachment(self, task_id: str, update_id: str, attachment_index: int):
        try:
            response = requests.delete(f"{self.backend_url}/api/tasks/{task_id}/updates/{update_id}/attachment/{attachment_index}", headers=self.get_auth_headers(), timeout=15)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_available_dependencies(self, task_id: str):
        try:
            response = requests.get(f"{self.backend_url}/api/tasks/{task_id}/available-dependencies", headers=self.get_auth_headers(), timeout=15)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_task_employee_recommendations(self, task_id: str):
        """Get employee recommendations for a task"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/tasks/{task_id}/employee-recommendations",
                headers=self.get_auth_headers(),
                timeout=15
            )
            return self._safe_json_response(response)
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def apply_employee_recommendation(self, task_id: str, employee_id: str, recommendation_data: dict):
        """Apply an employee recommendation to a task"""
        try:
            response = requests.post(
                f"{self.backend_url}/api/tasks/{task_id}/apply-employee-recommendation",
                json={
                    'employee_id': employee_id,
                    'recommendation_data': recommendation_data
                },
                headers=self.get_auth_headers(),
                timeout=15
            )
            return self._safe_json_response(response)
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_ai_progress(self, ai_meta_id: str):
        try:
            response = requests.get(f"{self.backend_url}/api/ai-meta/{ai_meta_id}", headers=self.get_auth_headers(), timeout=15)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ADD THE MISSING RAG METHODS HERE
    def generate_rag_recommendations(self, task_id: str):
        """Generate RAG-enhanced employee recommendations for a task"""
        try:
            response = requests.post(
                f"{self.backend_url}/api/tasks/{task_id}/generate-rag-recommendations",
                headers=self.get_auth_headers(),
                timeout=30
            )
            return self._safe_json_response(response)
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_rag_recommendation_progress(self, ai_meta_id: str):
        """Get progress for RAG recommendations"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/ai-meta/{ai_meta_id}",
                headers=self.get_auth_headers(),
                timeout=15
            )
            return self._safe_json_response(response)
        except Exception as e:
            return {'success': False, 'error': str(e)}

# NOTIFICATION METHODS
    def get_notifications(self):
        """Get notifications for current user"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/notifications",
                headers=self.get_auth_headers(),
                timeout=15
            )
            return self._safe_json_response(response)
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def mark_notification_read(self, notification_id: str):
        """Mark a notification as read"""
        try:
            response = requests.put(
                f"{self.backend_url}/api/notifications/{notification_id}/read",
                headers=self.get_auth_headers(),
                timeout=15
            )
            return self._safe_json_response(response)
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def mark_all_notifications_read(self):
        """Mark all notifications as read"""
        try:
            response = requests.put(
                f"{self.backend_url}/api/notifications/read-all",
                headers=self.get_auth_headers(),
                timeout=15
            )
            return self._safe_json_response(response)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    def get_available_employees_for_attachment(self, task_id: str):
        """Get available employees for note attachment"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/tasks/{task_id}/available-employees",
                headers=self.get_auth_headers(),
                timeout=15
            )
            return self._safe_json_response(response)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def add_task_note_with_attachments(self, task_id: str, notes: str, progress: int = None, attached_to: str = None, attached_to_multiple: list = None):
        """Add a task note with employee attachments"""
        try:
            data = {
                'notes': notes,
                'progress': progress,
                'attached_to': attached_to,
                'attached_to_multiple': attached_to_multiple or []
            }
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            response = requests.post(
                f"{self.backend_url}/api/tasks/{task_id}/add-note", 
                json=data, 
                headers=self.get_auth_headers(), 
                timeout=15
            )
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}
    

@st.cache_data(ttl=300)
def get_task_manager(token=None):
    if token:
        return TaskManager(config.BACKEND_URL, token)
    return TaskManager(config.BACKEND_URL)


# ========== GOAL MANAGEMENT FUNCTIONS ==========

def show_goal_management():
    st.subheader("🎯 Set Company Goals")
    
    # Check if we should show AI review
    if 'show_ai_review' in st.session_state and st.session_state.show_ai_review:
        show_ai_classification_review()
        return
    
    # Check if we're already processing
    if st.session_state.get('processing_goal', False):
        goal_data = st.session_state.get('goal_data')
        if goal_data:
            show_ai_classification_progress(goal_data)
        else:
            st.error("❌ No goal data found. Please start over.")
            st.session_state.processing_goal = False
            if st.button("← Back to Goal Form"):
                st.rerun()
        return
    
    # Only show the form if we're not processing
    with st.form("create_goal_form", clear_on_submit=True):
        title = st.text_input("Goal Title*", placeholder="Launch Product Orion")
        description = st.text_area("Goal Description", placeholder="Detailed description...")
        output = st.text_area("Expected Output", placeholder="Deliverables...")
        deadline = st.date_input("Deadline*", min_value=datetime.now().date())
        department = st.selectbox("Department", ["All", "Engineering", "Marketing", "Sales", "QA", "Operations"])
        priority = st.selectbox("Priority", ["low", "medium", "high"])
        auto_classify = st.checkbox("🤖 AI Task Classification", value=True)
        
        submitted = st.form_submit_button("🎯 Create Goal")
        
        if submitted:
            if not title:
                st.error("Goal title required")
                st.stop()
            
            goal_data = {
                'title': title,
                'description': description,
                'output': output,
                'deadline': deadline.isoformat(),
                'department': department if department != "All" else "",
                'priority': priority,
                'auto_classify': auto_classify
            }
            
            # Store in session and trigger processing
            st.session_state.processing_goal = True
            st.session_state.goal_data = goal_data
            st.rerun()

def show_ai_classification_progress(goal_data):
    st.info("🚀 AI Classifying Goal...")
    
    task_manager = get_task_manager()
    
    # Show diagnostics
    with st.expander("🔧 Diagnostics", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Backend Connection**")
            conn_test = task_manager.test_connection()
            if conn_test.get('success'):
                st.success("✅ Server reachable")
            else:
                st.error(f"❌ Connection failed: {conn_test.get('error')}")
                # Show retry button outside any form
                if st.button("🔄 Retry Connection", key="retry_conn"):
                    st.session_state.processing_goal = False
                    st.rerun()
                return
        with col2:
            st.write("**Authentication**")
            auth_test = task_manager.test_auth()
            if auth_test.get('success'):
                st.success(f"✅ Logged in as {auth_test.get('user', {}).get('email', 'Unknown')}")
            else:
                st.error(f"❌ Auth failed: {auth_test.get('error')}")
                if st.button("🔄 Retry Auth", key="retry_auth"):
                    st.session_state.processing_goal = False
                    st.rerun()
                return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Make the API call directly (no threading)
    try:
        # Show initial progress
        progress_bar.progress(10)
        status_text.info("🤖 Starting AI classification...")
        
        # Make the API call with progress updates
        with st.spinner("AI is analyzing your goal and generating tasks. This may take 30-60 seconds..."):
            result = task_manager.create_goal_classify_only(goal_data)
        
        if result and result.get('success'):
            progress_bar.progress(100)
            status_text.success("✅ Classification Complete!")
            
            # Store result and show review
            st.session_state.ai_goal_result = result
            st.session_state.show_ai_review = True
            st.session_state.processing_goal = False
            
            st.balloons()
            time.sleep(2)  # Let user see success message
            st.rerun()
        else:
            progress_bar.progress(0)
            error_msg = result.get('error') if result else "Unknown error occurred"
            status_text.error(f"❌ Failed: {error_msg}")
            
            # Show error details and retry option
            with st.expander("🔍 Error Details", expanded=True):
                st.write(f"**Error:** {error_msg}")
                st.write("**Possible solutions:**")
                st.write("- Check your internet connection")
                st.write("- Simplify the goal description")
                st.write("- Try again in a few moments")
                
            # Retry and back buttons - OUTSIDE any form
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Retry Classification", key="retry_classification", use_container_width=True):
                    st.rerun()
            with col2:
                if st.button("← Back to Form", key="back_to_form", use_container_width=True):
                    st.session_state.processing_goal = False
                    st.rerun()
                    
    except Exception as e:
        progress_bar.progress(0)
        status_text.error(f"❌ Unexpected error: {str(e)}")
        
        # Error recovery options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Retry", key="retry_unexpected", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("← Back to Form", key="back_from_error", use_container_width=True):
                st.session_state.processing_goal = False
                st.rerun()
# Update the get_task_manager function to handle both cases
@st.cache_data(ttl=300)
def get_task_manager(token=None):
    if token:
        return TaskManager(config.BACKEND_URL, token)
    return TaskManager(config.BACKEND_URL)

def show_ai_classification_review():
    result = st.session_state.ai_goal_result
    with st.expander("🔧 Debug", expanded=False):
        st.write("### AI Results")
        st.json({
            'success': result.get('success'),
            'ai_meta_id': result.get('ai_meta_id'),
            'ai_processing_time': result.get('ai_processing_time'),
            'ai_tasks_count': len(result.get('ai_tasks', [])),
            'ai_breakdown': result.get('ai_breakdown')
        })
        if result.get('ai_meta_id'):
            task_manager = get_task_manager()
            progress_response = task_manager.get_ai_progress(result['ai_meta_id'])
            if progress_response.get('success'):
                st.write("### AI Meta")
                st.json(progress_response['ai_meta'])
            else:
                st.error(f"Failed to load AI meta: {progress_response.get('error')}")
    
    if st.button("← Create Another Goal"):
        for key in ['show_ai_review', 'ai_goal_result', 'processing_complete', 'current_ai_meta_id']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    if result.get('ai_processing_time'):
        st.success(f"⏱️ Classification: {result['ai_processing_time']:.1f}s")
    
    if result.get('ai_breakdown'):
        with st.expander("🤖 Analysis", expanded=True):
            st.write(result['ai_breakdown'])
    
    if result.get('ai_tasks'):
        st.info(f"🤖 Generated {len(result['ai_tasks'])} tasks!")
        st.write("### 🎯 Tasks")
        for i, task in enumerate(result['ai_tasks']):
            show_classified_task_card(task, i, get_task_manager())
    else:
        st.error("❌ No tasks generated. Check debug info.")
    
    st.balloons()
def show_classified_task_card(task, index, task_manager):
    """Show task card with RAG employee recommendations button - FIXED VERSION"""
    with st.container():
        st.markdown("---")
        
        # Main card layout
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.subheader(f"📋 Task {index + 1}: {task['task_description']}")
            
            # Task details in a compact layout
            col1a, col1b, col1c = st.columns(3)
            with col1a:
                st.write(f"**Due:** {task.get('due_date', 'Not set')[:10]}")
                st.write(f"**Priority:** {task.get('priority', 'medium').title()}")
            with col1b:
                st.write(f"**Hours:** {task.get('estimated_hours', 8)}")
                st.write(f"**Status:** {task.get('status', 'ai_suggested').title()}")
            with col1c:
                strategic_meta = task.get('strategic_metadata', {})
                st.write(f"**Complexity:** {strategic_meta.get('complexity', 'medium').title()}")
            
            # Skills
            if strategic_meta.get('required_skills', []):
                st.write("**Required Skills:**")
                skill_chips = " ".join([f"`{skill}`" for skill in strategic_meta['required_skills'][:5]])
                st.markdown(skill_chips)
            
            # Success criteria
            if strategic_meta.get('success_criteria'):
                with st.expander("✅ Success Criteria", expanded=False):
                    st.write(strategic_meta['success_criteria'])
        
            # ===== NEW: OTHER DETAILS EXPANDER =====
            show_other_details_expander(task, strategic_meta)
            
            # ===== RAG BUTTONS IN MAIN TASK AREA - FIXED =====
            task_key = f"task_{task['id']}_{index}"
            if task_key not in st.session_state:
                st.session_state[task_key] = {
                    'show_approve_form': False,
                    'show_edit_form': False,
                    'show_recommendations': False,
                    'rag_loading': False,
                    'rag_ai_meta_id': None,
                    'selected_recommendation': None,
                    'approved': False
                }
            
            state = st.session_state[task_key]
            strategic_meta = task.get('strategic_metadata', {})
            
            # RAG button in the main task area - FIXED LOGIC
            has_recommendations = strategic_meta.get('employee_recommendations_available', False)
            recommendations_failed = strategic_meta.get('recommendations_failed', False)
            
            # Handle RAG loading state - FIXED: Check if we're in loading state first
            if state.get('rag_loading', False):
                # Show loading state and handle the RAG process
                show_rag_loading_state_main(task, task_manager, task_key)
                
            elif has_recommendations:
                recommendations_generated_at = strategic_meta.get('recommendations_generated_at')
                button_label = "🔍 View RAG Recommendations"
                    
                if recommendations_generated_at:
                    try:
                        gen_time = datetime.fromisoformat(recommendations_generated_at.replace('Z', ''))
                        time_diff = datetime.utcnow() - gen_time
                        if time_diff.days > 0:
                            time_text = f"({time_diff.days}d ago)"
                        elif time_diff.seconds > 3600:
                            time_text = f"({time_diff.seconds // 3600}h ago)"
                        else:
                            time_text = f"({time_diff.seconds // 60}m ago)"
                        
                        button_label = f"🔍 View RAG Recommendations {time_text}"
                    except:
                        pass
                        
                col_rag1, col_rag2 = st.columns(2)
                with col_rag1:
                    if st.button(button_label, key=f"view_rec_{task['id']}_{index}", use_container_width=True):
                        state['show_recommendations'] = True
                        state['show_approve_form'] = False
                        state['show_edit_form'] = False
                        st.rerun()
                with col_rag2:
                    if st.button("🔄 Refresh RAG", key=f"rag_refresh_{task['id']}_{index}", use_container_width=True):
                        state['rag_loading'] = True
                        state['rag_ai_meta_id'] = None
                        st.rerun()
                        
            elif recommendations_failed:
                col_rag1, col_rag2 = st.columns(2)
                with col_rag1:
                    st.button("❌ RAG Recommendations Failed", key=f"failed_{task['id']}_{index}", use_container_width=True, disabled=True)
                with col_rag2:
                    if st.button("🔍 Retry RAG", key=f"try_rag_{task['id']}_{index}", use_container_width=True):
                        state['rag_loading'] = True
                        state['rag_ai_meta_id'] = None
                        st.rerun()
            else:
                if st.button("🔍 Get RAG Recommendations", key=f"get_rag_{task['id']}_{index}", use_container_width=True):
                    state['rag_loading'] = True
                    state['rag_ai_meta_id'] = None
                    st.rerun()
        
        with col2:
            st.write("### Actions")
            
            # Only show Approve & Assign and Edit Task in the actions column
            state = st.session_state[task_key]
            
            # Button 1: Approve & Assign
            if not state['show_approve_form']:
                if st.button("✅ Approve & Assign", key=f"approve_{task['id']}_{index}", use_container_width=True):
                    state['show_approve_form'] = True
                    state['show_edit_form'] = False
                    state['show_recommendations'] = False
                    st.rerun()
            else:
                # We'll handle this in the main flow
                pass
            
            # Button 2: Edit Task
            if not state['show_edit_form']:
                if st.button("✏️ Edit Task", key=f"edit_{task['id']}_{index}", use_container_width=True):
                    state['show_edit_form'] = True
                    state['show_approve_form'] = False
                    state['show_recommendations'] = False
                    st.rerun()
            else:
                # We'll handle this in the main flow
                pass

            # Handle forms and recommendations that need full width
            state = st.session_state[task_key]
            
    # Show approve form if active
    if state.get('show_approve_form'):
        show_approve_assignment_form(task, task_manager, task_key)
    
    # Show edit form if active  
    elif state.get('show_edit_form'):
        show_edit_task_form(task, task_manager, task_key)
    
    # Show recommendations if active - with full width
    elif state.get('show_recommendations'):
        # Create full-width area for recommendations
        st.markdown("---")
        show_employee_recommendations(task, task_manager, task_key)

def show_other_details_expander(task, strategic_meta):
    """Show additional strategic details in an expander"""
    
    # Get the AI meta data from various sources
    output_json = strategic_meta.get('output_json', {})
    ai_meta_data = strategic_meta.get('strategic_analysis', {})
    
    # Collect all the strategic information
    sections = []
    
    # From output_json (direct AI response)
    if output_json and isinstance(output_json, dict):
        # WIG Alignment
        if output_json.get('wig_alignment'):
            sections.append(("🎯", "WIG Alignment", output_json['wig_alignment']))
        
        # Strategic Analysis
        if output_json.get('strategic_analysis'):
            sections.append(("📈", "Strategic Analysis", output_json['strategic_analysis']))
        
        # Validation Score
        if output_json.get('validation_score'):
            sections.append(("✅", "Validation Score", output_json['validation_score']))
        
        # Q4 Execution Context
        if output_json.get('q4_execution_context'):
            sections.append(("📅", "Q4 Execution Context", output_json['q4_execution_context']))
        
        # Tasks Generated
        if output_json.get('tasks_generated'):
            sections.append(("📋", "Tasks Generated", f"{output_json['tasks_generated']} tasks"))
    
    # From strategic_analysis (nested analysis)
    if ai_meta_data and isinstance(ai_meta_data, dict):
        # Strategic Alignment
        if ai_meta_data.get('strategic_alignment'):
            sections.append(("🔗", "Strategic Alignment", ai_meta_data['strategic_alignment']))
        
        # Q4 Execution Context (from strategic_analysis)
        if ai_meta_data.get('q4_execution_context') and not any("Q4 Execution" in title for _, title, _ in sections):
            sections.append(("📅", "Q4 Execution", ai_meta_data['q4_execution_context']))
        
        # Criteria Analysis
        if ai_meta_data.get('criteria_analysis') and isinstance(ai_meta_data['criteria_analysis'], dict):
            criteria_text = ""
            for criterion, analysis in ai_meta_data['criteria_analysis'].items():
                if analysis and analysis.strip():
                    criteria_text += f"• **{criterion.replace('_', ' ').title()}:** {analysis}\n"
            if criteria_text:
                sections.append(("📊", "Criteria Analysis", criteria_text))
    
    # From task's strategic_metadata
    # Strategic Phase
    if strategic_meta.get('strategic_phase'):
        sections.append(("🔄", "Strategic Phase", strategic_meta['strategic_phase']))
    
    # Key Stakeholders
    if strategic_meta.get('key_stakeholders'):
        stakeholders = strategic_meta['key_stakeholders']
        if isinstance(stakeholders, list) and stakeholders:
            sections.append(("👥", "Key Stakeholders", ", ".join(stakeholders)))
    
    # Potential Bottlenecks
    if strategic_meta.get('potential_bottlenecks'):
        bottlenecks = strategic_meta['potential_bottlenecks']
        if isinstance(bottlenecks, list) and bottlenecks:
            sections.append(("⚠️", "Potential Bottlenecks", " • ".join(bottlenecks)))
    
    # Resource Requirements
    if strategic_meta.get('resource_requirements'):
        resources = strategic_meta['resource_requirements']
        if isinstance(resources, list) and resources:
            sections.append(("🛠️", "Resource Requirements", " • ".join(resources)))
    
    # RAG Information
    if strategic_meta.get('rag_enhanced'):
        sections.append(("🔍", "RAG Enhanced", "JD documents analyzed for better matching"))
    
    if strategic_meta.get('employees_with_jd'):
        sections.append(("📄", "JD Analysis", f"Analyzed {strategic_meta['employees_with_jd']} employee JD documents"))
    
    # From the task itself (for backward compatibility)
    if task.get('strategic_outcome'):
        sections.append(("🎯", "Strategic Outcome", task['strategic_outcome']))
    
    # Success Metrics (if available in task)
    if task.get('success_metrics'):
        metrics = task['success_metrics']
        if isinstance(metrics, list) and metrics:
            sections.append(("📊", "Success Metrics", " • ".join(metrics)))
    
    # Show the expander only if there are details to display
    if sections:
        with st.expander("📊 Other Details", expanded=False):
            for icon, title, content in sections:
                st.write(f"{icon} **{title}**")
                
                if isinstance(content, list):
                    # Handle list items with bullet points
                    for item in content:
                        st.write(f"   • {item}")
                elif isinstance(content, dict):
                    # Handle nested dictionaries
                    for key, value in content.items():
                        if value and value not in ([], {}, ""):
                            formatted_key = key.replace('_', ' ').title()
                            st.write(f"   - **{formatted_key}:** {value}")
                else:
                    # Handle string content with proper formatting
                    content_str = str(content)
                    if len(content_str) > 200:
                        # For long text, use a scrollable area
                        st.text_area("", value=content_str, height=100, key=f"details_{title}_{task['id']}", label_visibility="collapsed")
                    else:
                        # For shorter text, just display it
                        st.write(f"   {content_str}")
                
                st.write("")  # Add spacing between sections
    else:
        # Optional: Show a message if no details available
        with st.expander("📊 Other Details", expanded=False):
            st.info("No additional strategic details available for this task.")      

def show_rag_loading_state_main(task, task_manager, task_key):
    """Show RAG loading state in the main task area - FIXED VERSION"""
    state = st.session_state[task_key]
    
    # Show loading UI in the main task area
    st.button("🔍 RAG Analysis in Progress...", 
             key=f"rag_loading_main_{task['id']}", use_container_width=True, disabled=True)
    
    # Check if we have an AI meta ID for tracking
    if not state.get('rag_ai_meta_id'):
        # Start RAG recommendations
        with st.spinner("🚀 Starting RAG-enhanced analysis with JD documents..."):
            result = task_manager.generate_rag_recommendations(task['id'])
            
        if result.get('success'):
            state['rag_ai_meta_id'] = result['ai_meta_id']
            st.rerun()
        else:
            st.error(f"❌ Failed to start RAG analysis: {result.get('error')}")
            state['rag_loading'] = False
            st.rerun()
        return
            
    # Poll for progress
    try:
        progress_data = task_manager.get_rag_recommendation_progress(state['rag_ai_meta_id'])
        
        if progress_data.get('success') and progress_data.get('ai_meta'):
            ai_meta = progress_data['ai_meta']
            output_json = ai_meta.get('output_json', {})
            status = output_json.get('status', 'processing')
            progress = output_json.get('progress', 0)
            current_activity = output_json.get('current_activity', 'Processing JD documents...')
            
            # Show progress with a progress bar
            st.progress(progress / 100)
            st.info(f"🔍 {current_activity} ({progress}%)")
            
            if status == 'completed':
                state['rag_loading'] = False
                state['show_recommendations'] = True
                time.sleep(1)  # Let user see completion
                st.rerun()
            elif status == 'error':
                st.error(f"❌ RAG analysis failed: {output_json.get('error', 'Unknown error')}")
                state['rag_loading'] = False
                st.rerun()
            else:
                # Continue polling after 3 seconds
                time.sleep(3)
                st.rerun()
        else:
            # Handle API error
            error_msg = progress_data.get('error', 'Failed to get RAG progress')
            st.error(f"❌ Progress check failed: {error_msg}")
            state['rag_loading'] = False
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        state['rag_loading'] = False
        st.rerun()

def show_task_action_buttons(task, task_manager, index, task_key):
    """Show only the basic action buttons - RAG moved to main task area"""
    
    state = st.session_state[task_key]
    
    # Ensure all required keys are in the state
    required_keys = ['show_approve_form', 'show_edit_form', 'show_recommendations', 
                    'rag_loading', 'rag_ai_meta_id', 'selected_recommendation', 'approved']
    
    for key in required_keys:
        if key not in state:
            if key == 'rag_loading':
                state[key] = False
            elif key == 'rag_ai_meta_id':
                state[key] = None
            elif key == 'selected_recommendation':
                state[key] = None
            elif key == 'approved':
                state[key] = False
            else:
                state[key] = False
    
    # Button 1: Approve & Assign
    if not state['show_approve_form']:
        if st.button("✅ Approve & Assign", key=f"approve_{task['id']}", use_container_width=True):
            state['show_approve_form'] = True
            state['show_edit_form'] = False
            state['show_recommendations'] = False
            st.rerun()
    else:
        show_approve_assignment_form(task, task_manager, task_key)
        return
    
    # Button 2: Edit Task
    if not state['show_edit_form']:
        if st.button("✏️ Edit Task", key=f"edit_{task['id']}", use_container_width=True):
            state['show_edit_form'] = True
            state['show_approve_form'] = False
            state['show_recommendations'] = False
            st.rerun()
    else:
        show_edit_task_form(task, task_manager, task_key)
        return
    
    # RAG recommendations have been moved to the main task details area
    # No RAG logic here anymore


def show_approve_assignment_form(task, task_manager, task_key):
    """Form to approve task and assign employees with AI recommendations"""
    st.write("### ✅ Approve & Assign Task")
    
    from employee_management import get_all_employees
    employees = get_all_employees()
    active_employees = [e for e in employees if e.get('is_active', True)]
    employee_options = {f"{e['id']} - {e['name']} ({e['role']})": e['id'] for e in active_employees}
    
    # Check if we have a selected AI recommendation
    selected_recommendation = st.session_state[task_key].get('selected_recommendation')
    default_employees = []
    
    if selected_recommendation:
        st.success(f"🎯 Using AI Recommendation: {selected_recommendation.get('employee_name')} (Fit: {selected_recommendation.get('fit_score')}%)")
        # Pre-select the recommended employee
        emp_id = selected_recommendation['employee_id']
        for key, value in employee_options.items():
            if value == emp_id:
                default_employees = [key]
                break
    
    # Multiple assignees selection
    assigned_employees = st.multiselect(
        "Assign to employees*",
        options=list(employee_options.keys()),
        default=default_employees,
        help="Select one or more employees for this task"
    )
    
    # Show AI recommendations summary if available
    strategic_meta = task.get('strategic_metadata', {})
    if strategic_meta.get('ai_recommendations'):
        with st.expander("🤖 AI Recommendations Summary", expanded=False):
            for i, rec in enumerate(strategic_meta['ai_recommendations'][:3]):
                st.write(f"**{i+1}. {rec.get('employee_name')}** - Fit: {rec.get('fit_score')}%")
                st.write(f"   Reason: {rec.get('reason', 'No reason provided')}")
    
    # Additional assignment options
    col1, col2 = st.columns(2)
    with col1:
        new_due_date = st.date_input("Due Date", 
                                   value=datetime.fromisoformat(task['due_date'].replace('Z', '')).date() if task.get('due_date') else datetime.now().date() + timedelta(days=7))
    with col2:
        new_priority = st.selectbox("Priority", ["low", "medium", "high"], 
                                  index=["low", "medium", "high"].index(task.get('priority', 'medium')))
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Approve & Assign", use_container_width=True):
            if not assigned_employees:
                st.error("Please assign the task to at least one employee")
                return
            
            # Prepare update data
            assignee_ids = [employee_options[emp] for emp in assigned_employees]
            update_data = {
                'status': 'not_started',
                'assigned_to': assignee_ids[0],  # Primary assignee
                'assigned_to_multiple': assignee_ids,  # All assignees
                'due_date': new_due_date.isoformat(),
                'priority': new_priority,
                'ai_suggested': False  # Now approved by admin
            }
            
            result = task_manager.update_task(task['id'], update_data)
            if result.get('success'):
                st.success("✅ Task approved and assigned!")
                st.session_state[task_key]['show_approve_form'] = False
                st.session_state[task_key]['approved'] = True
                if 'selected_recommendation' in st.session_state[task_key]:
                    del st.session_state[task_key]['selected_recommendation']
                st.rerun()
            else:
                st.error(f"❌ Failed to approve: {result.get('error')}")
    
    with col2:
        if st.button("💾 Save Only", use_container_width=True):
            if not assigned_employees:
                st.error("Please assign the task to at least one employee")
                return
                
            assignee_ids = [employee_options[emp] for emp in assigned_employees]
            update_data = {
                'assigned_to': assignee_ids[0],
                'assigned_to_multiple': assignee_ids,
                'due_date': new_due_date.isoformat(),
                'priority': new_priority
            }
            
            result = task_manager.update_task(task['id'], update_data)
            if result.get('success'):
                st.success("✅ Task updated!")
                st.session_state[task_key]['show_approve_form'] = False
                if 'selected_recommendation' in st.session_state[task_key]:
                    del st.session_state[task_key]['selected_recommendation']
                st.rerun()
            else:
                st.error(f"❌ Failed to update: {result.get('error')}")
    
    with col3:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state[task_key]['show_approve_form'] = False
            if 'selected_recommendation' in st.session_state[task_key]:
                del st.session_state[task_key]['selected_recommendation']
            st.rerun()

def show_edit_task_form(task, task_manager, task_key):
    st.write("### ✏️ Edit Task")
    current_description = task.get('task_description', '')
    current_due_date = task.get('due_date', '')
    current_priority = task.get('priority', 'medium')
    current_hours = task.get('estimated_hours', 8)
    
    new_description = st.text_area("Task Description", value=current_description, height=100)
    col1, col2 = st.columns(2)
    with col1:
        default_date = datetime.now().date() + timedelta(days=7)
        if current_due_date:
            try:
                default_date = datetime.fromisoformat(current_due_date.replace('Z', '')).date()
            except:
                pass
        new_due_date = st.date_input("Due Date", value=default_date)
        new_priority = st.selectbox("Priority", ["low", "medium", "high"], index=["low", "medium", "high"].index(current_priority))
    with col2:
        new_hours = st.number_input("Estimated Hours", min_value=1, max_value=200, value=current_hours)
    
    from employee_management import get_all_employees
    employees = get_all_employees()
    employee_options = {f"{e['id']} - {e['name']}": e['id'] for e in employees if e.get('is_active', True)}
    default_employee = None
    strategic_meta = task.get('strategic_metadata', {})
    if strategic_meta.get('ai_recommendations'):
        emp_id = strategic_meta['ai_recommendations'][0].get('employee_id')
        for key, value in employee_options.items():
            if value == emp_id:
                default_employee = key
                break
    
    assigned_employee = st.selectbox("Assign to", options=list(employee_options.keys()), 
                                    index=list(employee_options.keys()).index(default_employee) if default_employee else 0)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Save & Approve", use_container_width=True):
            update_task_and_approve(task, task_manager, task_key, {
                'task_description': new_description,
                'due_date': new_due_date.isoformat(),
                'priority': new_priority,
                'estimated_hours': new_hours,
                'assigned_to': employee_options[assigned_employee],
                'status': 'not_started',
                'ai_suggested': False
            })
    with col2:
        if st.button("💾 Save Only", use_container_width=True):
            update_task_and_approve(task, task_manager, task_key, {
                'task_description': new_description,
                'due_date': new_due_date.isoformat(),
                'priority': new_priority,
                'estimated_hours': new_hours,
                'assigned_to': employee_options[assigned_employee],
                'status': 'ai_suggested'
            }, approve=False)
    with col3:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state[task_key]['editing'] = False
            st.rerun()

def update_task_and_approve(task, task_manager, task_key, update_data, approve=True):
    result = task_manager.update_task(task['id'], update_data)
    if result.get('success'):
        st.session_state[task_key]['approved'] = approve
        st.success("✅ Task updated and approved!" if approve else "✅ Task updated!")
        emp_id = update_data.get('assigned_to')
        if emp_id:
            from employee_management import get_all_employees
            employee = next((e for e in get_all_employees() if e['id'] == emp_id), None)
            if employee:
                st.info(f"📨 Notified: {employee.get('name', 'employee')}")
        st.session_state[task_key]['editing'] = False
        st.rerun()
    else:
        st.error(f"❌ Failed: {result.get('error')}")


def show_employee_recommendations(task, task_manager, task_key):
    """Show RAG employee recommendations for a task in proper card layout"""
    # Centered title
    st.markdown(
        """
        <h2 style="text-align: center;">👥 RAG Employee Recommendations</h2>
        """,
        unsafe_allow_html=True
    )
    
    # Check if RAG-enhanced recommendations are available
    strategic_meta = task.get('strategic_metadata', {})
    is_rag_enhanced = strategic_meta.get('rag_enhanced', False)
    
    if is_rag_enhanced:
        st.success("🎯 **RAG-Enhanced Analysis** - Using JD documents for precise employee matching")
    
    # Load fresh recommendations data
    with st.spinner("🔄 Loading RAG recommendations..."):
        recommendations_data = task_manager.get_task_employee_recommendations(task['id'])
    
    if not recommendations_data.get('success'):
        st.error(f"❌ Failed to load recommendations: {recommendations_data.get('error')}")
        
        # Retry / back options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Retry", key=f"retry_load_{task['id']}", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("← Back to Task", key=f"back_error_{task['id']}", use_container_width=True):
                st.session_state[task_key]['show_recommendations'] = False
                st.rerun()
        return
    
    recommendations = recommendations_data.get('recommendations', [])
    
    if not recommendations:
        st.info("📭 No RAG employee recommendations available yet.")
        if st.button("🔍 Generate RAG Recommendations", key=f"generate_rag_{task['id']}", use_container_width=True):
            st.session_state[task_key]['rag_loading'] = True
            st.rerun()
        return
    
    # Show analysis summary if available
    analysis = strategic_meta.get('recommendations_analysis', '')
    total_considered = strategic_meta.get('total_employees_considered', 0)
    
    if analysis or total_considered:
        with st.expander("📊 RAG Analysis Summary", expanded=True):
            if total_considered:
                st.write(f"**Employees analyzed:** {total_considered}")
            if is_rag_enhanced:
                st.write(f"**JD Documents analyzed:** {strategic_meta.get('employees_with_jd', 0)}")
            if analysis:
                st.write("**Analysis:**", analysis)
    
    # Centered subtitle
    st.markdown(
        f"<h3 style='text-align: center;'>🎯 Top {len(recommendations)} Recommendations</h3>",
        unsafe_allow_html=True
    )
    
    # Center each recommendation card using columns
    for i, rec in enumerate(recommendations):
            show_rag_recommendation_card(task, task_manager, task_key, rec, i, is_rag_enhanced)
        
        
def show_rag_recommendation_card(task, task_manager, task_key, rec, index, is_rag_enhanced):
    """Show RAG recommendation in a proper card layout - FULL WIDTH"""
    
    # Card container using full width layout
    with st.container():
        st.markdown("---")
        
        # Full width header with employee name and fit score
        col_header1, col_header2, col_header3 = st.columns([2, 1, 1])
        
        with col_header1:
            st.subheader(f"👤 {rec.get('employee_name', 'Unknown Employee')}")
            
            # Role and department
            role_dept = []
            if rec.get('employee_role'):
                role_dept.append(rec['employee_role'])
            if rec.get('employee_department'):
                role_dept.append(rec['employee_department'])
            if role_dept:
                st.write(f"**Role:** {' - '.join(role_dept)}")
        
        with col_header2:
            # Fit score - large and prominent
            fit_score = rec.get('fit_score', 0)
            st.metric("Fit Score", f"{fit_score}%")
            
        with col_header3:
            # Confidence level
            confidence = rec.get('confidence', 'medium')
            confidence_color = {
                'high': 'green',
                'medium': 'orange', 
                'low': 'red'
            }.get(confidence, 'gray')
            st.markdown(
                f"<span style='color: {confidence_color}; font-weight: 600;'>🔍 {confidence.upper()} CONFIDENCE</span>",
                unsafe_allow_html=True
            )
            
            # RAG-enhanced flag
            if is_rag_enhanced:
                st.success("🔍 RAG Enhanced")
                rag_score = rec.get('rag_enhanced_score')
                if rag_score is not None:
                    st.metric("RAG Score", f"{rag_score}%")
            
        # Key qualifications section
            qualifications = rec.get('key_qualifications', [])
            if qualifications and isinstance(qualifications, list):
                st.write("**Key Skills:**")
            skill_chips = " ".join([f"`{skill}`" for skill in qualifications[:8]])
            st.markdown(skill_chips)
            
            # Skills match details
            skills_matches = rec.get('skills_match_list', rec.get('skills_match', []))
            if skills_matches and isinstance(skills_matches, list) and len(skills_matches) > 0:
                with st.expander(f"🔧 Matching Skills ({len(skills_matches)})", expanded=False):
                    for skill in skills_matches[:10]:  # Show top 10 matching skills
                        st.write(f"✅ {skill}")
            
            # Reason for recommendation
            reason = rec.get('reason', '')
            if reason:
                with st.expander("📊 Analysis Details", expanded=False):
                    st.write(reason)
            
        # Action buttons
        st.divider()
        show_rag_recommendation_actions(task, task_manager, task_key, rec, index)

def show_rag_recommendation_actions(task, task_manager, task_key, rec, index):
    """Show action buttons for RAG recommendations in a clean layout"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button(
            f"✅ Assign to {rec.get('employee_name', 'Employee')}", 
            key=f"assign_{index}_{task['id']}", 
            use_container_width=True,
            type="primary"
        ):
            # Apply this recommendation
            result = task_manager.apply_employee_recommendation(
                task['id'], 
                rec['employee_id'],
                rec
            )
            
            if result.get('success'):
                st.toast(f"✅ Task assigned to {rec.get('employee_name', 'employee')}!", icon="📩")
                st.session_state[task_key]['show_recommendations'] = False
                st.balloons()
                st.rerun()
            else:
                st.error(f"❌ Failed to assign: {result.get('error')}")
    
    with col2:
        # Use this recommendation in approve form
        if st.button(
            "✏️ Use in Form", 
            key=f"use_{index}_{task['id']}", 
            use_container_width=True
        ):
            st.session_state[task_key]['show_recommendations'] = False
            st.session_state[task_key]['show_approve_form'] = True
            st.session_state[task_key]['selected_recommendation'] = rec
            st.rerun()
    
    with col3:
        if st.button(
            "📊 View Profile", 
            key=f"profile_{index}_{task['id']}", 
            use_container_width=True
        ):
            # Store employee ID for profile view
            st.session_state['view_employee_profile'] = rec['employee_id']
            st.info(f"Would show profile for {rec.get('employee_name', 'employee')}")
            
def show_enhanced_recommendation_card(task, task_manager, task_key, rec, index, is_rag_enhanced):
    """Show cleaned up recommendation card with simplified layout"""
    with st.container():
        st.markdown("---")
        
        # Use columns for clean layout
        col_score, col_info = st.columns([1, 3])
        
        with col_score:
            # Fit score with metric display
            fit_score = rec.get('fit_score', 0)
            st.metric("Fit Score", f"{fit_score}%")
            
            # RAG-enhanced badge
            if is_rag_enhanced:
                st.success("🔍 RAG")
            
            # Confidence level
            confidence = rec.get('confidence', 'medium')
            confidence_color = {
                'high': 'green',
                'medium': 'orange', 
                'low': 'red'
            }.get(confidence, 'gray')
            st.markdown(f"<span style='color: {confidence_color}; font-weight: bold;'>🔍 {confidence.upper()} CONFIDENCE</span>", unsafe_allow_html=True)
        
        with col_info:
            # Employee info
            st.write(f"**{rec.get('employee_name', 'Unknown Employee')}**")
            st.write(f"*{rec.get('employee_role', 'Not specified')} - {rec.get('employee_department', 'Not specified')}*")
            
            # Key qualifications (limited display)
            qualifications = rec.get('key_qualifications', [])
            if qualifications and isinstance(qualifications, list):
                st.caption(", ".join(qualifications[:3]))
            elif qualifications:
                st.caption(str(qualifications))
            
            # Skills match - FIXED: Handle both list and other types safely
            skills_matches = rec.get('skills_match_list', rec.get('skills_match', []))
            if skills_matches and isinstance(skills_matches, list):
                with st.expander("🔧 Skills Match", expanded=False):
                    st.info(" | ".join(skills_matches[:3]))
            elif skills_matches:
                with st.expander("🔧 Skills Match", expanded=False):
                    st.info(str(skills_matches))
            
            # Reason for recommendation
            reason = rec.get('reason', '')
            if reason:
                with st.expander("🤖 AI Analysis", expanded=False):
                    st.write(reason)
        
        # Action buttons - simplified
        show_simplified_recommendation_actions(task, task_manager, task_key, rec, index)

def show_simplified_recommendation_actions(task, task_manager, task_key, rec, index):
    """Show simplified action buttons for recommendations"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button(f"✅ Assign to {rec.get('employee_name', 'Employee')}", 
                   key=f"assign_{index}_{task['id']}", use_container_width=True):
            # Apply this recommendation
            result = task_manager.apply_employee_recommendation(
                task['id'], 
                rec['employee_id'],
                rec
            )
            
            if result.get('success'):
                st.toast(f"✅ Task assigned to {rec.get('employee_name', 'employee')}!", icon="📩")
                st.session_state[task_key]['show_recommendations'] = False
                st.balloons()
                st.rerun()
            else:
                st.error(f"❌ Failed to assign: {result.get('error')}")
    
    with col2:
        # Use this recommendation in approve form
        if st.button("✏️ Use in Form", key=f"use_{index}_{task['id']}", use_container_width=True):
            st.session_state[task_key]['show_recommendations'] = False
            st.session_state[task_key]['show_approve_form'] = True
            st.session_state[task_key]['selected_recommendation'] = rec
            st.rerun()

def show_recommendation_actions(task, task_manager, task_key, rec, index):
    """Show action buttons for a recommendation"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button(f"✅ Assign to {rec.get('employee_name', 'Employee')}", 
                   key=f"assign_{index}_{task['id']}", use_container_width=True):
            # Apply this recommendation
            result = task_manager.apply_employee_recommendation(
                task['id'], 
                rec['employee_id'],
                rec
            )
            
            if result.get('success'):
                st.success(f"✅ Task assigned to {rec.get('employee_name', 'employee')}!")
                st.session_state[task_key]['show_recommendations'] = False
                st.balloons()
                st.rerun()
            else:
                st.error(f"❌ Failed to assign: {result.get('error')}")
    
    with col2:
        # Use this recommendation in approve form
        if st.button("✏️ Use in Form", key=f"use_{index}_{task['id']}", use_container_width=True):
            st.session_state[task_key]['show_recommendations'] = False
            st.session_state[task_key]['show_approve_form'] = True
            st.session_state[task_key]['selected_recommendation'] = rec
            st.rerun()
    
    with col3:
        if st.button("👤 View Profile", key=f"profile_{index}_{task['id']}", use_container_width=True):
            # Store employee ID for profile view
            st.session_state['view_employee_profile'] = rec['employee_id']
            st.info(f"Would show profile for {rec.get('employee_name', 'employee')}")

def show_task_action_buttons(task, task_manager, index, task_key):
    """Show the three action buttons for each task with ONLY RAG recommendations"""
    
    state = st.session_state[task_key]
    strategic_meta = task.get('strategic_metadata', {})
    
    # Ensure all required keys are in the state
    required_keys = ['show_approve_form', 'show_edit_form', 'show_recommendations', 
                    'rag_loading', 'rag_ai_meta_id', 'selected_recommendation', 'approved']
    
    for key in required_keys:
        if key not in state:
            if key == 'rag_loading':
                state[key] = False
            elif key == 'rag_ai_meta_id':
                state[key] = None
            elif key == 'selected_recommendation':
                state[key] = None
            elif key == 'approved':
                state[key] = False
            else:
                state[key] = False
    
    # Button 1: Approve & Assign
    if not state['show_approve_form']:
        if st.button("✅ Approve & Assign", key=f"approve_{task['id']}", use_container_width=True):
            state['show_approve_form'] = True
            state['show_edit_form'] = False
            state['show_recommendations'] = False
            st.rerun()
    else:
        show_approve_assignment_form(task, task_manager, task_key)
        return
    
    # Button 2: Edit Task
    if not state['show_edit_form']:
        if st.button("✏️ Edit Task", key=f"edit_{task['id']}", use_container_width=True):
            state['show_edit_form'] = True
            state['show_approve_form'] = False
            state['show_recommendations'] = False
            st.rerun()
    else:
        show_edit_task_form(task, task_manager, task_key)
        return
    
    # Button 3: ONLY RAG Employee Recommendations (removed AI button)
    has_recommendations = strategic_meta.get('employee_recommendations_available', False)
    recommendations_failed = strategic_meta.get('recommendations_failed', False)
    recommendations_generated_at = strategic_meta.get('recommendations_generated_at')
    is_rag_enhanced = strategic_meta.get('rag_enhanced', False)
    
    # Handle RAG loading state
    if state.get('rag_loading', False):
        show_rag_loading_state(task, task_manager, task_key)
        return
            
    elif has_recommendations:
        show_available_recommendations_ui(task, task_manager, task_key, strategic_meta, is_rag_enhanced)
            
    elif recommendations_failed:
        show_failed_recommendations_ui(task, task_manager, task_key)
    else:
        show_no_recommendations_ui(task, task_manager, task_key)
    
    # Show recommendations if active
    if state['show_recommendations']:
        show_employee_recommendations(task, task_manager, task_key)

def show_rag_loading_state(task, task_manager, task_key):
    """Show RAG-enhanced recommendations loading state"""
    state = st.session_state[task_key]
    
    # Check if we have an AI meta ID for tracking
    if not state.get('rag_ai_meta_id'):
        # Start RAG recommendations
        result = task_manager.generate_rag_recommendations(task['id'])
        if result.get('success'):
            state['rag_ai_meta_id'] = result['ai_meta_id']
            st.toast("🔍 Starting RAG-enhanced analysis with JD documents...", icon="📄")
        else:
            st.error(f"❌ Failed to start RAG analysis: {result.get('error')}")
            state['rag_loading'] = False
        st.rerun()
        return
    
    # Poll for progress
    progress_data = task_manager.get_rag_recommendation_progress(state['rag_ai_meta_id'])
    if progress_data.get('success'):
        ai_meta = progress_data['ai_meta']
        output_json = ai_meta.get('output_json', {})
        status = output_json.get('status', 'processing')
        progress = output_json.get('progress', 0)
        current_activity = output_json.get('current_activity', 'Processing...')
        
        # Show progress
        st.button(f"🔍 RAG Analysis... {progress}% - {current_activity}", 
                 key=f"rag_loading_{task['id']}", use_container_width=True, disabled=True)
        
        if status == 'completed':
            state['rag_loading'] = False
            state['show_recommendations'] = True
            st.rerun()
        elif status == 'error':
            st.error(f"❌ RAG analysis failed: {output_json.get('error')}")
            state['rag_loading'] = False
            st.rerun()
        else:
            # Continue polling
            time.sleep(2)
            st.rerun()
    else:
        st.error(f"❌ Failed to get RAG progress: {progress_data.get('error')}")
        state['rag_loading'] = False
        st.rerun()

def show_regular_loading_state(task, task_manager, task_key):
    """Show regular recommendations loading state"""
    state = st.session_state[task_key]
    
    st.button("⏳ Generating Recommendations...", key=f"loading_{task['id']}", use_container_width=True, disabled=True)
    
    # Check if recommendations are ready
    recommendations_data = task_manager.get_task_employee_recommendations(task['id'])
    if recommendations_data.get('success') and recommendations_data.get('recommendations_available'):
        state['recommendations_loading'] = False
        state['show_recommendations'] = True
        st.rerun()

def show_available_recommendations_ui(task, task_manager, task_key, strategic_meta, is_rag_enhanced):
    """Show UI when recommendations are available - ONLY RAG"""
    state = st.session_state[task_key]
    recommendations_generated_at = strategic_meta.get('recommendations_generated_at')
    
    button_label = "🔍 View RAG Recommendations"
        
    if recommendations_generated_at:
        # Show how long ago recommendations were generated
        try:
            gen_time = datetime.fromisoformat(recommendations_generated_at.replace('Z', ''))
            time_diff = datetime.utcnow() - gen_time
            if time_diff.days > 0:
                time_text = f"({time_diff.days}d ago)"
            elif time_diff.seconds > 3600:
                time_text = f"({time_diff.seconds // 3600}h ago)"
            else:
                time_text = f"({time_diff.seconds // 60}m ago)"
            
            button_label = f"🔍 View RAG Recommendations {time_text}"
        except:
            pass
            
    if st.button(button_label, key=f"view_rec_{task['id']}", use_container_width=True):
        state['show_recommendations'] = True
        state['show_approve_form'] = False
        state['show_edit_form'] = False
        st.rerun()
        
    # Refresh options - ONLY RAG refresh
    if st.button("🔄 Refresh RAG", key=f"rag_refresh_{task['id']}", use_container_width=True):
        state['rag_loading'] = True
        state['rag_ai_meta_id'] = None
        st.rerun()


def show_failed_recommendations_ui(task, task_manager, task_key):
    """Show UI when recommendations failed - ONLY RAG retry"""
    state = st.session_state[task_key]
    
    st.button("❌ RAG Recommendations Failed", key=f"failed_{task['id']}", use_container_width=True, disabled=True)
    
    if st.button("🔍 Retry RAG", key=f"try_rag_{task['id']}", use_container_width=True):
        state['rag_loading'] = True
        state['rag_ai_meta_id'] = None
        st.rerun()

def show_no_recommendations_ui(task, task_manager, task_key):
    """Show UI when no recommendations exist - ONLY RAG option"""
    state = st.session_state[task_key]
    
    if st.button("🔍 Get RAG Recommendations", key=f"get_rag_{task['id']}", use_container_width=True):
        state['rag_loading'] = True
        state['rag_ai_meta_id'] = None
        st.rerun()


def handle_goal_creation_result(result):
    """Handle goal creation result"""
    if result.get('success'):
        st.success("✅ Goal created successfully!")
        
        # Store the result in session state and show AI review
        st.session_state.ai_goal_result = result
        st.session_state.show_ai_review = True
        st.rerun()
    else:
        st.error(f"❌ Failed to create goal: {result.get('error')}")

# ========== DASHBOARD FUNCTIONS ==========

def show_admin_dashboard():
    """Admin task dashboard"""
    st.subheader("📊 Task Management Dashboard")
    
    task_manager = get_task_manager()
    dashboard_data = task_manager.get_task_dashboard()
    
    if not dashboard_data.get('success'):
        st.error(f"Failed to load dashboard: {dashboard_data.get('error')}")
        return
    
    stats = dashboard_data.get('stats', {})
    tasks = dashboard_data.get('tasks', [])
    
    # Display statistics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Tasks", stats.get('total_tasks', 0))
    with col2:
        st.metric("Completed", stats.get('completed_tasks', 0))
    with col3:
        st.metric("Pending", stats.get('pending_tasks', 0))
    with col4:
        st.metric("In Progress", stats.get('in_progress_tasks', 0))
    with col5:
        st.metric("Overdue", stats.get('overdue_tasks', 0))
    
    # Recent tasks
    st.subheader("📋 Recent Tasks")
    if tasks:
        recent_tasks = sorted(tasks, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
        
        for task in recent_tasks:
            with st.expander(f"📌 {task['task_description']} - {task.get('status', 'pending').title()}", expanded=False):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**Assigned to:** {task.get('employees', {}).get('name', 'Unassigned')}")
                    st.write(f"**Goal:** {task.get('objectives', {}).get('title', 'No Goal')}")
                    st.write(f"**Priority:** {task.get('priority', 'medium').title()}")
                    st.write(f"**Deadline:** {task.get('due_date', 'Not set')[:10]}")
                    st.write(f"**Progress:** {task.get('completion_percentage', 0)}%")
                
                with col2:
                    status = task.get('status', 'pending')
                    if status == 'completed':
                        st.success("✅ Completed")
                    elif status == 'in_progress':
                        st.info("🔄 In Progress")
                    else:
                        st.warning("⏳ Pending")
    else:
        st.info("No tasks found.")

# ========== TASK MANAGEMENT FUNCTIONS ==========
def show_task_management():
    st.title("🎯 AI Task Management System")
    if 'last_notification_check' not in st.session_state:
        st.session_state.last_notification_check = datetime.now()
    if (datetime.now() - st.session_state.last_notification_check).seconds > 30:
        st.session_state.last_notification_check = datetime.now()
        st.rerun()
    if st.session_state.get('user_role') in ['admin', 'superadmin']:
        show_admin_task_interface()
    else:
        show_employee_task_interface()

# ========== TASK MANAGEMENT ADMIN - UPDATED WITH NAVIGATION ==========

def show_task_management_admin():
    """Task management for admin with navigation support - FIXED VERSION"""
    st.subheader("📝 Manage All Tasks")
    
    # Check if we have a task ID from notification navigation
    current_task_id = st.session_state.get('current_task_id')
    if current_task_id:
        st.info(f"🎯 Viewing task from notification: {current_task_id}")
        # Clear the navigation state after displaying
        col_nav1, col_nav2 = st.columns([1, 5])
        with col_nav1:
            if st.button("← Back to All Tasks", key="back_to_all_tasks_admin", use_container_width=True):
                clear_task_navigation()
                st.rerun()
    
    task_manager = get_task_manager()
    dashboard_data = task_manager.get_task_dashboard()
    
    if not dashboard_data.get('success'):
        st.error("Failed to load tasks")
        return
    
    tasks = dashboard_data.get('tasks', [])
    
    # If we have a specific task to show, filter to just that task
    if current_task_id:
        filtered_tasks = [t for t in tasks if t.get('id') == current_task_id]
        if not filtered_tasks:
            st.error(f"Task {current_task_id} not found")
            if st.button("← Back to All Tasks", key="back_not_found_admin"):
                clear_task_navigation()
                st.rerun()
            return
    else:
        # Normal filtering for all tasks
        filtered_tasks = tasks
    
    # Filters for admin view
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All", "not_started", "in_progress", "completed", "waiting", "ai_suggested"])
    with col2:
        priority_filter = st.selectbox("Filter by Priority", ["All", "high", "medium", "low"])
    with col3:
        department_filter = st.selectbox("Filter by Department", ["All", "Engineering", "Marketing", "Sales", "QA", "Operations"])
    
    # Apply filters
    if status_filter != "All":
        filtered_tasks = [t for t in filtered_tasks if t.get('status') == status_filter]
    if priority_filter != "All":
        filtered_tasks = [t for t in filtered_tasks if t.get('priority') == priority_filter]
    if department_filter != "All":
        filtered_tasks = [t for t in filtered_tasks if t.get('employees', {}).get('department') == department_filter]
    
    # Sort options for admin
    sort_by = st.selectbox("Sort by", ["Due Date", "Priority", "Status", "Recently Created"])
    
    if sort_by == "Due Date":
        filtered_tasks.sort(key=lambda x: x.get('due_date', ''))
    elif sort_by == "Priority":
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        filtered_tasks.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 2))
    elif sort_by == "Status":
        status_order = {'in_progress': 0, 'not_started': 1, 'waiting': 2, 'ai_suggested': 3, 'completed': 4}
        filtered_tasks.sort(key=lambda x: status_order.get(x.get('status', 'not_started'), 5))
    else:  # Recently Created
        filtered_tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    if not filtered_tasks:
        st.info("No tasks found matching your filters.")
        return
    
    # Display tasks
    for task in filtered_tasks:
        # FIX: Ensure is_current_task is always boolean, not None
        is_current_task = bool(current_task_id and task.get('id') == current_task_id)
        
        with st.expander(
            f"📋 {task['task_description']} - {task.get('employees', {}).get('name', 'Unassigned')}", 
            expanded=is_current_task  # Auto-expand if this is the navigated task
        ):
            show_admin_task_detail_with_attachments(task)
    
    # Clear the navigation state after use if we were showing a specific task and user didn't clear it manually
    if current_task_id and len(filtered_tasks) == 1:
        # Don't auto-clear, let user use the back button
        pass
# ========== EMPLOYEE TASKS WITH ATTACHMENTS - UPDATED WITH NAVIGATION ==========

def show_employee_tasks_with_attachments():
    """Employee task view with attachments - IMPROVED NAVIGATION"""
    st.subheader("📋 My Assigned Tasks")
    
    # Check if we have a task ID from notification navigation
    current_task_id = st.session_state.get('current_task_id')
    if current_task_id:
        st.info(f"🎯 Viewing task from notification: {current_task_id}")
        # Add a clear button to reset navigation
        col_nav1, col_nav2 = st.columns([1, 5])
        with col_nav1:
            if st.button("← Back to All Tasks", key="back_to_all_tasks_employee", use_container_width=True):
                clear_task_navigation()
                st.rerun()
    
    task_manager = get_task_manager()
    user_data = st.session_state.get('user_data', {})
    employee_id = user_data.get('employee_id')
    
    if not employee_id:
        st.error("Cannot load employee information")
        return
    
    # This is correct - employees only see their own tasks
    tasks_data = task_manager.get_employee_tasks(employee_id)
    
    if not tasks_data.get('success'):
        st.error(f"Failed to load tasks: {tasks_data.get('error')}")
        return
    
    tasks = tasks_data.get('tasks', [])
    
    # If we have a specific task to show, filter to just that task
    if current_task_id:
        filtered_tasks = [t for t in tasks if t.get('id') == current_task_id]
        if not filtered_tasks:
            st.error(f"Task {current_task_id} not found or not assigned to you")
            if st.button("← Back to All Tasks", key="back_employee_not_found"):
                clear_task_navigation()
                st.rerun()
            return
    else:
        # Normal filtering for employee tasks
        filtered_tasks = tasks
    
    # Filter options (employee-specific)
    col1, col2 = st.columns(2)
    with col1:
        show_completed = st.checkbox("Show completed tasks", value=False)
    with col2:
        sort_by = st.selectbox("Sort by", ["Due Date", "Priority", "Status"], key="employee_sort")
    
    # Apply employee-specific filters
    if not show_completed:
        filtered_tasks = [t for t in filtered_tasks if t.get('status') != 'completed']
    
    if sort_by == "Due Date":
        filtered_tasks.sort(key=lambda x: x.get('due_date', ''))
    elif sort_by == "Priority":
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        filtered_tasks.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 2))
    else:
        status_order = {'in_progress': 0, 'not_started': 1, 'completed': 2}
        filtered_tasks.sort(key=lambda x: status_order.get(x.get('status', 'not_started'), 3))
    
    if not filtered_tasks:
        st.info("No tasks assigned to you. Great job! 🎉")
        return
    
    for task in filtered_tasks:
        # FIX: Ensure is_current_task is always boolean, not None
        is_current_task = bool(current_task_id and task.get('id') == current_task_id)
        
        with st.expander(
            f"📌 {task['task_description']} - {task.get('status', 'not_started').title()}", 
            expanded=is_current_task  # Auto-expand if this is the navigated task
        ):
            show_employee_task_detail_with_attachments(task)
    
    # Don't auto-clear the navigation state - let user use the back button


# ========== REST OF YOUR EXISTING FUNCTIONS (UNCHANGED) ==========
def reset_navigation_state():
    """Reset navigation-related session state"""
    keys_to_clear = ['current_task_id', 'notification_navigation']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

            
def show_admin_task_detail_with_attachments(task):
    """Show task details for admin with attachments and notes tabs"""
    task_manager = get_task_manager()
    
    # Create tabs for task details, attachments, and notes
    tab1, tab2, tab3 = st.tabs(["📋 Task Details", "📎 Attachments", "📝 Notes"])
    
    with tab1:
        show_admin_task_details_tab(task, task_manager)
    
    with tab2:
        show_attachments_tab(task, task_manager)
    
    with tab3:
        show_notes_tab(task, task_manager)

def show_admin_task_details_tab(task, task_manager):
    """Show task details tab for admin with enhanced RAG information"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**Description:** {task.get('task_description', 'No description')}")
        
        # Show assigned employees
        assigned_employees = []
        if task.get('employees', {}).get('name'):
            assigned_employees.append(task['employees']['name'])
        
        # Handle multiple assignees
        if task.get('assigned_to_multiple'):
            from employee_management import get_all_employees
            all_employees = get_all_employees()
            for emp_id in task['assigned_to_multiple']:
                emp = next((e for e in all_employees if e['id'] == emp_id), None)
                if emp and emp.get('name') and emp['name'] not in assigned_employees:
                    assigned_employees.append(emp['name'])
        
        if assigned_employees:
            st.write(f"**Assigned to:** {', '.join(assigned_employees)}")
        else:
            st.write("**Assigned to:** Unassigned")
        
        st.write(f"**Goal:** {task.get('objectives', {}).get('title', 'No Goal')}")
        st.write(f"**Priority:** {task.get('priority', 'medium').title()}")
        st.write(f"**Deadline:** {task.get('due_date', 'Not set')[:10]}")
        
        # Enhanced status display
        status = task.get('status', 'not_started')
        status_display = status.replace('_', ' ').title()
        if status == 'waiting':
            st.warning(f"**Status:** ⏳ {status_display} (Waiting for prerequisites)")
        elif status == 'completed':
            st.success(f"**Status:** ✅ {status_display}")
        elif status == 'in_progress':
            st.info(f"**Status:** 🔄 {status_display}")
        elif status == 'ai_suggested':
            st.info(f"**Status:** 🤖 {status_display} (AI Suggested - Needs Review)")
        else:
            st.write(f"**Status:** {status_display}")
        
        # Progress bar
        progress = task.get('completion_percentage', 0)
        st.progress(progress / 100)
        st.write(f"**Progress:** {progress}%")
        
        # Enhanced AI recommendations display with RAG info
        strategic_meta = task.get('strategic_metadata', {})
        if strategic_meta.get('employee_recommendations_available'):
            with st.expander("👥 AI Employee Recommendations", expanded=False):
                # Show RAG enhancement status
                if strategic_meta.get('rag_enhanced'):
                    st.success("🔍 **RAG-Enhanced Analysis**")
                    st.write(f"JD Documents Analyzed: {strategic_meta.get('employees_with_jd', 0)}")
                
                recommendations = strategic_meta.get('ai_recommendations', [])
                for rec in recommendations[:3]:  # Show top 3
                    st.write(f"**{rec.get('employee_name')}** - Fit: {rec.get('fit_score')}%")
                    if rec.get('rag_enhanced_score'):
                        st.write(f"  RAG Score: {rec.get('rag_enhanced_score')}%")
                    st.write(f"  Reason: {rec.get('reason', 'No reason provided')[:100]}...")
    
    with col2:
        # Use session state to track edit mode for admin task editing
        admin_edit_key = f"admin_edit_{task['id']}"
        
        if admin_edit_key not in st.session_state:
            st.session_state[admin_edit_key] = {
                'editing': False,
                'status': task.get('status', 'pending'),
                'priority': task.get('priority', 'medium'),
                'progress': task.get('completion_percentage', 0)
            }
        
        if st.session_state[admin_edit_key]['editing']:
            show_admin_edit_form(task, task_manager, admin_edit_key)
        else:
            if st.button("✏️ Edit Task", key=f"admin_edit_btn_{task['id']}", use_container_width=True):
                st.session_state[admin_edit_key]['editing'] = True
                st.rerun()

# Add RAG information to the goal management section
def show_ai_classification_review():
    """Enhanced AI classification review with RAG information"""
    result = st.session_state.ai_goal_result
    
    # Show RAG status if available
    if result.get('rag_enhanced'):
        st.success("🔍 **RAG-Enhanced Analysis** - Used JD documents for employee matching")
    
    with st.expander("🔧 Debug", expanded=False):
        st.write("### AI Results")
        debug_info = {
            'success': result.get('success'),
            'ai_meta_id': result.get('ai_meta_id'),
            'ai_processing_time': result.get('ai_processing_time'),
            'ai_tasks_count': len(result.get('ai_tasks', [])),
            'ai_breakdown': result.get('ai_breakdown'),
            'rag_enhanced': result.get('rag_enhanced', False)
        }
        st.json(debug_info)
        
        if result.get('ai_meta_id'):
            task_manager = get_task_manager()
            progress_response = task_manager.get_ai_progress(result['ai_meta_id'])
            if progress_response.get('success'):
                st.write("### AI Meta")
                st.json(progress_response['ai_meta'])
            else:
                st.error(f"Failed to load AI meta: {progress_response.get('error')}")
    
    if st.button("← Create Another Goal"):
        for key in ['show_ai_review', 'ai_goal_result', 'processing_complete', 'current_ai_meta_id']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    if result.get('ai_processing_time'):
        st.success(f"⏱️ Classification: {result['ai_processing_time']:.1f}s")
    
    if result.get('ai_breakdown'):
        with st.expander("🤖 Analysis", expanded=True):
            st.write(result['ai_breakdown'])
    
    if result.get('ai_tasks'):
        st.info(f"🤖 Generated {len(result['ai_tasks'])} tasks!")
        st.write("### 🎯 Tasks")
        for i, task in enumerate(result['ai_tasks']):
            show_classified_task_card(task, i, get_task_manager())
    else:
        st.error("❌ No tasks generated. Check debug info.")
    
    st.balloons()

def show_admin_edit_form(task, task_manager, edit_key):
    """Show admin task edit form with multiple assignees and dependencies"""
    st.write("### Edit Task")
    
    # Get current task data safely
    current_description = task.get('task_description', '')
    current_status = st.session_state[edit_key]['status']
    current_priority = st.session_state[edit_key]['priority']
    current_progress = st.session_state[edit_key]['progress']
    
    # Get employees for assignment
    from employee_management import get_all_employees
    employees = get_all_employees()
    active_employees = [e for e in employees if e.get('is_active', True)]
    employee_options = {f"{e['id']} - {e['name']} ({e['role']})": e['id'] for e in active_employees}
    
    # Get current assignees
    current_assignees = task.get('assigned_to_multiple', [])
    if task.get('assigned_to') and task['assigned_to'] not in current_assignees:
        current_assignees.append(task['assigned_to'])
    
    # Get available tasks for dependencies using the backend endpoint
    available_deps_data = task_manager.get_available_dependencies(task['id'])
    available_tasks = available_deps_data.get('available_dependencies', []) if available_deps_data.get('success') else []
    task_options = {f"{t['id']} - {t['task_description'][:50]}...": t['id'] for t in available_tasks}
    
    # Current dependencies
    current_dependencies = task.get('dependencies', [])
    
    # Task description
    new_description = st.text_area(
        "Task Description*",
        value=current_description,
        height=100,
        key=f"admin_desc_{task['id']}"
    )
    
    # Multiple assignees
    st.subheader("👥 Assign Employees")
    selected_assignees = st.multiselect(
        "Assign to employees*",
        options=list(employee_options.keys()),
        default=[k for k, v in employee_options.items() if v in current_assignees],
        key=f"assignees_{task['id']}"
    )
    
    # Priority
    new_priority = st.selectbox(
        "Priority", 
        ["low", "medium", "high"],
        index=["low", "medium", "high"].index(current_priority),
        key=f"priority_{task['id']}"
    )
    
    # Status
    status_options = ["not_started", "in_progress", "completed", "waiting", "ai_suggested"]
    try:
        status_index = status_options.index(current_status)
    except ValueError:
        status_index = 0
    
    new_status = st.selectbox(
        "Status", 
        status_options,
        index=status_index,
        key=f"status_{task['id']}"
    )
    
    # Due date
    current_due_date = task.get('due_date')
    if current_due_date:
        try:
            default_date = datetime.fromisoformat(current_due_date.replace('Z', '')).date()
        except:
            default_date = datetime.now().date() + timedelta(days=7)
    else:
        default_date = datetime.now().date() + timedelta(days=7)
    
    new_due_date = st.date_input(
        "Due Date",
        value=default_date,
        key=f"due_date_{task['id']}"
    )
    
    # Estimated hours
    new_estimated_hours = st.number_input(
        "Estimated Hours",
        min_value=1,
        max_value=200,
        value=task.get('estimated_hours', 8),
        key=f"hours_{task['id']}"
    )
    
    # Progress
    new_progress = st.slider(
        "Progress", 
        0, 100, 
        current_progress,
        key=f"progress_{task['id']}"
    )
    
    # Dependencies section
    st.subheader("⛓️ Prerequisite Tasks")
    st.info("Tasks that must be completed before this task can start")
    
    if available_tasks:
        selected_dependencies = st.multiselect(
            "Select prerequisite tasks",
            options=list(task_options.keys()),
            default=[k for k, v in task_options.items() if v in current_dependencies],
            key=f"dependencies_{task['id']}"
        )
        
        # Show current dependency status
        if current_dependencies:
            st.write("**Current Prerequisites:**")
            for dep_id in current_dependencies:
                dep_task = next((t for t in available_tasks if t['id'] == dep_id), None)
                if dep_task:
                    status = dep_task.get('status', 'unknown')
                    status_icon = "✅" if status == 'completed' else "🔄" if status == 'in_progress' else "⏳"
                    st.write(f"{status_icon} {dep_task['task_description'][:50]}... - {status}")
    else:
        st.info("No other tasks available to set as prerequisites")
        selected_dependencies = []
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Update Task", key=f"update_{task['id']}", use_container_width=True):
            if not new_description.strip():
                st.error("Task description is required")
                return
            
            if not selected_assignees:
                st.error("Please assign the task to at least one employee")
                return
            
            # Prepare update data
            update_data = {
                'task_description': new_description.strip(),
                'priority': new_priority,
                'status': new_status,
                'due_date': new_due_date.isoformat(),
                'estimated_hours': new_estimated_hours,
                'completion_percentage': new_progress
            }
            
            # Handle multiple assignees
            if selected_assignees:
                assignee_ids = [employee_options[emp] for emp in selected_assignees]
                update_data['assigned_to'] = assignee_ids[0]  # Primary assignee
                update_data['assigned_to_multiple'] = assignee_ids  # All assignees
            
            # Handle dependencies
            if selected_dependencies:
                dependency_ids = [task_options[dep] for dep in selected_dependencies]
                update_data['dependencies'] = dependency_ids
                
                # If task has dependencies and is not completed, set status to waiting
                if new_status != 'completed':
                    update_data['status'] = 'waiting'
            
            result = task_manager.update_task(task['id'], update_data)
            if result.get('success'):
                st.success("✅ Task updated!")
                st.session_state[edit_key]['editing'] = False
                st.session_state[edit_key]['status'] = new_status
                st.session_state[edit_key]['priority'] = new_priority
                st.session_state[edit_key]['progress'] = new_progress
                st.rerun()
            else:
                error_msg = result.get('error', 'Unknown error')
                st.error(f"❌ Failed to update: {error_msg}")
    
    with col2:
        if st.button("❌ Cancel", key=f"cancel_admin_{task['id']}", use_container_width=True):
            st.session_state[edit_key]['editing'] = False
            st.rerun()

def show_attachments_tab(task, task_manager):
    """Show attachments tab for a task"""
    st.subheader("📎 Task Attachments")
    
    # Load attachments
    attachments_data = task_manager.get_task_attachments(task['id'])
    
    if not attachments_data.get('success'):
        st.error(f"Failed to load attachments: {attachments_data.get('error')}")
        return
    
    attachments = attachments_data.get('attachments', [])
    
    if not attachments:
        st.info("No attachments found for this task.")
    else:
        # Display attachments in a table
        st.write(f"**Total Attachments:** {len(attachments)}")
        
        for i, attachment in enumerate(attachments):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{attachment.get('filename', 'Unknown')}**")
                    st.write(f"Type: {attachment.get('file_type', 'Unknown')}")
                
                with col2:
                    file_size = attachment.get('file_size', 0)
                    st.write(f"Size: {file_size} bytes")
                    st.write(f"Uploaded: {attachment.get('created_at', '')[:10]}")
                
                with col3:
                    uploaded_by = attachment.get('employee_name', 'Unknown')
                    st.write(f"By: {uploaded_by}")
                
                with col4:
                    # Download button
                    if st.button("⬇️ Download", key=f"download_{i}_{task['id']}", use_container_width=True):
                        # Create download link
                        public_url = attachment.get('public_url')
                        if public_url:
                            st.markdown(f'<a href="{public_url}" target="_blank">Download File</a>', unsafe_allow_html=True)
                    
                    # Delete button (admin only)
                    if st.session_state.get('user_role') in ['admin', 'superadmin']:
                        if st.button("🗑️ Delete", key=f"delete_attach_{i}_{task['id']}", use_container_width=True):
                            result = task_manager.delete_task_attachment(
                                task['id'], 
                                attachment['update_id'], 
                                i
                            )
                            if result.get('success'):
                                st.success("✅ Attachment deleted!")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to delete: {result.get('error')}")
                
                st.markdown("---")
    
    # File upload section
    st.subheader("Upload New File")
    with st.form(f"upload_form_{task['id']}"):
        uploaded_file = st.file_uploader(
            "Choose file", 
            type=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt', 'xlsx', 'pptx'],
            key=f"file_upload_{task['id']}"
        )
        
        notes = st.text_area(
            "Upload notes (optional)",
            placeholder="Add any notes about this file...",
            key=f"upload_notes_{task['id']}"
        )
        
        if st.form_submit_button("📤 Upload File"):
            if uploaded_file:
                result = task_manager.upload_task_file(task['id'], uploaded_file, notes)
                if result.get('success'):
                    st.success("✅ File uploaded successfully!")
                    st.rerun()
                else:
                    st.error(f"❌ Upload failed: {result.get('error')}")
            else:
                st.error("Please select a file to upload")

def show_notes_tab(task, task_manager):
    """Show notes tab for a task with attachment information"""
    st.subheader("📝 Task Notes & Updates")
    
    # Load notes
    notes_data = task_manager.get_task_notes(task['id'])
    
    if not notes_data:
        st.error("No response from server when loading notes")
        return
    
    if not notes_data.get('success'):
        error_msg = notes_data.get('error', 'Unknown error occurred')
        st.error(f"Failed to load notes: {error_msg}")
        return
    
    notes = notes_data.get('notes', [])
    
    if not notes:
        st.info("No notes found for this task.")
        return
    
    # Display notes in reverse chronological order (newest first)
    for note in notes:
        show_note_with_attachments(note, task_manager)

def show_note_with_attachments(note, task_manager):
    """Display a single note with attachment information"""
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Note content
            note_text = note.get('notes', '')
            if note_text:
                st.write(note_text)
            else:
                st.write("*No content*")
            
            # Progress information
            if note.get('progress') is not None:
                st.write(f"**Progress at time of note:** {note['progress']}%")
            
            # Attachment indicator
            if note.get('has_attachments'):
                attachments_count = note.get('attachments_count', 0)
                st.info(f"📎 This update has {attachments_count} attachment(s)")
            
            # Employee attachment information
            show_note_attachment_info(note)
            
            with col2:
            # Metadata
                employee_name = note.get('employee_name', 'Unknown')
                employee_role = note.get('employee_role', 'N/A')
                created_at = note.get('created_at', '')
                
                st.write(f"**By:** {employee_name}")
                st.write(f"**Role:** {employee_role}")
                
            # Format date
                if created_at:
                    try:
                        if 'T' in created_at:
                            display_date = created_at.replace('T', ' ')[:16]
                        else:
                            display_date = created_at[:16]
                        st.write(f"**Date:** {display_date}")
                    except:
                        st.write(f"**Date:** {created_at[:16]}")
                else:
                    st.write("**Date:** Unknown")
            
            # Special attachment badge
            if note.get('is_attached_to_me'):
                st.success("📨 Sent to you")
            
            st.markdown("---")

def show_note_attachment_info(note):
    """Show information about who the note was attached to"""
    attached_to_name = note.get('attached_to_name')
    attached_to_multiple_names = note.get('attached_to_multiple_names', [])
    
    if attached_to_name or attached_to_multiple_names:
        st.write("**Specifically notified:**")
        
        all_attached = []
        if attached_to_name:
            all_attached.append(attached_to_name)
        if attached_to_multiple_names:
            # Extract names from the list of dicts
            names = [emp.get('name', 'Unknown') for emp in attached_to_multiple_names]
            all_attached.extend(names)
        
        # Remove duplicates and display
        unique_attached = list(set(all_attached))
        for name in unique_attached:
            st.write(f"👤 {name}")
# ========== EMPLOYEE TASK FUNCTIONS ==========


def show_employee_task_detail_with_attachments(task):
    """Show task detail for employee with attachments and notes"""
    task_manager = get_task_manager()
    
    # Create tabs for task details, attachments, and notes
    tab1, tab2, tab3 = st.tabs(["📋 Task Details", "📎 Attachments", "📝 Notes"])
    
    with tab1:
        show_employee_task_details_tab(task, task_manager)
    
    with tab2:
        show_attachments_tab(task, task_manager)
    
    with tab3:
        show_notes_tab(task, task_manager)

def show_employee_task_details_tab(task, task_manager):
    """Show task details tab for employee"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**Description:** {task.get('task_description', 'No description')}")
        st.write(f"**Priority:** {task.get('priority', 'medium').title()}")
        st.write(f"**Due Date:** {task.get('due_date', 'Not set')[:10]}")
        st.write(f"**Status:** {task.get('status', 'not_started').title()}")
        st.write(f"**Goal:** {task.get('objectives', {}).get('title', 'General')}")
        
        # Check if deadline is overdue
        if task.get('due_date'):
            due_date = datetime.fromisoformat(task['due_date'].replace('Z', ''))
            if due_date.date() < datetime.utcnow().date() and task.get('status') != 'completed':
                st.error("⚠️ This task is overdue!")
        
        # Dependencies
        dependencies = task.get('dependencies', [])
        if dependencies:
            st.write("**Dependencies:**")
            for dep_id in dependencies:
                st.write(f"↳ Must complete task {dep_id[:8]}... first")

    with col2:
        employee_update_key = f"employee_update_{task['id']}"
        
        if employee_update_key not in st.session_state:
            st.session_state[employee_update_key] = {
                'updating': False,
                'progress': task.get('completion_percentage', 0),
                'notes': ''
            }
        
        if st.session_state[employee_update_key]['updating']:
            # This now calls the enhanced version with employee attachments
            show_employee_progress_update_form(task, task_manager, employee_update_key)
        else:
            if st.button("📈 Update Progress", key=f"update_btn_{task['id']}", use_container_width=True):
                st.session_state[employee_update_key]['updating'] = True
                st.rerun()

def show_employee_progress_update_form(task, task_manager, update_key):
    """Show employee progress update form with employee attachment feature"""
    st.write("### Update Progress")
    
    # Get available employees for attachment
    employees_data = task_manager.get_available_employees_for_attachment(task['id'])
    available_employees = employees_data.get('employees', []) if employees_data.get('success') else []
    
    new_progress = st.slider(
        "Completion %", 
        0, 100, 
        st.session_state[update_key]['progress'],
        key=f"employee_progress_{task['id']}"
    )
    
    notes = st.text_area(
        "Progress Notes*", 
        value=st.session_state[update_key]['notes'],
        placeholder="What have you completed? Any challenges?",
        key=f"notes_{task['id']}"
    )
    
    # Employee Attachment Section
    st.subheader("👥 Notify Additional Colleagues")
    st.info("Select colleagues who should be specifically notified about this update")
    
    # Create employee options for the selectors
    employee_options = {f"{emp['name']} ({emp['role']})": emp['id'] for emp in available_employees}
    
    # Single primary attachment
    attached_to = st.selectbox(
        "Primary Colleague to Notify",
        options=["None"] + list(employee_options.keys()),
        key=f"attached_to_{task['id']}"
    )
    
    # Multiple additional attachments
    attached_to_multiple = st.multiselect(
        "Additional Colleagues to Notify",
        options=list(employee_options.keys()),
        key=f"attached_to_multiple_{task['id']}"
    )
    
    # Show preview of selected employees
    selected_employees = []
    if attached_to != "None":
        selected_employees.append(attached_to.split(' (')[0])
    if attached_to_multiple:
        selected_employees.extend([name.split(' (')[0] for name in attached_to_multiple])
    
    if selected_employees:
        st.success(f"📨 Will notify: {', '.join(selected_employees)} + Admin")
    else:
        st.info("ℹ️ Only admin will be notified of this update")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Update Progress", key=f"save_progress_{task['id']}", use_container_width=True):
            if not notes.strip():
                st.error("Please enter progress notes")
                return
                
            # Prepare attachment data
            attached_to_id = employee_options[attached_to] if attached_to != "None" else None
            attached_to_multiple_ids = [employee_options[emp] for emp in attached_to_multiple]
                
            # Prepare update data - only allowed fields for employees
            update_data = {
                'completion_percentage': new_progress,
                'notes': notes.strip(),
                'status': 'completed' if new_progress == 100 else ('in_progress' if new_progress > 0 else 'not_started'),
                'attached_to': attached_to_id,
                'attached_to_multiple': attached_to_multiple_ids
            }
            
            # Use the new method for notes with attachments
            result = task_manager.add_task_note_with_attachments(
                task['id'], 
                notes.strip(),
                new_progress,
                attached_to_id,
                attached_to_multiple_ids
            )
            
            if result.get('success'):
                st.toast("✅ Progress updated! Notifications sent to selected colleagues.", icon="📩")
                st.session_state[update_key]['updating'] = False
                st.rerun()
            else:
                st.error(f"❌ Failed to update: {result.get('error')}")
    
    with col2:
        if st.button("❌ Cancel", key=f"cancel_progress_{task['id']}", use_container_width=True):
            st.session_state[update_key]['updating'] = False
            st.rerun()

# ========== PROPOSAL AND PROGRESS FUNCTIONS ==========

def show_task_proposal_form():
    """Form for employees to propose new tasks"""
    st.subheader("💡 Propose New Task")
    
    # Get goals for proposal
    task_manager = get_task_manager()
    goals_data = task_manager.get_goals()
    goals = goals_data.get('goals', []) if goals_data.get('success') else []
    
    # Get employees for assignment suggestion
    from employee_management import get_all_employees
    employees = get_all_employees()
    
    with st.form("task_proposal_form"):
        st.write("### Suggest a New Task")
        
        task_description = st.text_input("Task Description*", placeholder="What needs to be done?")
        detailed_description = st.text_area("Detailed Description*", 
                                         placeholder="Detailed description of the task and why it's important...")
        
        col1, col2 = st.columns(2)
        with col1:
            priority = st.selectbox("Suggested Priority", ["low", "medium", "high"])
            due_date = st.date_input("Suggested Due Date", min_value=datetime.now().date())
            goal_id = st.selectbox("Attach to Goal", 
                                 ["None"] + [f"{g['id']} - {g['title']}" for g in goals])
        with col2:
            estimated_hours = st.number_input("Estimated Hours", min_value=1, max_value=100, value=8)
            assign_suggestion = st.selectbox("Suggest Assignment", 
                                           ["Myself"] + [f"{e['id']} - {e['name']} ({e['role']})" 
                                                        for e in employees if e.get('is_active', True)])
        
        submitted = st.form_submit_button("📤 Submit Proposal")
        
        if submitted:
            if not task_description or not detailed_description:
                st.error("Please fill in required fields")
                return
            
            # Prepare task data
            task_data = {
                'task_description': f"{task_description} - {detailed_description}",
                'priority': priority,
                'due_date': due_date.isoformat(),
                'estimated_hours': estimated_hours
            }
            
            # Handle assignment suggestion
            if assign_suggestion != "Myself":
                task_data['assigned_to'] = assign_suggestion.split(' - ')[0]
            else:
                user_data = st.session_state.get('user_data', {})
                task_data['assigned_to'] = user_data.get('employee_id')
            
            # Add goal if selected
            if goal_id != "None":
                task_data['objective_id'] = goal_id.split(' - ')[0]
            
            result = task_manager.create_task(task_data)
            
            if result.get('success'):
                st.success("✅ Task proposal submitted! Waiting for admin approval.")
                st.balloons()
            else:
                st.error(f"❌ Failed to submit proposal: {result.get('error')}")

def show_employee_progress():
    """Employee progress tracking"""
    st.subheader("📈 My Progress Overview")
    
    task_manager = get_task_manager()
    user_data = st.session_state.get('user_data', {})
    employee_id = user_data.get('employee_id')
    
    if not employee_id:
        st.error("Cannot load employee information")
        return
    
    tasks_data = task_manager.get_employee_tasks(employee_id)
    
    if not tasks_data.get('success'):
        st.error("Failed to load progress data")
        return
    
    tasks = tasks_data.get('tasks', [])
    
    if not tasks:
        st.info("No tasks to show progress for.")
        return
    
    # Calculate statistics
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.get('status') == 'completed'])
    in_progress_tasks = len([t for t in tasks if t.get('status') == 'in_progress'])
    pending_tasks = len([t for t in tasks if t.get('status') == 'not_started'])
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tasks", total_tasks)
    with col2:
        st.metric("Completed", completed_tasks)
    with col3:
        st.metric("In Progress", in_progress_tasks)
    with col4:
        st.metric("Pending", pending_tasks)
    
    # Progress chart
    if total_tasks > 0:
        completion_rate = (completed_tasks / total_tasks) * 100
        st.subheader(f"Overall Completion: {completion_rate:.1f}%")
        st.progress(completion_rate / 100)
    
    # Task breakdown
    st.subheader("📊 Task Breakdown by Status")
    status_data = {
        'Completed': completed_tasks,
        'In Progress': in_progress_tasks,
        'Pending': pending_tasks
    }
    st.bar_chart(status_data)
    
    # Recent activity
    st.subheader("📅 Recent Activity")
    recent_tasks = sorted(tasks, key=lambda x: x.get('updated_at', ''), reverse=True)[:5]
    
    for task in recent_tasks:
        status_icon = "✅" if task.get('status') == 'completed' else "🔄" if task.get('status') == 'in_progress' else "⏳"
        st.write(f"{status_icon} **{task['task_description'][:50]}...** - {task.get('completion_percentage', 0)}% - {task.get('updated_at', '')[:10]}")

# ========== MAIN INTERFACE FUNCTIONS ==========

def show_admin_task_interface():
    """Admin task management interface"""
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard", "🎯 Set Goals", "📝 Manage Tasks", "👥 Assign Tasks"
    ])
    
    with tab1:
        show_admin_dashboard()
    with tab2:
        show_goal_management()
    with tab3:
        show_task_management_admin()
    with tab4:
        show_manual_task_assignment()

# ========== NOTIFICATIONS UI ==========

def show_notifications_tab():
    """Show notifications for the current user"""
    st.subheader("🔔 Notifications")
    
    task_manager = get_task_manager()
    
    # Load notifications
    notifications_data = task_manager.get_notifications()
    
    if not notifications_data.get('success'):
        st.error(f"Failed to load notifications: {notifications_data.get('error')}")
        return
    
    notifications = notifications_data.get('notifications', [])
    unread_count = notifications_data.get('unread_count', 0)
    
    if not notifications:
        st.info("No notifications found.")
        return
    
    # Show unread count and mark all as read button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**You have {unread_count} unread notifications**")
    with col2:
        if st.button("📭 Mark All Read", use_container_width=True):
            result = task_manager.mark_all_notifications_read()
            if result.get('success'):
                st.toast("✅ All notifications marked as read!", icon="✅")
                st.rerun()
            else:
                st.error(f"❌ Failed to mark all as read: {result.get('error')}")
    
    st.markdown("---")
    
    # Display notifications
    for notification in notifications:
        show_notification_card(notification, task_manager)

def show_notification_card(notification, task_manager):
    """Display a single notification card"""
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            # Notification message
            st.write(f"**{notification.get('message', 'No message')}**")
            
            # Notification metadata
            meta = notification.get('meta', {})
            if meta.get('task_description'):
                st.caption(f"Task: {meta['task_description']}")
            if meta.get('assigned_by'):
                st.caption(f"Assigned by: {meta['assigned_by']}")
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
        
        st.markdown("---")

def show_employee_task_interface():
    """Employee task interface"""
    tab1, tab2, tab3 = st.tabs(["📋 My Tasks", "💡 Propose Task", "📈 My Progress"])
    
    with tab1:
        show_employee_tasks_with_attachments()
    with tab2:
        show_task_proposal_form()
    with tab3:
        show_employee_progress()

def show_task_management():
    """Main task management function"""
    st.title("🎯 AI Task Management System")
    
    # Role-based interface
    if st.session_state.get('user_role') in ['admin', 'superadmin']:
        show_admin_task_interface()
    else:
        show_employee_task_interface()


def show_manual_task_assignment():
    """Manual task assignment interface"""
    st.subheader("👥 Manual Task Assignment")
    
    # Get employees for assignment
    from employee_management import get_all_employees
    employees = get_all_employees()
    active_employees = [e for e in employees if e.get('is_active', True)]
    
    # Get goals for assignment
    task_manager = get_task_manager()
    goals_data = task_manager.get_goals()
    goals = goals_data.get('goals', []) if goals_data.get('success') else []
    
    with st.form("manual_task_form"):
        st.write("### Create Task Manually")
        
        task_description = st.text_input("Task Description*", placeholder="Complete market research report")
        
        col1, col2 = st.columns(2)
        with col1:
            # Multiple assignees
            assigned_employees = st.multiselect(
                "Assign to employees*",
                [f"{e['id']} - {e['name']} ({e['role']})" for e in active_employees],
                help="Select one or more employees to assign this task to"
            )
            
            priority = st.selectbox("Priority", ["low", "medium", "high"])
            
            goal_id = st.selectbox("Attach to Goal", 
                                 ["None"] + [f"{g['id']} - {g['title']}" for g in goals])
        
        with col2:
            due_date = st.date_input("Due Date*", min_value=datetime.now().date())
            estimated_hours = st.number_input("Estimated Hours", min_value=1, max_value=100, value=8)
            status = st.selectbox("Status", ["not_started", "in_progress"])
        
        submitted = st.form_submit_button("📝 Create Task")
        
        if submitted:
            if not task_description:
                st.error("Please fill in required fields")
                return
            
            if not assigned_employees:
                st.error("Please assign the task to at least one employee")
                return
            
            # Extract employee IDs from selection
            employee_ids = [emp.split(' - ')[0] for emp in assigned_employees]
            
            task_data = {
                'task_description': task_description,
                'assigned_to': employee_ids[0],  # Primary assignee
                'assigned_to_multiple': employee_ids,  # All assignees
                'priority': priority,
                'due_date': due_date.isoformat(),
                'estimated_hours': estimated_hours,
                'status': status
            }
            
            # Add goal if selected
            if goal_id != "None":
                task_data['objective_id'] = goal_id.split(' - ')[0]
            
            result = task_manager.create_task(task_data)
            
            if result.get('success'):
                st.success("✅ Task created successfully!")
                st.balloons()
            else:
                st.error(f"❌ Failed to create task: {result.get('error')}")


def show_admin_notifications():
    """Admin notifications view"""
    st.subheader("🔔 Notifications")
    st.info("Notification system will be implemented in the next update")

def show_task_management():
    """Main task management function"""
    st.title("🎯 AI Task Management System")
    
    # Role-based interface
    if st.session_state.get('user_role') in ['admin', 'superadmin']:
        show_admin_task_interface()
    else:
        show_employee_task_interface()