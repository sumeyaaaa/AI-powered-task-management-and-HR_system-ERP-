import { api } from './api';
import {
  Employee,
  EmployeeCreateData,
  EmployeeUpdateData,
  EmployeeFilter,
  PhotoUploadResponse,
} from '../types/employee';

const buildEmployeeListParams = (includeInactive: boolean, filters?: EmployeeFilter) => ({
  ...(includeInactive && { include_inactive: true }),
  ...filters,
});

export const employeeService = {
  async getAllEmployees(includeInactive = false, filters?: EmployeeFilter): Promise<Employee[]> {
    const response = await api.get<Employee[]>('/api/employees', {
      params: buildEmployeeListParams(includeInactive, filters),
    });
    return response.data;
  },

  async getEmployeeById(id: string): Promise<Employee> {
    const response = await api.get<Employee>(`/api/employees/${id}`);
    return response.data;
  },

  async createEmployee(payload: EmployeeCreateData): Promise<Employee> {
    const response = await api.post<Employee>('/api/employees', payload);
    return response.data;
  },

  async updateEmployee(payload: EmployeeUpdateData): Promise<Employee> {
    const { id, ...update } = payload;
    const response = await api.put<Employee>(`/api/employees/${id}`, update);
    return response.data;
  },

  async deleteEmployee(id: string): Promise<void> {
    await api.delete(`/api/employees/${id}`);
  },

  async permanentDeleteEmployee(id: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.delete(`/api/employees/${id}/permanent`);
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to delete employee permanently',
      };
    }
  },

  async toggleEmployeeStatus(id: string, is_active: boolean): Promise<Employee> {
    const response = await api.patch<Employee>(`/api/employees/${id}/status`, { is_active });
    return response.data;
  },

  async uploadEmployeePhoto(id: string, file: File): Promise<{ success: boolean; photo_url?: string; error?: string }> {
    const formData = new FormData();
    formData.append('photo', file);

    try {
      const response = await api.post<{ success: boolean; photo_url?: string; error?: string }>(
        `/api/employees/${id}/upload-photo`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
        }
      );
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to upload photo',
      };
    }
  },

  async removeEmployeePhoto(id: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.delete<{ success: boolean; error?: string }>(`/api/employees/${id}/remove-photo`);
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to remove photo',
      };
    }
  },

  async updateEmployeeJDLink(id: string, job_description_url: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.put<{ success: boolean; error?: string }>(`/api/employees/${id}/jd-link`, {
        job_description_url,
      });
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to update JD link',
      };
    }
  },

  async resetEmployeePassword(id: string): Promise<{ success: boolean; default_passwords?: string[]; error?: string }> {
    try {
      const response = await api.post<{ success: boolean; default_passwords?: string[]; error?: string }>(
        `/api/employees/${id}/reset-password`
      );
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to reset password',
      };
    }
  },

  async uploadPhoto(file: File): Promise<PhotoUploadResponse> {
    const formData = new FormData();
    formData.append('photo', file);

    const response = await api.post<PhotoUploadResponse>(
      '/api/employees/upload-photo',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );

    return response.data;
  },
};