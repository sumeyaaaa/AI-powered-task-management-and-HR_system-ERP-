import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { taskService } from '../../services/task';
import { employeeService } from '../../services/employee';
import { Task, TaskAttachment, TaskNote } from '../../types';
import { Employee } from '../../types/employee';
import { Button } from '../../components/Common/UI/Button';
import { AITaskBuilder } from '../../components/TaskManagement/AITaskBuilder';
import { RAGRecommendations } from '../../components/TaskManagement/RAGRecommendations';
import './TaskManagement.css';

type StatusFilter =
  | 'all'
  | 'pending'
  | 'not_started'
  | 'in_progress'
  | 'completed'
  | 'waiting'
  | 'ai_suggested';

const statusOptions: StatusFilter[] = [
  'all',
  'pending',
  'not_started',
  'in_progress',
  'completed',
  'waiting',
  'ai_suggested',
];

const priorityOptions: Array<'all' | Task['priority']> = ['all', 'urgent', 'high', 'medium', 'low'];

const TaskManagement: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [pendingTaskId, setPendingTaskId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'list' | 'ai'>('list');
  const [detailTab, setDetailTab] = useState<'details' | 'attachments' | 'notes' | 'recommendations'>('details');
  const [taskNotes, setTaskNotes] = useState<TaskNote[]>([]);
  const [taskAttachments, setTaskAttachments] = useState<TaskAttachment[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);
  const [allEmployees, setAllEmployees] = useState<Employee[]>([]);
  const [employeesLoading, setEmployeesLoading] = useState(true);
  const [filters, setFilters] = useState({
    status: 'all' as StatusFilter,
    assignment: 'all',
    employee: 'all',
    priority: 'all' as 'all' | Task['priority'],
    objective: 'all',
    sortBy: 'recent',
    search: '',
    startDate: '',
    endDate: '',
  });

  useEffect(() => {
    loadTasks();
    loadAllEmployees();
  }, []);

  const loadAllEmployees = async () => {
    try {
      setEmployeesLoading(true);
      const data = await employeeService.getAllEmployees(true);
      // Handle different response formats
      let employeesList: Employee[] = [];
      if (Array.isArray(data)) {
        employeesList = data;
      } else if (data && typeof data === 'object' && 'employees' in data) {
        employeesList = Array.isArray((data as any).employees) ? (data as any).employees : [];
      } else if (data && typeof data === 'object' && 'data' in data) {
        employeesList = Array.isArray((data as any).data) ? (data as any).data : [];
      }
      console.log('✅ Loaded employees:', employeesList.length);
      if (employeesList.length > 0) {
        console.log('Sample employees:', employeesList.slice(0, 3).map(e => ({ id: e.id, name: e.name, is_active: e.is_active })));
      }
      setAllEmployees(employeesList);
    } catch (err) {
      console.error('❌ Failed to load employees:', err);
      setAllEmployees([]);
    } finally {
      setEmployeesLoading(false);
    }
  };

  // Check for task ID from notification navigation (runs on mount and when tasks change)
  useEffect(() => {
    const taskIdFromNotification = localStorage.getItem('current_task_id');
    if (taskIdFromNotification && !pendingTaskId) {
      // Clear it immediately to prevent re-triggering
      localStorage.removeItem('current_task_id');
      // Store it in state to use after tasks are loaded
      setPendingTaskId(taskIdFromNotification);
    }
  }, [tasks, pendingTaskId]);

  // Handle task navigation from notifications after tasks are loaded
  useEffect(() => {
    if (pendingTaskId && tasks.length > 0) {
      const task = tasks.find(t => t.id === pendingTaskId);
      if (task) {
        // Select the task and show details
        setSelectedTask(task);
        setDetailTab('details');
        
        // Load task details (attachments and notes)
        loadTaskAttachments(task.id);
        loadTaskNotes(task.id);
        
        // Scroll to the task card if it exists
        setTimeout(() => {
          const taskCard = document.querySelector(`[data-task-id="${pendingTaskId}"]`);
          if (taskCard) {
            taskCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 200);
        
        // Clear the highlighted class after animation
        setTimeout(() => {
          setPendingTaskId(null);
        }, 2000);
      } else {
        // Task not found, clear pending ID
        console.warn(`Task ${pendingTaskId} not found in loaded tasks`);
        setPendingTaskId(null);
      }
    }
  }, [tasks, pendingTaskId]);

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await taskService.getTasks();
      const normalized = Array.isArray(data)
        ? data
        : Array.isArray((data as any)?.tasks)
          ? (data as any).tasks
          : [];
      setTasks(normalized);
    } catch (err) {
      setError('Unable to load tasks. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  // Helper function to get display name (sanitize IDs)
  const getDisplayName = (name?: string | null) => {
    if (!name) return '';
    // Strip leading IDs like "12345 - John Doe" or "#123 | Jane"
    const cleaned = name.replace(/^[^A-Za-z]*[0-9]+[\s\-\|:_]+/, '').trim();
    return cleaned || name;
  };

  const employees = useMemo(() => {
    console.log('Processing employees, allEmployees count:', allEmployees.length);
    
    // Use all employees - return array of objects with id and display name
    const employeeList = allEmployees
      .filter(emp => {
        // Check if employee exists and has a name
        if (!emp || !emp.id) return false;
        if (!emp.name || emp.name.trim() === '') return false;
        // Check if employee is active (default to true if not specified)
        const isActive = emp.is_active !== false;
        return isActive;
      })
      .map(emp => {
        const displayName = getDisplayName(emp.name) || emp.name;
        return {
          id: emp.id,
          name: displayName,
          originalName: emp.name
        };
      })
      .filter(emp => emp.name && emp.name.trim() !== '') // Remove empty names
      .sort((a, b) => a.name.localeCompare(b.name)); // Sort alphabetically by display name
    
    console.log('Processed employees for filter:', employeeList.length);
    if (employeeList.length > 0) {
      console.log('First few employees:', employeeList.slice(0, 5));
    }
    return employeeList;
  }, [allEmployees]);

  const objectives = useMemo(() => {
    const set = new Set<string>();
    tasks.forEach(task => {
      if (task.objectives?.title) {
        set.add(task.objectives.title);
      }
    });
    return Array.from(set).sort();
  }, [tasks]);

  const filteredTasks = useMemo(() => {
    return tasks
      .filter(task => {
        if (filters.status !== 'all' && task.status !== filters.status) return false;
        if (filters.assignment !== 'all') {
          const hasAssignee =
            !!task.employees?.name ||
            (typeof task.assigned_to === 'string' && task.assigned_to.trim() !== '');
          if (filters.assignment === 'assigned' && !hasAssignee) return false;
          if (filters.assignment === 'unassigned' && hasAssignee) return false;
        }
        if (filters.employee !== 'all') {
          // Check if any assigned employee matches the filter
          const taskEmployeeNames = [
            getDisplayName(task.employees?.name || task.assigned_to_name || ''),
            // Also check assigned_to_multiple if it exists
            ...(task.assigned_to_multiple || []).map((empId: string) => {
              const emp = allEmployees.find(e => e.id === empId);
              return emp ? getDisplayName(emp.name) : '';
            })
          ].filter(name => name); // Remove empty names
          
          if (!taskEmployeeNames.includes(filters.employee)) return false;
        }
        if (filters.priority !== 'all' && (task.priority || 'low') !== filters.priority) {
          return false;
        }
        if (filters.objective !== 'all' && task.objectives?.title !== filters.objective) {
          return false;
        }
        if (filters.search) {
          const haystack = `${task.task_description || ''} ${task.description || ''}`.toLowerCase();
          if (!haystack.includes(filters.search.toLowerCase())) return false;
        }
        if (filters.startDate || filters.endDate) {
          const created = task.created_at ? task.created_at.slice(0, 10) : '';
          if (filters.startDate && created < filters.startDate) return false;
          if (filters.endDate && created > filters.endDate) return false;
        }
        return true;
      })
      .sort((a, b) => {
        switch (filters.sortBy) {
          case 'due_date':
            return (a.due_date || '').localeCompare(b.due_date || '');
          case 'priority':
            const order: Record<string, number> = { urgent: 0, high: 1, medium: 2, low: 3 };
            return (order[a.priority || 'low'] ?? 4) - (order[b.priority || 'low'] ?? 4);
          case 'status':
            return a.status.localeCompare(b.status);
          default:
            return (b.created_at || '').localeCompare(a.created_at || '');
        }
      });
  }, [tasks, filters]);

  useEffect(() => {
    if (filteredTasks.length === 0) {
      setSelectedTask(null);
      return;
    }
    setSelectedTask(prev =>
      prev && filteredTasks.some(task => task.id === prev.id) ? prev : null
    );
  }, [filteredTasks]);

  const summary = useMemo(() => {
    const total = tasks.length;
    const inProgress = tasks.filter(task => task.status === 'in_progress').length;
    const completed = tasks.filter(task => task.status === 'completed').length;
    const overdue = tasks.filter(task => {
      if (!task.due_date) return false;
      return new Date(task.due_date) < new Date() && task.status !== 'completed';
    }).length;
    return { total, inProgress, completed, overdue };
  }, [tasks]);

  const handleFilterChange = (key: keyof typeof filters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleStatusChange = async (status: Task['status']) => {
    if (!selectedTask) return;
    try {
      await taskService.updateTaskStatus(selectedTask.id, status);
      await loadTasks();
      setSelectedTask(prev => (prev ? { ...prev, status } : prev));
    } catch (err) {
      console.error('Failed to update task status', err);
    }
  };

  const loadTaskAttachments = async (taskId: string) => {
    try {
      setAttachmentsLoading(true);
      const data = await taskService.getTaskAttachments(taskId);
      setTaskAttachments(data);
    } finally {
      setAttachmentsLoading(false);
    }
  };

  const loadTaskNotes = async (taskId: string) => {
    try {
      setNotesLoading(true);
      const data = await taskService.getTaskNotes(taskId);
      setTaskNotes(data);
    } finally {
      setNotesLoading(false);
    }
  };

  useEffect(() => {
    const taskId = selectedTask?.id;
    if (!taskId) {
      setTaskAttachments([]);
      setTaskNotes([]);
      return;
    }
    setDetailTab('details');
    loadTaskAttachments(taskId);
    loadTaskNotes(taskId);
  }, [selectedTask?.id]);

  const handleAttachmentUpload = async (file: File) => {
    if (!selectedTask) return;
    const result = await taskService.uploadTaskAttachment(selectedTask.id, file);
    if (!result.success) {
      throw new Error(result.error || 'Failed to upload attachment');
    }
    // Wait a moment for the database to update, then refresh
    await new Promise(resolve => setTimeout(resolve, 500));
    await loadTaskAttachments(selectedTask.id);
  };

  const handleAddNote = async (note: string, progress?: number) => {
    if (!selectedTask) return;
    const result = await taskService.addTaskNote(selectedTask.id, {
      notes: note,
      progress,
    });
    if (!result.success) {
      throw new Error(result.error || 'Failed to add note');
    }
    await Promise.all([loadTaskNotes(selectedTask.id), loadTasks()]);
  };

  const renderFiltersSection = () => (
    <>
      <section className="task-hero">
        <div>
          <h1>📋 Task Command Center</h1>
          <p>Monitor every task in the organization, apply smart filters, and drill into full context.</p>
        </div>
        <div>
          <Button variant="ghost" onClick={loadTasks} disabled={loading}>
            {loading ? 'Syncing…' : '⟳ Refresh'}
          </Button>
        </div>
      </section>

      {error && (
        <div className="inline-error">
          {error}
          <Button variant="secondary" size="small" onClick={loadTasks}>
            Retry
          </Button>
        </div>
      )}

      <section className="filters-panel">
        <div className="filters-grid">
          <div>
            <label>Status</label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
            >
              {statusOptions.map(option => (
                <option key={option} value={option}>
                  {option === 'all' ? 'All statuses' : option.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label>Assignment</label>
            <select
              value={filters.assignment}
              onChange={(e) => handleFilterChange('assignment', e.target.value)}
            >
              <option value="all">All</option>
              <option value="assigned">Assigned</option>
              <option value="unassigned">Unassigned</option>
            </select>
          </div>

          <div>
            <label>Employee {employees.length > 0 && `(${employees.length})`}</label>
            <select
              value={filters.employee}
              onChange={(e) => handleFilterChange('employee', e.target.value)}
              disabled={employeesLoading}
            >
              <option value="all">All employees</option>
              {employeesLoading ? (
                <option value="" disabled>Loading employees...</option>
              ) : employees.length > 0 ? (
                employees.map(emp => (
                  <option key={emp.id} value={emp.name}>
                    {emp.name}
                  </option>
                ))
              ) : (
                <option value="" disabled>No employees available</option>
              )}
            </select>
            {!employeesLoading && employees.length === 0 && allEmployees.length > 0 && (
              <small style={{ color: '#ff6b6b', display: 'block', marginTop: '4px' }}>
                No active employees found (Total: {allEmployees.length})
              </small>
            )}
            {!employeesLoading && allEmployees.length === 0 && (
              <small style={{ color: '#ff6b6b', display: 'block', marginTop: '4px' }}>
                Failed to load employees. Check console for details.
              </small>
            )}
          </div>

          <div>
            <label>Objective</label>
            <select
              value={filters.objective}
              onChange={(e) => handleFilterChange('objective', e.target.value)}
            >
              <option value="all">All objectives</option>
              {objectives.map(obj => (
                <option key={obj} value={obj}>
                  {obj}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label>Priority</label>
            <select
              value={filters.priority}
              onChange={(e) => handleFilterChange('priority', e.target.value)}
            >
              {priorityOptions.map(option => (
                <option key={option} value={option}>
                  {option === 'all' ? 'All priorities' : option.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label>Sort by</label>
            <select
              value={filters.sortBy}
              onChange={(e) => handleFilterChange('sortBy', e.target.value)}
            >
              <option value="recent">Recently created</option>
              <option value="due_date">Due date</option>
              <option value="priority">Priority</option>
              <option value="status">Status</option>
            </select>
          </div>

          <div>
            <label>Search</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              placeholder="Search descriptions"
            />
          </div>

          <div>
            <label>Start date</label>
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => handleFilterChange('startDate', e.target.value)}
            />
          </div>

          <div>
            <label>End date</label>
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) => handleFilterChange('endDate', e.target.value)}
            />
          </div>
        </div>
      </section>
    </>
  );

  const renderSummarySection = () => (
    <div className="summary-row">
      <div className="summary-card">
        <p className="label">Total tasks</p>
        <p className="value">{summary.total}</p>
      </div>
      <div className="summary-card">
        <p className="label">In progress</p>
        <p className="value">{summary.inProgress}</p>
      </div>
      <div className="summary-card">
        <p className="label">Completed</p>
        <p className="value">{summary.completed}</p>
      </div>
      <div className="summary-card">
        <p className="label">Overdue</p>
        <p className="value">{summary.overdue}</p>
      </div>
    </div>
  );

  const handleSelectTask = (task: Task) => {
    setSelectedTask(prev => (prev?.id === task.id ? null : task));
    if (selectedTask?.id === task.id) {
      setTaskAttachments([]);
      setTaskNotes([]);
    } else {
      setDetailTab('details');
    }
  };

  const openTaskDetail = (task: Task) => {
    if (!task?.id) return;
    localStorage.setItem('current_task_id', task.id);
    navigate(`/admin/task-management/${task.id}`);
  };

  const renderCardLayout = () => {
    if (loading) {
      return <div className="loading">Loading tasks…</div>;
    }

    if (filteredTasks.length === 0) {
      return (
        <div className="no-employees">
          <p>No tasks match the current filters.</p>
        </div>
      );
    }

    return (
      <section className="task-cards-layout">
        <div className="task-cards-grid">
          {filteredTasks.map(task => {
            const description = task.task_description || task.description || 'Untitled task';
            const objectiveTitle = task.objectives?.title || '—';
            const strategicObjective = task.strategic_objective || objectiveTitle;
            const preNumber = task.pre_number || task.objectives?.pre_number || '—';
            const assignee =
              task.employees?.name ||
              (typeof task.assigned_to === 'string' ? task.assigned_to : 'Unassigned');
            const progress = task.completion_percentage ?? 0;

            return (
              <article
                key={task.id}
                data-task-id={task.id}
                className={`task-card ${selectedTask?.id === task.id ? 'active' : ''} ${pendingTaskId === task.id ? 'highlighted' : ''}`}
                onClick={() => openTaskDetail(task)}
              >
                <div className="task-card-header">
                  <div>
                    <p className="task-card-eyebrow">{preNumber !== '—' ? preNumber : 'Task'}</p>
                    <h4>{description}</h4>
                    {task.strategic_metadata?.predefined_process && (
                      <span className="process-type-badge predefined">📋 Predefined Process</span>
                    )}
                    {task.strategic_metadata && !task.strategic_metadata.predefined_process && (
                      <span className="process-type-badge ai-generated">🤖 AI Generated</span>
                    )}
                  </div>
                  <span className={`status-pill ${task.status}`}>
                    {task.status.replace('_', ' ')}
                  </span>
                </div>

                <div className="task-card-meta">
                  <div>
                    <p className="label">Objective</p>
                    <strong>{objectiveTitle}</strong>
                  </div>
                  <div>
                    <p className="label">Strategic Objective</p>
                    <strong>{strategicObjective}</strong>
                  </div>
                  <div>
                    <p className="label">Assignee</p>
                    <strong>{assignee || 'Unassigned'}</strong>
                  </div>
                  <div>
                    <p className="label">Priority</p>
                    <span className={`priority-badge ${task.priority || 'low'}`}>
                      {(task.priority || 'low').toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="label">Due</p>
                    <strong>{formatDate(task.due_date)}</strong>
                  </div>
                  <div>
                    <p className="label">Progress</p>
                    <strong>{progress}%</strong>
                  </div>
                </div>

                <div className="task-card-actions" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="ghost"
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectTask(task);
                    }}
                  >
                    👁️ Quick Preview
                  </Button>
                  {task.strategic_metadata && (
                    <Button
                      variant="secondary"
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (selectedTask?.id === task.id) {
                          setDetailTab('details');
                        } else {
                          handleSelectTask(task);
                          setTimeout(() => setDetailTab('details'), 100);
                        }
                      }}
                    >
                      📊 View Strategic Analysis
                    </Button>
                  )}
                  <Button
                    variant="primary"
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (selectedTask?.id === task.id) {
                        setDetailTab('recommendations');
                      } else {
                        handleSelectTask(task);
                        setTimeout(() => setDetailTab('recommendations'), 100);
                      }
                    }}
                  >
                    👥 RAG Recommendations
                  </Button>
                </div>

                <div className="task-card-footer">
                  <span>Created: {formatDate(task.created_at)}</span>
                  <span>Assigned: {formatDate(task.assigned_at)}</span>
                </div>

                {selectedTask?.id === task.id && (
                  <div
                    className="task-card-detail"
                    onClick={(evt) => evt.stopPropagation()}
                  >
                    <TaskDetailPanel
                      task={task}
                      activeTab={detailTab}
                      onTabChange={setDetailTab}
                      attachments={taskAttachments}
                      notes={taskNotes}
                      attachmentsLoading={attachmentsLoading}
                      notesLoading={notesLoading}
                      onUploadAttachment={handleAttachmentUpload}
                      onAddNote={handleAddNote}
                      onRefreshAttachments={() => loadTaskAttachments(task.id)}
                      onRefreshNotes={() => loadTaskNotes(task.id)}
                      onStatusChange={handleStatusChange}
                      onTaskUpdated={loadTasks}
                      variant="inline"
                    />
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </section>
    );
  };

  return (
    <div className="admin-task-page">
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'list' ? 'active' : ''}`}
          onClick={() => setActiveTab('list')}
        >
          📋 Task List
        </button>
        <button
          className={`tab ${activeTab === 'ai' ? 'active' : ''}`}
          onClick={() => setActiveTab('ai')}
        >
          🤖 AI/RAG Builder
        </button>
      </div>

      {activeTab === 'list' ? (
        <>
          {renderFiltersSection()}
          {renderSummarySection()}
          {renderCardLayout()}
        </>
      ) : (
        <AITaskBuilder onTasksGenerated={loadTasks} />
      )}
    </div>
  );
};

interface TaskDetailPanelProps {
  task: Task;
  activeTab: 'details' | 'attachments' | 'notes' | 'recommendations';
  onTabChange: (tab: 'details' | 'attachments' | 'notes' | 'recommendations') => void;
  attachments: TaskAttachment[];
  notes: TaskNote[];
  attachmentsLoading: boolean;
  notesLoading: boolean;
  onUploadAttachment: (file: File) => Promise<void>;
  onAddNote: (note: string, progress?: number) => Promise<void>;
  onRefreshAttachments: () => void;
  onRefreshNotes: () => void;
  onStatusChange: (status: Task['status']) => void;
  onTaskUpdated?: () => void;
  variant?: 'inline' | 'sidebar';
}

const TaskDetailPanel: React.FC<TaskDetailPanelProps> = ({
  task,
  activeTab,
  onTabChange,
  attachments,
  notes,
  attachmentsLoading,
  notesLoading,
  onUploadAttachment,
  onAddNote,
  onRefreshAttachments,
  onRefreshNotes,
  onStatusChange,
  onTaskUpdated,
  variant = 'sidebar',
}) => {
  const [noteText, setNoteText] = useState('');
  const [noteProgress, setNoteProgress] = useState(task.completion_percentage ?? 0);
  const [noteSubmitting, setNoteSubmitting] = useState(false);
  const [noteError, setNoteError] = useState('');
  const [noteMessage, setNoteMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadMessage, setUploadMessage] = useState('');

  useEffect(() => {
    setNoteText('');
    setNoteProgress(task.completion_percentage ?? 0);
    setNoteSubmitting(false);
    setNoteError('');
    setNoteMessage('');
    setSelectedFile(null);
    setUploading(false);
    setUploadError('');
    setUploadMessage('');
  }, [task.id]);

  const handleAttachmentSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedFile) {
      setUploadError('Please choose a file to upload');
      return;
    }
    try {
      setUploading(true);
      setUploadError('');
      await onUploadAttachment(selectedFile);
      setUploadMessage('Attachment uploaded successfully.');
      setSelectedFile(null);
    } catch (err: any) {
      setUploadError(err?.message || 'Failed to upload attachment');
    } finally {
      setUploading(false);
    }
  };

  const handleNoteSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!noteText.trim()) {
      setNoteError('Please add note content before submitting');
      return;
    }
    try {
      setNoteSubmitting(true);
      setNoteError('');
      setNoteMessage('');
      await onAddNote(noteText.trim(), noteProgress);
      setNoteMessage('Note added successfully.');
      setNoteText('');
    } catch (err: any) {
      setNoteError(err?.message || 'Failed to add note');
    } finally {
      setNoteSubmitting(false);
    }
  };

  const metadata = task.strategic_metadata;
  const metadataFields = [
    { label: '🎯 Context', value: metadata?.context },
    { label: '🎯 Objective', value: metadata?.objective },
    { label: '🔄 Process', value: metadata?.process },
    { label: '📦 Delivery', value: metadata?.delivery },
    { label: '📊 Reporting Requirements', value: metadata?.reporting_requirements },
    { label: 'Validation Score', value: metadata?.validation_score },
    { label: 'Execution Context', value: metadata?.q4_execution_context },
    { label: 'Process Applied', value: metadata?.process_applied },
    { label: 'Goal Type', value: metadata?.goal_type },
  ].filter(item => item.value);

  const statusShortcuts: Task['status'][] = ['in_progress', 'completed', 'pending'];

  const renderAttachments = () => {
    if (attachmentsLoading) {
      return <div className="inline-loading">Loading attachments…</div>;
    }
    if (!attachments.length) {
      return <p className="muted-text">No attachments uploaded yet.</p>;
    }
    return (
      <ul className="attachment-list">
        {attachments.map((attachment, idx) => (
          <li key={`${attachment.update_id}-${idx}`} className="attachment-item">
            <div>
              <strong>{attachment.filename || 'Attachment'}</strong>
              <p>{attachment.file_type || 'File'} · {formatFileSize(attachment.file_size)}</p>
            </div>
            <div>
              <p className="label">Uploaded</p>
              <span>{formatDateTime(attachment.created_at)}</span>
            </div>
            <div>
              <p className="label">By</p>
              <span>{attachment.employee_name || 'Unknown'}</span>
            </div>
            {attachment.public_url && (
              <a
                href={attachment.public_url}
                target="_blank"
                rel="noreferrer"
                className="link-button"
              >
                Open
              </a>
            )}
          </li>
        ))}
      </ul>
    );
  };

  const renderNotes = () => {
    if (notesLoading) {
      return <div className="inline-loading">Loading notes…</div>;
    }
    if (!notes.length) {
      return <p className="muted-text">No notes yet. Add the first update below.</p>;
    }
    return (
      <div className="notes-list">
        {notes.map(note => (
          <div key={note.id} className="note-card">
            <div className="note-card-header">
              <div>
                <strong>{note.employee_name || 'Unknown'}</strong>
                <span>{note.employee_role || 'Team member'}</span>
              </div>
              <span>{formatDateTime(note.created_at)}</span>
            </div>
            <p>{note.notes}</p>
            <div className="note-card-meta">
              <span>Progress: {note.progress ?? 0}%</span>
              {note.attachments_count ? (
                <span>📎 {note.attachments_count} attachment(s)</span>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const panelClass = ['task-detail-panel', variant === 'inline' ? 'inline' : '']
    .filter(Boolean)
    .join(' ');

  return (
    <div className={panelClass}>
      {variant !== 'inline' && (
        <div className="detail-heading">
          <div>
            <p className="drawer-eyebrow">Selected Task</p>
            <h3>{task.task_description || task.description || 'Untitled task'}</h3>
          </div>
          <span className={`status-pill ${task.status}`}>
            {task.status.replace('_', ' ')}
          </span>
        </div>
      )}

      <div className="detail-tabs">
        {(['details', 'attachments', 'notes', 'recommendations'] as const).map(tab => (
          <button
            key={tab}
            className={`detail-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => onTabChange(tab)}
          >
            {tab === 'details' && 'Details'}
            {tab === 'attachments' && 'Attachments'}
            {tab === 'notes' && 'Notes'}
            {tab === 'recommendations' && '👥 Recommendations'}
          </button>
        ))}
      </div>

      {activeTab === 'details' && (
        <div className="detail-section">
          <div className="detail-overview-grid">
            <div>
              <p className="label">Priority</p>
              <span className={`priority-badge ${task.priority || 'low'}`}>
                {(task.priority || 'low').toUpperCase()}
              </span>
            </div>
            <div>
              <p className="label">Due date</p>
              <strong>{formatDate(task.due_date)}</strong>
            </div>
            <div>
              <p className="label">Strategic Objective</p>
              <strong>{task.strategic_objective || task.objectives?.title || '—'}</strong>
            </div>
            <div>
              <p className="label">Pre Number</p>
              <strong>{task.pre_number || task.objectives?.pre_number || '—'}</strong>
            </div>
            <div>
              <p className="label">Progress</p>
              <strong>{task.completion_percentage ?? 0}%</strong>
            </div>
            <div>
              <p className="label">Assignee</p>
              <strong>
                {task.employees?.name ||
                  (typeof task.assigned_to === 'string' ? task.assigned_to : 'Unassigned')}
              </strong>
            </div>
          </div>

          <div className="detail-objective-card">
            <p className="label">Description</p>
            <p>{task.task_description || task.description || 'No description provided.'}</p>
          </div>

          {metadataFields.length > 0 && (
            <div className="strategic-analysis-card">
              <div className="strategic-analysis-header">
                <h4>
                  {metadata?.predefined_process 
                    ? '📋 Predefined Process Strategic Analysis'
                    : '🤖 AI Strategic Analysis'}
                </h4>
                {metadata?.predefined_process && (
                  <span className="process-badge">Predefined: {metadata?.process_applied || metadata?.goal_type || 'Standard Process'}</span>
                )}
                {metadata?.recommended_role && (
                  <span className="role-badge">Recommended Role: {metadata.recommended_role}</span>
                )}
              </div>
              <div className="strategic-meta">
                {metadataFields.map(field => (
                  <div key={field.label}>
                    <p className="label">{field.label}</p>
                    <p>{field.value}</p>
                  </div>
                ))}
              </div>
              {metadata?.strategic_analysis && typeof metadata.strategic_analysis === 'object' && (
                <div className="strategic-analysis-detailed">
                  <h5>Detailed Analysis</h5>
                  {Object.entries(metadata.strategic_analysis).map(([key, value]) => (
                    <div key={key}>
                      <p className="label">{key.replace(/_/g, ' ').toUpperCase()}</p>
                      <p>{String(value)}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="detail-actions">
            {statusShortcuts.map(status => (
              <Button
                key={status}
                variant={task.status === status ? 'success' : 'secondary'}
                size="small"
                onClick={() => onStatusChange(status)}
                disabled={task.status === status}
              >
                {status.replace('_', ' ')}
              </Button>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'attachments' && (
        <div className="detail-section">
          <div className="section-header">
            <div>
              <h4>Attachments</h4>
              <p className="muted-text">Files shared for this task.</p>
            </div>
            <Button variant="ghost" size="small" onClick={onRefreshAttachments}>
              Refresh
            </Button>
          </div>

          {renderAttachments()}

          <form className="attachment-upload" onSubmit={handleAttachmentSubmit}>
            <label>
              Upload new file
              <input
                type="file"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              />
            </label>
            <Button type="submit" variant="primary" disabled={uploading}>
              {uploading ? 'Uploading…' : 'Upload'}
            </Button>
          </form>
          {uploadError && <p className="error-text">{uploadError}</p>}
          {uploadMessage && <p className="success-text">{uploadMessage}</p>}
        </div>
      )}

      {activeTab === 'notes' && (
        <div className="detail-section">
          <div className="section-header">
            <div>
              <h4>Notes & Updates</h4>
              <p className="muted-text">Track conversations and progress updates.</p>
            </div>
            <Button variant="ghost" size="small" onClick={onRefreshNotes}>
              Refresh
            </Button>
          </div>

          {renderNotes()}

          <form className="note-form" onSubmit={handleNoteSubmit}>
            <label>
              Add note
              <textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Summarize updates, blockers, or decisions..."
              />
            </label>
            <label className="range-label">
              Progress ({noteProgress}%)
              <input
                type="range"
                min={0}
                max={100}
                value={noteProgress}
                onChange={(e) => setNoteProgress(Number(e.target.value))}
              />
            </label>
            <div className="note-form-actions">
              <Button type="submit" variant="primary" disabled={noteSubmitting}>
                {noteSubmitting ? 'Posting…' : 'Post note'}
              </Button>
              {noteError && <p className="error-text">{noteError}</p>}
              {noteMessage && <p className="success-text">{noteMessage}</p>}
            </div>
          </form>
        </div>
      )}

      {activeTab === 'recommendations' && (
        <div className="detail-section">
          <RAGRecommendations
            task={task}
            onRecommendationApplied={async () => {
              onTaskUpdated?.();
            }}
          />
        </div>
      )}
    </div>
  );
};

const formatDate = (value?: string) => {
  if (!value) return 'Not set';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return date.toLocaleDateString();
};

const formatDateTime = (value?: string) => {
  if (!value) return 'Not set';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 16);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
};

const formatFileSize = (bytes?: number) => {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default TaskManagement;

