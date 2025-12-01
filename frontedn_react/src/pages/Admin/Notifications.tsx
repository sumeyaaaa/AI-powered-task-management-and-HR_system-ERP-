import React, { useEffect, useState } from 'react';
import { useNotification } from '../../contexts/NotificationContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/Common/UI/Button';
import { Card } from '../../components/Common/UI/Card';
import { Notification } from '../../types/notifications';
import './Notifications.css';

const Notifications: React.FC = () => {
  const {
    notifications,
    unreadCount,
    isLoading,
    loadNotifications,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    navigateToTask,
    getRelativeTime
  } = useNotification();
  const navigate = useNavigate();
  const [selectedNotification, setSelectedNotification] = useState<Notification | null>(null);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const isTaskOwnerConfirmation = (notification: Notification) =>
    Boolean(notification.meta?.is_task_owner_confirmation);

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      markAsRead(notification.id);
    }
    
    if (notification.meta?.task_id) {
      const taskId = notification.meta.task_id;
      navigateToTask(taskId);
      localStorage.setItem('current_task_id', taskId);
      navigate(`/admin/task-management/${taskId}`);
    }
    
    setSelectedNotification(notification);
  };

  const handleMarkAllAsRead = async () => {
    await markAllAsRead();
  };

  const handleDelete = async (notificationId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteNotification(notificationId);
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'file_uploaded':
        return '📎';
      case 'note_added':
        return '📝';
      case 'task_status_changed':
        return '🔄';
      case 'progress_updated':
        return '📊';
      case 'task_assigned':
        return '📋';
      case 'task_updated':
        return '✏️';
      default:
        return '🔔';
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'file_uploaded':
        return 'file';
      case 'note_added':
        return 'note';
      case 'task_status_changed':
        return 'status';
      case 'progress_updated':
        return 'progress';
      case 'task_assigned':
        return 'assigned';
      default:
        return 'default';
    }
  };

  if (isLoading) {
    return (
      <div className="notifications-page">
        <div className="loading">Loading notifications...</div>
      </div>
    );
  }

  return (
    <div className="notifications-page">
      <div className="notifications-header">
    <div>
          <h1>🔔 Notifications</h1>
          {unreadCount > 0 ? (
            <p className="unread-message">You have {unreadCount} unread notification(s)</p>
          ) : (
            <p className="all-caught-up">All caught up! 🎉</p>
          )}
        </div>
        <div className="header-actions">
          {unreadCount > 0 && (
            <Button variant="primary" onClick={handleMarkAllAsRead}>
              📭 Mark All Read
            </Button>
          )}
          <Button variant="ghost" onClick={loadNotifications}>
            🔄 Refresh
            </Button>
        </div>
      </div>

      {notifications.length === 0 ? (
        <Card className="no-notifications-card">
          <div className="no-notifications">
            <h3>No notifications found</h3>
            <p>You're all caught up! No new notifications at this time.</p>
          </div>
        </Card>
      ) : (
        <div className="notifications-list">
          {notifications.map(notification => (
            <div
              key={notification.id}
              className={`notification-card ${notification.is_read ? 'read' : 'unread'} ${getNotificationColor(notification.type)}`}
              onClick={() => handleNotificationClick(notification)}
            >
              <div className="notification-content">
                <div className="notification-icon">
                  {getNotificationIcon(notification.type)}
                </div>
                <div className="notification-main">
                  <div className="notification-message">
                    <p className="message-text">{notification.message}</p>
                    {!notification.is_read && <span className="unread-dot"></span>}
                  </div>
                  
                  {notification.meta?.task_description && (
                    <p className="task-description">
                      Task: {notification.meta.task_description}
                    </p>
                  )}
                  
                  {notification.meta?.note_preview && (
                    <p className="note-preview">
                      Note: {notification.meta.note_preview}
                    </p>
                  )}
                  
                  {notification.meta?.added_by && (
                    <p className="added-by">
                      Added by: {notification.meta.added_by}
                    </p>
                  )}
                  
                  {notification.meta?.assigned_by && (
                    <p className="assigned-by">
                      Assigned by: {notification.meta.assigned_by}
                    </p>
                  )}
                  
                  <div className="notification-footer">
                    <span className="notification-time">
                      {getRelativeTime(notification.created_at)}
                    </span>
                    {notification.meta?.task_id && (
                      <Button
                        variant={isTaskOwnerConfirmation(notification) ? "primary" : "ghost"}
                        size="small"
                        onClick={() => {
                          handleNotificationClick(notification);
                        }}
                      >
                        {isTaskOwnerConfirmation(notification) ? "Go to Task →" : "View Task →"}
                      </Button>
                    )}
                  </div>
                </div>
                <div className="notification-actions">
                  {!notification.is_read && (
                    <Button
                      variant="ghost"
                      size="small"
                      onClick={() => {
                        markAsRead(notification.id);
                      }}
                    >
                      ✓ Read
                    </Button>
                  )}
                  <button
                    className="delete-btn"
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      handleDelete(notification.id, e);
                    }}
                    title="Delete notification"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedNotification && (
        <div className="notification-detail-modal" onClick={() => setSelectedNotification(null)}>
          <div className="modal-card" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Notification Details</h3>
              <button onClick={() => setSelectedNotification(null)}>×</button>
            </div>
            <div className="modal-content">
              <p><strong>Message:</strong> {selectedNotification.message}</p>
              <p><strong>Type:</strong> {selectedNotification.type}</p>
              <p><strong>Created:</strong> {new Date(selectedNotification.created_at).toLocaleString()}</p>
              {selectedNotification.meta?.task_id && (
                <p><strong>Task ID:</strong> {selectedNotification.meta.task_id}</p>
              )}
              {selectedNotification.meta?.task_description && (
                <p><strong>Task:</strong> {selectedNotification.meta.task_description}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Notifications;
