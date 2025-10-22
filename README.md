# 🧪 LeanChem Enterprise Management System

A comprehensive enterprise management platform built with **Flask (backend)** and **Streamlit (frontend)**, designed specifically for **LeanChem Ethiopia’s construction and coating chemical distribution business**.

---

## 🚀 Overview
The **LeanChem Enterprise Management System** is a full-stack web application that streamlines employee management, task assignment, goal tracking, and team collaboration.  
Built with modern web technologies, it features **AI-powered task classification**, **RAG-enhanced employee recommendations**, and **real-time notifications**.

---

## 🌟 Key Features

- 👥 **Employee Management** – Complete employee profiles with skills tracking  
- 🎯 **AI Task Management** – Intelligent goal classification and task breakdown  
- 🤖 **RAG Recommendations** – AI-powered employee matching using job descriptions  
- 🔔 **Real-time Notifications** – In-app notifications with task navigation  
- 📊 **Analytics Dashboard** – Comprehensive reporting and insights  
- 🔐 **Role-based Access** – Secure multi-level user permissions  

---

## 🏗️ Project Structure

```
├── .env                      # Environment variables (never commit!)
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── image/                    # Logo of LeanChem
├── utils/                    # 🔧 Shared utilities (backend & frontend)
└── tests/                    # Unit/integration tests

📁 backend/
    ├── app.py                 # Application entry point
    ├── auth.py                # Authentication & authorization
    ├── employee_routes_fixed.py  # Employee management endpoints
    ├── task_routes.py         # Task management & AI integration
    ├── notification_routes.py # Real-time notifications
    └── config.py              # Configuration settings

📁 frontend/
    ├── app.py                 # Main Streamlit application
    ├── auth.py                # Authentication UI & session
    ├── employee_management.py # Employee UI components
    ├── task_management.py     # Task management UI
    ├── notification_management.py # Notifications interface
    └── config.py              # Configuration settings
```

---

## 🛠️ Technology Stack

### Backend
- **Python 3.9+**
- **Flask** – Web framework  
- **Supabase** – PostgreSQL database & storage  
- **JWT** – Authentication  
- **OpenAI GPT-3.5/4** – AI task classification  
- **PyPDF2 / python-docx** – Document processing for RAG  

### Frontend
- **Streamlit** – Web application framework  
- **Requests** – HTTP client  
- **Pandas** – Data manipulation  
- **Plotly** – Interactive visualization  

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.9 or higher  
- Supabase account and project  
- OpenAI API key  
- Git  

### 1. Clone the Repository
```bash
git clone https://github.com/leanchem/enterprise-management.git
cd enterprise-management
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```
Edit `.env` with your credentials.

### 3. Frontend Setup
```bash
cd frontend
pip install -r requirements.txt
cp .env.example .env
```
Edit `.env` with your credentials.

### 4. Environment Configuration
```
# Backend (.env)
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
OPENAI_API_KEY=your_openai_api_key
JWT_SECRET_KEY=your_jwt_secret_key
BACKEND_URL=http://localhost:5000

# Frontend (.env)
BACKEND_URL=http://localhost:5000
```

---

## 🚀 Running the Application

### Start Backend
```bash
cd backend
python main.py
```
Runs on: **http://localhost:5000**

### Start Frontend
```bash
cd frontend
streamlit run main.py
```
Runs on: **http://localhost:8501**

---

## 📚 Usage Guide

### 👨‍💼 For Administrators
#### Employee Management
- Add employees, upload photos, and manage activation status  
- Job Descriptions with Google Drive integration  
- Skill and experience tracking  

#### Task Management
- Set company goals with **AI classification**  
- Auto-generate tasks per goal  
- RAG-powered employee assignment  
- Real-time progress tracking  

#### Notifications
- Organization-wide overview  
- Bulk mark as read / delete  
- Direct task navigation  

### 👩‍🔧 For Employees
#### Task Management
- Personal dashboard for assigned tasks  
- Update progress and upload files  
- Collaborate via notes and mentions  

#### Notifications
- Real-time task updates  
- Quick navigation and actions  

---

## 🔧 API Documentation

### Authentication
| Method | Endpoint | Description |
|--------|-----------|-------------|
| POST | `/api/auth/login` | User authentication |
| POST | `/api/auth/register` | User registration (admin only) |
| GET | `/api/auth/verify` | Token verification |

### Employee Management
| Method | Endpoint | Description |
|--------|-----------|-------------|
| GET | `/api/employees` | List employees |
| POST | `/api/employees` | Create new employee |
| PUT | `/api/employees/{id}` | Update employee |
| POST | `/api/employees/{id}/upload-photo` | Upload profile photo |

### Task Management
| Method | Endpoint | Description |
|--------|-----------|-------------|
| GET | `/api/tasks/goals` | Get company goals |
| POST | `/api/tasks/goals/classify-only` | AI goal classification |
| POST | `/api/tasks` | Create task |
| PUT | `/api/tasks/{id}` | Update task progress |

### Notifications
| Method | Endpoint | Description |
|--------|-----------|-------------|
| GET | `/api/notifications` | List notifications |
| PUT | `/api/notifications/{id}/read` | Mark as read |
| PUT | `/api/notifications/read-all` | Mark all as read |

---

## 🤖 AI Features

### Strategic Goal Classification
- Framework alignment with LeanChem’s 2025–2026 strategy  
- Generates 3–5 actionable tasks per goal  
- Compliance scoring (80% threshold)  
- Q4 execution alignment  

### RAG Employee Recommendations
- JD document parsing and semantic analysis  
- Skill & experience-based scoring  
- Confidence-level reporting  

---

## 🗄️ Database Schema

| Table | Description |
|--------|-------------|
| `employees` | Employee profiles |
| `objectives` | Company goals |
| `action_plans` | Tasks and assignments |
| `task_updates` | Task progress & notes |
| `notifications` | System notifications |
| `ai_meta` | AI operation logs |

**Storage Buckets:**
- `employee-photos` – Profile pictures  
- `task-updates` – Task attachments  

---

## 🔐 Security
- JWT-based authentication  
- Role-based access (Superadmin, Admin, Employee)  
- Secure password hashing  
- Token expiry & refresh system  

---

## 🚢 Deployment

### Using Docker
```bash
docker build -t leanchem-app .
docker run -p 8501:8501 leanchem-app
```

### Production Environment Variables
```
SUPABASE_URL=your_production_url
OPENAI_API_KEY=your_production_key
```

---

## 🐛 Troubleshooting

### Backend Connection Errors
```bash
curl http://localhost:5000/api/health
echo $SUPABASE_URL
```

### Authentication Issues
- Ensure JWT keys match in frontend/backend  
- Check token expiry and roles  

### File Upload Problems
- Verify Supabase bucket permissions  
- Check file size (≤5MB) and MIME type  

---

## 🆘 Getting Help
- Search existing GitHub Issues  
- Create a new Issue with detailed description  

---

## 📄 License
**Proprietary & Confidential**  
© LeanChem Ethiopia. All rights reserved.
