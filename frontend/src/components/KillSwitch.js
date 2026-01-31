import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import api from '../utils/api';
import { Power, AlertTriangle, ShieldAlert, Clock, Unlock } from 'lucide-react';

const KillSwitch = ({ userRole }) => {
  const [status, setStatus] = useState({ is_active: false, remaining_seconds: 0 });
  const [loading, setLoading] = useState(false);
  const [showActivateDialog, setShowActivateDialog] = useState(false);
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false);
  const [reason, setReason] = useState('');
  const [timer, setTimer] = useState(0);

  // Only PE Desk (role 1) can see and use the kill switch
  const isPEDesk = userRole === 1;

  const fetchStatus = useCallback(async () => {
    try {
      const response = await api.get('/kill-switch/status');
      setStatus(response.data);
      setTimer(response.data.remaining_seconds || 0);
    } catch (error) {
      console.error('Failed to fetch kill switch status:', error);
    }
  }, []);

  // Fetch status on mount and periodically (reduced from 5s to 30s)
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // 30 seconds instead of 5
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Countdown timer
  useEffect(() => {
    if (timer > 0) {
      const countdown = setInterval(() => {
        setTimer(prev => {
          if (prev <= 1) {
            fetchStatus();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(countdown);
    }
  }, [timer, fetchStatus]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleActivate = async () => {
    setLoading(true);
    try {
      const response = await api.post(`/kill-switch/activate?reason=${encodeURIComponent(reason || 'Emergency system freeze')}`);
      toast.success('Kill Switch Activated - System is now frozen');
      setShowActivateDialog(false);
      setReason('');
      fetchStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to activate kill switch');
    } finally {
      setLoading(false);
    }
  };

  const handleDeactivate = async () => {
    setLoading(true);
    try {
      await api.post('/kill-switch/deactivate');
      toast.success('Kill Switch Deactivated - System is now operational');
      setShowDeactivateDialog(false);
      fetchStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to deactivate kill switch');
    } finally {
      setLoading(false);
    }
  };

  if (!isPEDesk) return null;

  return (
    <>
      {/* Kill Switch Button */}
      <div className="px-3 py-2">
        {status.is_active ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 p-3 bg-red-100 dark:bg-red-900/30 rounded-xl border border-red-200 dark:border-red-800">
              <div className="relative">
                <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-400" />
                <div className="absolute inset-0 animate-ping">
                  <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-400 opacity-50" />
                </div>
              </div>
              <div className="flex-1">
                <p className="text-xs font-semibold text-red-700 dark:text-red-300">SYSTEM FROZEN</p>
                <p className="text-[10px] text-red-600 dark:text-red-400">{status.reason || 'Emergency freeze'}</p>
              </div>
            </div>
            
            {/* Timer Display */}
            {timer > 0 ? (
              <div className="flex items-center justify-center gap-2 p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                <span className="text-sm font-mono font-bold text-amber-700 dark:text-amber-300">
                  {formatTime(timer)}
                </span>
                <span className="text-xs text-amber-600 dark:text-amber-400">until unlock</span>
              </div>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDeactivateDialog(true)}
                className="w-full border-green-500 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20"
                data-testid="deactivate-kill-switch-btn"
              >
                <Unlock className="h-4 w-4 mr-2" />
                Deactivate Kill Switch
              </Button>
            )}
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowActivateDialog(true)}
            className="w-full border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
            data-testid="activate-kill-switch-btn"
          >
            <Power className="h-4 w-4 mr-2" />
            Kill Switch
          </Button>
        )}
      </div>

      {/* Activate Dialog */}
      <Dialog open={showActivateDialog} onOpenChange={setShowActivateDialog}>
        <DialogContent className="sm:max-w-md" data-testid="kill-switch-activate-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Activate Kill Switch
            </DialogTitle>
            <DialogDescription>
              This will immediately freeze the entire system for all users.
            </DialogDescription>
          </DialogHeader>

          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Warning: Emergency Action</AlertTitle>
            <AlertDescription>
              <ul className="list-disc ml-4 mt-2 space-y-1 text-sm">
                <li>All users will be blocked from any activity</li>
                <li>No emails will be sent</li>
                <li>All API calls will be rejected</li>
                <li>3-minute cooldown before you can deactivate</li>
                <li>Only you (PE Desk) can access the system</li>
              </ul>
            </AlertDescription>
          </Alert>

          <div className="space-y-2">
            <Label htmlFor="reason">Reason (optional)</Label>
            <Input
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g., Security incident, Maintenance"
              data-testid="kill-switch-reason-input"
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowActivateDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleActivate}
              disabled={loading}
              data-testid="confirm-activate-kill-switch"
            >
              {loading ? 'Activating...' : 'Activate Kill Switch'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Deactivate Dialog */}
      <Dialog open={showDeactivateDialog} onOpenChange={setShowDeactivateDialog}>
        <DialogContent className="sm:max-w-md" data-testid="kill-switch-deactivate-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-600">
              <Unlock className="h-5 w-5" />
              Deactivate Kill Switch
            </DialogTitle>
            <DialogDescription>
              This will restore normal system operations for all users.
            </DialogDescription>
          </DialogHeader>

          <Alert className="border-green-500 bg-green-50 dark:bg-green-900/20">
            <Unlock className="h-4 w-4 text-green-600" />
            <AlertTitle className="text-green-700 dark:text-green-300">Ready to Unlock</AlertTitle>
            <AlertDescription className="text-green-600 dark:text-green-400">
              The cooldown period has passed. You can now safely deactivate the kill switch and restore system access.
            </AlertDescription>
          </Alert>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeactivateDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleDeactivate}
              disabled={loading}
              className="bg-green-600 hover:bg-green-700"
              data-testid="confirm-deactivate-kill-switch"
            >
              {loading ? 'Deactivating...' : 'Deactivate & Restore'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default KillSwitch;
