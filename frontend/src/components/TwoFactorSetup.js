import { useState } from 'react';
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
import { AlertCircle, CheckCircle2, Copy, Shield, Smartphone, Key, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const TwoFactorSetup = ({ open, onOpenChange, onSetupComplete }) => {
  const [setupStep, setSetupStep] = useState('initial'); // initial, qrcode, verify, backup, complete
  const [password, setPassword] = useState('');
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [backupCodes, setBackupCodes] = useState([]);
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [copiedSecret, setCopiedSecret] = useState(false);

  const resetState = () => {
    setSetupStep('initial');
    setPassword('');
    setQrCodeUrl('');
    setSecretKey('');
    setBackupCodes([]);
    setTotpCode('');
    setError('');
    setCopiedIndex(null);
    setCopiedSecret(false);
  };

  const handleOpenChange = (isOpen) => {
    if (!isOpen) {
      resetState();
    }
    onOpenChange(isOpen);
  };

  const handleInitiateSetup = async () => {
    if (!password) {
      setError('Password is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await api.post('/auth/2fa/enable', { password });
      setQrCodeUrl(response.data.qr_code_url);
      setSecretKey(response.data.secret_key);
      setBackupCodes(response.data.backup_codes);
      setSetupStep('qrcode');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to initiate 2FA setup');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifySetup = async () => {
    if (totpCode.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await api.post('/auth/2fa/verify-setup', { totp_code: totpCode });
      setSetupStep('backup');
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const copyBackupCode = (code, index) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const copySecretKey = () => {
    navigator.clipboard.writeText(secretKey);
    setCopiedSecret(true);
    toast.success('Secret key copied to clipboard');
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  const copyAllBackupCodes = () => {
    navigator.clipboard.writeText(backupCodes.join('\n'));
    toast.success('All backup codes copied to clipboard');
  };

  const handleComplete = () => {
    setSetupStep('complete');
    toast.success('Two-factor authentication enabled successfully!');
    if (onSetupComplete) {
      onSetupComplete();
    }
    setTimeout(() => {
      setOpen(false);
      resetState();
    }, 2000);
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => {
      setOpen(isOpen);
      if (!isOpen) resetState();
    }}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2" data-testid="enable-2fa-btn">
          <Shield className="h-4 w-4" />
          Enable Two-Factor Authentication
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-[500px]">
        {/* Step 1: Password Confirmation */}
        {setupStep === 'initial' && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-emerald-600" />
                Enable Two-Factor Authentication
              </DialogTitle>
              <DialogDescription>
                Add an extra layer of security to your account using an authenticator app like Google Authenticator, Authy, or Microsoft Authenticator.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-4">
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
                <Label htmlFor="password">Confirm your password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your current password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  data-testid="2fa-password-input"
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              <Button
                onClick={handleInitiateSetup}
                disabled={loading || !password}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
                data-testid="2fa-continue-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Setting up...
                  </>
                ) : (
                  'Continue'
                )}
              </Button>
            </div>
          </>
        )}

        {/* Step 2: QR Code Scan */}
        {setupStep === 'qrcode' && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Smartphone className="h-5 w-5 text-emerald-600" />
                Scan QR Code
              </DialogTitle>
              <DialogDescription>
                Scan this QR code with your authenticator app (Google Authenticator, Authy, Microsoft Authenticator, etc.)
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-4">
              {/* QR Code */}
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

              {/* Manual Entry Option */}
              <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg text-sm">
                <p className="text-gray-600 dark:text-gray-400 mb-2">Can't scan the QR code? Enter this key manually:</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-white dark:bg-gray-800 p-2 rounded font-mono text-xs break-all">
                    {secretKey}
                  </code>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={copySecretKey}
                    className="flex-shrink-0"
                    data-testid="copy-secret-btn"
                  >
                    {copiedSecret ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              {/* TOTP Code Input */}
              <div className="space-y-2">
                <Label htmlFor="totp">Enter 6-digit code from your authenticator app</Label>
                <Input
                  id="totp"
                  type="text"
                  inputMode="numeric"
                  placeholder="000000"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  disabled={loading}
                  className="font-mono text-center text-2xl tracking-widest"
                  data-testid="2fa-code-input"
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              <Button
                onClick={handleVerifySetup}
                disabled={loading || totpCode.length !== 6}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
                data-testid="2fa-verify-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  'Verify and Continue'
                )}
              </Button>
            </div>
          </>
        )}

        {/* Step 3: Backup Codes */}
        {setupStep === 'backup' && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Key className="h-5 w-5 text-emerald-600" />
                Save Your Backup Codes
              </DialogTitle>
              <DialogDescription>
                Store these backup codes securely. You can use them to access your account if you lose access to your authenticator app.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-4">
              <div className="p-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-amber-800 dark:text-amber-200">
                  <strong>Important:</strong> Each backup code can only be used once. Store them in a safe place like a password manager.
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
                      data-testid={`copy-backup-${index}`}
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

              <Button
                variant="outline"
                onClick={copyAllBackupCodes}
                className="w-full"
                data-testid="copy-all-backup-btn"
              >
                <Copy className="h-4 w-4 mr-2" />
                Copy All Backup Codes
              </Button>

              <Button
                onClick={handleComplete}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
                data-testid="2fa-complete-btn"
              >
                <CheckCircle2 className="h-4 w-4 mr-2" />
                I've Saved My Backup Codes
              </Button>
            </div>
          </>
        )}

        {/* Step 4: Complete */}
        {setupStep === 'complete' && (
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900 mb-4">
              <CheckCircle2 className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Two-Factor Authentication Enabled!
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Your account is now more secure.
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default TwoFactorSetup;
