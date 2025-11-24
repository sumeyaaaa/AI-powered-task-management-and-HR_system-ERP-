import React, { useEffect, useMemo, useState } from 'react';
import { Employee } from '../../types';
import { employeeService } from '../../services/employee';
import { EmployeeList } from '../../components/EmployeeManagement/EmployeeList';
import { Button } from '../../components/Common/UI/Button';
import { EmployeeDetailView } from '../../components/EmployeeManagement/EmployeeDetailView';
import { EmployeeEditForm } from '../../components/EmployeeManagement/EmployeeEditForm';
import { EmployeePhotoSection } from '../../components/EmployeeManagement/EmployeePhotoSection';
import { EmployeeJDSection } from '../../components/EmployeeManagement/EmployeeJDSection';
import { EmployeeAnalytics } from '../../components/EmployeeManagement/EmployeeAnalytics';
import { AddEmployeeForm } from '../../components/EmployeeManagement/AddEmployeeForm';
import './EmployeeManagement.css';

type ViewMode = 'list' | 'detail' | 'edit' | 'add' | 'photo' | 'jd' | 'analytics' | 'delete';

const EmployeeManagement: React.FC = () => {
  const [directory, setDirectory] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [currentView, setCurrentView] = useState<ViewMode>('list');
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
  const [deleteCandidate, setDeleteCandidate] = useState<Employee | null>(null);

  useEffect(() => {
    loadDirectory();
  }, []);

  const loadDirectory = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await employeeService.getAllEmployees(true);
      const normalized = Array.isArray(data)
        ? data
        : Array.isArray((data as any)?.employees)
          ? (data as any).employees
          : [];
      setDirectory(normalized);
    } catch (err) {
      setError('Unable to fetch employees. Please try again or check the backend service.');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = (employee: Employee) => {
    setSelectedEmployee(employee);
    setCurrentView('detail');
  };

  const handleEditEmployee = (employee: Employee) => {
    setSelectedEmployee(employee);
    setCurrentView('edit');
  };

  const handleManagePhoto = (employee: Employee) => {
    setSelectedEmployee(employee);
    setCurrentView('photo');
  };

  const handleManageJD = (employee: Employee) => {
    setSelectedEmployee(employee);
    setCurrentView('jd');
  };

  const handleDeleteEmployee = (employee: Employee) => {
    setDeleteCandidate(employee);
    setCurrentView('delete');
  };

  const handleBackToList = () => {
    setCurrentView('list');
    setSelectedEmployee(null);
    setDeleteCandidate(null);
  };

  const handleAddEmployee = () => {
    setCurrentView('add');
  };

  const handleViewAnalytics = () => {
    setCurrentView('analytics');
  };

  const stats = useMemo(() => {
    if (!directory.length) {
      return {
        total: 0,
        active: 0,
        inactive: 0,
        averageExperience: 0,
      };
    }

    const total = directory.length;
    const active = directory.filter(emp => emp.is_active).length;
    const inactive = total - active;
    const experienceSum = directory.reduce((sum, emp) => sum + (emp.experience_years || 0), 0);
    const averageExperience = experienceSum / total;

    return { total, active, inactive, averageExperience };
  }, [directory]);

  const topDepartments = useMemo(() => {
    const counts: Record<string, number> = {};
    directory.forEach(emp => {
      const dept = emp.department || 'Unassigned';
      counts[dept] = (counts[dept] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4);
  }, [directory]);

  const topRoles = useMemo(() => {
    const counts: Record<string, number> = {};
    directory.forEach(emp => {
      const role = emp.role || 'Unassigned';
      counts[role] = (counts[role] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4);
  }, [directory]);

  // Render different views based on currentView state
  const renderCurrentView = () => {
    switch (currentView) {
      case 'detail':
        return selectedEmployee && (
          <EmployeeDetailView 
            employee={selectedEmployee} 
            onBack={handleBackToList}
            onEdit={() => handleEditEmployee(selectedEmployee)}
          />
        );
      
      case 'edit':
        return selectedEmployee && (
          <EmployeeEditForm 
            employee={selectedEmployee}
            onSave={() => {
              loadDirectory();
              handleBackToList();
            }}
            onBack={handleBackToList}
          />
        );
      
      case 'add':
        return (
          <AddEmployeeForm 
            onSave={() => {
              loadDirectory();
              handleBackToList();
            }}
            onBack={handleBackToList}
          />
        );
      
      case 'photo':
        return selectedEmployee && (
          <EmployeePhotoSection 
            employee={selectedEmployee}
            onBack={handleBackToList}
            onUpdated={loadDirectory}
          />
        );
      
      case 'jd':
        return selectedEmployee && (
          <EmployeeJDSection 
            employee={selectedEmployee}
            onBack={handleBackToList}
            onUpdated={loadDirectory}
          />
        );
      
      case 'analytics':
        return (
          <EmployeeAnalytics 
            employees={directory}
            onBack={handleBackToList}
          />
        );
      
      case 'delete':
        return deleteCandidate && (
          <DeleteConfirmation 
            employee={deleteCandidate}
            onConfirm={async () => {
              const result = await employeeService.permanentDeleteEmployee(deleteCandidate.id);
              if (!result.success) {
                alert(result.error || 'Failed to permanently delete employee');
                return;
              }
              loadDirectory();
              handleBackToList();
            }}
            onCancel={handleBackToList}
          />
        );
      
      default:
        return renderListView();
    }
  };

  const renderListView = () => (
    <>
      <section className="employee-hero">
        <div>
          <p className="eyebrow">People Operations</p>
          <h1>Employee Management Command Center</h1>
          <p className="subtitle">
            Review talent metrics, manage profiles, and keep your organization's directory healthy —
            all in one collaborative workspace.
          </p>
        </div>
        <div className="hero-actions">
          <Button variant="ghost" size="small" onClick={loadDirectory} disabled={loading}>
            {loading ? 'Syncing…' : '⟳ Sync Directory'}
          </Button>
          <Button variant="primary" onClick={handleAddEmployee}>
            ➕ Add Team Member
          </Button>
          <Button variant="secondary" onClick={handleViewAnalytics}>
            📊 Analytics
          </Button>
        </div>
      </section>

      {error && (
        <div className="inline-error">
          <span>{error}</span>
          <Button variant="secondary" size="small" onClick={loadDirectory}>
            Retry
          </Button>
        </div>
      )}

      <section className="employee-workspace">
        <EmployeeList 
          employees={directory}
          loading={loading}
          onRefresh={loadDirectory}
          onViewDetail={handleViewDetail}
          onEditEmployee={handleEditEmployee}
          onManagePhoto={handleManagePhoto}
          onManageJD={handleManageJD}
          onDeleteEmployee={handleDeleteEmployee}
        />
      </section>
    </>
  );

  return (
    <div className="admin-employee-page">
      {renderCurrentView()}
    </div>
  );
};

// Delete Confirmation Component
const DeleteConfirmation: React.FC<{
  employee: Employee;
  onConfirm: () => void;
  onCancel: () => void;
}> = ({ employee, onConfirm, onCancel }) => {
  return (
    <div className="delete-confirmation">
      <div className="confirmation-content">
        <h2>🚨 Confirm Permanent Delete</h2>
        <p>Are you sure you want to permanently delete <strong>{employee.name}</strong>?</p>
        <p className="warning-text">This action cannot be undone!</p>
        
        <div className="confirmation-actions">
          <Button variant="danger" onClick={onConfirm}>
            ✅ Confirm Permanent Delete
          </Button>
          <Button variant="secondary" onClick={onCancel}>
            ❌ Cancel
          </Button>
        </div>
      </div>
    </div>
  );
};

export default EmployeeManagement;