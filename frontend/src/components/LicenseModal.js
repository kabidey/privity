import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertTriangle, Key, Clock, Shield, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const LicenseModal = ({ open, onClose, onLicenseActivated }) => {
  const [licenseKey, setLicenseKey] = useState('');
  const [durationDays, setDurationDays] = useState('365');
  const [loading, setLoading] = useState(false);
  const [licenseStatus, setLicenseStatus] = useState(null);
  const [showDuration, setShowDuration] = useState(false);

  useEffect(() => {
    if (open) {
      checkLicenseStatus();
    }
  }, [open]);

  const checkLicenseStatus = async () => {
    try {
      const response = await api.get('/license/status');
      setLicenseStatus(response.data);
    } catch (error) {
      console.error('Failed to check license:', error);
    }
  };

  const handleActivate = async () => {
    if (!licenseKey.trim()) {
      toast.error('Please enter a license key');
      return;
    }

    // Format validation
    const keyPattern = /^PRIV-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/i;
    if (!keyPattern.test(licenseKey.trim())) {
      toast.error('Invalid license key format. Expected: PRIV-XXXX-XXXX-XXXX-XXXX');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        license_key: licenseKey.trim().toUpperCase()
      };
      
      if (showDuration) {
        payload.duration_days = parseInt(durationDays);
      }

      const response = await api.post('/license/activate', payload);
      
      toast.success(response.data.message || 'License activated successfully!');
      setLicenseKey('');
      checkLicenseStatus();
      
      if (onLicenseActivated) {
        onLicenseActivated(response.data);
      }
      
      if (onClose) {
        onClose();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to activate license');
    } finally {
      setLoading(false);
    }
  };

  const formatLicenseKey = (value) => {
    // Remove non-alphanumeric except dashes
    let cleaned = value.toUpperCase().replace(/[^A-Z0-9-]/g, '');
    
    // Auto-format as user types
    if (cleaned.startsWith('PRIV') && !cleaned.startsWith('PRIV-')) {
      cleaned = 'PRIV-' + cleaned.slice(4);
    }
    
    // Add dashes at appropriate positions
    const parts = cleaned.split('-');
    if (parts.length === 1 && parts[0].length > 4) {
      // Auto-add dashes
      let formatted = parts[0].slice(0, 4);
      let remaining = parts[0].slice(4);
      while (remaining.length > 0) {
        formatted += '-' + remaining.slice(0, 4);
        remaining = remaining.slice(4);
      }
      return formatted.slice(0, 24); // PRIV-XXXX-XXXX-XXXX-XXXX = 24 chars
    }
    
    return cleaned.slice(0, 24);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'text-green-600';
      case 'expiring_soon': return 'text-amber-600';
      case 'expired': return 'text-red-600';
      case 'no_license': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active': return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'expiring_soon': return <Clock className="h-5 w-5 text-amber-600" />;
      case 'expired': return <XCircle className="h-5 w-5 text-red-600" />;
      case 'no_license': return <AlertTriangle className="h-5 w-5 text-red-600" />;
      default: return <Shield className="h-5 w-5" />;
    }
  };

  const isBlocking = licenseStatus && !licenseStatus.is_valid;

  return (
    <Dialog open={open} onOpenChange={isBlocking ? undefined : onClose}>
      <DialogContent 
        className="sm:max-w-md"
        onPointerDownOutside={isBlocking ? (e) => e.preventDefault() : undefined}
        onEscapeKeyDown={isBlocking ? (e) => e.preventDefault() : undefined}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-5 w-5 text-emerald-600" />
            License Management
          </DialogTitle>
          <DialogDescription>
            {isBlocking 
              ? 'A valid license is required to use Privity. Please enter your license key.'
              : 'View license status or activate a new license key.'
            }
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Current License Status */}
          {licenseStatus && (
            <div className={`p-4 rounded-lg border ${
              licenseStatus.is_valid 
                ? 'bg-green-50 border-green-200 dark:bg-green-950/30 dark:border-green-800' 
                : 'bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800'
            }`}>
              <div className="flex items-start gap-3">
                {getStatusIcon(licenseStatus.status)}
                <div className="flex-1">
                  <h4 className={`font-semibold ${getStatusColor(licenseStatus.status)}`}>
                    {licenseStatus.status === 'active' && 'License Active'}
                    {licenseStatus.status === 'expiring_soon' && 'License Expiring Soon'}
                    {licenseStatus.status === 'expired' && 'License Expired'}
                    {licenseStatus.status === 'no_license' && 'No License Found'}
                  </h4>
                  <p className="text-sm text-muted-foreground mt-1">
                    {licenseStatus.message}
                  </p>
                  {licenseStatus.is_valid && (
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-muted-foreground">Days Remaining:</span>
                        <span className="ml-1 font-medium">{licenseStatus.days_remaining}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Expires:</span>
                        <span className="ml-1 font-medium">
                          {new Date(licenseStatus.expires_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                {licenseStatus?.is_valid ? 'Renew License' : 'Activate License'}
              </span>
            </div>
          </div>

          {/* License Key Input */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="licenseKey">License Key</Label>
              <Input
                id="licenseKey"
                placeholder="PRIV-XXXX-XXXX-XXXX-XXXX"
                value={licenseKey}
                onChange={(e) => setLicenseKey(formatLicenseKey(e.target.value))}
                className="font-mono text-center tracking-wider"
                data-testid="license-key-input"
              />
              <p className="text-xs text-muted-foreground">
                Enter the license key provided by SMIFS
              </p>
            </div>

            {/* Duration Toggle (PE Desk Only) */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="customDuration"
                checked={showDuration}
                onChange={(e) => setShowDuration(e.target.checked)}
                className="rounded border-gray-300"
              />
              <Label htmlFor="customDuration" className="text-sm cursor-pointer">
                Set custom duration (Admin only)
              </Label>
            </div>

            {showDuration && (
              <div className="space-y-2">
                <Label htmlFor="duration">License Duration</Label>
                <Select value={durationDays} onValueChange={setDurationDays}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select duration" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="30">30 Days (1 Month)</SelectItem>
                    <SelectItem value="90">90 Days (3 Months)</SelectItem>
                    <SelectItem value="180">180 Days (6 Months)</SelectItem>
                    <SelectItem value="365">365 Days (1 Year)</SelectItem>
                    <SelectItem value="730">730 Days (2 Years)</SelectItem>
                    <SelectItem value="1095">1095 Days (3 Years)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <Button 
              onClick={handleActivate} 
              disabled={loading || !licenseKey.trim()}
              className="w-full"
              data-testid="activate-license-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Activating...
                </>
              ) : (
                <>
                  <Key className="mr-2 h-4 w-4" />
                  Activate License
                </>
              )}
            </Button>
          </div>

          {/* Help Text */}
          <div className="text-center text-xs text-muted-foreground">
            <p>Need a license key? Contact your administrator or</p>
            <p>email <span className="text-emerald-600">support@smifs.com</span></p>
            <p className="mt-2 text-emerald-600 font-medium">
              Note: SMIFS employees (@smifs.com) are exempt from licensing.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default LicenseModal;
