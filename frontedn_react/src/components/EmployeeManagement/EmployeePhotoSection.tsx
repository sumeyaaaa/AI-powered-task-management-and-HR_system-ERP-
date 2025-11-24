import React, { useState } from 'react';
import { Employee } from '../../types';
import { employeeService } from '../../services/employee';
import { Button } from '../Common/UI/Button';
import './EmployeePhotoSection.css';

interface EmployeePhotoSectionProps {
  employee: Employee;
  onBack: () => void;
  onUpdated?: () => void;
}

export const EmployeePhotoSection: React.FC<EmployeePhotoSectionProps> = ({
  employee,
  onBack,
  onUpdated,
}) => {
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) {
      setFile(null);
      setPreview(null);
      return;
    }

    if (selected.size > 5 * 1024 * 1024) {
      setError('File too large. Maximum size is 5MB.');
      return;
    }

    setFile(selected);
    setPreview(URL.createObjectURL(selected));
    setError('');
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const result = await employeeService.uploadEmployeePhoto(employee.id, file);
      if (!result.success) {
        setError(result.error || 'Failed to upload photo');
      } else {
        onUpdated?.();
        onBack();
      }
    } catch (err) {
      setError('Failed to upload photo');
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async () => {
    if (!window.confirm('Remove current photo?')) return;
    setLoading(true);
    try {
      const result = await employeeService.removeEmployeePhoto(employee.id);
      if (!result.success) {
        setError(result.error || 'Failed to remove photo');
      } else {
        onUpdated?.();
        onBack();
      }
    } catch (err) {
      setError('Failed to remove photo');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="employee-photo-manager">
      <div className="manager-header">
        <Button variant="ghost" onClick={onBack}>
          ← Back to Employee List
        </Button>
        <h1>📷 Manage Photo: {employee.name}</h1>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="photo-manager-content">
        <div className="current-photo">
          <h3>Current Photo</h3>
          <img
            src={preview || employee.photo_url || 'https://via.placeholder.com/200x200.png?text=No+Photo'}
            alt={employee.name}
          />
        </div>

        <div className="upload-section">
          <h3>Upload New Photo</h3>
          <input
            type="file"
            accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
            onChange={handleFileChange}
          />
          <p className="helper-text">Supported formats: PNG, JPG, JPEG, GIF, WebP (max 5MB)</p>

          <div className="photo-actions">
            <Button variant="primary" onClick={handleUpload} disabled={!file || loading}>
              {loading ? 'Uploading...' : 'Upload Photo'}
            </Button>
            {employee.photo_url && (
              <Button variant="secondary" onClick={handleRemove} disabled={loading}>
                Remove Photo
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmployeePhotoSection;

