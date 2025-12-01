#!/usr/bin/env python3
"""
Production server runner
Automatically uses Waitress on Windows, Gunicorn on Linux/macOS
Run this script to start the server in production mode.
"""
import os
import sys
import platform

def main():
    """Run production WSGI server (Waitress on Windows, Gunicorn on Unix)"""
    # Set production environment
    os.environ['FLASK_ENV'] = 'production'
    
    # Get port from environment or use default
    port = int(os.getenv('PORT', '10000'))
    
    # Detect operating system
    is_windows = platform.system() == 'Windows'
    
    print("🚀 Starting ERP Backend Server (Production Mode)")
    print(f"📡 Port: {port}")
    print(f"🖥️  OS: {platform.system()}")
    
    if is_windows:
        print("🔧 Using Waitress WSGI server (Windows-compatible)")
        print("-" * 60)
        
        try:
            from waitress import serve
            from app import app
            
            print(f"✅ Server starting on http://0.0.0.0:{port}")
            print("   Press Ctrl+C to stop")
            print("-" * 60)
            
            # Run Waitress server
            serve(app, host='0.0.0.0', port=port, threads=4)
        except ImportError:
            print("❌ Waitress not installed!")
            print("   Install with: pip install waitress")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
            sys.exit(0)
    else:
        # Linux/macOS - use Gunicorn
        print("🔧 Using Gunicorn WSGI server")
        print("-" * 60)
        
        import subprocess
        try:
            subprocess.run([
                'gunicorn',
                '--config', 'gunicorn_config.py',
                'app:app'
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error starting Gunicorn: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
            sys.exit(0)

if __name__ == '__main__':
    main()

