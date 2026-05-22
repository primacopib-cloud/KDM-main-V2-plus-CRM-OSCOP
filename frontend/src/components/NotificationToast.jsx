import React, { useEffect, useRef, useCallback, useState } from 'react';
import { toast } from 'sonner';
import { 
  Bell, 
  ShoppingCart, 
  UserPlus, 
  AlertTriangle, 
  FileSignature,
  Package,
  CreditCard,
  Building2,
  Wifi,
  WifiOff
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Notification icon mapping
const getNotificationIcon = (type) => {
  const icons = {
    new_order: ShoppingCart,
    large_order: ShoppingCart,
    new_user: UserPlus,
    org_application: Building2,
    low_stock: Package,
    signature_completed: FileSignature,
    payment_failed: CreditCard,
    test: Bell,
    default: Bell
  };
  return icons[type] || icons.default;
};

// Notification color mapping
const getNotificationColor = (type, priority) => {
  if (priority === 'high') return '#EF4444';
  
  const colors = {
    new_order: '#D9B35A',
    large_order: '#10B981',
    new_user: '#3B82F6',
    org_application: '#8B5CF6',
    low_stock: '#F59E0B',
    signature_completed: '#8B5CF6',
    payment_failed: '#EF4444',
    test: '#6B7280',
    default: '#D9B35A'
  };
  return colors[type] || colors.default;
};

// Custom toast notification component
const NotificationContent = ({ notification }) => {
  const Icon = getNotificationIcon(notification.type);
  const color = getNotificationColor(notification.type, notification.priority);
  
  return (
    <div className="flex items-start gap-3">
      <div 
        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ background: `${color}20` }}
      >
        <Icon className="w-4 h-4" style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white">{notification.title}</p>
        <p className="text-xs text-white/70 mt-0.5">{notification.message}</p>
        {notification.data?.total && (
          <p className="text-xs text-emerald-400 mt-1 font-medium">
            {notification.data.total.toFixed(2)}€
          </p>
        )}
      </div>
    </div>
  );
};

export function useNotificationWebSocket(userId, isAdmin = false) {
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  
  const showNotification = useCallback((notification) => {
    const color = getNotificationColor(notification.type, notification.priority);
    
    toast.custom(
      (t) => <NotificationContent notification={notification} />,
      {
        duration: notification.priority === 'high' ? 10000 : 5000,
        style: {
          background: 'rgba(15, 20, 30, 0.95)',
          border: `1px solid ${color}40`,
          borderRadius: '12px',
          padding: '12px',
          backdropFilter: 'blur(10px)',
        },
      }
    );
    
    // Add to local state
    setNotifications(prev => [notification, ...prev].slice(0, 50));
  }, []);
  
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    // Build WebSocket URL
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = API_URL.replace(/^https?:\/\//, '').replace(/\/api$/, '');
    const wsUrl = `${wsProtocol}//${wsHost}/ws/notifications?user_id=${userId || ''}&is_admin=${isAdmin}`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        reconnectAttempts.current = 0;
        
        // Start heartbeat
        const heartbeat = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }));
          } else {
            clearInterval(heartbeat);
          }
        }, 30000);
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'notification') {
            showNotification(data.payload);
          } else if (data.type === 'connected') {
            console.log('WebSocket connection confirmed:', data.payload);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };
      
      wsRef.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        
        // Attempt reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
    } catch (err) {
      console.error('WebSocket connection error:', err);
    }
  }, [userId, isAdmin, showNotification]);
  
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);
  
  const markAsRead = useCallback((notificationId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'mark_read',
        payload: { notification_id: notificationId }
      }));
    }
  }, []);
  
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);
  
  return {
    isConnected,
    notifications,
    markAsRead,
    reconnect: connect
  };
}

// Connection status indicator component
export function ConnectionStatus({ isConnected }) {
  return (
    <div 
      className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs ${
        isConnected 
          ? 'bg-emerald-500/10 text-emerald-400' 
          : 'bg-red-500/10 text-red-400'
      }`}
    >
      {isConnected ? (
        <>
          <Wifi className="w-3 h-3" />
          <span>Connecté</span>
        </>
      ) : (
        <>
          <WifiOff className="w-3 h-3" />
          <span>Déconnecté</span>
        </>
      )}
    </div>
  );
}

export default { useNotificationWebSocket, ConnectionStatus };
