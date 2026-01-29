import { useState, useEffect, useCallback } from 'react';
import { ShieldAlert, Clock } from 'lucide-react';
import api from '../utils/api';

const SystemFrozenOverlay = ({ userRole }) => {
  const [status, setStatus] = useState({ is_active: false });
  const [visible, setVisible] = useState(false);

  // PE Desk (role 1) is exempt from the overlay
  const isPEDesk = userRole === 1;

  const fetchStatus = useCallback(async () => {
    try {
      const response = await api.get('/kill-switch/status');
      setStatus(response.data);
      setVisible(response.data.is_active && !isPEDesk);
    } catch (error) {
      // If we get a 503 error, the system is frozen
      if (error.response?.status === 503 && error.response?.data?.kill_switch_active) {
        setStatus({
          is_active: true,
          activated_by_name: error.response.data.activated_by,
          reason: error.response.data.reason
        });
        setVisible(!isPEDesk);
      }
    }
  }, [isPEDesk]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  if (!visible) return null;

  return (
    <div 
      className="fixed inset-0 z-[9999] bg-gray-900/95 backdrop-blur-md flex items-center justify-center"
      data-testid="system-frozen-overlay"
    >
      <div className="max-w-md w-full mx-4 text-center">
        {/* Animated Icon */}
        <div className="relative inline-block mb-6">
          <div className="absolute inset-0 bg-red-500 rounded-full blur-xl opacity-50 animate-pulse" />
          <div className="relative bg-red-600 rounded-full p-6">
            <ShieldAlert className="h-16 w-16 text-white" />
          </div>
        </div>

        {/* Title */}
        <h1 className="text-3xl font-bold text-white mb-4">
          System Temporarily Frozen
        </h1>

        {/* Message */}
        <p className="text-gray-300 mb-6 text-lg">
          The system has been temporarily frozen by the administrator for maintenance or security purposes.
        </p>

        {/* Details Card */}
        <div className="bg-gray-800/50 rounded-xl p-4 mb-6 border border-gray-700">
          <div className="flex items-center justify-center gap-2 text-amber-400 mb-2">
            <Clock className="h-5 w-5" />
            <span className="font-medium">Please wait</span>
          </div>
          <p className="text-sm text-gray-400">
            All activities are currently suspended. The system will be restored shortly.
          </p>
          {status.reason && (
            <p className="text-sm text-gray-500 mt-2">
              Reason: <span className="text-gray-300">{status.reason}</span>
            </p>
          )}
          {status.activated_by_name && (
            <p className="text-xs text-gray-500 mt-1">
              Activated by: {status.activated_by_name}
            </p>
          )}
        </div>

        {/* Animated Loading Dots */}
        <div className="flex items-center justify-center gap-2">
          <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>

        <p className="text-gray-500 text-sm mt-4">
          This page will automatically refresh when the system is restored
        </p>
      </div>
    </div>
  );
};

export default SystemFrozenOverlay;
