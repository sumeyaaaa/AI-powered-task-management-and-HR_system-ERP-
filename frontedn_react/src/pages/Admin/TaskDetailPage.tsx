import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { taskService } from '../../services/task';
import { employeeService } from '../../services/employee';
import { Task, TaskAttachment, TaskNote } from '../../types';
import { Employee } from '../../types/employee';
import { Button } from '../../components/Common/UI/Button';
import { RAGRecommendations } from '../../components/TaskManagement/RAGRecommendations';
import './TaskDetailPage.css';

const TaskDetailPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  const [notes, setNotes] = useState<TaskNote[]>([]);
  const [attachments, setAttachments] = useState<TaskAttachment[]>([]);
  const [noteText, setNoteText] = useState('');
  const [noteProgress, setNoteProgress] = useState<number>(0);
  const [submittingNote, setSubmittingNote] = useState(false);
  const [uploading, setUploading] = useState(false);
  
  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [editData, setEditData] = useState<Partial<Task>>({});
  const [saving, setSaving] = useState(false);
  const [showStrategicAnalysis, setShowStrategicAnalysis] = useState(false);
  const [showEmployeeRecommendations, setShowEmployeeRecommendations] = useState(false);
  const [showAssignEmployee, setShowAssignEmployee] = useState(false);

  const loadTask = useCallback(async () => {
    if (!taskId) {
      setError('Task ID missing');
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError('');
      const response = await taskService.getTaskById(taskId);
      const nextTask = (response as any)?.task ?? response;
      setTask(nextTask);
      setNoteProgress(nextTask?.completion_percentage ?? 0);
    } catch (err) {
      setError('Failed to load task details');
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  const loadNotes = useCallback(async () => {
    if (!taskId) return;
    const data = await taskService.getTaskNotes(taskId);
    setNotes(data);
  }, [taskId]);

  const loadAttachments = useCallback(async () => {
    if (!taskId) return;
    const data = await taskService.getTaskAttachments(taskId);
    setAttachments(data);
  }, [taskId]);

  useEffect(() => {
    loadTask();
  }, [loadTask]);

  useEffect(() => {
    loadEmployees();
  }, []);

  useEffect(() => {
    loadNotes();
    loadAttachments();
  }, [loadNotes, loadAttachments]);

  const loadEmployees = useCallback(async () => {
    try {
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
      console.log('✅ Loaded employees for assignment:', employeesList.length);
      setEmployees(employeesList.filter(emp => emp.is_active !== false));
    } catch (err) {
      console.error('Failed to load employees:', err);
      setEmployees([]);
    }
  }, []);

  const handleEdit = () => {
    if (!task) return;
    setEditData({
      task_description: task.task_description || task.description,
      priority: task.priority,
      due_date: task.due_date,
      estimated_hours: task.estimated_hours,
      completion_percentage: task.completion_percentage,
      assigned_to: task.assigned_to,
      assigned_to_multiple: task.assigned_to_multiple || [],
      strategic_metadata: task.strategic_metadata || {}
    });
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditData({});
  };

  const handleSave = async () => {
    if (!taskId || !task) return;
    try {
      setSaving(true);
      // Ensure assigned_to_multiple is properly formatted
      const saveData = { ...editData };
      if (saveData.assigned_to_multiple) {
        // Remove duplicates and ensure it's a valid array
        saveData.assigned_to_multiple = Array.from(new Set(saveData.assigned_to_multiple.filter(Boolean)));
        // Set assigned_to to first employee if not set
        if (!saveData.assigned_to && saveData.assigned_to_multiple.length > 0) {
          saveData.assigned_to = saveData.assigned_to_multiple[0];
        }
      }
      console.log('Saving task data:', saveData);
      await taskService.updateTask(taskId, saveData);
      setIsEditing(false);
      setEditData({});
      await loadTask();
    } catch (err) {
      console.error('Failed to save task:', err);
      alert('Failed to save task. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleAddAssignee = (employeeId: string) => {
    const currentMultiple = editData.assigned_to_multiple || [];
    if (currentMultiple.includes(employeeId)) {
      alert('This employee is already assigned to this task');
      return;
    }
    setEditData({
      ...editData,
      assigned_to_multiple: [...currentMultiple, employeeId],
      assigned_to: editData.assigned_to || employeeId
    });
  };

  const handleRemoveAssignee = (employeeId: string) => {
    const currentMultiple = editData.assigned_to_multiple || [];
    const remaining = currentMultiple.filter(id => id !== employeeId);
    setEditData({
      ...editData,
      assigned_to_multiple: remaining,
      assigned_to: editData.assigned_to === employeeId 
        ? (remaining.length > 0 ? remaining[0] : undefined)
        : editData.assigned_to
    });
  };

  const handleStatusChange = async (status: Task['status']) => {
    if (!task) return;
    await taskService.updateTaskStatus(task.id, status);
    await loadTask();
  };

  const handleAddNote = async () => {
    if (!taskId || !noteText.trim()) return;
    try {
      setSubmittingNote(true);
      await taskService.addTaskNote(taskId, { notes: noteText.trim(), progress: noteProgress });
      setNoteText('');
      await Promise.all([loadNotes(), loadTask()]);
    } finally {
      setSubmittingNote(false);
    }
  };

  const handleUpload = async (file?: FileList | null) => {
    if (!taskId || !file?.[0]) return;
    try {
      setUploading(true);
      await taskService.uploadTaskAttachment(taskId, file[0]);
      await loadAttachments();
    } finally {
      setUploading(false);
    }
  };

  const formatDate = (value?: string) => {
    if (!value) return 'Not set';
    try {
      return new Date(value).toLocaleDateString();
    } catch {
      return value;
    }
  };

  const formatDateTime = (value?: string) => {
    if (!value) return 'Not set';
    try {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value.slice(0, 16);
      return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch {
      return value;
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const sanitizeEmployeeName = (value?: string | null) => {
    if (!value) return '';
    return value.replace(/^[^A-Za-z]*[0-9]+[\s\-\|:_]+/, '').trim() || value;
  };

  const getEmployeeNameById = (employeeId?: string | null) => {
    if (!employeeId) return '';
    const match = Array.isArray(employees) ? employees.find(emp => emp.id === employeeId) : undefined;
    return match?.name || sanitizeEmployeeName(match?.name) || employeeId;
  };

  const handleMetadataValueChange = (key: string, newValue: any) => {
    const strategicSource = editData.strategic_metadata || task?.strategic_metadata || {};
    setEditData({
      ...editData,
      strategic_metadata: {
        ...strategicSource,
        [key]: newValue,
      },
    });
  };

  const handleAddMetadataField = () => {
    const newKey = prompt('Enter new AI insight field name (no spaces please):');
    if (!newKey) return;
    handleMetadataValueChange(newKey, '');
  };

  const strategicAnalysisFields = useMemo(() => {
    if (!task) return {
      context: undefined,
      delivery: undefined,
      goal_type: undefined,
      objective: undefined,
      process: undefined,
      reporting_requirements: undefined
    };
    const meta = task.strategic_metadata || {};
    return {
      context: meta.context,
      delivery: meta.delivery,
      goal_type: meta.goal_type,
      objective: meta.objective,
      process: meta.process,
      reporting_requirements: meta.reporting_requirements
    };
  }, [task]);

  const hasStrategicAnalysis = useMemo(() => {
    if (!task) return false;
    return Object.values(strategicAnalysisFields).some(v => v !== undefined && v !== null && v !== '');
  }, [task, strategicAnalysisFields]);

  const renderMetadataValue = (value: unknown) => {
    if (Array.isArray(value)) {
      return value.length ? value.join(', ') : '—';
    }
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value, null, 2);
    }
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    return String(value ?? '—');
  };

  const assigneeDisplay = useMemo(() => {
    if (!task) return 'Unassigned';
    return task.employees?.name || task.assigned_to_name || task.assigned_to || 'Unassigned';
  }, [task]);

  const createdByDisplay = useMemo(() => {
    if (!task) return 'System';
    // First try to get the name from the task object
    if (task.created_by_name) {
      return sanitizeEmployeeName(task.created_by_name) || task.created_by_name;
    }
    // If we have created_by ID, try to find the employee in our loaded employees list
    if (task.created_by && Array.isArray(employees) && employees.length > 0) {
      const creator = employees.find(emp => emp.id === task.created_by);
      if (creator && creator.name) {
        return sanitizeEmployeeName(creator.name) || creator.name;
      }
    }
    // Fallback to the ID if name is not available
    if (task.created_by) {
      return task.created_by;
    }
    // Last resort
    return 'System';
  }, [task, employees]);

  if (loading) {
    return <div className="task-detail-page loading">Loading task…</div>;
  }

  if (error || !task) {
    return (
      <div className="task-detail-page error">
        <p>{error || 'Task not found.'}</p>
        <Button variant="secondary" onClick={() => navigate('/admin/task-management')}>
          Back to Task List
        </Button>
      </div>
    );
  }

  const objectiveDetails = task.objectives || {};
  const dependencyList = Array.isArray(task.dependencies) ? task.dependencies.filter(Boolean) : [];
  const tagList = Array.isArray(task.tags) ? task.tags.filter(Boolean) : [];
  const assignedMultipleNames =
    Array.isArray(task.assigned_to_multiple) && task.assigned_to_multiple.length > 0
      ? task.assigned_to_multiple
          .map(id => getEmployeeNameById(id))
          .filter(Boolean)
      : [];
  const processBadge = task.strategic_metadata?.predefined_process
    ? 'Predefined Process'
    : task.strategic_metadata
    ? 'AI Generated'
    : 'Manual Entry';

  return (
    <div className="task-detail-page">
      <header className="task-detail-header">
        <div>
          <button className="back-link" onClick={() => navigate('/admin/task-management')}>
            ← Back to task list
          </button>
          {isEditing ? (
            <input
              type="text"
              value={editData.task_description || ''}
              onChange={(e) => setEditData({ ...editData, task_description: e.target.value })}
              style={{ fontSize: '24px', fontWeight: 'bold', width: '100%', padding: '8px', marginTop: '8px' }}
            />
          ) : (
            <h1>{task.task_description || task.description || 'Untitled Task'}</h1>
          )}
          <div className="task-meta-line">
            <div className="meta-item">
              <span className="meta-label">Objective:</span>
              <span className="meta-value">{task.objectives?.title || '—'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Objective Number:</span>
              <span className="meta-value highlight">{task.strategic_metadata?.objective_number || task.objectives?.pre_number || '—'}</span>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div className="task-status-block">
            <label>Status</label>
            <select
              value={isEditing ? (editData.status || task.status) : task.status}
              onChange={(e) => isEditing 
                ? setEditData({ ...editData, status: e.target.value as Task['status'] })
                : handleStatusChange(e.target.value as Task['status'])
              }
            >
              {['pending', 'not_started', 'in_progress', 'waiting', 'ai_suggested', 'completed', 'cancelled'].map(
                (status) => (
                  <option key={status} value={status}>
                    {status.replace('_', ' ')}
                  </option>
                )
              )}
            </select>
          </div>
          {isEditing ? (
            <>
              <Button variant="primary" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
              <Button variant="secondary" onClick={handleCancelEdit} disabled={saving}>
                Cancel
              </Button>
            </>
          ) : (
            <Button variant="primary" onClick={handleEdit}>
              ✏️ Edit Task
            </Button>
          )}
        </div>
      </header>

      <section className="task-summary-grid">
        <div>
          <p className="label">Assignee(s)</p>
          {isEditing || showAssignEmployee ? (
            <div>
              <select
                className="employee-select"
                value=""
                onChange={(e) => {
                  if (e.target.value) {
                    // Get current assignments - check both assigned_to and assigned_to_multiple
                    const currentMultiple = isEditing 
                      ? (editData.assigned_to_multiple || task.assigned_to_multiple || [])
                      : (task.assigned_to_multiple || []);
                    const currentAssignedTo = isEditing
                      ? (editData.assigned_to || task.assigned_to)
                      : task.assigned_to;
                    
                    // Check if employee is already in multiple assignments OR is the primary assignee
                    if (currentMultiple.includes(e.target.value) || currentAssignedTo === e.target.value) {
                      alert('This employee is already assigned to this task. Each employee can only be assigned once.');
                      e.target.value = '';
                      return;
                    }
                    if (isEditing) {
                      handleAddAssignee(e.target.value);
                    } else if (showAssignEmployee) {
                      // Get current assignments from editData or task
                      const baseMultiple = editData.assigned_to_multiple || task.assigned_to_multiple || [];
                      // Add new employee to the list (avoid duplicates)
                      const newMultiple = baseMultiple.includes(e.target.value) 
                        ? baseMultiple 
                        : [...baseMultiple, e.target.value];
                      setEditData({
                        ...editData,
                        assigned_to_multiple: newMultiple,
                        assigned_to: task.assigned_to || newMultiple[0]
                      });
                    }
                    e.target.value = '';
                  }
                }}
              >
                <option value="">Select Employee...</option>
                {Array.isArray(employees) && employees.length > 0 ? (
                  employees
                    .filter(emp => {
                      const currentMultiple = isEditing || showAssignEmployee
                        ? (editData.assigned_to_multiple || task.assigned_to_multiple || [])
                        : (task.assigned_to_multiple || []);
                      const currentAssignedTo = isEditing || showAssignEmployee
                        ? (editData.assigned_to || task.assigned_to)
                        : task.assigned_to;
                      // Filter out employees already assigned (either in multiple or as primary)
                      return !currentMultiple.includes(emp.id) && emp.id !== currentAssignedTo;
                    })
                    .map(emp => (
                      <option key={emp.id} value={emp.id}>
                        {sanitizeEmployeeName(emp.name) || emp.name} {emp.role ? `(${emp.role})` : ''}
                      </option>
                    ))
                ) : (
                  <option value="" disabled>Loading employees...</option>
                )}
              </select>
              {Array.isArray(employees) && employees.length === 0 && (
                <p className="muted" style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                  No employees available. Please check if employees are loaded.
                </p>
              )}
              <div className="employee-tags-container">
                {(isEditing || showAssignEmployee ? (editData.assigned_to_multiple || task.assigned_to_multiple || []) : (task.assigned_to_multiple || [])).map((empId: string) => {
                  const emp = Array.isArray(employees) ? employees.find(e => e.id === empId) : undefined;
                  return emp ? (
                    <span key={empId} className="employee-tag">
                      {emp.name}
                      {(isEditing || showAssignEmployee) && (
                        <button
                          onClick={() => {
                            if (isEditing) {
                              handleRemoveAssignee(empId);
                            } else if (showAssignEmployee) {
                              const currentMultiple = editData.assigned_to_multiple || task.assigned_to_multiple || [];
                              const remaining = currentMultiple.filter(id => id !== empId);
                              setEditData({
                                ...editData,
                                assigned_to_multiple: remaining,
                                assigned_to: task.assigned_to === empId 
                                  ? (remaining.length > 0 ? remaining[0] : undefined)
                                  : task.assigned_to
                              });
                            }
                          }}
                          type="button"
                          aria-label={`Remove ${emp.name}`}
                        >
                          ×
                        </button>
                      )}
                    </span>
                  ) : null;
                })}
              </div>
              {!isEditing && showAssignEmployee && (
                <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
                  <Button variant="primary" size="small" onClick={async () => {
                    try {
                      setSaving(true);
                      // Get the current assignments from editData (which includes newly added ones)
                      const currentMultiple = editData.assigned_to_multiple || task.assigned_to_multiple || [];
                      // Ensure we have a valid array and remove any duplicates
                      const uniqueAssignments = Array.from(new Set(currentMultiple.filter(Boolean)));
                      
                      console.log('Saving assignments:', uniqueAssignments);
                      
                      await taskService.updateTask(task.id, {
                        assigned_to_multiple: uniqueAssignments,
                        assigned_to: uniqueAssignments.length > 0 ? uniqueAssignments[0] : task.assigned_to
                      });
                      setShowAssignEmployee(false);
                      setEditData({});
                      await loadTask();
                    } catch (err) {
                      console.error('Failed to save assignments:', err);
                      alert('Failed to save assignments. Please try again.');
                    } finally {
                      setSaving(false);
                    }
                  }} disabled={saving}>
                    {saving ? 'Saving...' : 'Save Assignments'}
                  </Button>
                  <Button variant="secondary" size="small" onClick={() => {
                    setShowAssignEmployee(false);
                    setEditData({});
                  }}>
                    Cancel
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div>
              {task.assigned_to_multiple && task.assigned_to_multiple.length > 0 ? (
                <div className="employee-tags-container">
                  {task.assigned_to_multiple.map((empId: string) => {
                    const emp = Array.isArray(employees) ? employees.find(e => e.id === empId) : undefined;
                    return emp ? (
                      <span key={empId} className="employee-tag">
                        {emp.name}
                      </span>
                    ) : null;
                  })}
                </div>
              ) : (
                <strong>{assigneeDisplay}</strong>
              )}
              {!isEditing && (
                <div style={{ marginTop: '0.5rem' }}>
                  <Button variant="secondary" size="small" onClick={() => setShowAssignEmployee(true)}>
                    + Assign Employee
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
        <div>
          <p className="label">Priority</p>
          {isEditing ? (
            <select
              value={editData.priority || task.priority}
              onChange={(e) => setEditData({ 
                ...editData, 
                priority: e.target.value as 'low' | 'medium' | 'high' | 'urgent' 
              })}
            >
              {['low', 'medium', 'high', 'urgent'].map(p => (
                <option key={p} value={p}>{p.toUpperCase()}</option>
              ))}
            </select>
          ) : (
            <span className={`priority-badge ${task.priority}`}>{task.priority.toUpperCase()}</span>
          )}
        </div>
        <div>
          <p className="label">Due Date</p>
          {isEditing ? (
            <input
              type="date"
              value={editData.due_date ? editData.due_date.split('T')[0] : ''}
              onChange={(e) => setEditData({ ...editData, due_date: e.target.value })}
            />
          ) : (
            <strong>{formatDate(task.due_date)}</strong>
          )}
        </div>
        <div>
          <p className="label">Progress</p>
          {isEditing ? (
            <input
              type="number"
              min={0}
              max={100}
              value={editData.completion_percentage ?? task.completion_percentage ?? 0}
              onChange={(e) => setEditData({ ...editData, completion_percentage: Number(e.target.value) })}
              style={{ width: '80px' }}
            />
          ) : (
            <strong>{task.completion_percentage ?? 0}%</strong>
          )}
        </div>
        <div>
          <p className="label">Estimated Hours</p>
          {isEditing ? (
            <input
              type="number"
              min={0}
              value={editData.estimated_hours ?? task.estimated_hours ?? 8}
              onChange={(e) => setEditData({ ...editData, estimated_hours: Number(e.target.value) })}
              style={{ width: '80px' }}
            />
          ) : (
            <strong>{task.estimated_hours ?? 8}</strong>
          )}
        </div>
        <div>
          <p className="label">Created</p>
          <span>{formatDate(task.created_at)}</span>
        </div>
        <div>
          <p className="label">Updated</p>
          <span>{formatDate(task.updated_at)}</span>
        </div>
      </section>

      <section className="task-detail-section detail-grid">
        <div className="info-tile">
          <p className="label">Process Type</p>
          <p className="info-pill">{processBadge}</p>
        </div>
        <div className="info-tile">
          <p className="label">Primary Assignee</p>
          <p>{getEmployeeNameById(task.assigned_to) || assigneeDisplay}</p>
        </div>
        <div className="info-tile">
          <p className="label">Created By</p>
          <p>{createdByDisplay}</p>
        </div>
        <div className="info-tile">
          <p className="label">Objective Priority</p>
          <p>{objectiveDetails.priority || '—'}</p>
        </div>
      </section>

      <section className="task-detail-section">
        <h3>Assignments & Dependencies</h3>
        {assignedMultipleNames.length > 0 && (
          <div className="info-panel">
            <p className="label">Assigned Team</p>
            <div className="chip-list">
              {assignedMultipleNames.map(name => (
                <span key={name} className="chip">
                  {name}
                </span>
              ))}
            </div>
          </div>
        )}
        {dependencyList.length > 0 ? (
          <div className="info-panel">
            <p className="label">Dependencies</p>
            <ul className="styled-list">
              {dependencyList.map(dep => (
                <li key={dep}>{dep}</li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="muted">No dependencies listed.</p>
        )}
        {tagList.length > 0 && (
          <div className="info-panel">
            <p className="label">Tags</p>
            <div className="chip-list">
              {tagList.map(tag => (
                <span key={tag} className="chip">
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="task-detail-section">
        <h2>Description</h2>
        {isEditing ? (
          <textarea
            value={editData.task_description || task.task_description || task.description || ''}
            onChange={(e) => setEditData({ ...editData, task_description: e.target.value })}
            rows={4}
            style={{ width: '100%', padding: '8px' }}
          />
        ) : (
          <p>{task.task_description || task.description || 'No description provided.'}</p>
        )}
      </section>

      {task.strategic_metadata?.recommended_role && (
        <section className="task-detail-section">
          <div className="info-tile">
            <p className="label">Recommended Role</p>
            <p className="info-pill">{task.strategic_metadata.recommended_role}</p>
          </div>
        </section>
      )}

      {hasStrategicAnalysis && (
        <section className="task-detail-section">
          <div className="section-header">
            <div>
              <h2>Strategic Analysis</h2>
              <p className="section-subtitle">AI-generated strategic insights</p>
            </div>
            <Button 
              variant="secondary" 
              size="small"
              className="toggle-button"
              onClick={() => setShowStrategicAnalysis(!showStrategicAnalysis)}
            >
              {showStrategicAnalysis ? '▼ Hide Analysis' : '▶ Show Strategic Analysis'}
            </Button>
          </div>
          {showStrategicAnalysis && (
            <div className="strategic-analysis-content">
              {strategicAnalysisFields.context && (
                <div className="strategic-field">
                  <p className="label">Context</p>
                  <p>{strategicAnalysisFields.context}</p>
                </div>
              )}
              {strategicAnalysisFields.objective && (
                <div className="strategic-field">
                  <p className="label">Objective</p>
                  <p>{strategicAnalysisFields.objective}</p>
                </div>
              )}
              {strategicAnalysisFields.process && (
                <div className="strategic-field">
                  <p className="label">Process</p>
                  <p>{strategicAnalysisFields.process}</p>
                </div>
              )}
              {strategicAnalysisFields.delivery && (
                <div className="strategic-field">
                  <p className="label">Delivery</p>
                  <p>{strategicAnalysisFields.delivery}</p>
                </div>
              )}
              {strategicAnalysisFields.goal_type && (
                <div className="strategic-field">
                  <p className="label">Goal Type</p>
                  <p>{strategicAnalysisFields.goal_type}</p>
                </div>
              )}
              {strategicAnalysisFields.reporting_requirements && (
                <div className="strategic-field">
                  <p className="label">Reporting Requirements</p>
                  <p>{strategicAnalysisFields.reporting_requirements}</p>
                </div>
              )}
              {task.strategic_metadata?.required_skills && Array.isArray(task.strategic_metadata.required_skills) && (
                <div className="strategic-field">
                  <p className="label">Required Skills</p>
                  <p>{task.strategic_metadata.required_skills.join(' - ')}</p>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {task.strategic_metadata?.employee_recommendations_available && (
        <section className="task-detail-section">
          <div className="section-header">
            <div>
              <h2>Employee Recommendations</h2>
              <p className="section-subtitle">AI-recommended employees for this task</p>
            </div>
            <Button 
              variant="secondary" 
              size="small"
              className="toggle-button"
              onClick={() => setShowEmployeeRecommendations(!showEmployeeRecommendations)}
            >
              {showEmployeeRecommendations ? '▼ Hide Recommendations' : '▶ Show Employee Recommendations'}
            </Button>
          </div>
          {showEmployeeRecommendations && (
            <div className="rag-block">
              <RAGRecommendations task={task} onRecommendationApplied={loadTask} />
            </div>
          )}
        </section>
      )}

      <section className="task-detail-section">
        <div className="section-header">
          <h2>Quick Actions</h2>
          <p className="section-subtitle">Update status or add a progress note</p>
        </div>
        <div className="quick-actions-grid">
          <div className="status-actions">
            <p className="label">Change Status</p>
            <div className="status-buttons">
              {['in_progress', 'completed', 'pending'].map((status) => (
                <Button
                  key={status}
                  variant={task.status === status ? 'success' : 'secondary'}
                  size="small"
                  onClick={() => handleStatusChange(status as Task['status'])}
                  disabled={task.status === status}
                >
                  {status.replace('_', ' ')}
                </Button>
              ))}
            </div>
          </div>
          <div className="note-form">
            <label>
              Progress ({noteProgress}%)
              <input
                type="range"
                min={0}
                max={100}
                value={noteProgress}
                onChange={(e) => setNoteProgress(Number(e.target.value))}
              />
            </label>
            <textarea
              placeholder="Add context, blockers, or next steps…"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              rows={4}
            />
            <Button variant="primary" disabled={!noteText.trim() || submittingNote} onClick={handleAddNote}>
              {submittingNote ? 'Saving…' : 'Post Note'}
            </Button>
          </div>
        </div>
      </section>

      <section className="task-detail-section two-column">
        <div className="notes-section">
          <div className="section-header">
            <h2>Notes & Updates</h2>
            <p className="section-subtitle">Track conversations and progress updates</p>
          </div>
          {notes.length === 0 ? (
            <p className="muted">No notes yet. Add the first update below.</p>
          ) : (
            <div className="notes-list">
              {notes.map((note) => (
                <div key={note.id} className="note-card">
                  <div className="note-card-header">
                    <div>
                      <strong>{sanitizeEmployeeName(note.employee_name) || 'Unknown'}</strong>
                      <span>{note.employee_role || 'Team member'}</span>
                    </div>
                    <span className="note-date">{formatDateTime(note.created_at)}</span>
                  </div>
                  <p className="note-content">{note.notes}</p>
                  <div className="note-card-meta">
                    {typeof note.progress === 'number' && (
                      <span className="note-progress">Progress: {note.progress}%</span>
                    )}
                    {note.attachments_count && note.attachments_count > 0 && (
                      <span className="note-attachments">📎 {note.attachments_count} attachment(s)</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="attachments-section">
          <div className="section-header">
            <h2>Attachments</h2>
            <p className="section-subtitle">Files shared for this task</p>
          </div>
          <label className="upload-block">
            <span>{uploading ? 'Uploading…' : '📎 Upload file'}</span>
            <input type="file" onChange={(e) => handleUpload(e.target.files)} disabled={uploading} />
          </label>
          {attachments.length === 0 ? (
            <p className="muted">No attachments uploaded yet.</p>
          ) : (
            <ul className="attachment-list">
              {attachments.map((attachment, idx) => (
                <li key={`${attachment.id || attachment.update_id || idx}`} className="attachment-item">
                  <div className="attachment-info">
                    <div>
                      <strong>{attachment.filename || attachment.file_name || 'Attachment'}</strong>
                      <p className="attachment-meta">
                        {attachment.file_type || 'File'} · {formatFileSize(attachment.file_size)}
                      </p>
                    </div>
                    <div className="attachment-details">
                      <div>
                        <p className="label">Uploaded</p>
                        <span>{formatDateTime(attachment.created_at)}</span>
                      </div>
                      <div>
                        <p className="label">By</p>
                        <span>{sanitizeEmployeeName(attachment.employee_name) || attachment.uploaded_by_name || 'Unknown'}</span>
                      </div>
                    </div>
                  </div>
                  {attachment.public_url && (
                    <a
                      href={attachment.public_url}
                      target="_blank"
                      rel="noreferrer"
                      className="attachment-link"
                    >
                      Open
                    </a>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
};

export default TaskDetailPage;

