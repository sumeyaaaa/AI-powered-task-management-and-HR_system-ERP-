# 🎓 Learning Guide: Adding Predefined Processes
## Understanding Flask, RAG, and Frontend Integration

This guide walks you through adding a new predefined process to the system, explaining how Flask backend, RAG (Retrieval-Augmented Generation), and React frontend work together.

---

## 📚 Table of Contents

1. [Overview: What We're Building](#overview)
2. [Architecture: How Everything Connects](#architecture)
3. [Step-by-Step: Adding Employee Onboarding Process](#step-by-step)
4. [Understanding Flask Backend](#understanding-flask)
5. [Understanding RAG System](#understanding-rag)
6. [Understanding React Frontend](#understanding-react)
7. [Testing Your Changes](#testing)

---

## 🎯 Overview: What We're Building

We're adding a new **Employee Onboarding** predefined process that:
- Generates exactly 8 tasks (no more, no less)
- Uses predefined steps with specific roles, activities, and deliverables
- Integrates with the existing task management system
- Works with both Flask backend and React frontend

---

## 🏗️ Architecture: How Everything Connects

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE (React)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  AITaskBuilder.tsx                                   │   │
│  │  - User selects template: "employee_onboarding"       │   │
│  │  - Sends POST /api/tasks/generate-from-goal         │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP Request
                            │ { template: "employee_onboarding", ... }
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FLASK BACKEND (Python)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  task_routes.py                                      │   │
│  │  - Receives request                                  │   │
│  │  - Checks template in registry                      │   │
│  │  - Calls generate_predefined_process_tasks()        │   │
│  └──────────────────────────────────────────────────────┘   │
│                            │                                 │
│                            ▼                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  predefined_processes.py                             │   │
│  │  - get_predefined_processes_registry()               │   │
│  │  - Returns: { 'employee_onboarding': {...} }         │   │
│  └──────────────────────────────────────────────────────┘   │
│                            │                                 │
│                            ▼                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  generate_predefined_process_tasks()                │   │
│  │  - Creates 8 tasks from template                     │   │
│  │  - Sets recommended_role for each task               │   │
│  │  - Saves to Supabase database                        │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE (Supabase)                       │
│  - tasks table: Stores generated tasks                       │
│  - goals table: Stores objectives                            │
│  - employees table: For role-based recommendations          │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Step-by-Step: Adding Employee Onboarding Process

### Step 1: Define the Process in Backend

**File:** `backend/predefined_processes.py`

```python
def get_employee_onboarding_process():
    """
    Returns the Employee Onboarding 8-step process.
    This is the exact process that will be used - no tasks added or removed.
    Only descriptions will be customized for specific objectives.
    """
    return {
        "1. PRE-ONBOARDING PREPARATION (1 day)": {
            "responsible": "HR Manager",
            "activities": "Prepare welcome package, set up workstation, create email account",
            "deliverable": "Workstation ready and access credentials prepared"
        },
        "2. FIRST DAY WELCOME & ORIENTATION (1 day)": {
            "responsible": "HR Manager",
            "activities": "Welcome meeting, company introduction, tour of facilities",
            "deliverable": "Employee oriented and introduced to team"
        },
        # ... more steps
    }
```

**What this does:**
- Defines a dictionary where each key is a step title
- Each step has: `responsible` (role), `activities` (what to do), `deliverable` (expected output)
- The step title includes timing: `(1 day)`, `(2 days)`, etc.

### Step 2: Register the Process

**File:** `backend/predefined_processes.py`

```python
def get_predefined_processes_registry():
    return {
        'order_to_delivery': get_order_to_delivery_process(),
        'stock_to_delivery': get_stock_to_delivery_process(),
        'employee_onboarding': get_employee_onboarding_process(),  # ✅ ADDED
    }
```

**What this does:**
- Creates a registry (dictionary) of all available processes
- The key (`'employee_onboarding'`) is what the frontend sends
- The value is the function that returns the process steps

### Step 3: Add to Frontend Template Options

**File:** `frontedn_react/src/components/TaskManagement/AITaskBuilder.tsx`

**3a. Update TypeScript Type:**
```typescript
type TemplateKey = 'auto' | 'order_to_delivery' | 'stock_to_delivery' | 'employee_onboarding';
```

**3b. Add to Template Options:**
```typescript
const PROCESS_TEMPLATES: Record<TemplateKey, { label: string; description: string }> = {
  // ... existing templates
  employee_onboarding: {
    label: 'Employee Onboarding (8-step process)',
    description: 'Use the predefined employee onboarding process with recommended owners.',
  },
};
```

**What this does:**
- TypeScript ensures type safety (only valid template keys)
- Adds a user-friendly label and description for the dropdown

**3c. Handle Template in Form Submission:**
```typescript
if (formData.template === 'employee_onboarding' && !payload.title.toLowerCase().includes('employee onboarding')) {
  payload.title = `Employee Onboarding - ${payload.title}`;
  payload.description = `${payload.description || ''}\n\nThis goal should follow the Employee Onboarding process.`;
}
```

**What this does:**
- Automatically prefixes the goal title if user doesn't
- Adds context to description for better AI understanding

---

## 🔧 Understanding Flask Backend

### Flask Basics

**Flask** is a Python web framework. In this project:

```python
# backend/app.py
from flask import Flask
app = Flask(__name__)

# Register blueprints (route modules)
from task_routes import task_bp
app.register_blueprint(task_bp)
```

**Blueprints** organize routes into modules:
- `task_bp` = all task-related routes
- `employee_bp` = all employee-related routes

### How Our Route Works

**File:** `backend/task_routes.py`

```python
@task_bp.route('/api/tasks/generate-from-goal', methods=['POST'])
@token_required  # 🔒 Authentication required
def generate_tasks_from_goal():
    data = request.get_json()  # Get JSON from frontend
    template = data.get('template')  # e.g., 'employee_onboarding'
    
    # Check if template is a predefined process
    predefined_processes = get_predefined_processes_registry()
    if template in predefined_processes:
        # Use predefined process
        return generate_predefined_process_tasks(goal, goal_data, ai_meta_id, template)
    else:
        # Use AI classification
        return generate_ai_custom_tasks(goal, goal_data, ai_meta_id)
```

**Flow:**
1. Frontend sends POST request with `template: 'employee_onboarding'`
2. Flask receives request at `/api/tasks/generate-from-goal`
3. `@token_required` decorator checks authentication
4. Route handler checks if template exists in registry
5. Calls `generate_predefined_process_tasks()` if found

### Task Generation Function

**File:** `backend/task_routes.py` → `generate_predefined_process_tasks()`

```python
def generate_predefined_process_tasks(goal, goal_data, ai_meta_id, process_name):
    # 1. Get process from registry
    predefined_processes = get_predefined_processes_registry()
    process_steps = predefined_processes[process_name]  # Gets our 8 steps
    
    # 2. Loop through each step
    for i, (step_key, step_data) in enumerate(process_steps.items()):
        # 3. Calculate due date from step timing
        days_offset = calculate_days_from_step(step_key)
        due_date = (base_date + timedelta(days=days_offset)).strftime('%Y-%m-%d')
        
        # 4. Customize description for specific objective
        customized_activities = step_data['activities']
        if customization_text:
            customized_activities = f"{step_data['activities']} for {customization_text}"
        
        # 5. Create task record
        task_record = {
            "task_description": f"{step_key}: {customized_activities}",
            "due_date": due_date,
            "priority": "medium",
            "status": "not_started",
            "strategic_metadata": {
                "assigned_role": step_data['responsible'],  # 🎯 KEY: Role for recommendations
                # ... more metadata
            }
        }
        
        # 6. Save to database
        supabase.table("tasks").insert(task_record).execute()
```

**Key Points:**
- **Exact steps**: Always generates the same number of tasks (8 for onboarding)
- **Role assignment**: Sets `assigned_role` in `strategic_metadata`
- **Customization**: Adds objective-specific text to descriptions
- **Database**: Saves to Supabase (PostgreSQL database)

---

## 🤖 Understanding RAG System

### What is RAG?

**RAG (Retrieval-Augmented Generation)** combines:
1. **Retrieval**: Search through documents (job descriptions, employee data)
2. **Augmentation**: Add retrieved context to AI prompts
3. **Generation**: AI generates recommendations using that context

### Two Types of Recommendations

#### 1. Predefined Process Recommendations (Role-Based)

**File:** `backend/task_routes.py` → `get_role_based_recommendations_for_predefined_process()`

```python
def get_role_based_recommendations_for_predefined_process(task, recommended_role):
    """
    For predefined processes, find 1 employee matching the recommended role.
    Returns 100% fit score if role matches.
    """
    # Search employees by role/title
    employees = supabase.table("employees").select("*").execute()
    
    matching_employees = []
    for emp in employees:
        if recommended_role.lower() in emp.get('title', '').lower():
            matching_employees.append({
                'employee_id': emp['id'],
                'employee_name': emp['name'],
                'fit_score': 100,  # Perfect match for predefined processes
                'reason': f"Matches recommended role: {recommended_role}"
            })
    
    return matching_employees[:1]  # Return only 1 recommendation
```

**When used:**
- For predefined processes (like `employee_onboarding`)
- Task has `assigned_role: "HR Manager"` in metadata
- Simple role matching, no AI needed

#### 2. AI Classification Recommendations (Full RAG)

**File:** `backend/task_routes.py` → `enhanced_role_based_employee_recommendations()`

```python
def enhanced_role_based_employee_recommendations(task, task_description):
    """
    Full RAG system: Analyzes JD documents, employee skills, experience.
    Returns 1-3 recommendations with fit scores.
    """
    # 1. RETRIEVAL: Get relevant context
    # - Employee job descriptions (PDFs, DOCX)
    # - Employee titles, departments, skills
    # - Task requirements
    
    # 2. AUGMENTATION: Build AI prompt with context
    prompt = f"""
    Task: {task_description}
    Required skills: {task.get('required_skills', [])}
    
    Employee profiles:
    {employee_context}
    
    Job descriptions:
    {jd_context}
    
    Find best matching employees.
    """
    
    # 3. GENERATION: AI analyzes and recommends
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    # 4. Parse recommendations
    recommendations = parse_ai_response(response)
    return recommendations  # 1-3 employees with fit scores
```

**When used:**
- For AI-classified tasks (template: `'auto'`)
- No predefined role, AI determines requirements
- Analyzes job descriptions, skills, experience

### RAG Document Processing

**File:** `backend/task_routes.py` → Document parsing functions

```python
def extract_text_from_pdf(file_path):
    """Extract text from PDF job descriptions"""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def extract_text_from_docx(file_path):
    """Extract text from DOCX job descriptions"""
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])
```

**Flow:**
1. Employee uploads JD document (PDF/DOCX)
2. System extracts text
3. Stores in database or processes on-the-fly
4. RAG system searches through text when recommending

---

## ⚛️ Understanding React Frontend

### React Component Structure

**File:** `frontedn_react/src/components/TaskManagement/AITaskBuilder.tsx`

```typescript
export const AITaskBuilder: React.FC<AITaskBuilderProps> = ({ onTasksGenerated }) => {
  // 1. STATE: Component's data
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    template: 'auto' as TemplateKey,  // Selected template
  });
  
  const [aiTasks, setAiTasks] = useState<Task[]>([]);  // Generated tasks
  
  // 2. HANDLERS: User interactions
  const handleGenerate = async () => {
    const payload = {
      title: formData.title,
      template: formData.template,  // Send to backend
    };
    
    // 3. API CALL: Send to Flask backend
    const result = await taskService.generateTasksFromGoal(payload);
    
    // 4. UPDATE STATE: Store results
    setAiTasks(result.ai_tasks);
  };
  
  // 5. RENDER: Display UI
  return (
    <div>
      <select value={formData.template} onChange={...}>
        {Object.entries(PROCESS_TEMPLATES).map(([key, template]) => (
          <option key={key} value={key}>{template.label}</option>
        ))}
      </select>
      <button onClick={handleGenerate}>Generate Tasks</button>
    </div>
  );
};
```

### API Service Layer

**File:** `frontedn_react/src/services/task.ts`

```typescript
export const taskService = {
  async generateTasksFromGoal(payload: {
    title: string;
    template: TemplateKey;
    // ... other fields
  }): Promise<{ success: boolean; ai_tasks: Task[] }> {
    // 1. Make HTTP request to Flask backend
    const response = await fetch('/api/tasks/generate-from-goal', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`,  // Auth token
      },
      body: JSON.stringify(payload),
    });
    
    // 2. Parse response
    const data = await response.json();
    return data;
  },
};
```

**What this does:**
- Abstracts HTTP calls from components
- Handles authentication tokens
- Provides type-safe API methods

### TypeScript Types

**File:** `frontedn_react/src/types/task.ts`

```typescript
export interface Task {
  id: string;
  task_description: string;
  due_date: string;
  priority: 'low' | 'medium' | 'high';
  status: TaskStatus;
  assigned_to?: string;
  strategic_metadata?: {
    assigned_role?: string;  // For predefined processes
    // ... more fields
  };
}
```

**Benefits:**
- Type safety: Prevents errors at compile time
- Autocomplete: IDE suggests available properties
- Documentation: Types serve as inline docs

---

## 🧪 Testing Your Changes

### 1. Test Backend Registry

```python
# In Python shell or test script
from predefined_processes import get_predefined_processes_registry

registry = get_predefined_processes_registry()
assert 'employee_onboarding' in registry
assert len(registry['employee_onboarding']) == 8
print("✅ Registry test passed!")
```

### 2. Test Frontend Template

1. Start React dev server: `npm run dev`
2. Navigate to Task Management
3. Open "AI Task Builder"
4. Check dropdown has "Employee Onboarding (8-step process)"
5. Select it and generate tasks

### 3. Test Full Flow

1. **Frontend**: Select "Employee Onboarding" template
2. **Frontend**: Enter title: "Onboard John Doe"
3. **Frontend**: Click "Generate Tasks"
4. **Backend**: Check logs for "🎯 PREDEFINED PROCESS: Using employee_onboarding template"
5. **Backend**: Verify 8 tasks created in database
6. **Frontend**: Verify 8 tasks displayed in UI

### 4. Check Database

```sql
-- In Supabase SQL editor
SELECT 
  task_description,
  strategic_metadata->>'assigned_role' as role,
  due_date
FROM tasks
WHERE objective_id = '<your_goal_id>'
ORDER BY created_at;
```

Should show 8 tasks with roles like "HR Manager", "HR Specialist", etc.

---

## 📊 Summary: What Changed

### Files Modified

1. **`backend/predefined_processes.py`**
   - ✅ Added `get_employee_onboarding_process()` function
   - ✅ Added `'employee_onboarding'` to registry

2. **`frontedn_react/src/components/TaskManagement/AITaskBuilder.tsx`**
   - ✅ Added `'employee_onboarding'` to `TemplateKey` type
   - ✅ Added template option to `PROCESS_TEMPLATES`
   - ✅ Added template handling in form submission

### Files That Auto-Connect

- **`backend/task_routes.py`**: Automatically uses registry (no changes needed)
- **`backend/app.py`**: Already imports task_routes (no changes needed)
- **Frontend services**: Already configured (no changes needed)

---

## 🎓 Key Concepts Learned

### Flask
- **Blueprints**: Organize routes into modules
- **Decorators**: `@token_required` for authentication
- **Request handling**: `request.get_json()` to get data
- **Database**: Supabase client for PostgreSQL

### RAG
- **Retrieval**: Search documents and employee data
- **Augmentation**: Add context to AI prompts
- **Generation**: AI generates recommendations
- **Two modes**: Role-based (predefined) vs Full RAG (AI)

### React/TypeScript
- **State management**: `useState` for component data
- **API calls**: Service layer abstracts HTTP
- **Type safety**: TypeScript prevents errors
- **Component structure**: State → Handlers → API → Render

---

## 🚀 Next Steps

1. **Add more processes**: Follow the same pattern
2. **Customize steps**: Modify activities/deliverables
3. **Add RAG features**: Enhance employee recommendations
4. **Test thoroughly**: Verify all flows work

---

## 📖 Additional Resources

- **Flask Docs**: https://flask.palletsprojects.com/
- **React Docs**: https://react.dev/
- **TypeScript Docs**: https://www.typescriptlang.org/
- **RAG Explained**: https://www.pinecone.io/learn/retrieval-augmented-generation/

---

**Happy Learning! 🎉**

