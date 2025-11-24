import React from 'react';
import { Notification } from '../../types';

interface NotificationCardProps {
  notification: Notification;
  onMarkAsRead: (id: string) => void;
  onNavigateToTask?: (taskId: string) => void;
}

export const NotificationCard: React.FC<NotificationCardProps> = ({
  notification,
  onMarkAsRead,
  onNavigateToTask
}) => {
  const handleClick = () => {
    if (!notification.is_read) {
      onMarkAsRead(notification.id);
    }
    
    // Use meta.task_id instead of direct task_id property
    if (notification.meta?.task_id && onNavigateToTask) {
      onNavigateToTask(notification.meta.task_id);
    }
  };

  // Since priority doesn't exist in your Notification type, we'll derive it from type
  const getPriorityFromType = (type: Notification['type']): string => {
    switch (type) {
      case 'error': return 'high';
      case 'warning': return 'medium';
      case 'success': 
      case 'info': 
      default: return 'low';
    }
  };

  const getPriorityColor = (type: Notification['type']) => {
    const priority = getPriorityFromType(type);
    switch (priority) {
      case 'high': return '#ff4444';
      case 'medium': return '#ffaa00';
      case 'low': return '#00aa00';
      default: return '#666666';
    }
  };

  // Generate title from notification type and meta data
  const generateTitle = (notification: Notification): string => {
    const { type, meta } = notification;
    
    switch (type) {
      case 'task_assigned':
        return `Task Assigned: ${meta?.task_description || 'New Task'}`;
      case 'task_updated':
        return `Task Updated: ${meta?.task_description || 'Task'}`;
      case 'file_uploaded':
        return `File Uploaded: ${meta?.file_name || 'File'}`;
      case 'note_added':
        return `Note Added: ${meta?.note_preview ? meta.note_preview.substring(0, 30) + '...' : 'New Note'}`;
      case 'success':
        return 'Success';
      case 'warning':
        return 'Warning';
      case 'error':
        return 'Error';
      case 'info':
      default:
        return 'Notification';
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'task_assigned': return '📋';
      case 'task_updated': return '🔄';
      case 'file_uploaded': return '📎';
      case 'note_added': return '📝';
      case 'success': return '✅';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      case 'info':
      default: return 'ℹ️';
    }
  };

  const title = generateTitle(notification);
  const priority = getPriorityFromType(notification.type);
  const icon = getNotificationIcon(notification.type);

  return (
    <div 
      className={`notification-card ${notification.is_read ? 'read' : 'unread'}`}
      onClick={handleClick}
    >
      <div className="notification-header">
        <div className="notification-title">
          <span className="notification-icon">
            {icon}
          </span>
          <strong>{title}</strong>
        </div>
        <div className="notification-meta">
          <span 
            className="priority-badge"
            style={{ backgroundColor: getPriorityColor(notification.type) }}
          >
            {priority}
          </span>
          <span className="notification-time">
            {formatTime(notification.created_at)}
          </span>
        </div>
      </div>
      
      <div className="notification-body">
        <p>{notification.message}</p>
        
        {/* Show additional meta information if available */}
        {notification.meta?.assigned_by && (
          <p className="notification-meta-info">
            <small>Assigned by: {notification.meta.assigned_by}</small>
          </p>
        )}
        
        {notification.meta?.note_preview && (
          <p className="notification-meta-info">
            <small>Note: {notification.meta.note_preview}</small>
          </p>
        )}
        
        {notification.meta?.file_name && (
          <p className="notification-meta-info">
            <small>File: {notification.meta.file_name}</small>
          </p>
        )}
      </div>

      {notification.meta?.task_id && (
        <div className="notification-actions">
          <button 
            className="btn-link"
            onClick={(e) => {
              e.stopPropagation();
              onNavigateToTask?.(notification.meta!.task_id!);
            }}
          >
            🔍 View Task
          </button>
        </div>
      )}

      {!notification.is_read && (
        <div className="unread-indicator"></div>
      )}
    </div>
  );
};

export default NotificationCard;