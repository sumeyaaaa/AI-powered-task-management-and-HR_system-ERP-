import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { employeeService } from '../../services/employee';
import { Button } from '../../components/Common/UI/Button';
import { Card } from '../../components/Common/UI/Card';
import './Profile.css';

interface EmployeeProfile {
  id: string;
  name: string;
  email: string;
  role: string;
  department?: string;
  title?: string;
  location?: string;
  experience_years?: number;
  photo_url?: string;
  bio?: string;
  skills?: string[];
  strengths?: string[];
  area_of_development?: string;
  job_description_url?: string;
  linkedin_url?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

const Profile: React.FC = () => {
  const { user, getProfile } = useAuth();
  const [profile, setProfile] = useState<EmployeeProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [removingPhoto, setRemovingPhoto] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setIsLoading(true);
      console.log('[Profile] Loading employee profile...');
      const profileData = await getProfile();
      console.log('[Profile] Received profile data:', profileData);
      if (profileData) {
        setProfile(profileData as EmployeeProfile);
        console.log('[Profile] Profile set successfully');
      } else {
        console.error('[Profile] Failed to load profile: No data returned');
        setProfile(null);
      }
    } catch (error) {
      console.error('[Profile] Failed to load profile:', error);
      setProfile(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePhotoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !profile) return;

    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      alert('Please select a valid image file (PNG, JPG, JPEG, GIF, WebP)');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      alert('File size must be less than 5MB');
      return;
    }

