# Predefined Processes System

## Overview

This system allows you to define standardized process templates (like "Order to Delivery") that generate tasks using **exact predefined steps** - no adding or removing tasks. Only task descriptions are customized for specific objectives.

## How It Works

### For Predefined Processes (e.g., "Order to Delivery")
- Uses **EXACT predefined steps** - no tasks added or removed
- Only **customizes descriptions** by replacing placeholders (e.g., "for DGEDA")
- Uses **recommended_role** for employee recommendations (100% fit score, 1 recommendation)
- Example: "Order to Delivery - DGEDA" will customize all 13 steps for DGEDA

### For AI Classification (Template: "auto")
- Fully relies on **AI** for task generation
- Uses **full RAG system** with JD (job description) analysis for employee recommendations
- Analyzes employee titles, roles, and JD documents to find best matches

## Adding a New Predefined Process

### Step 1: Define the Process in `predefined_processes.py`

```python
def get_your_new_process():
    """Returns your new predefined process template"""
    return {
        "Step 1 Title": {
            "responsible": "Role Name",
            "activities": "What needs to be done",
            "deliverable": "Expected output"
        },
        "Step 2 Title": {
            "responsible": "Another Role",
            "activities": "Another activity",
            "deliverable": "Another deliverable"
        },
        # ... more steps
    }
```

### Step 2: Register the Process

In `predefined_processes.py`, add to the registry:

```python
def get_predefined_processes_registry():
    return {
        'order_to_delivery': get_order_to_delivery_process(),
        'your_new_process': get_your_new_process(),  # Add here
    }
```

### Step 3: Add Template Option in Frontend

In `frontedn_react/src/components/TaskManagement/AITaskBuilder.tsx`, add to `PROCESS_TEMPLATES`:

```typescript
const PROCESS_TEMPLATES: Record<
  TemplateKey,
  { label: string; description: string }
> = {
  auto: {
    label: 'Let AI classify tasks',
    description: 'Use the AI/RAG engine to classify this objective into tasks.',
  },
  order_to_delivery: {
    label: 'Order to Delivery (13-step process)',
    description: 'Use the predefined order-to-delivery process with recommended owners.',
  },
  your_new_process: {  // Add here
    label: 'Your New Process',
    description: 'Use the predefined your-new-process template.',
  },
};
```

And add to `TemplateKey` type:

```typescript
type TemplateKey = 'auto' | 'order_to_delivery' | 'your_new_process';
```

## Backend Flow

1. **Frontend sends template**: `template: 'order_to_delivery'` or `template: 'auto'`
2. **Backend routes**:
   - If `template == 'order_to_delivery'` → `generate_predefined_process_tasks()`
   - If `template == 'auto'` → `generate_ai_custom_tasks()`
3. **Task generation**:
   - Predefined: Uses exact steps, customizes descriptions
   - AI: Fully AI-generated tasks
4. **Employee recommendations**:
   - Predefined: Role-based (100% fit, 1 recommendation)
   - AI: Full RAG with JD analysis

## Key Functions

- `generate_predefined_process_tasks()`: Generates tasks using predefined steps
- `get_role_based_recommendations_for_predefined_process()`: Gets 1 employee matching recommended role
- `enhanced_role_based_employee_recommendations()`: Full RAG analysis for AI-classified tasks

## Example: Order to Delivery

When user selects "Order to Delivery" template with title "Order to Delivery - DGEDA":
- Generates exactly 13 tasks (no more, no less)
- Customizes each task: "1. FINALIZE DEAL DOCUMENTATION (1 day) for DGEDA: Complete agreement..."
- Each task has `recommended_role` set (e.g., "Account Executive")
- Employee recommendations use role matching (100% fit if role matches)

## Example: AI Classification

When user selects "Let AI classify tasks":
- AI generates 5-8 tasks based on goal description
- Tasks have `predefined_process: false` flag
- Employee recommendations use full RAG:
  - Analyzes JD documents
  - Matches skills, experience, role, department
  - Returns 1-3 recommendations based on fit score

