import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { employeeService } from '../../services/employee';
import { taskService } from '../../services/task';
import { Employee, Task } from '../../types';
import { Card } from '../../components/Common/UI/Card';
import { Button } from '../../components/Common/UI/Button';
import './Dashboard.css';

type TimeFilter = 'today' | 'week' | 'month' | 'year' | 'all';

interface DashboardStats {
  employees: {
    total: number;
    active: number;
    inactive: number;
  };
  tasks: {
    total: number;
    completed: number;
    inProgress: number;
    delayed: number;
    notStarted: number;
  };
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('all');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Load employees and tasks in parallel
      const [employeesData, tasksData] = await Promise.all([
        employeeService.getAllEmployees(true),
        taskService.getTasks()
      ]);
      
      // Ensure employees is an array
      let employeesArray: Employee[] = [];
      if (Array.isArray(employeesData)) {
        employeesArray = employeesData;
      } else if (employeesData && typeof employeesData === 'object' && 'employees' in employeesData) {
        employeesArray = Array.isArray((employeesData as any).employees) ? (employeesData as any).employees : [];
      }
      
      // Ensure tasks is an array
      let tasksArray: Task[] = [];
      if (Array.isArray(tasksData)) {
        tasksArray = tasksData;
      } else if (tasksData && typeof tasksData === 'object' && 'tasks' in tasksData) {
        tasksArray = Array.isArray((tasksData as any).tasks) ? (tasksData as any).tasks : [];
      }
      
