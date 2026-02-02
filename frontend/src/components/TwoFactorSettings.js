import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { 
  Shield, 
  ShieldOff, 
  Key, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  Loader2,
  Copy,
  ShieldCheck
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import TwoFactorSetup from './TwoFactorSetup';

const TwoFactorSettings = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [disableDialogOpen, setDisableDialogOpen] = useState(false);
  const [regenerateDialogOpen, setRegenerateDialogOpen] = useState(false);
  const [setupDialogOpen, setSetupDialogOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');
  const [newBackupCodes, setNewBackupCodes] = useState([]);
  const [copiedIndex, setCopiedIndex] = useState(null);

  const fetchStatus = async () => {
    try {
      const response = await api.get('/auth/2fa/status');
      setStatus(response.data);
    } catch (err) {
      console.error('Failed to fetch 2FA status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleDisable2FA = async () => {
    if (!password) {
      setError('Password is required');
      return;
    }

    setActionLoading(true);
    setError('');

    try {
      await api.post('/auth/2fa/disable', { password });
      toast.success('Two-factor authentication disabled');
      setDisableDialogOpen(false);
      setPassword('');
      fetchStatus();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to disable 2FA');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRegenerateBackupCodes = async () => {
    if (!password) {
      setError('Password is required');
      return;
    }

    setActionLoading(true);
    setError('');

    try {
      const response = await api.post('/auth/2fa/regenerate-backup-codes', { password });
      setNewBackupCodes(response.data.backup_codes);
      toast.success('New backup codes generated');
      setPassword('');
      fetchStatus();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to regenerate backup codes');
    } finally {
      setActionLoading(false);
    }
  };

  const copyBackupCode = (code, index) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const copyAllBackupCodes = () => {
    navigator.clipboard.writeText(newBackupCodes.join('\n'));
    toast.success('All backup codes copied');
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="2fa-settings-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-emerald-600" />
          Two-Factor Authentication
        </CardTitle>
        <CardDescription>
          Add an extra layer of security to your account
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Banner */}
        {status?.enabled ? (
          <div className="flex items-center gap-3 p-4 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
            <ShieldCheck className="h-8 w-8 text-green-600" />
            <div>
              <h4 className="font-medium text-green-800 dark:text-green-200">2FA is Enabled</h4>
              <p className="text-sm text-green-600 dark:text-green-400">
                Your account is protected with two-factor authentication
              </p>
              {status.enabled_at && (
                <p className="text-xs text-green-500 mt-1">
                  Enabled on {new Date(status.enabled_at).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 p-4 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg">
            <ShieldOff className="h-8 w-8 text-amber-600" />
            <div>
              <h4 className="font-medium text-amber-800 dark:text-amber-200">2FA is Not Enabled</h4>
              <p className="text-sm text-amber-600 dark:text-amber-400">
                Enable two-factor authentication to add extra security
              </p>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-3">
          {status?.enabled ? (
            <>
              {/* Backup Codes Info */}
              <div className="w-full p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Key className="h-4 w-4 text-gray-500" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      Backup codes remaining: <strong>{status.backup_codes_remaining || 0}</strong>
                    </span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setRegenerateDialogOpen(true)}
                    data-testid="regenerate-backup-btn"
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Regenerate
                  </Button>
                </div>
              </div>

              {/* Disable Button */}
              <Button
                variant="destructive"
                onClick={() => setDisableDialogOpen(true)}
                className="gap-2"
                data-testid="disable-2fa-btn"
              >
                <ShieldOff className="h-4 w-4" />
                Disable 2FA
              </Button>
            </>
          ) : (
            <TwoFactorSetup onSetupComplete={fetchStatus} />
          )}
        </div>

        {/* Disable 2FA Dialog */}
        <Dialog open={disableDialogOpen} onOpenChange={setDisableDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-600">
                <ShieldOff className="h-5 w-5" />
                Disable Two-Factor Authentication
              </DialogTitle>
              <DialogDescription>
                This will remove the extra security layer from your account. You can re-enable it anytime.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-4">
              <div className="p-3 bg-red-50 dark:bg-red-950 rounded-lg">
                <p className="text-sm text-red-800 dark:text-red-200">
                  <AlertCircle className="h-4 w-4 inline mr-1" />
                  Warning: Your account will be less secure without 2FA.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="disable-password">Confirm your password</Label>
                <Input
                  id="disable-password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={actionLoading}
                  data-testid="disable-2fa-password"
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                  <AlertCircle className="h-4 w-4" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setDisableDialogOpen(false);
                    setPassword('');
                    setError('');
                  }}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDisable2FA}
                  disabled={actionLoading || !password}
                  className="flex-1"
                  data-testid="confirm-disable-2fa-btn"
                >
                  {actionLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Disabling...
                    </>
                  ) : (
                    'Disable 2FA'
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Regenerate Backup Codes Dialog */}
        <Dialog open={regenerateDialogOpen} onOpenChange={(open) => {
          setRegenerateDialogOpen(open);
          if (!open) {
            setNewBackupCodes([]);
            setPassword('');
            setError('');
          }
        }}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Key className="h-5 w-5 text-emerald-600" />
                {newBackupCodes.length > 0 ? 'Your New Backup Codes' : 'Regenerate Backup Codes'}
              </DialogTitle>
              <DialogDescription>
                {newBackupCodes.length > 0 
                  ? 'Save these codes securely. Previous backup codes are now invalid.'
                  : 'This will invalidate all existing backup codes and generate new ones.'}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-4">
              {newBackupCodes.length > 0 ? (
                <>
                  <div className="p-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg">
                    <p className="text-sm text-amber-800 dark:text-amber-200">
                      <AlertCircle className="h-4 w-4 inline mr-1" />
                      Previous backup codes no longer work. Save these new codes now.
                    </p>
                  </div>

                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-2">
                    {newBackupCodes.map((code, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded"
                      >
                        <code className="font-mono text-sm">{code}</code>
                        <button
                          onClick={() => copyBackupCode(code, index)}
                          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                        >
                          {copiedIndex === index ? (
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                          ) : (
                            <Copy className="h-4 w-4 text-gray-400" />
                          )}
                        </button>
                      </div>
                    ))}
                  </div>

                  <Button variant="outline" onClick={copyAllBackupCodes} className="w-full">
                    <Copy className="h-4 w-4 mr-2" />
                    Copy All Codes
                  </Button>

                  <Button
                    onClick={() => {
                      setRegenerateDialogOpen(false);
                      setNewBackupCodes([]);
                    }}
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                  >
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Done
                  </Button>
                </>
              ) : (
                <>
                  <div className="p-3 bg-amber-50 dark:bg-amber-950 rounded-lg">
                    <p className="text-sm text-amber-800 dark:text-amber-200">
                      <AlertCircle className="h-4 w-4 inline mr-1" />
                      All existing backup codes will be invalidated.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="regen-password">Confirm your password</Label>
                    <Input
                      id="regen-password"
                      type="password"
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      disabled={actionLoading}
                      data-testid="regen-backup-password"
                    />
                  </div>

                  {error && (
                    <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                      <AlertCircle className="h-4 w-4" />
                      <span className="text-sm">{error}</span>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setRegenerateDialogOpen(false);
                        setPassword('');
                        setError('');
                      }}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleRegenerateBackupCodes}
                      disabled={actionLoading || !password}
                      className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                      data-testid="confirm-regen-btn"
                    >
                      {actionLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Generate New Codes
                        </>
                      )}
                    </Button>
                  </div>
                </>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};

export default TwoFactorSettings;
