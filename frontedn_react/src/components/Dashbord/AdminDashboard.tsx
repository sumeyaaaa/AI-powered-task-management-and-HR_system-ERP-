import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { employeeService } from '../../services/employee';
import { Employee } from '../../types';
import './AdminDashboard.css';
import { DashboardCard, DashboardCardsGrid } from './DashboardCards';

interface AdminStats {
  totalEmployees: number;
  activeEmployees: number;
  departmentsCount: number;
  avgExperience: number;
  recentHires: Employee[];
}

export const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<AdminStats>({
    totalEmployees: 0,
    activeEmployees: 0,
    departmentsCount: 0,
    avgExperience: 0,
    recentHires: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        const employees = await employeeService.getAllEmployees(true);
        
        const activeEmployees = employees.filter(emp => emp.is_active);
        const departments = new Set(employees.map(emp => emp.department).filter(Boolean));
        
        // Calculate average experience, handling null/undefined values
        const experienceValues = employees
          .map(emp => emp.experience_years || 0)
          .filter(exp => exp > 0);
        
        const avgExperience = experienceValues.length > 0 
          ? experienceValues.reduce((a, b) => a + b, 0) / experienceValues.length 
          : 0;

        // Get recent hires (last 5)
        const recentHires = employees
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          .slice(0, 5);

        setStats({
          totalEmployees: employees.length,
          activeEmployees: activeEmployees.length,
          departmentsCount: departments.size,
          avgExperience: Math.round(avgExperience * 10) / 10,
          recentHires
        });
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
        setError('Failed to load dashboard data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner">⏳</div>
        <p>Loading dashboard data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <div className="error-icon">⚠️</div>
        <h3>Error Loading Dashboard</h3>
        <p>{error}</p>
        <button 
          onClick={() => window.location.reload()}
          className="retry-button"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      <div className="dashboard-header">
        <h1>📊 Admin Dashboard</h1>
        <p>Welcome back, <strong>System Administrator</strong>!</p>
      </div>

      {/* Quick Stats Cards */}
      <DashboardCardsGrid>
        <DashboardCard
          title="Total Employees"
          value={stats.totalEmployees}
          icon="👥"
          variant="primary"
        />
        <DashboardCard
          title="Active Employees"
          value={stats.activeEmployees}
          subtitle={`${Math.round((stats.activeEmployees / stats.totalEmployees) * 100)}% active`}
          icon="🟢"
          variant="success"
        />
        <DashboardCard
          title="Departments"
          value={stats.departmentsCount}
          icon="🏢"
          variant="secondary"
        />
        <DashboardCard
          title="Avg Experience"
          value={`${stats.avgExperience} yrs`}
          icon="📈"
          variant="warning"
        />
      </DashboardCardsGrid>

      {/* Recent Activity Section */}
      <div className="dashboard-section">
        <h2>📈 Recent Activity</h2>
        <div className="recent-activity">
          {stats.recentHires.length > 0 ? (
            <div className="activity-list">
              {stats.recentHires.map(employee => (
                <div key={employee.id} className="activity-item">
                  <div className="activity-icon">
                    {employee.is_active ? '🟢' : '🔴'}
                  </div>
                  <div className="activity-content">
                    <div className="activity-title">
                      <strong>{employee.name}</strong> - {employee.role}
                    </div>
                    <div className="activity-meta">
                      Joined {new Date(employee.created_at).toLocaleDateString()}
                      {employee.department && ` • ${employee.department}`}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-activity">
              <p>No recent employee activity found.</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="dashboard-section">
        <h2>⚡ Quick Actions</h2>
        <div className="quick-actions">
          <button className="quick-action-btn">
            <span className="action-icon">➕</span>
            <span className="action-text">Add New Employee</span>
          </button>
          <button className="quick-action-btn">
            <span className="action-icon">📋</span>
            <span className="action-text">Manage Tasks</span>
          </button>
          <button className="quick-action-btn">
            <span className="action-icon">⚙️</span>
            <span className="action-text">System Settings</span>
          </button>
          <button className="quick-action-btn">
            <span className="action-icon">📊</span>
            <span className="action-text">View Reports</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;