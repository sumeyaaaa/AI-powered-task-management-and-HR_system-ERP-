# 🧪 LeanChem Enterprise Management System

A modern HR, task, and ERP assistant for **LeanChem Ethiopia** combining a **Flask API** with a **React TypeScript frontend**. The platform centralizes workforce data, automates AI task creation, delivers RAG-based employee recommendations, and offers proactive notifications for both administrators and employees.

---

## 🚀 Highlights

- 👥 **Employee managment** – Rich profiles, JD links, skills, notes, photo management
- 🎯 **AI Task Builder** – Predefined process templates & “Let AI classify tasks” workflow
- 📊 **Interactive Admin Dashboard** – Live KPIs, status filters, strategic insights
- 🔔 **Real-time Notifications** – Inbox + bell + deep links to specific tasks (admin & employee)h
- 🤖 **RAG Recommendations** – Role-first matching using Supabase JD data and AI metadata
- 📎 **Task Collaboration** – Attachments, notes, status changes trigger notifications
- 🔐 **Role-based access** – Superadmin/Admin vs Employee portals with JWT auth

---

## 🧱 Monorepo Layout

```
├── backend/                      # Flask + Supabase API
│   ├── app.py                    # App factory, auth endpoints, profile APIs
│   ├── auth.py                   # JWT helpers, decorators, token validation
│   ├── employee_routes_fixed.py  # Employee CRUD + photo/JD helpers
│   ├── task_routes.py            # AI generation, predefined processes, attachments
│   ├── notification_routes.py    # Notification ingestion + delivery rules
│   └── predefined_processes.py   # Order-to-delivery steps, reusable templates
│
├── frontedn_react/               # React 18 + TypeScript SPA
│   ├── src/
│   │   ├── pages/Admin/…         # Admin Dashboard, Task Mgmt, Notifications
│   │   ├── pages/Employee/…      # Employee Profile, Tasks, Notifications
│   │   ├── components/…          # Task builders, cards, RAG widgets, layout
│   │   ├── contexts/             # Auth + Notifications (polling, navigation)
│   │   ├── services/             # Axios wrappers (auth, tasks, employees, notifications)
│   │   └── Types/                # Central TypeScript interfaces
│   └── public/                   # Static assets, favicon, hero images
│
├── AUTHENTICATION_FIXES.md       # Current hardening notes & deployment checklist
├── REACT_LEARNING_GUIDE.md       # Walkthrough for learning React via this project
├── requirements.txt              # Backend dependencies
├── package.json                  # Frontend dependencies (inside `frontedn_react/`)
└── README.md                     # This file
```

> **Naming note:** historical files under `frontend/` (Streamlit) remain for reference, but the active UI lives inside `frontedn_react/`.

---

## 🛠️ Tech Stack

### Backend
- Python 3.10+, Flask, Supabase Python SDK
- JWT (PyJWT) for stateless auth
- OpenAI / custom AI helpers for classification
- RAG utilities (PyPDF2, python-docx) for JD parsing

### Frontend
- React 18 + TypeScript + Vite tooling
- React Router v6, Context API, hooks (`useState`, `useEffect`, `useMemo`, `useCallback`)
- Axios with interceptors, Ant Design–style primitives + custom UI kit
- CSS modules per feature (TaskManagement, Dashboard, Notifications, Profile)

---

## ⚙️ Environment Variables

Create `.env` files both in `backend/` and `frontedn_react/`.

### Backend `.env`
```
FLASK_SECRET_KEY=change-me
SUPERADMIN_EMAIL=admin@leanchem.com
SUPERADMIN_PASSWORD=super-secure-password
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=SUPABASE_SERVICE_ROLE_KEY
OPENAI_API_KEY=sk-...
```

### Frontend `.env`
```
REACT_APP_BACKEND_URL=http://localhost:5000
```

> Store secrets securely (1Password, Vault, AWS Secrets Manager) for production.

---

## 🧑‍💻 Local Development

