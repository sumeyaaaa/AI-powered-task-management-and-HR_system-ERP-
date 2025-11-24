import React, { createContext, useState, useContext, useEffect, type ReactNode } from 'react';
import { authService } from '../services/auth';
import type { User, LoginCredentials, AuthContextType } from '../types/auth';

// Export the context itself
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [userRole, setUserRole] = useState<string>('');

  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      const token = localStorage.getItem('token');
      const userData = localStorage.getItem('userData');
      
      if (token && userData) {
        // Validate token with backend before setting authenticated state
        try {
          const isValid = await authService.validateToken();
          if (isValid) {
            const parsedUser = JSON.parse(userData);
            setUser(parsedUser);
            setIsAuthenticated(true);
            setUserRole(parsedUser.role);
          } else {
            // Token is invalid, clear storage
            localStorage.removeItem('token');
            localStorage.removeItem('userData');
            setUser(null);
            setIsAuthenticated(false);
            setUserRole('');
          }
        } catch (error) {
          // Token validation failed, clear storage
          console.error('Token validation failed:', error);
          localStorage.removeItem('token');
          localStorage.removeItem('userData');
          setUser(null);
          setIsAuthenticated(false);
          setUserRole('');
        }
      } else {
        // No token or userData, ensure clean state
        setUser(null);
        setIsAuthenticated(false);
        setUserRole('');
      }
    } catch (error) {
      console.error('Auth initialization error:', error);
      localStorage.removeItem('token');
      localStorage.removeItem('userData');
      setUser(null);
      setIsAuthenticated(false);
      setUserRole('');
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (credentials: LoginCredentials): Promise<{ success: boolean; error?: string }> => {
    try {
      setIsLoading(true);
      const result = await authService.login(credentials);
      
      if (result.success && result.data) {
        const { token, user: userData } = result.data;
        
        localStorage.setItem('token', token);
        localStorage.setItem('userData', JSON.stringify(userData));
        
        setUser(userData);
        setIsAuthenticated(true);
        setUserRole(userData.role);
        
        return { success: true };
      } else {
        return { success: false, error: result.error || 'Login failed' };
      }
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: 'An error occurred during login' };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userData');
    setUser(null);
    setIsAuthenticated(false);
    setUserRole('');
    authService.logout().catch(console.error);
  };

  const changePassword = async (currentPassword: string, newPassword: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const result = await authService.changePassword(currentPassword, newPassword);
      return result;
    } catch (error) {
      console.error('Change password error:', error);
      return { success: false, error: 'Failed to change password' };
    }
  };

  const getProfile = async () => {
    try {
      const result = await authService.getProfile();
      if (result.success && result.data) {
        return result.data;
      }
      return null;
    } catch (error) {
      console.error('Get profile error:', error);
      return null;
    }
  };

  const isAdmin = (): boolean => {
    return userRole === 'superadmin';
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    userRole,
    login,
    logout,
    changePassword,
    getProfile,
    isAdmin,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Export the context for direct usage if needed
export { AuthContext as default };