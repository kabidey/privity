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
  Smartphone, Link2, Unlink, AlertTriangle, History, Settings, Key,
  MessageSquare, ArrowLeft, Copy, Info, Inbox
} from 'lucide-react';

const WhatsAppNotifications = () => {
  const [config, setConfig] = useState(null);
  const [templates, setTemplates] = useState({ local_templates: [], wati_templates: [] });
  const [messages, setMessages] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Automation state
  const [automationConfig, setAutomationConfig] = useState({
    payment_reminder_enabled: false,
    payment_reminder_days: 3,
    document_reminder_enabled: false,
    dp_ready_notification_enabled: true
  });
  const [automationLogs, setAutomationLogs] = useState([]);
  const [broadcasts, setBroadcasts] = useState([]);
  const [savingAutomation, setSavingAutomation] = useState(false);
  const [runningAutomation, setRunningAutomation] = useState(null);
  
  // Bulk broadcast state
  const [broadcastDialogOpen, setBroadcastDialogOpen] = useState(false);
  const [broadcastForm, setBroadcastForm] = useState({
    message: '',
    recipient_type: 'all_clients',
    broadcast_name: ''
  });
  const [sendingBroadcast, setSendingBroadcast] = useState(false);
  
  // Wati Config state
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [watiEndpoint, setWatiEndpoint] = useState('');
  const [watiToken, setWatiToken] = useState('');
  const [watiApiVersion, setWatiApiVersion] = useState('v1');
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

  // Conversation state for two-way communication
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [conversationMessages, setConversationMessages] = useState([]);
  const [replyMessage, setReplyMessage] = useState('');
  const [sendingReply, setSendingReply] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [webhookInfo, setWebhookInfo] = useState(null);

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

  // Permission checks
  const canConfig = checkPerm('notifications.whatsapp_config');

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
      
      // Fetch automation data if user has permission
      if (canConfig) {
        try {
          const [automationRes, logsRes, broadcastsRes] = await Promise.all([
            api.get('/whatsapp/automation/config'),
            api.get('/whatsapp/automation/logs?limit=20'),
            api.get('/whatsapp/broadcasts?limit=20')
          ]);
          setAutomationConfig(automationRes.data);
          setAutomationLogs(logsRes.data.logs || []);
          setBroadcasts(broadcastsRes.data.broadcasts || []);
        } catch (e) {
          console.log('Automation data not available');
        }
      }
    } catch (error) {
      toast.error('Failed to load WhatsApp configuration');
    } finally {
      setLoading(false);
    }
  };

  // Fetch conversations for two-way communication
  const fetchConversations = async () => {
    setLoadingConversations(true);
    try {
      const [convRes, webhookRes] = await Promise.all([
        api.get('/whatsapp/conversations'),
        api.get('/whatsapp/webhook/info').catch(() => ({ data: null }))
      ]);
      setConversations(convRes.data.conversations || []);
      if (webhookRes.data) {
        setWebhookInfo(webhookRes.data);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoadingConversations(false);
    }
  };

  // Load conversation thread
  const loadConversationThread = async (phoneNumber) => {
    try {
      const res = await api.get(`/whatsapp/conversations/${phoneNumber}`);
      setSelectedConversation(res.data);
      setConversationMessages(res.data.messages || []);
      // Refresh conversation list to update unread counts
      fetchConversations();
    } catch (error) {
      toast.error('Failed to load conversation');
    }
  };

  // Send reply in conversation
  const handleSendReply = async () => {
    if (!replyMessage.trim() || !selectedConversation) return;
    
    setSendingReply(true);
    try {
      const res = await api.post(`/whatsapp/conversations/${selectedConversation.phone_number}/reply`, {
        phone_number: selectedConversation.phone_number,
        message: replyMessage
      });
      
      if (res.data.success) {
        toast.success('Reply sent!');
        setReplyMessage('');
        // Reload conversation
        loadConversationThread(selectedConversation.phone_number);
      } else {
        toast.error(res.data.message || 'Failed to send reply');
        if (res.data.hint) {
          toast.info(res.data.hint);
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send reply');
    } finally {
      setSendingReply(false);
    }
  };

  // Copy webhook URL
  const copyWebhookUrl = () => {
    const url = webhookInfo?.webhook_url || `${window.location.origin}/api/whatsapp/webhook`;
    navigator.clipboard.writeText(url);
    toast.success('Webhook URL copied to clipboard!');
  };

  const handleConnectWati = async () => {
    if (!watiEndpoint || !watiToken) {
      toast.error('Please enter both API endpoint and token');
      return;
    }

    setConnecting(true);
    try {
      const response = await api.post(`/whatsapp/config?api_endpoint=${encodeURIComponent(watiEndpoint)}&api_token=${encodeURIComponent(watiToken)}&api_version=${watiApiVersion}`);
      const detectedVersion = response.data?.api_version || watiApiVersion;
      toast.success(`Wati.io connected successfully! (API ${detectedVersion})`);
      setShowConfigDialog(false);
      setWatiEndpoint('');
      setWatiToken('');
      setWatiApiVersion('v1');
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

  // Automation handlers
  const handleSaveAutomationConfig = async () => {
    setSavingAutomation(true);
    try {
      await api.put('/whatsapp/automation/config', automationConfig);
      toast.success('Automation settings saved');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save automation settings');
    } finally {
      setSavingAutomation(false);
    }
  };

  const handleRunAutomation = async (type) => {
    setRunningAutomation(type);
    try {
      let endpoint = '';
      switch (type) {
        case 'payment':
          endpoint = '/whatsapp/automation/payment-reminders';
          break;
        case 'document':
          endpoint = '/whatsapp/automation/document-reminders';
          break;
        case 'dp_ready':
          endpoint = '/whatsapp/automation/dp-ready-notifications';
          break;
        case 'all':
          endpoint = '/whatsapp/automation/run-all';
          break;
        default:
          return;
      }
      const res = await api.post(endpoint);
      toast.success(`Automation completed: ${res.data.success || 0} sent, ${res.data.failed || 0} failed`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Automation failed');
    } finally {
      setRunningAutomation(null);
    }
  };

  const handleSendBroadcast = async () => {
    if (!broadcastForm.message.trim()) {
      toast.error('Please enter a message');
      return;
    }
    
    setSendingBroadcast(true);
    try {
      const res = await api.post('/whatsapp/automation/bulk-broadcast', {
        message: broadcastForm.message,
        recipient_type: broadcastForm.recipient_type,
        broadcast_name: broadcastForm.broadcast_name || undefined
      });
      toast.success(`Broadcast sent: ${res.data.success || 0} delivered, ${res.data.failed || 0} failed`);
      setBroadcastDialogOpen(false);
      setBroadcastForm({ message: '', recipient_type: 'all_clients', broadcast_name: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Broadcast failed');
    } finally {
      setSendingBroadcast(false);
    }
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
                    <p>API Version: <Badge variant="outline" className="ml-1">{config.api_version || config.api_version_detected || 'v1'}</Badge></p>
                    <p>Token: {config.api_token_masked}</p>
                    <p>Connected: {new Date(config.connected_at).toLocaleString()}</p>
                    <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-950 rounded text-xs">
                      <p className="font-semibold text-blue-700 dark:text-blue-300">Webhook URL (configure in Wati dashboard):</p>
                      <code className="text-blue-600 dark:text-blue-400 break-all">{window.location.origin}/api/whatsapp/webhook</code>
                    </div>
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
      <Tabs defaultValue="conversations" className="space-y-4" onValueChange={(val) => {
        if (val === 'conversations') fetchConversations();
      }}>
        <TabsList>
          <TabsTrigger value="conversations" className="flex items-center gap-2">
            <Inbox className="w-4 h-4" />
            Conversations
            {conversations.filter(c => c.unread_count > 0).length > 0 && (
              <Badge variant="destructive" className="ml-1 h-5 w-5 p-0 text-xs flex items-center justify-center">
                {conversations.filter(c => c.unread_count > 0).length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          {canViewHistory && <TabsTrigger value="history">Message History</TabsTrigger>}
          {canConfig && <TabsTrigger value="automation">Automation</TabsTrigger>}
        </TabsList>

        {/* Conversations Tab - Two-Way Communication */}
        <TabsContent value="conversations">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Conversation List */}
            <Card className="lg:col-span-1">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Inbox</CardTitle>
                  <Button variant="ghost" size="sm" onClick={fetchConversations} disabled={loadingConversations}>
                    <RefreshCw className={`w-4 h-4 ${loadingConversations ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {/* Webhook Setup Info */}
                <div className="px-4 pb-3 border-b">
                  <div className="bg-blue-50 dark:bg-blue-950 rounded-lg p-3 text-sm">
                    <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300 font-medium mb-1">
                      <Info className="w-4 h-4" />
                      Webhook URL for Wati
                    </div>
                    <div className="flex items-center gap-2">
                      <code className="text-xs bg-white dark:bg-gray-900 px-2 py-1 rounded flex-1 truncate">
                        {webhookInfo?.webhook_url || `${window.location.origin}/api/whatsapp/webhook`}
                      </code>
                      <Button variant="ghost" size="sm" onClick={copyWebhookUrl} className="h-7 w-7 p-0">
                        <Copy className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </div>
                
                {/* Conversation List */}
                <div className="max-h-[500px] overflow-y-auto">
                  {loadingConversations ? (
                    <div className="flex items-center justify-center py-8">
                      <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : conversations.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>No conversations yet</p>
                      <p className="text-xs mt-1">Messages will appear here when customers reply</p>
                    </div>
                  ) : (
                    conversations.map((conv) => (
                      <div
                        key={conv.id || conv.phone_number}
                        className={`p-3 border-b cursor-pointer hover:bg-muted/50 transition-colors ${
                          selectedConversation?.phone_number === conv.phone_number ? 'bg-muted' : ''
                        }`}
                        onClick={() => loadConversationThread(conv.phone_number)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium truncate">
                                {conv.client_name !== 'Unknown' ? conv.client_name : conv.phone_number}
                              </span>
                              {conv.unread_count > 0 && (
                                <Badge variant="destructive" className="h-5 min-w-[20px] text-xs">
                                  {conv.unread_count}
                                </Badge>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground truncate">{conv.last_message}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {conv.last_message_at ? new Date(conv.last_message_at).toLocaleString() : ''}
                            </p>
                          </div>
                          {conv.session_active && (
                            <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
                              Active
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Conversation Thread */}
            <Card className="lg:col-span-2">
              {selectedConversation ? (
                <>
                  <CardHeader className="pb-3 border-b">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="lg:hidden"
                          onClick={() => setSelectedConversation(null)}
                        >
                          <ArrowLeft className="w-4 h-4" />
                        </Button>
                        <div>
                          <CardTitle className="text-lg flex items-center gap-2">
                            <Phone className="w-4 h-4" />
                            {selectedConversation.client_name !== 'Unknown' 
                              ? selectedConversation.client_name 
                              : selectedConversation.phone_number}
                          </CardTitle>
                          <p className="text-sm text-muted-foreground">
                            {selectedConversation.phone_number}
                            {selectedConversation.session_active && (
                              <Badge variant="outline" className="ml-2 text-xs bg-green-50 text-green-700">
                                24h Session Active
                              </Badge>
                            )}
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0">
                    {/* Messages */}
                    <div className="h-[350px] overflow-y-auto p-4 space-y-3 bg-gray-50 dark:bg-gray-900">
                      {conversationMessages.map((msg, idx) => (
                        <div
                          key={msg.id || idx}
                          className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}
                        >
                          <div
                            className={`max-w-[80%] rounded-lg px-3 py-2 ${
                              msg.direction === 'outbound'
                                ? 'bg-green-600 text-white'
                                : 'bg-white dark:bg-gray-800 border'
                            }`}
                          >
                            <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                            <div className={`text-xs mt-1 ${
                              msg.direction === 'outbound' ? 'text-green-100' : 'text-muted-foreground'
                            }`}>
                              {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                              {msg.sent_by && <span className="ml-2">• {msg.sent_by}</span>}
                              {msg.status && msg.direction === 'outbound' && (
                                <span className="ml-2">
                                  {msg.status === 'sent' && '✓'}
                                  {msg.status === 'delivered' && '✓✓'}
                                  {msg.status === 'read' && '✓✓'}
                                  {msg.status === 'failed' && '✗'}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    {/* Reply Input */}
                    <div className="p-4 border-t">
                      <div className="flex gap-2">
                        <Input
                          placeholder="Type a reply..."
                          value={replyMessage}
                          onChange={(e) => setReplyMessage(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendReply()}
                          disabled={sendingReply || !isConnected}
                          data-testid="reply-input"
                        />
                        <Button 
                          onClick={handleSendReply} 
                          disabled={!replyMessage.trim() || sendingReply || !isConnected}
                          className="bg-green-600 hover:bg-green-700"
                          data-testid="send-reply-btn"
                        >
                          {sendingReply ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : (
                            <Send className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                      {!selectedConversation.session_active && (
                        <p className="text-xs text-amber-600 mt-2">
                          ⚠️ 24-hour session may have expired. Use a template message to re-engage.
                        </p>
                      )}
                    </div>
                  </CardContent>
                </>
              ) : (
                <CardContent className="flex items-center justify-center h-[500px]">
                  <div className="text-center text-muted-foreground">
                    <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium">Select a conversation</p>
                    <p className="text-sm">Choose a conversation from the list to view messages</p>
                  </div>
                </CardContent>
              )}
            </Card>
          </div>
        </TabsContent>

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

        {/* Automation Tab */}
        {canConfig && (
          <TabsContent value="automation">
            <div className="space-y-6">
              {/* Automation Settings Card */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Settings className="w-5 h-5" />
                        Automation Settings
                      </CardTitle>
                      <CardDescription>Configure automated WhatsApp notifications</CardDescription>
                    </div>
                    <Button onClick={handleSaveAutomationConfig} disabled={savingAutomation}>
                      {savingAutomation ? (
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <CheckCircle className="w-4 h-4 mr-2" />
                      )}
                      Save Settings
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Payment Reminders */}
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-orange-500" />
                        <span className="font-medium">Payment Reminders</span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Send reminders to clients with pending payments
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <Label className="text-xs">Days overdue:</Label>
                        <Input
                          type="number"
                          min="1"
                          max="30"
                          value={automationConfig.payment_reminder_days}
                          onChange={(e) => setAutomationConfig(prev => ({
                            ...prev,
                            payment_reminder_days: parseInt(e.target.value) || 3
                          }))}
                          className="w-20 h-8"
                        />
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <Switch
                        checked={automationConfig.payment_reminder_enabled}
                        onCheckedChange={(checked) => setAutomationConfig(prev => ({
                          ...prev,
                          payment_reminder_enabled: checked
                        }))}
                      />
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleRunAutomation('payment')}
                        disabled={runningAutomation === 'payment'}
                      >
                        {runningAutomation === 'payment' ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Send className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Document Reminders */}
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-yellow-500" />
                        <span className="font-medium">Document Upload Reminders</span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Remind clients to upload missing documents (PAN, CML, Cheque)
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <Switch
                        checked={automationConfig.document_reminder_enabled}
                        onCheckedChange={(checked) => setAutomationConfig(prev => ({
                          ...prev,
                          document_reminder_enabled: checked
                        }))}
                      />
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleRunAutomation('document')}
                        disabled={runningAutomation === 'document'}
                      >
                        {runningAutomation === 'document' ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Send className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* DP Ready Notifications */}
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span className="font-medium">DP Ready Notifications</span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Notify clients when shares are ready for DP transfer
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <Switch
                        checked={automationConfig.dp_ready_notification_enabled}
                        onCheckedChange={(checked) => setAutomationConfig(prev => ({
                          ...prev,
                          dp_ready_notification_enabled: checked
                        }))}
                      />
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleRunAutomation('dp_ready')}
                        disabled={runningAutomation === 'dp_ready'}
                      >
                        {runningAutomation === 'dp_ready' ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Send className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Run All Button */}
                  <div className="flex justify-center pt-4 border-t">
                    <Button 
                      onClick={() => handleRunAutomation('all')}
                      disabled={runningAutomation === 'all'}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      {runningAutomation === 'all' ? (
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4 mr-2" />
                      )}
                      Run All Enabled Automations
                    </Button>
                  </div>

                  <p className="text-xs text-muted-foreground text-center">
                    Automations run automatically at 10:00 AM IST daily
                  </p>
                </CardContent>
              </Card>

              {/* Bulk Broadcast Card */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Users className="w-5 h-5" />
                      Bulk Broadcast
                    </CardTitle>
                    <CardDescription>Send messages to multiple recipients at once</CardDescription>
                  </div>
                  <Button onClick={() => setBroadcastDialogOpen(true)} className="bg-blue-600 hover:bg-blue-700">
                    <Send className="w-4 h-4 mr-2" />
                    New Broadcast
                  </Button>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Broadcast Name</TableHead>
                        <TableHead>Recipients</TableHead>
                        <TableHead>Success</TableHead>
                        <TableHead>Failed</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Date</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {broadcasts.map((broadcast) => (
                        <TableRow key={broadcast.id}>
                          <TableCell className="font-medium">{broadcast.name}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{broadcast.recipient_type}</Badge>
                            <span className="ml-2 text-muted-foreground">({broadcast.recipient_count})</span>
                          </TableCell>
                          <TableCell className="text-green-600">{broadcast.success_count || 0}</TableCell>
                          <TableCell className="text-red-600">{broadcast.failed_count || 0}</TableCell>
                          <TableCell>
                            <Badge variant={broadcast.status === 'completed' ? 'default' : 'secondary'}>
                              {broadcast.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{new Date(broadcast.created_at).toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                      {broadcasts.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                            No broadcasts sent yet
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              {/* Automation Logs Card */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <History className="w-5 h-5" />
                    Automation Logs
                  </CardTitle>
                  <CardDescription>Recent automation run history</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Automation Type</TableHead>
                        <TableHead>Trigger</TableHead>
                        <TableHead>Recipients</TableHead>
                        <TableHead>Success</TableHead>
                        <TableHead>Failed</TableHead>
                        <TableHead>Date</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {automationLogs.map((log) => (
                        <TableRow key={log.id}>
                          <TableCell className="font-medium">{log.automation_type}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{log.trigger_event}</Badge>
                          </TableCell>
                          <TableCell>{log.recipients_count}</TableCell>
                          <TableCell className="text-green-600">{log.success_count}</TableCell>
                          <TableCell className="text-red-600">{log.failed_count}</TableCell>
                          <TableCell>{new Date(log.run_at).toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                      {automationLogs.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                            No automation runs yet
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        )}
      </Tabs>

      {/* Wati.io Config Dialog */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="sm:max-w-md">
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
            <div>
              <Label htmlFor="watiApiVersion">API Version</Label>
              <Select value={watiApiVersion} onValueChange={setWatiApiVersion}>
                <SelectTrigger data-testid="wati-api-version-select">
                  <SelectValue placeholder="Select API version" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="v1">v1 (Standard)</SelectItem>
                  <SelectItem value="v3">v3 (Extended with bulk support)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground mt-1">System will auto-detect the best version</p>
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

      {/* Bulk Broadcast Dialog */}
      <Dialog open={broadcastDialogOpen} onOpenChange={setBroadcastDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Send Bulk Broadcast
            </DialogTitle>
            <DialogDescription>
              Send a message to multiple recipients at once
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Broadcast Name (optional)</Label>
              <Input
                placeholder="e.g., January 2026 Updates"
                value={broadcastForm.broadcast_name}
                onChange={(e) => setBroadcastForm({...broadcastForm, broadcast_name: e.target.value})}
              />
            </div>
            <div>
              <Label>Recipient Type *</Label>
              <Select 
                value={broadcastForm.recipient_type} 
                onValueChange={(v) => setBroadcastForm({...broadcastForm, recipient_type: v})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all_clients">All Clients</SelectItem>
                  <SelectItem value="all_rps">All Referral Partners</SelectItem>
                  <SelectItem value="all_bps">All Business Partners</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Message *</Label>
              <Textarea
                placeholder="Type your broadcast message..."
                rows={6}
                value={broadcastForm.message}
                onChange={(e) => setBroadcastForm({...broadcastForm, message: e.target.value})}
              />
            </div>
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm">
              <p className="text-yellow-800">
                <AlertTriangle className="w-4 h-4 inline mr-1" />
                This will send messages to all recipients in the selected group. Make sure your message is ready.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBroadcastDialogOpen(false)}>Cancel</Button>
            <Button 
              onClick={handleSendBroadcast} 
              disabled={sendingBroadcast}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {sendingBroadcast ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Send className="w-4 h-4 mr-2" />
              )}
              Send Broadcast
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default WhatsAppNotifications;
