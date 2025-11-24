import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { Card } from '../Common/UI/Card';
import { Button } from '../Common/UI/Button';
import './Login.css';

const HERO_IMAGE = '/image/photo_2025-09-25_16-18-26.jpg';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    if (!email || !password) {
      setError('Please enter both email and password');
      setIsLoading(false);
      return;
    }

    const result = await login({ email, password });

    if (result.success) {
      const userRole = localStorage.getItem('userData') 
        ? JSON.parse(localStorage.getItem('userData')!).role 
        : 'employee';
      
      // Redirect based on role
      navigate(userRole === 'superadmin' ? '/admin/dashboard' : '/employee/profile');
    } else {
      setError(result.error || 'Login failed. Please try again.');
    }

    setIsLoading(false);
  };

  return (
    <div className="login-container">
      <div className="login-background">
        <div className="login-content">
          <Card className="login-card">
              <div className="login-header">
                <div className="login-hero-image">
                 <img src={HERO_IMAGE} alt="LeanChem" />
                </div>
              <h1>LeanChem Task Management System</h1>
              <p className="login-subtitle">Unified Business Management Platform</p>
            </div>

            <div className="login-form-section">
              <h2>🔐 System Login</h2>
              
              <div className="login-info">
                <p><strong>Login Credentials:</strong></p>
                <ul>
                  <li><strong>Admins:</strong> Use your admin credentials</li>
                  <li><strong>Employees:</strong> Use your company email and password</li>
                </ul>
              </div>

              <form onSubmit={handleSubmit} className="login-form">
                <div className="form-group">
                  <label htmlFor="email">📧 Email Address</label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your.email@company.com"
                    disabled={isLoading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="password">🔑 Password</label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    disabled={isLoading}
                    required
                  />
                </div>

                {error && (
                  <div className="error-message">
                    ❌ {error}
                  </div>
                )}

                <Button
                  type="submit"
                  disabled={isLoading}
                  className="login-button"
                >
                  {isLoading ? '🔄 Logging in...' : '🚀 Login to System'}
                </Button>
              </form>

              <div className="login-footer">
                <Link to="/" className="back-link">
                  ← Back to Home
                </Link>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Login;