import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import './SystemSetting.css';

export const SystemSetting: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'user' | 'security' | 'backup'>('user');

  if (user?.role !== 'superadmin') {
    return (
      <div className="system-settings">
        <div className="access-denied">
          <h2>🔐 Access Denied</h2>
          <p>System settings are only accessible to administrators.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="system-settings">
      <h1>⚙️ System Settings</h1>
      
      <div className="settings-info">
        <p>System configuration and administration tools</p>
      </div>

      <div className="settings-tabs">
        <div className="tab-headers">
          <button 
            className={`tab-header ${activeTab === 'user' ? 'active' : ''}`}
            onClick={() => setActiveTab('user')}
          >
            User Management
          </button>
          <button 
            className={`tab-header ${activeTab === 'security' ? 'active' : ''}`}
            onClick={() => setActiveTab('security')}
          >
            Security
          </button>
          <button 
            className={`tab-header ${activeTab === 'backup' ? 'active' : ''}`}
            onClick={() => setActiveTab('backup')}
          >
            Backup & Restore
          </button>
        </div>

        <div className="tab-content">
          {activeTab === 'user' && (
            <div className="tab-panel">
              <h3>User Management</h3>
              <p>Administrator tools for user management</p>
              <div className="setting-item">
                <label>User Registration</label>
                <select defaultValue="enabled">
                  <option value="enabled">Enabled</option>
                  <option value="disabled">Disabled</option>
                </select>
              </div>
              <div className="setting-item">
                <label>Default User Role</label>
                <select defaultValue="employee">
                  <option value="employee">Employee</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="tab-panel">
              <h3>Security Settings</h3>
              <p>System security configuration</p>
              <div className="setting-item">
                <label>Password Policy</label>
                <select defaultValue="medium">
                  <option value="low">Low (6+ characters)</option>
                  <option value="medium">Medium (8+ characters, letters & numbers)</option>
                  <option value="high">High (12+ characters, mixed case, numbers & symbols)</option>
                </select>
              </div>
              <div className="setting-item">
                <label>Session Timeout</label>
                <select defaultValue="60">
                  <option value="30">30 minutes</option>
                  <option value="60">60 minutes</option>
                  <option value="120">2 hours</option>
                  <option value="480">8 hours</option>
                </select>
              </div>
            </div>
          )}

          {activeTab === 'backup' && (
            <div className="tab-panel">
              <h3>Backup & Restore</h3>
              <p>Data backup and restoration tools</p>
              <div className="backup-actions">
                <button className="btn-primary">
                  🔄 Create Backup
                </button>
                <button className="btn-secondary">
                  📥 Restore from Backup
                </button>
                <button className="btn-secondary">
                  📊 Export Data
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SystemSetting;