import React, { useMemo, useState } from 'react';
import { Employee } from '../../types';
import { employeeService } from '../../services/employee';
import './EmployeeList.css';

interface EmployeeListProps {
  employees: Employee[];
  loading?: boolean;
  onRefresh: () => void;
  onViewDetail: (employee: Employee) => void;
  onEditEmployee: (employee: Employee) => void;
  onManagePhoto: (employee: Employee) => void;
  onManageJD: (employee: Employee) => void;
  onDeleteEmployee: (employee: Employee) => void;
}

export const EmployeeList: React.FC<EmployeeListProps> = ({
  employees,
  loading = false,
  onRefresh,
  onViewDetail,
  onEditEmployee,
  onManagePhoto,
  onManageJD,
  onDeleteEmployee
}) => {
  const [showInactive, setShowInactive] = useState(true);
  const filteredEmployees = useMemo(
    () => (showInactive ? employees : employees.filter(emp => emp.is_active)),
    [employees, showInactive]
  );

  const handleToggleActivation = async (employee: Employee, activate: boolean) => {
    try {
      await employeeService.toggleEmployeeStatus(employee.id, activate);
      onRefresh();
    } catch (err) {
      console.error('Failed to update status', err);
    }
  };

  if (loading) {
    return <div className="loading">Loading employees...</div>;
  }

  return (
    <div className="employee-list-container">
      <div className="employee-list-header">
        <h2>👥 Employee Directory</h2>

        <div className="employee-list-controls">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            Show Inactive Employees
          </label>
        </div>
      </div>

      <div className="employee-stats">
        <div className="stat-card">
          <h3>Total Employees</h3>
          <p className="stat-number">{employees.length}</p>
        </div>

        <div className="stat-card">
          <h3>Active Employees</h3>
          <p className="stat-number">
            {employees.filter(emp => emp.is_active).length}
          </p>
        </div>

        <div className="stat-card">
          <h3>Inactive Employees</h3>
          <p className="stat-number">
            {employees.filter(emp => !emp.is_active).length}
          </p>
        </div>

        <div className="stat-card">
          <h3>Avg Experience</h3>
          <p className="stat-number">
            {employees.length > 0
              ? (employees.reduce((sum, emp) => sum + (emp.experience_years || 0), 0) / employees.length).toFixed(1)
              : '0'
            } years
          </p>
        </div>
      </div>

      <div className="employee-grid">
        {filteredEmployees.length === 0 ? (
          <div className="no-employees">
            <p>No employees found.</p>
          </div>
        ) : (
          filteredEmployees.map(employee => (
            <div key={employee.id} className="employee-item">
              <div className="employee-avatar">
                {employee.photo_url ? (
                  <img src={employee.photo_url} alt={employee.name} />
                ) : (
                  <div className="avatar-placeholder">
                    {employee.name.charAt(0).toUpperCase()}
                  </div>
                )}
                <div className={`status-indicator ${employee.is_active ? 'active' : 'inactive'}`}>
                  {employee.is_active ? '🟢' : '🔴'}
                </div>
              </div>

              <div className="employee-info">
                <h3>{employee.name}</h3>
                <p className="employee-role">{employee.role}</p>
                <p className="employee-department">{employee.department || 'No department'}</p>
                <p className="employee-email">{employee.email}</p>

                {employee.job_description_url && (
                  <div className="jd-indicator" title="Job Description Available">
                    📎
                  </div>
                )}
              </div>

              <div className="employee-actions">
                <button
                  onClick={() => onViewDetail(employee)}
                  className="btn-action"
                  title="View Details"
                >
                  👁️
                </button>

                <button
                  onClick={() => onEditEmployee(employee)}
                  className="btn-action"
                  title="Edit"
                >
                  ✏️
                </button>

                <button
                  onClick={() => onManagePhoto(employee)}
                  className="btn-action"
                  title="Manage Photo"
                >
                  📷
                </button>

                <button
                  onClick={() => onManageJD(employee)}
                  className="btn-action"
                  title="Manage Job Description"
                >
                  📄
                </button>

                {employee.is_active ? (
                  <button
                    onClick={() => handleToggleActivation(employee, false)}
                    className="btn-action danger"
                    title="Deactivate"
                  >
                    🗑️
                  </button>
                ) : (
                  <button
                    onClick={() => handleToggleActivation(employee, true)}
                    className="btn-action success"
                    title="Activate"
                  >
                    ✅
                  </button>
                )}

                <button
                  onClick={() => onDeleteEmployee(employee)}
                  className="btn-action danger"
                  title="Delete"
                >
                  🔥
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default EmployeeList;