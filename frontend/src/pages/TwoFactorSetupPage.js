import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Shield, 
  Key, 
  AlertCircle, 
  CheckCircle2, 
  Loader2,
  Copy,
  Smartphone,
  ArrowLeft,
  ArrowRight
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const TwoFactorSetupPage = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: password, 2: qr code, 3: verify, 4: backup codes
  const [password, setPassword] = useState('');
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [backupCodes, setBackupCodes] = useState([]);
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [checkingStatus, setCheckingStatus] = useState(true);

  useEffect(() => {
    // Check if 2FA is already enabled
    const checkStatus = async () => {
      try {
        const response = await api.get('/auth/2fa/status');
        if (response.data.enabled) {
          toast.info('2FA is already enabled');
          navigate('/account-security');
        }
      } catch (err) {
        console.error('Failed to check 2FA status:', err);
      } finally {
        setCheckingStatus(false);
      }
    };
    checkStatus();
  }, [navigate]);

  const handlePasswordSubmit = async () => {
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
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to initiate 2FA setup');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyTotp = async () => {
    if (totpCode.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await api.post('/auth/2fa/verify-setup', { totp_code: totpCode });
      setStep(4);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = () => {
    toast.success('Two-factor authentication enabled successfully!');
    navigate('/account-security');
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
    navigator.clipboard.writeText(backupCodes.join('\n'));
    toast.success('All backup codes copied');
  };

  if (checkingStatus) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto space-y-6" data-testid="2fa-setup-page">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/account-security')}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
      </div>

      <Card data-testid="2fa-setup-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-emerald-600" />
            Enable Two-Factor Authentication
          </CardTitle>
          <CardDescription>
            Step {step} of 4: {
              step === 1 ? 'Confirm Password' :
              step === 2 ? 'Scan QR Code' :
              step === 3 ? 'Verify Code' :
              'Save Backup Codes'
            }
          </CardDescription>
          {/* Progress bar */}
          <div className="flex gap-1 mt-2">
            {[1, 2, 3, 4].map((s) => (
              <div
                key={s}
                className={`h-1 flex-1 rounded ${
                  s <= step ? 'bg-emerald-500' : 'bg-gray-200 dark:bg-gray-700'
                }`}
              />
            ))}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Step 1: Password Confirmation */}
          {step === 1 && (
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
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  data-testid="2fa-password-input"
                  onKeyDown={(e) => e.key === 'Enter' && handlePasswordSubmit()}
                  autoFocus
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              <Button
                onClick={handlePasswordSubmit}
                disabled={loading || !password}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
                data-testid="2fa-continue-btn"
              >
                {loading ? (
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
          {step === 2 && (
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
                onClick={() => setStep(3)}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
              >
                I've Scanned the QR Code
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </>
          )}

          {/* Step 3: Verify TOTP */}
          {step === 3 && (
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
                  disabled={loading}
                  className="font-mono text-center text-2xl tracking-widest"
                  data-testid="2fa-code-input"
                  onKeyDown={(e) => e.key === 'Enter' && handleVerifyTotp()}
                  autoFocus
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setStep(2)} className="flex-1">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back
                </Button>
                <Button
                  onClick={handleVerifyTotp}
                  disabled={loading || totpCode.length !== 6}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                  data-testid="2fa-verify-btn"
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
              </div>
            </>
          )}

          {/* Step 4: Backup Codes */}
          {step === 4 && (
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
                onClick={handleComplete}
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
    </div>
  );
};

export default TwoFactorSetupPage;
