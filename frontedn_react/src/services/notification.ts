import { api } from './api';
import { Notification, NotificationServiceResponse } from '../types/notifications';

class NotificationService {
  private baseUrl = '/api/notifications';

  async getNotifications(): Promise<NotificationServiceResponse> {
    try {
      // Check if user is authenticated before making the request
      const token = localStorage.getItem('token');
      if (!token) {
        return {
          success: false,
          error: 'Not authenticated',
          notifications: [],
          unread_count: 0
        };
      }

      const response = await api.get<{
        success: boolean;
        notifications?: Notification[];
        unread_count?: number;
        total?: number;
        error?: string;
      }>(this.baseUrl);
      
      if (response.data?.success === false) {
        return {
          success: false,
          error: response.data.error || 'Failed to fetch notifications'
        };
      }

      return {
        success: true,
        notifications: response.data.notifications || [],
        unread_count: response.data.unread_count || 0
      };
    } catch (error: any) {
      // Don't log errors if user is not authenticated (401 errors are expected)
      if (error.response?.status !== 401) {
        console.error('Error fetching notifications:', error);
      }
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to fetch notifications'
      };
    }
  }

  async getNotificationCount(): Promise<{ success: boolean; unread_count?: number; error?: string }> {
    try {
      const response = await api.get<{
        success: boolean;
        unread_count?: number;
        error?: string;
      }>(`${this.baseUrl}/count`);
      
      return {
        success: response.data?.success ?? false,
        unread_count: response.data?.unread_count ?? 0,
        error: response.data?.error
      };
    } catch (error: any) {
      console.error('Error fetching notification count:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to fetch notification count'
      };
    }
  }

  async markAsRead(notificationId: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.put(`${this.baseUrl}/${notificationId}/read`);
      return response.data;
    } catch (error: any) {
      console.error('Error marking notification as read:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to mark notification as read'
      };
    }
  }

  async markAllAsRead(): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.put(`${this.baseUrl}/read-all`);
      return response.data;
    } catch (error: any) {
      console.error('Error marking all notifications as read:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to mark all notifications as read'
      };
    }
  }

  async deleteNotification(notificationId: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.delete(`${this.baseUrl}/${notificationId}`);
      return response.data;
    } catch (error: any) {
      console.error('Error deleting notification:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to delete notification'
      };
    }
  }
}

export const notificationService = new NotificationService();

