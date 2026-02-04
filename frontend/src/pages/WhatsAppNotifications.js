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
  MessageCircle, QrCode, RefreshCw, Plus, Send, Edit, Trash2,
  Phone, CheckCircle, XCircle, Clock, Users, Building2, UserCheck,
  Smartphone, Link2, Unlink, AlertTriangle, History
} from 'lucide-react';

const WhatsAppNotifications = () => {
  const [config, setConfig] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [messages, setMessages] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // QR Code state
  const [qrData, setQrData] = useState(null);
  const [showQrDialog, setShowQrDialog] = useState(false);
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
      setMessages(messagesRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load WhatsApp configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateQR = async () => {
    setConnecting(true);
    try {
      const response = await api.get('/whatsapp/qr-code');
      setQrData(response.data);
      setShowQrDialog(true);
    } catch (error) {
      toast.error('Failed to generate QR code');
    } finally {
      setConnecting(false);
    }
  };

  const handleSimulateConnect = async () => {
    // For demo purposes - simulate WhatsApp connection
    const phone = prompt('Enter phone number to simulate connection (e.g., +919876543210):');
    if (!phone) return;

    try {
      await api.post(`/whatsapp/simulate-connect?session_id=${qrData.session_id}&phone_number=${encodeURIComponent(phone)}`);
      toast.success('WhatsApp connected successfully!');
      setShowQrDialog(false);
      setQrData(null);
      fetchData();
    } catch (error) {
      toast.error('Failed to connect WhatsApp');
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Are you sure you want to disconnect WhatsApp?')) return;

    try {
      await api.post('/whatsapp/disconnect');
      toast.success('WhatsApp disconnected');
      fetchData();
    } catch (error) {
      toast.error('Failed to disconnect');
    }
  };

  const handleToggleEnabled = async (enabled) => {
    try {
      await api.post(`/whatsapp/config?enabled=${enabled}`);
      toast.success(`WhatsApp notifications ${enabled ? 'enabled' : 'disabled'}`);
      fetchData();
    } catch (error) {
      toast.error('Failed to update configuration');
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

  return (
    <div className="space-y-6" data-testid="whatsapp-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <MessageCircle className="w-7 h-7 text-green-600" />
            WhatsApp Notifications
          </h1>
          <p className="text-muted-foreground">Manage WhatsApp integration and message templates</p>
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

      {/* Connection Status */}
      <Card className={isConnected ? 'border-green-200 bg-green-50/50' : 'border-orange-200 bg-orange-50/50'}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-full ${isConnected ? 'bg-green-100' : 'bg-orange-100'}`}>
                {isConnected ? (
                  <Smartphone className="w-8 h-8 text-green-600" />
                ) : (
                  <QrCode className="w-8 h-8 text-orange-600" />
                )}
              </div>
              <div>
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  {isConnected ? (
                    <>
                      <CheckCircle className="w-5 h-5 text-green-600" />
                      Connected
                    </>
                  ) : (
                    <>
                      <XCircle className="w-5 h-5 text-orange-600" />
                      Not Connected
                    </>
                  )}
                </h3>
                {isConnected ? (
                  <p className="text-sm text-muted-foreground">
                    Phone: {config.phone_number} | Connected: {new Date(config.connected_at).toLocaleString()}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Scan QR code with your WhatsApp to connect
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-4">
              {isConnected && (
                <div className="flex items-center gap-2">
                  <Label>Notifications</Label>
                  <Switch
                    checked={config?.enabled}
                    onCheckedChange={handleToggleEnabled}
                  />
                </div>
              )}
              {isConnected ? (
                <Button variant="destructive" onClick={handleDisconnect}>
                  <Unlink className="w-4 h-4 mr-2" />
                  Disconnect
                </Button>
              ) : (
                <Button onClick={handleGenerateQR} disabled={connecting} className="bg-green-600 hover:bg-green-700">
                  {connecting ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <QrCode className="w-4 h-4 mr-2" />}
                  Connect WhatsApp
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
                <p className="text-3xl font-bold text-blue-600">{stats.today_messages}</p>
                <p className="text-sm text-muted-foreground">Today</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-emerald-600">{stats.by_status?.sent || 0}</p>
                <p className="text-sm text-muted-foreground">Sent</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-red-600">{stats.by_status?.failed || 0}</p>
                <p className="text-sm text-muted-foreground">Failed</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="templates">
        <TabsList>
          <TabsTrigger value="templates">Message Templates</TabsTrigger>
          <TabsTrigger value="history">Message History</TabsTrigger>
        </TabsList>

        <TabsContent value="templates" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Message Templates</h3>
            <Button onClick={() => {
              setEditingTemplate(null);
              setTemplateForm({ name: '', category: 'custom', message_template: '', variables: [], recipient_types: [] });
              setTemplateDialogOpen(true);
            }}>
              <Plus className="w-4 h-4 mr-2" />
              Create Template
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((template) => (
              <Card key={template.id} className="relative">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base">{template.name}</CardTitle>
                      <Badge className={getCategoryColor(template.category)}>
                        {template.category}
                      </Badge>
                    </div>
                    {!template.is_system && (
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" onClick={() => openEditTemplate(template)}>
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDeleteTemplate(template.id)}>
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground whitespace-pre-line line-clamp-4">
                    {template.message_template}
                  </p>
                  <div className="flex gap-1 mt-2">
                    {template.recipient_types?.map((type) => (
                      <Badge key={type} variant="outline" className="text-xs">
                        {getRecipientIcon(type)}
                        <span className="ml-1">{type}</span>
                      </Badge>
                    ))}
                  </div>
                  {template.is_system && (
                    <Badge variant="secondary" className="mt-2">System Template</Badge>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="w-5 h-5" />
                Recent Messages
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Phone</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Sent By</TableHead>
                    <TableHead>Sent At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {messages.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground">
                        No messages sent yet
                      </TableCell>
                    </TableRow>
                  ) : (
                    messages.map((msg) => (
                      <TableRow key={msg.id}>
                        <TableCell className="font-mono">{msg.phone_number}</TableCell>
                        <TableCell className="max-w-xs truncate">{msg.message}</TableCell>
                        <TableCell>
                          <Badge className={
                            msg.status === 'sent' ? 'bg-green-100 text-green-800' :
                            msg.status === 'failed' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                          }>
                            {msg.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{msg.sent_by_name}</TableCell>
                        <TableCell>{new Date(msg.sent_at).toLocaleString()}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* QR Code Dialog */}
      <Dialog open={showQrDialog} onOpenChange={setShowQrDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <QrCode className="w-5 h-5 text-green-600" />
              Connect WhatsApp
            </DialogTitle>
            <DialogDescription>
              Scan this QR code with your WhatsApp mobile app
            </DialogDescription>
          </DialogHeader>
          
          {qrData && (
            <div className="space-y-4">
              <div className="flex justify-center p-4 bg-white rounded-lg">
                <img src={qrData.qr_code} alt="WhatsApp QR Code" className="w-64 h-64" />
              </div>
              
              <div className="space-y-2">
                {qrData.instructions?.map((instruction, idx) => (
                  <p key={idx} className="text-sm text-muted-foreground">{instruction}</p>
                ))}
              </div>

              <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                <p className="text-sm text-yellow-800 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  QR code expires in {qrData.expires_in} seconds
                </p>
              </div>

              {/* Demo button - in production, connection would happen automatically */}
              <Button onClick={handleSimulateConnect} className="w-full bg-green-600 hover:bg-green-700">
                <Link2 className="w-4 h-4 mr-2" />
                Simulate Connection (Demo)
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Send Message Dialog */}
      <Dialog open={sendDialogOpen} onOpenChange={setSendDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Send WhatsApp Message</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>Phone Number</Label>
              <Input
                value={sendPhone}
                onChange={(e) => setSendPhone(e.target.value)}
                placeholder="+919876543210"
              />
            </div>

            <div>
              <Label>Template (Optional)</Label>
              <Select value={selectedTemplate} onValueChange={(v) => {
                const template = templates.find(t => t.id === v);
                if (template) applyTemplate(template);
              }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a template..." />
                </SelectTrigger>
                <SelectContent>
                  {templates.map((t) => (
                    <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Message</Label>
              <Textarea
                value={sendMessage}
                onChange={(e) => setSendMessage(e.target.value)}
                placeholder="Enter your message..."
                className="min-h-[150px]"
              />
            </div>
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
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingTemplate ? 'Edit Template' : 'Create Template'}</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>Template Name</Label>
              <Input
                value={templateForm.name}
                onChange={(e) => setTemplateForm({...templateForm, name: e.target.value})}
                placeholder="My Custom Template"
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
              <Label>Message Template</Label>
              <Textarea
                value={templateForm.message_template}
                onChange={(e) => setTemplateForm({...templateForm, message_template: e.target.value})}
                placeholder="Dear {{client_name}}, your booking #{{booking_number}} has been confirmed..."
                className="min-h-[150px]"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Use {'{{variable_name}}'} for dynamic content
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setTemplateDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveTemplate}>
              {editingTemplate ? 'Update' : 'Create'} Template
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default WhatsAppNotifications;
