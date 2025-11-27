import React from 'react';
import { Task } from '../../types';
import { Button } from '../Common/UI/Button';
import './TaskDetailDrawer.css';

interface TaskDetailDrawerProps {
  task: Task;
  onClose: () => void;
  onStatusChange: (status: Task['status']) => void;
}

export const TaskDetailDrawer: React.FC<TaskDetailDrawerProps> = ({
  task,
  onClose,
  onStatusChange,
}) => {
  const description = task.task_description || task.description || 'No description';
  const objectiveTitle = task.objectives?.title || 'No linked objective';
  const strategicObjective = task.strategic_objective || task.objectives?.title || 'Not set';
  const preNumber = task.pre_number || task.objectives?.pre_number || 'Not assigned';
  const metadata = task.strategic_metadata;
  const sanitizeName = (value?: string | null) => {
    if (!value) return '';
    const cleaned = value.replace(/^[^A-Za-z]*[0-9]+[\s\-\|:_]+/, '').trim();
    return cleaned || value;
  };

  const assignedTo =
    sanitizeName(task.employees?.name) ||
    task.employees?.email ||
    (typeof task.assigned_to_name === 'string'
      ? sanitizeName(task.assigned_to_name)
      : typeof task.assigned_to === 'string'
        ? sanitizeName(task.assigned_to)
        : 'Unassigned');

  const handleStatusClick = (status: Task['status']) => {
    if (task.status === status) return;
    onStatusChange(status);
  };

  return (
    <div className="task-drawer-overlay">
      <aside className="task-drawer">
        <header className="task-drawer-header">
          <div>
            <p className="drawer-eyebrow">Task Detail</p>
            <h2>{description}</h2>
          </div>
          <button className="drawer-close" onClick={onClose} aria-label="Close details">
            ✕
          </button>
        </header>

        <section className="task-drawer-section">
          <h3>Overview</h3>
          <div className="task-info-grid">
            <div>
              <p className="label">Status</p>
              <span className={`status-pill status-${task.status}`}>{task.status.replace('_', ' ')}</span>
            </div>
            <div>
              <p className="label">Priority</p>
              <span className={`priority-pill priority-${task.priority || 'low'}`}>
                {(task.priority || 'low').toUpperCase()}
              </span>
            </div>
            <div>
              <p className="label">Assignee</p>
              <span>{assignedTo || 'Unassigned'}</span>
            </div>
            <div>
              <p className="label">Due Date</p>
              <span>{task.due_date ? new Date(task.due_date).toLocaleDateString() : 'Not set'}</span>
            </div>
          </div>
        </section>

        <section className="task-drawer-section">
          <h3>Objective</h3>
          <div className="objective-meta-grid">
            <div>
              <p className="label">Linked Objective</p>
              <span>{objectiveTitle}</span>
            </div>
            <div>
              <p className="label">Strategic Objective</p>
              <span>{strategicObjective}</span>
            </div>
            <div>
              <p className="label">Pre Number</p>
              <span>{preNumber}</span>
            </div>
            {task.objectives?.priority && (
              <div>
                <p className="label">Objective Priority</p>
                <span>{task.objectives.priority}</span>
              </div>
            )}
          </div>
        </section>

        <section className="task-drawer-section">
          <h3>Description</h3>
          <p>{description}</p>
        </section>

        {metadata && (
          <section className="task-drawer-section">
            <h3>AI Strategic Analysis</h3>
            <div className="strategic-meta">
              {metadata.context && (
                <div>
                  <p className="label">🎯 Context</p>
                  <p>{metadata.context}</p>
                </div>
              )}
              {metadata.objective && (
                <div>
                  <p className="label">🎯 Objective</p>
                  <p>{metadata.objective}</p>
                </div>
              )}
              {metadata.process && (
                <div>
                  <p className="label">🔄 Process</p>
                  <p>{metadata.process}</p>
                </div>
              )}
              {metadata.delivery && (
                <div>
                  <p className="label">📦 Delivery</p>
                  <p>{metadata.delivery}</p>
                </div>
              )}
              {metadata.reporting_requirements && (
                <div>
                  <p className="label">📊 Reporting Requirements</p>
                  <p>{metadata.reporting_requirements}</p>
                </div>
              )}
              {metadata.validation_score && (
                <div>
                  <p className="label">Validation Score</p>
                  <p>{metadata.validation_score}</p>
                </div>
              )}
              {metadata.q4_execution_context && (
                <div>
                  <p className="label">Execution Context</p>
                  <p>{metadata.q4_execution_context}</p>
                </div>
              )}
              {metadata.process_applied && (
                <div>
                  <p className="label">Process Applied</p>
                  <p>{metadata.process_applied}</p>
                </div>
              )}
              {metadata.goal_type && (
                <div>
                  <p className="label">Goal Type</p>
                  <p>{metadata.goal_type}</p>
                </div>
              )}
            </div>
          </section>
        )}

        {task.tags && task.tags.length > 0 && (
          <section className="task-drawer-section">
            <h3>Tags</h3>
            <div className="tag-list">
              {task.tags.map(tag => (
                <span key={tag} className="tag">
                  #{tag}
                </span>
              ))}
            </div>
          </section>
        )}

        <section className="task-drawer-section">
          <h3>Quick Actions</h3>
          <div className="drawer-actions">
            <Button variant="secondary" onClick={() => handleStatusClick('in_progress')}>
              Mark In Progress
            </Button>
            <Button variant="success" onClick={() => handleStatusClick('completed')}>
              Mark Completed
            </Button>
            <Button variant="danger" onClick={() => handleStatusClick('pending')}>
              Move to Pending
            </Button>
          </div>
        </section>
      </aside>
    </div>
  );
};

export default TaskDetailDrawer;

