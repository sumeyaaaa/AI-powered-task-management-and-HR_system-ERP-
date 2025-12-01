# 🚀 Running the Flask Backend Server

## Quick Start

### Development Mode (Local Testing)
```bash
# Option 1: Use the development script
python run_dev.py

# Option 2: Run directly (shows warning - that's OK for dev)
python app.py

# Option 3: Use Flask CLI
flask --app app run --debug
```

**Development server runs at:** `http://127.0.0.1:5000`

---

### Production Mode (No Warnings)
```bash
# Option 1: Use the production script
python run_production.py

# Option 2: Run Gunicorn directly
gunicorn --config gunicorn_config.py app:app

# Option 3: Use Procfile (for deployment platforms)
# The Procfile already has: web: gunicorn --config gunicorn_config.py app:app
```

**Production server runs at:** `http://0.0.0.0:10000` (or PORT from environment)

---

## Understanding the Warning

### Why You See the Warning

Flask's built-in server shows this warning:
```
WARNING: This is a development server. Do not use it in a production deployment.
```

**This is normal** when running `python app.py` directly. Flask's development server is:
- ✅ Perfect for local development
- ✅ Has auto-reload on code changes
- ❌ NOT suitable for production (single-threaded, not optimized)

### When to Use Each Mode

| Mode | When to Use | Command |
|------|-------------|---------|
| **Development** | Local testing, debugging | `python run_dev.py` or `python app.py` |
| **Production** | Deploying to server, production use | `python run_production.py` or `gunicorn ...` |

---

## Production Setup (Gunicorn)

### What is Gunicorn?

**Gunicorn** (Green Unicorn) is a Python WSGI HTTP Server for production:
- ✅ Handles multiple requests concurrently
- ✅ Process management (workers)
- ✅ Production-ready and battle-tested
- ✅ Used by major platforms (Render, Heroku, etc.)

### Configuration

Your `gunicorn_config.py` is already set up with:
- **Workers**: `CPU cores * 2 + 1` (auto-scales)
- **Port**: From `PORT` environment variable (default: 10000)
- **Timeout**: 120 seconds
- **Logging**: Configured for production

### Running with Gunicorn

```bash
# Basic command
gunicorn --config gunicorn_config.py app:app

# Or with custom port
PORT=5000 gunicorn --config gunicorn_config.py app:app

# Or with explicit workers
gunicorn --workers 4 --bind 0.0.0.0:10000 app:app
```

---

## Environment Variables

Set these in your `.env` file or environment:

```bash
# Server Configuration
PORT=10000                    # Port to run on
FLASK_ENV=production          # Set to 'production' for production mode
FLASK_DEBUG=False             # Debug mode (False for production)

# Database & Auth
SUPABASE_URL=your_url
SUPABASE_SERVICE_KEY=your_key
FLASK_SECRET_KEY=your_secret_key

# AI
OPENAI_API_KEY=your_key
```

---

## Deployment Platforms

### Render.com
- Uses `Procfile` automatically
- Runs: `gunicorn --config gunicorn_config.py app:app`
- Sets `PORT` environment variable automatically
- ✅ No warning in production

### Heroku
- Uses `Procfile` automatically
- Same as Render

### Local Production Testing
```bash
# Set production environment
export FLASK_ENV=production
export PORT=10000

# Run with Gunicorn
python run_production.py
```

---

## Troubleshooting

### Issue: "Gunicorn not found"
```bash
pip install gunicorn
```

### Issue: "Port already in use"
```bash
# Find process using port
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows

# Kill process or use different port
PORT=5001 python run_production.py
```

### Issue: "Module not found"
```bash
# Make sure you're in the backend directory
cd backend
pip install -r requirements.txt
```

---

## Summary

- **Development**: Use `python app.py` or `python run_dev.py` (warning is OK)
- **Production**: Use `python run_production.py` or `gunicorn` (no warning)
- **Deployment**: Platforms use `Procfile` automatically (Gunicorn)

The warning only appears in development mode - that's expected and fine! 🎉

