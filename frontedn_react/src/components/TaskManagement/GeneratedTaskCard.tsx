import React, { useState, useEffect } from 'react';
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
  onRAGStarted?: () => void; // Callback to restart objective-level polling
  objectiveRAGStatus?: {
    tasks?: Array<{
      task_id: string;
      task_description: string;
      status: 'completed' | 'in_progress' | 'pending' | 'failed';
      progress: number;
      current_activity: string;
      recommendations_count?: number;
      ai_meta_id?: string;
      has_recommendations?: boolean;
      error?: string;
    }>;
    summary?: {
      total_tasks: number;
      completed: number;
      in_progress: number;
      pending: number;
      failed: number;
    };
  };
}

export const GeneratedTaskCard: React.FC<GeneratedTaskCardProps> = ({
  task,
  index,
  employees,
  onTaskChange,
  onAssignmentChange,
  onRecommendationApplied,
  onRAGStarted,
  objectiveRAGStatus,
}) => {
  const strategicMeta = task.strategic_metadata || {};
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [showApproveForm, setShowApproveForm] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [generatingRecommendations, setGeneratingRecommendations] = useState(false);
  const [ragProgress, setRagProgress] = useState(0);
  const [ragActivity, setRagActivity] = useState('');
  const [ragMetaId, setRagMetaId] = useState<string | null>(null);
  const [assignmentStrategy, setAssignmentStrategy] = useState<string | null>(strategicMeta.assignment_strategy || null);
  const [roleMatchingFlow, setRoleMatchingFlow] = useState<boolean>(
    Boolean(strategicMeta.predefined_process || strategicMeta.assignment_strategy === 'role_based_predefined_process')
  );
  const hasRecommendations = strategicMeta.employee_recommendations_available || false;
  const recommendationsFailed = strategicMeta.recommendations_failed || false;
  const isPredefinedProcess = strategicMeta.predefined_process || false;
  const recommendedRole = strategicMeta.recommended_role || strategicMeta.assigned_role;
  
  // Check if this task has recommendations available from objective-level RAG
  const taskHasRecommendationsFromObjective = !isPredefinedProcess && 
    objectiveRAGStatus?.tasks?.find(t => t.task_id === task.id)?.has_recommendations;
  
  // Use objective-level recommendations status if available, otherwise fall back to task metadata
  const hasAvailableRecommendations = taskHasRecommendationsFromObjective !== undefined 
    ? taskHasRecommendationsFromObjective 
    : hasRecommendations;
  const objectiveTitle = task.objectives?.title || task.strategic_objective || 'No Objective';
  const assignedEmployee = employees.find(emp => emp.id === task.assigned_to);
  const sanitizeName = (value?: string | null) => {
    if (!value) return '';
    const cleaned = value.replace(/^[^A-Za-z]*[0-9]+[\s\-\|:_]+/, '').trim();
    return cleaned || value;
  };

  const assignedEmployeeName = sanitizeName(assignedEmployee?.name || task.assigned_to_name) || 'Unassigned';
  const isRoleMatchingStrategy = roleMatchingFlow || assignmentStrategy === 'role_based_predefined_process';

  useEffect(() => {
    setAssignmentStrategy(strategicMeta.assignment_strategy || null);
    setRoleMatchingFlow(Boolean(
      strategicMeta.predefined_process ||
      strategicMeta.assignment_strategy === 'role_based_predefined_process'
    ));
  }, [
    task.id,
    strategicMeta.assignment_strategy,
    strategicMeta.predefined_process
  ]);

  // Check if ANY task in the objective is processing RAG (only for AI-generated tasks, not predefined)
  // Only show progress indicator when RAG is actually in progress, not just pending
  const isAnyTaskProcessingRAG = !isPredefinedProcess && objectiveRAGStatus?.summary && 
    (objectiveRAGStatus.summary.in_progress > 0);
  
  // Check if objective-level RAG is complete
  const isObjectiveRAGComplete = !isPredefinedProcess && objectiveRAGStatus?.summary && 
    objectiveRAGStatus.summary.completed + objectiveRAGStatus.summary.failed === objectiveRAGStatus.summary.total_tasks &&
    objectiveRAGStatus.summary.total_tasks > 0;
  
  // Get this task's RAG status from objective status
  const thisTaskRAGStatus = objectiveRAGStatus?.tasks?.find(t => t.task_id === task.id);
  const isThisTaskProcessing = thisTaskRAGStatus?.status === 'in_progress';
  const overallProgress = objectiveRAGStatus?.summary 
    ? Math.round((objectiveRAGStatus.summary.completed / objectiveRAGStatus.summary.total_tasks) * 100)
    : 0;
  const currentActivity = isThisTaskProcessing 
    ? thisTaskRAGStatus?.current_activity 
    : objectiveRAGStatus?.tasks?.find(t => t.status === 'in_progress')?.current_activity || 'Processing RAG recommendations...';
  const progressTitle = isRoleMatchingStrategy ? '🎯 Role Matching Progress' : '🤖 RAG Analysis Progress';
  const progressPlaceholder = isRoleMatchingStrategy
    ? `Matching role${recommendedRole ? `: ${recommendedRole}` : ''}`
    : 'Processing...';

  // Keep local progress/activity in sync with objective-level polling updates
  useEffect(() => {
    if (!thisTaskRAGStatus) {
      return;
    }

    if (typeof thisTaskRAGStatus.progress === 'number') {
      setRagProgress(prev => {
        const nextProgress = Math.max(
          thisTaskRAGStatus.progress,
          isRoleMatchingStrategy && prev < 10 ? 10 : prev
        );
        return Math.min(100, nextProgress);
      });
    } else if (thisTaskRAGStatus.status === 'completed') {
      setRagProgress(100);
    }

    if (thisTaskRAGStatus.current_activity) {
      setRagActivity(thisTaskRAGStatus.current_activity);
    }

    if (thisTaskRAGStatus.status === 'completed' || thisTaskRAGStatus.status === 'failed') {
      setGeneratingRecommendations(false);
      setRagMetaId(null);
    } else if (thisTaskRAGStatus.status === 'in_progress') {
      setGeneratingRecommendations(true);
    }
  }, [thisTaskRAGStatus, isRoleMatchingStrategy]);

  // Poll for RAG progress when generating
  useEffect(() => {
    if (ragMetaId && generatingRecommendations) {
      const interval = setInterval(async () => {
        try {
          const result = await taskService.getRAGRecommendationProgress(ragMetaId);
          if (result.success) {
            const metaRecord = (result as any).ai_meta || result;
            const output = metaRecord?.output_json || result.output_json || {};

            const progressCandidates = [
              result.progress,
              metaRecord?.progress,
              output?.progress,
              output?.progress_percent,
              output?.progressPercentage,
            ];
            const latestProgress = progressCandidates.find(
              (candidate) => typeof candidate === 'number'
            );
            if (typeof latestProgress === 'number') {
              setRagProgress(latestProgress);
            }

            const latestStrategy =
              output?.assignment_strategy ||
              metaRecord?.assignment_strategy ||
              (result as any).assignment_strategy;
            if (latestStrategy) {
              setAssignmentStrategy(latestStrategy);
            }

            const isRoleFlowUpdate =
              typeof output?.is_predefined_process === 'boolean'
                ? output.is_predefined_process
                : typeof metaRecord?.is_predefined_process === 'boolean'
                ? metaRecord.is_predefined_process
                : typeof (result as any).is_predefined_process === 'boolean'
                ? (result as any).is_predefined_process
                : undefined;
            if (typeof isRoleFlowUpdate === 'boolean') {
              setRoleMatchingFlow(isRoleFlowUpdate);
            }

            const activityLine =
              output?.current_activity ||
              metaRecord?.current_activity ||
              result.current_activity ||
              '';
            const activityDetails =
              output?.activity_details || metaRecord?.activity_details;
            if (activityLine || activityDetails) {
              const composed = activityDetails
                ? `${activityLine || ''}${activityLine ? ' - ' : ''}${activityDetails}`
                : activityLine;
              setRagActivity(composed);
            }

            const status =
              output?.status ||
              metaRecord?.status ||
              result.status ||
              (metaRecord?.output_json?.status ?? undefined);

            if (status === 'completed') {
              setGeneratingRecommendations(false);
              setRagMetaId(null);
              setRagProgress(100);
              onRecommendationApplied?.();
            } else if (status === 'error' || status === 'failed') {
              setGeneratingRecommendations(false);
              setRagMetaId(null);
            }
          }
        } catch (err) {
          console.error('Error checking RAG progress:', err);
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [ragMetaId, generatingRecommendations, onRecommendationApplied]);

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

  const triggerRecommendationGeneration = async () => {
    try {
      setGeneratingRecommendations(true);
      const initialRoleFlow = isRoleMatchingStrategy;
      const initialMessage = initialRoleFlow
        ? `Matching role${recommendedRole ? `: ${recommendedRole}` : ''}`
        : 'Starting RAG analysis...';
      setRagActivity(initialMessage);
      setRagProgress(initialRoleFlow ? 10 : 0);

      const result = await taskService.generateRAGRecommendations(task.id);
      if (result.success && result.ai_meta_id) {
        setRagMetaId(result.ai_meta_id);
        if (result.assignment_strategy) {
          setAssignmentStrategy(result.assignment_strategy);
        }
        if (typeof result.is_predefined_process === 'boolean') {
          setRoleMatchingFlow(result.is_predefined_process);
          if (result.is_predefined_process) {
            setRagProgress((prev) => (prev < 10 ? 10 : prev));
          }
        }
        if (result.initial_activity) {
          setRagActivity(result.initial_activity);
        }
        onRAGStarted?.();
      } else {
        setGeneratingRecommendations(false);
        setRagActivity(result.error || 'Failed to start employee matching');
      }
    } catch (error) {
      console.error(error);
      setGeneratingRecommendations(false);
      setRagActivity('Error starting employee matching');
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
                      onClick={triggerRecommendationGeneration}
                      disabled={generatingRecommendations}
                    >
                      {generatingRecommendations ? '⏳ Refreshing...' : '🔄 Refresh Recommendations'}
                    </Button>
                    {generatingRecommendations && (
                      <div style={{
                        marginTop: '12px',
                        padding: '12px',
                        backgroundColor: '#f8f9fa',
                        borderRadius: '6px',
                        border: '1px solid #e0e0e0'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{ fontSize: '14px', fontWeight: 600 }}>{progressTitle}</span>
                          <span style={{ fontSize: '12px', color: '#666' }}>{ragProgress}%</span>
                        </div>
                        <div style={{
                          width: '100%',
                          height: '6px',
                          backgroundColor: '#e0e0e0',
                          borderRadius: '3px',
                          overflow: 'hidden',
                          marginBottom: '8px'
                        }}>
                          <div style={{
                            width: `${ragProgress}%`,
                            height: '100%',
                            backgroundColor: '#4caf50',
                            transition: 'width 0.3s ease'
                          }} />
                        </div>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {ragActivity || progressPlaceholder}
                        </div>
                      </div>
                    )}
                  </>
                ) : recommendationsFailed ? (
                  <>
                    <Button variant="danger" disabled>
                      ❌ Employee Recommendations Failed
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={triggerRecommendationGeneration}
                      disabled={generatingRecommendations}
                    >
                      {generatingRecommendations ? '⏳ Retrying...' : '🔍 Retry Employee Recommendations'}
                    </Button>
                    {generatingRecommendations && (
                      <div style={{
                        marginTop: '12px',
                        padding: '12px',
                        backgroundColor: '#f8f9fa',
                        borderRadius: '6px',
                        border: '1px solid #e0e0e0'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{ fontSize: '14px', fontWeight: 600 }}>{progressTitle}</span>
                          <span style={{ fontSize: '12px', color: '#666' }}>{ragProgress}%</span>
                        </div>
                        <div style={{
                          width: '100%',
                          height: '6px',
                          backgroundColor: '#e0e0e0',
                          borderRadius: '3px',
                          overflow: 'hidden',
                          marginBottom: '8px'
                        }}>
                          <div style={{
                            width: `${ragProgress}%`,
                            height: '100%',
                            backgroundColor: '#4caf50',
                            transition: 'width 0.3s ease'
                          }} />
                        </div>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {ragActivity || progressPlaceholder}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                  {generatingRecommendations ? (
                    // Show task-specific progress when user clicked the button for this task
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '6px',
                      border: '1px solid #e0e0e0'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                        <span style={{ fontSize: '14px', fontWeight: 600 }}>{progressTitle}</span>
                        <span style={{ fontSize: '12px', color: '#666' }}>{ragProgress}%</span>
                      </div>
                      <div style={{
                        width: '100%',
                        height: '6px',
                        backgroundColor: '#e0e0e0',
                        borderRadius: '3px',
                        overflow: 'hidden',
                        marginBottom: '8px'
                      }}>
                        <div style={{
                          width: `${ragProgress}%`,
                          height: '100%',
                          backgroundColor: '#4caf50',
                          transition: 'width 0.3s ease'
                        }} />
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        {ragActivity || progressPlaceholder}
                      </div>
                    </div>
                  ) : isAnyTaskProcessingRAG ? (
                    // Show objective-level progress only when other tasks are processing (not this one)
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '6px',
                      border: '1px solid #e0e0e0'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                        <span style={{ fontSize: '14px', fontWeight: 600 }}>⏳ RAG Analysis in Progress (Other Tasks)</span>
                        <span style={{ fontSize: '12px', color: '#666' }}>{overallProgress}%</span>
                      </div>
                      <div style={{
                        width: '100%',
                        height: '6px',
                        backgroundColor: '#e0e0e0',
                        borderRadius: '3px',
                        overflow: 'hidden',
                        marginBottom: '8px'
                      }}>
                        <div style={{
                          width: `${overallProgress}%`,
                          height: '100%',
                          backgroundColor: '#4caf50',
                          transition: 'width 0.3s ease'
                        }} />
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        {currentActivity || 'Processing RAG recommendations...'}
                      </div>
                      {objectiveRAGStatus?.summary && (
                        <div style={{ fontSize: '11px', color: '#999', marginTop: '8px' }}>
                          {objectiveRAGStatus.summary.completed}/{objectiveRAGStatus.summary.total_tasks} tasks completed
                        </div>
                      )}
                    </div>
                  ) : isObjectiveRAGComplete && hasAvailableRecommendations ? (
                    // Objective-level RAG is complete and recommendations are available, show button to view
                    <Button
                      variant="primary"
                      onClick={() => setShowRecommendations(true)}
                    >
                      🔍 View Employee Recommendations
                    </Button>
                  ) : isObjectiveRAGComplete && !hasAvailableRecommendations ? (
                    // Objective-level RAG is complete but no recommendations for this task
                    <Button
                      variant="secondary"
                      onClick={triggerRecommendationGeneration}
                      disabled={generatingRecommendations}
                    >
                      {generatingRecommendations ? '⏳ Generating...' : '🔍 Get Employee Recommendations'}
                    </Button>
                ) : (
                    <>
                  <Button
                    variant="primary"
                        onClick={triggerRecommendationGeneration}
                        disabled={generatingRecommendations || isAnyTaskProcessingRAG}
                      >
                        {generatingRecommendations ? '⏳ Generating...' : '🔍 Get Employee Recommendations'}
                  </Button>
                    </>
                  )}
                  </>
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

