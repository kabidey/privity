import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertCircle, Shield, Key, Loader2, Clock } from 'lucide-react';
import api from '../utils/api';

const TwoFactorVerify = ({ 
  open, 
  onSuccess, 
  onCancel,
  tempToken  // Token from initial login for 2FA verification
}) => {
  const [verificationMethod, setVerificationMethod] = useState('totp');
  const [totpCode, setTotpCode] = useState('');
  const [backupCode, setBackupCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [timeRemaining, setTimeRemaining] = useState(30);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (!open) {
      setTotpCode('');
      setBackupCode('');
      setError('');
      setVerificationMethod('totp');
    }
  }, [open]);

  // Timer for TOTP code countdown
  useEffect(() => {
    if (!open) return;

    const calculateTimeRemaining = () => {
      const now = Math.floor(Date.now() / 1000);
      return 30 - (now % 30);
    };

    setTimeRemaining(calculateTimeRemaining());

    const timer = setInterval(() => {
      setTimeRemaining(calculateTimeRemaining());
    }, 1000);

    return () => clearInterval(timer);
  }, [open]);

  const handleTotpVerification = async () => {
    if (totpCode.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Set the temp token for this request
      const config = tempToken ? {
        headers: { 'Authorization': `Bearer ${tempToken}` }
      } : {};

      const response = await api.post('/auth/2fa/verify', { totp_code: totpCode }, config);

      if (response.data.verified) {
        onSuccess();
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleBackupCodeVerification = async () => {
    if (!backupCode.trim()) {
      setError('Please enter a backup code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const config = tempToken ? {
        headers: { 'Authorization': `Bearer ${tempToken}` }
      } : {};

      const response = await api.post('/auth/2fa/use-backup-code', { backup_code: backupCode }, config);

      if (response.data.verified) {
        onSuccess();
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid backup code');
    } finally {
      setLoading(false);
    }
  };

  // Auto-submit when 6 digits entered
  useEffect(() => {
    if (totpCode.length === 6 && verificationMethod === 'totp' && !loading) {
      handleTotpVerification();
    }
  }, [totpCode]);

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onCancel?.()}>
      <DialogContent className="sm:max-w-[400px]" data-testid="2fa-verify-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-emerald-600" />
            Two-Factor Authentication
          </DialogTitle>
          <DialogDescription>
            Enter the verification code to continue
          </DialogDescription>
        </DialogHeader>

        <Tabs value={verificationMethod} onValueChange={setVerificationMethod} className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="totp" className="data-[state=active]:bg-emerald-500 data-[state=active]:text-white">
              <Shield className="h-4 w-4 mr-2" />
              Authenticator
            </TabsTrigger>
            <TabsTrigger value="backup" className="data-[state=active]:bg-emerald-500 data-[state=active]:text-white">
              <Key className="h-4 w-4 mr-2" />
              Backup Code
            </TabsTrigger>
          </TabsList>

          {/* TOTP Verification */}
          <TabsContent value="totp" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="totp-code">Enter 6-digit code</Label>
              <div className="relative">
                <Input
                  id="totp-code"
                  type="text"
                  inputMode="numeric"
                  placeholder="000000"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  disabled={loading}
                  className="font-mono text-center text-2xl tracking-widest pr-16"
                  autoFocus
                  data-testid="2fa-totp-input"
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-sm text-gray-500">
                  <Clock className="h-3 w-3" />
                  {timeRemaining}s
                </div>
              </div>
              <p className="text-xs text-gray-500">
                Open your authenticator app and enter the code displayed
              </p>
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}

            <Button
              onClick={handleTotpVerification}
              disabled={loading || totpCode.length !== 6}
              className="w-full bg-emerald-600 hover:bg-emerald-700"
              data-testid="2fa-verify-totp-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Verifying...
                </>
              ) : (
                'Verify'
              )}
            </Button>
          </TabsContent>

          {/* Backup Code Verification */}
          <TabsContent value="backup" className="space-y-4 mt-4">
            <div className="p-3 bg-amber-50 dark:bg-amber-950 rounded-lg">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                Lost access to your authenticator app? Use one of your backup codes to sign in.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="backup-code">Backup Code</Label>
              <Input
                id="backup-code"
                type="text"
                placeholder="XXXX-XXXX"
                value={backupCode}
                onChange={(e) => setBackupCode(e.target.value.toUpperCase())}
                disabled={loading}
                className="font-mono text-center uppercase"
                data-testid="2fa-backup-input"
              />
              <p className="text-xs text-gray-500">
                Backup codes are one-time use only
              </p>
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}

            <Button
              onClick={handleBackupCodeVerification}
              disabled={loading || !backupCode.trim()}
              className="w-full bg-emerald-600 hover:bg-emerald-700"
              data-testid="2fa-verify-backup-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Verifying...
                </>
              ) : (
                'Verify Backup Code'
              )}
            </Button>
          </TabsContent>
        </Tabs>

        {/* Cancel Button */}
        <div className="mt-4 text-center">
          <Button
            variant="ghost"
            onClick={onCancel}
            className="text-gray-500 hover:text-gray-700"
            data-testid="2fa-cancel-btn"
          >
            Cancel and Sign Out
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default TwoFactorVerify;
