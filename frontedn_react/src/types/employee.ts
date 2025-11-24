export interface Employee {
  id: string;
  name: string;
  email: string;
  role: string;
  department?: string;
  title?: string;
  location?: string;
  experience_years?: number;
  bio?: string;
  skills: string[];
  strengths: string[];
  area_of_development?: string;
  linkedin_url?: string;
  telegram_chat_id?: string;
  photo_url?: string;
  job_description_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmployeeFormData {
  name: string;
  email: string;
  role: string;
  department?: string;
  title?: string;
  location?: string;
  experience_years?: number;
  bio?: string;
  skills: string[];
  strengths: string[];
  area_of_development?: string;
  linkedin_url?: string;
  telegram_chat_id?: string;
  is_active: boolean;
}

export interface EmployeeCreateData extends EmployeeFormData {
  password: string;
}

export interface EmployeeUpdateData extends Partial<EmployeeFormData> {
  id: string;
}

export interface EmployeeFilter {
  search?: string;
  department?: string;
  role?: string;
  is_active?: boolean;
}

export interface PhotoUploadResponse {
  success: boolean;
  photo_url?: string;
  error?: string;
}