### 1. Clone
```bash
git clone https://github.com/leanchem/enterprise-management.git
cd enterprise-management
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
flask --app app run --debug       # or python app.py
```
Backend runs at **http://localhost:5000**

### 3. Frontend (React)
```bash
cd ../frontedn_react
npm install
npm run dev
```
Frontend runs at **http://localhost:3000**

React dev server proxies API calls to the Flask backend via `REACT_APP_BACKEND_URL`.

---

## 🔐 Authentication Flow

1. User logs in via `/api/auth/login`, receives JWT + role (`superadmin`, `admin`, `employee`)
2. Token stored in `localStorage`; Axios attaches it via Authorization header
3. `AuthContext` validates token on page refresh using `/api/auth/validate-token`
4. Protected routes (`/admin/*`, `/employee/*`) guard access via `ProtectedRoute`
5. Password changes propagate to Supabase; superadmin password also updates `.env`



---

## 🧩 Feature Walkthrough

### Admin Portal
- **Dashboard** – KPIs (active/inactive employees, task SLA panels, charts)
- **Task Management** – AI Task Builder (cards, RAG button, strategic metadata)
- **Notifications** – Inbox with “view task” deep links + highlight animation
- **Employee Management** – (legacy Streamlit) + new React profile parity

### Employee Portal
- **My Profile** – Rich hero layout (photo, JD links, bio, skills, strengths)
- **Task Management** – Assigned tasks, attachments, notes, propose task form
- **Notifications** – Mirrors admin behavior but scoped to employee-centric alerts

### AI + RAG
- **Predefined processes** (e.g., order-to-delivery) enforce 13-step templates
- **“Let AI classify tasks”** template polls backend until tasks insert
- **RAG recommendations** query Supabase JDs and roles (role-first > department)
- **AI Strategic Analysis** cards display metadata (process, KPIs, risks)

---

## 🧪 Testing & Quality

- Backend: `pytest` (coming soon) + manual Postman collections
- Frontend: `npm run lint`, TypeScript strict mode, manual QA flows
- Linting: `read_lints` integration in CI ensures changed files stay clean

Recommended manual test matrix:
1. Superadmin login, navigate to task from notification, upload attachment
2. Employee login, propose task, receive admin notification, respond
3. AI goal classification path (predefined vs AI template) + RAG recommendations
4. File upload & download, JD link management

---

## 🚢 Deployment Guide

### Backend (Flask)
```bash
cd backend
pip install -r requirements.txt
gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
```
Recommended: host on Render, Railway, Fly.io, or EC2 with Nginx reverse proxy + HTTPS.

### Frontend (React)
```bash
cd frontedn_react
npm start
npm run build
npm run preview    # optional local check
```
Deploy `dist/` to Netlify, Vercel, or S3 + CloudFront. Ensure `REACT_APP_BACKEND_URL` points to the public API domain.

### Production Checklist
- [ ] Update `.env` secrets (no defaults)
- [ ] Enable HTTPS (certbot/Let’s Encrypt or CDN TLS)
- [ ] Configure Supabase RLS / bucket policies
- [ ] Run smoke tests (login, task creation, notifications)
- [ ] Set up monitoring (Sentry, Logtail, New Relic, etc.)

---

## 🐛 Troubleshooting

| Problem | Resolution |
|---------|------------|
| Infinite login loop | Ensure backend running on `REACT_APP_BACKEND_URL` and `/api/auth/validate-token` reachable |
| “Token missing” on protected API | Confirm Axios attaches token; check browser devtools → Network tab |
| File uploads not showing | Backend expects `/upload-file` endpoint with `file` field; front-end already aligned |
| Employees list empty on dashboard | Supabase response may wrap data; React normalizes via `Array.isArray` guard |
| Notifications redirect to wrong page | Confirm `localStorage.current_task_id` set before navigation |


---

## 📄 License

**Proprietary & Confidential**  
© LeanChem Ethiopia. All rights reserved. Unauthorized distribution prohibited.
