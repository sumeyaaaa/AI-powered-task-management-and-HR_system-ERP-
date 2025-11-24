import React, { useState } from 'react';
import { Employee } from '../../types';
import { Button } from '../Common/UI/Button';
import './EmployeeCard.css';

interface EmployeeCardProps {
  employee: Employee;
  onEdit: (employee: Employee) => void;
  onViewDetails: (employee: Employee) => void;
  onManagePhoto: (employee: Employee) => void;
  onManageJD: (employee: Employee) => void;
  onToggleStatus: (employee: Employee) => void;
  onDelete: (employee: Employee) => void;
  isAdmin?: boolean;
}

export const EmployeeCard: React.FC<EmployeeCardProps> = ({
  employee,
  onEdit,
  onViewDetails,
  onManagePhoto,
  onManageJD,
  onToggleStatus,
  onDelete,
  isAdmin = false
}) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleDeleteClick = () => {
    setShowDeleteConfirm(true);
  };

  const handleConfirmDelete = () => {
    onDelete(employee);
    setShowDeleteConfirm(false);
  };

  const handleCancelDelete = () => {
    setShowDeleteConfirm(false);
  };

  return (
    <div className={`employee-card ${!employee.is_active ? 'inactive' : ''}`}>
      <div className="employee-card-header">
        <div className="employee-avatar">
          {employee.photo_url ? (
            <img 
              src={employee.photo_url} 
              alt={employee.name}
              className="employee-photo"
            />
          ) : (
            <div className="employee-photo-placeholder">
              {employee.name.split(' ').map(n => n[0]).join('')}
            </div>
          )}
          <div className={`employee-status ${employee.is_active ? 'active' : 'inactive'}`}>
            {employee.is_active ? '🟢' : '🔴'}
          </div>
        </div>
        
        <div className="employee-basic-info">
          <h3 className="employee-name">{employee.name}</h3>
          <p className="employee-role">{employee.role}</p>
          <p className="employee-email">{employee.email}</p>
        </div>
      </div>

      <div className="employee-card-details">
        <div className="detail-row">
          <span className="detail-label">Department:</span>
          <span className="detail-value">{employee.department || 'N/A'}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Title:</span>
          <span className="detail-value">{employee.title || 'N/A'}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Experience:</span>
          <span className="detail-value">{employee.experience_years || 0} years</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">JD:</span>
          <span className="detail-value">
            {employee.job_description_url ? '📎 Attached' : '❌ Not attached'}
          </span>
        </div>
      </div>

      <div className="employee-card-actions">
        <div className="action-buttons">
          <Button 
            variant="secondary" 
            onClick={() => onViewDetails(employee)}
            className="action-btn"
          >
            📋 Details
          </Button>
          
          <Button 
            variant="secondary" 
            onClick={() => onEdit(employee)}
            className="action-btn"
          >
            ✏️ Edit
          </Button>
          
          <Button 
            variant="secondary" 
            onClick={() => onManagePhoto(employee)}
            className="action-btn"
          >
            📷 Photo
          </Button>
          
          <Button 
            variant="secondary" 
            onClick={() => onManageJD(employee)}
            className="action-btn"
          >
            📄 JD
          </Button>
          
          <Button 
            variant={employee.is_active ? "secondary" : "success"}
            onClick={() => onToggleStatus(employee)}
            className="action-btn"
          >
            {employee.is_active ? '🗑️ Deactivate' : '✅ Activate'}
          </Button>
          
          {isAdmin && (
            <Button 
              variant="danger" 
              onClick={handleDeleteClick}
              className="action-btn"
            >
              🔥 Delete
            </Button>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="delete-confirm-overlay">
          <div className="delete-confirm-modal">
            <h3>Confirm Permanent Delete</h3>
            <p>
              🚨 Are you sure you want to permanently delete <strong>{employee.name}</strong>? 
              This action cannot be undone!
            </p>
            <div className="delete-confirm-actions">
              <Button 
                variant="danger" 
                onClick={handleConfirmDelete}
              >
                ✅ Confirm Delete
              </Button>
              <Button 
                variant="secondary" 
                onClick={handleCancelDelete}
              >
                ❌ Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmployeeCard;