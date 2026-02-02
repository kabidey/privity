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
  ShieldCheck,
  Smartphone,
  ArrowLeft,
  ArrowRight
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const TwoFactorSettings = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Setup flow states
  const [setupMode, setSetupMode] = useState(false);
  const [setupStep, setSetupStep] = useState(1); // 1: password, 2: qr code, 3: verify, 4: backup codes
  const [setupPassword, setSetupPassword] = useState('');
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [backupCodes, setBackupCodes] = useState([]);
  const [totpCode, setTotpCode] = useState('');
  const [setupLoading, setSetupLoading] = useState(false);
  const [setupError, setSetupError] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  
  // Disable dialog states
  const [disableDialogOpen, setDisableDialogOpen] = useState(false);
  const [disablePassword, setDisablePassword] = useState('');
  const [disableLoading, setDisableLoading] = useState(false);
  const [disableError, setDisableError] = useState('');
  
  // Regenerate dialog states
  const [regenerateDialogOpen, setRegenerateDialogOpen] = useState(false);
  const [regeneratePassword, setRegeneratePassword] = useState('');
  const [regenerateLoading, setRegenerateLoading] = useState(false);
  const [regenerateError, setRegenerateError] = useState('');
  const [newBackupCodes, setNewBackupCodes] = useState([]);

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

  // Setup flow handlers
  const handleStartSetup = () => {
    setSetupMode(true);
    setSetupStep(1);
    setSetupPassword('');
    setSetupError('');
  };

  const handleCancelSetup = () => {
    setSetupMode(false);
    setSetupStep(1);
    setSetupPassword('');
    setQrCodeUrl('');
    setSecretKey('');
    setBackupCodes([]);
    setTotpCode('');
    setSetupError('');
  };

  const handlePasswordSubmit = async () => {
    if (!setupPassword) {
      setSetupError('Password is required');
      return;
    }

    setSetupLoading(true);
    setSetupError('');

    try {
      const response = await api.post('/auth/2fa/enable', { password: setupPassword });
      setQrCodeUrl(response.data.qr_code_url);
      setSecretKey(response.data.secret_key);
      setBackupCodes(response.data.backup_codes);
      setSetupStep(2);
    } catch (err) {
      setSetupError(err.response?.data?.detail || 'Failed to initiate 2FA setup');
    } finally {
      setSetupLoading(false);
    }
  };

  const handleVerifyTotp = async () => {
    if (totpCode.length !== 6) {
      setSetupError('Please enter a 6-digit code');
      return;
    }

    setSetupLoading(true);
    setSetupError('');

    try {
      await api.post('/auth/2fa/verify-setup', { totp_code: totpCode });
      setSetupStep(4);
    } catch (err) {
      setSetupError(err.response?.data?.detail || 'Invalid code. Please try again.');
    } finally {
      setSetupLoading(false);
    }
  };

  const handleSetupComplete = () => {
    toast.success('Two-factor authentication enabled successfully!');
    handleCancelSetup();
    fetchStatus();
  };

  const copySecretKey = () => {
    navigator.clipboard.writeText(secretKey);
    setCopiedSecret(true);
    toast.success('Secret key copied');
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  const copyBackupCode = (code, index) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const copyAllBackupCodes = () => {
    const codes = setupStep === 4 ? backupCodes : newBackupCodes;
    navigator.clipboard.writeText(codes.join('\n'));
    toast.success('All backup codes copied');
  };

  // Disable 2FA handler
  const handleDisable2FA = async () => {
    if (!disablePassword) {
      setDisableError('Password is required');
      return;
    }

    setDisableLoading(true);
    setDisableError('');

    try {
      await api.post('/auth/2fa/disable', { password: disablePassword });
      toast.success('Two-factor authentication disabled');
      setDisableDialogOpen(false);
      setDisablePassword('');
      fetchStatus();
    } catch (err) {
      setDisableError(err.response?.data?.detail || 'Failed to disable 2FA');
    } finally {
      setDisableLoading(false);
    }
  };

  // Regenerate backup codes handler
  const handleRegenerateBackupCodes = async () => {
    if (!regeneratePassword) {
      setRegenerateError('Password is required');
      return;
    }

    setRegenerateLoading(true);
    setRegenerateError('');

    try {
      const response = await api.post('/auth/2fa/regenerate-backup-codes', { password: regeneratePassword });
      setNewBackupCodes(response.data.backup_codes);
      toast.success('New backup codes generated');
      setRegeneratePassword('');
      fetchStatus();
    } catch (err) {
      setRegenerateError(err.response?.data?.detail || 'Failed to regenerate backup codes');
    } finally {
      setRegenerateLoading(false);
    }
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

  // Render setup flow
  if (setupMode) {
    return (
      <Card data-testid="2fa-setup-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-emerald-600" />
              Enable Two-Factor Authentication
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={handleCancelSetup}>
              <ArrowLeft className="h-4 w-4 mr-1" />
              Cancel
            </Button>
          </div>
          <CardDescription>
            Step {setupStep} of 4: {
              setupStep === 1 ? 'Confirm Password' :
              setupStep === 2 ? 'Scan QR Code' :
              setupStep === 3 ? 'Verify Code' :
              'Save Backup Codes'
            }
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Step 1: Password Confirmation */}
          {setupStep === 1 && (
            <>
              <div className="p-4 bg-blue-50 dark:bg-blue-950 rounded-lg">
                <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">How it works:</h4>
                <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                  <li>1. Confirm your password</li>
                  <li>2. Scan QR code with your authenticator app</li>
                  <li>3. Enter the 6-digit code to verify</li>
                  <li>4. Save your backup codes securely</li>
                </ul>
              </div>

              <div className="space-y-2">
                <Label htmlFor="setup-password">Confirm your password</Label>
                <Input
                  id="setup-password"
                  type="password"
                  placeholder="Enter your current password"
                  value={setupPassword}
                  onChange={(e) => setSetupPassword(e.target.value)}
                  disabled={setupLoading}
                  data-testid="2fa-password-input"
                  onKeyDown={(e) => e.key === 'Enter' && handlePasswordSubmit()}
                />
              </div>

              {setupError && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span className="text-sm">{setupError}</span>
                </div>
              )}

              <Button
                onClick={handlePasswordSubmit}
                disabled={setupLoading || !setupPassword}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
                data-testid="2fa-continue-btn"
              >
                {setupLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    Continue
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            </>
          )}

          {/* Step 2: QR Code */}
          {setupStep === 2 && (
            <>
              <div className="text-center">
                <Smartphone className="h-8 w-8 mx-auto mb-2 text-emerald-600" />
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
                </p>
              </div>

              <div className="flex justify-center">
                <div className="p-4 bg-white rounded-lg shadow-sm border">
                  <img
                    src={qrCodeUrl}
                    alt="2FA QR Code"
                    className="w-48 h-48"
                    data-testid="2fa-qr-code"
                  />
                </div>
              </div>

              <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg text-sm">
                <p className="text-gray-600 dark:text-gray-400 mb-2">Can't scan? Enter this key manually:</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-white dark:bg-gray-800 p-2 rounded font-mono text-xs break-all">
                    {secretKey}
                  </code>
                  <Button variant="ghost" size="sm" onClick={copySecretKey}>
                    {copiedSecret ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              <Button
                onClick={() => setSetupStep(3)}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
              >
                I've Scanned the QR Code
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </>
          )}

          {/* Step 3: Verify TOTP */}
          {setupStep === 3 && (
            <>
              <div className="space-y-2">
                <Label htmlFor="totp-code">Enter 6-digit code from your authenticator app</Label>
                <Input
                  id="totp-code"
                  type="text"
                  inputMode="numeric"
                  placeholder="000000"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  disabled={setupLoading}
                  className="font-mono text-center text-2xl tracking-widest"
                  data-testid="2fa-code-input"
                  onKeyDown={(e) => e.key === 'Enter' && handleVerifyTotp()}
                />
              </div>

              {setupError && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span className="text-sm">{setupError}</span>
                </div>
              )}

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setSetupStep(2)} className="flex-1">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back
                </Button>
                <Button
                  onClick={handleVerifyTotp}
                  disabled={setupLoading || totpCode.length !== 6}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                  data-testid="2fa-verify-btn"
                >
                  {setupLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    'Verify'
                  )}
                </Button>
              </div>
            </>
          )}

          {/* Step 4: Backup Codes */}
          {setupStep === 4 && (
            <>
              <div className="p-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-amber-800 dark:text-amber-200">
                  <strong>Important:</strong> Save these backup codes in a safe place. Each code can only be used once.
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-2">
                {backupCodes.map((code, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded"
                  >
                    <code className="font-mono text-sm">{code}</code>
                    <button
                      onClick={() => copyBackupCode(code, index)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
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
                Copy All Backup Codes
              </Button>

              <Button
                onClick={handleSetupComplete}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
                data-testid="2fa-complete-btn"
              >
                <CheckCircle2 className="h-4 w-4 mr-2" />
                I've Saved My Backup Codes
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    );
  }

  // Normal view (not in setup mode)
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
            <Button 
              variant="outline" 
              className="gap-2" 
              onClick={handleStartSetup}
              data-testid="enable-2fa-btn"
            >
              <Shield className="h-4 w-4" />
              Enable Two-Factor Authentication
            </Button>
          )}
        </div>

        {/* Disable 2FA Dialog */}
        <Dialog open={disableDialogOpen} onOpenChange={setDisableDialogOpen}>
          <DialogContent onInteractOutside={(e) => e.preventDefault()}>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-600">
                <ShieldOff className="h-5 w-5" />
                Disable Two-Factor Authentication
              </DialogTitle>
              <DialogDescription>
                This will remove the extra security layer from your account.
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
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  disabled={disableLoading}
                />
              </div>

              {disableError && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                  <AlertCircle className="h-4 w-4" />
                  <span className="text-sm">{disableError}</span>
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setDisableDialogOpen(false);
                    setDisablePassword('');
                    setDisableError('');
                  }}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDisable2FA}
                  disabled={disableLoading || !disablePassword}
                  className="flex-1"
                >
                  {disableLoading ? (
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
            setRegeneratePassword('');
            setRegenerateError('');
          }
        }}>
          <DialogContent className="sm:max-w-[500px]" onInteractOutside={(e) => e.preventDefault()}>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Key className="h-5 w-5 text-emerald-600" />
                {newBackupCodes.length > 0 ? 'Your New Backup Codes' : 'Regenerate Backup Codes'}
              </DialogTitle>
              <DialogDescription>
                {newBackupCodes.length > 0 
                  ? 'Save these codes securely. Previous backup codes are now invalid.'
                  : 'This will invalidate all existing backup codes.'}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-4">
              {newBackupCodes.length > 0 ? (
                <>
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
                      value={regeneratePassword}
                      onChange={(e) => setRegeneratePassword(e.target.value)}
                      disabled={regenerateLoading}
                    />
                  </div>

                  {regenerateError && (
                    <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                      <AlertCircle className="h-4 w-4" />
                      <span className="text-sm">{regenerateError}</span>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setRegenerateDialogOpen(false);
                        setRegeneratePassword('');
                        setRegenerateError('');
                      }}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleRegenerateBackupCodes}
                      disabled={regenerateLoading || !regeneratePassword}
                      className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                    >
                      {regenerateLoading ? (
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
