import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { taskService } from '../../services/task';
import { Task, TaskAttachment, TaskNote, EmployeeReference } from '../../types';
import { Button } from '../../components/Common/UI/Button';
import { formatObjectiveNumber } from '../../utils/helpers';
import './TaskDetailPage.css';

const TaskDetailPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  const [notes, setNotes] = useState<TaskNote[]>([]);
  const [attachments, setAttachments] = useState<TaskAttachment[]>([]);
  const [noteText, setNoteText] = useState('');
  const [noteProgress, setNoteProgress] = useState<number>(0);
  const [submittingNote, setSubmittingNote] = useState(false);
  const [selectedRecipients, setSelectedRecipients] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadMessage, setUploadMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [availableEmployees, setAvailableEmployees] = useState<EmployeeReference[]>([]);
  const [availableEmployeesLoading, setAvailableEmployeesLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'attachments' | 'notes'>('details');
  const [showNotificationMessage, setShowNotificationMessage] = useState(false);
  const [notificationMessage, setNotificationMessage] = useState<string>('');

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
      
      // Set default recipients
      const defaults = new Set<string>();
      if (typeof nextTask?.assigned_to === 'string' && nextTask.assigned_to) {
        defaults.add(nextTask.assigned_to);
      }
      (nextTask?.assigned_to_multiple || []).forEach((empId: string) => {
        if (typeof empId === 'string' && empId) {
          defaults.add(empId);
        }
      });
      setSelectedRecipients(Array.from(defaults));
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
    loadNotes();
    loadAttachments();
  }, [loadNotes, loadAttachments]);

  // Check if navigated from notification
  useEffect(() => {
    const taskIdFromNotification = localStorage.getItem('current_task_id');
    if (taskIdFromNotification === taskId) {
      // Clear the flag
      localStorage.removeItem('current_task_id');
      // Show notification message
      setNotificationMessage('You were redirected here from a notification');
      setShowNotificationMessage(true);
      // Auto-hide after 5 seconds
      const timer = setTimeout(() => {
        setShowNotificationMessage(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [taskId]);

  useEffect(() => {
    let isMounted = true;
    const fetchAvailableEmployees = async () => {
      if (!taskId) {
        setAvailableEmployees([]);
        return;
      }
      try {
        setAvailableEmployeesLoading(true);
        const response = await taskService.getAvailableEmployeesForAttachment(taskId);
        if (!isMounted) return;
        if (response.success) {
          setAvailableEmployees(response.employees ?? []);
        } else {
          setAvailableEmployees([]);
        }
      } catch (err) {
        if (isMounted) {
          console.error('Error loading employees for note notifications', err);
          setAvailableEmployees([]);
        }
      } finally {
        if (isMounted) {
          setAvailableEmployeesLoading(false);
        }
      }
    };
    fetchAvailableEmployees();
    return () => {
      isMounted = false;
    };
  }, [taskId]);

  const handleAttachmentSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedFile || !taskId) {
      setUploadError('Please choose a file to upload');
      return;
    }
    try {
      setUploading(true);
      setUploadError('');
      await taskService.uploadTaskAttachment(taskId, selectedFile);
      setUploadMessage('Attachment uploaded successfully.');
      setSelectedFile(null);
      await loadAttachments();
    } catch (err: any) {
      setUploadError(err?.message || 'Failed to upload attachment');
    } finally {
      setUploading(false);
    }
  };

  const handleAddNote = async () => {
    if (!taskId || !noteText.trim()) return;
    try {
      setSubmittingNote(true);
      const notifyIds = selectedRecipients.filter(id => id && id !== '__none__');
      const [attached_to, ...rest] = notifyIds;
      await taskService.addTaskNote(taskId, { 
        notes: noteText.trim(), 
        progress: noteProgress,
        attached_to,
        attached_to_multiple: rest.length ? rest : undefined
      });
      setNoteText('');
      setSelectedRecipients([]);
      await Promise.all([loadNotes(), loadTask()]);
    } finally {
      setSubmittingNote(false);
    }
  };

  const handleStatusChange = async (status: Task['status']) => {
    if (!taskId) return;
    try {
      await taskService.updateTaskStatus(taskId, status);
      await loadTask();
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

  const formatDateTime = (value?: string) => {
    if (!value) return 'Not set';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value.slice(0, 10);
    return date.toLocaleString();
  };

  const recipientNameMap = useMemo(() => {
    const map: Record<string, string> = {};
    availableEmployees.forEach((emp) => {
      if (!emp?.id) return;
      const displayName = emp.name || emp.email || emp.id;
      map[emp.id] = displayName;
    });
    return map;
  }, [availableEmployees]);

  const getNoteRecipientNames = (note: TaskNote) => {
    const names = new Set<string>();
    if (note.attached_to && recipientNameMap[note.attached_to]) {
      names.add(recipientNameMap[note.attached_to]);
    }
    (note.attached_to_multiple || []).forEach((empId) => {
      const name = recipientNameMap[empId];
      if (name) {
        names.add(name);
      }
    });
    if (note.attached_to_name) {
      names.add(note.attached_to_name);
    }
    if (Array.isArray(note.attached_to_multiple_names)) {
      note.attached_to_multiple_names.forEach((val: any) => {
        if (typeof val === 'string') {
          names.add(val);
        } else if (val && typeof val === 'object' && 'name' in val && val.name) {
          names.add(val.name);
        }
      });
    }
    return Array.from(names);
  };

  const metadata = task?.strategic_metadata;
  const metadataFields = [
    { label: '🎯 Context', value: metadata?.context },
    { label: '🎯 Objective', value: metadata?.objective },
    { label: '🔄 Process', value: metadata?.process },
    { label: '📦 Delivery', value: metadata?.delivery },
    { label: '📊 Reporting Requirements', value: metadata?.reporting_requirements },
  ].filter(item => item.value);

  const statusShortcuts: Task['status'][] = ['in_progress', 'completed', 'waiting'];

  if (loading) {
    return <div className="loading">Loading task details...</div>;
  }

  if (error || !task) {
    return (
      <div className="error-container">
        <p>{error || 'Task not found'}</p>
        <Button variant="secondary" onClick={() => navigate('/employee/task-management')}>
          Back to Tasks
        </Button>
      </div>
    );
  }

  return (
    <div className="task-detail-page">
      {showNotificationMessage && (
        <div className="notification-banner" style={{
          backgroundColor: '#e3f2fd',
          border: '1px solid #2196f3',
          borderRadius: '4px',
          padding: '12px 16px',
          marginBottom: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span style={{ color: '#1976d2' }}>🔔 {notificationMessage}</span>
          <button
            onClick={() => setShowNotificationMessage(false)}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '20px',
              cursor: 'pointer',
              color: '#1976d2',
              padding: '0 8px'
            }}
          >
            ×
          </button>
        </div>
      )}
      <div className="task-detail-header">
        <Button variant="ghost" onClick={() => navigate('/employee/task-management')}>
          ← Back to Tasks
        </Button>
        <h1>{task.task_description || task.description || 'Task Details'}</h1>
      </div>

      <div className="detail-tabs">
        {(['details', 'attachments', 'notes'] as const).map(tab => (
          <button 
            key={tab}
            className={`detail-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
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
              <p className="label">Objective Number</p>
              <strong>{formatObjectiveNumber(task.objectives?.pre_number || task.pre_number)}</strong>
            </div>
            <div>
              <p className="label">Objective Priority</p>
              <strong>{task.objectives?.priority || '—'}</strong>
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
                onClick={() => handleStatusChange(status)}
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
            <Button variant="ghost" size="small" onClick={loadAttachments}>
              Refresh
            </Button>
          </div>

          {attachments.length === 0 ? (
            <p className="muted-text">No attachments uploaded yet.</p>
          ) : (
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
          )}

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
            <Button variant="ghost" size="small" onClick={loadNotes}>
              Refresh
            </Button>
          </div>

          {notes.length === 0 ? (
            <p className="muted-text">No notes yet. Add the first update below.</p>
          ) : (
            <div className="notes-list">
              {notes.map(note => {
                const recipientNames = getNoteRecipientNames(note);
                return (
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
                    </div>
                    {(recipientNames.length > 0 || note.is_attached_to_me) && (
                      <div style={{ fontSize: '12px', color: '#555', marginTop: '6px' }}>
                        {recipientNames.length > 0 && (
                          <span>👥 Notified: {recipientNames.join(', ')}</span>
                        )}
                        {note.is_attached_to_me && (
                          <span style={{ marginLeft: recipientNames.length > 0 ? '8px' : 0, color: '#2e7d32', fontWeight: 600 }}>
                            You were notified
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <form className="note-form" onSubmit={(e) => { e.preventDefault(); handleAddNote(); }}>
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
            <label>
              Notify teammates (optional)
              {availableEmployeesLoading && <p className="muted-text">Loading employees...</p>}
              <p className="muted-text" style={{ fontSize: '12px', marginBottom: '8px' }}>
                Select teammates who should receive a notification about this update.
              </p>
              <div style={{ 
                border: '1px solid #ddd', 
                borderRadius: '4px', 
                padding: '8px', 
                maxHeight: '200px', 
                overflowY: 'auto',
                backgroundColor: '#fff',
                opacity: availableEmployeesLoading ? 0.6 : 1
              }}>
                {availableEmployees
                  .filter(emp => emp?.id)
                  .map((emp) => {
                    const empId = emp.id!;
                    const isSelected = selectedRecipients.includes(empId);
                    return (
                      <label
                        key={empId}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '6px 8px',
                          cursor: availableEmployeesLoading ? 'not-allowed' : 'pointer',
                          borderRadius: '4px',
                          marginBottom: '4px',
                          backgroundColor: isSelected ? '#e3f2fd' : 'transparent',
                          transition: 'background-color 0.2s',
                          pointerEvents: availableEmployeesLoading ? 'none' : 'auto'
                        }}
                        onMouseEnter={(e) => {
                          if (!isSelected && !availableEmployeesLoading) e.currentTarget.style.backgroundColor = '#f5f5f5';
                        }}
                        onMouseLeave={(e) => {
                          if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          disabled={availableEmployeesLoading}
                          onChange={() => {
                            if (isSelected) {
                              setSelectedRecipients(prev => prev.filter(id => id !== empId));
                            } else {
                              setSelectedRecipients(prev => [...prev.filter(id => id !== '__none__'), empId]);
                            }
                          }}
                          style={{ marginRight: '8px', cursor: availableEmployeesLoading ? 'not-allowed' : 'pointer' }}
                        />
                        <span style={{ flex: 1 }}>
                          {emp.name || emp.email || 'Unknown'}
                          {emp.role && <span style={{ color: '#666', marginLeft: '4px' }}>({emp.role})</span>}
                          {emp.department && <span style={{ color: '#999', marginLeft: '4px' }}>· {emp.department}</span>}
                        </span>
                      </label>
                    );
                  })}
              </div>
            </label>
            {selectedRecipients.length > 0 && (
              <p className="muted-text" style={{ marginTop: '8px' }}>
                Notifying: {selectedRecipients.filter(id => id !== '__none__').map(id => recipientNameMap[id] || id).join(', ')}
              </p>
            )}
            <div className="note-form-actions">
              <Button type="submit" variant="primary" disabled={!noteText.trim() || submittingNote}>
                {submittingNote ? 'Posting…' : 'Post note'}
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

export default TaskDetailPage;

