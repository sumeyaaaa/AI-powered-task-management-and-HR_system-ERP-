import React, { useEffect, useMemo, useState } from 'react';
import { taskService } from '../../services/task';
import { useAuth } from '../../contexts/AuthContext';
import { Task, TaskAttachment, TaskNote } from '../../types';
import { Button } from '../../components/Common/UI/Button';
import { Card } from '../../components/Common/UI/Card';
import './TaskManagement.css';

type StatusFilter = 'all' | 'not_started' | 'in_progress' | 'completed' | 'waiting';
type TabType = 'tasks' | 'propose' | 'progress';

const TaskManagement: React.FC = () => {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [pendingTaskId, setPendingTaskId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('tasks');
  const [detailTab, setDetailTab] = useState<'details' | 'attachments' | 'notes'>('details');
  const [taskNotes, setTaskNotes] = useState<TaskNote[]>([]);
  const [taskAttachments, setTaskAttachments] = useState<TaskAttachment[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);
  const [filters, setFilters] = useState({
    status: 'all' as StatusFilter,
    objective: 'all',
    sortBy: 'due_date' as 'due_date' | 'priority' | 'status' | 'recent',
  });

  // Propose task form state (moved to top level to fix hooks error)
  const [proposeFormData, setProposeFormData] = useState({
    task_description: '',
    detailed_description: '',
    priority: 'medium' as 'low' | 'medium' | 'high',
    due_date: '',
  });
  const [proposeSubmitting, setProposeSubmitting] = useState(false);
  const [proposeError, setProposeError] = useState('');
  const [proposeSuccess, setProposeSuccess] = useState('');

  useEffect(() => {
    if (activeTab === 'tasks') {
    loadTasks();
    }
  }, [activeTab]);

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
    if (pendingTaskId && tasks.length > 0 && activeTab === 'tasks') {
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
  }, [tasks, pendingTaskId, activeTab]);

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError('');
      // Use getTasks with employee filter - backend filters by current user
      const data = await taskService.getTasks();
      const normalized = Array.isArray(data)
        ? data
        : Array.isArray((data as any)?.tasks)
          ? (data as any).tasks
          : [];
      // Backend already filters tasks for employees, so use all returned tasks
      setTasks(normalized);
    } catch (err) {
      setError('Unable to load tasks. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

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
        if (filters.objective !== 'all' && task.objectives?.title !== filters.objective) return false;
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
            return (b.updated_at || b.created_at || '').localeCompare(a.updated_at || a.created_at || '');
        }
      });
  }, [tasks, filters]);

  useEffect(() => {
    if (selectedTask) {
      loadTaskAttachments(selectedTask.id);
      loadTaskNotes(selectedTask.id);
    }
  }, [selectedTask]);

  const loadTaskAttachments = async (taskId: string) => {
    try {
      setAttachmentsLoading(true);
      const attachments = await taskService.getTaskAttachments(taskId);
      setTaskAttachments(attachments);
    } catch (err) {
      console.error('Failed to load attachments:', err);
    } finally {
      setAttachmentsLoading(false);
    }
  };

  const loadTaskNotes = async (taskId: string) => {
    try {
      setNotesLoading(true);
      const notes = await taskService.getTaskNotes(taskId);
      setTaskNotes(notes);
    } catch (err) {
      console.error('Failed to load notes:', err);
    } finally {
      setNotesLoading(false);
    }
  };

  const handleAttachmentUpload = async (file: File) => {
    if (!selectedTask) return;
    try {
      const result = await taskService.uploadTaskAttachment(selectedTask.id, file);
      if (!result.success) {
        throw new Error(result.error || 'Failed to upload attachment');
      }
      // Wait a moment for the database to update, then refresh
      await new Promise(resolve => setTimeout(resolve, 500));
      await loadTaskAttachments(selectedTask.id);
    } catch (err: any) {
      throw new Error(err?.message || 'Failed to upload attachment');
    }
  };

  const handleAddNote = async (note: string, progress?: number) => {
    if (!selectedTask) return;
    try {
      await taskService.addTaskNote(selectedTask.id, {
        notes: note,
        progress: progress ?? selectedTask.completion_percentage ?? 0
      });
      await loadTaskNotes(selectedTask.id);
      await loadTasks(); // Refresh task list to update progress
    } catch (err: any) {
      throw new Error(err?.message || 'Failed to add note');
    }
  };

  const handleStatusChange = async (status: Task['status']) => {
    if (!selectedTask) return;
    try {
      await taskService.updateTaskStatus(selectedTask.id, status);
      await loadTasks();
      setSelectedTask(prev => prev ? { ...prev, status } : null);
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const formatDate = (value?: string) => {
    if (!value) return 'Not set';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value.slice(0, 10);
    return date.toLocaleDateString();
  };

  const renderFiltersSection = () => {
    return (
      <div className="task-filters">
        <div className="filter-group">
          <label>Status</label>
          <select
            value={filters.status}
            onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value as StatusFilter }))}
          >
            <option value="all">All</option>
            <option value="not_started">Not Started</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="waiting">Waiting</option>
          </select>
      </div>

        <div className="filter-group">
          <label>Objective</label>
          <select
            value={filters.objective}
            onChange={(e) => setFilters(prev => ({ ...prev, objective: e.target.value }))}
          >
            <option value="all">All Objectives</option>
            {objectives.map(obj => (
              <option key={obj} value={obj}>{obj}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Sort By</label>
          <select
            value={filters.sortBy}
            onChange={(e) => setFilters(prev => ({ ...prev, sortBy: e.target.value as any }))}
          >
            <option value="due_date">Due Date</option>
            <option value="priority">Priority</option>
            <option value="status">Status</option>
            <option value="recent">Recently Updated</option>
          </select>
        </div>
      </div>
    );
  };

  const renderTaskCards = () => {
    if (loading) {
      return <div className="loading">Loading tasks...</div>;
    }

    if (error) {
      return <div className="error">{error}</div>;
    }

    if (filteredTasks.length === 0) {
      return (
          <Card className="no-tasks-card">
            <div className="no-tasks">
              <h3>No tasks found</h3>
              <p>You don't have any tasks matching the current filter.</p>
            </div>
          </Card>
      );
    }

    return (
      <div className="task-cards-grid">
        {filteredTasks.map(task => {
          const description = task.task_description || task.description || 'No description';
          const objectiveTitle = task.objectives?.title || 'No Objective';
          const assignee = task.employees?.name || 'Unassigned';
          const progress = task.completion_percentage ?? 0;
          const preNumber = task.pre_number || task.objectives?.pre_number || '—';

          return (
            <article
              key={task.id}
              data-task-id={task.id}
              className={`task-card ${selectedTask?.id === task.id ? 'active' : ''} ${pendingTaskId === task.id ? 'highlighted' : ''}`}
              onClick={() => handleSelectTask(task)}
            >
              <div className="task-card-header">
                <div>
                  <p className="task-card-eyebrow">{preNumber !== '—' ? preNumber : 'Task'}</p>
                  <h4>{description}</h4>
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
    );
  };

  const handleSelectTask = (task: Task) => {
    if (selectedTask?.id === task.id) {
      setSelectedTask(null);
      setDetailTab('details');
    } else {
      setSelectedTask(task);
      setDetailTab('details');
    }
  };

  const renderProgressTab = () => {
    const totalTasks = tasks.length;
    const completedTasks = tasks.filter(t => t.status === 'completed').length;
    const inProgressTasks = tasks.filter(t => t.status === 'in_progress').length;
    const pendingTasks = tasks.filter(t => t.status === 'not_started').length;
    const completionRate = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

    const recentTasks = [...tasks]
      .sort((a, b) => (b.updated_at || b.created_at || '').localeCompare(a.updated_at || a.created_at || ''))
      .slice(0, 5);

    return (
      <div className="progress-tab">
        <div className="progress-metrics">
          <div className="metric-card">
            <h3>Total Tasks</h3>
            <p className="metric-value">{totalTasks}</p>
          </div>
          <div className="metric-card">
            <h3>Completed</h3>
            <p className="metric-value">{completedTasks}</p>
          </div>
          <div className="metric-card">
            <h3>In Progress</h3>
            <p className="metric-value">{inProgressTasks}</p>
          </div>
          <div className="metric-card">
            <h3>Pending</h3>
            <p className="metric-value">{pendingTasks}</p>
          </div>
                </div>

        <div className="completion-section">
          <h3>Overall Completion: {completionRate.toFixed(1)}%</h3>
          <div className="progress-bar-container">
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                style={{ width: `${completionRate}%` }}
              />
            </div>
          </div>
        </div>

        <div className="status-breakdown">
          <h3>Task Breakdown by Status</h3>
          <div className="breakdown-bars">
            <div className="breakdown-item">
              <span>Completed</span>
              <div className="breakdown-bar">
                <div className="breakdown-fill completed" style={{ width: `${totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0}%` }} />
              </div>
              <span>{completedTasks}</span>
            </div>
            <div className="breakdown-item">
              <span>In Progress</span>
              <div className="breakdown-bar">
                <div className="breakdown-fill in-progress" style={{ width: `${totalTasks > 0 ? (inProgressTasks / totalTasks) * 100 : 0}%` }} />
              </div>
              <span>{inProgressTasks}</span>
            </div>
            <div className="breakdown-item">
              <span>Pending</span>
              <div className="breakdown-bar">
                <div className="breakdown-fill pending" style={{ width: `${totalTasks > 0 ? (pendingTasks / totalTasks) * 100 : 0}%` }} />
              </div>
              <span>{pendingTasks}</span>
            </div>
          </div>
        </div>

        <div className="recent-activity">
          <h3>Recent Activity</h3>
          {recentTasks.length === 0 ? (
            <p className="muted-text">No recent activity</p>
          ) : (
            <div className="activity-list">
              {recentTasks.map(task => {
                const statusIcon = task.status === 'completed' ? '✅' : task.status === 'in_progress' ? '🔄' : '⏳';
                return (
                  <div key={task.id} className="activity-item">
                    <span className="activity-icon">{statusIcon}</span>
                    <div className="activity-content">
                      <strong>{task.task_description || task.description || 'Untitled'}</strong>
                      <span>{task.completion_percentage ?? 0}% - {formatDate(task.updated_at || task.created_at)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
                </div>
              </div>
    );
  };

  const handleProposeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!proposeFormData.task_description || !proposeFormData.detailed_description) {
      setProposeError('Please fill in all required fields');
      return;
    }

    try {
      setProposeSubmitting(true);
      setProposeError('');
      setProposeSuccess('');

      const fullDescription = `${proposeFormData.task_description} - ${proposeFormData.detailed_description}`;
      const result = await taskService.createTask({
        task_description: fullDescription,
        priority: proposeFormData.priority,
        due_date: proposeFormData.due_date || undefined,
      } as any);

      if (result.success) {
        setProposeSuccess('✅ Task proposal submitted! Waiting for admin approval.');
        setProposeFormData({
          task_description: '',
          detailed_description: '',
          priority: 'medium',
          due_date: '',
        });
      } else {
        setProposeError(result.error || 'Failed to submit proposal');
      }
    } catch (err: any) {
      setProposeError(err?.message || 'Failed to submit proposal');
    } finally {
      setProposeSubmitting(false);
    }
  };

  const renderProposeTaskTab = () => {

    return (
      <div className="propose-task-tab">
        <h3>💡 Propose New Task</h3>
        <p className="muted-text">Suggest a new task that needs to be completed</p>
        <Card>
          <form className="propose-task-form" onSubmit={handleProposeSubmit}>
            <label>
              Task Description*
              <input
                type="text"
                placeholder="What needs to be done?"
                value={proposeFormData.task_description}
                onChange={(e) => setProposeFormData(prev => ({ ...prev, task_description: e.target.value }))}
                required
              />
            </label>
            <label>
              Detailed Description*
              <textarea
                placeholder="Detailed description of the task and why it's important..."
                rows={5}
                value={proposeFormData.detailed_description}
                onChange={(e) => setProposeFormData(prev => ({ ...prev, detailed_description: e.target.value }))}
                required
              />
            </label>
            <div className="form-row">
              <label>
                Suggested Priority
                <select
                  value={proposeFormData.priority}
                  onChange={(e) => setProposeFormData(prev => ({ ...prev, priority: e.target.value as any }))}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </label>
              <label>
                Suggested Due Date
                <input
                  type="date"
                  min={new Date().toISOString().split('T')[0]}
                  value={proposeFormData.due_date}
                  onChange={(e) => setProposeFormData(prev => ({ ...prev, due_date: e.target.value }))}
                />
              </label>
            </div>
            {proposeError && <p className="error-text">{proposeError}</p>}
            {proposeSuccess && <p className="success-text">{proposeSuccess}</p>}
            <Button type="submit" variant="primary" disabled={proposeSubmitting}>
              {proposeSubmitting ? 'Submitting…' : '📤 Submit Proposal'}
                  </Button>
          </form>
        </Card>
      </div>
    );
  };

  return (
    <div className="employee-task-page">
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'tasks' ? 'active' : ''}`}
          onClick={() => setActiveTab('tasks')}
        >
          📋 My Tasks
        </button>
        <button
          className={`tab ${activeTab === 'propose' ? 'active' : ''}`}
          onClick={() => setActiveTab('propose')}
        >
          💡 Propose Task
        </button>
        <button
          className={`tab ${activeTab === 'progress' ? 'active' : ''}`}
          onClick={() => setActiveTab('progress')}
        >
          📈 My Progress
        </button>
      </div>

      {activeTab === 'tasks' && (
        <>
          {renderFiltersSection()}
          {renderTaskCards()}
                  </>
                )}

      {activeTab === 'propose' && renderProposeTaskTab()}

      {activeTab === 'progress' && renderProgressTab()}
    </div>
  );
};

// TaskDetailPanel component (similar to admin version but employee-focused)
interface TaskDetailPanelProps {
  task: Task;
  activeTab: 'details' | 'attachments' | 'notes';
  onTabChange: (tab: 'details' | 'attachments' | 'notes') => void;
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
      setNoteError('Note content is required');
      return;
    }
    try {
      setNoteSubmitting(true);
      setNoteError('');
      await onAddNote(noteText, noteProgress);
      setNoteMessage('Note added successfully.');
      setNoteText('');
    } catch (err: any) {
      setNoteError(err?.message || 'Failed to add note');
    } finally {
      setNoteSubmitting(false);
    }
  };

  const formatDate = (value?: string) => {
    if (!value) return 'Not set';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value.slice(0, 10);
    return date.toLocaleDateString();
  };

  const metadata = task.strategic_metadata;
  const metadataFields = [
    { label: '🎯 Context', value: metadata?.context },
    { label: '🎯 Objective', value: metadata?.objective },
    { label: '🔄 Process', value: metadata?.process },
    { label: '📦 Delivery', value: metadata?.delivery },
    { label: '📊 Reporting Requirements', value: metadata?.reporting_requirements },
  ].filter(item => item.value);

  const statusShortcuts: Task['status'][] = ['in_progress', 'completed', 'waiting'];

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
              <p>{attachment.file_type || 'File'}</p>
            </div>
            <div>
              <p className="label">Uploaded</p>
              <span>{formatDate(attachment.created_at)}</span>
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
              <span>{formatDate(note.created_at)}</span>
            </div>
            <p>{note.notes}</p>
            <div className="note-card-meta">
              <span>Progress: {note.progress ?? 0}%</span>
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
      <div className="detail-tabs">
        {(['details', 'attachments', 'notes'] as const).map(tab => (
              <button 
            key={tab}
            className={`detail-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => onTabChange(tab)}
              >
            {tab === 'details' && 'Details'}
            {tab === 'attachments' && '📎 Task Update'}
            {tab === 'notes' && 'Notes'}
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
              <h4>AI Strategic Analysis</h4>
              <div className="strategic-meta">
                {metadataFields.map(field => (
                  <div key={field.label}>
                    <p className="label">{field.label}</p>
                    <p>{field.value}</p>
                  </div>
                ))}
              </div>
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
    </div>
  );
};

export default TaskManagement;
