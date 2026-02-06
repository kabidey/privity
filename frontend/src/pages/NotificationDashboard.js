import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Input } from '../components/ui/input';
import { 
  Bell, MessageSquare, CheckCircle, XCircle, Clock, RefreshCw,
  Send, Eye, Trash2, BarChart3, TrendingUp, AlertTriangle,
  Phone, Mail, Filter, Search, ChevronDown, ChevronUp
} from 'lucide-react';

const NotificationDashboard = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  
  // Data states
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [deliveryStats, setDeliveryStats] = useState(null);
  const [webhookEvents, setWebhookEvents] = useState([]);
  const [incomingMessages, setIncomingMessages] = useState([]);
  const [automationLogs, setAutomationLogs] = useState([]);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  const isPELevel = user?.role === 1 || user?.role === 2;

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [notifRes, statsRes] = await Promise.all([
        api.get('/notifications?limit=50'),
        api.get('/whatsapp/delivery-stats?days=7').catch(() => ({ data: null }))
      ]);
      
      setNotifications(notifRes.data || []);
      setUnreadCount(notifRes.data?.filter(n => !n.read).length || 0);
      setDeliveryStats(statsRes.data);
      
      // Fetch additional data for PE level
      if (isPELevel) {
        const [eventsRes, messagesRes, logsRes] = await Promise.all([
          api.get('/whatsapp/webhook/events?limit=50').catch(() => ({ data: { events: [] } })),
          api.get('/whatsapp/incoming-messages?limit=50').catch(() => ({ data: { messages: [] } })),
          api.get('/whatsapp/automation/logs?limit=20').catch(() => ({ data: { logs: [] } }))
        ]);
        
        setWebhookEvents(eventsRes.data?.events || []);
        setIncomingMessages(messagesRes.data?.messages || []);
        setAutomationLogs(logsRes.data?.logs || []);
      }
    } catch (error) {
      console.error('Failed to fetch notification data:', error);
    } finally {
      setLoading(false);
    }
  }, [isPELevel]);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleMarkAsRead = async (notificationId) => {
    try {
      await api.put(`/notifications/${notificationId}/read`);
      setNotifications(prev => prev.map(n => 
        n.id === notificationId ? { ...n, read: true } : n
      ));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      toast.error('Failed to mark as read');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.put('/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
      toast.success('All notifications marked as read');
    } catch (error) {
      toast.error('Failed to mark all as read');
    }
  };

  const handleDeleteNotification = async (notificationId) => {
    try {
      await api.delete(`/notifications/${notificationId}`);
      setNotifications(prev => prev.filter(n => n.id !== notificationId));
      toast.success('Notification deleted');
    } catch (error) {
      toast.error('Failed to delete notification');
    }
  };

  const handleMarkIncomingRead = async (messageId) => {
    try {
      await api.put(`/whatsapp/incoming-messages/${messageId}/read`);
      setIncomingMessages(prev => prev.map(m => 
        m.id === messageId ? { ...m, read: true } : m
      ));
      toast.success('Message marked as read');
    } catch (error) {
      toast.error('Failed to mark message as read');
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'booking_created':
      case 'booking_approved':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'booking_rejected':
      case 'whatsapp_failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'client_approved':
        return <CheckCircle className="h-4 w-4 text-blue-500" />;
      case 'whatsapp_incoming':
        return <MessageSquare className="h-4 w-4 text-green-500" />;
      case 'payment_reminder':
        return <Clock className="h-4 w-4 text-orange-500" />;
      default:
        return <Bell className="h-4 w-4 text-gray-500" />;
    }
  };

  const filteredNotifications = notifications.filter(n => {
    if (showUnreadOnly && n.read) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return n.title?.toLowerCase().includes(query) || 
             n.message?.toLowerCase().includes(query);
    }
    return true;
  });

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-6 p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2">
            <Bell className="h-7 w-7 text-primary" />
            Notification Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            Real-time updates and message delivery tracking
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchData}
            disabled={loading}
            data-testid="refresh-notifications-btn"
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          {unreadCount > 0 && (
            <Button 
              variant="default" 
              size="sm" 
              onClick={handleMarkAllRead}
              data-testid="mark-all-read-btn"
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Mark All Read ({unreadCount})
            </Button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Unread Notifications</p>
                <p className="text-2xl font-bold">{unreadCount}</p>
              </div>
              <Bell className="h-8 w-8 text-orange-500 opacity-80" />
            </div>
          </CardContent>
        </Card>
        
        {deliveryStats && (
          <>
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Messages Sent (7d)</p>
                    <p className="text-2xl font-bold">{deliveryStats.total_sent}</p>
                  </div>
                  <Send className="h-8 w-8 text-blue-500 opacity-80" />
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Delivery Rate</p>
                    <p className="text-2xl font-bold text-green-600">{deliveryStats.delivery_rate}%</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-green-500 opacity-80" />
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Failed Messages</p>
                    <p className="text-2xl font-bold text-red-600">{deliveryStats.failed}</p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-red-500 opacity-80" />
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 sm:grid-cols-4 lg:w-auto lg:inline-flex">
          <TabsTrigger value="overview" data-testid="tab-overview">
            <Bell className="h-4 w-4 mr-1" />
            Notifications
            {unreadCount > 0 && (
              <Badge variant="destructive" className="ml-1 h-5 min-w-5 px-1">
                {unreadCount}
              </Badge>
            )}
          </TabsTrigger>
          {isPELevel && (
            <>
              <TabsTrigger value="incoming" data-testid="tab-incoming">
                <MessageSquare className="h-4 w-4 mr-1" />
                Incoming
                {incomingMessages.filter(m => !m.read).length > 0 && (
                  <Badge variant="secondary" className="ml-1 h-5 min-w-5 px-1">
                    {incomingMessages.filter(m => !m.read).length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="webhooks" data-testid="tab-webhooks">
                <BarChart3 className="h-4 w-4 mr-1" />
                Delivery Status
              </TabsTrigger>
              <TabsTrigger value="automation" data-testid="tab-automation">
                <Clock className="h-4 w-4 mr-1" />
                Automation Logs
              </TabsTrigger>
            </>
          )}
        </TabsList>

        {/* Notifications Tab */}
        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <CardTitle className="text-lg">All Notifications</CardTitle>
                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <div className="relative flex-1 sm:w-64">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search notifications..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-8"
                      data-testid="search-notifications"
                    />
                  </div>
                  <Button
                    variant={showUnreadOnly ? "default" : "outline"}
                    size="sm"
                    onClick={() => setShowUnreadOnly(!showUnreadOnly)}
                  >
                    <Filter className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {filteredNotifications.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Bell className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No notifications found</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                  {filteredNotifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                        notification.read 
                          ? 'bg-background' 
                          : 'bg-primary/5 border-primary/20'
                      }`}
                      data-testid={`notification-${notification.id}`}
                    >
                      <div className="mt-1">
                        {getNotificationIcon(notification.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className={`font-medium ${!notification.read ? 'text-primary' : ''}`}>
                              {notification.title}
                            </p>
                            <p className="text-sm text-muted-foreground line-clamp-2">
                              {notification.message}
                            </p>
                          </div>
                          <span className="text-xs text-muted-foreground whitespace-nowrap">
                            {formatTime(notification.created_at)}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        {!notification.read && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleMarkAsRead(notification.id)}
                            title="Mark as read"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-red-500 hover:text-red-600"
                          onClick={() => handleDeleteNotification(notification.id)}
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Incoming Messages Tab (PE Level Only) */}
        {isPELevel && (
          <TabsContent value="incoming" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-green-500" />
                  Incoming WhatsApp Messages
                </CardTitle>
                <CardDescription>
                  Messages received from clients via WhatsApp
                </CardDescription>
              </CardHeader>
              <CardContent>
                {incomingMessages.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No incoming messages</p>
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[600px] overflow-y-auto">
                    {incomingMessages.map((message) => (
                      <div
                        key={message.id}
                        className={`p-4 rounded-lg border ${
                          message.read ? 'bg-background' : 'bg-green-50 dark:bg-green-950 border-green-200'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <Phone className="h-4 w-4 text-green-600" />
                            <span className="font-medium">{message.wa_id}</span>
                            {!message.read && (
                              <Badge variant="secondary" className="bg-green-100 text-green-800">New</Badge>
                            )}
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {formatTime(message.received_at)}
                          </span>
                        </div>
                        <p className="mt-2 text-sm">{message.text}</p>
                        {!message.read && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="mt-2"
                            onClick={() => handleMarkIncomingRead(message.id)}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            Mark as Read
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {/* Webhook Events / Delivery Status Tab */}
        {isPELevel && (
          <TabsContent value="webhooks" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-blue-500" />
                  Message Delivery Status
                </CardTitle>
                <CardDescription>
                  Real-time delivery status from Wati.io webhooks
                </CardDescription>
              </CardHeader>
              <CardContent>
                {deliveryStats && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6 p-4 bg-muted/50 rounded-lg">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-blue-600">{deliveryStats.total_sent}</p>
                      <p className="text-xs text-muted-foreground">Total Sent</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-green-600">{deliveryStats.delivered}</p>
                      <p className="text-xs text-muted-foreground">Delivered</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-purple-600">{deliveryStats.read}</p>
                      <p className="text-xs text-muted-foreground">Read</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-red-600">{deliveryStats.failed}</p>
                      <p className="text-xs text-muted-foreground">Failed</p>
                    </div>
                  </div>
                )}
                
                {webhookEvents.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <BarChart3 className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No webhook events received yet</p>
                    <p className="text-sm mt-2">Configure your Wati.io webhook URL to receive delivery updates</p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[400px] overflow-y-auto">
                    {webhookEvents.slice(0, 20).map((event) => (
                      <div
                        key={event.id}
                        className="flex items-center justify-between p-3 rounded-lg border bg-muted/30"
                      >
                        <div className="flex items-center gap-3">
                          {event.status === 'delivered' && <CheckCircle className="h-4 w-4 text-green-500" />}
                          {event.status === 'read' && <Eye className="h-4 w-4 text-purple-500" />}
                          {event.status === 'failed' && <XCircle className="h-4 w-4 text-red-500" />}
                          {!event.status && <Clock className="h-4 w-4 text-gray-500" />}
                          <div>
                            <p className="text-sm font-medium">{event.event_type}</p>
                            <p className="text-xs text-muted-foreground">{event.wa_id}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge variant={event.processed ? "secondary" : "outline"}>
                            {event.status || event.event_type}
                          </Badge>
                          <p className="text-xs text-muted-foreground mt-1">
                            {formatTime(event.received_at)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {/* Automation Logs Tab */}
        {isPELevel && (
          <TabsContent value="automation" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Clock className="h-5 w-5 text-orange-500" />
                  Automation Run Logs
                </CardTitle>
                <CardDescription>
                  History of automated WhatsApp notification runs
                </CardDescription>
              </CardHeader>
              <CardContent>
                {automationLogs.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Clock className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No automation logs yet</p>
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[500px] overflow-y-auto">
                    {automationLogs.map((log) => (
                      <div
                        key={log.id}
                        className="p-4 rounded-lg border bg-muted/30"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{log.automation_type || 'Scheduled Run'}</p>
                            <p className="text-sm text-muted-foreground">
                              {log.total_sent || 0} messages sent
                              {log.failed > 0 && (
                                <span className="text-red-500 ml-2">
                                  ({log.failed} failed)
                                </span>
                              )}
                            </p>
                          </div>
                          <Badge variant={log.status === 'success' ? "secondary" : "destructive"}>
                            {log.status || 'completed'}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                          {formatTime(log.run_at)}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
};

export default NotificationDashboard;
