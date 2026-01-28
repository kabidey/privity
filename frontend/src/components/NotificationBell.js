import { useState, useEffect } from 'react';
import { Bell, Check, CheckCheck, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useNotifications } from '../context/NotificationContext';

const NotificationBell = () => {
  const [open, setOpen] = useState(false);
  const { notifications, unreadCount, markAsRead, markAllAsRead, isConnected, hasNewNotification, setHasNewNotification } = useNotifications();
  
  // Derive animation state directly from hasNewNotification
  const isAnimating = hasNewNotification && !open;

  // Handle popover open to stop animation
  const handleOpenChange = (newOpen) => {
    setOpen(newOpen);
    if (newOpen && hasNewNotification) {
      setHasNewNotification(false);
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'client_pending':
      case 'booking_pending':
        return '⏳';
      case 'client_approved':
      case 'booking_approved':
        return '✅';
      case 'client_rejected':
      case 'booking_rejected':
        return '❌';
      default:
        return '🔔';
    }
  };

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button 
          variant="ghost" 
          size="icon" 
          className={`relative ${isAnimating ? 'animate-bounce' : ''}`}
          data-testid="notification-bell"
          style={isAnimating ? {
            animation: 'bellRing 0.5s ease-in-out infinite',
          } : {}}
        >
          <Bell 
            className={`h-5 w-5 transition-all ${isAnimating ? 'text-yellow-500' : ''}`}
            style={isAnimating ? {
              filter: 'drop-shadow(0 0 8px #eab308) drop-shadow(0 0 16px #f59e0b)',
            } : {}}
          />
          {unreadCount > 0 && (
            <Badge 
              className={`absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs ${
                isAnimating ? 'animate-ping' : ''
              }`}
              variant="destructive"
              style={isAnimating ? {
                boxShadow: '0 0 10px #ef4444, 0 0 20px #ef4444',
              } : {}}
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </Badge>
          )}
          {/* Animated ring effect when new notification */}
          {isAnimating && (
            <>
              <span className="absolute inset-0 rounded-full bg-yellow-400 animate-ping opacity-30" />
              <span className="absolute -inset-1 rounded-full bg-gradient-to-r from-yellow-400 via-red-500 to-yellow-400 opacity-50 animate-pulse" style={{ filter: 'blur(4px)' }} />
            </>
          )}
          {isConnected && (
            <span className="absolute bottom-0 right-0 h-2 w-2 bg-green-500 rounded-full" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <div className="flex items-center justify-between p-3 border-b">
          <h4 className="font-semibold">Notifications</h4>
          {unreadCount > 0 && (
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={markAllAsRead}
              className="text-xs"
            >
              <CheckCheck className="h-4 w-4 mr-1" />
              Mark all read
            </Button>
          )}
        </div>
        <ScrollArea className="h-[300px]">
          {notifications.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              No notifications
            </div>
          ) : (
            <div className="divide-y">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-3 hover:bg-muted/50 cursor-pointer transition-colors ${
                    !notification.read ? 'bg-blue-50 dark:bg-blue-950/20' : ''
                  }`}
                  onClick={() => !notification.read && markAsRead(notification.id)}
                >
                  <div className="flex items-start gap-2">
                    <span className="text-lg">{getNotificationIcon(notification.type)}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{notification.title}</p>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {notification.message}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatTime(notification.created_at)}
                      </p>
                    </div>
                    {!notification.read && (
                      <div className="h-2 w-2 bg-blue-500 rounded-full flex-shrink-0" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
};

export default NotificationBell;
