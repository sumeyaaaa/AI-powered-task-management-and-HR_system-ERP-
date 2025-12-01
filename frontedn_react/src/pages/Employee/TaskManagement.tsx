import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { taskService } from '../../services/task';
import { useAuth } from '../../contexts/AuthContext';
import { Task } from '../../types';
import { Button } from '../../components/Common/UI/Button';
import { Card } from '../../components/Common/UI/Card';
import './TaskManagement.css';

type StatusFilter = 'all' | 'not_started' | 'in_progress' | 'completed' | 'waiting';
type TabType = 'tasks' | 'propose' | 'progress' | 'collaboration';

const TaskManagement: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [collaborationTasks, setCollaborationTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [collaborationLoading, setCollaborationLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [pendingTaskId, setPendingTaskId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('tasks');
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
    } else if (activeTab === 'collaboration') {
      loadCollaborationTasks();
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
        // Navigate to task detail page
        navigate(`/employee/task-management/${pendingTaskId}`);
        setPendingTaskId(null);
      } else {
        // Task not found, clear pending ID
        console.warn(`Task ${pendingTaskId} not found in loaded tasks`);
        setPendingTaskId(null);
      }
    }
  }, [tasks, pendingTaskId, activeTab, navigate]);

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

  const loadCollaborationTasks = async () => {
    try {
      setCollaborationLoading(true);
      setError('');
      const data = await taskService.getCollaborationTasks();
      setCollaborationTasks(Array.isArray(data) ? data : []);
    } catch (err) {
      setError('Unable to load collaboration tasks. Please try again later.');
    } finally {
      setCollaborationLoading(false);
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
    let filtered = [...tasks];

    if (filters.status !== 'all') {
      filtered = filtered.filter(task => task.status === filters.status);
    }

    if (filters.objective !== 'all') {
      filtered = filtered.filter(task => task.objectives?.title === filters.objective);
    }

    switch (filters.sortBy) {
      case 'due_date':
        filtered.sort((a, b) => {
          const aDate = a.due_date ? new Date(a.due_date).getTime() : 0;
          const bDate = b.due_date ? new Date(b.due_date).getTime() : 0;
          return aDate - bDate;
        });
        break;
      case 'priority':
        const priorityOrder = { high: 3, medium: 2, low: 1 };
        filtered.sort((a, b) => {
          const aPriority = priorityOrder[a.priority as keyof typeof priorityOrder] || 0;
          const bPriority = priorityOrder[b.priority as keyof typeof priorityOrder] || 0;
          return bPriority - aPriority;
        });
        break;
      case 'status':
        filtered.sort((a, b) => a.status.localeCompare(b.status));
        break;
      case 'recent':
        filtered.sort((a, b) => {
          const aDate = a.updated_at || a.created_at || '';
          const bDate = b.updated_at || b.created_at || '';
          return bDate.localeCompare(aDate);
        });
        break;
    }

    return filtered;
  }, [tasks, filters]);

  const formatDate = (value?: string) => {
    if (!value) return 'Not set';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value.slice(0, 10);
    return date.toLocaleDateString();
  };

  const renderCollaborationTab = () => {
    if (collaborationLoading) {
      return <div className="loading">Loading collaboration tasks...</div>;
    }

    if (error && activeTab === 'collaboration') {
      return <div className="error">{error}</div>;
    }

    if (collaborationTasks.length === 0) {
      return (
        <Card className="no-tasks-card">
          <div className="no-tasks">
            <h3>No collaboration tasks</h3>
            <p>You haven't been mentioned in any task notes yet. When someone mentions you in a task note, it will appear here.</p>
          </div>
        </Card>
      );
    }

    return (
      <div className="collaboration-tasks-section">
        <div className="section-header">
          <h2>🤝 Tasks I'm Mentioned In</h2>
          <p className="muted-text">These are tasks where you were mentioned in notes. You can add notes and attachments to collaborate.</p>
        </div>
        <div className="task-cards-grid">
          {collaborationTasks.map(task => {
            const description = task.task_description || task.description || 'No description';
            const objectiveTitle = task.objectives?.title || 'No Objective';
            const assignee = task.employees?.name || 'Unassigned';
            const progress = task.completion_percentage ?? 0;
            const preNumber = task.pre_number || task.objectives?.pre_number || '—';

            return (
              <article
                key={task.id}
                data-task-id={task.id}
                className="task-card collaboration-task"
                onClick={() => navigate(`/employee/task-management/${task.id}`)}
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
                    <p className="label">Assigned To</p>
                    <strong>{assignee}</strong>
                  </div>
                  <div>
                    <p className="label">Progress</p>
                    <strong>{progress}%</strong>
                  </div>
                </div>

                <div className="task-card-footer">
                  <span className="priority-badge">{task.priority}</span>
                  <span className="due-date">{formatDate(task.due_date)}</span>
                </div>
                <div className="collaboration-badge">
                  🤝 You're collaborating on this task
                </div>
              </article>
            );
          })}
        </div>
      </div>
    );
  };

  const renderFiltersSection = () => {
    return (
      <div className="filters-section">
        <div className="filter-group">
          <label>
            Status
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
          </label>
          <label>
            Objective
            <select
              value={filters.objective}
              onChange={(e) => setFilters(prev => ({ ...prev, objective: e.target.value }))}
            >
              <option value="all">All Objectives</option>
              {objectives.map(obj => (
                <option key={obj} value={obj}>{obj}</option>
              ))}
            </select>
          </label>
          <label>
            Sort By
            <select
              value={filters.sortBy}
              onChange={(e) => setFilters(prev => ({ ...prev, sortBy: e.target.value as any }))}
            >
              <option value="due_date">Due Date</option>
              <option value="priority">Priority</option>
              <option value="status">Status</option>
              <option value="recent">Recent</option>
            </select>
          </label>
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
              className={`task-card ${pendingTaskId === task.id ? 'highlighted' : ''}`}
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
            </article>
          );
        })}
      </div>
    );
  };

  const handleSelectTask = (task: Task) => {
    // Navigate to task detail page
    navigate(`/employee/task-management/${task.id}`);
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
        setProposeSuccess('Task created!');
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
        <button
          className={`tab ${activeTab === 'collaboration' ? 'active' : ''}`}
          onClick={() => setActiveTab('collaboration')}
        >
          🤝 Collaboration Tasks
        </button>
      </div>

      {activeTab === 'collaboration' && renderCollaborationTab()}

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

export default TaskManagement;
