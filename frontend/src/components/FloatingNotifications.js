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

  // Only show critical notifications (loss, rejection, urgent)
  const criticalNotifications = floatingNotifications.filter(n => 
    n.type?.includes('loss') || 
    n.type?.includes('rejected') || 
    n.type?.includes('urgent') ||
    n.type?.includes('error')
  );

  // Limit to max 2 notifications at a time
  const visibleNotifications = criticalNotifications.slice(0, 2);

  if (visibleNotifications.length === 0) return null;

  return (
    <div className="fixed top-20 right-4 z-[9999] flex flex-col gap-2 max-w-sm w-full sm:max-w-md pointer-events-none">
      {visibleNotifications.map((notification, index) => (
        <div
          key={notification.floatingId}
          className={cn(
            "pointer-events-auto rounded-lg border-l-4 p-3 shadow-lg",
            "animate-in slide-in-from-right-full duration-300",
            "backdrop-blur-sm",
            getNotificationColor(notification.type)
          )}
          style={{
            animationDelay: `${index * 100}ms`,
          }}
        >
          <div className="flex items-start gap-2">
            <div className="flex-shrink-0">
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
                  className="h-6 w-6 p-0 hover:bg-black/10 flex-shrink-0"
                  onClick={() => dismissFloatingNotification(notification.floatingId)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {notification.message}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
