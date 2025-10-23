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

def create_enhanced_task_notification(task_id, notification_type, message, assigned_by=None, note_preview=None, attached_to=None, attached_to_multiple=None):
    """Enhanced notification function that handles employee attachments with added_by field"""
    try:
        supabase = get_supabase_client()
        
        # DEDUPLICATION: Check for recent duplicate notification (last 2 minutes)
        duplicate_check = supabase.table("notifications").select("id").eq("meta->>task_id", task_id).eq("meta->>type", notification_type).eq("to_employee", task.get('assigned_to')).gte("created_at", (datetime.utcnow() - timedelta(minutes=2)).isoformat()).execute()
        
        if duplicate_check.data:
            print(f"⏭️  Skipping duplicate notification for task {task_id}, type {notification_type}")
            return
        
        # Get task details with assigned employee information
        task_result = supabase.table("action_plans").select("task_description, assigned_to, assigned_to_multiple").eq("id", task_id).execute()
        if not task_result.data:
            return
        
        task = task_result.data[0]
        
        # Get admin employee ID
        admin_employee_id = get_admin_employee_id()
        
        # Get current user's name for added_by field
        current_user_name = "Unknown"
        if hasattr(g, 'user') and g.user:
            # Try to get the employee name from the database
            user_employee_id = g.user.get('employee_id')
            if user_employee_id:
                employee_result = supabase.table("employees").select("name").eq("id", user_employee_id).execute()
                if employee_result.data:
                    current_user_name = employee_result.data[0].get('name', 'Unknown')
            else:
                # Fallback to user's name from token if available
                current_user_name = g.user.get('name', 'Unknown')
        
        # Get assigned employee names
        assigned_employee_names = []
        assigned_to_multiple_names = []
        
        # Get primary assigned employee name
        if task.get('assigned_to'):
            emp_result = supabase.table("employees").select("name").eq("id", task['assigned_to']).execute()
            if emp_result.data:
                assigned_employee_names.append(emp_result.data[0].get('name', 'Unknown'))
        
        # Get multiple assigned employee names
        if task.get('assigned_to_multiple'):
            for emp_id in task['assigned_to_multiple']:
                emp_result = supabase.table("employees").select("name").eq("id", emp_id).execute()
                if emp_result.data:
                    assigned_to_multiple_names.append(emp_result.data[0].get('name', 'Unknown'))
        
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
                # SECONDARY DEDUPLICATION: Check per recipient
                recipient_duplicate = supabase.table("notifications").select("id").eq("meta->>task_id", task_id).eq("meta->>type", notification_type).eq("to_employee", recipient).gte("created_at", (datetime.utcnow() - timedelta(minutes=2)).isoformat()).execute()
                
                if recipient_duplicate.data:
                    print(f"⏭️  Skipping duplicate notification for recipient {recipient}")
                    continue
                
                notification_data = {
                    "to_employee": recipient,
                    "channel": "in_app",
                    "message": message,
                    "meta": {
                        "task_id": task_id,
                        "task_description": task['task_description'][:100], 
                        "type": notification_type,
                        "assigned_by": assigned_by,
                        "added_by": current_user_name,
                        "assigned_to": task.get('assigned_to'),
                        "assigned_to_name": assigned_employee_names[0] if assigned_employee_names else None,
                        "assigned_to_multiple": task.get('assigned_to_multiple', []),
                        "assigned_to_multiple_names": assigned_to_multiple_names,
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
    """Apply a specific employee recommendation to a task"""
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        
        employee_id = data.get('employee_id')
        recommendation_data = data.get('recommendation_data', {})
        
        if not employee_id:
            return jsonify({'success': False, 'error': 'Employee ID is required'}), 400
        
        # Update task with assigned employee
        update_data = {
            "assigned_to": employee_id,
            "assigned_to_multiple": [employee_id],
            "status": "not_started",
            "updated_at": datetime.utcnow().isoformat(),
            "strategic_metadata": {
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

@backoff.on_exception(backoff.expo, Exception, max_tries=2, max_time=10)
def classify_goal_to_tasks_only(goal, goal_data, ai_meta_id):
    try:
        start_time = time.time()
        if not client:
            tasks, message = fallback_task_classification(goal_data)
            return tasks, message, time.time() - start_time
        
        # Create the master prompt with strategic framework
        prompt = f"""
        You are an expert strategic planner for Lean Solution Ethiopia, specifically focused on LeanChems Ethiopia - the Construction and Coating Chemical Distribution business. The company's strategic position is:

        2025 TARGETS:
        · Secure partnership with Brenntag (global chemical distributor)
        · Secure top 20% strong deals in Dry Mix - "Value You Deserve"
        · Confirm 80% product market fit in Paint - "Chemical You Trust"
        · Pre-sale $250K Stock Order (80% priority) + Secure $500K Pipeline (20%)
        · Build strong construction & coating product portfolio for 2026

        2026 VISION:
        · Active partnership with Brenntag in Chemical Distribution
        · 80% focus on Construction & Coating chemicals, 20% other sectors
        · Foundation for market leadership in Ethiopian chemical distribution

        OPERATING PRINCIPLES:
        · "Wig-Objectives" focus - Wildly Important Goals that drive 80% of results
        · CEO daily focus includes Sales & Business Development, Partnership securing
        · Resource-constrained environment requiring high-impact prioritization

        TASK:

        Transform the provided objective into an executable action plan by first ensuring it meets quality standards and strategic alignment.

        VALIDATION FRAMEWORK - 80% COMPLIANCE REQUIRED:

        Evaluate the provided objective against these 5 criteria (must pass 4/5):

        1. CLARITY & SPECIFICITY CHECK:
           · Can someone unfamiliar with the context understand exactly what success means?
           · Is the scope clearly defined (product, market, partner, etc.)?
        2. MEASURABILITY & VERIFICATION CHECK:
           · Is there a quantifiable metric and target value?
           · Is the evidence source for completion identifiable?
        3. RELEVANCE & ALIGNMENT CHECK:
           · Does this directly advance LeanChems' 2025 Brenntag partnership goal?
           · Does it align with "Value You Deserve" (Dry Mix) or "Chemical You Trust" (Paint) positioning?
        4. ACTIONABILITY & OWNERSHIP CHECK:
           · Can it be broken into sequential tasks?
           · Is it clear who would lead this effort?
        5. TIME-BOUND CHECK:
           · Is there a specific deadline within Q4 2025?
           · Are progress checkpoints implied or stated?

        INSTRUCTION FLOW:

        Step 1 - Objective Analysis:
        Analyze the provided objective against the 5 criteria above
        Identify which criteria are met and which need refinement
        Ensure minimum 4/5 criteria pass (80% compliance)

        Step 2 - Strategic Alignment Verification:
        Confirm the objective advances LeanChems' partnership with Brenntag
        Verify it contributes to either Dry Mix "Value You Deserve" or Paint "Chemical You Trust" positioning
        Ensure it supports the broader Lean Solution Ethiopia framework

        Step 3 - Objective Refinement (if needed):
        If criteria compliance <80%, provide specific suggestions to upgrade the objective
        Maintain the original intent while adding missing elements
        Ensure refined objective passes the 80% threshold

        Step 4 - Action Plan Foundation:
        Once objective validates, outline the major phases/chains required
        Identify critical dependencies and potential bottlenecks
        Suggest key stakeholders or resources needed

        Step 5 - Q4 Execution Alignment:
        Map the timeline to Q4 2025 (Oct-Dec) considering Ethiopian business context
        Align with CEO's "Sales & Business Development" focus from daily routine

        OBJECTIVE TO ANALYZE:
        GOAL: {goal_data['title']}
        DESCRIPTION: {goal_data.get('description', '')}
        OUTPUT: {goal_data.get('output', '')}
        DEADLINE: {goal_data.get('deadline', 'Q4 2025')}

        Return ONLY valid JSON in this exact format:
        {{
            "strategic_analysis": {{
                "validation_score": "X/5 criteria met - PASS/NEEDS REFINEMENT",
                "criteria_analysis": {{
                    "clarity_specificity": "Brief analysis",
                    "measurability_verification": "Brief analysis", 
                    "relevance_alignment": "Brief analysis",
                    "actionability_ownership": "Brief analysis",
                    "time_bound": "Brief analysis"
                }},
                "strategic_alignment": "How this advances LeanChems' goals",
                "refined_objective": "Clear, actionable version if refinement was needed",
                "q4_execution_context": "Alignment with Q4 2025 timeline and CEO focus"
            }},
            "tasks": [
                {{
                    "task_description": "Detailed, actionable task description with specific deliverables",
                    "due_date": "2025-10-15",
                    "priority": "high/medium/low",
                    "estimated_hours": 16,
                    "required_skills": [
                        "Advanced negotiation and partnership building",
                        "Chemical product knowledge - Dry Mix/Paint formulations",
                        "Market analysis and competitor intelligence",
                        "Financial modeling and ROI calculation",
                        "Stakeholder management and communication",
                        "Project management and timeline coordination",
                        "Technical sales and specification understanding"
                    ],
                    "success_criteria": "Specific, measurable success indicators",
                    "complexity": "low/medium/high",
                    "strategic_phase": "Phase name (e.g., Partnership Development, Market Validation)",
                    "key_stakeholders": ["CEO", "Sales Team", "Technical Team", "Partners"],
                    "potential_bottlenecks": ["Identified risks or challenges"],
                    "resource_requirements": ["Tools, budget, or support needed"]
                }}
            ]
        }}

        Generate 3-5 elaborated tasks with comprehensive required skills and strategic context.
        """

        print(f"🤖 Sending strategic prompt to AI: {prompt[:200]}...")  # Debug
        
        if ai_meta_id:
            update_ai_progress(ai_meta_id, 40, "Strategic Analysis", "Validating objective against framework")
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "Return ONLY valid JSON. You are a strategic planner for LeanChems Ethiopia."}, {"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000,
            timeout=20
        )
        task_time = time.time() - start_time
        response_text = response.choices[0].message.content.strip()
        
        print(f"🤖 AI Strategic Response: {response_text[:200]}...")  # Debug
        
        ai_analysis = safe_json_parse(response_text, {})
        if not ai_analysis:
            log_ai_error("task_classification", "Invalid JSON response", ai_meta_id, goal['id'], prompt, response_text)
            tasks, message = fallback_task_classification(goal_data)
            return tasks, message, task_time
        
        strategic_analysis = ai_analysis.get('strategic_analysis', {})
        ai_tasks_data = ai_analysis.get('tasks', [])
        if not ai_tasks_data:
            log_ai_error("task_classification", "No tasks generated", ai_meta_id, goal['id'], prompt, response_text)
            tasks, message = fallback_task_classification(goal_data)
            return tasks, message, task_time
        
        supabase = get_supabase_client()
        created_tasks = []
        for task_data in ai_tasks_data[:5]:
            if not task_data.get('task_description'):
                continue
            
            # Enhanced strategic metadata with comprehensive analysis
            strategic_metadata = {
                "required_skills": task_data.get('required_skills', []),
                "success_criteria": task_data.get('success_criteria', ''),
                "complexity": task_data.get('complexity', 'medium'),
                "strategic_analysis": strategic_analysis,
                "strategic_phase": task_data.get('strategic_phase', ''),
                "key_stakeholders": task_data.get('key_stakeholders', []),
                "potential_bottlenecks": task_data.get('potential_bottlenecks', []),
                "resource_requirements": task_data.get('resource_requirements', []),
                "validation_score": strategic_analysis.get('validation_score', ''),
                "q4_execution_context": strategic_analysis.get('q4_execution_context', '')
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
        
        # Update AI meta record with enhanced strategic data
        if ai_meta_id:
            supabase.table("ai_meta").update({
                "source": "chatgpt-strategic-classification",
                "model": "gpt-3.5-turbo",
                "prompt": prompt,
                "input_json": {
                    "goal_id": goal['id'],
                    "goal_title": goal_data['title'],
                    "goal_description": goal_data.get('description', ''),
                    "goal_output": goal_data.get('output', ''),
                    "goal_deadline": goal_data.get('deadline', 'Q4 2025'),
                    "processing_time": task_time,
                    "strategic_framework_applied": True
                },
                "output_json": {
                    "status": "strategic_classification_completed",
                    "tasks_generated": len(created_tasks),
                    "goal_id": goal['id'],
                    "strategic_analysis": strategic_analysis,
                    "tasks": ai_tasks_data,
                    "validation_score": strategic_analysis.get('validation_score', ''),
                    "processing_time": task_time,
                    "q4_alignment": strategic_analysis.get('q4_execution_context', '')
                },
                "raw_response": response_text,
                "confidence": 0.90,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", ai_meta_id).execute()
        
        return created_tasks, f"Created {len(created_tasks)} strategic tasks in {task_time:.1f}s", task_time
    except TimeoutError:
        log_ai_error("task_classification", "Timeout after 20 seconds", ai_meta_id, goal['id'])
        tasks, message = fallback_task_classification(goal_data)
        return tasks, message, time.time() - start_time
    except Exception as e:
        log_ai_error("task_classification", str(e), ai_meta_id, goal['id'])
        tasks, message = fallback_task_classification(goal_data)
        return tasks, message, time.time() - start_time   

    
@task_bp.route('/api/tasks/goals/classify-only', methods=['POST'])
@token_required
def create_goal_classify_only():
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        if not data.get('title'):
            return jsonify({'success': False, 'error': 'Goal title required'}), 400
        
        goal_data = {
            "title": data['title'].strip(),
            "description": data.get('description', '').strip(),
            "output": data.get('output', '').strip(),
            "deadline": data.get('deadline'),
            "department": data.get('department', '').strip(),
            "priority": data.get('priority', 'medium'),
            "status": "draft",
            "created_by": safe_get_employee_id(),
            "assignee_mode": "manual"
        }
        goal_data = {k: v for k, v in goal_data.items() if v is not None and v != ''}
        
        result = supabase.table("objectives").insert(goal_data).execute()
        if not result.data:
            return jsonify({'success': False, 'error': 'Failed to create goal'}), 500
        
        goal = result.data[0]
        ai_tasks, ai_breakdown, ai_processing_time = [], None, 0
        ai_meta_id = None
        
        if data.get('auto_classify') and client:
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
                    "status": "starting"
                },
                "output_json": {
                    "status": "starting", 
                    "progress": 0, 
                    "goal_id": goal['id']
                },
                "confidence": None,
                "created_at": datetime.utcnow().isoformat()
            }
            
            ai_meta_result = supabase.table("ai_meta").insert(initial_ai_meta).execute()
            if ai_meta_result.data:
                ai_meta_id = ai_meta_result.data[0]['id']
                supabase.table("objectives").update({'ai_meta_id': ai_meta_id}).eq('id', goal['id']).execute()
                goal['ai_meta_id'] = ai_meta_id
            
            ai_tasks, ai_breakdown, ai_processing_time = classify_goal_to_tasks_only(goal, data, ai_meta_id)
        
        return jsonify({
            'success': True,
            'goal': goal,
            'ai_tasks': ai_tasks,
            'ai_breakdown': ai_breakdown,
            'ai_processing_time': ai_processing_time,
            'ai_meta_id': ai_meta_id,
            'message': 'Goal created with task classification'
        })
    except Exception as e:
        print(f"❌ Error creating goal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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

def get_general_tasks_objective_id():
    """Return the ID for the General Tasks objective"""
    return "6fa01185-8218-4c8c-b3c9-a66311dfe53f"

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
        
        # If no objective_id provided, use the General Tasks objective
        if not objective_id:
            objective_id = get_general_tasks_objective_id()  # Use your existing General Tasks objective
        
        assigned_to = safe_uuid(data.get('assigned_to'))
        
        # Handle multiple assignees if provided
        assigned_to_multiple = []
        if data.get('assigned_to_multiple'):
            assigned_to_multiple = [safe_uuid(uid) for uid in data.get('assigned_to_multiple', []) if safe_uuid(uid)]
        
        task_data = {
            "task_description": data['task_description'],
            "objective_id": objective_id,
            "assigned_to": assigned_to,
            "assigned_to_multiple": assigned_to_multiple,
            "priority": data.get('priority', 'medium'),
            "due_date": data.get('due_date'),
            "estimated_hours": data.get('estimated_hours', 8),
            "dependencies": data.get('dependencies', []),
            "completion_percentage": data.get('completion_percentage', 0),
            "notes": data.get('notes', '')
        }
        
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
                create_enhanced_task_notification(
                    result.data[0]['id'],
                    "task_assigned",
                    f"New task assigned: {data['task_description'][:100]}...",
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
    """Update task - different permissions for admin vs employee"""
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
                update_data['assigned_to_multiple'] = [safe_uuid(uid) for uid in update_data['assigned_to_multiple'] if safe_uuid(uid)]
            
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
            
            # Create notification for significant changes - EXPANDED to include more field changes
            significant_changes = ['status', 'assigned_to', 'task_description', 'due_date', 'priority', 'estimated_hours']
            if any(field in update_data for field in significant_changes):
                notification_type = "task_updated"
                
                # Create more descriptive message based on what changed
                change_messages = []
                if 'task_description' in update_data:
                    change_messages.append("description updated")
                if 'due_date' in update_data:
                    change_messages.append("due date changed")
                if 'priority' in update_data:
                    change_messages.append("priority changed")
                if 'estimated_hours' in update_data:
                    change_messages.append("estimated hours updated")
                if 'status' in update_data:
                    change_messages.append(f"status changed to {update_data['status']}")
                if 'assigned_to' in update_data:
                    change_messages.append("assignment changed")
                
                change_summary = ", ".join(change_messages)
                message = f"Task updated ({change_summary}): {current_task['task_description'][:50]}..."
                
                # For admin updates, include their name; for employees, keep as None
                assigned_by = g.user.get('name') if user_role in ['admin', 'superadmin'] else None
                
                create_enhanced_task_notification(task_id, notification_type, message, assigned_by=assigned_by)
            return jsonify({'success': True, 'task': result.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Failed to update task'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Add this to your backend task_routes.py

@task_bp.route('/api/tasks/dashboard', methods=['GET'])
@token_required
def get_task_dashboard():
    """Get task dashboard data - FIXED VERSION"""
    try:
        supabase = get_supabase_client()
        
        user_role = g.user.get('role') if hasattr(g, 'user') and g.user else None
        user_employee_id = safe_get_employee_id()
        
        print(f"🔍 Dashboard Debug - Role: {user_role}, Employee ID: {user_employee_id}")
        
        if user_role in ['admin', 'superadmin']:
            # Admin sees all tasks with proper joins
            print("👨‍💼 Admin accessing dashboard - loading all tasks")
            tasks_result = supabase.table("action_plans")\
                .select("*, employees!assigned_to(name, email, department, role), objectives(title, description)")\
                .execute()
        else:
            # Employee sees only their tasks
            if user_employee_id:
                employee_id_str = str(user_employee_id)
                print(f"👤 Employee {employee_id_str} accessing dashboard")
                tasks_result = supabase.table("action_plans")\
                    .select("*, employees!assigned_to(name, email, department, role), objectives(title, description)")\
                    .or_(f"assigned_to.eq.{employee_id_str},assigned_to_multiple.cs.{{{employee_id_str}}}")\
                    .execute()
            else:
                return jsonify({'success': False, 'error': 'Employee ID not found'}), 400
        
        tasks = tasks_result.data if tasks_result.data else []
        
        # Ensure each task has at least an empty employees object
        for task in tasks:
            if 'employees' not in task or task['employees'] is None:
                task['employees'] = {}
            if 'objectives' not in task or task['objectives'] is None:
                task['objectives'] = {}
        
        # Calculate statistics
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get('status') == 'completed'])
        pending_tasks = len([t for t in tasks if t.get('status') == 'not_started'])
        in_progress_tasks = len([t for t in tasks if t.get('status') == 'in_progress'])
        
        # Overdue tasks
        today = datetime.utcnow().date()
        overdue_tasks = len([t for t in tasks if t.get('due_date') and 
                           datetime.fromisoformat(t['due_date'].replace('Z', '')).date() < today and 
                           t.get('status') != 'completed'])
        
        print(f"📊 Dashboard stats - Total: {total_tasks}, Completed: {completed_tasks}, In Progress: {in_progress_tasks}, Pending: {pending_tasks}, Overdue: {overdue_tasks}")
        
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
        print(f"❌ Error in get_task_dashboard: {e}")
        import traceback
        traceback.print_exc()
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
    """Add an update to a task"""
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        
        user_employee_id = safe_get_employee_id()
        
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
        
        # Permission check - employee can only upload to their own tasks
        user_role = g.user.get('role')
        if user_role == 'employee':
            if (task['assigned_to'] != user_employee_id and 
                user_employee_id not in (task.get('assigned_to_multiple') or [])):
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
        
        # In upload_task_file route, replace the notification call with:
        create_file_upload_notification(
            task_id,
            file.filename,
            g.user.get('name', 'Unknown')
        )
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
        
        result = supabase.table("action_plans").select("*, employees!assigned_to(name, email, department, role), objectives(title, description)").eq("id", task_id).execute()
        
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
    """Add a note to a task without file upload, with employee attachment feature - IMPROVED VERSION"""
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
        
        # Permission check - employee can only update their own tasks
        if user_role == 'employee':
            if (task['assigned_to'] != user_employee_id and 
                user_employee_id not in (task.get('assigned_to_multiple') or [])):
                return jsonify({'success': False, 'error': 'Not authorized to update this task'}), 403
        
        notes = data.get('notes', '')
        progress = data.get('progress', task.get('completion_percentage', 0))
        
        if not notes.strip():
            return jsonify({'success': False, 'error': 'Note content is required'}), 400
        
        # IMPROVEMENT 1: Allow attaching any employee without restrictions
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
        
        # Update task progress if different
        if progress != task.get('completion_percentage', 0):
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
        
        # Create enhanced notification with employee attachments
        notification_message = f"Note added to task: {task['task_description'][:50]}..."
        
        # Get admin employee ID for notifications
        admin_employee_id = get_admin_employee_id()
        
        # IMPROVEMENT: Enhanced notification logic for attachments
        recipients = set()
        
        # Always notify admin when employee adds a note
        if user_role == 'employee' and admin_employee_id:
            recipients.add(admin_employee_id)
        
        # Notify ALL attached employees (no restrictions)
        if attached_to:
            recipients.add(attached_to)
        if attached_to_multiple:
            recipients.update(attached_to_multiple)
        
        # Also notify task assignees
        if task.get('assigned_to'):
            recipients.add(task['assigned_to'])
        if task.get('assigned_to_multiple'):
            recipients.update(task['assigned_to_multiple'])
        
        # Remove the current user from recipients (they don't need notification for their own note)
        if user_employee_id in recipients:
            recipients.remove(user_employee_id)
        
        # Create notifications for all recipients
        for recipient in recipients:
            if recipient:
                # Get current user's name for the notification
                current_user_name = "Unknown"
                if hasattr(g, 'user') and g.user:
                    # Try to get the employee name from the database
                    if user_employee_id:
                        employee_result = supabase.table("employees").select("name").eq("id", user_employee_id).execute()
                        if employee_result.data:
                            current_user_name = employee_result.data[0].get('name', 'Unknown')
                    else:
                        current_user_name = g.user.get('name', 'Unknown')
                
                notification_data = {
                    "to_employee": recipient,
                    "channel": "in_app",
                    "message": notification_message,
                    "meta": {
                        "task_id": task_id,
                        "task_description": task['task_description'][:100],
                        "type": "note_added",
                        "added_by": current_user_name,  # NEW: Record who added the note
                        "note_preview": notes[:100] + '...' if len(notes) > 100 else notes,
                        "attached_specifically": True if attached_to or attached_to_multiple else False,
                        "attached_to": attached_to,
                        "attached_to_multiple": attached_to_multiple,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "priority": "normal",
                    "created_at": datetime.utcnow().isoformat(),
                    "is_read": False
                }
                supabase.table("notifications").insert(notification_data).execute()
                print(f"📨 Note notification sent to {recipient}")
        
        return jsonify({
            'success': True, 
            'message': 'Note added successfully',
            'update': update_result.data[0],
            'attached_to': attached_to,
            'attached_to_multiple': attached_to_multiple,
            'notifications_sent_to': len(recipients)
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
    
# ========== RAG IMPLEMENTATION FOR EMPLOYEE RECOMMENDATIONS ==========

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

def create_employee_jd_embeddings(employees):
    """
    Create simple text embeddings for employee JD matching
    This is a simplified version - in production, you'd use proper embedding models
    """
    embeddings = []
    
    for employee in employees:
        # Extract JD text if available
        jd_text = ""
        if employee.get('google_drive_jd'):
            jd_text = extract_text_from_google_drive_url(employee['google_drive_jd'])
        
        # Create embedding profile
        profile_text = f"""
        Name: {employee.get('name', '')}
        Role: {employee.get('role', '')}
        Title: {employee.get('title', '')}
        Department: {employee.get('department', '')}
        Skills: {', '.join(employee.get('skills', []))}
        Experience: {employee.get('experience_years', 0)} years
        Strengths: {', '.join(employee.get('strengths', []))}
        Job Description: {jd_text if jd_text else 'Not available'}
        """
        
        embedding = {
            'employee_id': employee['id'],
            'profile_text': profile_text.lower(),
            'skills': [skill.lower() for skill in employee.get('skills', [])],
            'role': employee.get('role', '').lower(),
            'department': employee.get('department', '').lower(),
            'experience_years': employee.get('experience_years', 0),
            'jd_available': bool(jd_text),
            'jd_text': jd_text
        }
        embeddings.append(embedding)
    
    return embeddings

def semantic_similarity_score(task_description, employee_embedding):
    """
    Calculate semantic similarity score between task and employee profile
    This is a simplified version - in production, use proper embedding models
    """
    task_lower = task_description.lower()
    profile_text = employee_embedding['profile_text']
    
    score = 0
    matches = []
    
    # Skill matching
    for skill in employee_embedding['skills']:
        if skill in task_lower:
            score += 15
            matches.append(f"Skill: {skill}")
    
    # Role matching
    if employee_embedding['role'] and employee_embedding['role'] in task_lower:
        score += 20
        matches.append(f"Role: {employee_embedding['role']}")
    
    # Department matching
    if employee_embedding['department'] and employee_embedding['department'] in task_lower:
        score += 10
        matches.append(f"Department: {employee_embedding['department']}")
    
    # Keyword matching in JD text
    if employee_embedding['jd_text']:
        jd_lower = employee_embedding['jd_text'].lower()
        # Check for task-related keywords in JD
        task_keywords = ['manage', 'develop', 'create', 'implement', 'analyze', 'coordinate', 'lead']
        for keyword in task_keywords:
            if keyword in task_lower and keyword in jd_lower:
                score += 5
                matches.append(f"JD keyword: {keyword}")
    
    # Experience bonus
    if employee_embedding['experience_years'] >= 5:
        score += 15
    elif employee_embedding['experience_years'] >= 3:
        score += 10
    elif employee_embedding['experience_years'] >= 1:
        score += 5
    
    # JD availability bonus
    if employee_embedding['jd_available']:
        score += 5
    
    return min(score, 100), matches

def rag_employee_recommendations(task_description, employees, top_k=5,required_skills=None):
    """
    Advanced RAG-based employee recommendations using JD document analysis
    """
    try:
        print(f"🔍 Starting RAG analysis for {len(employees)} employees...")
        
        recommendations = []
        employees_processed = 0
        
        for employee in employees:
            try:
                employees_processed += 1
                
                # Extract JD text if available - using job_description_url
                jd_text = None
                jd_available = False
                if employee.get('job_description_url'):  # Changed from google_drive_jd
                    print(f"📄 Extracting JD for {employee.get('name')}: {employee.get('job_description_url')[:50]}...")
                    jd_text = extract_text_from_google_drive_url(employee['job_description_url'])
                    jd_available = bool(jd_text)
                    if jd_available:
                        print(f"✅ Successfully extracted JD text for {employee.get('name')} ({len(jd_text)} chars)")
                    else:
                        print(f"❌ Failed to extract JD text for {employee.get('name')}")
                
                # Calculate base score from profile
                base_score = calculate_base_matching_score(task_description, employee,required_skills)
                
                # Calculate RAG-enhanced score if JD available
                rag_score = 0
                key_matches = []
                
                if jd_available and jd_text:
                    rag_score, jd_matches = calculate_jd_enhanced_score(task_description, jd_text, employee)
                    key_matches.extend(jd_matches)
                    # Boost score for JD availability
                    base_score += 15
                
                # Combine scores
                final_score = max(base_score, rag_score) if jd_available else base_score
                
                # Only include if above threshold
                if final_score >= 40:
                    recommendation = {
                        'employee_id': employee['id'],
                        'employee_name': employee['name'],
                        'employee_role': employee.get('role', ''),
                        'employee_department': employee.get('department', ''),
                        'fit_score': final_score,
                        'rag_enhanced_score': rag_score if jd_available else 0,
                        'base_score': base_score,
                        'key_qualifications': key_matches[:8],
                        'experience_years': employee.get('experience_years', 0),
                        'skills_match': [skill for skill in employee.get('skills', []) 
                                       if skill.lower() in task_description.lower()],
                        'jd_available': jd_available,
                        'jd_confidence': 'high' if jd_available and rag_score > 70 else 
                                        'medium' if jd_available and rag_score > 50 else 
                                        'low' if jd_available else 'none',
                        'reason': generate_rag_reason(employee, jd_available, key_matches, final_score),
                        'rag_enhanced': jd_available
                    }
                    recommendations.append(recommendation)
                    
            except Exception as emp_error:
                print(f"⚠️ Error processing employee {employee.get('name')}: {emp_error}")
                continue
        
        # Sort by fit score and return top K
        sorted_recommendations = sorted(recommendations, key=lambda x: x['fit_score'], reverse=True)[:top_k]
        
        print(f"✅ RAG analysis completed: {len(sorted_recommendations)} recommendations from {employees_processed} employees")
        return sorted_recommendations
        
    except Exception as e:
        print(f"❌ RAG recommendation error: {e}")
        return ultra_fast_employee_recommendations(task_description, employees, top_k)
    

def calculate_base_matching_score(task_description, employee, required_skills=None):
    task_lower = task_description.lower()
    score = 0

    # Match against required_skills if provided
    if required_skills:
        employee_skills_lower = [s.lower() for s in employee.get('skills', [])]
        for req_skill in required_skills:
            req = req_skill.lower()
            # Direct skill match
            if req in employee_skills_lower:
                score += 20
            # Partial/fuzzy match (optional)
            elif any(req in emp_skill or emp_skill in req for emp_skill in employee_skills_lower):
                score += 10
    else:
        # Fallback to old logic using task description
        skills = employee.get('skills', [])
        skill_matches = sum(1 for skill in skills if skill.lower() in task_lower)
        score += min(skill_matches * 10, 40)
    
    # Role matching
    role = employee.get('role', '').lower()
    if role and any(keyword in task_lower for keyword in [role]):
        score += 30
    
    # Skills matching
    skills = employee.get('skills', [])
    skill_matches = sum(1 for skill in skills if skill.lower() in task_lower)
    score += min(skill_matches * 10, 40)
    
    # Department matching
    department = employee.get('department', '').lower()
    if department and department in task_lower:
        score += 15
    
    # Experience bonus
    experience = employee.get('experience_years', 0)
    if experience >= 5:
        score += 20
    elif experience >= 3:
        score += 15
    elif experience >= 1:
        score += 10
    
    return min(score, 100)

def calculate_jd_enhanced_score(task_description, jd_text, employee):
    """Calculate JD-enhanced matching score"""
    task_lower = task_description.lower()
    jd_lower = jd_text.lower()
    
    score = 0
    matches = []
    
    # Check for task keywords in JD
    task_keywords = [
        'manage', 'develop', 'create', 'implement', 'analyze', 
        'coordinate', 'lead', 'design', 'build', 'execute'
    ]
    
    for keyword in task_keywords:
        if keyword in task_lower and keyword in jd_lower:
            score += 8
            matches.append(f"JD keyword: {keyword}")
    
    # Check for specific skills in JD
    skills = employee.get('skills', [])
    for skill in skills:
        if skill.lower() in jd_lower and skill.lower() in task_lower:
            score += 12
            matches.append(f"JD skill: {skill}")
    
    # Check for role-specific terminology
    role_terms = {
        'developer': ['code', 'programming', 'software', 'debug'],
        'manager': ['lead', 'manage', 'coordinate', 'oversee'],
        'analyst': ['analyze', 'data', 'report', 'research'],
        'designer': ['design', 'create', 'ui', 'ux', 'visual']
    }
    
    for role, terms in role_terms.items():
        if role in employee.get('role', '').lower():
            for term in terms:
                if term in task_lower and term in jd_lower:
                    score += 10
                    matches.append(f"Role term: {term}")
    
    return min(score, 100), matches

def generate_rag_reason(employee, jd_available, key_matches, score):
    """Generate reasoning for RAG recommendations"""
    base_reason = f"{employee['name']} ({employee.get('role', 'N/A')}) scored {score}%"
    
    if jd_available and key_matches:
        match_details = ", ".join(key_matches[:3])
        return f"{base_reason} based on JD analysis matching: {match_details}"
    elif jd_available:
        return f"{base_reason} (JD document analyzed but limited matches found)"
    else:
        return f"{base_reason} based on profile matching (no JD document available)"
    
def enhanced_process_employee_recommendations_for_task(task, employees, ai_meta_id):
    """
    Complete RAG-enhanced employee recommendation process
    """
    try:
        supabase = get_supabase_client()
        start_time = time.time()
        
        print(f"👥 Processing RAG-enhanced employee recommendations for task: {task['task_description'][:50]}...")
        
        # Step 1: Update progress - Starting JD extraction
        update_data = {
            "output_json": {
                "status": "processing",
                "progress": 20,
                "current_activity": "Extracting JD documents from Google Drive",
                "task_id": task['id'],
                "employees_analyzed": len(employees),
                "rag_enhanced": True
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(update_data).eq("id", ai_meta_id).execute()
        
        # Step 2: Extract JD documents and create embeddings
        employees_with_jd = []
        for emp in employees:
            if emp.get('google_drive_jd'):
                jd_text = extract_text_from_google_drive_url(emp['google_drive_jd'])
                if jd_text:
                    emp['jd_text'] = jd_text
                    employees_with_jd.append(emp)
        
        # Step 3: Update progress - JD analysis
        update_data = {
            "output_json": {
                "status": "processing",
                "progress": 40,
                "current_activity": "Analyzing JD documents and creating semantic matches",
                "task_id": task['id'],
                "employees_with_jd": len(employees_with_jd),
                "jd_analysis_complete": True
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(update_data).eq("id", ai_meta_id).execute()
        
        # Step 4: Get RAG-based recommendations
        rag_recommendations = rag_employee_recommendations(
            task['task_description'], 
            employees, 
            top_k=5,
            required_skills=required_skills
        )
        
        # Step 5: Update progress - AI analysis with RAG context
        update_data = {
            "output_json": {
                "status": "processing",
                "progress": 70,
                "current_activity": "AI analyzing RAG-enhanced matches",
                "task_id": task['id'],
                "rag_recommendations_count": len(rag_recommendations),
                "top_rag_score": rag_recommendations[0]['fit_score'] if rag_recommendations else 0
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(update_data).eq("id", ai_meta_id).execute()
        
        # Step 6: Prepare enhanced AI prompt with RAG results
        strategic_meta = task.get('strategic_metadata', {})
        required_skills = strategic_meta.get('required_skills', [])
        task_complexity = strategic_meta.get('complexity', 'medium')
        
        # Prepare RAG details for AI context
        rag_details = []
        for rec in rag_recommendations[:3]:  # Top 3 RAG matches
            rag_details.append({
                'employee_name': rec['employee_name'],
                'fit_score': rec['fit_score'],
                'key_matches': rec['key_qualifications'],
                'jd_available': rec['jd_available'],
                'skills_matches': rec.get('skills_match', [])
            })
        
        # Enhanced AI prompt with RAG context
        prompt = f"""
        As an HR and talent matching expert, analyze this task and recommend the best employees using RAG-enhanced analysis that has already analyzed their Job Descriptions.

        TASK ANALYSIS:
        - Description: {task['task_description']}
        - Required Skills: {', '.join(required_skills) if required_skills else 'Not specified'}
        - Complexity: {task_complexity}
        - Priority: {task.get('priority', 'medium')}
        - Estimated Hours: {task.get('estimated_hours', 8)}
        - Goal: {task.get('objectives', {}).get('title', 'Not specified')}

        RAG-ENHANCED ANALYSIS RESULTS (Based on JD Document Analysis):
        The following employees showed strong matches based on their Job Description analysis:
        {json.dumps(rag_details, indent=2)}

        FINAL RECOMMENDATION INSTRUCTIONS:
        1. Consider the RAG-enhanced matching scores from JD analysis
        2. Evaluate skills alignment with task requirements
        3. Consider role relevance and experience level
        4. Factor in department alignment and workload
        5. Provide detailed reasoning for each recommendation

        Return ONLY valid JSON with your top 3 recommendations:

        {{
            "recommendations": [
                {{
                    "employee_id": "uuid-string-here",
                    "employee_name": "Employee Name",
                    "fit_score": 85,
                    "rag_enhanced_score": 90,
                    "skills_match": 90,
                    "role_alignment": 80,
                    "experience_suitability": 75,
                    "strengths_alignment": 85,
                    "jd_based_confidence": "high/medium/low",
                    "key_qualifications": ["Qualification 1", "Qualification 2"],
                    "reason": "Detailed explanation including specific JD-based insights",
                    "potential_gaps": ["Any skill or experience gaps"],
                    "development_opportunity": true/false,
                    "confidence": "high/medium/low"
                }}
            ],
            "analysis_summary": "Brief summary of why these employees are the best fit",
            "total_employees_considered": {len(employees)},
            "employees_with_jd": {len(employees_with_jd)},
            "rag_enhanced": true,
            "jd_analysis_impact": "How JD analysis improved the recommendations"
        }}
        """
        
        # Step 7: Call AI for final recommendations
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an HR expert specializing in talent matching using RAG-enhanced analysis of Job Descriptions. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
            timeout=30
        )
        
        response_text = response.choices[0].message.content.strip()
        ai_recommendations = safe_json_parse(response_text, {})
        
        processing_time = time.time() - start_time
        
        # Step 8: Update task with enhanced recommendations
        strategic_meta = task.get('strategic_metadata', {})
        strategic_meta['ai_recommendations'] = ai_recommendations.get('recommendations', [])
        strategic_meta['employee_recommendations_available'] = True
        strategic_meta['recommendations_analysis'] = ai_recommendations.get('analysis_summary', '')
        strategic_meta['recommendations_generated_at'] = datetime.utcnow().isoformat()
        strategic_meta['total_employees_considered'] = ai_recommendations.get('total_employees_considered', len(employees))
        strategic_meta['rag_enhanced'] = True
        strategic_meta['employees_with_jd'] = ai_recommendations.get('employees_with_jd', len(employees_with_jd))
        strategic_meta['rag_details'] = rag_details
        strategic_meta['jd_analysis_impact'] = ai_recommendations.get('jd_analysis_impact', 'JD documents provided additional context for matching')
        
        update_result = supabase.table("action_plans").update({
            "strategic_metadata": strategic_meta
        }).eq("id", task['id']).execute()
        
        # Step 9: Final update to AI meta
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
                "rag_enhanced": True,
                "employees_with_jd": strategic_meta['employees_with_jd'],
                "jd_analysis_impact": strategic_meta['jd_analysis_impact'],
                "top_recommendation": strategic_meta['ai_recommendations'][0] if strategic_meta['ai_recommendations'] else None
            },
            "confidence": 0.90,
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("ai_meta").update(final_update).eq("id", ai_meta_id).execute()
        
        print(f"✅ RAG-enhanced employee recommendations completed in {processing_time:.2f}s")
        print(f"📊 Generated {len(strategic_meta['ai_recommendations'])} recommendations")
        print(f"📄 Analyzed {strategic_meta['employees_with_jd']} JD documents")
        
        return True
        
    except Exception as e:
        error_msg = f"Error in RAG employee recommendations: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Fallback to standard recommendations
        try:
            print("🔄 Falling back to standard recommendations...")
            return process_employee_recommendations_for_task(task, employees, ai_meta_id)
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            # Update AI meta with error
            try:
                supabase.table("ai_meta").update({
                    "output_json": {
                        "status": "error",
                        "error": error_msg,
                        "fallback_error": str(fallback_error),
                        "progress": 0
                    },
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", ai_meta_id).execute()
            except Exception as update_error:
                print(f"❌ Failed to update AI meta with error: {update_error}")
            return False
        

# Update the route to use enhanced RAG method
@task_bp.route('/api/tasks/<task_id>/generate-rag-recommendations', methods=['POST'])
@token_required
@admin_required
def generate_rag_employee_recommendations(task_id):
    """Generate RAG-enhanced employee recommendations for a specific task"""
    try:
        supabase = get_supabase_client()
        
        # Get task details
        task_result = supabase.table("action_plans").select("*, objectives(title)").eq("id", task_id).execute()
        if not task_result.data:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = task_result.data[0]
        
        # Get all active employees with JD links
        employees_result = supabase.table("employees").select(
            "id, name, role, title, skills, experience_years, department, strengths,job_description_url"
        ).eq("is_active", True).execute()
        
        employees = employees_result.data if employees_result.data else []
        
        if not employees:
            return jsonify({'success': False, 'error': 'No active employees found'}), 400
        
        # Create AI meta record for RAG recommendations
        ai_meta_data = {
            "source": "rag-employee-recommendations",
            "model": "gpt-3.5-turbo",
            "input_json": {
                "task_id": task_id,
                "task_description": task['task_description'],
                "employees_count": len(employees),
                "employees_with_jd": len([emp for emp in employees if emp.get('job_description_url')]),
                "status": "starting",
                "rag_enhanced": True
            },
            "output_json": {
                "status": "processing",
                "progress": 0,
                "current_activity": "Starting RAG-enhanced employee recommendations",
                "task_id": task_id,
                "rag_enhanced": True
            },
            "created_at": datetime.utcnow().isoformat()
        }
        
        ai_meta_result = supabase.table("ai_meta").insert(ai_meta_data).execute()
        if not ai_meta_result.data:
            return jsonify({'success': False, 'error': 'Failed to create AI meta record'}), 500
        
        ai_meta_id = ai_meta_result.data[0]['id']
        
        # Start RAG-enhanced recommendation process in background
        threading.Thread(
            target=enhanced_process_employee_recommendations_for_task,
            args=(task, employees, ai_meta_id),
            daemon=True
        ).start()
        
        return jsonify({
            'success': True, 
            'ai_meta_id': ai_meta_id,
            'message': 'RAG-enhanced employee recommendations processing started',
            'task_id': task_id,
            'rag_enhanced': True,
            'employees_count': len(employees),
            'employees_with_jd': len([emp for emp in employees if emp.get('job_description_url')])
        })
        
    except Exception as e:
        error_msg = f"Error starting RAG employee recommendations: {str(e)}"
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