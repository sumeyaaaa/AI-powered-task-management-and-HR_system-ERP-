from flask import Blueprint, request, jsonify
from auth import token_required, admin_required
import os
from datetime import datetime, timedelta
import uuid
import json
from openai import OpenAI
from flask import g
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dotenv import load_dotenv
import re
import traceback
import threading
import backoff
import threading
import io
import requests
import PyPDF2
import docx
from docx import Document
from predefined_processes import get_predefined_processes_registry
# Load environment variables
load_dotenv()

print("=" * 50)
print("🔍 TASK ROUTES - ENVIRONMENT DEBUG")
print("=" * 50)
print(f"OPENAI_API_KEY exists: {os.getenv('OPENAI_API_KEY') is not None}")
print(f"OPENAI_API_KEY length: {len(os.getenv('OPENAI_API_KEY', ''))}")
print(f"SUPABASE_URL exists: {os.getenv('SUPABASE_URL') is not None}")
print(f"Current directory: {os.getcwd()}")
print("=" * 50)

# Configure OpenAI ChatGPT API with new client
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
    print(f"✅ OpenAI API key configured. Key: {OPENAI_API_KEY[:12]}...")
else:
    print("❌ ERROR: OPENAI_API_KEY not found")
    client = None
task_bp = Blueprint('tasks', __name__)

# Import the correct notification function from notification_routes
from notification_routes import create_enhanced_task_notification

# Add thread pool for async processing

# Add thread pool for async processing
task_executor = ThreadPoolExecutor(max_workers=3)

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    if not supabase_url or not supabase_key:
        raise Exception("Supabase credentials not configured")
    from supabase import create_client
    return create_client(supabase_url, supabase_key)

@task_bp.route('/api/debug/auth', methods=['GET'])
@token_required
def debug_auth():
    user_data = {
        'user_id': g.user.get('user_id'),
        'email': g.user.get('email'),
        'role': g.user.get('role'),
        'employee_id': g.user.get('employee_id')
    }
    return jsonify({
        'success': True,
        'message': 'Authentication is working',
        'user': user_data
    })

@task_bp.route('/api/debug/auth-test', methods=['GET'])
def debug_auth_test():
    return jsonify({
        'success': True,
        'message': 'Public endpoint is accessible',
        'timestamp': datetime.utcnow().isoformat()
    })
# ========== HELPER FUNCTIONS ==========

def safe_uuid(value):
    if not value or value in ('None', 'null'):
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError):
        return None

def safe_get_employee_id():
    return safe_uuid(g.user.get('employee_id')) if hasattr(g, 'user') and g.user else None

