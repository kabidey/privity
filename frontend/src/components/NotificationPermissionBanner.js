import { Bell, X, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNotifications } from '../context/NotificationContext';

const NotificationPermissionBanner = () => {
  const { 
    showPermissionBanner, 
    requestPermissions, 
    dismissPermissionBanner,
    notificationPermission 
  } = useNotifications();

  // Don't show if permission already granted or banner dismissed
  if (!showPermissionBanner || notificationPermission === 'granted') {
    return null;
  }

  return (
    <div 
      className="fixed top-16 left-1/2 transform -translate-x-1/2 z-[100] w-full max-w-lg mx-auto px-4"
      data-testid="notification-permission-banner"
    >
      <div className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-2xl shadow-2xl p-4 animate-in slide-in-from-top duration-500">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-white/20 rounded-xl">
            <Bell className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-lg">Enable Notifications</h3>
            <p className="text-sm text-white/90 mt-1">
              Get instant alerts with sound when there are new bookings, approvals, or important updates.
            </p>
            <div className="flex items-center gap-2 mt-3">
              <Button 
                onClick={requestPermissions}
                className="bg-white text-emerald-600 hover:bg-white/90 font-medium"
                size="sm"
                data-testid="enable-notifications-btn"
              >
                <Volume2 className="h-4 w-4 mr-2" />
                Enable Now
              </Button>
              <Button 
                onClick={dismissPermissionBanner}
                variant="ghost"
                size="sm"
                className="text-white/80 hover:text-white hover:bg-white/20"
              >
                Maybe Later
              </Button>
            </div>
          </div>
          <button 
            onClick={dismissPermissionBanner}
            className="p-1 hover:bg-white/20 rounded-lg transition-colors"
            aria-label="Dismiss"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotificationPermissionBanner;