    setUploadingPhoto(true);
    try {
      const result = await employeeService.uploadEmployeePhoto(profile.id, file);
      if (result.success) {
        await loadProfile();
        alert('Photo uploaded successfully!');
      } else {
        alert(`Failed to upload photo: ${result.error}`);
      }
    } catch (error) {
      console.error('Photo upload error:', error);
      alert('Failed to upload photo');
    } finally {
      setUploadingPhoto(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemovePhoto = async () => {
    if (!profile) return;

    if (!window.confirm('Are you sure you want to remove your profile photo?')) {
      return;
    }

    setRemovingPhoto(true);
    try {
      const result = await employeeService.removeEmployeePhoto(profile.id);
      if (result.success) {
        await loadProfile();
        alert('Photo removed successfully!');
      } else {
        alert(`Failed to remove photo: ${result.error}`);
      }
    } catch (error) {
      console.error('Photo removal error:', error);
      alert('Failed to remove photo');
    } finally {
      setRemovingPhoto(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Not available';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (isLoading) {
    return (
      <div className="profile-page">
        <div className="profile-loading">
          <div className="loading-spinner">⏳</div>
          <p>Loading your profile...</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="profile-page">
        <div className="profile-error">
          <div className="error-icon">⚠️</div>
          <h3>Failed to Load Profile</h3>
          <p>Unable to load your profile information. Please try again.</p>
          <Button onClick={loadProfile}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      {/* Hero Section with Name, Photo, and Key Info */}
      <div className="profile-hero">
        <Card className="profile-hero-card">
          <div className="profile-hero-content">
            <div className="profile-photo-section">
              <div className="photo-wrapper">
                <img
                  src={profile.photo_url || 'https://via.placeholder.com/200x200.png?text=No+Photo'}
                  alt={profile.name}
                  className="profile-photo-large"
                />
                <div className="photo-overlay">
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handlePhotoUpload}
                      accept="image/png, image/jpeg, image/jpg, image/gif, image/webp"
                      style={{ display: 'none' }}
                    />
                  <button
                    className="photo-edit-btn"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploadingPhoto}
                    title="Change photo"
                    >
                    {uploadingPhoto ? '📤' : '📷'}
                  </button>
                    {profile.photo_url && (
                    <button
                      className="photo-remove-btn"
                        onClick={handleRemovePhoto}
                        disabled={removingPhoto}
                      title="Remove photo"
                    >
                      {removingPhoto ? '⏳' : '🗑️'}
                    </button>
                  )}
                </div>
              </div>
              <div className="status-badge">
                <span className={`status-indicator ${profile.is_active ? 'active' : 'inactive'}`}></span>
                <span>{profile.is_active ? 'Active' : 'Inactive'}</span>
              </div>
            </div>

            <div className="profile-hero-info">
              <div className="profile-name-section">
                <h1 className="profile-name">{profile.name}</h1>
                <div className="profile-title-role">
                  {profile.title && (
                    <span className="profile-title">{profile.title}</span>
                  )}
                  <span className="profile-role">{profile.role}</span>
                </div>
              </div>

              <div className="profile-contact-info">
                <div className="contact-item">
                  <span className="contact-icon">📧</span>
                  <div className="contact-details">
                    <span className="contact-label">Email</span>
                    <a href={`mailto:${profile.email}`} className="contact-value">
                      {profile.email}
                    </a>
                  </div>
                </div>

                {profile.department && (
                  <div className="contact-item">
                    <span className="contact-icon">🏢</span>
                    <div className="contact-details">
                      <span className="contact-label">Department</span>
                      <span className="contact-value">{profile.department}</span>
                    </div>
                    </div>
                )}

                {profile.location && (
                  <div className="contact-item">
                    <span className="contact-icon">📍</span>
                    <div className="contact-details">
                      <span className="contact-label">Location</span>
                      <span className="contact-value">{profile.location}</span>
                    </div>
                      </div>
                    )}

                {profile.experience_years !== undefined && (
                  <div className="contact-item">
                    <span className="contact-icon">💼</span>
                    <div className="contact-details">
                      <span className="contact-label">Experience</span>
                      <span className="contact-value">{profile.experience_years} years</span>
                    </div>
                  </div>
                )}
                </div>

              <div className="profile-actions">
                {profile.linkedin_url && (
                  <a
                    href={profile.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="social-link linkedin"
                  >
                    <span>🔗</span> LinkedIn
                  </a>
                )}
                {profile.job_description_url && (
                  <a
                    href={profile.job_description_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="social-link jd-link"
                  >
                    <span>📄</span> Job Description
                  </a>
                )}
              </div>
            </div>
          </div>
        </Card>
            </div>

      {/* Additional Information Cards */}
      <div className="profile-details-grid">
        {/* Bio Section */}
        {profile.bio && (
          <Card className="profile-detail-card">
            <div className="detail-card-header">
              <span className="detail-icon">📝</span>
              <h3>About Me</h3>
                  </div>
            <div className="detail-card-content">
              <p className="bio-text">{profile.bio}</p>
                </div>
          </Card>
        )}

        {/* Skills Section */}
        <Card className="profile-detail-card">
          <div className="detail-card-header">
            <span className="detail-icon">🛠️</span>
            <h3>Skills</h3>
          </div>
          <div className="detail-card-content">
                  {profile.skills && profile.skills.length > 0 ? (
              <div className="tags-container">
                      {profile.skills.map((skill, index) => (
                  <span key={index} className="skill-tag">
                    {skill}
                  </span>
                      ))}
              </div>
                  ) : (
              <p className="empty-state">No skills listed yet</p>
                  )}
                </div>
        </Card>

        {/* Strengths Section */}
        <Card className="profile-detail-card">
          <div className="detail-card-header">
            <span className="detail-icon">💪</span>
            <h3>Strengths</h3>
          </div>
          <div className="detail-card-content">
                  {profile.strengths && profile.strengths.length > 0 ? (
              <div className="tags-container">
                      {profile.strengths.map((strength, index) => (
                  <span key={index} className="strength-tag">
                    {strength}
                  </span>
                      ))}
              </div>
                  ) : (
              <p className="empty-state">No strengths listed yet</p>
                  )}
                </div>
        </Card>

        {/* Development Area */}
        {profile.area_of_development && (
          <Card className="profile-detail-card">
            <div className="detail-card-header">
              <span className="detail-icon">📈</span>
              <h3>Area of Development</h3>
                  </div>
            <div className="detail-card-content">
              <p className="development-text">{profile.area_of_development}</p>
            </div>
          </Card>
        )}

        {/* Employment Details */}
        <Card className="profile-detail-card">
          <div className="detail-card-header">
            <span className="detail-icon">📋</span>
              <h3>Employment Details</h3>
                  </div>
          <div className="detail-card-content">
            <div className="info-list">
              <div className="info-row">
                <span className="info-label">Employee ID</span>
                <code className="info-value-code">{profile.id}</code>
                  </div>
              <div className="info-row">
                <span className="info-label">Employee Since</span>
                <span className="info-value">{formatDate(profile.created_at)}</span>
                  </div>
              <div className="info-row">
                <span className="info-label">Last Updated</span>
                <span className="info-value">{formatDate(profile.updated_at)}</span>
              </div>
              </div>
            </div>
          </Card>
      </div>
    </div>
  );
};

export default Profile;
