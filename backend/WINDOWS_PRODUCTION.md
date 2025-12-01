# 🪟 Windows Production Server Setup

## Issue: Gunicorn Doesn't Work on Windows

Gunicorn requires Unix-specific modules (`fcntl`) and doesn't work on Windows.

## ✅ Solution: Use Waitress

**Waitress** is a production WSGI server that works on **all platforms** including Windows.

---

## 🚀 Quick Start

### 1. Install Waitress
```bash
pip install waitress
```

Or it's already in `requirements.txt` - just run:
```bash
pip install -r requirements.txt
```

### 2. Run Production Server
```bash
python run_production.py
```

The script automatically detects Windows and uses Waitress instead of Gunicorn!

---

## 📋 How It Works

The `run_production.py` script:
1. **Detects your OS** (Windows vs Linux/macOS)
2. **Windows**: Uses Waitress (imports and runs directly)
3. **Linux/macOS**: Uses Gunicorn (via subprocess)

---

## 🔧 Manual Waitress Usage

If you want to run Waitress directly:

```python
from waitress import serve
from app import app

serve(app, host='0.0.0.0', port=10000, threads=4)
```

Or via command line:
```bash
waitress-serve --host=0.0.0.0 --port=10000 app:app
```

---

## 📊 Waitress vs Gunicorn

| Feature | Waitress | Gunicorn |
|---------|----------|----------|
| **Windows Support** | ✅ Yes | ❌ No |
| **Linux/macOS** | ✅ Yes | ✅ Yes |
| **Performance** | ✅ Excellent | ✅ Excellent |
| **Production Ready** | ✅ Yes | ✅ Yes |
| **Threads** | ✅ Yes | ✅ Yes (workers) |

**Both are production-ready!** Waitress is just Windows-compatible.

---

## 🎯 Recommended Setup

### For Windows Development/Testing:
```bash
python run_production.py  # Uses Waitress automatically
```

### For Linux/macOS or Deployment:
```bash
python run_production.py  # Uses Gunicorn automatically
```

### For Deployment Platforms (Render, Heroku):
- They use Linux, so Gunicorn works fine
- Your `Procfile` already has: `web: gunicorn --config gunicorn_config.py app:app`
- ✅ No changes needed for deployment!

---

## ✅ Status

- ✅ `run_production.py` now detects Windows
- ✅ Uses Waitress on Windows automatically
- ✅ Uses Gunicorn on Linux/macOS automatically
- ✅ Production-ready on all platforms!

---

**TL;DR**: Just run `python run_production.py` - it works on Windows now! 🎉

