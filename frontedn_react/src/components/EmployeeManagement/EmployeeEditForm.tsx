// components/EmployeeManagement/EmployeeEditForm.tsx
import React, { useState } from 'react';
import { Employee } from '../../types';
import { employeeService } from '../../services/employee';
import { Button } from '../Common/UI/Button';
import './EmployeeEditForm.css';

interface EmployeeEditFormProps {
  employee: Employee;
  onSave: () => void;
  onBack: () => void;
}

export const EmployeeEditForm: React.FC<EmployeeEditFormProps> = ({
  employee,
  onSave,
  onBack
}) => {
  const [formData, setFormData] = useState({
    name: employee.name || '',
    email: employee.email || '',
    role: employee.role || '',
    department: employee.department || '',
    title: employee.title || '',
    location: employee.location || '',
    experience_years: employee.experience_years || 0,
    linkedin_url: employee.linkedin_url || '',
    telegram_chat_id: employee.telegram_chat_id || '',
    area_of_development: employee.area_of_development || '',
    bio: employee.bio || '',
    skills: employee.skills ? employee.skills.join(', ') : '',
    strengths: employee.strengths ? employee.strengths.join(', ') : '',
    is_active: employee.is_active ?? true
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const updateData = {
        ...formData,
        skills: formData.skills.split(',').map(s => s.trim()).filter(s => s),
        strengths: formData.strengths.split(',').map(s => s.trim()).filter(s => s)
      };

      const result = await employeeService.updateEmployee({
        id: employee.id,
        ...updateData,
      });
      
      onSave();
    } catch (err) {
      setError('An error occurred while updating employee');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async () => {
    if (window.confirm('Are you sure you want to reset this employee\'s password?')) {
      try {
        const result = await employeeService.resetEmployeePassword(employee.id);
        if (result.success) {
          alert('Password reset successfully!');
        } else {
          alert(`Failed to reset password: ${result.error}`);
        }
      } catch (err) {
        alert('An error occurred while resetting password');
      }
    }
  };

  return (
    <div className="employee-edit-form">
      <div className="edit-header">
        <Button variant="ghost" onClick={onBack}>
          ← Back to Employee List
        </Button>
        <h1>✏️ Edit Employee: {employee.name}</h1>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="edit-form">
        <div className="form-section">
          <h3>Basic Information</h3>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="name">Full Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="email">Email *</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="role">Role *</label>
              <input
                type="text"
                id="role"
                name="role"
                value={formData.role}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="department">Department</label>
              <input
                type="text"
                id="department"
                name="department"
                value={formData.department}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="title">Title</label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="location">Location</label>
              <input
                type="text"
                id="location"
                name="location"
                value={formData.location}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="experience_years">Experience (years)</label>
              <input
                type="number"
                id="experience_years"
                name="experience_years"
                value={formData.experience_years}
                onChange={handleChange}
                min="0"
                max="50"
              />
            </div>
            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="is_active"
                  checked={formData.is_active}
                  onChange={handleChange}
                />
                Active Employee
              </label>
            </div>
          </div>
        </div>

        <div className="form-section">
          <h3>Contact Information</h3>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="linkedin_url">LinkedIn URL</label>
              <input
                type="url"
                id="linkedin_url"
                name="linkedin_url"
                value={formData.linkedin_url}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="telegram_chat_id">Telegram Chat ID</label>
              <input
                type="text"
                id="telegram_chat_id"
                name="telegram_chat_id"
                value={formData.telegram_chat_id}
                onChange={handleChange}
              />
            </div>
          </div>
        </div>

        <div className="form-section">
          <h3>Professional Information</h3>
          <div className="form-group">
            <label htmlFor="area_of_development">Area of Development</label>
            <input
              type="text"
              id="area_of_development"
              name="area_of_development"
              value={formData.area_of_development}
              onChange={handleChange}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="bio">Bio</label>
            <textarea
              id="bio"
              name="bio"
              value={formData.bio}
              onChange={handleChange}
              rows={4}
            />
          </div>

          <div className="form-group">
            <label htmlFor="skills">Skills (comma-separated)</label>
            <textarea
              id="skills"
              name="skills"
              value={formData.skills}
              onChange={handleChange}
              rows={3}
              placeholder="Python, Testing, Automation, ..."
            />
          </div>

          <div className="form-group">
            <label htmlFor="strengths">Strengths (comma-separated)</label>
            <textarea
              id="strengths"
              name="strengths"
              value={formData.strengths}
              onChange={handleChange}
              rows={3}
              placeholder="Leadership, Communication, Problem-solving, ..."
            />
          </div>
        </div>

        <div className="form-actions">
          <Button type="submit" variant="primary" disabled={loading}>
            {loading ? 'Updating...' : '💾 Update Employee'}
          </Button>
          <Button type="button" variant="secondary" onClick={onBack}>
            ❌ Cancel
          </Button>
        </div>
      </form>

      <div className="password-section">
        <h3>🔐 Password Management</h3>
        <p>Reset employee password to default (Admin only)</p>
        <Button variant="secondary" onClick={handleResetPassword}>
          🔄 Reset Password
        </Button>
      </div>
    </div>
  );
};