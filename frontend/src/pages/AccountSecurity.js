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
  Key, 
  Lock, 
  Clock, 
  MapPin, 
  Laptop,
  AlertCircle,
  Loader2,
  CheckCircle2
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import TwoFactorSettings from '../components/TwoFactorSettings';

const AccountSecurity = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState('');

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
    setLoading(false);
  }, []);

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError('All fields are required');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return;
    }

    setChangingPassword(true);
    setPasswordError('');

    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      toast.success('Password changed successfully');
      setShowChangePassword(false);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPasswordError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setChangingPassword(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="account-security-page">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-emerald-100 dark:bg-emerald-900 rounded-lg">
          <Shield className="h-6 w-6 text-emerald-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Account Security</h1>
          <p className="text-gray-500 dark:text-gray-400">Manage your security settings and authentication methods</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Two-Factor Authentication Card */}
        <div className="md:col-span-2">
          <TwoFactorSettings />
        </div>

        {/* Password Security Card */}
        <Card data-testid="password-security-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5 text-blue-600" />
              Password
            </CardTitle>
            <CardDescription>
              Manage your account password
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <Lock className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">Password</p>
                <p className="text-xs text-gray-500">••••••••••••</p>
              </div>
            </div>

            <Button
              variant="outline"
              onClick={() => setShowChangePassword(true)}
              className="w-full gap-2"
              data-testid="change-password-btn"
            >
              <Key className="h-4 w-4" />
              Change Password
            </Button>
          </CardContent>
        </Card>

        {/* Account Information Card */}
        <Card data-testid="account-info-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Laptop className="h-5 w-5 text-purple-600" />
              Account Information
            </CardTitle>
            <CardDescription>
              Your account details
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <span className="text-sm text-gray-500">Email</span>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <span className="text-sm text-gray-500">Name</span>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{user?.name}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <span className="text-sm text-gray-500">Role</span>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{user?.role_name}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Security Tips Card */}
        <Card className="md:col-span-2" data-testid="security-tips-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-600" />
              Security Tips
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="p-4 bg-emerald-50 dark:bg-emerald-950 rounded-lg">
                <Shield className="h-8 w-8 text-emerald-600 mb-2" />
                <h4 className="font-medium text-emerald-900 dark:text-emerald-100 mb-1">Enable 2FA</h4>
                <p className="text-sm text-emerald-700 dark:text-emerald-300">
                  Two-factor authentication adds an extra layer of security to your account
                </p>
              </div>
              <div className="p-4 bg-blue-50 dark:bg-blue-950 rounded-lg">
                <Key className="h-8 w-8 text-blue-600 mb-2" />
                <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-1">Strong Password</h4>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  Use a unique password with letters, numbers, and special characters
                </p>
              </div>
              <div className="p-4 bg-purple-50 dark:bg-purple-950 rounded-lg">
                <Lock className="h-8 w-8 text-purple-600 mb-2" />
                <h4 className="font-medium text-purple-900 dark:text-purple-100 mb-1">Stay Vigilant</h4>
                <p className="text-sm text-purple-700 dark:text-purple-300">
                  Never share your password or backup codes with anyone
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Change Password Dialog */}
      <Dialog open={showChangePassword} onOpenChange={setShowChangePassword}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Key className="h-5 w-5 text-blue-600" />
              Change Password
            </DialogTitle>
            <DialogDescription>
              Enter your current password and choose a new one
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="current-password">Current Password</Label>
              <Input
                id="current-password"
                type="password"
                placeholder="Enter current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                disabled={changingPassword}
                data-testid="current-password-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="new-password">New Password</Label>
              <Input
                id="new-password"
                type="password"
                placeholder="Enter new password (min 8 characters)"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={changingPassword}
                data-testid="new-password-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm-password">Confirm New Password</Label>
              <Input
                id="confirm-password"
                type="password"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={changingPassword}
                data-testid="confirm-password-input"
              />
            </div>

            {passwordError && (
              <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-md">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm">{passwordError}</span>
              </div>
            )}

            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setShowChangePassword(false);
                  setCurrentPassword('');
                  setNewPassword('');
                  setConfirmPassword('');
                  setPasswordError('');
                }}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handleChangePassword}
                disabled={changingPassword || !currentPassword || !newPassword || !confirmPassword}
                className="flex-1 bg-blue-600 hover:bg-blue-700"
                data-testid="save-password-btn"
              >
                {changingPassword ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Changing...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Change Password
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AccountSecurity;
