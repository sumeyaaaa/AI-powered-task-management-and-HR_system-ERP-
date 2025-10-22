from flask import Blueprint, request, jsonify
import os
from datetime import datetime
from auth import token_required
import secrets
import uuid
from werkzeug.utils import secure_filename

# Configure allowed file extensions and upload folder
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Initialize Supabase client
def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        raise Exception("Supabase credentials not configured")
    
    from supabase import create_client
    return create_client(supabase_url, supabase_key)

employee_bp = Blueprint('employees', __name__)

def generate_temp_password(length: int = 12) -> str:
    return secrets.token_urlsafe(length)[:length]

@employee_bp.route('/api/employees', methods=['GET'])
@token_required
def get_employees():
    """Get all employees with proper table structure"""
    try:
        supabase = get_supabase_client()
        result = supabase.table("employees").select("*").order("created_at", desc=True).execute()
        employees = result.data if result.data else []
        return jsonify({'success': True, 'employees': employees})
    except Exception as e:
        print(f"❌ Error fetching employees: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@employee_bp.route('/api/employees', methods=['POST'])
@token_required
def create_employee():
    """Create new employee with all fields"""
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        
        print(f"📥 Create employee data: {data}")
        
        # Validate required fields
        if not data.get('name') or not data.get('email'):
            return jsonify({'success': False, 'error': 'Name and email are required'}), 400
        
        # Check if employee already exists
        existing = supabase.table("employees").select("*").eq("email", data['email']).execute()
        if existing.data:
            return jsonify({'success': False, 'error': 'Employee with this email already exists'}), 400
        
        # Create employee record with all fields
        employee_data = {
            "name": data['name'].strip(),
            "email": data['email'].strip().lower(),
            "role": data.get('role', '').strip(),
            "department": data.get('department', '').strip(),
            "title": data.get('title', '').strip(),
            "bio": data.get('bio', '').strip(),
            "linkedin_url": data.get('linkedin_url', '').strip(),
            "telegram_chat_id": data.get('telegram_chat_id', '').strip(),
            "area_of_development": data.get('area_of_development', '').strip(),
            "skills": data.get('skills', []),
            "strengths": data.get('strengths', []),
            "experience_years": data.get('experience_years'),
            "location": data.get('location', '').strip(),
            "is_active": True,
        }
        
        # Remove empty fields
        employee_data = {k: v for k, v in employee_data.items() if v is not None and v != ''}
        
        print(f"📤 Inserting employee: {employee_data}")
        
        result = supabase.table("employees").insert(employee_data).execute()
        
        if result.data:
            employee = result.data[0]
            return jsonify({
                'success': True, 
                'employee': employee,
                'message': 'Employee created successfully',
                'login_info': {
                    'email': employee['email'],
                    'default_passwords': [str(employee['id']), '1234'],
                    'note': 'Employee can use Employee ID or 1234 as initial password'
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create employee record'}), 500
            
    except Exception as e:
        print(f"❌ Error creating employee: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@employee_bp.route('/api/employees/<employee_id>', methods=['GET'])
@token_required
def get_employee(employee_id):
    """Get specific employee details"""
    try:
        supabase = get_supabase_client()
        result = supabase.table("employees").select("*").eq("id", employee_id).execute()
        
        if result.data:
            return jsonify({'success': True, 'employee': result.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@employee_bp.route('/api/employees/<employee_id>', methods=['PUT'])
@token_required
def update_employee(employee_id):
    """Update employee details with all fields"""
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        
        print(f"📥 Update employee {employee_id}: {data}")
        
        # Build update data with all editable fields
        update_data = {}
        fields = ['name', 'role', 'department', 'title', 'bio', 'linkedin_url', 
                 'telegram_chat_id', 'area_of_development', 'skills', 'strengths', 
                 'experience_years', 'location', 'is_active']
        
        for field in fields:
            if field in data:
                update_data[field] = data[field]
        
        if not update_data:
            return jsonify({'success': False, 'error': 'No data to update'}), 400
        
        # Add updated_at timestamp
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        result = supabase.table("employees").update(update_data).eq("id", employee_id).execute()
        
        if result.data:
            return jsonify({'success': True, 'employee': result.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
            
    except Exception as e:
        print(f"❌ Error updating employee: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@employee_bp.route('/api/employees/<employee_id>', methods=['DELETE'])
@token_required
def delete_employee(employee_id):
    """Delete employee (soft delete)"""
    try:
        supabase = get_supabase_client()
        result = supabase.table("employees").update({
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", employee_id).execute()
        
        if result.data:
            return jsonify({'success': True, 'message': 'Employee deactivated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@employee_bp.route('/api/employees/<employee_id>/permanent', methods=['DELETE'])
@token_required
def permanent_delete_employee(employee_id):
    """Permanently delete employee from database"""
    try:
        supabase = get_supabase_client()
        
        # First check if employee exists
        existing = supabase.table("employees").select("*").eq("id", employee_id).execute()
        if not existing.data:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
        
        print(f"🗑️ Permanent deletion requested for employee: {employee_id}")
        
        # Permanent delete from database
        result = supabase.table("employees").delete().eq("id", employee_id).execute()
        
        if result.data:
            print(f"✅ Employee {employee_id} permanently deleted")
            return jsonify({
                'success': True, 
                'message': 'Employee permanently deleted from system'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete employee'}), 500
            
    except Exception as e:
        print(f"❌ Error in permanent deletion: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@employee_bp.route('/api/employees/<employee_id>/reset-password', methods=['POST'])
@token_required
def reset_employee_password(employee_id):
    """Reset employee password to default (admin only)"""
    try:
        supabase = get_supabase_client()
        
        # Get employee
        employee_data = supabase.table("employees").select("*").eq("id", employee_id).execute()
        if not employee_data.data:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
        
        # Reset password (set to NULL so they can use default passwords)
        result = supabase.table("employees").update({
            'password': None,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', employee_id).execute()
        
        if result.data:
            return jsonify({
                'success': True, 
                'message': 'Password reset successfully',
                'default_passwords': [employee_id, '1234']
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to reset password'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@employee_bp.route('/api/employees/<employee_id>/upload-photo', methods=['POST'])
@token_required
def upload_employee_photo(employee_id):
    """Upload employee photo with corrected response handling"""
    try:
        supabase = get_supabase_client()
        
        # Check if employee exists
        employee_data = supabase.table("employees").select("*").eq("id", employee_id).execute()
        if not employee_data.data:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
        
        # Check if file is present
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['photo']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400
        
        # Validate file size
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)
        
        if file_length > MAX_FILE_SIZE:
            return jsonify({'success': False, 'error': 'File too large. Maximum size is 5MB'}), 400
        
        # Generate unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{employee_id}_{uuid.uuid4().hex}.{file_extension}"
        
        # Upload to Supabase Storage
        bucket_name = "employee-photos"
        
        try:
            # Check and create bucket if needed
            try:
                buckets_response = supabase.storage.list_buckets()
                # Handle different response formats
                if hasattr(buckets_response, 'buckets'):
                    buckets = buckets_response.buckets
                elif isinstance(buckets_response, list):
                    buckets = buckets_response
                else:
                    buckets = buckets_response.data if hasattr(buckets_response, 'data') else []
                
                bucket_exists = any(bucket.name == bucket_name if hasattr(bucket, 'name') else bucket.get('name') == bucket_name for bucket in buckets)
                
                if not bucket_exists:
                    print(f"📦 Creating bucket: {bucket_name}")
                    create_result = supabase.storage.create_bucket(bucket_name, {
                        'public': True,
                        'file_size_limit': MAX_FILE_SIZE,
                        'allowed_mime_types': ['image/*']
                    })
                    print(f"✅ Bucket creation result: {create_result}")
            except Exception as bucket_error:
                print(f"⚠️ Bucket check/create warning: {bucket_error}")
            
            # Upload file
            print(f"📤 Uploading file to bucket: {bucket_name}")
            file_data = file.read()
            
            # Upload with proper error handling for new response format
            upload_result = supabase.storage.from_(bucket_name).upload(
                unique_filename, 
                file_data,
                {"content-type": file.content_type}
            )
            
            print(f"📄 Upload result type: {type(upload_result)}")
            print(f"📄 Upload result: {upload_result}")
            
            # Handle different response formats
            if hasattr(upload_result, 'error') and upload_result.error:
                error_msg = upload_result.error
                print(f"❌ Upload error: {error_msg}")
                return jsonify({'success': False, 'error': f"Upload failed: {error_msg}"}), 500
            elif isinstance(upload_result, dict) and upload_result.get('error'):
                error_msg = upload_result['error']
                print(f"❌ Upload error: {error_msg}")
                return jsonify({'success': False, 'error': f"Upload failed: {error_msg}"}), 500
            elif upload_result is None:
                return jsonify({'success': False, 'error': "Upload failed: No response from storage"}), 500
            
            # If we get here, upload was successful
            print(f"✅ File uploaded successfully")
            
            # Get public URL
            try:
                public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
                photo_url = public_url
                print(f"🌐 Public URL: {photo_url}")
            except Exception as url_error:
                print(f"❌ Error getting public URL: {url_error}")
                # Construct URL manually if needed
                supabase_url = os.getenv('SUPABASE_URL')
                photo_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{unique_filename}"
                print(f"🔗 Manual URL: {photo_url}")
            
            # Update employee record with photo URL
            update_result = supabase.table("employees").update({
                'photo_url': photo_url,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', employee_id).execute()
            
            if hasattr(update_result, 'data') and update_result.data:
                return jsonify({
                    'success': True, 
                    'photo_url': photo_url,
                    'message': 'Photo uploaded successfully'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to update employee record'}), 500
                
        except Exception as storage_error:
            print(f"❌ Storage error: {str(storage_error)}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': f"Storage error: {str(storage_error)}"}), 500
            
    except Exception as e:
        print(f"❌ Error uploading photo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@employee_bp.route('/api/employees/<employee_id>/remove-photo', methods=['DELETE'])
@token_required
def remove_employee_photo(employee_id):
    """Remove employee photo with corrected response handling"""
    try:
        supabase = get_supabase_client()
        
        # Get current photo URL
        employee_data = supabase.table("employees").select("photo_url").eq("id", employee_id).execute()
        if not employee_data.data:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
        
        current_photo_url = employee_data.data[0].get('photo_url')
        
        if current_photo_url:
            # Extract filename from URL and delete from storage
            try:
                filename = current_photo_url.split('/')[-1]
                bucket_name = "employee-photos"
                
                # Remove file from storage
                remove_result = supabase.storage.from_(bucket_name).remove([filename])
                
                print(f"🗑️ Remove result type: {type(remove_result)}")
                print(f"🗑️ Remove result: {remove_result}")
                
                # Handle different response formats
                if hasattr(remove_result, 'error') and remove_result.error:
                    print(f"⚠️ Could not delete file from storage: {remove_result.error}")
                elif isinstance(remove_result, dict) and remove_result.get('error'):
                    print(f"⚠️ Could not delete file from storage: {remove_result['error']}")
                else:
                    print(f"✅ File removed from storage: {filename}")
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not delete file from storage: {e}")
        
        # Update employee record
        update_result = supabase.table("employees").update({
            'photo_url': None,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', employee_id).execute()
        
        if hasattr(update_result, 'data') and update_result.data:
            return jsonify({'success': True, 'message': 'Photo removed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update employee record'}), 500
            
    except Exception as e:
        print(f"❌ Error removing photo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
# In employee_route.py - Remove JD file upload endpoints and keep only:
@employee_bp.route('/api/employees/<employee_id>/jd-link', methods=['PUT'])
@token_required
def update_employee_jd_link(employee_id):
    """Update only the job description Google Drive link"""
    try:
        supabase = get_supabase_client()
        data = request.get_json()
        
        print(f"📥 Update JD link for employee {employee_id}: {data}")
        
        jd_link = data.get('job_description_url', '').strip()
        
        # Validate Google Drive link format (optional)
        if jd_link and not jd_link.startswith('https://drive.google.com/'):
            print(f"⚠️ Warning: This doesn't look like a Google Drive link: {jd_link}")
            # Don't return error, just warn but still save
        
        # Check if employee exists
        employee_data = supabase.table("employees").select("*").eq("id", employee_id).execute()
        if not employee_data.data:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
        
        # Update only the JD link
        update_data = {
            'job_description_url': jd_link if jd_link else None,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = supabase.table("employees").update(update_data).eq("id", employee_id).execute()
        
        if hasattr(result, 'data') and result.data:
            return jsonify({
                'success': True, 
                'message': 'Job description link updated successfully',
                'job_description_url': jd_link
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update employee record'}), 500
            
    except Exception as e:
        print(f"❌ Error updating JD link: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
