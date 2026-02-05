import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '../utils/api';
import { useProtectedPage } from '../hooks/useProtectedPage';
import { 
  MessageCircle, RefreshCw, Plus, Send, Edit, Trash2,
  Phone, CheckCircle, XCircle, Clock, Users, Building2, UserCheck,
  Smartphone, Link2, Unlink, AlertTriangle, History, Settings, Key
} from 'lucide-react';

const WhatsAppNotifications = () => {
  const [config, setConfig] = useState(null);
  const [templates, setTemplates] = useState({ local_templates: [], wati_templates: [] });
  const [messages, setMessages] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Wati Config state
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [watiEndpoint, setWatiEndpoint] = useState('');
  const [watiToken, setWatiToken] = useState('');
  const [connecting, setConnecting] = useState(false);
  
  // Send message state
  const [sendDialogOpen, setSendDialogOpen] = useState(false);
  const [sendPhone, setSendPhone] = useState('');
  const [sendMessage, setSendMessage] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [sending, setSending] = useState(false);
  
  // Template state
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [templateForm, setTemplateForm] = useState({
    name: '',
    category: 'custom',
    message_template: '',
    variables: [],
    recipient_types: []
  });

  // Check for any WhatsApp permission to access the page
  const { isLoading, isAuthorized, hasPermission: checkPerm } = useProtectedPage({
    allowIf: ({ isPELevel, hasPermission }) => {
      if (isPELevel) return true;
      const waPermissions = ['notifications.whatsapp_view', 'notifications.whatsapp_connect', 
                            'notifications.whatsapp_templates', 'notifications.whatsapp_send',
                            'notifications.whatsapp_bulk', 'notifications.whatsapp_history'];
      return waPermissions.some(p => hasPermission(p));
    },
    deniedMessage: 'Access denied. You need WhatsApp permissions.'
  });
  
  // Individual permission checks
  const canConnect = checkPerm('notifications.whatsapp_connect');
  const canManageTemplates = checkPerm('notifications.whatsapp_templates');
  const canSend = checkPerm('notifications.whatsapp_send');
  const canBulkSend = checkPerm('notifications.whatsapp_bulk');
  const canViewHistory = checkPerm('notifications.whatsapp_history');

  useEffect(() => {
    if (!isAuthorized) return;
    fetchData();
  }, [isAuthorized]);

  const fetchData = async () => {
    try {
      const [configRes, templatesRes, messagesRes, statsRes] = await Promise.all([
        api.get('/whatsapp/config'),
        api.get('/whatsapp/templates'),
        api.get('/whatsapp/messages'),
        api.get('/whatsapp/stats')
      ]);
      setConfig(configRes.data);
      setTemplates(templatesRes.data);
      setMessages(messagesRes.data.messages || messagesRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load WhatsApp configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleConnectWati = async () => {
    if (!watiEndpoint || !watiToken) {
      toast.error('Please enter both API endpoint and token');
      return;
    }

    setConnecting(true);
    try {
      await api.post(`/whatsapp/config?api_endpoint=${encodeURIComponent(watiEndpoint)}&api_token=${encodeURIComponent(watiToken)}`);
      toast.success('Wati.io connected successfully!');
      setShowConfigDialog(false);
      setWatiEndpoint('');
      setWatiToken('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to connect to Wati.io');
    } finally {
      setConnecting(false);
    }
  };

  const handleTestConnection = async () => {
    try {
      const response = await api.post('/whatsapp/test-connection');
      if (response.data.connected) {
        toast.success('Connection is healthy!');
      } else {
        toast.error(response.data.message || 'Connection test failed');
      }
    } catch (error) {
      toast.error('Failed to test connection');
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Are you sure you want to disconnect Wati.io?')) return;

    try {
      await api.post('/whatsapp/disconnect');
      toast.success('WhatsApp disconnected');
      fetchData();
    } catch (error) {
      toast.error('Failed to disconnect');
    }
  };

  const handleSendMessage = async () => {
    if (!sendPhone || !sendMessage) {
      toast.error('Please enter phone number and message');
      return;
    }

    setSending(true);
    try {
      await api.post('/whatsapp/send', {
        phone_number: sendPhone,
        message: sendMessage,
        template_id: selectedTemplate || null
      });
      toast.success('Message sent successfully');
      setSendDialogOpen(false);
      setSendPhone('');
      setSendMessage('');
      setSelectedTemplate('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const handleSaveTemplate = async () => {
    if (!templateForm.name || !templateForm.message_template) {
      toast.error('Please fill in required fields');
      return;
    }

    try {
      if (editingTemplate) {
        await api.put(`/whatsapp/templates/${editingTemplate.id}`, templateForm);
        toast.success('Template updated');
      } else {
        await api.post('/whatsapp/templates', templateForm);
        toast.success('Template created');
      }
      setTemplateDialogOpen(false);
      setEditingTemplate(null);
      setTemplateForm({ name: '', category: 'custom', message_template: '', variables: [], recipient_types: [] });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save template');
    }
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!window.confirm('Are you sure you want to delete this template?')) return;

    try {
      await api.delete(`/whatsapp/templates/${templateId}`);
      toast.success('Template deleted');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete template');
    }
  };

  const openEditTemplate = (template) => {
    setEditingTemplate(template);
    setTemplateForm({
      name: template.name,
      category: template.category,
      message_template: template.message_template,
      variables: template.variables || [],
      recipient_types: template.recipient_types || []
    });
    setTemplateDialogOpen(true);
  };

  const applyTemplate = (template) => {
    setSelectedTemplate(template.id);
    setSendMessage(template.message_template);
  };

  const getCategoryColor = (category) => {
    const colors = {
      booking: 'bg-blue-100 text-blue-800',
      payment: 'bg-green-100 text-green-800',
      dp_transfer: 'bg-purple-100 text-purple-800',
      alert: 'bg-orange-100 text-orange-800',
      custom: 'bg-gray-100 text-gray-800'
    };
    return colors[category] || colors.custom;
  };

  const getRecipientIcon = (type) => {
    const icons = {
      client: <Users className="h-4 w-4" />,
      user: <UserCheck className="h-4 w-4" />,
      bp: <Building2 className="h-4 w-4" />,
      rp: <UserCheck className="h-4 w-4" />
    };
    return icons[type] || <Users className="h-4 w-4" />;
  };

  if (isLoading || loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  const isConnected = config?.status === 'connected';
  const allTemplates = templates.local_templates || [];

  return (
    <div className="space-y-6" data-testid="whatsapp-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <MessageCircle className="w-7 h-7 text-green-600" />
            WhatsApp Notifications
          </h1>
          <p className="text-muted-foreground">Manage Wati.io WhatsApp integration and message templates</p>
        </div>
        <div className="flex gap-2">
          {isConnected && canSend && (
            <Button onClick={() => setSendDialogOpen(true)} className="bg-green-600 hover:bg-green-700">
              <Send className="w-4 h-4 mr-2" />
              Send Message
            </Button>
          )}
        </div>
      </div>

      {/* Connection Status Card */}
      <Card className={isConnected ? 'border-green-200 bg-green-50/50' : 'border-orange-200 bg-orange-50/50'}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-full ${isConnected ? 'bg-green-100' : 'bg-orange-100'}`}>
                {isConnected ? (
                  <Smartphone className="w-8 h-8 text-green-600" />
                ) : (
                  <Settings className="w-8 h-8 text-orange-600" />
                )}
              </div>
              <div>
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  {isConnected ? (
                    <>
                      <CheckCircle className="w-5 h-5 text-green-600" />
                      Wati.io Connected
                    </>
                  ) : (
                    <>
                      <XCircle className="w-5 h-5 text-orange-600" />
                      Not Connected
                    </>
                  )}
                </h3>
                {isConnected ? (
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>API Endpoint: {config.api_endpoint}</p>
                    <p>Token: {config.api_token_masked}</p>
                    <p>Connected: {new Date(config.connected_at).toLocaleString()}</p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Configure your Wati.io API credentials to start sending WhatsApp messages
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isConnected && canConnect && (
                <>
                  <Button variant="outline" onClick={handleTestConnection}>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Test Connection
                  </Button>
                  <Button variant="destructive" onClick={handleDisconnect}>
                    <Unlink className="w-4 h-4 mr-2" />
                    Disconnect
                  </Button>
                </>
              )}
              {!isConnected && canConnect && (
                <Button onClick={() => setShowConfigDialog(true)} className="bg-green-600 hover:bg-green-700">
                  <Key className="w-4 h-4 mr-2" />
                  Configure Wati.io
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-green-600">{stats.total_messages}</p>
                <p className="text-sm text-muted-foreground">Total Messages</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-blue-600">{stats.sent}</p>
                <p className="text-sm text-muted-foreground">Sent</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-red-600">{stats.failed}</p>
                <p className="text-sm text-muted-foreground">Failed</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-purple-600">{stats.today_messages}</p>
                <p className="text-sm text-muted-foreground">Today</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content Tabs */}
      <Tabs defaultValue="templates" className="space-y-4">
        <TabsList>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          {canViewHistory && <TabsTrigger value="history">Message History</TabsTrigger>}
        </TabsList>

        <TabsContent value="templates">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Message Templates</CardTitle>
                <CardDescription>Pre-defined message templates for common notifications</CardDescription>
              </div>
              {canManageTemplates && (
                <Button onClick={() => {
                  setEditingTemplate(null);
                  setTemplateForm({ name: '', category: 'custom', message_template: '', variables: [], recipient_types: [] });
                  setTemplateDialogOpen(true);
                }}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Template
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {allTemplates.map((template) => (
                  <div key={template.id} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-medium">{template.name}</h4>
                          <Badge className={getCategoryColor(template.category)}>{template.category}</Badge>
                          {template.is_system && <Badge variant="outline">System</Badge>}
                        </div>
                        <p className="text-sm text-muted-foreground whitespace-pre-line mb-2">
                          {template.message_template}
                        </p>
                        {template.variables?.length > 0 && (
                          <div className="flex gap-1 flex-wrap">
                            {template.variables.map((v, i) => (
                              <Badge key={i} variant="secondary" className="text-xs">
                                {`{{${v}}}`}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex gap-2">
                        {canSend && isConnected && (
                          <Button variant="ghost" size="sm" onClick={() => applyTemplate(template)}>
                            <Send className="w-4 h-4" />
                          </Button>
                        )}
                        {canManageTemplates && !template.is_system && (
                          <>
                            <Button variant="ghost" size="sm" onClick={() => openEditTemplate(template)}>
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteTemplate(template.id)}>
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {allTemplates.length === 0 && (
                  <p className="text-center text-muted-foreground py-8">No templates found</p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="w-5 h-5" />
                Message History
              </CardTitle>
              <CardDescription>Recent WhatsApp messages sent through the system</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Phone</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Sent By</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(Array.isArray(messages) ? messages : []).slice(0, 50).map((msg) => (
                    <TableRow key={msg.id}>
                      <TableCell className="font-mono">{msg.phone_number}</TableCell>
                      <TableCell className="max-w-xs truncate">{msg.message || msg.template_name || '-'}</TableCell>
                      <TableCell>
                        <Badge variant={msg.status === 'sent' ? 'default' : msg.status === 'failed' ? 'destructive' : 'secondary'}>
                          {msg.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{msg.sent_by_name}</TableCell>
                      <TableCell>{new Date(msg.sent_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                  {(!messages || messages.length === 0) && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                        No messages sent yet
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Wati.io Config Dialog */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Key className="w-5 h-5" />
              Configure Wati.io API
            </DialogTitle>
            <DialogDescription>
              Enter your Wati.io API credentials to enable WhatsApp messaging
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
              <p className="font-medium text-blue-800 mb-1">How to get credentials:</p>
              <ol className="list-decimal list-inside text-blue-700 space-y-1">
                <li>Log in to your Wati.io dashboard</li>
                <li>Navigate to More → API Docs</li>
                <li>Copy your API Endpoint and Token</li>
              </ol>
            </div>
            <div>
              <Label htmlFor="watiEndpoint">API Endpoint *</Label>
              <Input
                id="watiEndpoint"
                placeholder="https://live-mt-server.wati.io/xxxxx"
                value={watiEndpoint}
                onChange={(e) => setWatiEndpoint(e.target.value)}
                data-testid="wati-endpoint-input"
              />
              <p className="text-xs text-muted-foreground mt-1">Your Wati.io API endpoint URL</p>
            </div>
            <div>
              <Label htmlFor="watiToken">API Token *</Label>
              <Input
                id="watiToken"
                type="password"
                placeholder="Enter your API token"
                value={watiToken}
                onChange={(e) => setWatiToken(e.target.value)}
                data-testid="wati-token-input"
              />
              <p className="text-xs text-muted-foreground mt-1">Your Wati.io Bearer token</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigDialog(false)}>Cancel</Button>
            <Button onClick={handleConnectWati} disabled={connecting} className="bg-green-600 hover:bg-green-700">
              {connecting ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Link2 className="w-4 h-4 mr-2" />}
              Connect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Send Message Dialog */}
      <Dialog open={sendDialogOpen} onOpenChange={setSendDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send WhatsApp Message</DialogTitle>
            <DialogDescription>Send a message via Wati.io</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Phone Number *</Label>
              <Input
                placeholder="10-digit mobile number"
                value={sendPhone}
                onChange={(e) => setSendPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                data-testid="send-phone-input"
              />
              <p className="text-xs text-muted-foreground mt-1">Enter 10-digit Indian mobile number</p>
            </div>
            <div>
              <Label>Message *</Label>
              <Textarea
                placeholder="Type your message..."
                rows={4}
                value={sendMessage}
                onChange={(e) => setSendMessage(e.target.value)}
                data-testid="send-message-input"
              />
            </div>
            {allTemplates.length > 0 && (
              <div>
                <Label>Use Template</Label>
                <Select value={selectedTemplate} onValueChange={(v) => {
                  setSelectedTemplate(v);
                  const tpl = allTemplates.find(t => t.id === v);
                  if (tpl) setSendMessage(tpl.message_template);
                }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a template" />
                  </SelectTrigger>
                  <SelectContent>
                    {allTemplates.map((t) => (
                      <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSendDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSendMessage} disabled={sending} className="bg-green-600 hover:bg-green-700">
              {sending ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              Send
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Template Dialog */}
      <Dialog open={templateDialogOpen} onOpenChange={setTemplateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingTemplate ? 'Edit Template' : 'Create Template'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Template Name *</Label>
              <Input
                value={templateForm.name}
                onChange={(e) => setTemplateForm({...templateForm, name: e.target.value})}
                placeholder="e.g., Payment Confirmation"
              />
            </div>
            <div>
              <Label>Category</Label>
              <Select value={templateForm.category} onValueChange={(v) => setTemplateForm({...templateForm, category: v})}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="booking">Booking</SelectItem>
                  <SelectItem value="payment">Payment</SelectItem>
                  <SelectItem value="dp_transfer">DP Transfer</SelectItem>
                  <SelectItem value="alert">Alert</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Message Template *</Label>
              <Textarea
                value={templateForm.message_template}
                onChange={(e) => setTemplateForm({...templateForm, message_template: e.target.value})}
                rows={6}
                placeholder="Dear {{client_name}}, your booking #{{booking_number}} has been confirmed..."
              />
              <p className="text-xs text-muted-foreground mt-1">
                Use {`{{variable_name}}`} for dynamic content
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTemplateDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveTemplate}>Save Template</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default WhatsAppNotifications;
