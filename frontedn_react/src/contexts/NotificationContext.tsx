import React, { createContext, useState, useContext, useEffect, useCallback, ReactNode } from 'react';
import { Notification, NotificationContextType } from '../types/notifications';
import { notificationService } from '../services/notification';

// Export the context itself
export const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

// Fixed: Changed from useNotifications to useNotification to match your App.tsx
export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Check if user is authenticated before loading notifications
  const isAuthenticated = () => {
    try {
      const token = localStorage.getItem('token');
      return !!token;
    } catch {
      return false;
    }
  };

  const loadNotifications = useCallback(async () => {
    // Only load notifications if user is authenticated
    if (!isAuthenticated()) {
      setNotifications([]);
      setUnreadCount(0);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      const response = await notificationService.getNotifications();
      
      if (response.success && response.notifications) {
        // Map backend notification format to frontend format
        const mappedNotifications: Notification[] = response.notifications.map((notif: any) => ({
          id: notif.id,
          message: notif.message || 'No message',
          type: notif.meta?.type || 'info',
          is_read: notif.is_read || false,
          meta: {
            task_id: notif.meta?.task_id,
            task_description: notif.meta?.task_description,
            assigned_by: notif.meta?.assigned_by,
            added_by: notif.meta?.added_by,
            note_preview: notif.meta?.note_preview,
            file_name: notif.meta?.file_name,
            attached_specifically: notif.meta?.specially_attached,
            attached_to: notif.meta?.attached_to,
            attached_to_multiple: notif.meta?.attached_to_multiple,
          },
          created_at: notif.created_at,
          read_at: notif.read_at,
        }));
        
        setNotifications(mappedNotifications);
        setUnreadCount(response.unread_count || 0);
      } else {
        // Don't log errors if user is not authenticated
        if (isAuthenticated()) {
          console.error('Failed to load notifications:', response.error);
        }
        setNotifications([]);
        setUnreadCount(0);
      }
    } catch (error) {
      // Don't log errors if user is not authenticated
      if (isAuthenticated()) {
        console.error('Failed to load notifications:', error);
      }
      setNotifications([]);
      setUnreadCount(0);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Only set up polling if user is authenticated
    if (!isAuthenticated()) {
      setNotifications([]);
      setUnreadCount(0);
      setIsLoading(false);
      return;
    }

    // Load notifications immediately
    loadNotifications();
    
    // Set up polling for new notifications every 30 seconds
    const interval = setInterval(() => {
      if (isAuthenticated()) {
        loadNotifications();
      } else {
        setNotifications([]);
        setUnreadCount(0);
      }
    }, 30000);
    
    return () => clearInterval(interval);
  }, [loadNotifications]);

  const markAsRead = async (notificationId: string) => {
    try {
      const result = await notificationService.markAsRead(notificationId);
      
      if (result.success) {
        setNotifications(prev =>
          prev.map(notification =>
            notification.id === notificationId 
              ? { ...notification, is_read: true, read_at: new Date().toISOString() }
              : notification
          )
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
      } else {
        console.error('Failed to mark notification as read:', result.error);
      }
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      const result = await notificationService.markAllAsRead();
      
      if (result.success) {
        setNotifications(prev =>
          prev.map(notification => ({ 
            ...notification, 
            is_read: true,
            read_at: notification.read_at || new Date().toISOString()
          }))
        );
        setUnreadCount(0);
      } else {
        console.error('Failed to mark all notifications as read:', result.error);
      }
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error);
    }
  };

  const deleteNotification = async (notificationId: string) => {
    try {
      const result = await notificationService.deleteNotification(notificationId);
      
      if (result.success) {
        const notificationToDelete = notifications.find(n => n.id === notificationId);
        setNotifications(prev => prev.filter(notification => notification.id !== notificationId));
        
        // Update unread count if the deleted notification was unread
        if (notificationToDelete && !notificationToDelete.is_read) {
          setUnreadCount(prev => Math.max(0, prev - 1));
        }
      } else {
        console.error('Failed to delete notification:', result.error);
      }
    } catch (error) {
      console.error('Failed to delete notification:', error);
    }
  };

  const navigateToTask = (taskId: string) => {
    // Store task ID for navigation - this would be used by the task management component
    localStorage.setItem('current_task_id', taskId);
    // You can also use a state management solution or context to handle this navigation
    console.log(`Navigating to task: ${taskId}`);
  };

  const getRelativeTime = (timestamp: string): string => {
    const createdTime = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - createdTime.getTime();
    
    if (diff > 24 * 60 * 60 * 1000) {
      const days = Math.floor(diff / (24 * 60 * 60 * 1000));
      return `${days} day${days > 1 ? 's' : ''} ago`;
    } else if (diff > 60 * 60 * 1000) {
      const hours = Math.floor(diff / (60 * 60 * 1000));
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (diff > 60 * 1000) {
      const minutes = Math.floor(diff / (60 * 1000));
      return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else {
      return 'Just now';
    }
  };

  const value: NotificationContextType = {
    notifications,
    unreadCount,
    isLoading,
    loadNotifications,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    navigateToTask,
    getRelativeTime
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

// Export the context for direct usage if needed
export { NotificationContext as default };