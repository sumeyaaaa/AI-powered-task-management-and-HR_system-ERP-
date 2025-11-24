// components/EmployeeManagement/EmployeeDetailView.tsx
import React from 'react';
import { Employee } from '../../types';
import { Button } from '../Common/UI/Button';
import './EmployeeDetailView.css';

interface EmployeeDetailViewProps {
  employee: Employee;
  onBack: () => void;
  onEdit: () => void;
}

export const EmployeeDetailView: React.FC<EmployeeDetailViewProps> = ({
  employee,
  onBack,
  onEdit
}) => {
  return (
    <div className="employee-detail-view">
      <div className="detail-header">
        <Button variant="ghost" onClick={onBack}>
          ← Back to Employee List
        </Button>
        <h1>👤 Employee Details: {employee.name}</h1>
      </div>

      <div className="detail-content">
        <div className="detail-main">
          <div className="employee-photo-section">
            <img 
              src={employee.photo_url || "https://via.placeholder.com/200x200.png?text=No+Photo"} 
              alt={employee.name}
              className="employee-photo"
            />
          </div>

          <div className="employee-info">
            <div className="info-grid">
              <div className="info-item">
                <label>Email:</label>
                <span>{employee.email}</span>
              </div>
              <div className="info-item">
                <label>Role:</label>
                <span>{employee.role || 'N/A'}</span>
              </div>
              <div className="info-item">
                <label>Department:</label>
                <span>{employee.department || 'N/A'}</span>
              </div>
              <div className="info-item">
                <label>Title:</label>
                <span>{employee.title || 'N/A'}</span>
              </div>
              <div className="info-item">
                <label>Location:</label>
                <span>{employee.location || 'N/A'}</span>
              </div>
              <div className="info-item">
                <label>Experience:</label>
                <span>{employee.experience_years || 0} years</span>
              </div>
              <div className="info-item">
                <label>Status:</label>
                <span className={`status ${employee.is_active ? 'active' : 'inactive'}`}>
                  {employee.is_active ? '🟢 Active' : '🔴 Inactive'}
                </span>
              </div>
            </div>

            {employee.job_description_url && (
              <div className="jd-section">
                <h3>Job Description</h3>
                <p>✅ Linked to Google Drive</p>
                <a href={employee.job_description_url} target="_blank" rel="noopener noreferrer">
                  🔗 Open JD in Google Drive
                </a>
              </div>
            )}

            {employee.linkedin_url && (
              <div className="linkedin-section">
                <h3>LinkedIn</h3>
                <a href={employee.linkedin_url} target="_blank" rel="noopener noreferrer">
                  {employee.linkedin_url}
                </a>
              </div>
            )}
          </div>
        </div>

        <div className="detail-secondary">
          <div className="professional-info">
            <h3>Professional Information</h3>
            
            <div className="bio-section">
              <h4>Bio</h4>
              <p>{employee.bio || 'No bio provided.'}</p>
            </div>

            <div className="skills-section">
              <h4>Skills</h4>
              {employee.skills && employee.skills.length > 0 ? (
                <ul>
                  {employee.skills.map((skill, index) => (
                    <li key={index}>{skill}</li>
                  ))}
                </ul>
              ) : (
                <p>No skills listed.</p>
              )}
            </div>

            <div className="strengths-section">
              <h4>Strengths</h4>
              {employee.strengths && employee.strengths.length > 0 ? (
                <ul>
                  {employee.strengths.map((strength, index) => (
                    <li key={index}>{strength}</li>
                  ))}
                </ul>
              ) : (
                <p>No strengths listed.</p>
              )}
            </div>

            <div className="development-section">
              <h4>Area of Development</h4>
              <p>{employee.area_of_development || 'Not specified'}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="detail-footer">
        <div className="employment-details">
          <h3>Employment Details</h3>
          <div className="employment-grid">
            <div className="employment-item">
              <label>Employee ID:</label>
              <code>{employee.id}</code>
            </div>
            <div className="employment-item">
              <label>Employee Since:</label>
              <span>{employee.created_at ? new Date(employee.created_at).toLocaleDateString() : 'Unknown'}</span>
            </div>
            <div className="employment-item">
              <label>Last Updated:</label>
              <span>{employee.updated_at ? new Date(employee.updated_at).toLocaleDateString() : 'Unknown'}</span>
            </div>
          </div>
        </div>

        <div className="action-buttons">
          <Button variant="primary" onClick={onEdit}>
            ✏️ Edit Employee
          </Button>
          <Button variant="secondary" onClick={onBack}>
            ← Back to List
          </Button>
        </div>
      </div>
    </div>
  );
};