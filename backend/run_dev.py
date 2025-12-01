#!/usr/bin/env python3
"""
Development server runner
Run this script to start the server in development mode with auto-reload.
"""
import os
import sys
import warnings
import logging

def main():
    """Run Flask development server"""
    # Set development environment
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = 'True'
    
    # Suppress Flask development server warning
    warnings.filterwarnings('ignore', message='.*development server.*')
    warnings.filterwarnings('ignore', category=UserWarning, module='werkzeug')
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    
    # Get port from environment or use default
    port = os.getenv('PORT', '5000')
    
    print("🚀 Starting ERP Backend Server (Development Mode)")
    print(f"📡 Port: {port}")
    print("🔧 Using Flask development server")
    print("📝 Development server warning suppressed - this is fine for local testing")
    print("⚠️  For production, use: python run_production.py")
    print("-" * 60)
    
    # Import and run app
    from app import app
    app.run(host='127.0.0.1', port=int(port), debug=True)

if __name__ == '__main__':
    main()

