import React from 'react';
import { User } from '../../../types/auth';
import { Button } from '../UI/Button';
import NotificationBell from '../../Notifications/NotificationBell';
import './Header.css';

const LOGO_IMAGE = '/image/photo_2025-09-25_16-18-26.jpg';

interface HeaderProps {
  user: User | null;
  onToggleSidebar: () => void;
  onLogout: () => void;
}

const Header: React.FC<HeaderProps> = ({ 
  user, 
  onToggleSidebar, 
  onLogout 
}) => {
  return (
    <header className="header">
      <div className="header-left">
        <button 
          className="sidebar-toggle"
          onClick={onToggleSidebar}
          aria-label="Toggle sidebar"
        >
          ☰
        </button>
        <div className="header-logo">
          <img src={LOGO_IMAGE} alt="LeanChem" />
          <h1>LeanChem Task Management System</h1>
        </div>
      </div>

      <div className="header-right">
        <div className="header-actions">
          <NotificationBell /> {/* Remove unreadCount prop */}
          
          <div className="user-info">
            <span className="welcome-text">
              👋 Welcome, <strong>{user?.name || 'User'}</strong>
            </span>
            <span className="user-role">
              Role: {user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : 'Employee'}
            </span>
          </div>
          
          <Button 
            variant="secondary" 
            onClick={onLogout}
            className="logout-btn"
          >
            🚪 Logout
          </Button>
        </div>
      </div>
    </header>
  );
};

export default Header;