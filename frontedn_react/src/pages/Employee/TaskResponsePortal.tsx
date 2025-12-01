import React, { useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Button } from '../../components/Common/UI/Button';
import { Card } from '../../components/Common/UI/Card';
import { taskService } from '../../services/task';
import { useNotification } from '../../contexts/NotificationContext';
import './TaskResponsePortal.css';

interface ResponsePortalState {
  taskDescription?: string;
  notePreview?: string;
  message?: string;
  notificationId?: string;
  added_by?: string;
}

export const TaskResponsePortal: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { markAsRead } = useNotification();
  const portalState = (location.state || {}) as ResponsePortalState;

  const [noteText, setNoteText] = useState('');
  const [submitMessage, setSubmitMessage] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadMessage, setUploadMessage] = useState('');
  const [uploadError, setUploadError] = useState('');
  const [uploading, setUploading] = useState(false);

  if (!taskId) {
    return (
      <div className="task-response-page">
        <Card>
          <h2>Task unavailable</h2>
          <p>We couldn&apos;t find the task referenced by this response link.</p>
          <Button variant="secondary" onClick={() => navigate(-1)}>
            Go back
          </Button>
        </Card>
      </div>
    );
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!noteText.trim()) {
      setSubmitError('Please share a short update or response before submitting.');
      return;
    }

    try {
      setSubmitting(true);
      setSubmitError('');
      setSubmitMessage('');

      const result = await taskService.addTaskNote(taskId, { notes: noteText.trim() });
      if (!result.success) {
        throw new Error(result.error || 'Failed to send your response');
      }

      if (portalState.notificationId) {
        markAsRead(portalState.notificationId);
      }

      setNoteText('');
      setSubmitMessage('Response sent! The task owners have been notified.');
    } catch (error: any) {
      setSubmitError(error?.message || 'Something went wrong while sending your response.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAttachmentUpload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedFile) {
      setUploadError('Choose a file before uploading.');
      return;
    }

    try {
      setUploading(true);
      setUploadError('');
      setUploadMessage('');

      const result = await taskService.uploadTaskAttachment(taskId, selectedFile);
      if (!result.success) {
        throw new Error(result.error || 'Failed to upload attachment');
      }

      setSelectedFile(null);
      setUploadMessage('Attachment uploaded successfully.');
    } catch (error: any) {
      setUploadError(error?.message || 'Unable to upload attachment.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="task-response-page">
      <div className="task-response-layout">
        <Card className="task-response-info">
          <div className="info-header">
            <div>
              <p className="eyebrow">Task Response Portal</p>
              <h2>Respond to task collaborators</h2>
            </div>
            <Button variant="ghost" onClick={() => navigate('/employee/notifications')}>
              ← Back to notifications
            </Button>
          </div>
          <div className="info-body">
            <p>
              You were specifically mentioned on this task. Use this space to reply with updates or share any files,
              even if the full task isn&apos;t visible in your workspace.
            </p>
            <ul>
              {portalState.taskDescription && (
                <li>
                  <span className="label">Task:</span> {portalState.taskDescription}
                </li>
              )}
              {portalState.notePreview && (
                <li>
                  <span className="label">Last note:</span> {portalState.notePreview}
                </li>
              )}
              {portalState.added_by && (
                <li>
                  <span className="label">Tagged by:</span> {portalState.added_by}
                </li>
              )}
            </ul>
          </div>
        </Card>

        <div className="task-response-panel">
          <Card>
            <h3>Send a quick response</h3>
            <form className="response-form" onSubmit={handleSubmit}>
              <label>
                Your message
                <textarea
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Share updates, answers, or next steps..."
                  rows={5}
                />
              </label>
              {submitError && <p className="error-text">{submitError}</p>}
              {submitMessage && <p className="success-text">{submitMessage}</p>}
              <div className="form-actions">
                <Button type="submit" variant="primary" disabled={submitting}>
                  {submitting ? 'Sending…' : 'Send response'}
                </Button>
              </div>
            </form>
          </Card>

          <Card>
            <h3>Share an attachment</h3>
            <form className="attachment-form" onSubmit={handleAttachmentUpload}>
              <label>
                Upload file
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                />
              </label>
              {selectedFile && (
                <p className="muted-text">Selected: {selectedFile.name}</p>
              )}
              {uploadError && <p className="error-text">{uploadError}</p>}
              {uploadMessage && <p className="success-text">{uploadMessage}</p>}
              <div className="form-actions">
                <Button type="submit" variant="secondary" disabled={uploading}>
                  {uploading ? 'Uploading…' : 'Upload attachment'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default TaskResponsePortal;


