import React, { useState } from 'react';
import { useAuth } from '../../../contexts/AuthContext';
import Header from './Header';
import Sidebar from './Sidebar';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, logout, isAdmin } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="layout">
      <Header 
        user={user}
        onToggleSidebar={toggleSidebar}
        onLogout={handleLogout}
      />
      
      <div className="layout-body">
        <Sidebar 
          isAdmin={isAdmin()}
          collapsed={sidebarCollapsed}
          onLogout={handleLogout}
        />
        
        <main className={`layout-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
          <div className="content-wrapper">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;