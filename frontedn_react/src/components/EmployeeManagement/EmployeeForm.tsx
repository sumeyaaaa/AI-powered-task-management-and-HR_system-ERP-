import React, { useState, useEffect } from 'react';
import { Employee, EmployeeFormData } from '../../types';
import { employeeService } from '../../services/employee';
import './EmployeeForm.css';

const createInitialFormState = (): EmployeeFormData => ({
  name: '',
  email: '',
  role: '',
  department: '',
  title: '',
  location: '',
  experience_years: 0,
  bio: '',
  skills: [],
  strengths: [],
  area_of_development: '',
  linkedin_url: '',
  telegram_chat_id: '',
  is_active: true
});

interface EmployeeFormProps {
  employee?: Employee;
  onSave: () => void;
  onCancel: () => void;
  mode: 'create' | 'edit';
}

export const EmployeeForm: React.FC<EmployeeFormProps> = ({
  employee,
  onSave,
  onCancel,
  mode
}) => {
  const [formData, setFormData] = useState<EmployeeFormData>(() => createInitialFormState());
  const [password, setPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (employee && mode === 'edit') {
      setFormData({
        name: employee.name || '',
        email: employee.email || '',
        role: employee.role || '',
        department: employee.department || '',
        title: employee.title || '',
        location: employee.location || '',
        experience_years: employee.experience_years || 0,
        bio: employee.bio || '',
        skills: employee.skills || [],
        strengths: employee.strengths || [],
        area_of_development: employee.area_of_development || '',
        linkedin_url: employee.linkedin_url || '',
        telegram_chat_id: employee.telegram_chat_id || '',
        is_active: employee.is_active ?? true
      });
      setPassword('');
    } else if (mode === 'create') {
      setFormData(createInitialFormState());
      setPassword('');
    }
  }, [employee, mode]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: parseInt(value) || 0
    }));
  };

  const handleArrayChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    const arrayValue = value.split(',').map(item => item.trim()).filter(item => item !== '');
    setFormData(prev => ({
      ...prev,
      [name]: arrayValue
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (!formData.name || !formData.email || !formData.role) {
      setError('Please fill in all required fields (Name, Email, Role)');
      setLoading(false);
      return;
    }

    if (mode === 'create' && !password.trim()) {
      setError('Please provide a temporary password for the new employee.');
      setLoading(false);
      return;
    }

    try {
      if (mode === 'create') {
        await employeeService.createEmployee({
          ...formData,
          password: password.trim()
        });
      } else {
        await employeeService.updateEmployee({
          id: employee!.id,
          ...formData
        });
      }

      onSave();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Error ${mode === 'create' ? 'creating' : 'updating'} employee: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const getArrayDisplayValue = (array: string[]): string => {
    return array.join(', ');
  };

  return (
    <div className="employee-form-container">
      <h2>{mode === 'create' ? '➕ Add New Employee' : `✏️ Edit Employee: ${employee?.name}`}</h2>
      
      <form onSubmit={handleSubmit} className="employee-form">
        <div className="form-columns">
          <div className="form-column">
            <div className="form-group">
              <label htmlFor="name">Full Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="John Doe"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="email">Email Address *</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="john.doe@company.com"
                required
              />
            </div>

            {mode === 'create' && (
              <div className="form-group">
                <label htmlFor="password">Temporary Password *</label>
                <input
                  type="password"
                  id="password"
                  name="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Set a temporary password"
                  required
                />
              </div>
            )}

            <div className="form-group">
              <label htmlFor="role">Role *</label>
              <input
                type="text"
                id="role"
                name="role"
                value={formData.role}
                onChange={handleChange}
                placeholder="QA Engineer"
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
                placeholder="Engineering"
              />
            </div>

            <div className="form-group">
              <label htmlFor="title">Job Title</label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                placeholder="Senior QA Engineer"
              />
            </div>

            <div className="form-group">
              <label htmlFor="experience_years">Years of Experience</label>
              <input
                type="number"
                id="experience_years"
                name="experience_years"
                value={formData.experience_years}
                onChange={handleNumberChange}
                min="0"
                max="50"
              />
            </div>
          </div>

          <div className="form-column">
            <div className="form-group">
              <label htmlFor="location">Location</label>
              <input
                type="text"
                id="location"
                name="location"
                value={formData.location}
                onChange={handleChange}
                placeholder="City, Country"
              />
            </div>

            <div className="form-group">
              <label htmlFor="linkedin_url">LinkedIn URL</label>
              <input
                type="url"
                id="linkedin_url"
                name="linkedin_url"
                value={formData.linkedin_url}
                onChange={handleChange}
                placeholder="https://linkedin.com/in/username"
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
                placeholder="123456789"
              />
            </div>

            <div className="form-group">
              <label htmlFor="area_of_development">Area of Development</label>
              <input
                type="text"
                id="area_of_development"
                name="area_of_development"
                value={formData.area_of_development}
                onChange={handleChange}
                placeholder="Software Development, Marketing, etc."
              />
            </div>

            {mode === 'edit' && (
              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="is_active"
                    checked={formData.is_active}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      is_active: e.target.checked
                    }))}
                  />
                  Active Employee
                </label>
              </div>
            )}
          </div>
        </div>

        <div className="form-full-width">
          <div className="form-group">
            <label htmlFor="skills">Skills (comma-separated)</label>
            <textarea
              id="skills"
              name="skills"
              value={getArrayDisplayValue(formData.skills)}
              onChange={handleArrayChange}
              placeholder="Python, Testing, Automation, ..."
              rows={3}
            />
          </div>

          <div className="form-group">
            <label htmlFor="strengths">Strengths (comma-separated)</label>
            <textarea
              id="strengths"
              name="strengths"
              value={getArrayDisplayValue(formData.strengths)}
              onChange={handleArrayChange}
              placeholder="Leadership, Communication, Problem-solving, ..."
              rows={3}
            />
          </div>

          <div className="form-group">
            <label htmlFor="bio">Bio</label>
            <textarea
              id="bio"
              name="bio"
              value={formData.bio}
              onChange={handleChange}
              placeholder="Brief professional description..."
              rows={4}
            />
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="form-actions">
          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
          >
            {loading ? 'Saving...' : (mode === 'create' ? 'Create Employee' : 'Update Employee')}
          </button>
          
          <button
            type="button"
            className="btn-secondary"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default EmployeeForm;