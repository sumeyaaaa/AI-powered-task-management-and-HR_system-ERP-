# 🚀 Render Deployment Guide

## Backend Deployment on Render

### Step 1: Prepare Your Repository

1. **Ensure your backend code is ready:**
   - Backend code is in the `backend/` directory
   - `Procfile` is in the root or `backend/` directory
   - `requirements.txt` is in the `backend/` directory

### Step 2: Create Render Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:

   **Basic Settings:**
   - **Name**: `leanchem-backend` (or your preferred name)
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your deployment branch)
   - **Root Directory**: `backend` (since Procfile is in backend/)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: Leave empty (Render will use Procfile automatically)
   
   **Important:** Make sure your Procfile is in the `backend/` directory and contains:
   ```
   web: gunicorn --config gunicorn_config.py app:app
   ```
   
   The `gunicorn_config.py` file handles all production settings including:
   - Proper worker configuration
   - Timeout settings
   - Logging configuration
   - PORT from environment variable

### Step 3: Environment Variables

Add these environment variables in Render Dashboard → Environment:

**Required:**
```
FLASK_SECRET_KEY=your-secret-key-here (generate a strong random string)
SUPERADMIN_EMAIL=admin@leanchem.com
SUPERADMIN_PASSWORD=your-secure-password
SUPABASE_URL=your-supabase-project-url
SUPABASE_SERVICE_KEY=your-supabase-service-key
OPENAI_API_KEY=your-openai-api-key
FRONTEND_ORIGIN=https://your-react-app.onrender.com
PORT=10000
```

**Optional:**
```
DEFAULT_PASSWORD=1234
```

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Start your application
3. Your backend will be available at: `https://leanchem-backend.onrender.com` (or your service name)

### Step 5: Verify Deployment

1. Check health endpoint:
   ```bash
   curl https://your-backend.onrender.com/api/health
   ```
   Should return: `{"status": "healthy", "service": "ERP Backend API"}`

2. Check Render logs for any errors

---

## React Frontend Deployment

### Step 1: Update Environment Variables

Create/update `frontedn_react/.env.production`:

```env
REACT_APP_BACKEND_URL=https://your-backend.onrender.com
```

**Important:** Replace `your-backend.onrender.com` with your actual Render backend URL.

### Step 2: Deploy to Netlify/Vercel

#### Option A: Netlify

1. Go to [Netlify Dashboard](https://app.netlify.com/)
2. Click **"Add new site"** → **"Import an existing project"**
3. Connect your GitHub repository
4. Configure build:
   - **Base directory**: `frontedn_react`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontedn_react/dist`
5. Add environment variable:
   - **Key**: `REACT_APP_BACKEND_URL`
   - **Value**: `https://your-backend.onrender.com`
6. Deploy!

#### Option B: Vercel

1. Go to [Vercel Dashboard](https://vercel.com/)
2. Click **"Add New Project"**
3. Import your GitHub repository
4. Configure:
   - **Root Directory**: `frontedn_react`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Add environment variable:
   - **Key**: `REACT_APP_BACKEND_URL`
   - **Value**: `https://your-backend.onrender.com`
6. Deploy!

#### Option C: Render (Web Service - Recommended for SPA)

**Important:** For React Router to work properly on Render, use a Web Service (not Static Site) with a Node.js server.

1. Go to Render Dashboard
2. Click **"New +"** → **"Web Service"**
3. Connect your repository
4. Configure:
   - **Name**: `leanchem-frontend`
   - **Root Directory**: `frontedn_react`
   - **Runtime**: `Node`
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm run serve`
5. Add environment variable:
   - **Key**: `REACT_APP_BACKEND_URL`
   - **Value**: `https://your-backend.onrender.com`
6. Deploy!

**Note:** The `server.js` file handles all routes by serving `index.html`, which fixes the "not found" issue when navigating directly to routes like `/login` or refreshing the page.

---

## Post-Deployment Configuration

### 1. Update CORS in Backend

After deploying React, update the `FRONTEND_ORIGIN` environment variable in Render:

```
FRONTEND_ORIGIN=https://your-react-app.netlify.app,https://your-react-app.vercel.app
```

(Add all your frontend URLs, separated by commas)

### 2. Test the Connection

1. Open your deployed React app
2. Open browser DevTools → Network tab
3. Try logging in
4. Verify API calls are going to your Render backend URL
5. Check for CORS errors

### 3. Common Issues & Solutions

**Issue: CORS Errors**
- **Solution**: Update `FRONTEND_ORIGIN` in Render backend environment variables

**Issue: 401 Unauthorized**
- **Solution**: Check that `FLASK_SECRET_KEY` is set correctly in Render

**Issue: Database Connection Errors**
- **Solution**: Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are correct

**Issue: API Calls Going to localhost**
- **Solution**: Rebuild React app with correct `REACT_APP_BACKEND_URL` environment variable

---

## Environment Variables Summary

### Backend (Render)
```
FLASK_SECRET_KEY=xxx
SUPERADMIN_EMAIL=admin@leanchem.com
SUPERADMIN_PASSWORD=xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx
OPENAI_API_KEY=sk-xxx
FRONTEND_ORIGIN=https://your-frontend.netlify.app
PORT=10000
```

### Frontend (Netlify/Vercel/Render)
```
REACT_APP_BACKEND_URL=https://your-backend.onrender.com
```

---

## Testing Checklist

- [ ] Backend health check returns 200
- [ ] Backend login endpoint works
- [ ] Frontend can connect to backend
- [ ] Authentication works (login/logout)
- [ ] API calls succeed (no CORS errors)
- [ ] Employee data loads
- [ ] Task data loads
- [ ] Notifications work
- [ ] File uploads work

---

## Production URLs

After deployment, you'll have:

- **Backend**: `https://leanchem-backend.onrender.com`
- **Frontend**: `https://leanchem-frontend.netlify.app` (or Vercel/Render URL)

Update your React app's `REACT_APP_BACKEND_URL` to point to your Render backend URL!

