import os
from functools import wraps
from flask import request, jsonify, g  # Add 'g' import
import jwt
from datetime import datetime, timedelta
import hashlib

class AuthManager:
    def __init__(self):
        self.secret_key = os.getenv('FLASK_SECRET_KEY')
        self.superadmin_email = os.getenv('SUPERADMIN_EMAIL')
        self.superadmin_password = os.getenv('SUPERADMIN_PASSWORD')

    def hash_password(self, password: str) -> str:
        """Simple password hashing"""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, email: str, password: str) -> dict:
        """Unified authentication for both admin and employees - BACKEND VERSION"""
        print(f"🔐 Auth attempt: {email}")
        
        # Initialize supabase client
        try:
            from supabase import create_client
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
            
            if not supabase_url or not supabase_key:
                return {'success': False, 'error': 'Database not configured'}
                
            supabase = create_client(supabase_url, supabase_key)
        except Exception as e:
            return {'success': False, 'error': f'Database connection failed: {str(e)}'}
        
        # First try superadmin authentication
        if email.strip().lower() == self.superadmin_email.lower() and password == self.superadmin_password:
            # Get or create admin employee record
            admin_employee_id = self.get_or_create_admin_employee(supabase)
            
            token = self.generate_token(email, 'superadmin', employee_id=admin_employee_id)
            return {
                'success': True,
                'token': token,
                'user': {
                    'email': email, 
                    'role': 'superadmin',
                    'employee_id': admin_employee_id,
                    'name': 'System Administrator'
                },
                'expires_in': 365 * 24 * 3600
            }
        
        # For employees, check password in database
        try:
            
            # Check if employee exists
            employee_data = supabase.table("employees").select("*").eq("email", email).execute()
            
            if employee_data.data:
                employee = employee_data.data[0]
                
                # Check password
                password_valid = False
                hashed_input = self.hash_password(password)
                
                if employee.get('password'):
                    # Check against stored password
                    password_valid = (employee['password'] == hashed_input)
                else:
                    # Check against default passwords (employee ID or configurable default)
                    default_passwords = [
                        str(employee['id']),                     # Employee ID
                        os.getenv('DEFAULT_PASSWORD'),   # Fallback to '1234' if not set
                    ]
                    password_valid = password in default_passwords
                
                if password_valid:
                    if not employee.get('is_active', True):
                        return {'success': False, 'error': 'Employee account is deactivated'}
                    
                    token = self.generate_token(email, 'employee', employee_id=employee['id'])
                    
                    return {
                        'success': True,
                        'token': token,
                        'user': {
                            'email': email,
                            'role': 'employee',
                            'employee_id': employee['id'],
                            'name': employee.get('name', 'Employee')
                        },
                        'expires_in': 365 * 24 * 3600
                    }
                else:
                    return {'success': False, 'error': 'Invalid email or password'}
            
            return {'success': False, 'error': 'Invalid email or password'}
            
        except Exception as e:
            print(f"Auth error: {e}")
            return {'success': False, 'error': 'Authentication service unavailable'}

    def change_password(self, user_info: dict, current_password: str, new_password: str) -> dict:
        """Change password for the user - BACKEND VERSION"""
        try:
            from supabase import create_client
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
            
            if not supabase_url or not supabase_key:
                return {'success': False, 'error': 'Database not configured'}
                
            supabase = create_client(supabase_url, supabase_key)
            
            if user_info.get('role') == 'superadmin':
                # Handle superadmin password change
                if current_password != self.superadmin_password:
                    return {'success': False, 'error': 'Current password is incorrect'}
                return {'success': False, 'error': 'Changing superadmin password is not allowed in demo'}
                
            else:
                # Handle employee password change
                employee_id = user_info.get('employee_id')
                if not employee_id:
                    return {'success': False, 'error': 'Employee ID not found'}
                
                # Get employee data
                employee_data = supabase.table("employees").select("*").eq("id", employee_id).execute()
                if not employee_data.data:
                    return {'success': False, 'error': 'Employee not found'}
                
                employee = employee_data.data[0]
                
                # Verify current password
                current_password_valid = False
                hashed_current = self.hash_password(current_password)
                
                if employee.get('password'):
                    current_password_valid = (employee['password'] == hashed_current)
                else:
                    default_passwords = [str(employee['id']), '1234']
                    current_password_valid = current_password in default_passwords
                
                if not current_password_valid:
                    return {'success': False, 'error': 'Current password is incorrect'}
                
                # Update password
                hashed_new = self.hash_password(new_password)
                update_result = supabase.table("employees").update({
                    'password': hashed_new,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', employee_id).execute()
                
                if update_result.data:
                    return {'success': True, 'message': 'Password updated successfully'}
                else:
                    return {'success': False, 'error': 'Failed to update password'}
                
        except Exception as e:
            print(f"Password change error: {e}")
            return {'success': False, 'error': str(e)}

    def get_or_create_admin_employee(self, supabase):
        """Get or create admin employee record and return employee ID"""
        try:
            # First try to find existing admin employee
            admin_result = supabase.table("employees").select("id").eq("email", "admin@leanchem.com").execute()
            
            if admin_result.data:
                return admin_result.data[0]['id']
            
            # If not found, create admin employee record
            admin_employee_data = {
                "name": "System Administrator",
                "email": "admin@leanchem.com",
                "role": "Administrator",
                "department": "IT",
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            create_result = supabase.table("employees").insert(admin_employee_data).execute()
            
            if create_result.data:
                print(f"✅ Created admin employee record with ID: {create_result.data[0]['id']}")
                return create_result.data[0]['id']
            else:
                print("❌ Failed to create admin employee record")
                return None
                
        except Exception as e:
            print(f"❌ Error getting/creating admin employee: {e}")
            return None

    def generate_token(self, email: str, role: str, employee_id: str = None) -> str:
        """Generate JWT token"""
        payload = {
            'email': email,
            'role': role,
            'employee_id': employee_id,
            'exp': datetime.utcnow() + timedelta(days=365),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def verify_token(self, token: str) -> dict:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return {
                'success': True, 
                'email': payload['email'],
                'role': payload.get('role'),
                'employee_id': payload.get('employee_id')
            }
        except jwt.ExpiredSignatureError:
            return {'success': False, 'error': 'Token expired'}
        except jwt.InvalidTokenError:
            return {'success': False, 'error': 'Invalid token'}

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if authorization header is present
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Handle both "Bearer token" and just "token" formats
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                else:
                    token = auth_header
                print(f"🔐 Token found: {token[:20]}...")
            except Exception as e:
                print(f"❌ Token parsing error: {e}")
                return jsonify({'success': False, 'error': 'Invalid token format'}), 401
        else:
            print("❌ No Authorization header found")
            return jsonify({'success': False, 'error': 'Token is missing'}), 401
        
        if not token:
            print("❌ No token provided in request")
            return jsonify({'success': False, 'error': 'Token is missing'}), 401
        
        try:
            auth_manager = AuthManager()
            verification = auth_manager.verify_token(token)
            
            if not verification['success']:
                print(f"❌ Token verification failed: {verification.get('error')}")
                return jsonify({'success': False, 'error': verification['error']}), 401
            
            # PROPERLY set g.user for use in routes
            g.user = {
                'email': verification['email'],
                'role': verification.get('role'),
                'employee_id': verification.get('employee_id')
            }
            
            print(f"✅ Token validated for user: {g.user['email']} (role: {g.user['role']})")
            
        except Exception as e:
            print(f"❌ Token validation error: {e}")
            return jsonify({'success': False, 'error': 'Token validation failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if authorization header is present
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Handle both "Bearer token" and just "token" formats
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                else:
                    token = auth_header
                print(f"🔐 Admin token found: {token[:20]}...")
            except Exception as e:
                print(f"❌ Admin token parsing error: {e}")
                return jsonify({'success': False, 'error': 'Invalid token format'}), 401
        else:
            print("❌ No Authorization header found for admin route")
            return jsonify({'success': False, 'error': 'Token is missing'}), 401
        
        if not token:
            print("❌ No token provided in admin request")
            return jsonify({'success': False, 'error': 'Token is missing'}), 401
        
        try:
            auth_manager = AuthManager()
            verification = auth_manager.verify_token(token)
            
            if not verification['success']:
                print(f"❌ Admin token verification failed: {verification.get('error')}")
                return jsonify({'success': False, 'error': verification['error']}), 401
            
            # Check if user has admin role
            user_role = verification.get('role')
            if user_role not in ['superadmin', 'admin']:
                print(f"❌ Admin access denied for role: {user_role}")
                return jsonify({'success': False, 'error': 'Admin access required'}), 403
            
            # PROPERLY set g.user for use in routes
            g.user = {
                'email': verification['email'],
                'role': user_role,
                'employee_id': verification.get('employee_id')
            }
            
            print(f"✅ Admin access granted for: {g.user['email']} (role: {g.user['role']})")
            
        except Exception as e:
            print(f"❌ Admin token validation error: {e}")
            return jsonify({'success': False, 'error': 'Token validation failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated