import { useNotifications } from '../context/NotificationContext';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Bell, AlertTriangle, CheckCircle, Clock, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const getNotificationDetails = (notification) => {
  const type = notification?.type || '';
  
  if (type.includes('booking_approved')) {
    return {
      icon: <CheckCircle className="h-12 w-12 text-green-500" />,
      color: 'text-green-600',
      bgColor: 'bg-green-100 dark:bg-green-900/30',
      action: 'View Booking',
      path: '/bookings'
    };
  }
  if (type.includes('booking_rejected') || type.includes('loss')) {
    return {
      icon: <AlertTriangle className="h-12 w-12 text-red-500" />,
      color: 'text-red-600',
      bgColor: 'bg-red-100 dark:bg-red-900/30',
      action: 'Review Now',
      path: '/bookings'
    };
  }
  if (type.includes('approval') || type.includes('pending')) {
    return {
      icon: <Clock className="h-12 w-12 text-yellow-500" />,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100 dark:bg-yellow-900/30',
      action: 'Take Action',
      path: '/bookings'
    };
  }
  if (type.includes('client')) {
    return {
      icon: <Bell className="h-12 w-12 text-blue-500" />,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100 dark:bg-blue-900/30',
      action: 'View Client',
      path: '/clients'
    };
  }
  
  return {
    icon: <Bell className="h-12 w-12 text-primary" />,
    color: 'text-primary',
    bgColor: 'bg-primary/10',
    action: 'View Details',
    path: null
  };
};

export default function NotificationDialog() {
  const { showNotificationDialog, setShowNotificationDialog, latestNotification, markAsRead } = useNotifications();
  const navigate = useNavigate();
  
  if (!latestNotification) return null;
  
  const details = getNotificationDetails(latestNotification);
  
  const handleAction = () => {
    markAsRead(latestNotification.id);
    setShowNotificationDialog(false);
    if (details.path) {
      navigate(details.path);
    }
  };
  
  const handleDismiss = () => {
    markAsRead(latestNotification.id);
    setShowNotificationDialog(false);
  };

  return (
    <Dialog open={showNotificationDialog} onOpenChange={setShowNotificationDialog}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className={`mx-auto p-4 rounded-full ${details.bgColor} mb-4`}>
            {details.icon}
          </div>
          <DialogTitle className="text-center text-xl">
            {latestNotification.title}
          </DialogTitle>
          <DialogDescription className="text-center text-base mt-2">
            {latestNotification.message}
          </DialogDescription>
        </DialogHeader>
        
        {latestNotification.data && Object.keys(latestNotification.data).length > 0 && (
          <div className="bg-muted/50 rounded-lg p-3 mt-2">
            <div className="grid grid-cols-2 gap-2 text-sm">
              {latestNotification.data.booking_number && (
                <>
                  <span className="text-muted-foreground">Booking:</span>
                  <span className="font-medium">{latestNotification.data.booking_number}</span>
                </>
              )}
              {latestNotification.data.stock_symbol && (
                <>
                  <span className="text-muted-foreground">Stock:</span>
                  <span className="font-medium">{latestNotification.data.stock_symbol}</span>
                </>
              )}
              {latestNotification.data.client_name && (
                <>
                  <span className="text-muted-foreground">Client:</span>
                  <span className="font-medium">{latestNotification.data.client_name}</span>
                </>
              )}
            </div>
          </div>
        )}
        
        <div className="text-center text-xs text-muted-foreground mt-2">
          {new Date(latestNotification.created_at).toLocaleString()}
        </div>
        
        <DialogFooter className="flex-col sm:flex-row gap-2 mt-4">
          <Button variant="outline" onClick={handleDismiss} className="w-full sm:w-auto">
            Dismiss
          </Button>
          <Button onClick={handleAction} className="w-full sm:w-auto gap-2">
            {details.action}
            <ArrowRight className="h-4 w-4" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
