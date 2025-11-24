import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/Common/UI/Button';
import { Card } from '../components/Common/UI/Card';
import './Home.css';

const Home: React.FC = () => {
  const { isAuthenticated, userRole } = useAuth();

  return (
    <div className="home-container">
      <div className="home-header">
        <div className="home-hero-image">
          <img
            src="/image/photo_2025-09-25_16-18-26.jpg"
            alt="LeanChem ERP"
          />
        </div>
        <h1>Welcome to LeanChem Task Management System</h1>
        <p className="home-subtitle">Unified Business Management Platform</p>
      </div>

      <div className="home-content">
        <Card className="features-card">
          <h2>Comprehensive Management Tools for Your Organization</h2>
          
          <div className="features-grid">
            <div className="feature-section">
              <h3>👥 For Administrators:</h3>
              <ul>
                <li>Complete employee management</li>
                <li>Business analytics and reporting</li>
                <li>System configuration</li>
              </ul>
            </div>

            <div className="feature-section">
              <h3>👤 For Employees:</h3>
              <ul>
                <li>Personal profile management</li>
                <li>Secure password management</li>
                <li>Access to company resources</li>
              </ul>
            </div>
          </div>

          <div className="getting-started">
            <h3> Getting Started:</h3>
            <p>Use the login button below to access your account.</p>
            
            {isAuthenticated ? (
              <div className="auth-buttons">
                <Link to={(userRole === 'superadmin' || userRole === 'admin') ? '/admin/dashboard' : '/employee/profile'}>
                  <Button variant="primary">
                    Go to Dashboard
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="auth-buttons">
                <Link to="/login">
                  <Button variant="primary" className="login-btn">
                    🔐 Login to System
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Home;