import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Employee } from '../../types';
import { DashboardCard, DashboardCardsGrid } from './DashboardCards';
import './EmployeeDashboard.css';

interface EmployeeStats {
  pendingTasks: number;
  completedTasks: number;
  totalTasks: number;
  performanceScore?: number;
  upcomingDeadlines: number;
}

export const EmployeeDashboard: React.FC = () => {
  const { user } = useAuth();
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [stats, setStats] = useState<EmployeeStats>({
    pendingTasks: 0,
    completedTasks: 0,
    totalTasks: 0,
    performanceScore: 0,
    upcomingDeadlines: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate loading employee data and stats
    const loadEmployeeData = async () => {
      try {
        setLoading(true);
        // In a real app, you would fetch employee-specific data here
        // For now, we'll simulate with mock data
        
        // Mock employee stats
        const mockStats: EmployeeStats = {
          pendingTasks: 5,
          completedTasks: 12,
          totalTasks: 17,
          performanceScore: 85,
          upcomingDeadlines: 2
        };

        setStats(mockStats);
        
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
      } catch (error) {
        console.error('Failed to load employee data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadEmployeeData();
  }, []);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner">⏳</div>
        <p>Loading your dashboard...</p>
      </div>
    );
  }

  const completionRate = stats.totalTasks > 0 
    ? Math.round((stats.completedTasks / stats.totalTasks) * 100) 
    : 0;

  return (
    <div className="employee-dashboard">
      <div className="dashboard-header">
        <h1>👤 Employee Dashboard</h1>
        <p>Welcome back, <strong>{user?.name || 'Employee'}</strong>!</p>
      </div>

      {/* Work Summary Cards */}
      <DashboardCardsGrid>
        <DashboardCard
          title="Pending Tasks"
          value={stats.pendingTasks}
          icon="📋"
          variant="warning"
        />
        <DashboardCard
          title="Completed Tasks"
          value={stats.completedTasks}
          subtitle={`${completionRate}% completion rate`}
          icon="✅"
          variant="success"
        />
        <DashboardCard
          title="Performance Score"
          value={`${stats.performanceScore}%`}
          icon="⭐"
          variant="primary"
        />
        <DashboardCard
          title="Upcoming Deadlines"
          value={stats.upcomingDeadlines}
          icon="⏰"
          variant="danger"
        />
      </DashboardCardsGrid>

      {/* Quick Access Section */}
      <div className="dashboard-section">
        <h2>🚀 Quick Access</h2>
        <div className="quick-access">
          <button className="access-btn">
            <span className="access-icon">📋</span>
            <span className="access-text">My Tasks</span>
            <span className="access-badge">{stats.pendingTasks}</span>
          </button>
          <button className="access-btn">
            <span className="access-icon">👤</span>
            <span className="access-text">My Profile</span>
          </button>
          <button className="access-btn">
            <span className="access-icon">🔔</span>
            <span className="access-text">Notifications</span>
            <span className="access-badge">3</span>
          </button>
          <button className="access-btn">
            <span className="access-icon">📊</span>
            <span className="access-text">Performance</span>
          </button>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="dashboard-section">
        <h2>📈 My Recent Activity</h2>
        <div className="recent-activity">
          <div className="activity-timeline">
            <div className="timeline-item">
              <div className="timeline-marker completed"></div>
              <div className="timeline-content">
                <div className="timeline-title">Completed task: Monthly Report</div>
                <div className="timeline-time">2 hours ago</div>
              </div>
            </div>
            <div className="timeline-item">
              <div className="timeline-marker assigned"></div>
              <div className="timeline-content">
                <div className="timeline-title">New task assigned: Client Meeting</div>
                <div className="timeline-time">Yesterday</div>
              </div>
            </div>
            <div className="timeline-item">
              <div className="timeline-marker updated"></div>
              <div className="timeline-content">
                <div className="timeline-title">Updated profile information</div>
                <div className="timeline-time">2 days ago</div>
              </div>
            </div>
            <div className="timeline-item">
              <div className="timeline-marker completed"></div>
              <div className="timeline-content">
                <div className="timeline-title">Completed task: Code Review</div>
                <div className="timeline-time">3 days ago</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Overview */}
      <div className="dashboard-section">
        <h2>📊 Performance Overview</h2>
        <div className="performance-overview">
          <div className="performance-metric">
            <div className="metric-label">Task Completion</div>
            <div className="metric-bar">
              <div 
                className="metric-fill completion" 
                style={{ width: `${completionRate}%` }}
              ></div>
            </div>
            <div className="metric-value">{completionRate}%</div>
          </div>
          <div className="performance-metric">
            <div className="metric-label">On Time Delivery</div>
            <div className="metric-bar">
              <div 
                className="metric-fill ontime" 
                style={{ width: '92%' }}
              ></div>
            </div>
            <div className="metric-value">92%</div>
          </div>
          <div className="performance-metric">
            <div className="metric-label">Quality Score</div>
            <div className="metric-bar">
              <div 
                className="metric-fill quality" 
                style={{ width: '88%' }}
              ></div>
            </div>
            <div className="metric-value">88%</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmployeeDashboard;