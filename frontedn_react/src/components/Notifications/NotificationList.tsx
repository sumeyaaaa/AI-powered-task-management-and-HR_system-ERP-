import React from 'react';
import { Notification } from '../../types';
import { NotificationCard } from './NotificationCard';
import './NotificationList.css';

interface NotificationListProps {
  notifications: Notification[];
  onMarkAsRead: (id: string) => void;
  onNavigateToTask: (taskId: string) => void;
  onMarkAllAsRead: () => void;
  onClearAll: () => void;
}

export const NotificationList: React.FC<NotificationListProps> = ({
  notifications,
  onMarkAsRead,
  onNavigateToTask,
  onMarkAllAsRead,
  onClearAll
}) => {
  const unreadCount = notifications.filter(n => !n.is_read).length;
  const hasNotifications = notifications.length > 0;

  const groupedNotifications = notifications.reduce((groups, notification) => {
    const date = new Date(notification.created_at).toDateString();
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(notification);
    return groups;
  }, {} as Record<string, Notification[]>);

  return (
    <div className="notification-list">
      <div className="notification-list-header">
        <h3>🔔 Notifications</h3>
        <div className="notification-stats">
          {unreadCount > 0 && (
            <span className="unread-count">{unreadCount} unread</span>
          )}
        </div>
      </div>

      {hasNotifications && (
        <div className="notification-actions-bar">
          <button 
            className="btn-secondary btn-sm"
            onClick={onMarkAllAsRead}
            disabled={unreadCount === 0}
          >
            Mark all as read
          </button>
          <button 
            className="btn-secondary btn-sm"
            onClick={onClearAll}
          >
            Clear all
          </button>
        </div>
      )}

      <div className="notification-list-content">
        {!hasNotifications ? (
          <div className="no-notifications">
            <p>No notifications yet</p>
            <span>You're all caught up!</span>
          </div>
        ) : (
          Object.entries(groupedNotifications).map(([date, dayNotifications]) => (
            <div key={date} className="notification-day-group">
              <h4 className="day-header">
                {new Date(date).toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </h4>
              
              <div className="day-notifications">
                {dayNotifications.map(notification => (
                  <NotificationCard
                    key={notification.id}
                    notification={notification}
                    onMarkAsRead={onMarkAsRead}
                    onNavigateToTask={onNavigateToTask}
                  />
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default NotificationList;