      setEmployees(employeesArray);
      setTasks(tasksArray);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setError(err.message || 'Failed to load dashboard data');
      // Set empty arrays on error to prevent filter errors
      setEmployees([]);
      setTasks([]);
    } finally {
      setLoading(false);
    }
  };

  // Calculate date range based on filter
  const dateRange = useMemo(() => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    switch (timeFilter) {
      case 'today':
        return { start: today, end: now };
      case 'week':
        const weekStart = new Date(today);
        weekStart.setDate(today.getDate() - 7);
        return { start: weekStart, end: now };
      case 'month':
        const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
        return { start: monthStart, end: now };
      case 'year':
        const yearStart = new Date(today.getFullYear(), 0, 1);
        return { start: yearStart, end: now };
      default:
        return null; // All time
    }
  }, [timeFilter]);

  // Filter tasks based on date range
  const filteredTasks = useMemo(() => {
    if (!dateRange) return tasks;
    
    return tasks.filter(task => {
      const taskDate = task.created_at ? new Date(task.created_at) : null;
      if (!taskDate) return false;
      return taskDate >= dateRange.start && taskDate <= dateRange.end;
    });
  }, [tasks, dateRange]);

  // Calculate statistics
  const stats: DashboardStats = useMemo(() => {
    // Ensure employees is an array
    const employeesArray = Array.isArray(employees) ? employees : [];
    const tasksArray = Array.isArray(filteredTasks) ? filteredTasks : [];
    
    const activeEmployees = employeesArray.filter(emp => emp?.is_active);
    const inactiveEmployees = employeesArray.filter(emp => !emp?.is_active);
    
    const completedTasks = tasksArray.filter(t => t?.status === 'completed');
    const inProgressTasks = tasksArray.filter(t => t?.status === 'in_progress');
    const notStartedTasks = tasksArray.filter(t => t?.status === 'not_started');
    
    // Calculate delayed tasks (past due date and not completed)
    const now = new Date();
    const delayedTasks = tasksArray.filter(task => {
      if (!task?.due_date || task?.status === 'completed') return false;
      try {
        const dueDate = new Date(task.due_date);
        return dueDate < now;
      } catch {
        return false;
      }
    });

    return {
      employees: {
        total: employeesArray.length,
        active: activeEmployees.length,
        inactive: inactiveEmployees.length,
      },
      tasks: {
        total: tasksArray.length,
        completed: completedTasks.length,
        inProgress: inProgressTasks.length,
        delayed: delayedTasks.length,
        notStarted: notStartedTasks.length,
      },
    };
  }, [employees, filteredTasks]);

  // Calculate completion rate
  const completionRate = useMemo(() => {
    if (stats.tasks.total === 0) return 0;
    return Math.round((stats.tasks.completed / stats.tasks.total) * 100);
  }, [stats]);

  // Calculate active employee percentage
  const activeEmployeeRate = useMemo(() => {
    if (stats.employees.total === 0) return 0;
    return Math.round((stats.employees.active / stats.employees.total) * 100);
  }, [stats]);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner">⏳</div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <div className="error-icon">⚠️</div>
        <h3>Error Loading Dashboard</h3>
        <p>{error}</p>
        <Button onClick={loadDashboardData}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="admin-dashboard-page">
      <div className="dashboard-header">
    <div>
          <h1>📊 Admin Dashboard</h1>
          <p className="dashboard-subtitle">Comprehensive overview of your organization</p>
        </div>
        <div className="time-filter-group">
          <label>Time Period:</label>
          <div className="time-filter-buttons">
            {(['today', 'week', 'month', 'year', 'all'] as TimeFilter[]).map(filter => (
              <button
                key={filter}
                className={`time-filter-btn ${timeFilter === filter ? 'active' : ''}`}
                onClick={() => setTimeFilter(filter)}
              >
                {filter.charAt(0).toUpperCase() + filter.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Employee Statistics */}
      <div className="dashboard-section">
        <h2 className="section-title">
          <span className="section-icon">👥</span>
          Employee Statistics
        </h2>
        <div className="stats-grid">
          <Card className="stat-card employee-total">
            <div className="stat-card-content">
              <div className="stat-icon">👥</div>
              <div className="stat-info">
                <h3>Total Employees</h3>
                <p className="stat-value">{stats.employees.total}</p>
              </div>
            </div>
          </Card>

          <Card className="stat-card employee-active">
            <div className="stat-card-content">
              <div className="stat-icon active-icon">🟢</div>
              <div className="stat-info">
                <h3>Active Employees</h3>
                <p className="stat-value">{stats.employees.active}</p>
                <p className="stat-percentage">{activeEmployeeRate}% active</p>
              </div>
              <div className="stat-progress">
                <div 
                  className="progress-bar active-progress"
                  style={{ width: `${activeEmployeeRate}%` }}
                />
              </div>
            </div>
          </Card>

          <Card className="stat-card employee-inactive">
            <div className="stat-card-content">
              <div className="stat-icon inactive-icon">🔴</div>
              <div className="stat-info">
                <h3>Inactive Employees</h3>
                <p className="stat-value">{stats.employees.inactive}</p>
                <p className="stat-percentage">{100 - activeEmployeeRate}% inactive</p>
              </div>
              <div className="stat-progress">
                <div 
                  className="progress-bar inactive-progress"
                  style={{ width: `${100 - activeEmployeeRate}%` }}
                />
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Task Statistics */}
      <div className="dashboard-section">
        <h2 className="section-title">
          <span className="section-icon">📋</span>
          Task Statistics
          {dateRange && (
            <span className="date-range-badge">
              {dateRange.start.toLocaleDateString()} - {dateRange.end.toLocaleDateString()}
            </span>
          )}
        </h2>
        <div className="stats-grid">
          <Card className="stat-card task-total">
            <div className="stat-card-content">
              <div className="stat-icon">📋</div>
              <div className="stat-info">
                <h3>Total Tasks</h3>
                <p className="stat-value">{stats.tasks.total}</p>
              </div>
            </div>
          </Card>

          <Card className="stat-card task-completed">
            <div className="stat-card-content">
              <div className="stat-icon completed-icon">✅</div>
              <div className="stat-info">
                <h3>Completed</h3>
                <p className="stat-value">{stats.tasks.completed}</p>
                <p className="stat-percentage">{completionRate}% completion rate</p>
              </div>
              <div className="stat-progress">
                <div 
                  className="progress-bar completed-progress"
                  style={{ width: `${completionRate}%` }}
                />
              </div>
            </div>
          </Card>

          <Card className="stat-card task-in-progress">
            <div className="stat-card-content">
              <div className="stat-icon in-progress-icon">🔄</div>
              <div className="stat-info">
                <h3>In Progress</h3>
                <p className="stat-value">{stats.tasks.inProgress}</p>
                <p className="stat-percentage">
                  {stats.tasks.total > 0 
                    ? Math.round((stats.tasks.inProgress / stats.tasks.total) * 100) 
                    : 0}% of total
                </p>
              </div>
              <div className="stat-progress">
                <div 
                  className="progress-bar in-progress-bar"
                  style={{ 
                    width: `${stats.tasks.total > 0 ? (stats.tasks.inProgress / stats.tasks.total) * 100 : 0}%` 
                  }}
                />
              </div>
            </div>
          </Card>

          <Card className="stat-card task-delayed">
            <div className="stat-card-content">
              <div className="stat-icon delayed-icon">⚠️</div>
              <div className="stat-info">
                <h3>Delayed</h3>
                <p className="stat-value">{stats.tasks.delayed}</p>
                <p className="stat-percentage">
                  {stats.tasks.total > 0 
                    ? Math.round((stats.tasks.delayed / stats.tasks.total) * 100) 
                    : 0}% of total
                </p>
              </div>
              <div className="stat-progress">
                <div 
                  className="progress-bar delayed-progress"
                  style={{ 
                    width: `${stats.tasks.total > 0 ? (stats.tasks.delayed / stats.tasks.total) * 100 : 0}%` 
                  }}
                />
              </div>
            </div>
          </Card>

          <Card className="stat-card task-not-started">
            <div className="stat-card-content">
              <div className="stat-icon not-started-icon">⏸️</div>
              <div className="stat-info">
                <h3>Not Started</h3>
                <p className="stat-value">{stats.tasks.notStarted}</p>
                <p className="stat-percentage">
                  {stats.tasks.total > 0 
                    ? Math.round((stats.tasks.notStarted / stats.tasks.total) * 100) 
                    : 0}% of total
                </p>
              </div>
              <div className="stat-progress">
                <div 
                  className="progress-bar not-started-progress"
                  style={{ 
                    width: `${stats.tasks.total > 0 ? (stats.tasks.notStarted / stats.tasks.total) * 100 : 0}%` 
                  }}
                />
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Visual Chart Section */}
      <div className="dashboard-section">
        <h2 className="section-title">
          <span className="section-icon">📊</span>
          Task Status Distribution
        </h2>
        <Card className="chart-card">
          <div className="chart-container">
            <div className="chart-bars">
              <div className="chart-bar-group">
                <div 
                  className="chart-bar completed-bar"
                  style={{ 
                    height: `${stats.tasks.total > 0 ? (stats.tasks.completed / stats.tasks.total) * 300 : 0}px`,
                    width: '20%'
                  }}
                  title={`Completed: ${stats.tasks.completed}`}
                >
                  <span className="chart-bar-value">{stats.tasks.completed}</span>
                </div>
                <label>Completed</label>
              </div>
              <div className="chart-bar-group">
                <div 
                  className="chart-bar in-progress-bar"
                  style={{ 
                    height: `${stats.tasks.total > 0 ? (stats.tasks.inProgress / stats.tasks.total) * 300 : 0}px`,
                    width: '20%'
                  }}
                  title={`In Progress: ${stats.tasks.inProgress}`}
                >
                  <span className="chart-bar-value">{stats.tasks.inProgress}</span>
                </div>
                <label>In Progress</label>
              </div>
              <div className="chart-bar-group">
                <div 
                  className="chart-bar delayed-bar"
                  style={{ 
                    height: `${stats.tasks.total > 0 ? (stats.tasks.delayed / stats.tasks.total) * 300 : 0}px`,
                    width: '20%'
                  }}
                  title={`Delayed: ${stats.tasks.delayed}`}
                >
                  <span className="chart-bar-value">{stats.tasks.delayed}</span>
                </div>
                <label>Delayed</label>
              </div>
              <div className="chart-bar-group">
                <div 
                  className="chart-bar not-started-bar"
                  style={{ 
                    height: `${stats.tasks.total > 0 ? (stats.tasks.notStarted / stats.tasks.total) * 300 : 0}px`,
                    width: '20%'
                  }}
                  title={`Not Started: ${stats.tasks.notStarted}`}
                >
                  <span className="chart-bar-value">{stats.tasks.notStarted}</span>
                </div>
                <label>Not Started</label>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="dashboard-section">
        <h2 className="section-title">
          <span className="section-icon">⚡</span>
          Quick Actions
        </h2>
        <div className="quick-actions-grid">
          <Button 
            variant="primary" 
            onClick={() => navigate('/admin/employee-management')}
            className="quick-action-btn"
          >
            👥 Manage Employees
          </Button>
          <Button 
            variant="primary" 
            onClick={() => navigate('/admin/task-management')}
            className="quick-action-btn"
          >
            📋 Manage Tasks
          </Button>
          <Button 
            variant="secondary" 
            onClick={() => navigate('/admin/notifications')}
            className="quick-action-btn"
          >
            🔔 View Notifications
          </Button>
          <Button 
            variant="secondary" 
            onClick={loadDashboardData}
            className="quick-action-btn"
          >
            🔄 Refresh Data
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
