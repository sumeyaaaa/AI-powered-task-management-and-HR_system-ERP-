export interface User {
    id: string;
    email: string;
    name: string;
    role: 'superadmin' | 'employee';
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
  
  export interface LoginCredentials {
    email: string;
    password: string;
  }
  
  export interface AuthResponse {
    token: string;
    user: User;
    message?: string;
  }
  
  export interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    userRole: string;
    login: (credentials: LoginCredentials) => Promise<{ success: boolean; error?: string }>;
    logout: () => void;
    changePassword: (currentPassword: string, newPassword: string) => Promise<{ success: boolean; error?: string }>;
    getProfile: () => Promise<User | null>;
    isAdmin: () => boolean;
  }
  
  export interface ChangePasswordData {
    current_password: string;
    new_password: string;
  }
  
  export interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
  }