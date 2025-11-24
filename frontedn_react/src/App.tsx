import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';
import Layout from './components/Common/Layout/Layout';
import Login from './components/Auth/Login';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import Home from './pages/Home';

// Role-based route components
import AdminRoutes from './pages/Admin/AdminRoutes';
import EmployeeRoutes from './pages/Employee/EmployeeRoutes';

function AppContent() {
  const { isAuthenticated, userRole } = useAuth();

  return (
    <div className="App">
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/home" element={<Home />} />
        
        {/* Protected admin routes */}
        <Route path="/admin/*" element={
          <ProtectedRoute requiredRole="superadmin">
            <Layout>
              <AdminRoutes />
            </Layout>
          </ProtectedRoute>
        } />
        
        {/* Protected employee routes */}
        <Route path="/employee/*" element={
          <ProtectedRoute requiredRole="employee">
            <Layout>
              <EmployeeRoutes />
            </Layout>
          </ProtectedRoute>
        } />
        
        {/* Catch all route */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <NotificationProvider>
          <AppContent />
        </NotificationProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;