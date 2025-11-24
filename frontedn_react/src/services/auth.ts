import { api } from './api';
import { User, LoginCredentials, AuthContextType , AuthResponse} from '../types/auth';

export const authService = {
  async login(credentials: LoginCredentials): Promise<{ success: boolean; data?: AuthResponse; error?: string }> {
    try {
      console.log('Attempting login to:', '/api/auth/login'); // Debug log
      const response = await api.post<AuthResponse>('/api/auth/login', credentials);
      
      console.log('Login response:', response.data); // Debug log
      
      if (response.data && response.data.token) {
        return { success: true, data: response.data };
      } else {
        return { success: false, error: 'Invalid response from server' };
      }
    } catch (error: any) {
      console.error('Login service error:', error);
      
      if (error.response?.data?.error) {
        return { success: false, error: error.response.data.error };
      } else if (error.request) {
        return { success: false, error: 'Cannot connect to server. Make sure backend is running on port 5000.' };
      } else {
        return { success: false, error: 'Login failed' };
      }
    }
  },

  async logout(): Promise<{ success: boolean; error?: string }> {
    try {
      await api.post('/api/auth/logout');
      return { success: true };
    } catch (error) {
      console.error('Logout error:', error);
      return { success: false, error: 'Logout failed' };
    }
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.post('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      
      if (response.data.success) {
        return { success: true };
      } else {
        return { success: false, error: response.data.error || 'Password change failed' };
      }
    } catch (error: any) {
      console.error('Change password service error:', error);
      
      if (error.response?.data?.error) {
        return { success: false, error: error.response.data.error };
      } else {
        return { success: false, error: 'Failed to change password' };
      }
    }
  },

  async getProfile(): Promise<{ success: boolean; data?: User; error?: string }> {
    try {
      console.log('[AuthService] Fetching employee profile...');
      const response = await api.get<{ success: boolean; employee?: User; employees?: User[]; error?: string }>('/api/employee/profile');
      
      console.log('[AuthService] Profile response:', response.data);
      
      // Backend returns { success: true, employee: {...} } for employees
      // or { success: true, employees: [...] } for admins
      if (response.data.success) {
        // For employees, the data is in 'employee' field
        if (response.data.employee) {
          console.log('[AuthService] Found employee data:', response.data.employee);
          return { success: true, data: response.data.employee };
        }
        // For admins, it's in 'employees' array (but getProfile should return single employee)
        // This shouldn't happen for employee profile, but handle it gracefully
        if (response.data.employees && response.data.employees.length > 0) {
          console.log('[AuthService] Found employees array, using first employee');
          return { success: true, data: response.data.employees[0] };
        }
        console.error('[AuthService] No employee data found in response');
        return { success: false, error: 'No employee data found' };
      } else {
        console.error('[AuthService] Response indicates failure:', response.data.error);
        return { success: false, error: response.data.error || 'Failed to fetch profile' };
      }
    } catch (error: any) {
      console.error('[AuthService] Get profile service error:', error);
      if (error.response?.data?.error) {
        return { success: false, error: error.response.data.error };
      }
      return { success: false, error: 'Failed to fetch profile' };
    }
  },

  // Validate token on app start
  async validateToken(): Promise<boolean> {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        console.log('[AuthService] No token found');
        return false;
      }

      const response = await api.get<{ success: boolean; valid: boolean }>('/api/auth/validate-token');
      
      if (response.data.success && response.data.valid) {
        console.log('[AuthService] Token is valid');
        return true;
      } else {
        console.log('[AuthService] Token validation failed:', response.data);
        return false;
      }
    } catch (error: any) {
      console.error('[AuthService] Token validation error:', error);
      // If 401, token is invalid
      if (error.response?.status === 401) {
        return false;
      }
      // For other errors, assume token is invalid to be safe
      return false;
    }
  }
};