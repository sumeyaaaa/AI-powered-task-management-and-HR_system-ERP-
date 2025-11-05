from flask import Flask, jsonify, request
from flask_cors import CORS
from .auth import AuthManager, token_required, admin_required
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
    
    CORS(app)
    
    # Import and register employee routes
    try:
        from .employee_routes_fixed import employee_bp
        app.register_blueprint(employee_bp)
        print("✅ Employee routes registered successfully")
    except Exception as e:
        print(f"❌ Failed to register employee routes: {e}")
    
    # Health check
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'service': 'ERP Backend API'})
    
    # Import and register task routes
    try:
        from .task_routes import task_bp
        app.register_blueprint(task_bp)
        print("✅ Task routes registered successfully")
    except Exception as e:
        print(f"❌ Failed to register Task routes: {e}")

    # OLD NOTIFICATION ROUTES (keep for compatibility but they might not work for admin)
    try:
        from .notification_routes import notification_bp
        app.register_blueprint(notification_bp)
        print("✅ OLD Notification routes registered successfully")
    except Exception as e:
        print(f"❌ Failed to register OLD notification routes: {e}")



    # Unified login endpoint
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        auth_manager = AuthManager()
        result = auth_manager.authenticate(data['email'], data['password'])
        
        return jsonify(result) if result['success'] else (jsonify(result), 401)
    
    # Change password endpoint
    @app.route('/api/auth/change-password', methods=['POST'])
    @token_required
    def change_password():
        data = request.get_json()
        if not data or not data.get('current_password') or not data.get('new_password'):
            return jsonify({'success': False, 'error': 'Current and new password required'}), 400
        
        token = request.headers.get('Authorization').replace('Bearer ', '')
        auth_manager = AuthManager()
        verification = auth_manager.verify_token(token)
        
        if not verification['success']:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        result = auth_manager.change_password(verification, data['current_password'], data['new_password'])
        return jsonify(result)
    
    # Employee profile endpoint
    @app.route('/api/employee/profile', methods=['GET'])
    @token_required
    def get_employee_profile():
        """Get employee profile (for employees) or all employees (for admin)"""
        try:
            token = request.headers.get('Authorization').replace('Bearer ', '')
            auth_manager = AuthManager()
            verification = auth_manager.verify_token(token)
            
            if not verification['success']:
                return jsonify({'success': False, 'error': 'Invalid token'}), 401
            
            from supabase import create_client
            supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
            
            if verification.get('role') == 'employee':
                employee_id = verification.get('employee_id')
                if not employee_id:
                    return jsonify({'success': False, 'error': 'Employee ID not found'}), 400
                
                result = supabase.table("employees").select("*").eq("id", employee_id).execute()
                
                if result.data:
                    employee = result.data[0]
                    employee.pop('auth_uid', None)
                    return jsonify({'success': True, 'employee': employee})
                else:
                    return jsonify({'success': False, 'error': 'Employee not found'}), 404
                    
            else:
                result = supabase.table("employees").select("*").order("created_at", desc=True).execute()
                return jsonify({'success': True, 'employees': result.data if result.data else []})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    return app

# Create the app instance ONCE — for both Gunicorn and local dev
app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Unified ERP Backend Server")
    app.run(host='0.0.0.0', port=10000, debug=False)
    #app.run(host='127.0.0.1', port=5000, debug=True)