# 🔧 Render Deployment Fix

## Problem

Render is running `python app.py` (development server) instead of using Gunicorn from the `Procfile`.

## Solution

### 1. Verify Procfile Location

The `Procfile` must be in the **root of your backend directory** that Render uses.

**Current location:** `backend/Procfile` ✅

**Content:**
```
web: gunicorn --config gunicorn_config.py app:app
```

### 2. Render Service Configuration

In Render dashboard, make sure your **Web Service** has:

**Root Directory:** `backend`

This tells Render:
- Where to find the `Procfile`
- Where to run commands from
- Where your `app.py` is located

### 3. Start Command (Should Auto-Detect)

Render should automatically detect the `Procfile` and use:
```
gunicorn --config gunicorn_config.py app:app
```

**If it doesn't auto-detect**, manually set in Render dashboard:
- **Start Command:** `gunicorn --config gunicorn_config.py app:app`

### 4. Build Command

```
pip install -r requirements.txt
```

### 5. Environment Variables

Make sure these are set in Render:
- `FLASK_SECRET_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `OPENAI_API_KEY`
- `PORT` (auto-set by Render, don't set manually)

---

## 🔍 Why It's Running `python app.py`

Render runs `python app.py` when:
1. It can't find the `Procfile`
2. The `Procfile` is in the wrong location
3. Root directory is not set correctly

---

## ✅ Fix Steps

### Step 1: Check Root Directory in Render

1. Go to your Render service dashboard
2. Go to **Settings** tab
3. Check **Root Directory** field
4. Should be: `backend`
5. If empty or wrong, set it to: `backend`

### Step 2: Verify Procfile

1. In Render dashboard, go to **Logs** tab
2. Check build logs for: `Detected Procfile`
3. Should see: `web: gunicorn --config gunicorn_config.py app:app`

### Step 3: Manual Override (If Needed)

If Render still doesn't use Procfile:

1. Go to **Settings** → **Start Command**
2. Set to: `gunicorn --config gunicorn_config.py app:app`
3. Save changes
4. Redeploy

---

## 🎯 Expected Behavior

After fix, you should see in Render logs:

```
==> Build successful 🎉
==> Deploying...
==> Running 'gunicorn --config gunicorn_config.py app:app'
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:XXXX (XXXX)
[INFO] Using worker: sync
[INFO] Booting worker with pid: XXXX
✅ Employee routes registered successfully
✅ Task routes registered successfully
```

**NOT:**
```
==> Running 'python app.py'
🚀 Starting Unified ERP Backend Server (Development Mode)
```

---

## 📋 Checklist

- [ ] `Procfile` exists in `backend/` directory
- [ ] `Procfile` contains: `web: gunicorn --config gunicorn_config.py app:app`
- [ ] Render **Root Directory** is set to: `backend`
- [ ] `gunicorn_config.py` exists in `backend/` directory
- [ ] `requirements.txt` includes `gunicorn==21.2.0`
- [ ] All environment variables are set in Render

---

## 🚀 Quick Fix

If you want to force Render to use Gunicorn:

1. In Render dashboard → **Settings**
2. Set **Start Command** to:
   ```
   cd backend && gunicorn --config gunicorn_config.py app:app
   ```
3. Or if Root Directory is already `backend`:
   ```
   gunicorn --config gunicorn_config.py app:app
   ```

---

## 📝 Notes

- The `app.py` fix I made will help if Render accidentally runs `python app.py`
- It will now bind to `0.0.0.0` when PORT is set (Render provides this)
- But the best solution is to ensure Render uses the `Procfile` with Gunicorn

---

**TL;DR**: Set **Root Directory** to `backend` in Render dashboard, and ensure `Procfile` is in that directory. Render should then use Gunicorn automatically! 🎉

