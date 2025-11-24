import React, { useState } from 'react';
import { Task, Employee } from '../../types';
import { taskService } from '../../services/task';
import { Button } from '../Common/UI/Button';
import { RAGRecommendations } from './RAGRecommendations';
import './GeneratedTaskCard.css';

interface GeneratedTaskCardProps {
  task: Task;
  index: number;
  employees: Employee[];
  onTaskChange: (taskId: string | undefined, field: keyof Task | 'assigned_role', value: string) => void;
  onAssignmentChange: (taskId: string | undefined, employeeId: string) => void;
  onRecommendationApplied?: () => void;
}

export const GeneratedTaskCard: React.FC<GeneratedTaskCardProps> = ({
  task,
  index,
  employees,
  onTaskChange,
  onAssignmentChange,
  onRecommendationApplied,
}) => {
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [showApproveForm, setShowApproveForm] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);

  const strategicMeta = task.strategic_metadata || {};
  const hasRecommendations = strategicMeta.employee_recommendations_available || false;
  const recommendationsFailed = strategicMeta.recommendations_failed || false;
  const objectiveTitle = task.objectives?.title || task.strategic_objective || 'No Objective';
  const assignedEmployee = employees.find(emp => emp.id === task.assigned_to);
  const assignedEmployeeName = assignedEmployee?.name || task.assigned_to_name || 'Unassigned';

  const formatDate = (value?: string) => {
    if (!value) return 'Not set';
    try {
      return new Date(value).toLocaleDateString();
    } catch {
      return value.slice(0, 10);
    }
  };

  const handleApprove = async () => {
    if (task.assigned_to) {
      await onTaskChange(task.id, 'status', 'not_started');
      setShowApproveForm(false);
      onRecommendationApplied?.();
    }
  };

  return (
    <div className="generated-task-card">
      <div className="generated-task-header">
        <div className="generated-task-title-section">
          <p className="generated-task-eyebrow">
            {task.pre_number || `Task ${index + 1}`}
          </p>
          <h4>{task.task_description || task.description || 'Untitled Task'}</h4>
        </div>
        <span className={`status-pill ${task.status || 'ai_suggested'}`}>
          {(task.status || 'ai_suggested').replace('_', ' ')}
        </span>
      </div>

      <div className="generated-task-content">
        <div className="generated-task-main">
          <div className="generated-task-description">
            <p className="generated-task-label">Objective:</p>
            <p className="generated-task-value">{objectiveTitle}</p>
          </div>

          <div className="generated-task-details-grid">
            <div className="generated-task-detail-item">
              <p className="label">Created</p>
              <strong>{formatDate(task.created_at)}</strong>
            </div>
            <div className="generated-task-detail-item">
              <p className="label">Assigned</p>
              <strong>{formatDate(task.assigned_at)}</strong>
            </div>
            <div className="generated-task-detail-item">
              <p className="label">Due Date</p>
              <strong>{formatDate(task.due_date)}</strong>
            </div>
            <div className="generated-task-detail-item">
              <p className="label">Priority</p>
              <span className={`priority-badge ${task.priority || 'medium'}`}>
                {(task.priority || 'medium').toUpperCase()}
              </span>
            </div>
            <div className="generated-task-detail-item">
              <p className="label">Estimated Hours</p>
              <strong>{task.estimated_hours || 8}</strong>
            </div>
            <div className="generated-task-detail-item">
              <p className="label">Complexity</p>
              <strong>{(strategicMeta.complexity || 'medium').toUpperCase()}</strong>
            </div>
          </div>

          {strategicMeta.required_skills && strategicMeta.required_skills.length > 0 && (
            <div className="generated-task-skills">
              <p className="generated-task-label">Required Skills:</p>
              <div className="skill-chips">
                {strategicMeta.required_skills.slice(0, 5).map((skill, i) => (
                  <span key={i} className="skill-chip">{skill}</span>
                ))}
              </div>
            </div>
          )}

          {strategicMeta.success_criteria && (
            <details className="generated-task-expander">
              <summary>✅ Success Criteria</summary>
              <p>{strategicMeta.success_criteria}</p>
            </details>
          )}

      <div className="generated-task-analysis-section">
        {!showAnalysis ? (
          <Button variant="secondary" size="small" onClick={() => setShowAnalysis(true)}>
            🔎 AI Strategic Analysis
          </Button>
        ) : (
          <div className="generated-task-analysis-card">
            <div className="generated-task-analysis-header">
              <h5>AI Strategic Analysis</h5>
              <Button variant="ghost" size="small" onClick={() => setShowAnalysis(false)}>
                Close
              </Button>
            </div>
            <div className="generated-task-analysis-grid">
              {[
                { label: '🎯 Context', value: strategicMeta.context },
                { label: '🎯 Objective', value: strategicMeta.objective },
                { label: '🔁 Process', value: strategicMeta.process },
                { label: '📦 Delivery', value: strategicMeta.delivery },
                { label: '📊 Reporting', value: strategicMeta.reporting_requirements },
                { label: 'Goal Type', value: strategicMeta.goal_type },
                { label: 'Process Applied', value: strategicMeta.process_applied },
                { label: 'Execution Context', value: strategicMeta.q4_execution_context },
              ]
                .filter(item => item.value)
                .map(item => (
                  <div key={item.label} className="generated-task-analysis-item">
                    <p className="label">{item.label}</p>
                    <p>{item.value}</p>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>

          <div className="generated-task-rag-section">
            {showRecommendations ? (
              <div className="generated-task-recommendations">
                <div className="generated-task-recommendations-header">
                  <h5>Employee Recommendations</h5>
                  <Button
                    variant="ghost"
                    size="small"
                    onClick={() => setShowRecommendations(false)}
                  >
                    Close
                  </Button>
                </div>
                <RAGRecommendations
                  task={task}
                  onRecommendationApplied={() => {
                    onRecommendationApplied?.();
                    setShowRecommendations(false);
                  }}
                />
              </div>
            ) : (
              <div className="generated-task-rag-buttons">
                {hasRecommendations ? (
                  <>
                    <Button
                      variant="primary"
                      onClick={() => setShowRecommendations(true)}
                    >
                      🔍 View Employee Recommendations
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={async () => {
                        await taskService.generateRAGRecommendations(task.id);
                        // Refresh after a delay
                        setTimeout(() => {
                          onRecommendationApplied?.();
                        }, 2000);
                      }}
                    >
                      🔄 Refresh Recommendations
                    </Button>
                  </>
                ) : recommendationsFailed ? (
                  <>
                    <Button variant="danger" disabled>
                      ❌ Employee Recommendations Failed
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={async () => {
                        await taskService.generateRAGRecommendations(task.id);
                        setTimeout(() => {
                          onRecommendationApplied?.();
                        }, 2000);
                      }}
                    >
                      🔍 Retry Employee Recommendations
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="primary"
                    onClick={async () => {
                      await taskService.generateRAGRecommendations(task.id);
                      setTimeout(() => {
                        onRecommendationApplied?.();
                      }, 2000);
                    }}
                  >
                    🔍 Get Employee Recommendations
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="generated-task-actions">
          <div className="generated-task-actions-section">
            <h5>Actions</h5>
            
            {!showApproveForm ? (
              <Button
                variant="success"
                onClick={() => setShowApproveForm(true)}
                className="action-button"
              >
                ✅ Approve & Assign
              </Button>
            ) : (
              <div className="generated-task-approve-form">
                <label>
                  Assign to Employee
                  <select
                    value={task.assigned_to || ''}
                    onChange={(e) => onAssignmentChange(task.id, e.target.value)}
                  >
                    <option value="">Select employee...</option>
                    {employees.map(emp => (
                      <option key={emp.id} value={emp.id}>
                        {emp.name} {emp.role ? `(${emp.role})` : ''}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="generated-task-form-actions">
                  <Button
                    variant="primary"
                    onClick={handleApprove}
                    className="action-button"
                  >
                    Confirm Assignment
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => setShowApproveForm(false)}
                    className="action-button"
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {!showEditForm ? (
              <Button
                variant="secondary"
                onClick={() => setShowEditForm(true)}
                className="action-button"
              >
                ✏️ Edit Task
              </Button>
            ) : (
              <div className="generated-task-edit-form">
                <label>
                  Task Description
                  <textarea
                    value={task.task_description || ''}
                    onChange={(e) => onTaskChange(task.id, 'task_description', e.target.value)}
                    rows={3}
                  />
                </label>
                <label>
                  Priority
                  <select
                    value={task.priority || 'medium'}
                    onChange={(e) => onTaskChange(task.id, 'priority', e.target.value)}
                  >
                    {['low', 'medium', 'high', 'urgent'].map(opt => (
                      <option key={opt} value={opt}>{opt.toUpperCase()}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Status
                  <select
                    value={task.status || 'ai_suggested'}
                    onChange={(e) => onTaskChange(task.id, 'status', e.target.value)}
                  >
                    {['ai_suggested', 'not_started', 'pending', 'in_progress'].map(opt => (
                      <option key={opt} value={opt}>{opt.replace('_', ' ')}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Due Date
                  <input
                    type="date"
                    value={task.due_date ? task.due_date.slice(0, 10) : ''}
                    onChange={(e) => onTaskChange(task.id, 'due_date', e.target.value)}
                  />
                </label>
                <label>
                  Assigned Date
                  <input
                    type="date"
                    value={task.assigned_at ? task.assigned_at.slice(0, 10) : ''}
                    onChange={(e) => onTaskChange(task.id, 'assigned_at', e.target.value)}
                  />
                </label>
                <div className="generated-task-form-actions">
                  <Button
                    variant="primary"
                    onClick={() => {
                      setShowEditForm(false);
                      onRecommendationApplied?.();
                    }}
                    className="action-button"
                  >
                    Save Changes
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => setShowEditForm(false)}
                    className="action-button"
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GeneratedTaskCard;

