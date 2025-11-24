import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Button } from '../UI/Button';
import './Sidebar.css';

interface SidebarProps {
  isAdmin: boolean;
  collapsed: boolean;
  onLogout: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isAdmin, collapsed, onLogout }) => {
  const location = useLocation();

  const adminNavigation = [
    { path: '/admin/dashboard', label: ' Dashboard', icon: '📊' },
    { path: '/admin/employee-management', label: ' Employee Management', icon: '👥' },
    { path: '/admin/task-management', label: 'Task Management', icon: '🎯' },
    { path: '/admin/notifications', label: ' Notifications', icon: '🔔' },
  ];

  const employeeNavigation = [
    { path: '/employee/profile', label: ' My Profile', icon: '👤' },
    { path: '/employee/task-management', label: ' Task Management', icon: '📋' },
    { path: '/employee/notifications', label: ' Notifications', icon: '🔔' },
    { path: '/employee/change-password', label: ' Change Password', icon: '🔐' },
  ];

  const navigation = isAdmin ? adminNavigation : employeeNavigation;

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-content">
        <div className="sidebar-logo">
          {!collapsed && <h2>Navigation</h2>}
        </div>

        <nav className="sidebar-nav">
          <ul>
            {navigation.map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`nav-link ${isActive(item.path) ? 'active' : ''}`}
                  title={collapsed ? item.label : ''}
                >
                  <span className="nav-icon">{item.icon}</span>
                  {!collapsed && <span className="nav-label">{item.label}</span>}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <Button
            variant="secondary"
            onClick={onLogout}
            className="sidebar-logout-btn"
            fullWidth
          >
            <span className="logout-icon">🚪</span>
            {!collapsed && <span>Logout</span>}
          </Button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;