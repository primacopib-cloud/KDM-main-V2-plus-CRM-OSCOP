import i18n from '@/i18n';
import React, { useState, useEffect, useCallback } from 'react';
import { Bell, X, Check, CheckCheck, FileText, User, Building2, Wallet, AlertTriangle } from 'lucide-react';
import { notificationsAPI } from '../services/api';

const POLL_INTERVAL = 30000; // 30 seconds

const NotificationIcon = ({ type }) => {
  switch (type) {
    case 'new_quote':
      return <FileText className="w-4 h-4 text-[#D9B35A]" />;
    case 'new_user':
      return <User className="w-4 h-4 text-[#D4AF37]" />;
    case 'org_submitted':
    case 'org_approved':
    case 'org_rejected':
      return <Building2 className="w-4 h-4 text-blue-400" />;
    case 'subscription_activated':
    case 'subscription_past_due':
      return <Wallet className="w-4 h-4 text-purple-400" />;
    case 'system_alert':
      return <AlertTriangle className="w-4 h-4 text-red-400" />;
    default:
      return <Bell className="w-4 h-4 text-white/60" />;
  }
};

const NotificationBadge = ({ count }) => {
  if (count === 0) return null;
  return (
    <span className="absolute -top-1 -right-1 w-5 h-5 flex items-center justify-center rounded-full bg-red-500 text-white text-xs font-bold">
      {count > 9 ? '9+' : count}
    </span>
  );
};

const NotificationsDropdown = ({ isAdmin = false }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [lastPoll, setLastPoll] = useState(null);

  const fetchNotifications = useCallback(async () => {
    try {
      const data = await notificationsAPI.getAll(20, false);
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    }
  }, []);

  const pollNotifications = useCallback(async () => {
    try {
      const data = await notificationsAPI.poll(lastPoll);
      if (data.has_new) {
        // Refresh full list if there are new notifications
        fetchNotifications();
      }
      setUnreadCount(data.unread_count || 0);
      setLastPoll(data.server_time);
    } catch (error) {
      console.error('Failed to poll notifications:', error);
    }
  }, [lastPoll, fetchNotifications]);

  useEffect(() => {
    // Initial fetch
    fetchNotifications();
    
    // Set up polling
    const interval = setInterval(pollNotifications, POLL_INTERVAL);
    
    return () => clearInterval(interval);
  }, [fetchNotifications, pollNotifications]);

  const handleMarkAsRead = async (notificationId) => {
    try {
      await notificationsAPI.markAsRead(notificationId);
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationsAPI.markAllAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const formatTime = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'À l\'instant';
    if (diff < 3600000) return `Il y a ${Math.floor(diff / 60000)} min`;
    if (diff < 86400000) return `Il y a ${Math.floor(diff / 3600000)} h`;
    return date.toLocaleDateString(i18n.language);
  };

  return (
    <div className="relative">
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] transition-colors"
        data-testid="notifications-bell"
      >
        <Bell className="w-5 h-5 text-white/70" />
        <NotificationBadge count={unreadCount} />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)} 
          />
          
          {/* Panel */}
          <div 
            className="absolute right-0 top-full mt-2 w-96 z-50 rounded-2xl overflow-hidden"
            style={{
              background: 'linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03))',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255,255,255,0.12)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/[0.08]">
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-[#D9B35A]" />
                <h3 className="font-semibold">Notifications</h3>
                {unreadCount > 0 && (
                  <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 text-xs">
                    {unreadCount} nouveau{unreadCount > 1 ? 'x' : ''}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {unreadCount > 0 && (
                  <button 
                    onClick={handleMarkAllAsRead}
                    className="p-1.5 rounded-lg hover:bg-white/[0.08] text-white/60 hover:text-white"
                    title="Tout marquer comme lu"
                  >
                    <CheckCheck className="w-4 h-4" />
                  </button>
                )}
                <button 
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-white/[0.08] text-white/60 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Notifications List */}
            <div className="max-h-96 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-8 text-center">
                  <Bell className="w-10 h-10 text-white/20 mx-auto mb-3" />
                  <p className="text-white/50 text-sm">Aucune notification</p>
                </div>
              ) : (
                notifications.map((notification) => (
                  <div
                    key={notification.id}
                    className={`p-4 border-b border-white/[0.04] hover:bg-white/[0.04] transition-colors cursor-pointer ${
                      !notification.is_read ? 'bg-white/[0.02]' : ''
                    }`}
                    onClick={() => !notification.is_read && handleMarkAsRead(notification.id)}
                  >
                    <div className="flex gap-3">
                      <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                        !notification.is_read ? 'bg-[#D9B35A]/20' : 'bg-white/[0.04]'
                      }`}>
                        <NotificationIcon type={notification.type} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`text-sm font-medium ${!notification.is_read ? 'text-white' : 'text-white/70'}`}>
                            {notification.title}
                          </p>
                          {!notification.is_read && (
                            <span className="w-2 h-2 rounded-full bg-[#D9B35A] flex-shrink-0 mt-1.5" />
                          )}
                        </div>
                        <p className="text-xs text-white/50 mt-0.5 truncate">
                          {notification.message}
                        </p>
                        <p className="text-xs text-white/30 mt-1">
                          {formatTime(notification.created_at)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            {notifications.length > 0 && (
              <div className="p-3 border-t border-white/[0.08]">
                <button className="w-full py-2 text-center text-sm text-[#D9B35A] hover:text-[#F2D07A] font-medium">
                  Voir toutes les notifications
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default NotificationsDropdown;
