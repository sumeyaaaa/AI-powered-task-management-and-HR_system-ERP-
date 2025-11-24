import React, { useState } from 'react';
import { Employee } from '../../types';
import { employeeService } from '../../services/employee';
import { Button } from '../Common/UI/Button';
import './EmployeeJDSection.css';

interface EmployeeJDSectionProps {
  employee: Employee;
  onBack: () => void;
  onUpdated?: () => void;
}

export const EmployeeJDSection: React.FC<EmployeeJDSectionProps> = ({
  employee,
  onBack,
  onUpdated,
}) => {
  const [link, setLink] = useState(employee.job_description_url || '');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSave = async () => {
    if (!link) {
      setError('Please provide a Google Drive link.');
      return;
    }
    await persistLink(link);
  };

  const persistLink = async (value: string) => {
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const result = await employeeService.updateEmployeeJDLink(employee.id, value);
      if (!result.success) {
        setError(result.error || 'Failed to update JD link');
      } else {
        setMessage(value ? 'JD link saved successfully!' : 'JD link removed.');
        onUpdated?.();
      }
    } catch (err) {
      setError('Failed to update JD link');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = () => {
    if (!window.confirm('Remove the existing JD link?')) return;
    setLink('');
    persistLink('');
  };

  return (
    <div className="employee-jd-manager">
      <div className="manager-header">
        <Button variant="ghost" onClick={onBack}>
          ← Back to Employee List
        </Button>
        <h1>📄 Job Description Management: {employee.name}</h1>
      </div>

      {error && <div className="error-message">{error}</div>}
      {message && <div className="success-message">{message}</div>}

      <div className="jd-content">
        <div className="current-jd">
          <h3>Current JD Status</h3>
          {employee.job_description_url ? (
            <>
              <p>✅ JD Linked</p>
              <a href={employee.job_description_url} target="_blank" rel="noopener noreferrer">
                🔗 Open JD in Google Drive
              </a>
            </>
          ) : (
            <p>❌ No JD linked yet.</p>
          )}
        </div>

        <div className="jd-form">
          <label htmlFor="jd-link">Google Drive Shareable Link</label>
          <input
            id="jd-link"
            type="url"
            placeholder="https://drive.google.com/file/d/.../view?usp=sharing"
            value={link}
            onChange={(e) => setLink(e.target.value)}
          />
          <p className="helper-text">
            Ensure link sharing is set to &ldquo;Anyone with the link can view&rdquo;.
          </p>

          <div className="jd-actions">
            <Button variant="primary" onClick={handleSave} disabled={loading}>
              {loading ? 'Saving...' : '💾 Save JD Link'}
            </Button>
            {employee.job_description_url && (
              <Button variant="secondary" onClick={handleDelete} disabled={loading}>
                🗑️ Delete JD Link
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmployeeJDSection;

