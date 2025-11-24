import React, { useMemo } from 'react';
import { Employee } from '../../types';
import { Button } from '../Common/UI/Button';
import './EmployeeAnalytics.css';

interface EmployeeAnalyticsProps {
  employees: Employee[];
  onBack: () => void;
}

export const EmployeeAnalytics: React.FC<EmployeeAnalyticsProps> = ({ employees, onBack }) => {
  const stats = useMemo(() => {
    const total = employees.length;
    const active = employees.filter(emp => emp.is_active).length;
    const inactive = total - active;
    const experienceValues = employees.map(emp => emp.experience_years || 0);
    const avgExp = experienceValues.length
      ? experienceValues.reduce((sum, val) => sum + val, 0) / experienceValues.length
      : 0;

    const departmentCounts = employees.reduce<Record<string, number>>((acc, emp) => {
      const key = emp.department || 'Not Specified';
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    const roleCounts = employees.reduce<Record<string, number>>((acc, emp) => {
      const key = emp.role || 'Not Specified';
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    const topDepartments = Object.entries(departmentCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);
    const topRoles = Object.entries(roleCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);

    return {
      total,
      active,
      inactive,
      avgExp: avgExp.toFixed(1),
      topDepartments,
      topRoles,
    };
  }, [employees]);

  return (
    <div className="employee-analytics">
      <div className="analytics-header">
        <Button variant="ghost" onClick={onBack}>
          ← Back to Employee List
        </Button>
        <div>
          <p className="eyebrow">Workforce Intelligence</p>
          <h1>📊 Employee Analytics</h1>
        </div>
      </div>

      <div className="analytics-grid">
        <div className="analytics-card">
          <p className="label">Total Employees</p>
          <p className="value">{stats.total}</p>
        </div>
        <div className="analytics-card">
          <p className="label">Active Employees</p>
          <p className="value">{stats.active}</p>
        </div>
        <div className="analytics-card">
          <p className="label">Inactive Employees</p>
          <p className="value">{stats.inactive}</p>
        </div>
        <div className="analytics-card">
          <p className="label">Average Experience</p>
          <p className="value">{stats.avgExp} yrs</p>
        </div>
      </div>

      <div className="distribution-grid">
        <div className="distribution-card">
          <h3>Top Departments</h3>
          <ul>
            {stats.topDepartments.length ? (
              stats.topDepartments.map(([dept, count]) => (
                <li key={dept}>
                  <span>{dept}</span>
                  <strong>{count}</strong>
                </li>
              ))
            ) : (
              <p>No department data available.</p>
            )}
          </ul>
        </div>

        <div className="distribution-card">
          <h3>Role Distribution</h3>
          <ul>
            {stats.topRoles.length ? (
              stats.topRoles.map(([role, count]) => (
                <li key={role}>
                  <span>{role}</span>
                  <strong>{count}</strong>
                </li>
              ))
            ) : (
              <p>No role data available.</p>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default EmployeeAnalytics;

