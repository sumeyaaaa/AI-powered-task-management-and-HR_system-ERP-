import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { taskService } from '../../services/task';
import { Task } from '../../types';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalTasks: 0,
    completedTasks: 0,
    pendingTasks: 0,
    overdueTasks: 0
  });

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Load recent tasks assigned to current user
      const tasks = await taskService.getTasks({
        assigned_to: user?.id || 'all',
        status: 'all'
      });
      
      setRecentTasks(tasks.slice(0, 5)); // Show only 5 most recent
      
      // Calculate stats
      const totalTasks = tasks.length;
      const completedTasks = tasks.filter(t => t.status === 'completed').length;
      const pendingTasks = tasks.filter(t => t.status === 'pending').length;
      const overdueTasks = tasks.filter(t => 
        t.due_date && new Date(t.due_date) < new Date() && t.status !== 'completed'
      ).length;

      setStats({
        totalTasks,
        completedTasks,
        pendingTasks,
        overdueTasks
      });
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="dashboard-loading">Loading your dashboard...</div>;
  }

  return (
    <div className="employee-dashboard">
      <div className="dashboard-header">
        <h1>📊 Employee Dashboard</h1>
        <p>Welcome back, <strong>{user?.name}</strong>! Here's your current overview.</p>
      </div>

      {/* Quick Stats */}
      <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-icon">📋</div>
          <div className="stat-info">
            <h3>Total Tasks</h3>
            <p className="stat-number">{stats.totalTasks}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-info">
            <h3>Completed</h3>
            <p className="stat-number">{stats.completedTasks}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">⏳</div>
          <div className="stat-info">
            <h3>Pending</h3>
            <p className="stat-number">{stats.pendingTasks}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">⚠️</div>
          <div className="stat-info">
            <h3>Overdue</h3>
            <p className="stat-number">{stats.overdueTasks}</p>
          </div>
        </div>
      </div>

      {/* Recent Tasks */}
      <div className="dashboard-section">
        <h2>Recent Tasks</h2>
        {recentTasks.length === 0 ? (
          <div className="no-tasks">
            <p>No tasks assigned to you yet.</p>
          </div>
        ) : (
          <div className="recent-tasks">
            {recentTasks.map(task => (
              <div key={task.id} className="task-item">
                <div className="task-main">
                  <h4>{task.title}</h4>
                  <p className="task-description">{task.description}</p>
                  <div className="task-meta">
                    <span className={`priority-badge priority-${task.priority}`}>
                      {task.priority}
                    </span>
                    <span className="task-due-date">
                      Due: {new Date(task.due_date).toLocaleDateString()}
                    </span>
                    <span className={`status-badge status-${task.status}`}>
                      {task.status}
                    </span>
                  </div>
                </div>
                <div className="task-actions">
                  <button className="btn-secondary btn-sm">
                    View Details
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="dashboard-section">
        <h2>Quick Actions</h2>
        <div className="quick-actions">
          <button className="action-card">
            <span className="action-icon">📋</span>
            <span className="action-text">View All Tasks</span>
          </button>
          <button className="action-card">
            <span className="action-icon">👤</span>
            <span className="action-text">Update Profile</span>
          </button>
          <button className="action-card">
            <span className="action-icon">🔐</span>
            <span className="action-text">Change Password</span>
          </button>
          <button className="action-card">
            <span className="action-icon">🔔</span>
            <span className="action-text">View Notifications</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;