import { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { 
  Plus, Search, Send, Check, X, CreditCard, FileCheck,
  Clock, AlertCircle, ChevronRight, Eye, FileText, Users,
  Building2, TrendingUp, Calendar, Banknote, RefreshCw
} from 'lucide-react';

const ORDER_STATUSES = {
  draft: { label: 'Draft', color: 'secondary', icon: FileText },
  pending_approval: { label: 'Pending Approval', color: 'warning', icon: Clock },
  client_approved: { label: 'Client Approved', color: 'success', icon: Check },
  client_rejected: { label: 'Rejected', color: 'destructive', icon: X },
  payment_pending: { label: 'Payment Pending', color: 'warning', icon: CreditCard },
  payment_received: { label: 'Payment Received', color: 'success', icon: Banknote },
  settlement_initiated: { label: 'Settlement Initiated', color: 'info', icon: RefreshCw },
  settled: { label: 'Settled', color: 'success', icon: FileCheck },
  cancelled: { label: 'Cancelled', color: 'destructive', icon: X },
  expired: { label: 'Expired', color: 'secondary', icon: AlertCircle },
};

const FIOrders = () => {
  const [orders, setOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [pagination, setPagination] = useState({ skip: 0, limit: 25, total: 0 });

  const [formData, setFormData] = useState({
    client_id: '',
    isin: '',
    order_type: 'secondary_buy',
    quantity: '',
    clean_price: '',
    settlement_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    notes: '',
  });

  const [paymentData, setPaymentData] = useState({
    payment_amount: '',
    payment_reference: '',
    payment_date: new Date().toISOString().split('T')[0],
  });

  const [calculatedPricing, setCalculatedPricing] = useState(null);

  const { isPEDesk, isPEManager, isPELevel } = useCurrentUser();

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: pagination.skip.toString(),
        limit: pagination.limit.toString(),
      });
      
      if (activeTab !== 'all') params.append('status', activeTab);

      const response = await api.get(`/api/fixed-income/orders?${params}`);
      setOrders(response.data.orders || []);
      setPagination(prev => ({ ...prev, total: response.data.total || 0 }));
    } catch (error) {
      console.error('Error fetching orders:', error);
      toast.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  }, [pagination.skip, pagination.limit, activeTab]);

  const fetchClients = async () => {
    try {
      const response = await api.get('/api/clients?limit=500');
      setClients(response.data.clients || []);
    } catch (error) {
      console.error('Error fetching clients:', error);
    }
  };

  const fetchInstruments = async () => {
    try {
      const response = await api.get('/api/fixed-income/instruments?limit=500');
      setInstruments(response.data.instruments || []);
    } catch (error) {
      console.error('Error fetching instruments:', error);
    }
  };

  useEffect(() => {
    fetchOrders();
    fetchClients();
    fetchInstruments();
  }, [fetchOrders]);

  const calculatePricing = async () => {
    if (!formData.isin || !formData.clean_price || !formData.quantity) {
      return;
    }

    try {
      const response = await api.post('/api/fixed-income/instruments/calculate-pricing', null, {
        params: {
          isin: formData.isin,
          clean_price: parseFloat(formData.clean_price),
          settlement_date: formData.settlement_date,
        }
      });
      
      const pricing = response.data;
      const qty = parseInt(formData.quantity);
      const cleanPrice = parseFloat(pricing.clean_price);
      const accruedInterest = parseFloat(pricing.accrued_interest);
      const dirtyPrice = parseFloat(pricing.dirty_price);
      
      setCalculatedPricing({
        ...pricing,
        quantity: qty,
        principal_amount: (cleanPrice * qty).toFixed(2),
        accrued_interest_amount: (accruedInterest * qty).toFixed(2),
        total_consideration: (dirtyPrice * qty).toFixed(2),
        brokerage: ((dirtyPrice * qty) * 0.001).toFixed(2),
        stamp_duty: ((dirtyPrice * qty) * 0.00015).toFixed(2),
        gst: (((dirtyPrice * qty) * 0.001) * 0.18).toFixed(2),
        net_amount: (
          (dirtyPrice * qty) + 
          ((dirtyPrice * qty) * 0.001) + 
          ((dirtyPrice * qty) * 0.00015) + 
          (((dirtyPrice * qty) * 0.001) * 0.18)
        ).toFixed(2),
      });
    } catch (error) {
      console.error('Error calculating pricing:', error);
    }
  };

  useEffect(() => {
    if (formData.isin && formData.clean_price && formData.quantity && formData.settlement_date) {
      const timer = setTimeout(calculatePricing, 500);
      return () => clearTimeout(timer);
    }
  }, [formData.isin, formData.clean_price, formData.quantity, formData.settlement_date]);

  const handleCreateOrder = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        client_id: formData.client_id,
        isin: formData.isin,
        instrument_id: instruments.find(i => i.isin === formData.isin)?.id,
        order_type: formData.order_type,
        quantity: parseInt(formData.quantity),
        clean_price: parseFloat(formData.clean_price),
        settlement_date: formData.settlement_date,
        notes: formData.notes,
      };

      const response = await api.post('/api/fixed-income/orders', payload);
      toast.success(`Order ${response.data.order_number} created successfully`);
      setCreateDialogOpen(false);
      resetForm();
      fetchOrders();
    } catch (error) {
      console.error('Error creating order:', error);
      toast.error(error.response?.data?.detail || 'Failed to create order');
    }
  };

  const handleSendDealSheet = async (orderId) => {
    try {
      await api.post(`/api/fixed-income/orders/${orderId}/send-deal-sheet`);
      toast.success('Deal sheet sent to client');
      fetchOrders();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send deal sheet');
    }
  };

  const handleApproveOrder = async (orderId) => {
    try {
      await api.post(`/api/fixed-income/orders/${orderId}/approve`);
      toast.success('Order approved');
      fetchOrders();
      setDetailDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve order');
    }
  };

  const handleRecordPayment = async () => {
    if (!selectedOrder) return;
    
    try {
      await api.post(`/api/fixed-income/orders/${selectedOrder.id}/record-payment`, null, {
        params: {
          payment_amount: parseFloat(paymentData.payment_amount),
          payment_reference: paymentData.payment_reference,
          payment_date: paymentData.payment_date,
        }
      });
      toast.success('Payment recorded');
      setPaymentDialogOpen(false);
      fetchOrders();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    }
  };

  const handleInitiateSettlement = async (orderId) => {
    try {
      await api.post(`/api/fixed-income/orders/${orderId}/initiate-settlement`);
      toast.success('Settlement initiated');
      fetchOrders();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to initiate settlement');
    }
  };

  const handleCompleteSettlement = async (orderId) => {
    const counterpartyPayment = prompt('Enter counterparty payment amount:');
    if (!counterpartyPayment) return;

    try {
      await api.post(`/api/fixed-income/orders/${orderId}/complete-settlement`, null, {
        params: {
          counterparty_payment: parseFloat(counterpartyPayment),
        }
      });
      toast.success('Settlement completed');
      fetchOrders();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete settlement');
    }
  };

  const resetForm = () => {
    setFormData({
      client_id: '',
      isin: '',
      order_type: 'secondary_buy',
      quantity: '',
      clean_price: '',
      settlement_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      notes: '',
    });
    setCalculatedPricing(null);
  };

  const openOrderDetails = async (order) => {
    try {
      const response = await api.get(`/api/fixed-income/orders/${order.id}`);
      setSelectedOrder(response.data);
      setDetailDialogOpen(true);
    } catch (error) {
      toast.error('Failed to load order details');
    }
  };

  const openPaymentDialog = (order) => {
    setSelectedOrder(order);
    setPaymentData({
      payment_amount: order.net_amount || '',
      payment_reference: '',
      payment_date: new Date().toISOString().split('T')[0],
    });
    setPaymentDialogOpen(true);
  };

  const getStatusBadge = (status) => {
    const config = ORDER_STATUSES[status] || { label: status, color: 'secondary' };
    const Icon = config.icon || FileText;
    
    const colorClasses = {
      secondary: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
      warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
      success: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
      destructive: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    };

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${colorClasses[config.color]}`}>
        <Icon className="h-3 w-3" />
        {config.label}
      </span>
    );
  };

  const filteredOrders = orders.filter(order =>
    order.order_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    order.client_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    order.issuer_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    order.isin?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="fi-orders">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <FileText className="h-6 w-6 text-emerald-600" />
            Fixed Income - Orders
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage NCD/Bond orders and deal sheets
          </p>
        </div>
        <Button
          onClick={() => { resetForm(); setCreateDialogOpen(true); }}
          className="bg-emerald-600 hover:bg-emerald-700"
          data-testid="create-order-btn"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Order
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Pending Approval</p>
                <p className="text-2xl font-bold text-amber-600">
                  {orders.filter(o => o.status === 'pending_approval').length}
                </p>
              </div>
              <Clock className="h-8 w-8 text-amber-500/20" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Payment Pending</p>
                <p className="text-2xl font-bold text-blue-600">
                  {orders.filter(o => ['client_approved', 'payment_pending'].includes(o.status)).length}
                </p>
              </div>
              <CreditCard className="h-8 w-8 text-blue-500/20" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">In Settlement</p>
                <p className="text-2xl font-bold text-purple-600">
                  {orders.filter(o => o.status === 'settlement_initiated').length}
                </p>
              </div>
              <RefreshCw className="h-8 w-8 text-purple-500/20" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Settled (MTD)</p>
                <p className="text-2xl font-bold text-emerald-600">
                  {orders.filter(o => o.status === 'settled').length}
                </p>
              </div>
              <FileCheck className="h-8 w-8 text-emerald-500/20" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search by order number, client, ISIN..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button variant="outline" onClick={fetchOrders}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">All Orders</TabsTrigger>
          <TabsTrigger value="draft">Draft</TabsTrigger>
          <TabsTrigger value="pending_approval">Pending</TabsTrigger>
          <TabsTrigger value="client_approved">Approved</TabsTrigger>
          <TabsTrigger value="settled">Settled</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-4">
          <Card>
            <CardContent className="p-0">
              {loading ? (
                <div className="p-6 space-y-4">
                  {[1,2,3,4,5].map(i => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : (
                <ScrollArea className="h-[500px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Order No.</TableHead>
                        <TableHead>Client</TableHead>
                        <TableHead>Instrument</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead className="text-right">Qty</TableHead>
                        <TableHead className="text-right">Net Amount</TableHead>
                        <TableHead className="text-right">YTM</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-center">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredOrders.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={9} className="text-center py-8 text-gray-500">
                            No orders found
                          </TableCell>
                        </TableRow>
                      ) : (
                        filteredOrders.map((order) => (
                          <TableRow key={order.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                            <TableCell className="font-medium">
                              <button 
                                onClick={() => openOrderDetails(order)}
                                className="text-emerald-600 hover:underline"
                              >
                                {order.order_number}
                              </button>
                            </TableCell>
                            <TableCell>{order.client_name}</TableCell>
                            <TableCell>
                              <div className="max-w-[150px] truncate">{order.issuer_name}</div>
                              <div className="text-xs text-gray-500">{order.isin}</div>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {order.order_type?.replace('_', ' ').toUpperCase()}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">{order.quantity?.toLocaleString()}</TableCell>
                            <TableCell className="text-right font-mono">
                              ₹{parseFloat(order.net_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                            </TableCell>
                            <TableCell className="text-right text-emerald-600 font-semibold">
                              {order.ytm ? `${parseFloat(order.ytm).toFixed(2)}%` : '-'}
                            </TableCell>
                            <TableCell>{getStatusBadge(order.status)}</TableCell>
                            <TableCell>
                              <div className="flex justify-center gap-1">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => openOrderDetails(order)}
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                                
                                {order.status === 'draft' && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleSendDealSheet(order.id)}
                                    title="Send Deal Sheet"
                                  >
                                    <Send className="h-4 w-4 text-blue-500" />
                                  </Button>
                                )}
                                
                                {order.status === 'pending_approval' && isPELevel && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleApproveOrder(order.id)}
                                    title="Approve"
                                  >
                                    <Check className="h-4 w-4 text-emerald-500" />
                                  </Button>
                                )}
                                
                                {['client_approved', 'payment_pending'].includes(order.status) && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => openPaymentDialog(order)}
                                    title="Record Payment"
                                  >
                                    <CreditCard className="h-4 w-4 text-amber-500" />
                                  </Button>
                                )}
                                
                                {order.status === 'payment_received' && isPELevel && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleInitiateSettlement(order.id)}
                                    title="Initiate Settlement"
                                  >
                                    <RefreshCw className="h-4 w-4 text-purple-500" />
                                  </Button>
                                )}
                                
                                {order.status === 'settlement_initiated' && isPELevel && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleCompleteSettlement(order.id)}
                                    title="Complete Settlement"
                                  >
                                    <FileCheck className="h-4 w-4 text-emerald-500" />
                                  </Button>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create Order Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5 text-emerald-600" />
              Create Fixed Income Order
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handleCreateOrder} className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              {/* Left Column - Order Details */}
              <div className="space-y-4">
                <div>
                  <Label>Client *</Label>
                  <Select value={formData.client_id} onValueChange={(v) => setFormData(prev => ({ ...prev, client_id: v }))}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select client" />
                    </SelectTrigger>
                    <SelectContent>
                      {clients.map(c => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.name} ({c.pan_number})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>Instrument (ISIN) *</Label>
                  <Select value={formData.isin} onValueChange={(v) => setFormData(prev => ({ ...prev, isin: v }))}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select instrument" />
                    </SelectTrigger>
                    <SelectContent>
                      {instruments.map(i => (
                        <SelectItem key={i.isin} value={i.isin}>
                          {i.issuer_name} ({i.isin}) - {i.coupon_rate}%
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>Order Type</Label>
                  <Select value={formData.order_type} onValueChange={(v) => setFormData(prev => ({ ...prev, order_type: v }))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="secondary_buy">Secondary Buy</SelectItem>
                      <SelectItem value="secondary_sell">Secondary Sell</SelectItem>
                      <SelectItem value="primary">Primary (New Issue)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Quantity *</Label>
                    <Input
                      type="number"
                      value={formData.quantity}
                      onChange={(e) => setFormData(prev => ({ ...prev, quantity: e.target.value }))}
                      placeholder="1000"
                      required
                    />
                  </div>
                  <div>
                    <Label>Clean Price *</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.clean_price}
                      onChange={(e) => setFormData(prev => ({ ...prev, clean_price: e.target.value }))}
                      placeholder="1050.00"
                      required
                    />
                  </div>
                </div>

                <div>
                  <Label>Settlement Date</Label>
                  <Input
                    type="date"
                    value={formData.settlement_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, settlement_date: e.target.value }))}
                  />
                </div>

                <div>
                  <Label>Notes</Label>
                  <Textarea
                    value={formData.notes}
                    onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                    placeholder="Additional notes..."
                    rows={3}
                  />
                </div>
              </div>

              {/* Right Column - Pricing Summary */}
              <div>
                <Card className="bg-gray-50 dark:bg-gray-800/50">
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-emerald-600" />
                      Pricing Summary
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {calculatedPricing ? (
                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Clean Price:</span>
                          <span className="font-mono">₹{calculatedPricing.clean_price}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Accrued Interest:</span>
                          <span className="font-mono">₹{calculatedPricing.accrued_interest}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Dirty Price:</span>
                          <span className="font-mono">₹{calculatedPricing.dirty_price}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">YTM:</span>
                          <span className="font-mono text-emerald-600 font-semibold">{calculatedPricing.ytm}%</span>
                        </div>
                        
                        <hr className="my-2" />
                        
                        <div className="flex justify-between">
                          <span className="text-gray-500">Principal ({formData.quantity} units):</span>
                          <span className="font-mono">₹{parseFloat(calculatedPricing.principal_amount).toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Accrued Interest:</span>
                          <span className="font-mono">₹{parseFloat(calculatedPricing.accrued_interest_amount).toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Total Consideration:</span>
                          <span className="font-mono">₹{parseFloat(calculatedPricing.total_consideration).toLocaleString()}</span>
                        </div>
                        
                        <hr className="my-2" />
                        
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-500">Brokerage (0.10%):</span>
                          <span className="font-mono">₹{calculatedPricing.brokerage}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-500">Stamp Duty (0.015%):</span>
                          <span className="font-mono">₹{calculatedPricing.stamp_duty}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-500">GST (18% on brokerage):</span>
                          <span className="font-mono">₹{calculatedPricing.gst}</span>
                        </div>
                        
                        <hr className="my-2" />
                        
                        <div className="flex justify-between text-lg font-semibold">
                          <span>Net Amount:</span>
                          <span className="text-emerald-600">₹{parseFloat(calculatedPricing.net_amount).toLocaleString()}</span>
                        </div>
                        
                        {calculatedPricing.duration && (
                          <div className="mt-4 p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded">
                            <div className="flex justify-between text-xs">
                              <span>Duration:</span>
                              <span>{calculatedPricing.duration} years</span>
                            </div>
                            <div className="flex justify-between text-xs">
                              <span>Modified Duration:</span>
                              <span>{calculatedPricing.modified_duration}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 text-center py-4">
                        Enter quantity and price to calculate
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700" disabled={!calculatedPricing}>
                Create Order
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Order Detail Dialog */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Order Details - {selectedOrder?.order_number}</DialogTitle>
          </DialogHeader>
          
          {selectedOrder && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                {getStatusBadge(selectedOrder.status)}
                <span className="text-sm text-gray-500">
                  Created: {new Date(selectedOrder.created_at).toLocaleDateString()}
                </span>
              </div>

              <Card>
                <CardContent className="pt-4 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">Client</p>
                    <p className="font-semibold">{selectedOrder.client?.name}</p>
                    <p className="text-sm text-gray-500">{selectedOrder.client?.pan_number}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Instrument</p>
                    <p className="font-semibold">{selectedOrder.instrument?.issuer_name}</p>
                    <p className="text-sm text-gray-500">{selectedOrder.isin}</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4">
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">Quantity</p>
                      <p className="font-semibold">{selectedOrder.quantity?.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Clean Price</p>
                      <p className="font-semibold">₹{selectedOrder.clean_price}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Dirty Price</p>
                      <p className="font-semibold">₹{selectedOrder.dirty_price}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">YTM</p>
                      <p className="font-semibold text-emerald-600">{selectedOrder.ytm}%</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-emerald-50 dark:bg-emerald-900/20">
                <CardContent className="pt-4">
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Net Amount</span>
                    <span className="text-2xl font-bold text-emerald-600">
                      ₹{parseFloat(selectedOrder.net_amount || 0).toLocaleString()}
                    </span>
                  </div>
                </CardContent>
              </Card>

              <DialogFooter>
                {selectedOrder.status === 'draft' && (
                  <Button onClick={() => handleSendDealSheet(selectedOrder.id)}>
                    <Send className="h-4 w-4 mr-2" />
                    Send Deal Sheet
                  </Button>
                )}
                {selectedOrder.status === 'pending_approval' && isPELevel && (
                  <Button onClick={() => handleApproveOrder(selectedOrder.id)} className="bg-emerald-600 hover:bg-emerald-700">
                    <Check className="h-4 w-4 mr-2" />
                    Approve Order
                  </Button>
                )}
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Payment Dialog */}
      <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Banknote className="h-5 w-5 text-emerald-600" />
              Record Payment
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>Payment Amount</Label>
              <Input
                type="number"
                step="0.01"
                value={paymentData.payment_amount}
                onChange={(e) => setPaymentData(prev => ({ ...prev, payment_amount: e.target.value }))}
              />
            </div>
            <div>
              <Label>Payment Reference</Label>
              <Input
                value={paymentData.payment_reference}
                onChange={(e) => setPaymentData(prev => ({ ...prev, payment_reference: e.target.value }))}
                placeholder="UTR / Transaction ID"
              />
            </div>
            <div>
              <Label>Payment Date</Label>
              <Input
                type="date"
                value={paymentData.payment_date}
                onChange={(e) => setPaymentData(prev => ({ ...prev, payment_date: e.target.value }))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setPaymentDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleRecordPayment} className="bg-emerald-600 hover:bg-emerald-700">
              Record Payment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default FIOrders;
