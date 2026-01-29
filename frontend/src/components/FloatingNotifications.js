import { useNotifications } from '../context/NotificationContext';
import { X, Bell, AlertTriangle, CheckCircle, Info, Clock } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '../lib/utils';

const getNotificationIcon = (type) => {
  if (type?.includes('approved') || type?.includes('success')) {
    return <CheckCircle className="h-5 w-5 text-green-500" />;
  }
  if (type?.includes('rejected') || type?.includes('error') || type?.includes('loss')) {
    return <AlertTriangle className="h-5 w-5 text-red-500" />;
  }
  if (type?.includes('pending') || type?.includes('waiting')) {
    return <Clock className="h-5 w-5 text-yellow-500" />;
  }
  if (type?.includes('info')) {
    return <Info className="h-5 w-5 text-blue-500" />;
  }
  return <Bell className="h-5 w-5 text-primary" />;
};

const getNotificationColor = (type) => {
  if (type?.includes('approved') || type?.includes('success')) {
    return 'border-l-green-500 bg-green-50 dark:bg-green-950/30';
  }
  if (type?.includes('rejected') || type?.includes('error') || type?.includes('loss')) {
    return 'border-l-red-500 bg-red-50 dark:bg-red-950/30';
  }
  if (type?.includes('pending') || type?.includes('waiting') || type?.includes('approval')) {
    return 'border-l-yellow-500 bg-yellow-50 dark:bg-yellow-950/30';
  }
  return 'border-l-blue-500 bg-blue-50 dark:bg-blue-950/30';
};

export default function FloatingNotifications() {
  const { floatingNotifications, dismissFloatingNotification, markAsRead } = useNotifications();

  if (floatingNotifications.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-3 max-w-md w-full pointer-events-none">
      {floatingNotifications.map((notification, index) => (
        <div
          key={notification.floatingId}
          className={cn(
            "pointer-events-auto rounded-lg border-l-4 p-4 shadow-2xl",
            "animate-in slide-in-from-right-full duration-300",
            "backdrop-blur-sm",
            getNotificationColor(notification.type)
          )}
          style={{
            animationDelay: `${index * 100}ms`,
            boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
          }}
        >
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 mt-0.5">
              {getNotificationIcon(notification.type)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h4 className="font-semibold text-sm text-foreground truncate">
                  {notification.title}
                </h4>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 hover:bg-black/10"
                  onClick={() => dismissFloatingNotification(notification.floatingId)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                {notification.message}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <Button
                  variant="secondary"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => {
                    markAsRead(notification.id);
                    dismissFloatingNotification(notification.floatingId);
                  }}
                >
                  Mark as Read
                </Button>
                <span className="text-xs text-muted-foreground">
                  {new Date(notification.created_at).toLocaleTimeString()}
                </span>
              </div>
            </div>
          </div>
          
          {/* Progress bar for auto-dismiss */}
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/10 rounded-b-lg overflow-hidden">
            <div 
              className="h-full bg-primary/50 animate-shrink-width"
              style={{ animationDuration: '8s' }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