def safe_json_parse(json_string, default=None):
    if not json_string or not json_string.strip():
        return default
    try:
        return json.loads(json_string.strip())
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', json_string, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except:
                pass
        for pattern in [r'\[.*\]', r'\{.*\}']:
            match = re.search(pattern, json_string, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    continue
        return default
    
def check_task_permission(task, user_employee_id, user_role):
    if user_role in ['admin', 'superadmin']:
        return True
    return task['assigned_to'] == user_employee_id or user_employee_id in (task.get('assigned_to_multiple') or [])

def employee_has_collaboration_access(task_id, task, employee_id, supabase):
    """Allow employees who were explicitly attached to a task update or notification to collaborate even if not assigned."""
    if not employee_id or not task_id:
        print(f"🔍 Collaboration check: Missing employee_id or task_id (employee_id={employee_id}, task_id={task_id})")
        return False
    
    # Normalize to strings for comparison
    employee_id_str = str(employee_id)
    
    # Direct assignment still grants access
    assigned_to = task.get('assigned_to')
    if assigned_to and str(assigned_to) == employee_id_str:
        print(f"✅ Collaboration access: Direct assignment (task {task_id})")
        return True
    
    assigned_multiple = task.get('assigned_to_multiple') or []
    if isinstance(assigned_multiple, list):
        assigned_multiple_str = [str(id) for id in assigned_multiple]
        if employee_id_str in assigned_multiple_str:
            print(f"✅ Collaboration access: Multiple assignment (task {task_id})")
            return True
    
    # Check if employee was attached to any previous update
    try:
        updates_result = (
            supabase
            .table("task_updates")
            .select("attached_to, attached_to_multiple")
            .eq("task_id", task_id)
            .limit(500)
            .execute()
        )
        
        print(f"🔍 Checking {len(updates_result.data or [])} task updates for collaboration access")
        
        for update in updates_result.data or []:
            update_id = update.get('id', 'unknown')
            # Check attached_to
            attached_to = update.get('attached_to')
            print(f"  📝 Update {update_id}: attached_to={attached_to} (type: {type(attached_to)})")
            if attached_to and str(attached_to) == employee_id_str:
                print(f"✅ Collaboration access: Found in attached_to (task {task_id}, update {update_id})")
                return True
            
            # Check attached_to_multiple
            attached_multiple = update.get('attached_to_multiple') or []
            print(f"  📝 Update {update_id}: attached_to_multiple={attached_multiple} (type: {type(attached_multiple)})")
            if isinstance(attached_multiple, list):
                attached_multiple_str = [str(id) for id in attached_multiple]
                print(f"  📝 Update {update_id}: attached_multiple_str={attached_multiple_str}")
                if employee_id_str in attached_multiple_str:
                    print(f"✅ Collaboration access: Found in attached_to_multiple (task {task_id}, update {update_id})")
                    return True
                else:
                    print(f"  📝 Update {update_id}: {employee_id_str} not in {attached_multiple_str}")
    except Exception as e:
        print(f"⚠️ Collaboration access check (task_updates) failed for task {task_id}: {e}")
        import traceback
        traceback.print_exc()
    
    # Also check notifications table - if employee received a notification where they were specifically attached
    try:
        notifications_result = (
            supabase
            .table("notifications")
            .select("id, meta, to_employee")
            .eq("to_employee", employee_id_str)
            .eq("meta->>task_id", task_id)
            .limit(100)
            .execute()
        )
        
        print(f"🔍 Checking {len(notifications_result.data or [])} notifications for collaboration access")
        
        for notification in notifications_result.data or []:
            meta_raw = notification.get('meta')
            # Handle both dict and JSON string
            if isinstance(meta_raw, str):
                try:
                    import json
                    meta = json.loads(meta_raw)
                except:
                    meta = {}
            else:
                meta = meta_raw or {}
            
            print(f"  📧 Notification {notification.get('id')}: meta={meta}")
            
            # Check if this notification was specifically attached to this employee
            specially_attached = meta.get('specially_attached') or meta.get('specially_attached')
            print(f"    - specially_attached: {specially_attached}")
            
            if specially_attached:
                attached_to = meta.get('attached_to')
                attached_to_multiple = meta.get('attached_to_multiple') or []
                
                print(f"    - attached_to: {attached_to} (type: {type(attached_to)})")
                print(f"    - attached_to_multiple: {attached_to_multiple} (type: {type(attached_to_multiple)})")
                print(f"    - Comparing with employee_id_str: {employee_id_str}")
                
                # Check if this employee is in the attached list
                if attached_to:
                    if str(attached_to) == employee_id_str:
                        print(f"✅ Collaboration access: Found in notification attached_to (task {task_id}, notification {notification.get('id', 'unknown')})")
                        return True
                    else:
                        print(f"    - attached_to mismatch: {str(attached_to)} != {employee_id_str}")
                
                if isinstance(attached_to_multiple, list) and len(attached_to_multiple) > 0:
                    attached_multiple_str = [str(id) for id in attached_to_multiple]
                    print(f"    - attached_to_multiple_str: {attached_multiple_str}")
                    if employee_id_str in attached_multiple_str:
                        print(f"✅ Collaboration access: Found in notification attached_to_multiple (task {task_id}, notification {notification.get('id', 'unknown')})")
                        return True
                    else:
                        print(f"    - attached_to_multiple mismatch: {employee_id_str} not in {attached_multiple_str}")
            else:
                # Even if not specially_attached, if they received a notification for this task, they might have access
                # This is a fallback - if they got notified, they can respond
                notification_task_id = meta.get('task_id')
                if notification_task_id and str(notification_task_id) == str(task_id):
                    print(f"✅ Collaboration access: Employee received notification for this task (task {task_id}, notification {notification.get('id', 'unknown')})")
                    return True
    except Exception as e:
        print(f"⚠️ Collaboration access check (notifications) failed for task {task_id}: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"❌ Collaboration access DENIED: Employee {employee_id_str} not found in assignments, task_updates, or notifications for task {task_id}")
    return False

def update_ai_progress(ai_meta_id, progress, current_activity, details):
    try:
        supabase = get_supabase_client()
        supabase.table("ai_meta").update({
            "output_json": {
                "status": "processing",
                "progress": progress,
                "current_activity": current_activity,
                "details": details,
                "last_updated": datetime.utcnow().isoformat()
            },
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", ai_meta_id).execute()
        print(f"📊 AI Progress: {progress}% - {current_activity}")
    except Exception as e:
        print(f"⚠️ Failed to update AI progress: {e}")

def log_ai_error(step, error, ai_meta_id=None, goal_id=None, task_id=None, prompt=None, response=None):
    print("=" * 60)
    print(f"🤖 AI ERROR - {step}")
    print(f"📝 Error: {str(error)}")
    if ai_meta_id:
        print(f"🔍 AI Meta ID: {ai_meta_id}")
    if goal_id:
        print(f"🎯 Goal ID: {goal_id}")
    if task_id:
        print(f"📋 Task ID: {task_id}")
    if prompt:
        print(f"📤 Prompt: {prompt[:500]}...")
    if response:
        print(f"📥 Response: {response[:500]}...")
    print("🔍 Stack Trace:")
    traceback.print_exc()
    print("=" * 60)

def analyze_ai_response_errors(response_text, step):
    """Analyze common AI response errors and provide suggestions"""
    errors = []
    
    if not response_text or response_text.strip() == "":
        errors.append("Empty response from AI")
        return errors
    
    # Check for common error patterns
    error_patterns = [
        ("rate limit", "OpenAI rate limit exceeded"),
        ("timeout", "Request timed out"),
        ("invalid api key", "Invalid API key"),
        ("quota exceeded", "API quota exceeded"),
        ("server error", "OpenAI server error"),
        ("context length", "Context length exceeded"),
        ("model overloaded", "Model is overloaded")
    ]
    
    response_lower = response_text.lower()
    for pattern, message in error_patterns:
        if pattern in response_lower:
            errors.append(message)
    
    # Check for JSON parsing issues
    if step == "task_breakdown":
        if "```json" not in response_text and "{" not in response_text:
            errors.append("No JSON structure found in response")
    
    # Check for incomplete responses
    if len(response_text.strip()) < 50:
        errors.append("Response too short, likely incomplete")
    
    # Check for error messages from OpenAI
    if "error:" in response_lower:
        error_match = re.search(r'error:\s*(.*)', response_text, re.IGNORECASE)
        if error_match:
            errors.append(f"OpenAI error: {error_match.group(1)}")
    
    return errors

def validate_ai_task_breakdown(tasks_data, goal_data):
    """Validate AI task breakdown output"""
    validation_errors = []
    
    if not tasks_data or not isinstance(tasks_data, list):
        validation_errors.append("No tasks array found in AI response")
        return validation_errors
    
    if len(tasks_data) == 0:
        validation_errors.append("Empty tasks array in AI response")
        return validation_errors
    
    # Check each task
    for i, task in enumerate(tasks_data):
        if not isinstance(task, dict):
            validation_errors.append(f"Task {i} is not a dictionary")
            continue
        
        # Required fields
        if not task.get('task_description'):
            validation_errors.append(f"Task {i} missing 'task_description'")
        
        # Validate due dates
        due_date = task.get('due_date')
        if due_date:
            try:
                datetime.fromisoformat(due_date.replace('Z', ''))
            except ValueError:
                validation_errors.append(f"Task {i} has invalid due_date format: {due_date}")
        
        # Validate priority
        priority = task.get('priority', '').lower()
        if priority and priority not in ['high', 'medium', 'low']:
            validation_errors.append(f"Task {i} has invalid priority: {priority}")
    
    return validation_errors


# ========== EMPLOYEE RECOMMENDATIONS ==========

@backoff.on_exception(backoff.expo, Exception, max_tries=2, max_time=10)
def recommend_employees_for_task(task, employees, ai_meta_id=None):
    try:
        if not client:
            return ultra_fast_employee_recommendations(task['task_description'], employees)
        
        prompt = f"""
        Recommend 2 employees for task:
        TASK: {task['task_description']}
        SKILLS: {task.get('strategic_metadata', {}).get('required_skills', [])}
        EMPLOYEES: {json.dumps([{'id': emp['id'], 'name': emp['name'], 'role': emp.get('role', ''), 'skills': emp.get('skills', [])[:3]} for emp in employees[:5]], indent=2)}
        Return JSON: {{"recommendations": [{"employee_id": "uuid", "fit_score": 85, "key_qualifications": [], "reason": ""}]}}
        """
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 70, "Recommending employees", f"Processing task {task['id']}")
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "Return ONLY valid JSON."}, {"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400,
            timeout=15
        )
        response_data = safe_json_parse(response.choices[0].message.content, {})
        recommendations = response_data.get('recommendations', [])
        for rec in recommendations:
            employee = next((emp for emp in employees if emp['id'] == rec['employee_id']), None)
            if employee:
                rec['employee_name'] = employee['name']
                rec['employee_role'] = employee.get('role', '')
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 90, "Recommendations completed", f"Got {len(recommendations)} recommendations")
        return recommendations
    except Exception as e:
        log_ai_error("employee_recommendations", str(e), ai_meta_id, task_id=task['id'])
        return ultra_fast_employee_recommendations(task['task_description'], employees)
    

def ultra_fast_employee_recommendations(task_description, employees, max_recommendations=2):
    try:
        task_lower = task_description.lower()
        recommendations = []
        for employee in employees[:8]:
            profile = {
                'id': employee['id'],
                'name': employee['name'],
                'role': employee.get('role', '').lower(),
                'skills': employee.get('skills', [])[:3],
                'experience_years': employee.get('experience_years', 0)
            }
            score = 0
            if any(keyword in task_lower for keyword in [profile['role']]):
                score += 40
            skills = profile.get('skills', [])
            skill_matches = sum(1 for skill in skills if skill.lower() in task_lower)
            score += min(skill_matches * 10, 30)
            if profile['experience_years'] >= 3:
                score += 15
            elif profile['experience_years'] >= 1:
                score += 10
            score = min(score, 100)
            if score >= 30:
                recommendations.append({
                    'employee_id': profile['id'],
                    'employee_name': employee['name'],
                    'employee_role': employee.get('role', ''),
                    'fit_score': score,
                    'key_qualifications': [f"Role: {employee.get('role', 'N/A')}", f"Experience: {profile['experience_years']} years"],
                    'reason': "Fast-match based on role and skills"
                })
        return sorted(recommendations, key=lambda x: x['fit_score'], reverse=True)[:max_recommendations]
    except Exception as e:
        print(f"❌ Ultra-fast recommendation error: {e}")
        return []


def process_employee_recommendations_for_task(task, employees, ai_meta_id):
    """Background process for employee recommendations with enhanced AI analysis"""
    try:
        supabase = get_supabase_client()
        start_time = time.time()
        
        print(f"👥 Processing employee recommendations for task: {task['task_description'][:50]}...")
        
        # Update AI meta with progress
        update_data = {
            "output_json": {
                "status": "processing",
                "progress": 20,
                "current_activity": "Analyzing task requirements and employee profiles",
                "task_id": task['id'],
                "employees_analyzed": len(employees)
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(update_data).eq("id", ai_meta_id).execute()
        
        # Get strategic metadata from task
        strategic_meta = task.get('strategic_metadata', {})
        required_skills = strategic_meta.get('required_skills', [])
        task_complexity = strategic_meta.get('complexity', 'medium')
        estimated_hours = task.get('estimated_hours', 8)
        
        # Prepare employee data for AI analysis
        employee_profiles = []
        for emp in employees:
            profile = {
                'id': emp['id'],
                'name': emp['name'],
                'role': emp.get('role', ''),
                'title': emp.get('title', ''),
                'department': emp.get('department', ''),
                'skills': emp.get('skills', []),
                'experience_years': emp.get('experience_years', 0),
                'strengths': emp.get('strengths', []),
                'google_drive_jd': emp.get('google_drive_jd', '')[:1000]  # Limit JD length
            }
            employee_profiles.append(profile)
        
        # Update progress
        update_data = {
            "output_json": {
                "status": "processing",
                "progress": 40,
                "current_activity": "Preparing AI analysis",
                "task_id": task['id']
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(update_data).eq("id", ai_meta_id).execute()
        
        # AI prompt for comprehensive employee recommendations
        prompt = f"""
        As an HR and talent matching expert, analyze this task and recommend the best employees based on their profiles.

        TASK ANALYSIS:
        - Description: {task['task_description']}
        - Required Skills: {', '.join(required_skills) if required_skills else 'Not specified'}
        - Complexity: {task_complexity}
        - Priority: {task.get('priority', 'medium')}
        - Estimated Hours: {estimated_hours}
        - Goal: {task.get('objectives', {}).get('title', 'Not specified')}

        EMPLOYEE PROFILES TO ANALYZE:
        {json.dumps(employee_profiles, indent=2)}

        ANALYSIS CRITERIA:
        1. Skills Match: How well do the employee's skills match the required skills?
        2. Role Alignment: How relevant is the employee's role and title to this task?
        3. Experience Level: Does the employee have sufficient experience?
        4. Strengths Alignment: Do the employee's strengths align with task requirements?
        5. Department Fit: Is this task relevant to the employee's department?
        6. Workload Consideration: Consider if the employee might be overloaded

        Provide TOP 3 recommendations with detailed scoring and reasoning.

        Return ONLY valid JSON in this exact format:
        {{
            "recommendations": [
                {{
                    "employee_id": "uuid-string-here",
                    "employee_name": "Employee Name",
                    "fit_score": 85,
                    "skills_match": 90,
                    "role_alignment": 80,
                    "experience_suitability": 75,
                    "strengths_alignment": 85,
                    "overall_fit": "excellent/good/moderate",
                    "key_qualifications": ["Qualification 1", "Qualification 2", "Qualification 3"],
                    "reason": "Detailed explanation of why this employee is well-suited for the task",
                    "potential_gaps": ["Any skill or experience gaps", "Other considerations"],
                    "development_opportunity": true/false,
                    "confidence": "high/medium/low"
                }}
            ],
            "analysis_summary": "Brief summary of the overall matching analysis",
            "total_employees_considered": {len(employees)}
        }}
        """
        
        # Update progress
        update_data = {
            "output_json": {
                "status": "processing",
                "progress": 70,
                "current_activity": "AI analyzing employee-task matching",
                "task_id": task['id']
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(update_data).eq("id", ai_meta_id).execute()
        
        # Call AI for recommendations
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an HR expert specializing in talent matching and task assignment. Return ONLY valid JSON with employee recommendations and analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
            timeout=30
        )
        
        response_text = response.choices[0].message.content.strip()
        ai_recommendations = safe_json_parse(response_text, {})
        
        processing_time = time.time() - start_time
        
        # Update task with recommendations
        strategic_meta = task.get('strategic_metadata', {})
        strategic_meta['ai_recommendations'] = ai_recommendations.get('recommendations', [])
        strategic_meta['employee_recommendations_available'] = True
        strategic_meta['recommendations_analysis'] = ai_recommendations.get('analysis_summary', '')
        strategic_meta['recommendations_generated_at'] = datetime.utcnow().isoformat()
        strategic_meta['total_employees_considered'] = ai_recommendations.get('total_employees_considered', len(employees))
        
        update_result = supabase.table("action_plans").update({
            "strategic_metadata": strategic_meta
        }).eq("id", task['id']).execute()
        
        # Final update to AI meta
        final_update = {
            "prompt": prompt,
            "raw_response": response_text,
            "output_json": {
                "status": "completed",
                "progress": 100,
                "task_id": task['id'],
                "recommendations_generated": len(strategic_meta['ai_recommendations']),
                "processing_time": processing_time,
                "analysis_summary": strategic_meta['recommendations_analysis'],
                "top_recommendation": strategic_meta['ai_recommendations'][0] if strategic_meta['ai_recommendations'] else None
            },
            "confidence": 0.85,
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(final_update).eq("id", ai_meta_id).execute()
        
        print(f"✅ Employee recommendations completed in {processing_time:.2f}s for task {task['id']}")
        print(f"📊 Generated {len(strategic_meta['ai_recommendations'])} recommendations")
        
    except Exception as e:
        error_msg = f"Error in employee recommendations: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Update AI meta with error
        try:
            supabase.table("ai_meta").update({
                "output_json": {
                    "status": "error",
                    "error": error_msg,
                    "progress": 0
                },
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", ai_meta_id).execute()
        except Exception as update_error:
            print(f"❌ Failed to update AI meta with error: {update_error}")
        
        # Mark task as having failed recommendations
        try:
            strategic_meta = task.get('strategic_metadata', {})
            strategic_meta['employee_recommendations_available'] = False
            strategic_meta['recommendations_failed'] = True
            strategic_meta['recommendations_error'] = str(e)
            
            supabase.table("action_plans").update({
                "strategic_metadata": strategic_meta
            }).eq("id", task['id']).execute()
        except Exception as task_error:
            print(f"❌ Failed to update task with error status: {task_error}")

# ========== NOTIFICATION FUNCTIONS ==========

def get_admin_employee_id():
    """Get admin employee ID for notifications"""
    try:
        supabase = get_supabase_client()
        admin_result = supabase.table("employees").select("id").eq("email", "admin@leanchem.com").execute()
        if admin_result.data:
            return admin_result.data[0]['id']
        return None
    except Exception as e:
        print(f"⚠️ Failed to get admin employee ID: {e}")
        return None


def fallback_task_classification(goal_data):
    try:
        title = goal_data['title'].lower()
        deadline = goal_data.get('deadline', '2025-12-31')
        try:
            deadline_date = datetime.fromisoformat(deadline.replace('Z', '')).date()
        except:
            deadline_date = datetime.now().date() + timedelta(days=90)
        
        tasks = []
        for i in range(3):
            task_deadline = (deadline_date - timedelta(days=(2-i)*15)).isoformat()
            tasks.append({
                "task_description": f"Task {i+1}: Execute part of {title}",
                "due_date": task_deadline,
                "priority": "medium",
                "estimated_hours": 16,
                "required_skills": ["project management", "communication"],
                "success_criteria": f"Complete part {i+1} of the goal",
                "complexity": "medium"
            })
        return tasks, "Fallback classification completed"
    except Exception as e:
        print(f"❌ Fallback classification error: {e}")
        return [], f"Fallback classification failed: {str(e)}"
    
def update_task_status_based_on_dependencies(task_id, supabase):
    """Update task status based on dependency completion"""
    try:
        # Get task with dependencies
        task_result = supabase.table("action_plans").select("dependencies, status").eq("id", task_id).execute()
        if not task_result.data:
            return
        
        task = task_result.data[0]
        dependencies = task.get('dependencies', [])
        
        if not dependencies:
            return
        
        # Check if all dependencies are completed
        all_completed = True
        for dep_id in dependencies:
            dep_result = supabase.table("action_plans").select("status").eq("id", dep_id).execute()
            if dep_result.data and dep_result.data[0].get('status') != 'completed':
                all_completed = False
                break
        
        # If all dependencies completed and task was waiting, set to not_started
        if all_completed and task.get('status') == 'waiting':
            supabase.table("action_plans").update({
                "status": "not_started",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", task_id).execute()
            
    except Exception as e:
        print(f"❌ Error updating task status based on dependencies: {e}")

def get_available_tasks_for_dependencies(task_id, supabase):
    """Get available tasks that can be set as dependencies"""
    try:
        # Get all tasks except the current one
        result = supabase.table("action_plans").select("id, task_description, status, due_date").neq("id", task_id).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"❌ Error getting available tasks for dependencies: {e}")
        return []

# ========== ROUTES ==========
@task_bp.route('/api/tasks/<task_id>/generate-employee-recommendations', methods=['POST'])
@token_required
@admin_required
def generate_employee_recommendations(task_id):
    """Generate AI employee recommendations for a specific task"""
    try:
        supabase = get_supabase_client()
        
        # Get task details
        task_result = supabase.table("action_plans").select("*, objectives(title)").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = task_result.data[0]
        
        # Get all active employees
        employees_result = supabase.table("employees").select("id, name, role, title, skills, experience_years, department, strengths, google_drive_jd").eq("is_active", True).execute()
        employees = employees_result.data if employees_result.data else []
        
        if not employees:
            return jsonify({'success': False, 'error': 'No active employees found'}), 400
        
        # Create AI meta record for recommendations
        ai_meta_data = {
            "source": "chatgpt-employee-recommendations",
            "model": "gpt-3.5-turbo",
            "input_json": {
                "task_id": task_id,
                "task_description": task['task_description'],
                "employees_count": len(employees),
                "status": "starting"
            },
            "output_json": {
                "status": "processing",
                "progress": 0,
                "current_activity": "Starting employee recommendations",
                "task_id": task_id
            },
            "created_at": datetime.utcnow().isoformat()
        }
        
        ai_meta_result = supabase.table("ai_meta").insert(ai_meta_data).execute()
        if not ai_meta_result.data:
            return jsonify({'success': False, 'error': 'Failed to create AI meta record'}), 500
        
        ai_meta_id = ai_meta_result.data[0]['id']
        
        # Start recommendation process in background
        threading.Thread(
            target=process_employee_recommendations_for_task,
            args=(task, employees, ai_meta_id),
            daemon=True
        ).start()
        
        return jsonify({
            'success': True, 
            'ai_meta_id': ai_meta_id,
            'message': 'AI employee recommendations processing started',
            'task_id': task_id
        })
        
    except Exception as e:
        error_msg = f"Error starting employee recommendations: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500

@task_bp.route('/api/tasks/<task_id>/apply-employee-recommendation', methods=['POST'])
@token_required
@admin_required
def apply_employee_recommendation(task_id):
    """Apply a specific employee recommendation to a task - UPDATED TO PRESERVE STRATEGIC METADATA"""
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        
        employee_id = data.get('employee_id')
        recommendation_data = data.get('recommendation_data', {})
        
        if not employee_id:
            return jsonify({'success': False, 'error': 'Employee ID is required'}), 400
        
        # First get the current task to preserve strategic_metadata and check existing assignments
        current_task_result = supabase.table("action_plans").select("strategic_metadata, assigned_to, assigned_to_multiple").eq("id", task_id).execute()
        current_strategic_meta = {}
        current_assigned_to = None
        current_assigned_multiple = []
        
        if current_task_result.data:
            current_task = current_task_result.data[0]
            current_strategic_meta = current_task.get('strategic_metadata', {})
            current_assigned_to = current_task.get('assigned_to')
            current_assigned_multiple = current_task.get('assigned_to_multiple') or []
        
        # Check if employee is already assigned
        employee_uuid = safe_uuid(employee_id)
        if employee_uuid in current_assigned_multiple or employee_uuid == current_assigned_to:
            return jsonify({'success': False, 'error': 'This employee is already assigned to this task'}), 400
        
        # Add to multiple assignments (keep existing ones)
        new_assigned_multiple = list(current_assigned_multiple)
        if employee_uuid not in new_assigned_multiple:
            new_assigned_multiple.append(employee_uuid)
        
        # If no primary assignee, set this as primary
        if not current_assigned_to:
            primary_assignee = employee_uuid
        else:
            primary_assignee = current_assigned_to
        
        # Update task with assigned employee while preserving strategic metadata
        update_data = {
            "assigned_to": primary_assignee,
            "assigned_to_multiple": new_assigned_multiple,
            "status": "not_started",
            "updated_at": datetime.utcnow().isoformat(),
            "strategic_metadata": {
                # Preserve existing strategic metadata
                **current_strategic_meta,
                # Add recommendation application info
                "ai_recommendation_applied": True,
                "applied_recommendation": recommendation_data,
                "applied_at": datetime.utcnow().isoformat()
            }
        }
        
        result = supabase.table("action_plans").update(update_data).eq("id", task_id).execute()
        
        if result.data:
            # Create notification for the assigned employee
            create_enhanced_task_notification(
                task_id,
                "task_assigned",
                f"New task assigned to you: {result.data[0]['task_description'][:100]}...",
                assigned_by=g.user.get('name', 'Admin')
            )
            
            return jsonify({
                'success': True,
                'message': 'Employee recommendation applied successfully',
                'task': result.data[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to apply recommendation'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def update_task_strategic_details(task_id, strategic_analysis):
    """Update task with strategic details"""
    try:
        supabase = get_supabase_client()
        
        strategic_metadata = {
            "context": strategic_analysis.get('context', ''),
            "objective": strategic_analysis.get('objective', ''),
            "process": strategic_analysis.get('process', ''),
            "delivery": strategic_analysis.get('delivery', ''),
            "reporting_requirements": strategic_analysis.get('reporting_requirements', ''),
            # Include other existing strategic metadata
            "required_skills": strategic_analysis.get('required_skills', []),
            "success_criteria": strategic_analysis.get('success_criteria', ''),
            "complexity": strategic_analysis.get('complexity', 'medium')
        }
        
        update_data = {
            "strategic_metadata": strategic_metadata,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("action_plans").update(update_data).eq("id", task_id).execute()
        return result.data[0] if result.data else None
        
    except Exception as e:
        print(f"❌ Error updating task strategic details: {e}")
        return None
 
# ========== UPDATED STANDARD ORDER-TO-DELIVERY PROCESS ==========
def get_next_objective_number():
    """Get the next objective number by finding the highest pre_number and incrementing.

    NOTE:
    - The `pre_number` column in the `objectives` table is an INTEGER in the database.
    - This function therefore MUST return an `int`, not a formatted string like "OBJ-001",
      otherwise Postgres will raise `22P02: invalid input syntax for type integer`.
    - Frontend display formatting (e.g. "OBJ-001") is handled separately in the React app.
    """
    try:
        supabase = get_supabase_client()
        
        # Get the highest pre_number from objectives (stored as INTEGER in DB)
        result = supabase.table("objectives").select("pre_number").order("pre_number", desc=True).limit(1).execute()
        
        if result.data and result.data[0].get('pre_number'):
            highest_number = result.data[0]['pre_number']
            # Defensive handling in case old data was stored as a string like "OBJ-001"
            try:
                if isinstance(highest_number, str):
                    if highest_number.startswith('OBJ-'):
                        current_num = int(highest_number.split('-')[1])
                    else:
                        current_num = int(highest_number)
                else:
                    # If it's already a number, use it directly
                    current_num = int(highest_number)
                return current_num + 1
            except Exception:
                # Fallback if parsing fails for some unexpected legacy value
                return 1
        else:
            # First objective
            return 1
            
    except Exception as e:
        print(f"❌ Error getting next objective number: {e}")
        # Safe fallback for DB errors
        return 1

@task_bp.route('/api/tasks/goals/classify-only', methods=['POST'])
@token_required
def create_goal_classify_only():
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        if not data.get('title'):
            return jsonify({'success': False, 'error': 'Goal title required'}), 400
        
        # 🎯 AUTO-GENERATE OBJECTIVE NUMBER
        next_objective_number = get_next_objective_number()
        
        goal_data = {
            "title": data['title'].strip(),
            "description": data.get('description', '').strip(),
            "output": data.get('output', '').strip(),
            "deadline": data.get('deadline'),
            "department": data.get('department', '').strip(),
            "priority": data.get('priority', 'medium'),
            "status": "draft",
            "created_by": safe_get_employee_id(),
            "assignee_mode": "manual",
            "pre_number": next_objective_number  # 🎯 ADD AUTO-GENERATED NUMBER
        }
        goal_data = {k: v for k, v in goal_data.items() if v is not None and v != ''}
        
        result = supabase.table("objectives").insert(goal_data).execute()
        if not result.data:
            return jsonify({'success': False, 'error': 'Failed to create goal'}), 500
        
        goal = result.data[0]
        ai_tasks, ai_breakdown, ai_processing_time = [], None, 0
        ai_meta_id = None
        
        if data.get('auto_classify') and client:
            # Get template from frontend (defaults to 'auto' for AI classification)
            template = data.get('template', 'auto')
            
            # Create initial AI meta record according to schema
            initial_ai_meta = {
                "source": "chatgpt-classify-only",
                "model": "gpt-3.5-turbo",
                "input_json": {
                    "goal_id": goal['id'],
                    "goal_title": data['title'],
                    "goal_description": data.get('description', ''),
                    "goal_output": data.get('output', ''),
                    "goal_deadline": data.get('deadline'),
                    "objective_number": next_objective_number,
                    "template": template,  # 🎯 ADD TEMPLATE INFO
                    "status": "starting"
                },
                "output_json": {
                    "status": "starting", 
                    "progress": 0, 
                    "goal_id": goal['id'],
                    "objective_number": next_objective_number,
                    "template": template
                },
                "confidence": None,
                "created_at": datetime.utcnow().isoformat()
            }
            
            ai_meta_result = supabase.table("ai_meta").insert(initial_ai_meta).execute()
            if ai_meta_result.data:
                ai_meta_id = ai_meta_result.data[0]['id']
                supabase.table("objectives").update({'ai_meta_id': ai_meta_id}).eq('id', goal['id']).execute()
                goal['ai_meta_id'] = ai_meta_id
            
            ai_tasks, ai_breakdown, ai_processing_time = classify_goal_to_tasks_only(goal, data, ai_meta_id, template)
        
        return jsonify({
            'success': True,
            'goal': goal,
            'ai_tasks': ai_tasks,
            'ai_breakdown': ai_breakdown,
            'ai_processing_time': ai_processing_time,
            'ai_meta_id': ai_meta_id,
            'message': f'Goal {next_objective_number} created with task classification'  # 🎯 SHOW NUMBER
        })
    except Exception as e:
        print(f"❌ Error creating goal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
def get_updated_standard_process():
    """Return the updated standard process framework - DEPRECATED, use predefined_processes.py instead"""
    # Import from predefined_processes module
    from predefined_processes import get_order_to_delivery_process
    return get_order_to_delivery_process()

def get_updated_standard_process_old():
    """Return the updated standard process framework - OLD VERSION"""
    return {
        "1. FINALIZE DEAL DOCUMENTATION (1 day)": {
            "responsible": "Account Executive",
            "activities": "Complete agreement, Proforma Invoice (PI), and other commercial terms",
            "deliverable": "Signed PI and commercial agreement"
        },
        "2. SUPPLIER STOCK ORDER CONFIRMATION (1 day)": {
            "responsible": "Supply Chain Specialist", 
            "activities": "Contact Kenya suppliers, verify stock availability, reserve inventory, obtain written confirmation, formal order placement, request proforma invoice and final pricing",
            "deliverable": "Supplier order confirmation"
        },
        "3. PRODUCT MANAGEMENT APPROVAL (0.5 day)": {
            "responsible": "Product Development Manager",
            "activities": "Validate product specifications meet quality standards",
            "deliverable": "Product acceptance confirmation"
        },
        "4. FOREIGN CURRENCY PERMIT APPLICATION (5 days)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Apply for foreign currency approval from appropriate bank, obtain permit",
            "deliverable": "Bank permit for foreign currency"
        },
        "5. SUPPLIER PAYMENT PROCESSING (5 days)": {
            "responsible": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
            "activities": "Process payment to supplier, request export documentation initiation",
            "deliverable": "Payment confirmation and supplier acknowledgment"
        },
        "6. TRANSPORTATION LOGISTICS ARRANGEMENT (1 day)": {
            "responsible": "Kenyan operation specialist", 
            "activities": "Identify appropriate truck, coordinate with supplier for export documentation",
            "deliverable": "Transport arrangement confirmation and supplier export documentation"
        },
        "7. KENYA SIDE DISPATCH & CLEARANCE (2 days)": {
            "responsible": "Kenyan operation specialist",
            "activities": "Coordinate product dispatch from Kenya Moyale side, complete Kenyan customs clearance",
            "deliverable": "Kenya border clearance documents"
        },
        "8. ETHIOPIAN CUSTOMS CLEARANCE (2 days)": {
            "responsible": "Ethiopian Operation Specialist",
            "activities": "Handle Ethiopian customs clearance, process 1st payment based on permit value",
            "deliverable": "Ethiopian customs clearance certificate"
        },
        "9. TAX REASSESSMENT & FINAL PAYMENT (0.5 day)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Complete tax reassessment, process 2nd tax payment",
            "deliverable": "Final tax payment confirmation"
        },
        "10. PRODUCT LOADING & DISPATCH (0.5 day)": {
            "responsible": "Ethiopian Operation Specialist",
            "activities": "Supervise product loading, coordinate dispatch to final destination", 
            "deliverable": "Dispatch confirmation"
        },
        "11. TRANSPORT MONITORING (2 days)": {
            "responsible": "Ethiopian Operation Specialist",
            "activities": "Track truck movement, coordinate with transport provider",
            "deliverable": "Regular transport status updates"
        },
        "12. FINAL DELIVERY & WAREHOUSE HANDOVER (1 day)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Coordinate final delivery to customer warehouse, complete handover",
            "deliverable": "Customer delivery confirmation and signed receipt"
        },
        "13. POST-DELIVERY DOCUMENTATION & SETTLEMENT (1 day)": {
            "responsible": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
            "activities": "Complete all financial settlements, document archiving, lesson learned",
            "deliverable": "Closed order file and settlement confirmation"
        }
    }

def get_kickoff_information_requirements():
    """Return the information required to start the order-to-delivery process"""
    return {
        "CLIENT INFORMATION": [
            "Client company name and contact details",
            "Authorized signatory information", 
            "Delivery address and warehouse details",
            "Contact person for delivery coordination"
        ],
        "COMMERCIAL DOCUMENTS": [
            "Finalized commercial agreement",
            "Signed Proforma Invoice (PI)",
            "Payment terms and conditions",
            "Incoterms agreement",
            "Credit terms (if applicable)"
        ],
        "PRODUCT SPECIFICATIONS": [
            "Product name and description",
            "Technical specifications and standards",
            "Quantity required",
            "Brand and manufacturer details", 
            "Quality requirements and certifications",
            "Packaging specifications"
        ],
        "SUPPLIER INFORMATION": [
            "Kenya supplier contact details",
            "Supplier product availability confirmation",
            "Supplier pricing and terms",
            "Supplier lead time commitments"
        ],
        "LOGISTICS REQUIREMENTS": [
            "Preferred transport mode",
            "Special handling requirements",
            "Insurance requirements",
            "Delivery timeline expectations"
        ],
        "FINANCIAL REQUIREMENTS": [
            "Total order value",
            "Currency requirements", 
            "Payment schedule",
            "Bank details for transfers",
            "Tax and duty considerations"
        ],
        "REGULATORY REQUIREMENTS": [
            "Import license details",
            "Product certification requirements",
            "Customs clearance prerequisites",
            "Any special permits needed"
        ]
    }

def generate_13_step_delivery_tasks(goal, goal_data, ai_meta_id):
    """Generate exactly 13 tasks using the predefined delivery process"""
    start_time = time.time()
    
    try:
        # Get the predefined standard process
        standard_process = get_updated_standard_process()
        
        # 🎯 GET OBJECTIVE NUMBER FROM GOAL
        objective_number = goal.get('pre_number', 'N/A')
        
        # Create prompt specifically for delivery goals - INCLUDING OBJECTIVE NUMBER
        prompt = f"""
You are generating tasks for a DELIVERY/PROCUREMENT goal. Use the EXACT 13-step Order-to-Delivery process.

OBJECTIVE: {objective_number} - {goal_data['title']}
DESCRIPTION: {goal_data.get('description', '')}
OUTPUT: {goal_data.get('output', '')}

STANDARD 13-STEP PROCESS:
{json.dumps(standard_process, indent=2)}

Generate EXACTLY 13 tasks following this process exactly. For each task:
1. Use the EXACT process step title as task_description
2. Include due_date within Q4 2025
3. Use appropriate priority (high/medium/low)
4. Set estimated_hours between 4-16 hours
5. CRITICAL: Use the EXACT assigned_role from the standard process step - DO NOT CHANGE IT
6. Reference objective {objective_number} in strategic context

IMPORTANT: The assigned_role MUST match exactly the "responsible" field from the corresponding step in the standard process. Do not modify or change the role names.

Return ONLY valid JSON with exactly 13 tasks in this format:
{{
    "tasks": [
        {{
            "task_description": "1. FINALIZE DEAL DOCUMENTATION (1 day): Complete agreement, Proforma Invoice (PI), and other commercial terms",
            "due_date": "2025-11-05",
            "priority": "high",
            "estimated_hours": 8,
            "assigned_role": "Account Executive",
            "strategic_context": "Executing step 1 for objective {objective_number}"
        }},
        ... // 12 more tasks
    ]
}}
"""
        
        print(f"🤖 Generating 13-step delivery tasks for {objective_number}: {goal_data['title'][:50]}...")
        
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 40, "13-Step Delivery Process", f"Applying standard delivery framework for {objective_number}")
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON. Generate exactly 13 tasks using the 13-step delivery process."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=3000,
            timeout=30
        )
        
        task_time = time.time() - start_time
        response_text = response.choices[0].message.content.strip()
        
        print(f"🤖 AI Response: {response_text[:500]}...")
        
        # Parse the AI response
        ai_analysis = safe_json_parse(response_text, {})
        if not ai_analysis:
            print("❌ Failed to parse AI response as JSON")
            raise Exception("Invalid JSON response from AI")
        
        ai_tasks_data = ai_analysis.get('tasks', [])
        
        # CRITICAL: Validate we have exactly 13 tasks
        if len(ai_tasks_data) != 13:
            print(f"⚠️ AI returned {len(ai_tasks_data)} tasks, generating 13-step fallback")
            return generate_13_step_fallback_tasks(goal, goal_data, standard_process, ai_meta_id)
        
        # Process and save tasks - PASS OBJECTIVE NUMBER
        return process_and_save_tasks(goal, ai_tasks_data, standard_process, ai_meta_id, task_time, "13-step_delivery")
        
    except Exception as e:
        print(f"❌ Error in 13-step delivery generation: {e}")
        # Fallback to predefined 13-step process
        return generate_13_step_fallback_tasks(goal, goal_data, get_updated_standard_process(), ai_meta_id)
    
def classify_goal_to_tasks_only(goal, goal_data, ai_meta_id, template='auto'):
    """
    Classify goal to tasks based on template selection.
    
    Args:
        goal: Goal/objective record
        goal_data: Goal data dictionary
        ai_meta_id: AI meta record ID
        template: Template type ('auto' for AI classification, 'order_to_delivery' for predefined process, etc.)
    """
    try:
        start_time = time.time()
        if not client:
            tasks, message = fallback_task_classification(goal_data)
            return tasks, message, time.time() - start_time
        
        # 🎯 TEMPLATE-BASED ROUTING
        if template == 'order_to_delivery' or template == 'order-to-delivery':
            print(f"🎯 PREDEFINED PROCESS: Using Order-to-Delivery template")
            return generate_predefined_process_tasks(goal, goal_data, ai_meta_id, 'order_to_delivery')
        
        elif template == 'stock_to_delivery' or template == 'stock-to-delivery':
            print(f"🎯 PREDEFINED PROCESS: Using Stock-to-Delivery template")
            return generate_predefined_process_tasks(goal, goal_data, ai_meta_id, 'stock_to_delivery')
        
        elif template == 'lead_to_delivery' or template == 'lead-to-delivery':
            print(f"🎯 PREDEFINED PROCESS: Using Lead-to-Delivery template")
            return generate_predefined_process_tasks(goal, goal_data, ai_meta_id, 'lead_to_delivery')
        
        elif template == 'auto':
            # 🎯 AI CLASSIFICATION: Fully rely on AI for task generation
            print(f"🎯 AI CLASSIFICATION: Using full AI task generation with RAG")
            return generate_ai_custom_tasks(goal, goal_data, ai_meta_id)
        else:
            # Check if template matches any predefined process
            predefined_processes = get_predefined_processes_registry()
            if template in predefined_processes:
                print(f"🎯 PREDEFINED PROCESS: Using {template} template")
                return generate_predefined_process_tasks(goal, goal_data, ai_meta_id, template)
            else:
                # Fallback to AI classification
                print(f"🎯 UNKNOWN TEMPLATE '{template}': Falling back to AI classification")
            return generate_ai_custom_tasks(goal, goal_data, ai_meta_id)
        
    except Exception as e:
        log_ai_error("task_classification", str(e), ai_meta_id, goal['id'])
        tasks, message = generate_fallback_tasks_based_on_type(goal_data)
        return tasks, message, time.time() - start_time

def detect_delivery_goal(goal_data):
    """Detect if this is a delivery/procurement goal that should use 13-step process"""
    delivery_keywords = [
        'deliver', 'procure', 'order', 'ship', 'logistics', 'supply', 
        'import', 'export', 'customs', 'clearance', 'transport',
        'stock', 'inventory', 'supplier', 'shipment', 'border',
        'kenya', 'ethiopia', 'moyale', 'clearance', 'customs'
    ]
    
    title = goal_data.get('title', '').lower()
    description = goal_data.get('description', '').lower()
    output = goal_data.get('output', '').lower()
    
    # Check for delivery-related keywords
    text_to_check = f"{title} {description} {output}"
    
    keyword_matches = sum(1 for keyword in delivery_keywords if keyword in text_to_check)
    
    # If we have at least 2 delivery keywords, consider it a delivery goal
    is_delivery = keyword_matches >= 2
    
    print(f"🔍 Goal Type Detection: {keyword_matches} delivery keywords - {'DELIVERY' if is_delivery else 'NON-DELIVERY'}")
    print(f"   Title: {title}")
    print(f"   Keywords found: {[kw for kw in delivery_keywords if kw in text_to_check]}")
    
    return is_delivery

def generate_fallback_tasks_based_on_type(goal_data):
    """Generate fallback tasks based on goal type (delivery vs custom)"""
    try:
        # Check if this is a delivery goal
        is_delivery = detect_delivery_goal(goal_data)
        
        if is_delivery:
            print("🎯 Using delivery fallback for goal")
            # Return empty tasks - let the calling function handle the delivery fallback
            return [], "Delivery goal - will use 13-step process"
        else:
            print("🎯 Using custom fallback for goal")
            # For now return empty, the calling function will handle custom fallback
            return [], "Custom goal - will use AI generation"
            
    except Exception as e:
        print(f"❌ Error in fallback task type detection: {e}")
        return [], "Error in fallback detection"

def update_ai_progress(ai_meta_id, progress, activity, details=""):
    """Update AI meta progress"""
    try:
        supabase = get_supabase_client()
        update_data = {
            "output_json": {
                "status": "processing",
                "progress": progress,
                "current_activity": activity,
                "activity_details": details
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(update_data).eq("id", ai_meta_id).execute()
        print(f"📊 AI Progress: {progress}% - {activity}")
    except Exception as e:
        print(f"❌ Error updating AI progress: {e}")

def log_ai_error(function_name, error_message, ai_meta_id=None, goal_id=None, prompt=None, response=None):
    """Log AI errors with context"""
    print(f"❌ AI Error in {function_name}: {error_message}")
    
    if ai_meta_id:
        try:
            supabase = get_supabase_client()
            error_data = {
                "output_json": {
                    "status": "error",
                    "error": error_message,
                    "function": function_name,
                    "goal_id": goal_id,
                    "error_time": datetime.utcnow().isoformat()
                },
                "updated_at": datetime.utcnow().isoformat()
            }
            supabase.table("ai_meta").update(error_data).eq("id", ai_meta_id).execute()
        except Exception as e:
            print(f"❌ Failed to log AI error: {e}")

def fallback_task_classification(goal_data):
    """Fallback task classification when AI is not available"""
    try:
        supabase = get_supabase_client()
        created_tasks = []
        
        # Simple fallback - create 3 basic tasks
        base_tasks = [
            {
                "description": f"Plan and strategize {goal_data['title']}",
                "priority": "high",
                "estimated_hours": 8
            },
            {
                "description": f"Execute {goal_data['title']}",
                "priority": "medium", 
                "estimated_hours": 16
            },
            {
                "description": f"Review and complete {goal_data['title']}",
                "priority": "low",
                "estimated_hours": 4
            }
        ]
        
        base_date = datetime.now()
        
        for i, task_template in enumerate(base_tasks):
            due_date = (base_date + timedelta(days=i*3)).strftime('%Y-%m-%d')
            
            task_record = {
                "task_description": task_template['description'],
                "objective_id": goal_data.get('id', 'fallback'),
                "due_date": due_date,
                "priority": task_template['priority'],
                "estimated_hours": task_template['estimated_hours'],
                "status": "not_started",
                "completion_percentage": 0,
                "ai_suggested": False
            }
            
            # For fallback, we don't actually save to database without a goal ID
            created_tasks.append(task_record)
        
        return created_tasks, f"Generated {len(created_tasks)} fallback tasks"
        
    except Exception as e:
        print(f"❌ Error in fallback task classification: {e}")
        return [], "Failed to generate fallback tasks"

def generate_custom_fallback_tasks(goal, goal_data, ai_meta_id):
    """Generate fallback tasks for non-delivery goals when AI fails"""
    start_time = time.time()
    try:
        supabase = get_supabase_client()
        created_tasks = []
        
        base_date = datetime.now()
        
        # Create 5-7 generic strategic tasks based on goal type
        generic_tasks = [
            {
                "description": f"Strategic planning and analysis for {goal_data['title']}",
                "role": "Account Executive",
                "days_offset": 0,
                "priority": "high"
            },
            {
                "description": f"Research and market analysis for {goal_data['title']}",
                "role": "Product Development Manager", 
                "days_offset": 2,
                "priority": "high"
            },
            {
                "description": f"Stakeholder engagement and partnership development",
                "role": "Account Executive",
                "days_offset": 5,
                "priority": "medium"
            },
            {
                "description": f"Resource planning and budget allocation",
                "role": "Commercial and Finance Specialist",
                "days_offset": 7,
                "priority": "medium"
            },
            {
                "description": f"Implementation plan and timeline development",
                "role": "Supply Chain Specialist",
                "days_offset": 10,
                "priority": "medium"
            },
            {
                "description": f"Progress review and adjustment strategy",
                "role": "Account Executive",
                "days_offset": 14,
                "priority": "low"
            }
        ]
        
        for i, task_template in enumerate(generic_tasks):
            due_date = (base_date + timedelta(days=task_template['days_offset'])).strftime('%Y-%m-%d')
            
            strategic_metadata = {
                "required_skills": ["Strategic planning", "Analysis", "Coordination"],
                "success_criteria": f"Complete {task_template['description']} successfully",
                "complexity": "medium",
                "strategic_analysis": {
                    "validation_score": "Custom fallback applied",
                    "context": f"Custom strategic task for {goal_data['title']}",
                    "objective": goal_data['title'],
                    "process": task_template['description'],
                    "delivery": due_date,
                    "reporting_requirements": "Completion report and next steps",
                    "q4_execution_context": "Q4 2025 execution",
                    "process_applied": "Custom AI Task Generation",
                    "goal_type": "custom"
                },
                "strategic_phase": f"Strategic Phase {i+1}",
                "key_stakeholders": [task_template['role']],
                "potential_bottlenecks": ["Resource constraints", "Timeline pressure"],
                "resource_requirements": ["Strategic planning tools"],
                "assigned_role": task_template['role'],
                "process_step": f"Custom Step {i+1}",
                "information_requirements": "Goal-specific information",
                "context": f"Executing {task_template['description']}",
                "objective": goal_data['title'],
                "process": task_template['description'],
                "delivery": due_date,
                "reporting_requirements": "Completion report",
                "goal_type": "custom",
                "objective_number": goal.get('pre_number', 'N/A')
            }
            
            task_record = {
                "task_description": task_template['description'],
                "objective_id": goal['id'],
                "due_date": due_date,
                "priority": task_template['priority'],
                "estimated_hours": 8,
                "status": "ai_suggested",
                "completion_percentage": 0,
                "ai_suggested": True,
                "strategic_metadata": strategic_metadata
            }
            
            task_result = supabase.table("action_plans").insert(task_record).execute()
            if task_result.data:
                created_tasks.append(task_result.data[0])
        
        # Update AI meta with custom fallback info
        if ai_meta_id:
            supabase.table("ai_meta").update({
                "output_json": {
                    "status": "custom_fallback_completed",
                    "tasks_generated": len(created_tasks),
                    "goal_id": goal['id'],
                    "goal_type": "custom",
                    "process_applied": "Custom fallback",
                    "framework_version": "custom",
                    "fallback_used": True,
                    "rag_recommendations_status": "pending"
                }
            }).eq("id", ai_meta_id).execute()
        
        # RAG recommendations will be generated only when user clicks "Recommend Employee" button
        return created_tasks, f"Generated {len(created_tasks)} custom fallback tasks", time.time() - start_time
        
    except Exception as e:
        print(f"❌ Error in custom fallback generation: {e}")
        return [], "Failed to generate custom fallback tasks", 0

def process_and_save_custom_tasks(goal, ai_tasks_data, ai_analysis, ai_meta_id, task_time):
    """Process and save custom AI-generated tasks to database"""
    try:
        supabase = get_supabase_client()
        created_tasks = []
        
        strategic_analysis = ai_analysis.get('strategic_analysis', {})
        
        for i, task_data in enumerate(ai_tasks_data):
            if not task_data.get('task_description'):
                continue
            
            # For custom tasks, we don't have predefined process steps
            # Use AI-generated data with fallbacks
            strategic_metadata = {
                "required_skills": task_data.get('required_skills', ["Strategic planning", "Coordination"]),
                "success_criteria": task_data.get('success_criteria', 'Task completed successfully'),
                "complexity": task_data.get('complexity', 'medium'),
                "strategic_analysis": strategic_analysis,
                "strategic_phase": task_data.get('strategic_phase', f'Phase {i+1}'),
                "key_stakeholders": task_data.get('key_stakeholders', []),
                "potential_bottlenecks": task_data.get('potential_bottlenecks', []),
                "resource_requirements": task_data.get('resource_requirements', []),
                "assigned_role": task_data.get('assigned_role', 'Account Executive'),
                "process_step": f"Custom Step {i+1}",
                "context": task_data.get('context', ''),
                "objective": goal['title'],
                "process": task_data.get('process', task_data['task_description']),
                "delivery": task_data.get('due_date'),
                "reporting_requirements": task_data.get('reporting_requirements', 'Completion report'),
                "goal_type": "custom",
                "objective_number": goal.get('pre_number', 'N/A')
            }
            
            task_record = {
                "task_description": task_data['task_description'],
                "objective_id": goal['id'],
                "due_date": task_data.get('due_date'),
                "priority": task_data.get('priority', 'medium'),
                "estimated_hours": task_data.get('estimated_hours', 8),
                "status": "ai_suggested",
                "completion_percentage": 0,
                "ai_meta_id": ai_meta_id,
                "ai_suggested": True,
                "strategic_metadata": strategic_metadata
            }
            
            task_result = supabase.table("action_plans").insert(task_record).execute()
            if task_result.data:
                created_tasks.append(task_result.data[0])
        
        # Update AI meta with custom task info
        if ai_meta_id:
            supabase.table("ai_meta").update({
                "output_json": {
                    "status": "custom_ai_tasks_completed",
                    "tasks_generated": len(created_tasks),
                    "goal_id": goal['id'],
                    "goal_type": "custom",
                    "process_applied": "Custom AI Generation",
                    "framework_version": "custom",
                    "ai_analysis_used": True,
                    "strategic_analysis": strategic_analysis,
                    "rag_recommendations_status": "pending"
                }
            }).eq("id", ai_meta_id).execute()
        
        # RAG recommendations will be generated only when user clicks "Recommend Employee" button
        return created_tasks, f"Created {len(created_tasks)} custom AI tasks", task_time
        
    except Exception as e:
        print(f"❌ Error processing custom tasks: {e}")
        import traceback
        traceback.print_exc()
        # Need goal_data for fallback - extract from goal if needed
        goal_data = {
            'title': goal.get('title', 'Unknown Goal'),
            'description': goal.get('description', ''),
            'output': goal.get('output', ''),
            'deadline': goal.get('deadline', 'Q4 2025')
        }
        return generate_custom_fallback_tasks(goal, goal_data, ai_meta_id)
    
def generate_ai_custom_tasks(goal, goal_data, ai_meta_id):
    """Generate custom AI tasks for non-delivery goals"""
    start_time = time.time()
    
    try:
        print(f"🤖 Generating custom AI tasks for: {goal_data['title'][:50]}...")
        
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 20, "Custom AI Task Generation", "Preparing AI classification")
        
        # Enhanced prompt with explicit JSON format
        prompt = f"""
You are generating tasks for a NON-DELIVERY goal. Create 5-8 appropriate, customized tasks.

GOAL INFORMATION:
- Title: {goal_data['title']}
- Description: {goal_data.get('description', 'N/A')}
- Output/Goal: {goal_data.get('output', 'N/A')}
- Deadline: {goal_data.get('deadline', 'Q4 2025')}

DEPARTMENT STRUCTURE:
- SUPPLY CHAIN: Logistics, inventory, customs, transport
- SALES: Client relationships, deals, partnerships  
- PRODUCT: Quality, specifications, testing
- FINANCE & ADMIN: Payments, compliance, administration

TASK FOCUS AREAS:
- Strategic planning and analysis
- Research and development  
- Partnership building
- Market analysis
- Process improvement
- Training and development

REQUIRED JSON FORMAT:
{{
  "tasks": [
    {{
      "task_description": "Clear, specific task description",
      "priority": "high|medium|low",
      "estimated_hours": 8,
      "due_date": "YYYY-MM-DD",
      "assigned_role": "Account Executive|Product Development Manager|Supply Chain Specialist|Commercial and Finance Specialist",
      "required_skills": ["Skill 1", "Skill 2"],
      "success_criteria": "What success looks like",
      "context": "Task context and background"
    }}
  ],
  "strategic_analysis": {{
    "context": "Overall strategic context",
    "objective": "{goal_data['title']}",
    "process": "Custom AI Task Generation",
    "delivery": "{goal_data.get('deadline', 'Q4 2025')}",
    "reporting_requirements": "Progress updates and completion reports",
    "goal_type": "custom"
  }}
}}

Generate 5-8 tasks. Return ONLY valid JSON in the exact format above. Do not include markdown code blocks.
"""
        
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 40, "Custom AI Task Generation", "Calling OpenAI API")
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a task planning expert. Return ONLY valid JSON in the exact format specified. Do not include markdown, code blocks, or any text outside the JSON."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000,
            timeout=60
        )
        
        task_time = time.time() - start_time
        response_text = response.choices[0].message.content.strip()
        
        print(f"📥 AI Response received ({len(response_text)} chars): {response_text[:200]}...")
        
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 60, "Custom AI Task Generation", "Parsing AI response")
        
        # Parse JSON response
        ai_analysis = safe_json_parse(response_text, {})
        
        if not ai_analysis:
            print(f"❌ Failed to parse AI response. Raw response: {response_text[:500]}")
            raise Exception("Invalid JSON response from AI - could not parse")
        
        ai_tasks_data = ai_analysis.get('tasks', [])
        
        if not ai_tasks_data:
            print(f"⚠️ AI response has no 'tasks' array. Full response: {ai_analysis}")
            raise Exception("AI response missing 'tasks' array")
        
        print(f"✅ Parsed {len(ai_tasks_data)} tasks from AI response")
        
        # Validate we have reasonable number of tasks
        if len(ai_tasks_data) < 3:
            print(f"⚠️ AI returned only {len(ai_tasks_data)} tasks (minimum 3 required), using fallback")
            return generate_custom_fallback_tasks(goal, goal_data, ai_meta_id)
        
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 80, "Custom AI Task Generation", f"Processing {len(ai_tasks_data)} tasks")
        
        # Process and save tasks
        result = process_and_save_custom_tasks(goal, ai_tasks_data, ai_analysis, ai_meta_id, task_time)
        
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 100, "Custom AI Task Generation", f"Successfully created {len(result[0])} tasks")
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error in custom AI task generation: {error_msg}")
        import traceback
        traceback.print_exc()
        
        if ai_meta_id:
            log_ai_error("generate_ai_custom_tasks", error_msg, ai_meta_id, goal.get('id'), prompt if 'prompt' in locals() else None, response_text if 'response_text' in locals() else None)
        
        # Fallback to custom fallback tasks
        return generate_custom_fallback_tasks(goal, goal_data, ai_meta_id)

def generate_predefined_process_tasks(goal, goal_data, ai_meta_id, process_name):
    """
    Generate tasks using a predefined process template.
    Uses EXACT predefined steps - no adding or removing tasks.
    Only customizes task descriptions for the specific objective.
    
    Args:
        goal: Goal/objective record
        goal_data: Goal data dictionary
        ai_meta_id: AI meta record ID
        process_name: Name of the predefined process (e.g., 'order_to_delivery')
    
    Returns:
        tuple: (created_tasks, message, processing_time)
    """
    start_time = time.time()
    supabase = get_supabase_client()
    
    try:
        # Get the predefined process from registry
        predefined_processes = get_predefined_processes_registry()
        if process_name not in predefined_processes:
            raise ValueError(f"Unknown predefined process: {process_name}")
        
        process_steps = predefined_processes[process_name]
        objective_number = goal.get('pre_number', 'N/A')
        goal_title = goal_data.get('title', '')
        
        # Extract customization info from goal title/description
        # Example: "Order to Delivery - DGEDA" -> customize for "DGEDA"
        customization_text = goal_title
        if ' - ' in goal_title:
            customization_text = goal_title.split(' - ', 1)[1]
        elif 'for ' in goal_title.lower():
            # Extract text after "for"
            parts = goal_title.lower().split('for ', 1)
            if len(parts) > 1:
                customization_text = parts[1].split()[0]  # Get first word after "for"
        
        created_tasks = []
        base_date = datetime.now()
        
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 30, f"Applying {process_name} process", 
                             f"Generating {len(process_steps)} predefined tasks for {objective_number}")
        
        # Generate tasks using EXACT predefined steps
        for i, (step_key, step_data) in enumerate(process_steps.items()):
            # Calculate due date based on step timing
            days_offset = i  # Default: sequential days
            if '(1 day)' in step_key:
                days_offset = i
            elif '(2 days)' in step_key:
                days_offset = i + 1
            elif '(5 days)' in step_key:
                days_offset = i + 4
            elif '(0.5 day)' in step_key:
                days_offset = i
            
            due_date = (base_date + timedelta(days=days_offset)).strftime('%Y-%m-%d')
            
            # Customize task description for specific objective
            # Replace generic terms with customization text if needed
            customized_activities = step_data['activities']
            if customization_text and customization_text != goal_title:
                # Add customization context (e.g., "for DGEDA")
                customized_activities = f"{step_data['activities']} for {customization_text}"
            
            # Customize step key if needed
            customized_step_key = step_key
            if customization_text and customization_text != goal_title:
                # Add customization to step title
                customized_step_key = step_key.replace(":", f" for {customization_text}:")
            
            strategic_metadata = {
                "required_skills": ["Process execution", "Coordination", step_data['responsible']],
                "success_criteria": f"Complete {customized_activities} successfully",
                "complexity": "medium",
                "strategic_analysis": {
                    "validation_score": f"{process_name} process applied",
                    "context": f"Predefined {process_name} process for {goal_title}",
                    "objective": goal_title,
                    "process": customized_activities,
                    "delivery": due_date,
                    "reporting_requirements": step_data['deliverable'],
                    "q4_execution_context": "Q4 2025 execution",
                    "process_applied": f"{process_name.upper().replace('_', '-')} Standard Framework",
                    "goal_type": process_name
                },
                "strategic_phase": f"Process Step {i+1}",
                "key_stakeholders": [step_data['responsible']],
                "potential_bottlenecks": ["Timeline constraints", "Coordination requirements"],
                "resource_requirements": ["Standard process tools"],
                "assigned_role": step_data['responsible'],  # 🎯 USE RECOMMENDED ROLE
                "process_step": customized_step_key,
                "information_requirements": f"Using {process_name} framework",
                "context": f"Executing {customized_step_key} for {goal_title}",
                "objective": goal_title,
                "process": customized_activities,
                "delivery": due_date,
                "reporting_requirements": step_data['deliverable'],
                "goal_type": process_name,
                "predefined_process": True,  # 🎯 FLAG FOR RAG SYSTEM
                "recommended_role": step_data['responsible']  # 🎯 FOR EMPLOYEE RECOMMENDATIONS
            }
            
            task_record = {
                "task_description": f"{customized_step_key}: {customized_activities}",
                "objective_id": goal['id'],
                "due_date": due_date,
                "priority": "medium",
                "estimated_hours": 8,
                "status": "ai_suggested",
                "completion_percentage": 0,
                "ai_suggested": True,
                "strategic_metadata": strategic_metadata
            }
            
            task_result = supabase.table("action_plans").insert(task_record).execute()
            if task_result.data:
                created_tasks.append(task_result.data[0])
        
        # Update AI meta
        if ai_meta_id:
            supabase.table("ai_meta").update({
                "output_json": {
                    "status": f"{process_name}_completed",
                    "tasks_generated": len(created_tasks),
                    "goal_id": goal['id'],
                    "goal_type": process_name,
                    "process_applied": process_name,
                    "framework_version": process_name,
                    "predefined_process": True,
                    "customization": customization_text
                }
            }).eq("id", ai_meta_id).execute()
        
        processing_time = time.time() - start_time
        return created_tasks, f"Generated {len(created_tasks)} tasks using {process_name} predefined process", processing_time
        
    except Exception as e:
        print(f"❌ Error generating predefined process tasks: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to old method if new one fails
        if process_name == 'order_to_delivery':
            return generate_13_step_fallback_tasks(goal, goal_data, get_updated_standard_process(), ai_meta_id)
        else:
            raise e

def generate_13_step_fallback_tasks(goal, goal_data, standard_process, ai_meta_id):
    """Fallback to generate exactly 13 tasks using predefined process"""
    start_time = time.time()
    supabase = get_supabase_client()
    created_tasks = []
    
    base_date = datetime.now()
    
    for i, (step_key, step_data) in enumerate(standard_process.items()):
        due_date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        
        strategic_metadata = {
            "required_skills": ["Process execution", "Coordination", step_data['responsible']],
            "success_criteria": f"Complete {step_data['activities']} successfully",
            "complexity": "medium",
            "strategic_analysis": {
                "validation_score": "13-step process applied",
                "context": f"Standard delivery process for {goal_data['title']}",
                "objective": goal_data['title'],
                "process": step_data['activities'],
                "delivery": due_date,
                "reporting_requirements": step_data['deliverable'],
                "q4_execution_context": "Q4 2025 execution",
                "process_applied": "UPDATED Order-to-Delivery Standard Framework",
                "goal_type": "delivery"
            },
            "strategic_phase": f"Process Step {i+1}",
            "key_stakeholders": [step_data['responsible']],
            "potential_bottlenecks": ["Timeline constraints", "Coordination requirements"],
            "resource_requirements": ["Standard process tools"],
            "assigned_role": step_data['responsible'],
            "process_step": step_key,
            "information_requirements": "Using standard delivery framework",
            "context": f"Executing {step_key} for {goal_data['title']}",
            "objective": goal_data['title'],
            "process": step_data['activities'],
            "delivery": due_date,
            "reporting_requirements": step_data['deliverable'],
            "goal_type": "delivery",
            "predefined_process": True,  # 🎯 FLAG FOR RAG SYSTEM
            "recommended_role": step_data['responsible']  # 🎯 ALWAYS USE PREDEFINED ROLE
        }
        
        task_record = {
            "task_description": f"{step_key}: {step_data['activities']}",
            "objective_id": goal['id'],
            "due_date": due_date,
            "priority": "medium",
            "estimated_hours": 8,
            "status": "ai_suggested",
            "completion_percentage": 0,
            "ai_suggested": True,
            "strategic_metadata": strategic_metadata
        }
        
        task_result = supabase.table("action_plans").insert(task_record).execute()
        if task_result.data:
            created_tasks.append(task_result.data[0])
    
    # Update AI meta with fallback info
    if ai_meta_id:
        supabase.table("ai_meta").update({
            "output_json": {
                "status": "13_step_fallback_completed",
                "tasks_generated": len(created_tasks),
                "goal_id": goal['id'],
                "goal_type": "delivery",
                "process_applied": "13-step fallback",
                "framework_version": "13-step",
                "fallback_used": True
            }
        }).eq("id", ai_meta_id).execute()
    
    return created_tasks, f"Generated {len(created_tasks)} delivery tasks using 13-step fallback", time.time() - start_time

def process_and_save_tasks(goal, ai_tasks_data, standard_process, ai_meta_id, task_time, task_type):
    """Process and save tasks to database"""
    supabase = get_supabase_client()
    created_tasks = []
    
    # 🎯 GET OBJECTIVE NUMBER FROM GOAL
    objective_number = goal.get('pre_number', 'N/A')
    
    for i, task_data in enumerate(ai_tasks_data):
        if not task_data.get('task_description'):
            print(f"⚠️ Skipping task {i}: No task_description")
            continue
        
        # Get the corresponding standard process step
        process_step_key = list(standard_process.keys())[i]
        process_step_data = standard_process[process_step_key]
        
        # Use AI data with fallbacks
        task_description = task_data.get('task_description', f"{process_step_key}: {process_step_data['activities']}")
        due_date = task_data.get('due_date', (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'))
        priority = task_data.get('priority', 'medium')
        estimated_hours = task_data.get('estimated_hours', 8)
        # 🎯 ALWAYS USE THE EXACT ROLE FROM PREDEFINED PROCESS - DO NOT TRUST AI
        assigned_role = process_step_data['responsible']
        
        strategic_metadata = {
            "required_skills": ["Process execution", "Coordination", assigned_role],
            "success_criteria": f"Complete {process_step_data['activities']} successfully",
            "complexity": "medium",
            "strategic_analysis": {
                "validation_score": "13-step process applied",
                "context": f"Standard delivery process for {goal['title']}",
                "objective": f"{objective_number} - {goal['title']}",  # 🎯 INCLUDE OBJECTIVE NUMBER
                "process": process_step_data['activities'],
                "delivery": due_date,
                "reporting_requirements": process_step_data['deliverable'],
                "q4_execution_context": "Q4 2025 execution",
                "process_applied": "UPDATED Order-to-Delivery Standard Framework",
                "goal_type": "delivery",
                "objective_number": objective_number  # 🎯 ADD THIS
            },
            "strategic_phase": f"Process Step {i+1}",
            "key_stakeholders": [assigned_role],
            "potential_bottlenecks": ["Timeline constraints", "Coordination requirements"],
            "resource_requirements": ["Standard process tools"],
            "assigned_role": assigned_role,
            "process_step": process_step_key,
            "information_requirements": "Using standard delivery framework",
            "context": f"Executing {process_step_key} for objective {objective_number}",  # 🎯 INCLUDE NUMBER
            "objective": f"{objective_number} - {goal['title']}",  # 🎯 INCLUDE NUMBER
            "process": process_step_data['activities'],
            "delivery": due_date,
            "reporting_requirements": process_step_data['deliverable'],
            "goal_type": "delivery",
            "objective_number": objective_number,  # 🎯 INCLUDE NUMBER
            "predefined_process": True,  # 🎯 FLAG FOR RAG SYSTEM
            "recommended_role": assigned_role  # 🎯 ALWAYS USE PREDEFINED ROLE
        }
        
        task_record = {
            "task_description": task_description,
            "objective_id": goal['id'],
            "due_date": due_date,
            "priority": priority,
            "estimated_hours": estimated_hours,
            "status": "ai_suggested",
            "completion_percentage": 0,
            "ai_meta_id": ai_meta_id,
            "ai_suggested": True,
            "strategic_metadata": strategic_metadata
        }
        
        try:
            task_result = supabase.table("action_plans").insert(task_record).execute()
            if task_result.data:
                created_tasks.append(task_result.data[0])
                print(f"✅ Saved task {i+1} for {objective_number}: {task_description[:50]}...")
            else:
                print(f"❌ Failed to save task {i+1} for {objective_number}")
        except Exception as e:
            print(f"❌ Error saving task {i+1} for {objective_number}: {e}")
    
    # Update AI meta with results
    if ai_meta_id:
        try:
            supabase.table("ai_meta").update({
                "output_json": {
                    "status": "13_step_delivery_completed",
                    "tasks_generated": len(created_tasks),
                    "goal_id": goal['id'],
                    "goal_type": "delivery",
                    "process_applied": "13-step delivery",
                    "framework_version": "13-step",
                    "processing_time": task_time,
                    "objective_number": objective_number  # 🎯 INCLUDE NUMBER
                }
            }).eq("id", ai_meta_id).execute()
        except Exception as e:
            print(f"❌ Error updating AI meta: {e}")
    
    return created_tasks, f"Created {len(created_tasks)} {task_type} tasks for {objective_number}", task_time

@task_bp.route('/api/tasks/debug-routes', methods=['GET'])
def debug_routes():
    """Debug endpoint to check all registered routes"""
    from flask import current_app
    routes = []
    for rule in current_app.url_map.iter_rules():
        if 'tasks' in rule.endpoint:
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
    return jsonify({'task_routes': routes})


@task_bp.route('/api/tasks/<task_id>/employee-recommendations', methods=['GET'])  # Changed from POST to GET
@token_required
def get_task_employee_recommendations(task_id):
    """Get employee recommendations for a task"""
    try:
        supabase = get_supabase_client()
        
        # Get task with strategic metadata
        task_result = supabase.table("action_plans").select("strategic_metadata").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = task_result.data[0]
        strategic_metadata = task.get('strategic_metadata', {})
        
        recommendations = strategic_metadata.get('ai_recommendations', [])
        recommendations_available = strategic_metadata.get('employee_recommendations_available', False)
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'recommendations_available': recommendations_available,
            'recommendations_generated_at': strategic_metadata.get('recommendations_generated_at')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/goals', methods=['GET'])
@token_required
def get_company_goals():
    """Get all company goals - FIXED VERSION"""
    try:
        supabase = get_supabase_client()
        
        user_role = g.user.get('role') if hasattr(g, 'user') and g.user else None
        user_employee_id = safe_get_employee_id()
        
        print(f"🎯 Fetching goals - Role: {user_role}, Employee ID: {user_employee_id}")
        
        if user_role == 'employee':
            # Employee sees only goals with tasks assigned to them
            if user_employee_id:
                # Get goals that have tasks assigned to this employee
                tasks_result = supabase.table("action_plans").select("objective_id").eq("assigned_to", user_employee_id).execute()
                goal_ids = list(set([task['objective_id'] for task in tasks_result.data])) if tasks_result.data else []
                
                if goal_ids:
                    result = supabase.table("objectives").select("*").in_("id", goal_ids).execute()
                    goals = result.data if result.data else []
                else:
                    goals = []
            else:
                return jsonify({'success': False, 'error': 'Employee ID not found'}), 400
        else:
            # Admin sees all goals
            result = supabase.table("objectives").select("*").order("created_at", desc=True).execute()
            goals = result.data if result.data else []
        
        print(f"📥 Found {len(goals)} goals")
        return jsonify({'success': True, 'goals': goals})
            
    except Exception as e:
        print(f"❌ Error getting goals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@task_bp.route('/api/tasks/goals/<goal_id>', methods=['GET'])
@token_required
def get_goal_detail(goal_id):
    """Get specific goal with all tasks - FIXED VERSION"""
    try:
        supabase = get_supabase_client()
        
        # Get goal
        goal_result = supabase.table("objectives").select("*").eq("id", goal_id).execute()
        if not goal_result.data:
            return jsonify({'success': False, 'error': 'Goal not found'}), 404
        
        goal = goal_result.data[0]
        
        # Get tasks with employee information
        tasks_result = supabase.table("action_plans").select("*, employees!assigned_to(name, email, role, department)").eq("objective_id", goal_id).execute()
        
        goal['tasks'] = tasks_result.data if tasks_result.data else []
        
        return jsonify({'success': True, 'goal': goal})
            
    except Exception as e:
        print(f"❌ Error getting goal detail: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/goals/<goal_id>/tasks', methods=['GET'])
@token_required
def get_goal_tasks(goal_id):
    """Get all tasks for a specific goal - FIXED VERSION"""
    try:
        supabase = get_supabase_client()
        
        # Get tasks with employee information
        result = supabase.table("action_plans").select("*, employees!assigned_to(name, email, department, role)").eq("objective_id", goal_id).execute()
        
        tasks = result.data if result.data else []
        print(f"📋 Found {len(tasks)} tasks for goal {goal_id}")
        
        return jsonify({'success': True, 'tasks': tasks})
            
    except Exception as e:
        print(f"❌ Error getting goal tasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_or_create_general_tasks_objective_id():
    """
    Deprecated: previously used to force every task to belong to a
    "General Tasks" objective. We now allow tasks to exist without an
    objective at all, so callers should NOT rely on this.
    """
    return None

@task_bp.route('/api/tasks', methods=['POST'])
@token_required
def create_task():
    """Create a new task (Admin) or propose a task (Employee)"""
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        
        user_role = g.user.get('role') if hasattr(g, 'user') and g.user else None
        user_employee_id = safe_get_employee_id()
        
        if not user_role:
            return jsonify({'success': False, 'error': 'User role not found'}), 401
        
        # Validate and sanitize UUID fields
        objective_id = safe_uuid(data.get('objective_id'))
        
        assigned_to = safe_uuid(data.get('assigned_to'))
        
        # Handle multiple assignees if provided
        assigned_to_multiple = []
        if data.get('assigned_to_multiple'):
            assigned_to_multiple = [safe_uuid(uid) for uid in data.get('assigned_to_multiple', []) if safe_uuid(uid)]
        
        # Handle both 'task_description' and 'description' fields
        task_description = data.get('task_description') or data.get('description', '')
        if not task_description:
            return jsonify({'success': False, 'error': 'Task description is required'}), 400
        
        # Build base task payload; we will only set objective_id if one is provided.
        task_data = {
            "task_description": task_description,
            "assigned_to": assigned_to,
            "assigned_to_multiple": assigned_to_multiple,
            "priority": data.get('priority', 'medium'),
            "due_date": data.get('due_date'),
            "estimated_hours": data.get('estimated_hours', 8),
            "dependencies": data.get('dependencies', []),
            "completion_percentage": data.get('completion_percentage', 0),
            "notes": data.get('notes', '')
        }

        # If the client provided a valid objective_id, attach it; otherwise leave it NULL
        if objective_id:
            task_data["objective_id"] = objective_id
        
        # If employee is creating, it's a proposal
        if user_role == 'employee':
            task_data['status'] = 'not_started'
            task_data['ai_suggested'] = False
            # Employees can only assign to themselves
            task_data['assigned_to'] = user_employee_id
            if user_employee_id not in task_data['assigned_to_multiple']:
                task_data['assigned_to_multiple'] = [user_employee_id]
        else:
            task_data['status'] = 'not_started'
            task_data['ai_suggested'] = False
        
        result = supabase.table("action_plans").insert(task_data).execute()
        
        if result.data:
            # Create notification if assigned to someone
            if task_data['assigned_to']:
                notification_message = f"New task assigned: {task_description[:100]}..."
                create_enhanced_task_notification(
                    result.data[0]['id'],
                    "task_assigned",
                    notification_message,
                    assigned_by=g.user.get('name', 'Admin')
                )
            
            return jsonify({'success': True, 'task': result.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Failed to create task'}), 500
            
    except Exception as e:
        print(f"❌ Error creating task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/<task_id>', methods=['PUT'])
@token_required
def update_task(task_id):
    """Update task - different permissions for admin vs employee - SEPARATE PROGRESS NOTIFICATIONS"""
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        
        user_role = g.user.get('role') if hasattr(g, 'user') and g.user else None
        user_employee_id = safe_get_employee_id()
        
        # Get current task
        task_result = supabase.table("action_plans").select("*").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        current_task = task_result.data[0]
        old_progress = current_task.get('completion_percentage', 0)  # Store old progress
        
        # Permission checks
        if user_role == 'employee':
            # Employees can only update their own tasks
            if (current_task['assigned_to'] != user_employee_id and 
                user_employee_id not in (current_task.get('assigned_to_multiple') or [])):
                return jsonify({'success': False, 'error': 'Not authorized to update this task'}), 403
            
            # Employees can only update progress and notes
            allowed_fields = ['completion_percentage', 'notes', 'status']
            update_data = {k: v for k, v in data.items() if k in allowed_fields}
            
            # Auto-update status based on progress
            if 'completion_percentage' in update_data:
                progress = update_data['completion_percentage']
                if progress == 100:
                    update_data['status'] = 'completed'
                elif progress > 0:
                    update_data['status'] = 'in_progress'
        else:
            # Admins can update most fields including task_description
            allowed_fields = [
                'task_description', 'assigned_to', 'assigned_to_multiple', 
                'priority', 'due_date', 'status', 'completion_percentage', 
                'dependencies', 'estimated_hours', 'notes', 'strategic_metadata'
            ]
            update_data = {k: v for k, v in data.items() if k in allowed_fields}
            
            # Sanitize UUID fields for admin updates
            if 'assigned_to' in update_data:
                update_data['assigned_to'] = safe_uuid(update_data['assigned_to'])
            if 'assigned_to_multiple' in update_data:
                # Get current assignments to check for duplicates
                current_assigned_to = current_task.get('assigned_to')
                current_assigned_multiple = current_task.get('assigned_to_multiple') or []
                
                # Remove duplicates and None values
                assigned_list = [safe_uuid(uid) for uid in update_data['assigned_to_multiple'] if safe_uuid(uid)]
                
                # Check for duplicates with existing assignments
                all_current_assignees = set()
                if current_assigned_to:
                    all_current_assignees.add(current_assigned_to)
                all_current_assignees.update(current_assigned_multiple)
                
                # Remove duplicates while preserving order and checking against existing assignments
                seen = set()
                unique_list = []
                for uid in assigned_list:
                    if uid and uid not in seen:
                        # Check if this employee is already assigned (either as primary or in multiple)
                        if uid in all_current_assignees:
                            continue  # Skip if already assigned
                        seen.add(uid)
                        unique_list.append(uid)
                
                update_data['assigned_to_multiple'] = unique_list
                
                # If assigned_to is in the multiple list, ensure it's not duplicated
                if update_data.get('assigned_to') and update_data['assigned_to'] in unique_list:
                    # Keep assigned_to as primary, but don't duplicate in multiple
                    pass
                elif update_data.get('assigned_to') and update_data['assigned_to'] not in unique_list:
                    # Add assigned_to to multiple if not already there and not already assigned
                    if update_data['assigned_to'] not in all_current_assignees:
                        unique_list.insert(0, update_data['assigned_to'])
                        update_data['assigned_to_multiple'] = unique_list
            
            # Handle dependencies - if task has dependencies, set status to 'waiting'
            if 'dependencies' in update_data and update_data['dependencies']:
                update_data['status'] = 'waiting'
        
        if not update_data:
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
        
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        result = supabase.table("action_plans").update(update_data).eq("id", task_id).execute()
        
        if result.data:
            # If task was completed, check dependent tasks
            if update_data.get('status') == 'completed':
                # Find all tasks that have this task as a dependency
                dependent_tasks_result = supabase.table("action_plans").select("id").contains("dependencies", [task_id]).execute()
                if dependent_tasks_result.data:
                    for dependent_task in dependent_tasks_result.data:
                        update_task_status_based_on_dependencies(dependent_task['id'], supabase)
            
            # Create task update history
            update_history = {
                "task_id": task_id,
                "updated_by": user_employee_id,
                "progress": update_data.get('completion_percentage', current_task.get('completion_percentage', 0)),
                "notes": update_data.get('notes', ''),
            }
            supabase.table("task_updates").insert(update_history).execute()
            
            # ========== SEPARATE PROGRESS NOTIFICATION ==========
            new_progress = update_data.get('completion_percentage')
            if new_progress is not None and new_progress != old_progress:
                # Get current user's name for progress notification
                current_user_name = "Unknown"
                if hasattr(g, 'user') and g.user:
                    if user_employee_id:
                        employee_result = supabase.table("employees").select("name").eq("id", user_employee_id).execute()
                        if employee_result.data:
                            current_user_name = employee_result.data[0].get('name', 'Unknown')
                    else:
                        current_user_name = g.user.get('name', 'Unknown')
                
                create_enhanced_task_notification(
                    task_id=task_id,
                    notification_type="progress_updated",
                    message=f"Progress updated on task: {current_task['task_description'][:50]}...",
                    assigned_by=current_user_name if user_role in ['admin', 'superadmin'] else None,
                    old_progress=old_progress,
                    new_progress=new_progress
                )
                print(f"📊 Progress-only notification: {user_role} updated progress from {old_progress}% to {new_progress}%")
            
            # ========== OTHER NOTIFICATION TYPES ==========
            current_user_name = "Unknown"
            if hasattr(g, 'user') and g.user:
                if user_employee_id:
                    employee_result = supabase.table("employees").select("name").eq("id", user_employee_id).execute()
                    if employee_result.data:
                        current_user_name = employee_result.data[0].get('name', 'Unknown')
                else:
                    current_user_name = g.user.get('name', 'Unknown')
            
            # Create notification for status changes (separate from progress)
            if 'status' in update_data:
                old_status = current_task.get('status', 'not_started')
                new_status = update_data['status']
                
                if old_status != new_status:
                    notification_type = "task_status_changed"
                    status_display = new_status.replace('_', ' ').title()
                    message = f"🔄 Status changed to {status_display}: {current_task['task_description'][:50]}..."
                    
                    create_enhanced_task_notification(
                        task_id=task_id,
                        notification_type=notification_type,
                        message=message,
                        assigned_by=current_user_name if user_role in ['admin', 'superadmin'] else None
                    )
                    
                    print(f"🔄 Status notification: {user_role} changed status from {old_status} to {new_status}")
            
            # Create notification for assignment changes
            if 'assigned_to' in update_data or 'assigned_to_multiple' in update_data:
                notification_type = "task_assigned"
                
                # Get old and new assignees for comparison
                old_assignees = set()
                if current_task.get('assigned_to'):
                    old_assignees.add(current_task['assigned_to'])
                if current_task.get('assigned_to_multiple'):
                    old_assignees.update(current_task['assigned_to_multiple'])
                
                new_assignees = set()
                if update_data.get('assigned_to'):
                    new_assignees.add(update_data['assigned_to'])
                if update_data.get('assigned_to_multiple'):
                    new_assignees.update(update_data['assigned_to_multiple'])
                
                # Only notify if assignment actually changed
                if old_assignees != new_assignees:
                    message = f"🎯 Task assignment updated: {current_task['task_description'][:50]}..."
                    
                    create_enhanced_task_notification(
                        task_id=task_id,
                        notification_type=notification_type,
                        message=message,
                        assigned_by=current_user_name if user_role in ['admin', 'superadmin'] else None
                    )
                    
                    print(f"🎯 Assignment notification: {user_role} updated task assignment")
            
            # Create notification for other significant changes
            other_significant_changes = ['task_description', 'due_date', 'priority', 'estimated_hours']
            if any(field in update_data for field in other_significant_changes):
                notification_type = "task_updated"
                
                # Create descriptive message based on what changed
                change_messages = []
                if 'task_description' in update_data:
                    change_messages.append("description updated")
                if 'due_date' in update_data:
                    change_messages.append("due date changed")
                if 'priority' in update_data:
                    change_messages.append("priority changed")
                if 'estimated_hours' in update_data:
                    change_messages.append("estimated hours updated")
                
                change_summary = ", ".join(change_messages)
                message = f"✏️ Task updated ({change_summary}): {current_task['task_description'][:50]}..."
                
                create_enhanced_task_notification(
                    task_id=task_id,
                    notification_type=notification_type,
                    message=message,
                    assigned_by=current_user_name if user_role in ['admin', 'superadmin'] else None
                )
                
                print(f"✏️ Task update notification: {user_role} made changes - {change_summary}")
            
            return jsonify({'success': True, 'task': result.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Failed to update task'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
# Add this to your backend task_routes.py

@task_bp.route('/api/tasks/filter-by-objective', methods=['GET'])
@token_required
def get_tasks_filtered_by_objective():
    """Get tasks filtered by objective - FIXED TO INCLUDE OBJECTIVE PRIORITY"""
    try:
        supabase = get_supabase_client()
        
        objective_id = request.args.get('objective_id')
        priority_filter = request.args.get('priority')
        created_date = request.args.get('created_date')
        user_role = g.user.get('role')
        user_employee_id = safe_get_employee_id()
        
        # Build the query with objective data - FIXED: Include priority field
        query = supabase.table("action_plans").select(
            "*, employees!assigned_to(name, email, department, role), objectives(title, description, pre_number, priority, created_at)"
        )
        
        # Apply objective filter if provided
        if objective_id and objective_id != 'all':
            query = query.eq("objective_id", objective_id)
        
        # Apply objective priority filter if provided
        if priority_filter and priority_filter != 'All':
            if priority_filter == "No Objective":
                # Filter tasks that have no objective
                query = query.is_("objective_id", "null")
            else:
                # Filter by objective priority
                query = query.eq("objectives.priority", priority_filter)
        
        # Apply creation date filter if provided
        if created_date:
            # Filter tasks created on this specific date
            query = query.eq("created_at", created_date)
        
        # Role-based filtering
        if user_role == 'employee':
            if user_employee_id:
                query = query.or_(f"assigned_to.eq.{user_employee_id},assigned_to_multiple.cs.{{{user_employee_id}}}")
            else:
                return jsonify({'success': False, 'error': 'Employee ID not found'}), 400
        
        result = query.order("created_at", desc=True).execute()
        
        tasks = result.data if result.data else []
        return jsonify({'success': True, 'tasks': tasks})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/dashboard', methods=['GET'])
@token_required
def get_task_dashboard():
    """Get task dashboard data with objective filtering - FIXED TO INCLUDE OBJECTIVE PRIORITY"""
    try:
        supabase = get_supabase_client()
        
        user_role = g.user.get('role')
        user_employee_id = safe_get_employee_id()
        objective_id = request.args.get('objective_id')
        
        if user_role in ['admin', 'superadmin']:
            # FIXED: Include priority in the select
            query = supabase.table("action_plans").select(
                "*, employees!assigned_to(name, email, department, role), objectives(title, description, pre_number, priority)"
            )
            
            # Apply objective filter for admin
            if objective_id and objective_id != 'all':
                query = query.eq("objective_id", objective_id)
                
            tasks_result = query.execute()
        else:
            # Employee view with objective filtering
            if user_employee_id:
                employee_id_str = str(user_employee_id)
                # FIXED: Include priority in the select
                query = supabase.table("action_plans").select(
                    "*, employees!assigned_to(name, email, department, role), objectives(title, description, pre_number, priority)"
                ).or_(f"assigned_to.eq.{employee_id_str},assigned_to_multiple.cs.{{{employee_id_str}}}")
                
                # Apply objective filter for employee
                if objective_id and objective_id != 'all':
                    query = query.eq("objective_id", objective_id)
                    
                tasks_result = query.execute()
            else:
                return jsonify({'success': False, 'error': 'Employee ID not found'}), 400
        
        tasks = tasks_result.data if tasks_result.data else []
        
        # Calculate statistics
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get('status') == 'completed'])
        pending_tasks = len([t for t in tasks if t.get('status') == 'not_started'])
        in_progress_tasks = len([t for t in tasks if t.get('status') == 'in_progress'])
        
        today = datetime.utcnow().date()
        overdue_tasks = len([t for t in tasks if t.get('due_date') and 
                           datetime.fromisoformat(t['due_date'].replace('Z', '')).date() < today and 
                           t.get('status') != 'completed'])
        
        return jsonify({
            'success': True,
            'stats': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks,
                'in_progress_tasks': in_progress_tasks,
                'overdue_tasks': overdue_tasks
            },
            'tasks': tasks
        })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/employee/<employee_id>', methods=['GET'])
@token_required
def get_employee_tasks(employee_id):
    """Get tasks assigned to specific employee"""
    try:
        supabase = get_supabase_client()
        
        user_role = g.user.get('role')
        user_employee_id = g.user.get('employee_id')
        
        # Permission check
        if user_role == 'employee' and user_employee_id != employee_id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403
        
        # Get tasks where employee is either primary assignee or in multiple assignees
        result = supabase.table("action_plans").select("*, objectives(title, deadline)").or_(f"assigned_to.eq.{employee_id},assigned_to_multiple.cs.{{{employee_id}}}").order("due_date").execute()
        
        if result.data:
            return jsonify({'success': True, 'tasks': result.data})
        else:
            return jsonify({'success': True, 'tasks': []})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/collaboration', methods=['GET'])
@token_required
def get_collaboration_tasks():
    """Get tasks where user is attached (mentioned in notes) but not assigned"""
    try:
        supabase = get_supabase_client()
        user_employee_id = safe_get_employee_id()
        
        if not user_employee_id:
            return jsonify({'success': False, 'error': 'Employee ID not found'}), 400
        
        employee_id_str = str(user_employee_id)
        
        # Get all task updates where this employee is attached
        updates_result = supabase.table("task_updates").select("task_id, attached_to, attached_to_multiple").execute()
        
        # Collect unique task IDs where user is attached
        collaboration_task_ids = set()
        for update in (updates_result.data or []):
            task_id = update.get('task_id')
            if not task_id:
                continue
                
            # Check if user is in attached_to
            attached_to = update.get('attached_to')
            if attached_to and str(attached_to) == employee_id_str:
                collaboration_task_ids.add(task_id)
                continue
            
            # Check if user is in attached_to_multiple
            attached_multiple = update.get('attached_to_multiple') or []
            if isinstance(attached_multiple, list):
                attached_multiple_str = [str(id) for id in attached_multiple]
                if employee_id_str in attached_multiple_str:
                    collaboration_task_ids.add(task_id)
        
        # Also check notifications for attached employees
        notifications_result = supabase.table("notifications").select("meta").eq("to_employee", employee_id_str).execute()
        
        for notification in (notifications_result.data or []):
            meta_raw = notification.get('meta')
            if isinstance(meta_raw, str):
                try:
                    import json
                    meta = json.loads(meta_raw)
                except:
                    meta = {}
            else:
                meta = meta_raw or {}
            
            # Check if this notification was specifically attached
            if meta.get('specially_attached'):
                task_id = meta.get('task_id')
                if task_id:
                    collaboration_task_ids.add(task_id)
        
        # Get all tasks where user is assigned (to exclude them)
        assigned_tasks_result = supabase.table("action_plans").select("id").or_(
            f"assigned_to.eq.{employee_id_str},assigned_to_multiple.cs.{{{employee_id_str}}}"
        ).execute()
        
        assigned_task_ids = {task['id'] for task in (assigned_tasks_result.data or [])}
        
        # Filter out tasks that are already assigned to user
        collaboration_task_ids = collaboration_task_ids - assigned_task_ids
        
        if not collaboration_task_ids:
            return jsonify({'success': True, 'tasks': []})
        
        # Get full task details for collaboration tasks
        task_ids_list = list(collaboration_task_ids)
        tasks_result = supabase.table("action_plans").select(
            "*, employees!assigned_to(name, email, department, role), objectives(title, description, pre_number, priority)"
        ).in_("id", task_ids_list).order("created_at", desc=True).execute()
        
        tasks = tasks_result.data if tasks_result.data else []
        
        return jsonify({'success': True, 'tasks': tasks})
        
    except Exception as e:
        print(f"❌ Error getting collaboration tasks: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/<task_id>/updates', methods=['GET'])
@token_required
def get_task_updates(task_id):
    """Get update history for a task"""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("task_updates").select("*, employees(name, role)").eq("task_id", task_id).order("created_at", desc=True).execute()
        
        if result.data:
            return jsonify({'success': True, 'updates': result.data})
        else:
            return jsonify({'success': True, 'updates': []})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/<task_id>/updates', methods=['POST'])
@token_required
def add_task_update(task_id):
    """Add an update to a task - allows attached users to collaborate"""
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        
        user_employee_id = safe_get_employee_id()
        user_role = g.user.get('role')
        
        # Get task to check permissions
        task_result = supabase.table("action_plans").select("*").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = task_result.data[0]
        
        # Permission check - employees can add notes if assigned OR explicitly attached
        if user_role == 'employee':
            has_access = employee_has_collaboration_access(task_id, task, user_employee_id, supabase)
            if not has_access:
                return jsonify({'success': False, 'error': 'Not authorized to add notes to this task'}), 403
        
        update_data = {
            "task_id": task_id,
            "updated_by": user_employee_id,
            "progress": data.get('progress'),
            "notes": data.get('notes', ''),
            "attachments": data.get('attachments', [])
        }
        
        result = supabase.table("task_updates").insert(update_data).execute()
        
        if result.data:
            # Update the main task's completion percentage if progress is provided
            if data.get('progress') is not None:
                task_update = {
                    "completion_percentage": data.get('progress'),
                    "updated_at": datetime.utcnow().isoformat()
                }
                # Auto-update status based on progress
                if data.get('progress') == 100:
                    task_update['status'] = 'completed'
                elif data.get('progress') > 0:
                    task_update['status'] = 'in_progress'
                
                supabase.table("action_plans").update(task_update).eq("id", task_id).execute()
            
            return jsonify({'success': True, 'update': result.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Failed to add task update'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def create_file_upload_notification(task_id, file_name, uploaded_by_name):
    """Create a simple notification specifically for file uploads"""
    try:
        supabase = get_supabase_client()
        
        # Get task details
        task_result = supabase.table("action_plans").select("task_description, assigned_to, assigned_to_multiple").eq("id", task_id).execute()
        if not task_result.data:
            return
        
        task = task_result.data[0]
        
        # Get admin employee ID
        admin_employee_id = get_admin_employee_id()
        
        # Determine recipients - notify task assignees and admin
        recipients = set()
        if task.get('assigned_to'):
            recipients.add(task['assigned_to'])
        if task.get('assigned_to_multiple'):
            recipients.update(task['assigned_to_multiple'])
        
        # Always notify admin for file uploads
        if admin_employee_id:
            recipients.add(admin_employee_id)
        
        # Create simple notifications
        for recipient in recipients:
            if recipient:
                notification_data = {
                    "to_employee": recipient,
                    "channel": "in_app",
                    "message": f"File '{file_name}' uploaded to task: {task['task_description'][:50]}...",
                    "meta": {
                        "task_id": task_id,
                        "task_description": task['task_description'][:100],
                        "type": "file_uploaded",
                        "uploaded_by": uploaded_by_name,
                        "file_name": file_name,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "priority": "normal",
                    "created_at": datetime.utcnow().isoformat(),
                    "is_read": False
                }
                supabase.table("notifications").insert(notification_data).execute()
                print(f"📎 File upload notification sent to {recipient}")
                
    except Exception as e:
        print(f"⚠️ Failed to create file upload notification: {e}")


@task_bp.route('/api/tasks/<task_id>/upload-file', methods=['POST'])
@token_required
def upload_task_file(task_id):
    """Upload file for task and create task update with attachment"""
    try:
        supabase = get_supabase_client()
        
        # Check if task exists
        task_result = supabase.table("action_plans").select("*").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = task_result.data[0]
        user_employee_id = safe_get_employee_id()
        
        # Permission check - employees can upload if assigned OR explicitly attached
        user_role = g.user.get('role')
        print(f"🔐 Upload file authorization check: user_role={user_role}, employee_id={user_employee_id}, task_id={task_id}")
        
        if user_role == 'employee':
            has_access = employee_has_collaboration_access(task_id, task, user_employee_id, supabase)
            print(f"🔐 Authorization result: {has_access}")
            if not has_access:
                print(f"❌ Access denied for employee {user_employee_id} on task {task_id}")
                return jsonify({'success': False, 'error': 'Not authorized to upload files for this task'}), 403
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Get notes from form data
        notes = request.form.get('notes', '')
        
        # Read file data
        file_data = file.read()
        file_size = len(file_data)
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Upload to Supabase storage
        bucket_name = "task_updates"
        file_path = f"{task_id}/{unique_filename}"
        
        try:
            # Upload file to storage
            storage_response = supabase.storage.from_(bucket_name).upload(
                file_path, 
                file_data,
                file_options={"content-type": file.content_type}
            )
            
            # Get public URL
            public_url_data = supabase.storage.from_(bucket_name).get_public_url(file_path)
            public_url = public_url_data
            
        except Exception as storage_error:
            print(f"❌ Storage upload error: {storage_error}")
            return jsonify({'success': False, 'error': f'File upload failed: {str(storage_error)}'}), 500
        
        # Create attachment record
        attachment_data = {
            "filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "file_type": file.content_type,
            "public_url": public_url,
            "uploaded_by": user_employee_id,
            "uploaded_at": datetime.utcnow().isoformat()
        }
        
        # Create task update with attachment
        update_data = {
            "task_id": task_id,
            "updated_by": user_employee_id,
            "progress": task.get('completion_percentage', 0),
            "notes": notes,
            "attachments": [attachment_data]
        }
        
        # Insert task update
        update_result = supabase.table("task_updates").insert(update_data).execute()
        
        if not update_result.data:
            return jsonify({'success': False, 'error': 'Failed to create task update'}), 500

        # ========== UPDATED NOTIFICATION FLOW ==========
        if update_result.data:
            # Get current user's name for notification
            current_user_name = "Unknown"
            if user_employee_id:
                employee_result = supabase.table("employees").select("name").eq("id", user_employee_id).execute()
                if employee_result.data:
                    current_user_name = employee_result.data[0].get('name', 'Unknown')
            else:
                current_user_name = g.user.get('name', 'Unknown')
            
            # Prepare notification message
            file_name = os.path.basename(file.filename)
            message = f"📎 File '{file_name}' uploaded to task: {task['task_description'][:50]}..."
            
            # Use the updated notification system
            create_enhanced_task_notification(
                task_id=task_id,
                notification_type="file_uploaded",
                message=message,
                assigned_by=current_user_name if user_role in ['admin', 'superadmin'] else None,
                note_preview=notes if notes else None
            )
            
            print(f"✅ File upload notification sent for '{file_name}' by {current_user_name} ({user_role})")
        # ========== END UPDATED NOTIFICATION FLOW ==========
        
        return jsonify({
            'success': True, 
            'message': 'File uploaded successfully',
            'attachment': attachment_data,
            'update': update_result.data[0]
        })
        
    except Exception as e:
        print(f"❌ File upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/<task_id>', methods=['GET'])
@token_required
def get_task(task_id):
    """Get specific task details - FIXED VERSION"""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("action_plans").select("*, employees!assigned_to(name, email, department, role), objectives(title, description, pre_number, priority)").eq("id", task_id).execute()
        
        if result.data:
            return jsonify({'success': True, 'task': result.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
            
    except Exception as e:
        print(f"❌ Error getting task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    

@task_bp.route('/api/tasks/<task_id>/attachments', methods=['GET'])
@token_required
def get_task_attachments(task_id):
    """Get all attachments for a task - FIXED VERSION"""
    try:
        supabase = get_supabase_client()
        
        # Check if task exists
        task_result = supabase.table("action_plans").select("*").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found', 'attachments': [], 'total': 0}), 404
        
        # Get all task updates that have attachments
        updates_result = supabase.table("task_updates").select(
            "id, attachments, created_at, updated_by, employees(name)"
        ).eq("task_id", task_id).execute()
        
        attachments = []
        if updates_result.data:
            for update in updates_result.data:
                if update.get('attachments') and isinstance(update['attachments'], list):
                    for attachment in update['attachments']:
                        if isinstance(attachment, dict):
                            # Add update context to each attachment
                            attachment_with_context = attachment.copy()
                            attachment_with_context['update_id'] = update['id']
                            attachment_with_context['created_at'] = update['created_at']
                            attachment_with_context['updated_by'] = update['updated_by']
                            attachment_with_context['employee_name'] = update.get('employees', {}).get('name', 'Unknown')
                            attachments.append(attachment_with_context)
        
        # Sort by creation date, newest first
        attachments.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'attachments': attachments,
            'total': len(attachments)
        })
        
    except Exception as e:
        print(f"❌ Error getting task attachments: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': str(e),
            'attachments': [],
            'total': 0
        }), 500

@task_bp.route('/api/tasks/<task_id>/add-note', methods=['POST'])
@token_required
def add_task_note(task_id):
    """Add a note to a task without file upload, with employee attachment feature - SEPARATE NOTIFICATIONS"""
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        
        # Check if task exists
        task_result = supabase.table("action_plans").select("*").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = task_result.data[0]
        user_employee_id = safe_get_employee_id()
        user_role = g.user.get('role')
        
        print(f"🔐 Add note authorization check: user_role={user_role}, employee_id={user_employee_id}, task_id={task_id}")
        
        # Permission check - allow employees who are assigned OR were explicitly attached
        if user_role == 'employee':
            has_access = employee_has_collaboration_access(task_id, task, user_employee_id, supabase)
            print(f"🔐 Authorization result: {has_access}")
            if not has_access:
                print(f"❌ Access denied for employee {user_employee_id} on task {task_id}")
                return jsonify({'success': False, 'error': 'Not authorized to update this task'}), 403
        
        notes = data.get('notes', '')
        progress = data.get('progress', task.get('completion_percentage', 0))
        old_progress = task.get('completion_percentage', 0)  # Store old progress
        
        if not notes.strip():
            return jsonify({'success': False, 'error': 'Note content is required'}), 400
        
        # Allow attaching any employee without restrictions
        attached_to = safe_uuid(data.get('attached_to'))
        attached_to_multiple = []
        if data.get('attached_to_multiple'):
            attached_to_multiple = [safe_uuid(uid) for uid in data.get('attached_to_multiple', []) if safe_uuid(uid)]
        
        # Remove validation restrictions - allow attaching any active employee
        if attached_to or attached_to_multiple:
            all_attached_employees = []
            if attached_to:
                all_attached_employees.append(attached_to)
            if attached_to_multiple:
                all_attached_employees.extend(attached_to_multiple)
            
            # Remove duplicates
            all_attached_employees = list(set(all_attached_employees))
            
            # Simply verify employees exist and are active (no permission restrictions)
            employees_result = supabase.table("employees").select("id, name").in_("id", all_attached_employees).eq("is_active", True).execute()
            valid_employee_ids = [emp['id'] for emp in employees_result.data] if employees_result.data else []
            
            # Filter out invalid employees but don't restrict based on role or task assignment
            if attached_to and attached_to not in valid_employee_ids:
                attached_to = None
            attached_to_multiple = [emp_id for emp_id in attached_to_multiple if emp_id in valid_employee_ids]
        
        # Create task update
        update_data = {
            "task_id": task_id,
            "updated_by": user_employee_id,
            "progress": progress,
            "notes": notes.strip(),
            "attachments": [],
            "attached_to": attached_to,
            "attached_to_multiple": attached_to_multiple
        }
        
        # Insert task update
        update_result = supabase.table("task_updates").insert(update_data).execute()
        
        if not update_result.data:
            return jsonify({'success': False, 'error': 'Failed to add note'}), 500
        
        # Resolve current user's display name once for notifications
        current_user_name = "Unknown"
        if hasattr(g, 'user') and g.user:
            if user_employee_id:
                employee_result = supabase.table("employees").select("name").eq("id", user_employee_id).execute()
                if employee_result.data:
                    current_user_name = employee_result.data[0].get('name', 'Unknown')
            else:
                current_user_name = g.user.get('name', 'Unknown')
        
        # Update task progress if different - SEPARATE NOTIFICATION FOR PROGRESS
        if progress != old_progress:
            task_update = {
                "completion_percentage": progress,
                "updated_at": datetime.utcnow().isoformat()
            }
            # Auto-update status based on progress
            if progress == 100:
                task_update['status'] = 'completed'
            elif progress > 0:
                task_update['status'] = 'in_progress'
            
            supabase.table("action_plans").update(task_update).eq("id", task_id).execute()
            
            # ========== SEPARATE PROGRESS NOTIFICATION ==========
            create_enhanced_task_notification(
                task_id,
                "progress_updated",
                f"Progress updated on task: {task['task_description'][:50]}...",
                assigned_by=current_user_name if user_role in ['admin', 'superadmin'] else None,
                old_progress=old_progress,
                new_progress=progress
            )
            print(f"📊 Separate progress notification sent: {old_progress}% → {progress}%")

        # ========== SEPARATE NOTE NOTIFICATION ==========
        # Create separate note notification
        create_enhanced_task_notification(
            task_id,
            "note_added",
            f"Note added to task: {task['task_description'][:50]}...",
            assigned_by=current_user_name if user_role in ['admin', 'superadmin'] else None,
            note_preview=notes[:100] + '...' if len(notes) > 100 else notes,
            attached_to=attached_to,
            attached_to_multiple=attached_to_multiple
        )
        
        print(f"💬 Separate note notification sent by {current_user_name} ({user_role})")
        
        return jsonify({
            'success': True, 
            'message': 'Note added successfully',
            'update': update_result.data[0],
            'attached_to': attached_to,
            'attached_to_multiple': attached_to_multiple
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/<task_id>/notes', methods=['GET'])
@token_required
def get_task_notes(task_id):
    """Get all notes for a task - FIXED VERSION"""
    try:
        supabase = get_supabase_client()
        
        # Check if task exists
        task_result = supabase.table("action_plans").select("*").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found', 'notes': [], 'total': 0}), 404
        
        # Get all task updates (notes) with employee information
        updates_result = supabase.table("task_updates").select(
            "*, employees!updated_by(name, role, department)"
        ).eq("task_id", task_id).order("created_at", desc=True).execute()
        
        notes = []
        if updates_result.data:
            for update in updates_result.data:
                # FIX: Safely handle the employees relationship which might be None
                employees_data = update.get('employees') or {}
                
                note_data = {
                    'id': update['id'],
                    'notes': update.get('notes', ''),
                    'progress': update.get('progress', 0),
                    'created_at': update.get('created_at'),
                    'updated_by': update.get('updated_by'),
                    'employee_name': employees_data.get('name', 'Unknown'),  # FIXED: Use safe access
                    'employee_role': employees_data.get('role', 'N/A'),      # FIXED: Use safe access
                    'has_attachments': bool(update.get('attachments')) and len(update.get('attachments', [])) > 0,
                    'attachments_count': len(update.get('attachments', [])),
                    'attachments': update.get('attachments', [])
                }
                
                # Add employee attachment information if available
                if update.get('attached_to') or update.get('attached_to_multiple'):
                    note_data['is_attached_to_me'] = False
                    note_data['attached_to'] = update.get('attached_to')
                    note_data['attached_to_multiple'] = update.get('attached_to_multiple', [])
                    
                    # Get current user's employee ID
                    user_employee_id = safe_get_employee_id()
                    if user_employee_id:
                        # Check if this note was specifically attached to current user
                        if (update.get('attached_to') == user_employee_id or 
                            user_employee_id in (update.get('attached_to_multiple') or [])):
                            note_data['is_attached_to_me'] = True
                
                notes.append(note_data)
        
        return jsonify({
            'success': True,
            'notes': notes,
            'total': len(notes)
        })
        
    except Exception as e:
        print(f"❌ Error getting task notes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': str(e),
            'notes': [],
            'total': 0
        }), 500
    
      
@task_bp.route('/api/tasks/<task_id>/available-employees', methods=['GET'])
@token_required
def get_available_employees_for_attachment(task_id):
    """Get list of ALL employees that can be attached to notes for this task - IMPROVED VERSION"""
    try:
        supabase = get_supabase_client()
        
        # Check if task exists
        task_result = supabase.table("action_plans").select("assigned_to, assigned_to_multiple").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        # IMPROVEMENT: Get ALL active employees without restrictions
        employees_result = supabase.table("employees").select("id, name, role, department, email").eq("is_active", True).execute()
        employees = employees_result.data if employees_result.data else []
        
        return jsonify({
            'success': True,
            'employees': employees,
            'total': len(employees)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@task_bp.route('/api/tasks/<task_id>/updates/<update_id>/attachment/<attachment_index>', methods=['DELETE'])
@token_required
def delete_task_attachment(task_id, update_id, attachment_index):
    """Delete a specific attachment from a task update"""
    try:
        supabase = get_supabase_client()
        user_role = g.user.get('role')
        
        # Only admin can delete attachments
        if user_role not in ['admin', 'superadmin']:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403
        
        # Get the task update
        update_result = supabase.table("task_updates").select("*").eq("id", update_id).eq("task_id", task_id).execute()
        if not update_result.data:
            return jsonify({'success': False, 'error': 'Update not found'}), 404
        
        update = update_result.data[0]
        attachments = update.get('attachments', [])
        
        try:
            attachment_index = int(attachment_index)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid attachment index'}), 400
        
        if attachment_index < 0 or attachment_index >= len(attachments):
            return jsonify({'success': False, 'error': 'Attachment index out of range'}), 400
        
        # Get attachment info before removal
        attachment_to_delete = attachments[attachment_index]
        
        # Remove from Supabase storage
        try:
            bucket_name = "task_updates"
            file_path = attachment_to_delete.get('file_path')
            if file_path:
                supabase.storage.from_(bucket_name).remove([file_path])
        except Exception as storage_error:
            print(f"⚠️ Failed to delete file from storage: {storage_error}")
        
        # Remove from attachments array
        attachments.pop(attachment_index)
        
        # Update the task update
        update_data = {
            "attachments": attachments,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        update_result = supabase.table("task_updates").update(update_data).eq("id", update_id).execute()
        
        if update_result.data:
            return jsonify({
                'success': True, 
                'message': 'Attachment deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete attachment'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/tasks/<task_id>/available-dependencies', methods=['GET'])
@token_required
def get_available_dependencies(task_id):
    """Get available tasks that can be set as dependencies"""
    try:
        supabase = get_supabase_client()
        
        # Check if task exists
        task_result = supabase.table("action_plans").select("id").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        available_tasks = get_available_tasks_for_dependencies(task_id, supabase)
        
        return jsonify({
            'success': True,
            'available_dependencies': available_tasks
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/ai-meta/<ai_meta_id>', methods=['GET'])
@token_required
def get_ai_meta_progress(ai_meta_id):
    """Get AI meta progress for real-time updates - FIXED VERSION"""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("ai_meta").select("*").eq("id", ai_meta_id).execute()
        
        if result.data:
            return jsonify({'success': True, 'ai_meta': result.data[0]})
        else:
            return jsonify({'success': False, 'error': 'AI meta not found'}), 404
            
    except Exception as e:
        print(f"❌ Error getting AI meta: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@task_bp.route('/api/objectives/<objective_id>/rag-recommendations-status', methods=['GET'])
@token_required
def get_rag_recommendations_status(objective_id):
    """Get RAG recommendation status for all tasks in an objective"""
    try:
        supabase = get_supabase_client()
        
        # Get all tasks for this objective
        tasks_result = supabase.table("action_plans").select("id, task_description, strategic_metadata").eq("objective_id", objective_id).execute()
        
        if not tasks_result.data:
            return jsonify({
                'success': True,
                'tasks': [],
                'summary': {
                    'total_tasks': 0,
                    'completed': 0,
                    'in_progress': 0,
                    'pending': 0,
                    'failed': 0
                }
            })
        
        tasks = tasks_result.data
        task_ids = [task['id'] for task in tasks]
        
        # Get all AI meta records for RAG recommendations for these tasks
        # Query for both custom tasks and fallback tasks sources, plus manual RAG (when user clicks "Recommend Employee")
        ai_meta_custom = supabase.table("ai_meta").select("*").eq("source", "auto-rag-recommendations-custom-tasks").execute()
        ai_meta_fallback = supabase.table("ai_meta").select("*").eq("source", "auto-rag-recommendations-fallback-tasks").execute()
        ai_meta_manual = supabase.table("ai_meta").select("*").eq("source", "chatgpt-rag-employee-recommendations").execute()
        ai_meta_corrected_rag = supabase.table("ai_meta").select("*").eq("source", "corrected-rag-recommendations").execute()
        
        all_ai_meta = (ai_meta_custom.data or []) + (ai_meta_fallback.data or []) + (ai_meta_manual.data or []) + (ai_meta_corrected_rag.data or [])
        
        # Create a map of task_id -> ai_meta
        ai_meta_map = {}
        for meta in all_ai_meta:
            task_id = meta.get('input_json', {}).get('task_id')
            if task_id and task_id in task_ids:
                ai_meta_map[task_id] = meta
        
        # Build status for each task
        task_statuses = []
        summary = {
            'total_tasks': len(tasks),
            'completed': 0,
            'in_progress': 0,
            'pending': 0,
            'failed': 0
        }
        
        for task in tasks:
            task_id = task['id']
            meta = ai_meta_map.get(task_id)
            strategic_meta = task.get('strategic_metadata', {}) or {}
            has_recommendations = bool(strategic_meta.get('ai_recommendations'))
            
            if has_recommendations:
                status = 'completed'
                summary['completed'] += 1
            elif meta:
                output_json = meta.get('output_json', {})
                meta_status = output_json.get('status', 'unknown')
                progress = output_json.get('progress', 0)
                
                if meta_status == 'completed':
                    status = 'completed'
                    summary['completed'] += 1
                elif meta_status == 'error':
                    status = 'failed'
                    summary['failed'] += 1
                elif meta_status in ['processing', 'starting']:
                    status = 'in_progress'
                    summary['in_progress'] += 1
                else:
                    status = 'pending'
                    summary['pending'] += 1
                
                task_statuses.append({
                    'task_id': task_id,
                    'task_description': task.get('task_description', '')[:50],
                    'status': status,
                    'progress': progress,
                    'current_activity': output_json.get('current_activity', ''),
                    'recommendations_count': len(strategic_meta.get('ai_recommendations', [])),
                    'ai_meta_id': meta.get('id'),
                    'has_recommendations': has_recommendations,
                    'error': output_json.get('error') if meta_status == 'error' else None
                })
            # Skip tasks with no RAG activity - they shouldn't appear in the status
        
        return jsonify({
            'success': True,
            'tasks': task_statuses,
            'summary': summary
        })
        
    except Exception as e:
        print(f"❌ Error getting RAG recommendations status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ========== RAG IMPLEMENTATION FOR EMPLOYEE RECOMMENDATIONS ==========

# ========== SIMPLIFIED RAG IMPLEMENTATION ==========

def extract_text_from_google_drive_url(google_drive_url):
    """Extract text from Google Drive URL - handles job_description_url column"""
    try:
        if not google_drive_url:
            return None
            
        # Convert Google Drive URL to direct download link
        if 'drive.google.com' in google_drive_url:
            if '/file/d/' in google_drive_url:
                file_id = google_drive_url.split('/file/d/')[1].split('/')[0]
                direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            elif '/open?id=' in google_drive_url:
                file_id = google_drive_url.split('/open?id=')[1].split('&')[0]
                direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            else:
                print(f"❌ Unsupported Google Drive URL format: {google_drive_url}")
                return None
        else:
            direct_url = google_drive_url

        # Download the file with timeout and headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(direct_url, timeout=30, headers=headers)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        
        # Handle PDF files
        if 'pdf' in content_type or google_drive_url.lower().endswith('.pdf'):
            return extract_text_from_pdf(response.content)
        
        # Handle DOCX files
        elif 'word' in content_type or 'docx' in content_type or google_drive_url.lower().endswith('.docx'):
            return extract_text_from_docx(response.content)
        
        # Handle text files
        elif 'text' in content_type or google_drive_url.lower().endswith('.txt'):
            return response.text[:10000]  # Limit text length
        
        else:
            # Try to detect file type from content
            if response.content.startswith(b'%PDF'):
                return extract_text_from_pdf(response.content)
            elif response.content.startswith(b'PK'):  # DOCX files start with PK
                return extract_text_from_docx(response.content)
            else:
                # Fallback: return as text with length limit
                return response.text[:5000] if response.text else None
                
    except Exception as e:
        print(f"❌ Error extracting text from Google Drive URL: {e}")
        return None

def extract_text_from_pdf(pdf_content):
    """Extract text from PDF content"""
    try:
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text[:10000]  # Limit text length
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {e}")
        return None

def extract_text_from_docx(docx_content):
    """Extract text from DOCX content"""
    try:
        docx_file = io.BytesIO(docx_content)
        doc = docx.Document(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text[:10000]  # Limit text length
    except Exception as e:
        print(f"❌ Error extracting text from DOCX: {e}")
        return None

def identify_responsible_role_from_process(task_description):
    """
    SIMPLE AND DIRECT role identification - strictly follows the 13-step process
    """
    if not task_description:
        return None
        
    task_lower = task_description.lower()
    
    # DIRECT MAPPING - Exact process step to role
    process_role_mapping = {
        # Lead-to-Delivery Process Steps
        "lead generation": "Account Executive",
        "lead capture": "Account Executive",
        "lead qualification": "Product Development Manager",
        "needs analysis": "Product Development Manager",
        "proposal offering": "Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "commercial proposal": "Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "negotiation": "CEO and Chief Revenue Officer",
        "closing the deal": "Account Executive",
        "signed agreements": "Account Executive",
        
        # Order-to-Delivery Process Steps
        # Step 1 - Account Executive
        "finalize deal": "Account Executive",
        "deal documentation": "Account Executive", 
        "proforma invoice": "Account Executive",
        "commercial agreement": "Account Executive",
        "signed pi": "Account Executive",
        "commercial terms": "Account Executive",
        
        # Step 2 - Supply Chain Specialist
        "supplier stock": "Supply Chain Specialist",
        "stock order": "Supply Chain Specialist",
        "kenya suppliers": "Supply Chain Specialist",
        "stock availability": "Supply Chain Specialist",
        "inventory reservation": "Supply Chain Specialist",
        "order confirmation": "Supply Chain Specialist",
        "final pricing": "Supply Chain Specialist",
        "supplier coordination": "Supply Chain Specialist",
        
        # Step 3 - Product Development Manager
        "product management": "Product Development Manager",
        "product approval": "Product Development Manager", 
        "product validation":"Product Development Manager",
        "quality standards": "Product Development Manager",
        "specification approval": "Product Development Manager",
        "technical assessment": "Product Development Manager",
        "product acceptance": "Product Development Manager",
        
        # Step 4 - Tax Accounting and Admin Specialist
        "foreign currency": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "bank permit": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "currency permit": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "bank permits": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        
        # Step 5 -  Commercial & Finance Specialist (Consolidation and Kenya-Focused)
        "supplier payment": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "payment processing": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "process payment": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "export documentation": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "payment confirmation": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        
        # Step 6 - Kenyan operation specialist
        "transportation logistics": "Kenyan operation specialist",
        "transport arrangement": "Kenyan operation specialist",
        "appropriate truck": "Kenyan operation specialist",
        "kenya operation": "Kenyan operation specialist",
        
        # Step 7 - Kenyan operation specialist
        "kenya side": "Kenyan operation specialist",
        "kenya dispatch": "Kenyan operation specialist", 
        "kenya clearance": "Kenyan operation specialist",
        "kenyan customs": "Kenyan operation specialist",
        "kenya border": "Kenyan operation specialist",
        "kenya moyale": "Kenyan operation specialist",
        
        # Step 8 - Ethiopian Operation Specialist
        "ethiopian customs": "Ethiopia Operation Specialist (Senior)",
        "ethiopian clearance": "Ethiopia Operation Specialist (Senior)",
        "customs clearance": "Ethiopia Operation Specialist (Senior)",
        "1st payment": "Ethiopia Operation Specialist (Senior)",
        "permit value": "Ethiopia Operation Specialist (Senior)",
        
        # Step 9 - Tax Accounting and Admin Specialist
        "tax reassessment": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "2nd tax": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "final payment": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "tax payment": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        
        # Step 10 - Ethiopian Operation Specialist
        "product loading": "Ethiopia Operation Specialist (Senior)",
        "dispatch coordination": "Ethiopia Operation Specialist (Senior)",
        "product dispatch": "Ethiopia Operation Specialist (Senior)",
        
        # Step 11 - Ethiopian Operation Specialist
        "transport monitoring": "Ethiopia Operation Specialist (Senior)",
        "truck movement": "Ethiopia Operation Specialist (Senior)",
        "truck tracking": "Ethiopia Operation Specialist (Senior)",
        
        # Step 12 - Tax Accounting and Admin Specialist
        "final delivery": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "warehouse handover": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "customer delivery": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "customer warehouse": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        
        # Step 13 - Commercial and Finance Specialist
        "post-delivery": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "financial settlements": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "document archiving": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "lesson learned": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "closed order": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)"
    }
    
    # DIRECT CHECK - No complex logic, just direct mapping
    for keyword, role in process_role_mapping.items():
        if keyword in task_lower:
            print(f"🎯 DIRECT MATCH: '{keyword}' -> {role}")
            return role
    
    # If no direct match, check for step numbers
    step_keywords = {
        "step 1": "Account Executive", "step1": "Account Executive", "1.": "Account Executive",
        "step 2": "Supply Chain Specialist", "step2": "Supply Chain Specialist", "2.": "Supply Chain Specialist", 
        "step 3": "Product Development Manager", "step3": "Product Development Manager", "3.": "Product Development Manager",
        "step 4": "Tax Accounting & Admin Specialist (Ethiopia-Focused)", "step4": "Tax Accounting & Admin Specialist (Ethiopia-Focused)", "4.": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "step 5": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)", "step5": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)", "5.": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
        "step 6": "Kenyan operation specialist", "step6": "Kenyan operation specialist", "6.": "Kenyan operation specialist",
        "step 7": "Kenyan operation specialist", "step7": "Kenyan operation specialist", "7.": "Kenyan operation specialist",
        "step 8": "Ethiopian Operation Specialist", "step8": "Ethiopian Operation Specialist", "8.": "Ethiopian Operation Specialist",
        "step 9": "Tax Accounting & Admin Specialist (Ethiopia-Focused)", "step9": "Tax Accounting & Admin Specialist (Ethiopia-Focused)", "9.": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "step 10": "Ethiopian Operation Specialist", "step10": "Ethiopian Operation Specialist", "10.": "Ethiopian Operation Specialist",
        "step 11": "Ethiopian Operation Specialist", "step11": "Ethiopian Operation Specialist", "11.": "Ethiopian Operation Specialist",
        "step 12": "Tax Accounting & Admin Specialist (Ethiopia-Focused)", "step12": "Tax Accounting & Admin Specialist (Ethiopia-Focused)", "12.": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
        "step 13": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)", "step13": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)", "13.": " Commercial & Finance Specialist (Consolidation and Kenya-Focused)"
    }
    
    for step_keyword, role in step_keywords.items():
        if step_keyword in task_lower:
            print(f"🎯 STEP MATCH: '{step_keyword}' -> {role}")
            return role
    
    print(f"❌ No process role identified for: {task_description}")
    return None



def get_role_based_qualifications(task_description, employee, jd_text=None):
    """
    Extract key qualifications with focus on role and task alignment
    """
    task_lower = task_description.lower()
    qualifications = []
    
    # Role-based qualifications (primary)
    employee_role = employee.get('role') or ''
    if employee_role:
        qualifications.append(f"Role: {employee_role}")
    
    # Check for role keywords in task
    role_keywords = {
        'supply chain': ['logistics', 'shipment', 'inventory', 'customs', 'border', 'transport'],
        'sales': ['client', 'deal', 'agreement', 'invoice', 'customer', 'sales'],
        'product': ['product', 'quality', 'specification', 'technical', 'testing'],
        'finance': ['payment', 'bank', 'tax', 'financial', 'currency', 'accounting']
    }
    
    for role_type, keywords in role_keywords.items():
        if any(keyword in task_lower for keyword in keywords):
            if role_type in employee_role.lower():
                qualifications.append(f"Task-Role Alignment: {role_type.title()}")
                break
    
    # Department-based qualifications
    department = employee.get('department') or ''
    if department:
        qualifications.append(f"Department: {department}")
    
    # JD-based qualifications (if available)
    if jd_text:
        jd_lower = jd_text.lower()
        
        # Look for role-specific keywords in JD
        matched_keywords = []
        role_task_keywords = ['manage', 'coordinate', 'lead', 'process', 'arrange', 'finalize']
        
        for keyword in role_task_keywords:
            if keyword in task_lower and keyword in jd_lower:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            qualifications.append(f"JD Task Alignment: {', '.join(matched_keywords[:2])}")
    
    return qualifications[:4]  # Limit to 4 key qualifications

def get_role_based_recommendations_for_predefined_process(recommended_role, employees, task_description):
    """
    Get employee recommendations for predefined process tasks.
    Returns exactly 1 employee with 100% fit score if they match the recommended role.
    Uses recommended_role from strategic_metadata.
    
    Args:
        recommended_role: The recommended role from predefined process
        employees: List of all employees
        task_description: Task description
    
    Returns:
        list: List with 1 recommendation if match found, empty list otherwise
    """
    recommendations = []
    
    if not recommended_role:
        return recommendations
    
    recommended_role_lower = recommended_role.lower().strip()
    
    # 🎯 PREDEFINED PROCESS: Match role assigned in task with employee role - suggest ONLY that employee
    # Find employees matching the recommended role exactly
    for employee in employees:
        employee_role = (employee.get('role') or '').lower().strip()
        employee_title = (employee.get('title') or '').lower().strip()
        
        # Check for exact role match first
        if recommended_role_lower == employee_role:
            recommendations.append({
                'employee_id': employee['id'],
                'employee_name': employee.get('name', 'Unknown'),
                'employee_role': employee.get('role', ''),
                'employee_department': employee.get('department', ''),
                'fit_score': 100,  # 🎯 100% fit for predefined process role match
                'confidence': 'high',
                'reason': f"Perfect role match for predefined process: {recommended_role}",
                'key_qualifications': [
                    f"Role: {employee.get('role', 'N/A')}",
                    f"Department: {employee.get('department', 'N/A')}",
                    "Predefined Process Role Match"
                ],
                'skills_match': [],
                'skills_match_list': [],
                'rag_enhanced': False,  # Not using RAG for predefined processes
                'rag_enhanced_score': None,
                'role_based_assignment': True,  # 🎯 FLAG AS ROLE-BASED
                'assignment_type': 'direct_role_assignment'  # 🎯 DIRECT ROLE ASSIGNMENT
            })
            # 🎯 RETURN ONLY 1 RECOMMENDATION FOR PREDEFINED PROCESSES
            return recommendations  # Return immediately after finding exact match
    
    # If no exact match, try partial match
    if not recommendations:
        for employee in employees:
            employee_role = (employee.get('role') or '').lower().strip()
            
            # Check for partial role match (contains recommended role keywords)
            role_keywords = recommended_role_lower.split()
            matching_keywords = sum(1 for keyword in role_keywords if len(keyword) > 3 and keyword in employee_role)
            
            if matching_keywords >= len(role_keywords) * 0.6:  # 60% keyword match
                recommendations.append({
                    'employee_id': employee['id'],
                    'employee_name': employee.get('name', 'Unknown'),
                    'employee_role': employee.get('role', ''),
                    'employee_department': employee.get('department', ''),
                    'fit_score': 95,  # High fit for partial match
                    'confidence': 'high',
                    'reason': f"Strong role match for predefined process: {recommended_role}",
                    'key_qualifications': [
                        f"Role: {employee.get('role', 'N/A')}",
                        f"Department: {employee.get('department', 'N/A')}",
                        "Predefined Process Role Match (Partial)"
                    ],
                    'skills_match': [],
                    'skills_match_list': [],
                    'rag_enhanced': False,
                    'rag_enhanced_score': None,
                    'role_based_assignment': True,
                    'assignment_type': 'direct_role_assignment'
                })
                break
    
    return recommendations

def generate_role_based_reason(employee, jd_available, fit_score, task_description):
    """
    Generate reasoning focused on role and task alignment
    """
    base_reason = f"{employee['name']} ({employee.get('role', 'N/A')}) - {fit_score}% role-task alignment"
    
    if jd_available:
        return f"{base_reason} (JD-verified role capabilities)"
    else:
        return f"{base_reason} (role and department matching)"

def get_confidence_level(fit_score):
    """Convert fit_score to confidence level"""
    if fit_score >= 90:
        return 'high'
    elif fit_score >= 80:
        return 'medium'
    else:
        return 'low'
    

def find_employee_by_exact_role(employees, target_role):
    """
    Find employees by EXACT role match first, then fall back to department
    """
    if not target_role or not employees:
        return []
    
    target_role_lower = target_role.lower().strip()
    exact_matches = []
    department_matches = []
    
    # Department to roles mapping
    department_roles = {
        "SUPPLY CHAIN DEPARTMENT": [
            "Supply Chain Specialist", 
            "Kenyan operation specialist", 
            "Ethiopian Operation Specialist"
        ],
        "SALES DEPARTMENT": [
            "Account Executive"
        ],
        "PRODUCT DEVELOPMENT DEPARTMENT": [
            "Product Development Manager"
        ],
        "FINANCE & ADMIN DEPARTMENT": [
            "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            " Commercial & Finance Specialist (Consolidation and Kenya-Focused)"
        ]
    }
    
    # Find department for the target role
    target_department = None
    for dept, roles in department_roles.items():
        if target_role in roles:
            target_department = dept
            break
    
    for employee in employees:
        employee_role = (employee.get('role') or '').lower().strip()
        employee_department = (employee.get('department') or '').upper().strip()
        
        # 1. EXACT ROLE MATCH (Highest priority)
        if employee_role == target_role_lower:
            exact_matches.append(employee)
        
        # 2. DEPARTMENT MATCH (Fallback - only if no exact matches)
        elif target_department and employee_department == target_department:
            department_matches.append(employee)
    
    print(f"🔍 Role matching for '{target_role}':")
    print(f"   - Exact role matches: {len(exact_matches)}")
    print(f"   - Department matches: {len(department_matches)}")
    
    # Return exact matches first, then department matches as fallback
    if exact_matches:
        return exact_matches
    elif department_matches:
        print(f"   ⚠️ Using department fallback for {target_role}")
        return department_matches
    else:
        return []
    
def enhanced_role_based_employee_recommendations(task_description, employees, top_k=3, ai_meta_id=None, task_title=None, task=None):
    """
    FULL RAG with JD Analysis - Uses AI to analyze Job Descriptions and Task requirements
    For custom AI-generated tasks, this performs deep analysis of JD content and task titles
    """
    try:
        print(f"🔍 FULL RAG ANALYSIS for: {task_description[:100]}...")
        
        if ai_meta_id:
            task_context = f"{task_title or task_description[:50]}..." if task_title else task_description[:50]
            update_ai_progress(ai_meta_id, 25, "Analyzing Task Requirements", f"Analyzing task: {task_context}")
        
        # STEP 1: Check for recommended_role from strategic_metadata first (for predefined processes)
        responsible_role = None
        if task:
            strategic_meta_raw = task.get('strategic_metadata')
            if strategic_meta_raw:
                if isinstance(strategic_meta_raw, str):
                    try:
                        strategic_meta = json.loads(strategic_meta_raw)
                    except:
                        strategic_meta = {}
                elif isinstance(strategic_meta_raw, dict):
                    strategic_meta = strategic_meta_raw
                else:
                    strategic_meta = {}
                
                responsible_role = strategic_meta.get('recommended_role') or strategic_meta.get('assigned_role')
                if responsible_role:
                    print(f"🎯 USING RECOMMENDED ROLE FROM METADATA: {responsible_role}")
        
        # STEP 2: If no recommended_role found, try to identify from process description
        if not responsible_role:
            responsible_role = identify_responsible_role_from_process(task_description)
        
        if responsible_role:
            print(f"🎯 PROCESS ROLE FOUND: {responsible_role}")
            if ai_meta_id:
                update_ai_progress(ai_meta_id, 50, "Using Predefined Process Role", f"Role: {responsible_role}")
            matched_employees = find_employee_by_exact_role(employees, responsible_role)
            
            if matched_employees:
                employee = matched_employees[0]
                assignment_type = "exact_role_assignment" if employee.get('role', '').lower() == responsible_role.lower() else "department_fallback_assignment"
                
                recommendation = {
                    'employee_id': employee['id'],
                    'employee_name': employee['name'],
                    'employee_role': employee.get('role', ''),
                    'employee_department': employee.get('department', ''),
                    'fit_score': 100,
                    'key_qualifications': [f"Process Role: {responsible_role}", f"Assignment: {assignment_type}"],
                    'reason': f"Process assignment: {employee['name']} ({employee.get('role', '')}) handles {responsible_role} tasks",
                    'rag_enhanced': False,
                    'assignment_type': assignment_type,
                    'role_based_assignment': True,
                    'process_role_matched': responsible_role
                }
                print(f"✅ ASSIGNED: {employee['name']} as {responsible_role} ({assignment_type})")
                if ai_meta_id:
                    update_ai_progress(ai_meta_id, 100, "Recommendation Complete", f"Assigned: {employee['name']}")
                return [recommendation]
        
        # STEP 2: For custom AI tasks, use FULL RAG with JD analysis
        task_context = f"{task_title or task_description[:50]}..." if task_title else task_description[:50]
        print(f"🔍 Custom AI Task - Starting FULL RAG with JD Analysis for: {task_context}")
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 30, "Starting JD Analysis", f"Preparing to analyze Job Descriptions for task: {task_context}")
        
        return full_rag_jd_analysis(task_description, employees, top_k, ai_meta_id, task_title)
        
    except Exception as e:
        print(f"❌ Enhanced RAG error: {e}")
        import traceback
        traceback.print_exc()
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 0, "Error", f"Error in RAG analysis: {str(e)}")
        return []

def full_rag_jd_analysis(task_description, employees, top_k=3, ai_meta_id=None, task_title=None):
    """
    FULL RAG Analysis using AI to analyze Job Descriptions and Task requirements
    """
    try:
        if not client:
            print("⚠️ OpenAI client not available, using fallback")
            return department_based_analysis(task_description, employees, top_k=3)
        
        # Combine task title and description for better context
        full_task_context = f"{task_title or ''} {task_description}".strip()
        task_display = task_title or task_description[:60] + "..." if len(task_description) > 60 else task_description
        
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 35, "Analyzing Task Context", f"Extracting requirements from: {task_display}")
        
        # Filter employees with JD URLs
        employees_with_jd = [emp for emp in employees if emp.get('job_description_url')]
        employees_without_jd = [emp for emp in employees if not emp.get('job_description_url')]
        
        print(f"📊 Employees with JD: {len(employees_with_jd)}, without JD: {len(employees_without_jd)}")
        
        recommendations = []
        
        # Process employees with JD using AI analysis
        if employees_with_jd:
            if ai_meta_id:
                update_ai_progress(ai_meta_id, 40, "Fetching Job Descriptions", f"Loading JDs for {len(employees_with_jd)} employees")
            
            for i, employee in enumerate(employees_with_jd[:10]):  # Limit to 10 for performance
                try:
                    jd_url = employee.get('job_description_url')
                    if not jd_url:
                        continue
                    
                    if ai_meta_id:
                        progress = 40 + int((i / min(len(employees_with_jd), 10)) * 40)
                        employee_name = employee.get('name', 'Employee')
                        update_ai_progress(ai_meta_id, progress, "Analyzing Job Descriptions", 
                                         f"Analyzing JD for {employee_name} against task: {task_display} ({i+1}/{min(len(employees_with_jd), 10)})")
                    
                    # Fetch JD content (simplified - in production, you'd fetch from Google Drive)
                    # For now, we'll use AI to analyze based on role, title, and task requirements
                    jd_analysis = analyze_employee_jd_with_ai(
                        task_description=full_task_context,
                        task_title=task_title or task_description,
                        employee=employee,
                        ai_meta_id=ai_meta_id
                    )
                    
                    if jd_analysis and jd_analysis.get('fit_score', 0) >= 60:
                        recommendations.append(jd_analysis)
                        
                except Exception as emp_error:
                    print(f"⚠️ Error analyzing employee {employee.get('name')}: {emp_error}")
                    continue
        
        # Process employees without JD using basic analysis
        if employees_without_jd and len(recommendations) < top_k:
            if ai_meta_id:
                update_ai_progress(ai_meta_id, 85, "Analyzing Employees Without JD", "Using role and department matching")
            
            basic_recommendations = department_based_analysis(task_description, employees_without_jd, top_k=top_k - len(recommendations))
            recommendations.extend(basic_recommendations)
        
        # Sort by fit score and return top_k
        recommendations.sort(key=lambda x: x.get('fit_score', 0), reverse=True)
        top_recommendations = recommendations[:top_k]
        
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 95, "Finalizing Recommendations", 
                             f"Generated {len(top_recommendations)} recommendations")
        
        print(f"✅ Generated {len(top_recommendations)} RAG recommendations")
        return top_recommendations
        
    except Exception as e:
        print(f"❌ Full RAG JD Analysis error: {e}")
        import traceback
        traceback.print_exc()
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 0, "Error", f"Error in JD analysis: {str(e)}")
        return department_based_analysis(task_description, employees, top_k=3)

def analyze_employee_jd_with_ai(task_description, task_title, employee, ai_meta_id=None):
    """
    Use AI to analyze employee JD against task requirements
    """
    try:
        employee_name = employee.get('name', 'Unknown')
        employee_role = employee.get('role', '')
        employee_title = employee.get('title', '')
        employee_department = employee.get('department', '')
        employee_skills = employee.get('skills', [])
        jd_url = employee.get('job_description_url', '')
        
        # Build employee profile summary
        employee_profile = f"""
Employee Profile:
- Name: {employee_name}
- Role: {employee_role}
- Title: {employee_title}
- Department: {employee_department}
- Skills: {', '.join(employee_skills) if isinstance(employee_skills, list) else str(employee_skills)}
- Job Description Available: {'Yes' if jd_url else 'No'}
"""
        
        prompt = f"""
You are an HR expert analyzing employee-task fit using Job Descriptions and role information.

TASK REQUIREMENTS:
Title: {task_title}
Description: {task_description}

EMPLOYEE PROFILE:
{employee_profile}

Analyze how well this employee matches the task requirements based on:
1. **Role alignment** - How well does the employee's role match the task requirements?
2. **Job Description analysis** - If JD is available, analyze the JD content against task requirements
3. **Department relevance** - Is the employee's department relevant to the task?
4. **Skills match** - Do the employee's skills align with task requirements?
5. **Experience level** - Does the employee have appropriate experience?

**IMPORTANT:** Prioritize role and JD analysis. If JD is available, use it to assess fit. If not, rely on role, department, and skills.

Return ONLY valid JSON in this exact format:
{{
    "fit_score": 85,
    "skills_match": 90,
    "role_alignment": 80,
    "jd_relevance": 75,
    "overall_fit": "excellent",
    "key_qualifications": ["Qualification 1", "Qualification 2", "Qualification 3"],
    "reason": "Detailed explanation of why this employee is suitable for the task",
    "confidence": "high"
}}

Fit score should be 0-100 based on overall match.
"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an HR expert. Return ONLY valid JSON. Do not include markdown or code blocks."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500,
            timeout=20
        )
        
        response_text = response.choices[0].message.content.strip()
        analysis = safe_json_parse(response_text, {})
        
        if not analysis or not analysis.get('fit_score'):
            # Fallback to basic scoring
            return create_basic_recommendation(employee, task_description)
        
        # Build recommendation from AI analysis
        recommendation = {
            'employee_id': employee['id'],
            'employee_name': employee_name,
            'employee_role': employee_role,
            'employee_department': employee_department,
            'fit_score': analysis.get('fit_score', 70),
            'skills_match': analysis.get('skills_match', 0),
            'role_alignment': analysis.get('role_alignment', 0),
            'jd_relevance': analysis.get('jd_relevance', 0),
            'overall_fit': analysis.get('overall_fit', 'moderate'),
            'key_qualifications': analysis.get('key_qualifications', [
                f"Role: {employee_role}",
                f"Department: {employee_department}"
            ]),
            'reason': analysis.get('reason', f"{employee_name} matches task requirements based on role and skills"),
            'confidence': analysis.get('confidence', 'medium'),
            'rag_enhanced': True,
            'jd_analyzed': bool(jd_url),
            'assignment_type': 'ai_jd_analysis',
            'role_based_assignment': False
        }
        
        return recommendation
        
    except Exception as e:
        print(f"⚠️ Error in AI JD analysis for {employee.get('name')}: {e}")
        return create_basic_recommendation(employee, task_description)

def create_basic_recommendation(employee, task_description):
    """Create a basic recommendation when AI analysis fails"""
    task_lower = task_description.lower()
    employee_role = (employee.get('role') or '').lower()
    employee_department = (employee.get('department') or '').lower()
    
    score = 50  # Base score
    
    # Role matching
    if employee_role and any(word in task_lower for word in employee_role.split() if len(word) > 3):
        score += 20
    
    # Department matching
    dept_keywords = {
        'supply chain': ['logistics', 'shipment', 'inventory', 'customs'],
        'sales': ['client', 'deal', 'agreement', 'invoice'],
        'product': ['product', 'quality', 'specification'],
        'finance': ['payment', 'bank', 'tax', 'financial']
    }
    
    for dept, keywords in dept_keywords.items():
        if dept in employee_department:
            if any(kw in task_lower for kw in keywords):
                score += 15
            break
    
    return {
        'employee_id': employee['id'],
        'employee_name': employee.get('name', 'Unknown'),
        'employee_role': employee.get('role', ''),
        'employee_department': employee.get('department', ''),
        'fit_score': min(score, 100),
        'key_qualifications': [
            f"Role: {employee.get('role', 'N/A')}",
            f"Department: {employee.get('department', 'N/A')}"
        ],
        'reason': f"{employee.get('name')} matches based on role and department",
        'rag_enhanced': False,
        'assignment_type': 'basic_analysis'
    }
def department_based_analysis(task_description, employees, top_k=3):
    """
    Department-based analysis for non-process tasks
    Returns top_k recommendations (default: 3)
    """
    task_lower = task_description.lower()
    recommendations = []
    
    # Department to task keyword mapping
    department_keywords = {
        "SUPPLY CHAIN DEPARTMENT": [
            "logistics", "shipment", "inventory", "customs", "border", "transport",
            "supplier", "stock", "delivery", "clearance", "dispatch", "shipping"
        ],
        "SALES DEPARTMENT": [
            "client", "deal", "agreement", "invoice", "customer", "sales",
            "commercial", "revenue", "proposal", "negotiation"
        ],
        "PRODUCT DEVELOPMENT DEPARTMENT": [
            "product", "quality", "specification", "technical", "testing",
            "validation", "development", "design", "engineering"
        ],
        "FINANCE & ADMIN DEPARTMENT": [
            "payment", "bank", "tax", "financial", "currency", "accounting",
            "budget", "compliance", "documentation", "admin", "administrative"
        ]
    }
    
    for employee in employees:
        try:
            employee_department = (employee.get('department') or '').upper().strip()
            employee_role = employee.get('role') or ''
            
            if not employee_department:
                continue
                
            # Check if employee's department keywords match the task
            department_score = 0
            if employee_department in department_keywords:
                keywords = department_keywords[employee_department]
                matching_keywords = sum(1 for keyword in keywords if keyword in task_lower)
                department_score = min(matching_keywords * 15, 60)  # Max 60 points
            
            # Role relevance bonus
            role_score = 0
            if employee_role:
                role_words = employee_role.lower().split()
                role_matches = sum(1 for word in role_words if len(word) > 4 and word in task_lower)
                role_score = min(role_matches * 10, 30)  # Max 30 points
            
            # Experience bonus
            experience = employee.get('experience_years', 0)
            exp_score = min(experience * 2, 10)  # Max 10 points
            
            total_score = department_score + role_score + exp_score
            
            if total_score >= 40:
                recommendations.append({
                    'employee_id': employee['id'],
                    'employee_name': employee['name'],
                    'employee_role': employee_role,
                    'employee_department': employee_department,
                    'fit_score': total_score,
                    'key_qualifications': [
                        f"Department: {employee_department}",
                        f"Role: {employee_role}",
                        f"Experience: {experience} years"
                    ],
                    'reason': f"Department-based match: {employee_department} expertise",
                    'rag_enhanced': False,
                    'assignment_type': 'department_analysis',
                    'role_based_assignment': False
                })
                
        except Exception as emp_error:
            print(f"⚠️ Error processing employee {employee.get('name', 'Unknown')}: {emp_error}")
            continue
    
    # Sort and return top_k recommendations
    sorted_recommendations = sorted(recommendations, key=lambda x: x['fit_score'], reverse=True)
    return sorted_recommendations[:top_k]

# Update the main function to use the corrected approach
def corrected_process_employee_recommendations_for_task(task, employees, ai_meta_id):
    """
    CORRECTED RAG-enhanced employee recommendation process
    
    For predefined processes: Uses recommended_role for role-based assignment (100% fit, 1 recommendation)
    For AI-classified tasks: Uses full RAG with JD analysis for employee recommendations
    """
    try:
        supabase = get_supabase_client()
        start_time = time.time()
        
        print(f"👥 Processing CORRECTED RAG employee recommendations for task: {task['task_description'][:50]}...")
        
        # 🎯 SIMPLE RULE: Check template from objective
        # Get objective to check template
        objective_id = task.get('objective_id')
        objective_template = None
        if objective_id:
            try:
                objective_result = supabase.table("objectives").select("ai_meta_id").eq("id", objective_id).execute()
                if objective_result.data and objective_result.data[0].get('ai_meta_id'):
                    ai_meta_id_obj = objective_result.data[0]['ai_meta_id']
                    ai_meta_result = supabase.table("ai_meta").select("input_json").eq("id", ai_meta_id_obj).execute()
                    if ai_meta_result.data and ai_meta_result.data[0].get('input_json'):
                        objective_template = ai_meta_result.data[0]['input_json'].get('template')
            except Exception as e:
                print(f"⚠️ Error getting objective template: {e}")
        
        # Get recommended_role from strategic_metadata
        strategic_meta_raw = task.get('strategic_metadata')
        if isinstance(strategic_meta_raw, str):
            try:
                strategic_meta = json.loads(strategic_meta_raw)
            except:
                strategic_meta = {}
        elif isinstance(strategic_meta_raw, dict):
            strategic_meta = strategic_meta_raw
        else:
            strategic_meta = {}
        
        recommended_role = strategic_meta.get('recommended_role') or strategic_meta.get('assigned_role')
        
        # 🎯 SIMPLE CHECK: predefined processes (order_to_delivery, stock_to_delivery) = role matching, auto = RAG
        is_predefined_process = objective_template in ('order_to_delivery', 'order-to-delivery', 'stock_to_delivery', 'stock-to-delivery', 'lead_to_delivery', 'lead-to-delivery')
        
        # Debug logging
        print(f"=" * 80)
        print(f"🔍 FUNCTION DEBUG: Task ID: {task.get('id')}")
        print(f"🔍 FUNCTION DEBUG: Objective ID: {objective_id}")
        print(f"🔍 FUNCTION DEBUG: Objective template: {objective_template}")
        print(f"🔍 FUNCTION DEBUG: Is predefined process: {is_predefined_process}")
        print(f"🔍 FUNCTION DEBUG: recommended_role: {recommended_role}")
        print(f"🔍 FUNCTION DEBUG: Condition check - is_predefined_process AND recommended_role: {is_predefined_process and bool(recommended_role)}")
        print(f"=" * 80)
        
        # Step 1: Update progress based on template type
        if is_predefined_process and recommended_role:
            strategy = "role_based_predefined_process"
            activity = f"Matching role: {recommended_role}"
            details = f"Searching for employee with role: {recommended_role}"
            print(f"✅ PREDEFINED PROCESS TEMPLATE ({objective_template}): Will use role-based matching for {recommended_role}")
        else:
            strategy = "full_rag_ai_classified"
            activity = "Starting full RAG analysis with JD documents"
            details = "Analyzing task requirements and preparing to match with employee Job Descriptions"
            print(f"ℹ️ AI-GENERATED TASK (template: {objective_template}): Will use full RAG analysis")
        
        # Update progress IMMEDIATELY - this is the first thing that happens
        update_data = {
            "output_json": {
                "status": "processing",
                "progress": 10 if (is_predefined_process and recommended_role) else 20,
                "current_activity": activity,  # This should be "Matching role: X" for order_to_delivery
                "activity_details": details,
                "task_id": task['id'],
                "employees_analyzed": len(employees),
                "rag_enhanced": not (is_predefined_process and recommended_role),  # False for order_to_delivery
                "assignment_strategy": strategy,
                "is_predefined_process": is_predefined_process,
                "template": objective_template
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(update_data).eq("id", ai_meta_id).execute()
        print(f"📊 IMMEDIATE Progress update: {activity} (progress: {update_data['output_json']['progress']}%)")
        
        # Step 2: Get recommendations based on template type
        rag_recommendations = []
        if is_predefined_process and recommended_role:
            # 🎯 PREDEFINED PROCESS TEMPLATE: Use recommended role only (100% fit, 1 recommendation)
            print(f"🎯 PREDEFINED PROCESS ({objective_template}): Using role-based assignment for role: {recommended_role}")
            
            # Update progress immediately to show role matching (no artificial delay)
            supabase.table("ai_meta").update({
                "output_json": {
                    "status": "processing",
                    "progress": 50,
                    "current_activity": f"Matching role: {recommended_role}",
                    "activity_details": f"Checking employees with role: {recommended_role}",
                    "task_id": task['id'],
                    "employees_analyzed": len(employees),
                    "rag_enhanced": False,
                    "assignment_strategy": strategy,
                    "is_predefined_process": True
                },
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", ai_meta_id).execute()
            
            rag_recommendations = get_role_based_recommendations_for_predefined_process(
                recommended_role=recommended_role,
                employees=employees,
                task_description=task['task_description']
            )
            
            print(f"✅ Role-based matching complete: Found {len(rag_recommendations)} employee(s)")
            if rag_recommendations:
                print(f"   → Recommended: {rag_recommendations[0]['employee_name']} ({rag_recommendations[0]['employee_role']})")
            
            # Update progress to show match found immediately
            supabase.table("ai_meta").update({
                "output_json": {
                    "status": "processing",
                    "progress": 95,
                    "current_activity": "Role match found" if rag_recommendations else "No matching role found",
                    "activity_details": f"Found {len(rag_recommendations)} matching employee(s) for role: {recommended_role}" if rag_recommendations else f"No employee found with role: {recommended_role}",
                    "task_id": task['id'],
                    "employees_analyzed": len(employees),
                    "rag_enhanced": False,
                    "assignment_strategy": strategy,
                    "is_predefined_process": True
                },
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", ai_meta_id).execute()
            
        else:
            # 🎯 AI-CLASSIFIED: Use full RAG with JD analysis
            print(f"🔍 AI-CLASSIFIED TASK: Using full RAG analysis with JD documents")
            task_title = task.get('task_description', '').split(':')[0] if ':' in task.get('task_description', '') else None
            rag_recommendations = enhanced_role_based_employee_recommendations(
                task_description=task['task_description'],
                employees=employees,
                top_k=3,  # 🎯 TOP 3 FOR AI-GENERATED TASKS
                ai_meta_id=ai_meta_id,
                task_title=task_title,
                task=task  # 🎯 PASS TASK OBJECT TO CHECK RECOMMENDED_ROLE
            )
        
        print(f"✅ Recommendation function returned {len(rag_recommendations)} recommendations")
        for rec in rag_recommendations:
            assignment_type = rec.get('assignment_type', 'analysis')
            role_based = rec.get('role_based_assignment', False)
            print(f"   - {rec['employee_name']}: {rec['fit_score']}% ({assignment_type}, role_based: {role_based})")
        
        # Step 3: Prepare final output
        processing_time = time.time() - start_time
        
        # Update task with final recommendations
        if not strategic_meta:
            strategic_meta = {}
        strategic_meta['ai_recommendations'] = rag_recommendations
        strategic_meta['employee_recommendations_available'] = bool(rag_recommendations)
        if is_predefined_process:
            strategic_meta['recommendations_analysis'] = f"Role-based assignment for predefined process - {len(rag_recommendations)} recommendation(s) matching role: {recommended_role}"
        else:
            strategic_meta['recommendations_analysis'] = f"Full RAG analysis with JD documents - {len(rag_recommendations)} recommendation(s)"
        strategic_meta['recommendations_generated_at'] = datetime.utcnow().isoformat()
        strategic_meta['rag_enhanced'] = True
        strategic_meta['recommendation_count'] = len(rag_recommendations)
        strategic_meta['assignment_strategy'] = strategy
        strategic_meta['total_employees_considered'] = len(employees)
        
        update_result = supabase.table("action_plans").update({
            "strategic_metadata": strategic_meta
        }).eq("id", task['id']).execute()
        
        # Step 4: Final update
        jd_analyzed_count = len([r for r in rag_recommendations if r.get('jd_analyzed')])
        ai_analyzed_count = len([r for r in rag_recommendations if r.get('rag_enhanced')])
        
        # For predefined processes, use simpler completion message
        if is_predefined_process:
            completion_message = f"Role-based assignment complete: {len(rag_recommendations)} employee(s) matched"
        else:
            completion_message = "RAG Analysis Complete"
        
        final_update = {
            "output_json": {
                "status": "completed",
                "progress": 100,
                "current_activity": completion_message,
                "activity_details": f"Generated {len(rag_recommendations)} recommendations ({jd_analyzed_count} with JD analysis, {ai_analyzed_count} AI-enhanced)",
                "task_id": task['id'],
                "recommendations_generated": len(rag_recommendations),
                "processing_time": processing_time,
                "rag_enhanced": True,
                "recommendation_count": len(rag_recommendations),
                "assignment_strategy": strategy,
                "role_based_assignments": len([r for r in rag_recommendations if r.get('role_based_assignment')]),
                "jd_analyzed_count": jd_analyzed_count,
                "ai_analyzed_count": ai_analyzed_count,
                "is_predefined_process": is_predefined_process,
                "recommended_role": recommended_role if is_predefined_process else None
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(final_update).eq("id", ai_meta_id).execute()
        
        print(f"✅ CORRECTED RAG recommendations completed in {processing_time:.2f}s")
        print(f"📊 Final recommendations: {len(rag_recommendations)}")
        print(f"🎯 Role-based assignments: {len([r for r in rag_recommendations if r.get('role_based_assignment')])}")
        
        return True
        
    except Exception as e:
        error_msg = f"Error in corrected RAG employee recommendations: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        
        return False


def calculate_advanced_fit_score(task_description, employee_role, employee_department, 
                               employee_skills, employee_experience, jd_text=None):
    """
    ADVANCED scoring system analyzing multiple criteria
    """
    task_lower = task_description.lower()
    score = 0
    
    # 1. ROLE ALIGNMENT (40 points max)
    role_score = calculate_role_alignment_score(task_lower, employee_role)
    score += role_score
    
    # 2. DEPARTMENT ALIGNMENT (20 points max)
    dept_score = calculate_department_alignment_score(task_lower, employee_department)
    score += dept_score
    
    # 3. SKILLS MATCHING (20 points max)
    skills_score = calculate_skills_matching_score(task_lower, employee_skills)
    score += skills_score
    
    # 4. JD CONTENT ANALYSIS (15 points max) - Only if JD available
    jd_score = 0
    if jd_text:
        jd_score = calculate_jd_analysis_score(task_lower, jd_text)
    score += jd_score
    
    # 5. EXPERIENCE BONUS (5 points max)
    exp_score = min(employee_experience, 5)
    score += exp_score
    
    return min(score, 100)

def calculate_role_alignment_score(task_lower, employee_role):
    """Calculate role alignment score (0-40 points)"""
    if not employee_role:
        return 0
        
    employee_role_lower = employee_role.lower()
    
    # Exact role match in task description
    if employee_role_lower in task_lower:
        return 40
    
    # Partial role match
    role_keywords = employee_role_lower.split()
    keyword_matches = sum(1 for keyword in role_keywords if len(keyword) > 3 and keyword in task_lower)
    
    if keyword_matches >= 2:
        return 30
    elif keyword_matches >= 1:
        return 20
    
    return 10  # Base score for having a role

def calculate_department_alignment_score(task_lower, employee_department):
    """Calculate department alignment score (0-20 points)"""
    if not employee_department:
        return 0
        
    dept_lower = employee_department.lower()
    
    # Department mapping to task keywords
    department_keywords = {
        "supply chain": ["logistics", "shipment", "inventory", "customs", "supplier", "stock", "delivery"],
        "sales": ["client", "deal", "agreement", "invoice", "customer", "sales", "revenue"],
        "product": ["product", "quality", "specification", "technical", "testing", "validation"],
        "finance": ["payment", "bank", "tax", "financial", "currency", "accounting", "budget"],
        "operations": ["coordinate", "arrange", "manage", "dispatch", "clearance", "transport"]
    }
    
    # Check if department matches task keywords
    for dept, keywords in department_keywords.items():
        if dept in dept_lower:
            matching_keywords = sum(1 for keyword in keywords if keyword in task_lower)
            return min(matching_keywords * 5, 20)  # 5 points per matching keyword, max 20
    
    return 5  # Base score for having a department

def calculate_skills_matching_score(task_lower, employee_skills):
    """Calculate skills matching score (0-20 points)"""
    if not employee_skills or not isinstance(employee_skills, list):
        return 0
    
    # Common task-related skills
    task_skills = [
        "management", "coordination", "analysis", "planning", "communication",
        "negotiation", "documentation", "processing", "validation", "testing",
        "logistics", "finance", "sales", "product", "quality", "technical"
    ]
    
    # Check for skill matches
    skill_matches = 0
    for skill in employee_skills[:10]:  # Check first 10 skills
        skill_lower = str(skill).lower()
        
        # Direct skill match in task
        if skill_lower in task_lower:
            skill_matches += 2
        # Partial skill match
        elif any(task_skill in skill_lower for task_skill in task_skills):
            skill_matches += 1
    
    return min(skill_matches * 4, 20)  # 4 points per strong match, 2 points per partial

def calculate_jd_analysis_score(task_lower, jd_text):
    """Calculate JD content analysis score (0-15 points)"""
    jd_lower = jd_text.lower()
    
    # Task-specific keywords to look for in JD
    task_keywords = [
        "manage", "coordinate", "lead", "process", "arrange", "finalize",
        "handle", "execute", "implement", "oversee", "supervise", "analyze",
        "develop", "create", "build", "design", "plan", "organize"
    ]
    
    # Count matching keywords between task and JD
    matching_keywords = sum(1 for keyword in task_keywords if keyword in task_lower and keyword in jd_lower)
    
    return min(matching_keywords * 3, 15)  # 3 points per matching keyword

def get_advanced_qualifications(task_description, employee, jd_text=None):
    """Generate advanced qualifications based on multiple criteria"""
    task_lower = task_description.lower()
    qualifications = []
    
    # Role-based qualification
    employee_role = employee.get('role') or ''
    if employee_role:
        qualifications.append(f"Role: {employee_role}")
    
    # Department qualification
    department = employee.get('department') or ''
    if department:
        qualifications.append(f"Department: {department}")
    
    # Skills qualification (top 3 relevant skills)
    skills = employee.get('skills', [])
    if skills and isinstance(skills, list):
        relevant_skills = []
        for skill in skills[:5]:  # Check first 5 skills
            skill_lower = str(skill).lower()
            if any(task_word in skill_lower for task_word in task_lower.split()):
                relevant_skills.append(skill)
        
        if relevant_skills:
            qualifications.append(f"Relevant Skills: {', '.join(relevant_skills[:3])}")
    
    # Experience qualification
    experience = employee.get('experience_years', 0)
    if experience > 0:
        qualifications.append(f"Experience: {experience} years")
    
    # JD-based qualification (if available)
    if jd_text:
        jd_lower = jd_text.lower()
        task_words = set(task_lower.split())
        jd_words = set(jd_lower.split())
        common_words = task_words.intersection(jd_words)
        
        if len(common_words) >= 3:
            qualifications.append(f"JD Alignment: {len(common_words)} matching terms")
    
    return qualifications[:5]  # Limit to 5 qualifications

def generate_advanced_reason(employee, fit_score, task_description, jd_available):
    """Generate detailed reasoning for advanced analysis"""
    base_reason = f"{employee['name']} ({employee.get('role', 'N/A')}) - {fit_score}% task alignment"
    
    if jd_available:
        return f"{base_reason} (JD-enhanced analysis with skills and experience matching)"
    else:
        return f"{base_reason} (role, department, and skills analysis)"
    

def get_key_qualifications(task_description, employee, jd_text=None):
    """
    Extract key qualifications based on role, department, and JD with null safety
    """
    task_lower = task_description.lower()
    qualifications = []
    
    # Role-based qualifications
    employee_role = employee.get('role') or ''
    if employee_role:
        qualifications.append(f"Role: {employee_role}")
    
    # Department-based qualifications
    department = employee.get('department') or ''
    if department:
        qualifications.append(f"Department: {department}")
    
    # JD-based qualifications (if available)
    if jd_text:
        jd_lower = jd_text.lower()
        
        # Look for matching keywords in JD
        matched_keywords = []
        task_keywords = ['manage', 'develop', 'create', 'implement', 'coordinate', 'lead']
        
        for keyword in task_keywords:
            if keyword in task_lower and keyword in jd_lower:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            qualifications.append(f"JD keywords: {', '.join(matched_keywords[:3])}")
    
    return qualifications[:5]  # Limit to 5 qualification

def generate_simplified_reason(employee, jd_available, fit_score):
    """
    Generate simplified reasoning without confidence
    """
    base_reason = f"{employee['name']} ({employee.get('role', 'N/A')}) - {fit_score}% match"
    
    if jd_available:
        return f"{base_reason} (JD-enhanced analysis)"
    else:
        return f"{base_reason} (role and department matching)"


def ultra_fast_fallback(task_description, employees):
    """
    Fixed ultra-fast fallback with proper None handling
    """
    try:
        if not task_description:
            return []
            
        task_lower = task_description.lower()
        recommendations = []
        
        for employee in employees[:15]:  # Check more employees
            try:
                # Safe handling with proper None checks
                employee_name = employee.get('name', 'Unknown')
                employee_role = employee.get('role') or ''
                employee_department = employee.get('department') or ''
                
                # Skip if no role information
                if not employee_role:
                    continue
                    
                score = 0
                
                # Simple role matching
                if employee_role.lower() in task_lower:
                    score += 60
                
                # Simple department matching
                if employee_department and employee_department.lower() in task_lower:
                    score += 30
                
                # Experience bonus
                experience = employee.get('experience_years', 0)
                score += min(experience, 10)
                
                if score >= 40:
                    recommendations.append({
                        'employee_id': employee['id'],
                        'employee_name': employee_name,
                        'employee_role': employee_role,
                        'employee_department': employee_department,
                        'fit_score': score,
                        'key_qualifications': [
                            f"Role: {employee_role}",
                            f"Department: {employee_department or 'N/A'}"
                        ],
                        'reason': "Fallback matching based on role and department",
                        'jd_available': False,
                        'rag_enhanced': False,
                        'assignment_type': 'fallback'
                    })
                    
            except Exception as emp_error:
                print(f"⚠️ Error in fallback for employee {employee.get('name', 'Unknown')}: {emp_error}")
                continue
        
        # Apply same fit_score logic
        sorted_recs = sorted(recommendations, key=lambda x: x['fit_score'], reverse=True)
        if not sorted_recs:
            return []
        
        top_score = sorted_recs[0]['fit_score']
        
        if top_score > 90:
            return sorted_recs[:1]
        elif top_score >= 80:
            return sorted_recs[:min(2, len(sorted_recs))]
        else:
            return sorted_recs[:min(3, len(sorted_recs))]
            
    except Exception as e:
        print(f"❌ Ultra-fast fallback error: {e}")
        import traceback
        traceback.print_exc()
        return []

# Update the route to use corrected RAG method
@task_bp.route('/api/tasks/<task_id>/generate-rag-recommendations', methods=['POST'])
@token_required
@admin_required
def generate_rag_employee_recommendations(task_id):
    """Generate CORRECTED RAG-enhanced employee recommendations for a specific task"""
    try:
        supabase = get_supabase_client()
        
        # Get task details with objective info
        task_result = supabase.table("action_plans").select("*, objectives(*)").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = task_result.data[0]
        objective = task.get('objectives') or {}
        
        # 🎯 SIMPLE RULE: Check template from objective
        # If template is "order_to_delivery" → use predefined role matching
        # If template is "auto" → use RAG
        objective_template = None
        if isinstance(objective, dict):
            # Check ai_meta for template
            ai_meta_id_obj = objective.get('ai_meta_id')
            if ai_meta_id_obj:
                ai_meta_result = supabase.table("ai_meta").select("input_json").eq("id", ai_meta_id_obj).execute()
                if ai_meta_result.data and ai_meta_result.data[0].get('input_json'):
                    objective_template = ai_meta_result.data[0]['input_json'].get('template')
        
        # Also check strategic_metadata for role info
        strategic_meta_raw = task.get('strategic_metadata')
        if isinstance(strategic_meta_raw, str):
            try:
                strategic_meta = json.loads(strategic_meta_raw)
            except:
                strategic_meta = {}
        elif isinstance(strategic_meta_raw, dict):
            strategic_meta = strategic_meta_raw
        else:
            strategic_meta = {}
        
        recommended_role = strategic_meta.get('recommended_role') or strategic_meta.get('assigned_role')
        
        # 🎯 SIMPLE CHECK: predefined processes (order_to_delivery, stock_to_delivery) = role matching, auto = RAG
        is_predefined_process = objective_template in ('order_to_delivery', 'order-to-delivery', 'stock_to_delivery', 'stock-to-delivery', 'lead_to_delivery', 'lead-to-delivery')
        
        print(f"🔍 ENDPOINT DEBUG: Task ID: {task_id}")
        print(f"🔍 ENDPOINT DEBUG: Objective template: {objective_template}")
        print(f"🔍 ENDPOINT DEBUG: Is predefined process: {is_predefined_process}")
        print(f"🔍 ENDPOINT DEBUG: recommended_role: {recommended_role}")
        
        # Get all active employees with JD links
        employees_result = supabase.table("employees").select(
            "id, name, role, title, department, job_description_url"
        ).eq("is_active", True).execute()
        
        employees = employees_result.data if employees_result.data else []
        
        if not employees:
            return jsonify({'success': False, 'error': 'No active employees found'}), 400
        
        # 🎯 SIMPLE RULE: predefined processes = role matching, auto = RAG
        if is_predefined_process and recommended_role:
            initial_activity = f"Matching role: {recommended_role}"
            initial_details = f"Searching for employee with role: {recommended_role}"
            assignment_strategy = "role_based_predefined_process"
            print(f"✅ ENDPOINT: Predefined process template ({objective_template}) - will use role matching for {recommended_role}")
        else:
            initial_activity = "Starting full RAG analysis with JD documents"
            initial_details = "Analyzing task requirements and preparing to match with employee Job Descriptions"
            assignment_strategy = "full_rag_ai_classified"
            print(f"ℹ️ ENDPOINT: AI-generated task (template: {objective_template}) - will use full RAG analysis")
        
        # Create AI meta record for RAG recommendations
        ai_meta_data = {
            "source": "corrected-rag-recommendations",
            "model": "role-first-then-department",
            "input_json": {
                "task_id": task_id,
                "task_description": task['task_description'],
                "employees_count": len(employees),
                "employees_with_jd": len([emp for emp in employees if emp.get('job_description_url')]),
                "status": "starting",
                "corrected_rag": True,
                "assignment_strategy": assignment_strategy,
                "is_predefined_process": is_predefined_process,
                "recommended_role": recommended_role
            },
            "output_json": {
                "status": "processing",
                "progress": 0,
                "current_activity": initial_activity,
                "activity_details": initial_details,
                "task_id": task_id,
                "corrected_rag": True,
                "rag_enhanced": not (is_predefined_process and recommended_role),
                "assignment_strategy": assignment_strategy,
                "is_predefined_process": is_predefined_process,
                "template": objective_template
            },
            "created_at": datetime.utcnow().isoformat()
        }
        
        ai_meta_result = supabase.table("ai_meta").insert(ai_meta_data).execute()
        if not ai_meta_result.data:
            return jsonify({'success': False, 'error': 'Failed to create AI meta record'}), 500
        
        ai_meta_id = ai_meta_result.data[0]['id']
        
        # Start CORRECTED RAG-enhanced recommendation process in background
        threading.Thread(
            target=corrected_process_employee_recommendations_for_task,  # CHANGED THIS LINE
            args=(task, employees, ai_meta_id),
            daemon=True
        ).start()
        
        return jsonify({
            'success': True, 
            'ai_meta_id': ai_meta_id,
            'message': 'CORRECTED RAG employee recommendations processing started',
            'task_id': task_id,
            'corrected_rag': True,
            'assignment_strategy': assignment_strategy,
            'employees_count': len(employees),
            'is_predefined_process': is_predefined_process,
            'template': objective_template,
            'recommended_role': recommended_role,
            'initial_activity': initial_activity,
            'initial_details': initial_details
        })
        
    except Exception as e:
        error_msg = f"Error starting CORRECTED RAG employee recommendations: {str(e)}"  # UPDATED ERROR
        print(f"❌ {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500

@task_bp.route('/api/health/tasks', methods=['GET'])
def health_check():
    """Health check for tasks"""
    return jsonify({
        'success': True,
        'message': 'Tasks API is working',
        'openai_configured': bool(client),
        'timestamp': datetime.utcnow().isoformat()
    })

print("✅ Task routes loaded successfully with SEPARATED TWO-STEP AI PROCESS")
# Add this at the VERY BOTTOM of your task_routes.py file for testing
if __name__ == '__main__':
    from flask import Flask
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(task_bp)
    
    print("🚀 Starting Task API Server...")
    print("📋 Registered routes:")
    for rule in app.url_map.iter_rules():
        if 'tasks' in rule.endpoint:
            print(f"  {rule.endpoint:50} {rule.methods} {rule}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)