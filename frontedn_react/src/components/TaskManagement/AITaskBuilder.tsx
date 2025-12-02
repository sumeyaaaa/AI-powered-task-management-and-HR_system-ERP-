import React, { useEffect, useMemo, useState, useRef } from 'react';
import { Task, Goal, Employee } from '../../types';
import { taskService } from '../../services/task';
import { employeeService } from '../../services/employee';
import { Button } from '../Common/UI/Button';
import GeneratedTaskCard from './GeneratedTaskCard';
import './AITaskBuilder.css';

type TemplateKey = 'auto' | 'order_to_delivery' | 'stock_to_delivery';

interface EditableTask extends Partial<Task> {
  isNew?: boolean;
}

interface AITaskBuilderProps {
  onTasksGenerated?: () => void;
}

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
  stock_to_delivery: {
    label: 'Stock to Delivery (13-step process)',
    description: 'Use the predefined stock-to-delivery process with recommended owners.',
  },
};

const STATUS_OPTIONS: Task['status'][] = [
  'not_started',
  'pending',
  'in_progress',
  'completed',
  'waiting',
  'ai_suggested',
];

export const AITaskBuilder: React.FC<AITaskBuilderProps> = ({ onTasksGenerated }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    output: '',
    deadline: '',
    department: 'All',
    priority: 'medium',
    template: 'auto' as TemplateKey,
  });
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [aiTasks, setAiTasks] = useState<Task[]>([]);
  const [goal, setGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [ragProgress, setRagProgress] = useState<{
    tasks: Array<{
      task_id: string;
      task_description: string;
      status: 'completed' | 'in_progress' | 'pending' | 'failed';
      progress: number;
      current_activity: string;
      recommendations_count: number;
    }>;
    summary: {
      total_tasks: number;
      completed: number;
      in_progress: number;
      pending: number;
      failed: number;
    };
  } | null>(null);
  const ragPollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const employeeOptions = useMemo(
    () =>
      employees.map(emp => ({
        id: emp.id,
        label: emp.name,
      })),
    [employees]
  );

  const fetchEmployees = async () => {
    try {
      const data = await employeeService.getAllEmployees(true);
      const normalized = Array.isArray(data) ? data : (data as any)?.employees || [];
      setEmployees(normalized);
      console.log('✅ Loaded employees for assignment:', normalized.length);
    } catch (err) {
      console.warn('Failed to load employees for AI builder', err);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  // Refresh employees when tasks are generated
  useEffect(() => {
    if (aiTasks.length > 0) {
      fetchEmployees();
    }
  }, [aiTasks.length]);

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const payload = {
        title: formData.title || 'New Objective',
        description: formData.description,
        output: formData.output,
        deadline: formData.deadline || undefined,
        department: formData.department === 'All' ? undefined : formData.department,
        priority: formData.priority,
        auto_classify: true,
        template: formData.template,  // 🎯 PASS TEMPLATE TO BACKEND
      };

      if (formData.template === 'order_to_delivery' && !payload.title.toLowerCase().includes('order to delivery')) {
        payload.title = `Order to Delivery - ${payload.title}`;
        payload.description = `${payload.description || ''}\n\nThis goal should follow the Order to Delivery process.`;
      }
      
      if (formData.template === 'stock_to_delivery' && !payload.title.toLowerCase().includes('stock to delivery')) {
        payload.title = `Stock to Delivery - ${payload.title}`;
        payload.description = `${payload.description || ''}\n\nThis goal should follow the Stock to Delivery process.`;
      }
      
      const result = await taskService.generateTasksFromGoal(payload);
      if (!result.success) {
        throw new Error(result.message || 'Unable to generate tasks');
      }

      setGoal(result.goal || null);

      let generatedTasks = Array.isArray(result.ai_tasks) ? result.ai_tasks : [];
      if ((!generatedTasks || !generatedTasks.length) && result.goal?.id) {
        generatedTasks = await loadTasksWithRetry(result.goal.id);
      }

      if (!generatedTasks.length) {
        setError('AI classification completed but tasks are not yet available. Please try again in a moment.');
      } else {
        setAiTasks(generatedTasks);
        setSuccess(result.message || 'AI tasks generated. You can edit them below.');
        
        // RAG recommendations will only be polled when user clicks "Recommend Employee" button
        // Don't start polling automatically after task generation
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleTaskChange = (
    taskId: string | undefined,
    field: keyof Task | 'assigned_role',
    value: string
  ) => {
    setAiTasks(prev =>
      prev.map(task =>
        task.id === taskId
          ? {
              ...task,
              ...(field === 'assigned_role'
                ? {
                    strategic_metadata: {
                      ...(task.strategic_metadata || {}),
                      assigned_role: value,
                    },
                  }
                : { [field]: value }),
            }
          : task
      )
    );
  };

  const handleAssignmentChange = (taskId: string | undefined, employeeId: string) => {
    setAiTasks(prev =>
      prev.map(task =>
        task.id === taskId
          ? {
              ...task,
              assigned_to: employeeId,
            }
          : task
      )
    );
  };

  const handleSave = async () => {
    if (!aiTasks.length) {
      setError('Generate tasks first before saving.');
      return;
    }
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      for (const task of aiTasks) {
        if (!task.id) continue;
        const payload: Partial<Task> = {
          task_description: task.task_description,
          due_date: task.due_date,
          priority: task.priority,
          assigned_to: task.assigned_to,
          status: task.status,
          strategic_objective: task.strategic_objective,
          pre_number: task.pre_number,
        };
        if (task.strategic_metadata) {
          payload.strategic_metadata = {
            ...task.strategic_metadata,
            ...(task.strategic_metadata.assigned_role ? { assigned_role: task.strategic_metadata.assigned_role } : {}),
          };
        }
        const result = await taskService.updateTask(task.id, payload);
        if (!result.success) {
          throw new Error(result.error || 'Failed to update task');
        }
      }
      setSuccess('Tasks updated successfully.');
      onTasksGenerated?.();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update tasks';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const fetchTasksForGoal = async (goalId?: string): Promise<Task[]> => {
    if (!goalId) return [];
    try {
      const allTasks = await taskService.getTasks();
      return allTasks.filter(task => {
        const objectiveId = task.objective_id || task.objectives?.id;
        return objectiveId && String(objectiveId) === String(goalId);
      });
    } catch (err) {
      console.error('Failed to fetch generated tasks for goal', err);
      return [];
    }
  };

  const loadTasksWithRetry = async (goalId: string, attempt = 0): Promise<Task[]> => {
    const tasksForGoal = await fetchTasksForGoal(goalId);
    if (tasksForGoal.length || attempt >= 3) {
      return tasksForGoal;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
    return loadTasksWithRetry(goalId, attempt + 1);
  };

  const refreshTask = async (taskId: string) => {
    try {
      const allTasks = await taskService.getTasks();
      const updatedTask = allTasks.find(t => t.id === taskId);
      if (updatedTask) {
        setAiTasks(prev => prev.map(t => t.id === taskId ? updatedTask : t));
      }
    } catch (err) {
      console.error('Failed to refresh task:', err);
    }
  };

  const startRAGProgressPolling = (objectiveId: string) => {
    // Clear any existing polling
    if (ragPollingIntervalRef.current) {
      clearInterval(ragPollingIntervalRef.current);
    }

    const pollInterval = setInterval(async () => {
      try {
        const status = await taskService.getRAGRecommendationsStatus(objectiveId);
        if (status.success && status.tasks && status.summary) {
          // Only set progress if there are actually tasks with RAG activity
          if (status.summary.total_tasks > 0) {
            setRagProgress({
              tasks: status.tasks,
              summary: status.summary
            });
            
            // Stop polling if all tasks are completed or failed
            if (status.summary.completed + status.summary.failed === status.summary.total_tasks) {
              clearInterval(pollInterval);
              ragPollingIntervalRef.current = null;
              // Keep RAG progress to show completion status - don't clear it
              // This allows the UI to know that RAG is complete and show "View Recommendations" buttons
              // Refresh tasks to get updated recommendations
              if (goal?.id) {
                const updatedTasks = await fetchTasksForGoal(goal.id);
                if (updatedTasks.length) {
                  setAiTasks(updatedTasks);
                }
              }
              // Don't clear ragProgress - keep it so buttons know RAG is complete
            }
          } else {
            // No tasks with RAG activity - clear progress and stop polling
            clearInterval(pollInterval);
            ragPollingIntervalRef.current = null;
            setRagProgress(null);
          }
        }
      } catch (err) {
        console.error('Error polling RAG progress:', err);
      }
    }, 2000); // Poll every 2 seconds

    ragPollingIntervalRef.current = pollInterval;

    // Cleanup after 5 minutes
    setTimeout(() => {
      if (ragPollingIntervalRef.current === pollInterval) {
        clearInterval(pollInterval);
        ragPollingIntervalRef.current = null;
      }
    }, 5 * 60 * 1000);
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (ragPollingIntervalRef.current) {
        clearInterval(ragPollingIntervalRef.current);
        ragPollingIntervalRef.current = null;
      }
    };
  }, []);

  return (
    <div className="ai-builder">
      <div className="ai-builder-header">
        <div>
          <p className="eyebrow">AI & RAG Task Creation</p>
          <h2>Create Tasks from Objectives</h2>
          <p>Select a template or let the AI classify your objective into actionable tasks.</p>
        </div>
        <Button variant="primary" onClick={handleGenerate} disabled={loading}>
          {loading ? 'Generating…' : 'Generate Tasks'}
        </Button>
      </div>

      <div className="ai-builder-form">
        <div className="form-grid">
          <label>
            Objective Title*
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              placeholder="Order Fulfilment Overhaul"
            />
          </label>
          <label>
            Output / Goal
            <input
              type="text"
              value={formData.output}
              onChange={(e) => setFormData(prev => ({ ...prev, output: e.target.value }))}
              placeholder="Deliver consolidated shipment by Q4"
            />
          </label>
          <label>
            Deadline
            <input
              type="date"
              value={formData.deadline}
              onChange={(e) => setFormData(prev => ({ ...prev, deadline: e.target.value }))}
            />
          </label>
          <label>
            Department
            <select
              value={formData.department}
              onChange={(e) => setFormData(prev => ({ ...prev, department: e.target.value }))}
            >
              {['All', 'Operations', 'Supply Chain', 'Sales', 'Finance', 'Product'].map(dep => (
                <option key={dep} value={dep}>
                  {dep}
                </option>
              ))}
            </select>
          </label>
          <label>
            Priority
            <select
              value={formData.priority}
              onChange={(e) => setFormData(prev => ({ ...prev, priority: e.target.value }))}
            >
              {['low', 'medium', 'high', 'urgent'].map(option => (
                <option key={option} value={option}>
                  {option.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
          <label>
            Template
            <select
              value={formData.template}
              onChange={(e) => setFormData(prev => ({ ...prev, template: e.target.value as TemplateKey }))}
            >
              {Object.entries(PROCESS_TEMPLATES).map(([key, meta]) => (
                <option key={key} value={key}>
                  {meta.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Objective Details
          <textarea
            value={formData.description}
            onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
            placeholder="Provide any background so AI can classify tasks accurately..."
          />
        </label>
        <p className="template-hint">{PROCESS_TEMPLATES[formData.template].description}</p>
      </div>

      {error && <div className="inline-error">{error}</div>}
      {success && <div className="inline-success">{success}</div>}


      {!!aiTasks.length && (
        <div className="ai-tasks-editor">
          <div className="editor-header">
            <div>
              <p className="eyebrow">Generated Tasks</p>
              <h3>{goal ? goal.title : formData.title || 'Objective tasks'}</h3>
              <p>Review tasks, get employee recommendations, assign owners, and update priorities before publishing.</p>
            </div>
            <Button variant="success" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save All Tasks'}
            </Button>
          </div>

          {aiTasks.length > 0 && (
            <div className="generated-tasks-summary">
              <div className="generated-tasks-summary-item">
                <span className="number">{aiTasks.length}</span>
                <span className="label">Total Tasks</span>
              </div>
              <div className="generated-tasks-summary-item">
                <span className="number">{aiTasks.filter(t => t.assigned_to).length}</span>
                <span className="label">Assigned</span>
              </div>
              <div className="generated-tasks-summary-item">
                <span className="number">{aiTasks.filter(t => !t.assigned_to).length}</span>
                <span className="label">Unassigned</span>
              </div>
            </div>
          )}

          <div className="generated-tasks-list">
            {aiTasks.map((task, index) => (
              <GeneratedTaskCard
                key={task.id}
                task={task}
                index={index}
                employees={employees}
                onTaskChange={handleTaskChange}
                onAssignmentChange={handleAssignmentChange}
                onRecommendationApplied={async () => {
                  await refreshTask(task.id);
                }}
                onRAGStarted={() => {
                  // Restart polling if a task starts RAG process
                  if (goal?.id) {
                    startRAGProgressPolling(goal.id);
                  }
                }}
                objectiveRAGStatus={ragProgress ? {
                  tasks: ragProgress.tasks,
                  summary: ragProgress.summary
                } : undefined}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AITaskBuilder;

