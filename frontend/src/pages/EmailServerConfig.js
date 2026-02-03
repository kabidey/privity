import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { Mail, Server, Shield, Send, CheckCircle, XCircle, AlertCircle, Eye, EyeOff, RefreshCw } from 'lucide-react';

const EmailServerConfig = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [presets, setPresets] = useState([]);
  const [testDialog, setTestDialog] = useState({ open: false });
  const [testEmail, setTestEmail] = useState('');
  
  const [config, setConfig] = useState({
    smtp_host: 'smtp.office365.com',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    smtp_from_email: '',
    smtp_from_name: 'SMIFS Private Equity System',
    use_tls: true,
    use_ssl: false,
    timeout: 30,
    is_enabled: true,
    connection_status: 'not_configured',
    last_test: null,
    last_test_result: null
  });

  const { user, isPELevel } = useCurrentUser();

  useEffect(() => {
    // Wait for user to load before checking permissions
    if (user === null) return;
    
    if (!isPELevel) {
      navigate('/');
      return;
    }
    fetchConfig();
    fetchPresets();
  }, [user, isPELevel, navigate]);

  const fetchConfig = async () => {
    try {
      const response = await api.get('/email-config');
      setConfig(prev => ({ ...prev, ...response.data }));
    } catch (error) {
      toast.error('Failed to load email configuration');
    } finally {
      setLoading(false);
    }
  };

  const fetchPresets = async () => {
    try {
      const response = await api.get('/email-config/presets');
      // Backend returns array directly, not wrapped in {presets: [...]}
      setPresets(Array.isArray(response.data) ? response.data : response.data.presets || []);
    } catch (error) {
      console.error('Failed to load presets:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/email-config', config);
      toast.success('Email configuration saved successfully');
      fetchConfig();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!testEmail) {
      toast.error('Please enter a test email address');
      return;
    }
    
    setTesting(true);
    try {
      const response = await api.post('/email-config/test', { test_email: testEmail });
      if (response.data.success) {
        toast.success(response.data.message || `Test email sent successfully to ${testEmail}`);
      } else {
        toast.error(response.data.message || 'Failed to send test email');
      }
      setTestDialog({ open: false });
      fetchConfig();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send test email');
    } finally {
      setTesting(false);
    }
  };

  const applyPreset = (preset) => {
    setConfig(prev => ({
      ...prev,
      smtp_host: preset.smtp_host,
      smtp_port: preset.smtp_port,
      use_tls: preset.use_tls,
      use_ssl: preset.use_ssl
    }));
    toast.info(`Applied ${preset.name} preset. Please enter your credentials.`);
  };

  const getStatusBadge = () => {
    switch (config.connection_status) {
      case 'connected':
        return <Badge className="bg-green-100 text-green-800"><CheckCircle className="h-3 w-3 mr-1" />Connected</Badge>;
      case 'auth_failed':
        return <Badge className="bg-red-100 text-red-800"><XCircle className="h-3 w-3 mr-1" />Auth Failed</Badge>;
      case 'connection_failed':
        return <Badge className="bg-red-100 text-red-800"><XCircle className="h-3 w-3 mr-1" />Connection Failed</Badge>;
      case 'configured':
        return <Badge className="bg-blue-100 text-blue-800"><AlertCircle className="h-3 w-3 mr-1" />Configured (Untested)</Badge>;
      default:
        return <Badge variant="outline"><AlertCircle className="h-3 w-3 mr-1" />Not Configured</Badge>;
    }
  };

  if (!isPELevel) return null;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="email-server-config">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Email Server Configuration</h1>
          <p className="text-muted-foreground">Configure SMTP settings for sending emails (Microsoft 365 compatible)</p>
        </div>
        <div className="flex items-center gap-3">
          {getStatusBadge()}
        </div>
      </div>

      <Tabs defaultValue="settings" className="space-y-4">
        <TabsList>
          <TabsTrigger value="settings">
            <Server className="h-4 w-4 mr-2" />
            Server Settings
          </TabsTrigger>
          <TabsTrigger value="presets">
            <Mail className="h-4 w-4 mr-2" />
            Provider Presets
          </TabsTrigger>
        </TabsList>

        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                SMTP Server Configuration
              </CardTitle>
              <CardDescription>
                Configure your email server settings. For Microsoft 365, use smtp.office365.com with port 587 and TLS enabled.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Enable/Disable */}
              <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                <div>
                  <Label className="text-base font-medium">Enable Email Sending</Label>
                  <p className="text-sm text-muted-foreground">Turn off to disable all outgoing emails</p>
                </div>
                <Switch
                  checked={config.is_enabled}
                  onCheckedChange={(checked) => setConfig({ ...config, is_enabled: checked })}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* SMTP Host */}
                <div className="space-y-2">
                  <Label htmlFor="smtp_host">SMTP Host *</Label>
                  <Input
                    id="smtp_host"
                    value={config.smtp_host}
                    onChange={(e) => setConfig({ ...config, smtp_host: e.target.value })}
                    placeholder="smtp.office365.com"
                  />
                </div>

                {/* SMTP Port */}
                <div className="space-y-2">
                  <Label htmlFor="smtp_port">SMTP Port *</Label>
                  <Input
                    id="smtp_port"
                    type="number"
                    value={config.smtp_port}
                    onChange={(e) => setConfig({ ...config, smtp_port: parseInt(e.target.value) || 587 })}
                    placeholder="587"
                  />
                </div>

                {/* Username */}
                <div className="space-y-2">
                  <Label htmlFor="smtp_username">Username / Email *</Label>
                  <Input
                    id="smtp_username"
                    value={config.smtp_username}
                    onChange={(e) => setConfig({ ...config, smtp_username: e.target.value })}
                    placeholder="your-email@company.com"
                  />
                </div>

                {/* Password */}
                <div className="space-y-2">
                  <Label htmlFor="smtp_password">Password / App Password *</Label>
                  <div className="relative">
                    <Input
                      id="smtp_password"
                      type={showPassword ? "text" : "password"}
                      value={config.smtp_password}
                      onChange={(e) => setConfig({ ...config, smtp_password: e.target.value })}
                      placeholder="Enter password or app password"
                      className="pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground">For Microsoft 365 with MFA, use an App Password</p>
                </div>

                {/* From Email */}
                <div className="space-y-2">
                  <Label htmlFor="smtp_from_email">From Email Address *</Label>
                  <Input
                    id="smtp_from_email"
                    type="email"
                    value={config.smtp_from_email}
                    onChange={(e) => setConfig({ ...config, smtp_from_email: e.target.value })}
                    placeholder="noreply@company.com"
                  />
                  <p className="text-xs text-muted-foreground">Must match or be allowed by your email account</p>
                </div>

                {/* From Name */}
                <div className="space-y-2">
                  <Label htmlFor="smtp_from_name">From Display Name</Label>
                  <Input
                    id="smtp_from_name"
                    value={config.smtp_from_name}
                    onChange={(e) => setConfig({ ...config, smtp_from_name: e.target.value })}
                    placeholder="SMIFS Private Equity System"
                  />
                </div>
              </div>

              {/* Security Settings */}
              <div className="border rounded-lg p-4 space-y-4">
                <h3 className="font-medium">Security Settings</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Use TLS (STARTTLS)</Label>
                      <p className="text-xs text-muted-foreground">Recommended for port 587</p>
                    </div>
                    <Switch
                      checked={config.use_tls}
                      onCheckedChange={(checked) => setConfig({ ...config, use_tls: checked, use_ssl: checked ? false : config.use_ssl })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Use SSL</Label>
                      <p className="text-xs text-muted-foreground">For port 465 only</p>
                    </div>
                    <Switch
                      checked={config.use_ssl}
                      onCheckedChange={(checked) => setConfig({ ...config, use_ssl: checked, use_tls: checked ? false : config.use_tls })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="timeout">Connection Timeout (seconds)</Label>
                    <Input
                      id="timeout"
                      type="number"
                      value={config.timeout}
                      onChange={(e) => setConfig({ ...config, timeout: parseInt(e.target.value) || 30 })}
                      min={5}
                      max={120}
                    />
                  </div>
                </div>
              </div>

              {/* Last Test Info */}
              {config.last_test && (
                <div className="bg-muted/50 p-4 rounded-lg text-sm">
                  <p><strong>Last Test:</strong> {new Date(config.last_test).toLocaleString()}</p>
                  <p><strong>Result:</strong> {config.last_test_result === 'success' ? '✅ Success' : `❌ ${config.last_test_result}`}</p>
                  {config.last_test_email && <p><strong>Test Email:</strong> {config.last_test_email}</p>}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex justify-end gap-3 pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => setTestDialog({ open: true })}
                  disabled={!config.smtp_host || !config.smtp_username}
                >
                  <Send className="h-4 w-4 mr-2" />
                  Send Test Email
                </Button>
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Configuration'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="presets">
          <Card>
            <CardHeader>
              <CardTitle>Email Provider Presets</CardTitle>
              <CardDescription>
                Quick configuration presets for popular email providers. Click to apply settings.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {presets.map((preset, index) => (
                  <Card key={index} className="cursor-pointer hover:border-primary transition-colors" onClick={() => applyPreset(preset)}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Mail className="h-4 w-4" />
                        {preset.name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-1">
                      <p><strong>Host:</strong> {preset.smtp_host}</p>
                      <p><strong>Port:</strong> {preset.smtp_port}</p>
                      <p><strong>TLS:</strong> {preset.use_tls ? 'Yes' : 'No'}</p>
                      <p className="text-xs text-muted-foreground mt-2">{preset.notes}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Test Email Dialog */}
      <Dialog open={testDialog.open} onOpenChange={(open) => setTestDialog({ open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Send className="h-5 w-5" />
              Send Test Email
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Send a test email to verify your SMTP configuration is working correctly.
            </p>
            <div className="space-y-2">
              <Label htmlFor="test-email">Recipient Email Address</Label>
              <Input
                id="test-email"
                type="email"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                placeholder="your-email@example.com"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTestDialog({ open: false })}>
              Cancel
            </Button>
            <Button onClick={handleTest} disabled={testing || !testEmail}>
              {testing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Send Test Email
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EmailServerConfig;
