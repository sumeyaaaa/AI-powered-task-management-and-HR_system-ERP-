export interface Notification {
    id: string;
    message: string;
    type: 'info' | 'success' | 'warning' | 'error' | 'task_assigned' | 'task_updated' | 'task_status_changed' | 'file_uploaded' | 'note_added' | 'progress_updated';
    is_read: boolean;
    meta?: {
      task_id?: string;
      task_description?: string;
      assigned_by?: string;
      added_by?: string;
      note_preview?: string;
      file_name?: string;
      attached_specifically?: boolean;
      attached_to?: string;
      attached_to_multiple?: string[];
      type?: string;
      user_role?: string;
      timestamp?: string;
      specially_attached?: boolean;
      is_note_notification?: boolean;
      is_attachment_notification?: boolean;
      is_task_owner_confirmation?: boolean;
      objective_number?: string;
    };
    created_at: string;
    read_at?: string;
  }
  
  export interface NotificationContextType {
    notifications: Notification[];
    unreadCount: number;
    isLoading: boolean;
    loadNotifications: () => Promise<void>;
    markAsRead: (notificationId: string) => Promise<void>;
    markAllAsRead: () => Promise<void>;
    deleteNotification: (notificationId: string) => Promise<void>;
    navigateToTask: (taskId: string) => void;
    getRelativeTime: (timestamp: string) => string;
  }
  
  export interface NotificationServiceResponse {
    success: boolean;
    notifications?: Notification[];
    unread_count?: number;
    error?: string;
  }