from flask import Flask, jsonify, request, g
from flask_cors import CORS
from auth import AuthManager, token_required, admin_required
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
    
    CORS(app)
    
    # Import and register employee routes
    try:
        from employee_routes_fixed import employee_bp
        app.register_blueprint(employee_bp)
        print("✅ Employee routes registered successfully")
    except Exception as e:
        print(f"❌ Failed to register employee routes: {e}")
    
    # Root route
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            'status': 'healthy',
            'service': 'ERP Backend API',
            'message': 'API is running. Use /api/health for health checks.'
        })
    
    # Health check
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'service': 'ERP Backend API'})
    
    # Import and register task routes
    try:
        from task_routes import task_bp
        app.register_blueprint(task_bp)
        print("✅ Task routes registered successfully")
    except Exception as e:
        print(f"❌ Failed to register Task routes: {e}")

    # OLD NOTIFICATION ROUTES (keep for compatibility but they might not work for admin)
    try:
        from notification_routes import notification_bp
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
    
    # Token validation endpoint
    @app.route('/api/auth/validate-token', methods=['GET'])
    @token_required
    def validate_token():
        """Validate if the current token is still valid"""
        try:
            # g.user is set by @token_required decorator
            return jsonify({
                'success': True,
                'valid': True,
                'user': {
                    'email': g.user['email'],
                    'role': g.user.get('role'),
                    'employee_id': g.user.get('employee_id')
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'valid': False, 'error': str(e)}), 401
    
    # Change password endpoint
    @app.route('/api/auth/change-password', methods=['POST'])
    @token_required
    def change_password():
        data = request.get_json()
        if not data or not data.get('current_password') or not data.get('new_password'):
            return jsonify({'success': False, 'error': 'Current and new password required'}), 400
        
        # g.user is set by @token_required decorator - no need to verify token again
        auth_manager = AuthManager()
        result = auth_manager.change_password(g.user, data['current_password'], data['new_password'])
        return jsonify(result)
    
    # Employee profile endpoint
    @app.route('/api/employee/profile', methods=['GET'])
    @token_required
    def get_employee_profile():
        """Get employee profile (for employees) or all employees (for admin)"""
        try:
            # g.user is set by @token_required decorator - no need to verify token again
            from supabase import create_client
            supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
            
            if g.user.get('role') == 'employee':
                employee_id = g.user.get('employee_id')
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
    import sys
    
    # Check if running in production mode (Gunicorn sets this)
    is_production = os.getenv('FLASK_ENV') == 'production' or os.getenv('GUNICORN_WORKERS') is not None
    
    if is_production:
        print("🚀 Production mode: Use Gunicorn to run this app")
        print("   Run: gunicorn --config gunicorn_config.py app:app")
        sys.exit(1)
    
    # Development mode - suppress Flask warning
    import warnings
    import logging
    # Suppress Werkzeug development server warning
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    warnings.filterwarnings('ignore', category=UserWarning, module='werkzeug')
    
    print("🚀 Starting Unified ERP Backend Server (Development Mode)")
    print("📝 Note: Development server warning is suppressed - this is fine for local testing")
    print("⚠️  For production, use: python run_production.py")
    print("-" * 60)
    
    # Use environment variable for port, default to 5000 for local dev
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Run with use_reloader=False to avoid some warnings, but keep debug features
    app.run(host='127.0.0.1', port=port, debug=debug, use_reloader=debug)