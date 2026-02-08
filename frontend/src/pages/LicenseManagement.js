import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { ScrollArea } from '../components/ui/scroll-area';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  Key, Shield, Building2, Calendar, Users, Package, 
  CheckCircle2, XCircle, AlertTriangle, Copy, RefreshCw,
  Plus, Trash2, Eye, Lock, Unlock, TrendingUp, Briefcase,
  FileText, BarChart3, MessageSquare, Mail, ScanLine, FolderOpen,
  UserCheck, Handshake, DollarSign, Database
} from 'lucide-react';

const LicenseManagement = () => {
  // State
  const [isLicenseAdmin, setIsLicenseAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [definitions, setDefinitions] = useState({ modules: {}, features: {}, usage_limits: {} });
  const [licenses, setLicenses] = useState([]);
  const [licenseStatus, setLicenseStatus] = useState({ private_equity: null, fixed_income: null });
  
  // Generate License Dialog
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [newLicense, setNewLicense] = useState({
    company_type: 'private_equity',
    company_name: 'SMIFS',
    duration_days: 365,
    modules: [],
    features: [],
    usage_limits: {}
  });
  const [generatedKey, setGeneratedKey] = useState(null);
  
  // Activate License Dialog
  const [activateDialogOpen, setActivateDialogOpen] = useState(false);
  const [activateKey, setActivateKey] = useState('');
  const [activating, setActivating] = useState(false);
  
  // Feature icons mapping
  const featureIcons = {
    clients: Users,
    bookings: FileText,
    inventory: Package,
    vendors: Building2,
    purchases: DollarSign,
    stocks: TrendingUp,
    reports: BarChart3,
    analytics: BarChart3,
    bi_reports: BarChart3,
    whatsapp: MessageSquare,
    email: Mail,
    ocr: ScanLine,
    documents: FolderOpen,
    referral_partners: UserCheck,
    business_partners: Handshake,
    fi_instruments: TrendingUp,
    fi_orders: FileText,
    fi_reports: BarChart3,
    fi_primary_market: Building2,
    user_management: Users,
    role_management: Shield,
    audit_logs: FileText,
    database_backup: Database,
    company_master: Building2,
    finance: DollarSign,
    contract_notes: FileText
  };
  
  // Verify admin access on mount
  useEffect(() => {
    checkAdminAccess();
  }, []);
  
  const checkAdminAccess = async () => {
    try {
      const response = await api.get('/licence/verify-admin');
      if (response.data.is_license_admin) {
        setIsLicenseAdmin(true);
        await Promise.all([
          fetchDefinitions(),
          fetchLicenses(),
          fetchLicenseStatus()
        ]);
      } else {
        setIsLicenseAdmin(false);
      }
    } catch (error) {
      console.error('Admin verification failed:', error);
      setIsLicenseAdmin(false);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchDefinitions = async () => {
    try {
      const response = await api.get('/licence/definitions');
      setDefinitions(response.data);
    } catch (error) {
      console.error('Failed to fetch definitions:', error);
    }
  };
  
  const fetchLicenses = async () => {
    try {
      const response = await api.get('/licence/all');
      setLicenses(response.data.licenses || []);
    } catch (error) {
      console.error('Failed to fetch licenses:', error);
    }
  };
  
  const fetchLicenseStatus = async () => {
    try {
      const response = await api.get('/licence/status');
      setLicenseStatus(response.data.status || { private_equity: null, fixed_income: null });
    } catch (error) {
      console.error('Failed to fetch license status:', error);
    }
  };
  
  const handleGenerateLicense = async () => {
    setGenerating(true);
    try {
      const payload = {
        ...newLicense,
        modules: newLicense.modules.length > 0 ? newLicense.modules : [newLicense.company_type],
        features: newLicense.features.length > 0 ? newLicense.features : Object.keys(definitions.features)
      };
      
      const response = await api.post('/licence/generate', payload);
      
      if (response.data.success) {
        setGeneratedKey(response.data.license);
        toast.success('License key generated successfully!');
        await fetchLicenses();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate license');
    } finally {
      setGenerating(false);
    }
  };
  
  const handleActivateLicense = async () => {
    if (!activateKey.trim()) {
      toast.error('Please enter a license key');
      return;
    }
    
    setActivating(true);
    try {
      const response = await api.post('/licence/activate', { license_key: activateKey });
      
      if (response.data.success) {
        toast.success(response.data.message);
        setActivateDialogOpen(false);
        setActivateKey('');
        await Promise.all([fetchLicenses(), fetchLicenseStatus()]);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to activate license');
    } finally {
      setActivating(false);
    }
  };
  
  const handleRevokeLicense = async (licenseKey) => {
    if (!window.confirm('Are you sure you want to revoke this license?')) return;
    
    try {
      const response = await api.post('/licence/revoke', { license_key: licenseKey });
      
      if (response.data.success) {
        toast.success('License revoked successfully');
        await Promise.all([fetchLicenses(), fetchLicenseStatus()]);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to revoke license');
    }
  };
  
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };
  
  const toggleFeature = (feature) => {
    setNewLicense(prev => ({
      ...prev,
      features: prev.features.includes(feature)
        ? prev.features.filter(f => f !== feature)
        : [...prev.features, feature]
    }));
  };
  
  const toggleModule = (module) => {
    setNewLicense(prev => ({
      ...prev,
      modules: prev.modules.includes(module)
        ? prev.modules.filter(m => m !== module)
        : [...prev.modules, module]
    }));
  };
  
  const selectAllFeatures = () => {
    setNewLicense(prev => ({
      ...prev,
      features: Object.keys(definitions.features)
    }));
  };
  
  const clearAllFeatures = () => {
    setNewLicense(prev => ({
      ...prev,
      features: []
    }));
  };
  
  const getStatusBadge = (status) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-500"><CheckCircle2 className="w-3 h-3 mr-1" /> Active</Badge>;
      case 'expired':
        return <Badge className="bg-red-500"><XCircle className="w-3 h-3 mr-1" /> Expired</Badge>;
      case 'expiring_soon':
        return <Badge className="bg-amber-500"><AlertTriangle className="w-3 h-3 mr-1" /> Expiring Soon</Badge>;
      case 'revoked':
        return <Badge className="bg-gray-500"><Lock className="w-3 h-3 mr-1" /> Revoked</Badge>;
      case 'pending':
        return <Badge className="bg-blue-500"><Key className="w-3 h-3 mr-1" /> Pending</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };
  
  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }
  
  // Access denied
  if (!isLicenseAdmin) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <Lock className="w-16 h-16 text-red-500" />
        <h1 className="text-2xl font-bold text-gray-800">Access Denied</h1>
        <p className="text-gray-600">You don't have permission to access this page.</p>
      </div>
    );
  }
  
  return (
    <div className="p-6 space-y-6" data-testid="license-management-page">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Key className="w-7 h-7 text-blue-600" />
            License Management
          </h1>
          <p className="text-gray-500 mt-1">Manage granular licensing for PE and FI modules</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setActivateDialogOpen(true)}
            data-testid="activate-license-btn"
          >
            <Unlock className="w-4 h-4 mr-2" />
            Activate License
          </Button>
          <Button
            onClick={() => {
              setGeneratedKey(null);
              setNewLicense({
                company_type: 'private_equity',
                company_name: 'SMIFS',
                duration_days: 365,
                modules: [],
                features: [],
                usage_limits: {}
              });
              setGenerateDialogOpen(true);
            }}
            data-testid="generate-license-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Generate License
          </Button>
        </div>
      </div>
      
      {/* License Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Private Equity License */}
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Briefcase className="w-5 h-5 text-blue-600" />
              Private Equity License
            </CardTitle>
          </CardHeader>
          <CardContent>
            {licenseStatus.private_equity?.is_active ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  {getStatusBadge(licenseStatus.private_equity.status)}
                  <span className="text-sm text-gray-500">
                    {licenseStatus.private_equity.days_remaining} days remaining
                  </span>
                </div>
                <div className="text-sm">
                  <span className="text-gray-500">Features:</span>
                  <span className="ml-2 font-medium">
                    {licenseStatus.private_equity.features?.length || 0} enabled
                  </span>
                </div>
                <div className="text-xs text-gray-400">
                  Expires: {new Date(licenseStatus.private_equity.expires_at).toLocaleDateString()}
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <XCircle className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-500">No active license</p>
              </div>
            )}
          </CardContent>
        </Card>
        
        {/* Fixed Income License */}
        <Card className="border-l-4 border-l-teal-500">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <TrendingUp className="w-5 h-5 text-teal-600" />
              Fixed Income License
            </CardTitle>
          </CardHeader>
          <CardContent>
            {licenseStatus.fixed_income?.is_active ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  {getStatusBadge(licenseStatus.fixed_income.status)}
                  <span className="text-sm text-gray-500">
                    {licenseStatus.fixed_income.days_remaining} days remaining
                  </span>
                </div>
                <div className="text-sm">
                  <span className="text-gray-500">Features:</span>
                  <span className="ml-2 font-medium">
                    {licenseStatus.fixed_income.features?.length || 0} enabled
                  </span>
                </div>
                <div className="text-xs text-gray-400">
                  Expires: {new Date(licenseStatus.fixed_income.expires_at).toLocaleDateString()}
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <XCircle className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-500">No active license</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      
      {/* License History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            License History
          </CardTitle>
          <CardDescription>All generated and activated licenses</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-2">License Key</th>
                  <th className="text-left py-3 px-2">Type</th>
                  <th className="text-left py-3 px-2">Company</th>
                  <th className="text-left py-3 px-2">Status</th>
                  <th className="text-left py-3 px-2">Duration</th>
                  <th className="text-left py-3 px-2">Features</th>
                  <th className="text-left py-3 px-2">Created</th>
                  <th className="text-left py-3 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {licenses.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-gray-500">
                      No licenses found. Generate your first license.
                    </td>
                  </tr>
                ) : (
                  licenses.map((license, idx) => (
                    <tr key={idx} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-2">
                        <div className="flex items-center gap-2">
                          <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                            {license.license_key_masked || license.license_key?.substring(0, 15) + '...'}
                          </code>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => copyToClipboard(license.license_key)}
                          >
                            <Copy className="w-3 h-3" />
                          </Button>
                        </div>
                      </td>
                      <td className="py-3 px-2">
                        <Badge variant="outline" className={
                          license.company_type === 'private_equity' 
                            ? 'border-blue-500 text-blue-600' 
                            : 'border-teal-500 text-teal-600'
                        }>
                          {license.company_type === 'private_equity' ? 'PE' : 'FI'}
                        </Badge>
                      </td>
                      <td className="py-3 px-2">{license.company_name}</td>
                      <td className="py-3 px-2">{getStatusBadge(license.status)}</td>
                      <td className="py-3 px-2">{license.duration_days} days</td>
                      <td className="py-3 px-2">
                        <span className="text-gray-600">{license.features?.length || 0} features</span>
                      </td>
                      <td className="py-3 px-2 text-xs text-gray-500">
                        {license.created_at ? new Date(license.created_at).toLocaleDateString() : '-'}
                      </td>
                      <td className="py-3 px-2">
                        <div className="flex gap-1">
                          {license.is_active && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-500 hover:text-red-700"
                              onClick={() => handleRevokeLicense(license.license_key)}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      
      {/* Generate License Dialog */}
      <Dialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle className="flex items-center gap-2">
              <Key className="w-5 h-5 text-blue-600" />
              Generate New License
            </DialogTitle>
            <DialogDescription>
              Configure granular permissions for the license
            </DialogDescription>
          </DialogHeader>
          
          {generatedKey ? (
            // Show generated key
            <div className="py-6 space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-green-700 mb-2">
                  <CheckCircle2 className="w-5 h-5" />
                  <span className="font-medium">License Generated Successfully!</span>
                </div>
                <div className="bg-white rounded border p-3 font-mono text-center text-lg">
                  {generatedKey.key}
                </div>
                <Button
                  variant="outline"
                  className="w-full mt-3"
                  onClick={() => copyToClipboard(generatedKey.key)}
                >
                  <Copy className="w-4 h-4 mr-2" />
                  Copy License Key
                </Button>
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Company Type:</span>
                  <span className="ml-2 font-medium">{generatedKey.company_type}</span>
                </div>
                <div>
                  <span className="text-gray-500">Duration:</span>
                  <span className="ml-2 font-medium">{generatedKey.duration_days} days</span>
                </div>
                <div>
                  <span className="text-gray-500">Expires:</span>
                  <span className="ml-2 font-medium">
                    {new Date(generatedKey.expires_at).toLocaleDateString()}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Features:</span>
                  <span className="ml-2 font-medium">{generatedKey.features?.length || 0}</span>
                </div>
              </div>
              
              <DialogFooter>
                <Button onClick={() => setGenerateDialogOpen(false)}>Close</Button>
              </DialogFooter>
            </div>
          ) : (
            // License configuration form
            <div className="flex-1 overflow-y-auto">
              <Tabs defaultValue="basic" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="basic">Basic</TabsTrigger>
                  <TabsTrigger value="features">Features</TabsTrigger>
                  <TabsTrigger value="limits">Usage Limits</TabsTrigger>
                </TabsList>
                
                <TabsContent value="basic" className="space-y-4 mt-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Company Type</Label>
                      <Select
                        value={newLicense.company_type}
                        onValueChange={(value) => setNewLicense(prev => ({ ...prev, company_type: value }))}
                      >
                        <SelectTrigger data-testid="company-type-select">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="private_equity">Private Equity</SelectItem>
                          <SelectItem value="fixed_income">Fixed Income</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Company Name</Label>
                      <Input
                        value={newLicense.company_name}
                        onChange={(e) => setNewLicense(prev => ({ ...prev, company_name: e.target.value }))}
                        data-testid="company-name-input"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Duration (Days)</Label>
                      <Input
                        type="number"
                        min={1}
                        max={3650}
                        value={newLicense.duration_days}
                        onChange={(e) => setNewLicense(prev => ({ ...prev, duration_days: parseInt(e.target.value) || 365 }))}
                        data-testid="duration-input"
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Modules</Label>
                    <div className="flex gap-4">
                      {Object.entries(definitions.modules).map(([key, module]) => (
                        <div key={key} className="flex items-center gap-2">
                          <Switch
                            checked={newLicense.modules.includes(key)}
                            onCheckedChange={() => toggleModule(key)}
                          />
                          <Label className="font-normal">{module.name}</Label>
                        </div>
                      ))}
                    </div>
                  </div>
                </TabsContent>
                
                <TabsContent value="features" className="mt-4">
                  <div className="flex justify-between mb-4">
                    <span className="text-sm text-gray-500">
                      {newLicense.features.length} of {Object.keys(definitions.features).length} features selected
                    </span>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={selectAllFeatures}>
                        Select All
                      </Button>
                      <Button variant="outline" size="sm" onClick={clearAllFeatures}>
                        Clear All
                      </Button>
                    </div>
                  </div>
                  
                  <ScrollArea className="h-[300px]">
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(definitions.features).map(([key, feature]) => {
                        const IconComponent = featureIcons[key] || Package;
                        return (
                          <div
                            key={key}
                            className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                              newLicense.features.includes(key)
                                ? 'bg-blue-50 border-blue-200'
                                : 'bg-white border-gray-200 hover:bg-gray-50'
                            }`}
                            onClick={() => toggleFeature(key)}
                          >
                            <Switch
                              checked={newLicense.features.includes(key)}
                              onCheckedChange={() => toggleFeature(key)}
                            />
                            <IconComponent className="w-4 h-4 text-gray-500" />
                            <div className="flex-1">
                              <p className="text-sm font-medium">{feature.name}</p>
                              <p className="text-xs text-gray-400">{feature.module}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </ScrollArea>
                </TabsContent>
                
                <TabsContent value="limits" className="space-y-4 mt-4">
                  <p className="text-sm text-gray-500 mb-4">
                    Set usage limits (-1 for unlimited)
                  </p>
                  
                  <div className="grid grid-cols-2 gap-4">
                    {Object.entries(definitions.usage_limits).map(([key, limit]) => (
                      <div key={key} className="space-y-2">
                        <Label>{limit.name}</Label>
                        <Input
                          type="number"
                          min={-1}
                          placeholder={`Default: ${limit.default}`}
                          value={newLicense.usage_limits[key] || ''}
                          onChange={(e) => setNewLicense(prev => ({
                            ...prev,
                            usage_limits: {
                              ...prev.usage_limits,
                              [key]: parseInt(e.target.value) || limit.default
                            }
                          }))}
                        />
                        <p className="text-xs text-gray-400">{limit.description}</p>
                      </div>
                    ))}
                  </div>
                </TabsContent>
              </Tabs>
              
              <DialogFooter className="mt-6">
                <Button variant="outline" onClick={() => setGenerateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleGenerateLicense} disabled={generating}>
                  {generating ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Key className="w-4 h-4 mr-2" />
                      Generate License
                    </>
                  )}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Activate License Dialog */}
      <Dialog open={activateDialogOpen} onOpenChange={setActivateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Unlock className="w-5 h-5 text-green-600" />
              Activate License
            </DialogTitle>
            <DialogDescription>
              Enter a license key to activate it for the system
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>License Key</Label>
              <Input
                placeholder="PRIV-PE-XXXX-XXXX-XXXX"
                value={activateKey}
                onChange={(e) => setActivateKey(e.target.value.toUpperCase())}
                className="font-mono"
                data-testid="activate-key-input"
              />
              <p className="text-xs text-gray-500">
                Format: PRIV-PE-XXXX-XXXX-XXXX (for Private Equity) or PRIV-FI-XXXX-XXXX-XXXX (for Fixed Income)
              </p>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setActivateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleActivateLicense} disabled={activating}>
              {activating ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Activating...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Activate
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default LicenseManagement;
