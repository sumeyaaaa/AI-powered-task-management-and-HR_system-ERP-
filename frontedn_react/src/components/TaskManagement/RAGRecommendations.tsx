import React, { useState, useEffect } from 'react';
import { Task, EmployeeRecommendation } from '../../types';
import { taskService } from '../../services/task';
import { Button } from '../Common/UI/Button';
import './RAGRecommendations.css';

interface RAGRecommendationsProps {
  task: Task;
  onRecommendationApplied?: () => void;
}

export const RAGRecommendations: React.FC<RAGRecommendationsProps> = ({
  task,
  onRecommendationApplied,
}) => {
  const [recommendations, setRecommendations] = useState<EmployeeRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [ragMetaId, setRagMetaId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [currentActivity, setCurrentActivity] = useState('');

  const strategicMeta = task.strategic_metadata || {};
  const isRAGEnhanced = strategicMeta.rag_enhanced || false;
  const recommendationsAvailable = strategicMeta.employee_recommendations_available || false;

  useEffect(() => {
    if (recommendationsAvailable) {
      loadRecommendations();
    }
  }, [task.id, recommendationsAvailable]);

  useEffect(() => {
    if (ragMetaId && generating) {
      const interval = setInterval(() => {
        checkProgress();
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [ragMetaId, generating]);

  const loadRecommendations = async () => {
    try {
      setLoading(true);
      setError('');
      const result = await taskService.getTaskEmployeeRecommendations(task.id);
      if (result.success && result.recommendations) {
        setRecommendations(result.recommendations);
      } else {
        setError(result.error || 'Failed to load recommendations');
      }
    } catch (err) {
      setError('Failed to load recommendations');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const generateRecommendations = async () => {
    try {
      setGenerating(true);
      setError('');
      setProgress(0);
      const result = await taskService.generateRAGRecommendations(task.id);
      if (result.success && result.ai_meta_id) {
        setRagMetaId(result.ai_meta_id);
      } else {
        setError(result.error || 'Failed to start RAG analysis');
        setGenerating(false);
      }
    } catch (err) {
      setError('Failed to generate recommendations');
      setGenerating(false);
      console.error(err);
    }
  };

  const checkProgress = async () => {
    if (!ragMetaId) return;

    try {
      const result = await taskService.getRAGRecommendationProgress(ragMetaId);
      if (result.success) {
        if (result.progress !== undefined) {
          setProgress(result.progress);
        }
        if (result.current_activity) {
          setCurrentActivity(result.current_activity);
        }

        if (result.status === 'completed') {
          setGenerating(false);
          setRagMetaId(null);
          await loadRecommendations();
        } else if (result.status === 'failed') {
          setError(result.output_json?.error || 'RAG analysis failed');
          setGenerating(false);
          setRagMetaId(null);
        }
      } else {
        setError(result.error || 'Failed to check progress');
        setGenerating(false);
        setRagMetaId(null);
      }
    } catch (err) {
      console.error('Error checking progress:', err);
    }
  };

  const applyRecommendation = async (employeeId: string, recommendation: EmployeeRecommendation) => {
    try {
      const result = await taskService.applyEmployeeRecommendation(task.id, employeeId, recommendation);
      if (result.success) {
        onRecommendationApplied?.();
        // Reload recommendations to update status
        await loadRecommendations();
      } else {
        setError(result.error || 'Failed to apply recommendation');
      }
    } catch (err) {
      setError('Failed to apply recommendation');
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="rag-recommendations">
        <div className="rag-loading">Loading recommendations...</div>
      </div>
    );
  }

  if (generating) {
    return (
      <div className="rag-recommendations">
        <div className="rag-generating">
          <div className="rag-progress-bar">
            <div className="rag-progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <p className="rag-activity">{currentActivity || 'Analyzing employees...'}</p>
          <p className="rag-progress-text">{progress}% complete</p>
        </div>
      </div>
    );
  }

  if (error && !recommendations.length) {
    return (
      <div className="rag-recommendations">
        <div className="rag-error">{error}</div>
        <Button variant="secondary" onClick={generateRecommendations}>
          🔍 Retry RAG Recommendations
        </Button>
      </div>
    );
  }

  return (
    <div className="rag-recommendations">
      <div className="rag-header">
        <h4>👥 AI Employee Recommendations</h4>
        {isRAGEnhanced && (
          <span className="rag-badge">🔍 RAG-Enhanced</span>
        )}
      </div>

      {isRAGEnhanced && (
        <div className="rag-info">
          <p>Using JD documents for precise employee matching</p>
          {strategicMeta.employees_with_jd && (
            <p className="rag-meta">JD Documents analyzed: {strategicMeta.employees_with_jd}</p>
          )}
        </div>
      )}

      {strategicMeta.recommendations_analysis && (
        <div className="rag-analysis">
          <strong>Analysis:</strong>
          <p>{strategicMeta.recommendations_analysis}</p>
        </div>
      )}

      {recommendations.length === 0 ? (
        <div className="rag-empty">
          <p>No recommendations available yet.</p>
          <Button variant="primary" onClick={generateRecommendations}>
            🔍 Generate AI Recommendations
          </Button>
        </div>
      ) : (
        <>
          <div className="rag-summary">
            <p><strong>{recommendations.length}</strong> recommendation(s) found</p>
            {strategicMeta.total_employees_considered && (
              <p className="rag-meta">Employees analyzed: {strategicMeta.total_employees_considered}</p>
            )}
          </div>

          <div className="rag-list">
            {recommendations.map((rec, index) => (
              <div key={index} className="rag-card">
                <div className="rag-card-header">
                  <div>
                    <h5>{rec.employee_name}</h5>
                    {rec.employee_role && <p className="rag-role">{rec.employee_role}</p>}
                    {rec.employee_department && (
                      <p className="rag-department">{rec.employee_department}</p>
                    )}
                  </div>
                  <div className="rag-score">
                    <span className={`rag-score-value rag-score-${getScoreClass(rec.fit_score)}`}>
                      {rec.fit_score}%
                    </span>
                    <span className="rag-score-label">Fit Score</span>
                  </div>
                </div>

                {rec.rag_enhanced && (
                  <div className="rag-enhanced-badge">🔍 RAG Enhanced</div>
                )}

                {rec.role_based_assignment && (
                  <div className="rag-role-badge">🎯 Role-Based Assignment</div>
                )}

                {rec.reason && (
                  <div className="rag-reason">
                    <strong>Reason:</strong>
                    <p>{rec.reason}</p>
                  </div>
                )}

                {rec.key_qualifications && rec.key_qualifications.length > 0 && (
                  <div className="rag-qualifications">
                    <strong>Key Qualifications:</strong>
                    <ul>
                      {rec.key_qualifications.map((qual, i) => (
                        <li key={i}>{qual}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {rec.skills_match_list && rec.skills_match_list.length > 0 && (
                  <div className="rag-skills">
                    <strong>Skills Match:</strong>
                    <div className="rag-skills-tags">
                      {rec.skills_match_list.map((skill, i) => (
                        <span key={i} className="rag-skill-tag">{skill}</span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="rag-actions">
                  <Button
                    variant="primary"
                    size="small"
                    onClick={() => applyRecommendation(rec.employee_id, rec)}
                  >
                    Assign to {rec.employee_name}
                  </Button>
                </div>
              </div>
            ))}
          </div>

          <div className="rag-actions-footer">
            <Button variant="secondary" onClick={generateRecommendations}>
              🔄 Refresh Recommendations
            </Button>
          </div>
        </>
      )}
    </div>
  );
};

function getScoreClass(score: number): string {
  if (score >= 90) return 'excellent';
  if (score >= 80) return 'good';
  if (score >= 70) return 'moderate';
  return 'low';
}

export default RAGRecommendations;

