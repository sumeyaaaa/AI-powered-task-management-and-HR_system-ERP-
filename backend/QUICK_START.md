# ⚡ Quick Start: Running the Server

## 🎯 The Warning Explained

When you run `python app.py`, you'll see:
```
WARNING: This is a development server. Do not use it in a production deployment.
```

**This is normal and expected!** Flask's development server is perfect for local testing.

---

## ✅ Solutions

### Option 1: Suppress Warning (Development) ⭐ Recommended for Local Dev

```bash
python run_dev.py
```

This script suppresses the warning and runs in development mode.

### Option 2: Use Production Server (No Warning)

```bash
python run_production.py
```

This automatically uses:
- **Waitress** on Windows (production WSGI server)
- **Gunicorn** on Linux/macOS (production WSGI server)

No warnings, production-ready!

### Option 3: Run Directly (Shows Warning - OK for Dev)

```bash
python app.py
```

The warning appears but the server works fine for development.

---

## 📋 Quick Commands

| Command | Mode | Warning? | Use Case | Platform |
|---------|------|----------|----------|----------|
| `python run_dev.py` | Development | ❌ No | Local testing | All |
| `python run_production.py` | Production | ❌ No | Production/testing | All (auto-detects OS) |
| `python app.py` | Development | ⚠️ Yes | Quick start (warning OK) | All |
| `gunicorn --config gunicorn_config.py app:app` | Production | ❌ No | Linux/macOS only | Unix |

---

## 🚀 Recommended Workflow

### For Development:
```bash
cd backend
python run_dev.py
```

### For Production:
```bash
cd backend
python run_production.py
```

---

## 💡 Key Points

- ✅ **Development warning is OK** - Flask dev server is fine for local work
- ✅ **Use Gunicorn for production** - Better performance, no warnings
- ✅ **Both work the same** - Same API, same functionality
- ✅ **Deployment platforms** (Render, Heroku) use Gunicorn automatically

---

**TL;DR**: Use `python run_dev.py` for development (no warning) or `python run_production.py` for production! 🎉

