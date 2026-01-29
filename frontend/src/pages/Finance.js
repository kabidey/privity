import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  Wallet, ArrowDownLeft, ArrowUpRight, FileSpreadsheet, 
  RefreshCw, TrendingUp, TrendingDown, DollarSign, FileText,
  ExternalLink, RotateCcw, CheckCircle, Clock, AlertCircle, XCircle,
  Building, CreditCard, Edit, Users
} from 'lucide-react';

const Finance = () => {
  const [payments, setPayments] = useState([]);
  const [refundRequests, setRefundRequests] = useState([]);
  const [rpPayments, setRpPayments] = useState([]);
  const [bpPayments, setBpPayments] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [filters, setFilters] = useState({
    type: 'all',
    startDate: '',
    endDate: ''
  });
  const [refundDialogOpen, setRefundDialogOpen] = useState(false);
  const [selectedRefund, setSelectedRefund] = useState(null);
  const [refundForm, setRefundForm] = useState({
    status: '',
    notes: '',
    reference_number: ''
  });
  const [rpPaymentDialogOpen, setRpPaymentDialogOpen] = useState(false);
  const [selectedRpPayment, setSelectedRpPayment] = useState(null);
  const [rpPaymentForm, setRpPaymentForm] = useState({
    status: '',
    notes: '',
    payment_reference: '',
    payment_date: ''
  });
  const [bpPaymentDialogOpen, setBpPaymentDialogOpen] = useState(false);
  const [selectedBpPayment, setSelectedBpPayment] = useState(null);
  const [bpPaymentForm, setBpPaymentForm] = useState({
    status: '',
    notes: '',
    payment_reference: '',
    payment_date: ''
  });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  // PE Level (1, 2) or Finance role (7) can access Finance page
  const hasFinanceAccess = currentUser.role === 1 || currentUser.role === 2 || currentUser.role === 7;

  useEffect(() => {
    if (hasFinanceAccess) {
      fetchData();
    }
  }, [filters, hasFinanceAccess]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.type !== 'all') params.append('payment_type', filters.type);
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);

      const [paymentsRes, summaryRes, refundsRes, rpPaymentsRes, commissionsRes, commSummaryRes] = await Promise.all([
        api.get(`/finance/payments?${params.toString()}`),
        api.get(`/finance/summary?${params.toString()}`),
        api.get('/finance/refund-requests'),
        api.get('/finance/rp-payments'),
        api.get('/finance/employee-commissions'),
        api.get('/finance/employee-commissions/summary')
      ]);

      setPayments(paymentsRes.data);
      setSummary(summaryRes.data);
      setRefundRequests(refundsRes.data);
      setRpPayments(rpPaymentsRes.data || []);
      setEmployeeCommissions(commissionsRes.data || []);
      setCommissionSummary(commSummaryRes.data || []);
    } catch (error) {
      toast.error('Failed to fetch finance data');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (filters.type !== 'all') params.append('payment_type', filters.type);
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);

      const response = await api.get(`/finance/export/excel?${params.toString()}`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `finance_report_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Excel exported successfully');
    } catch (error) {
      toast.error('Failed to export Excel');
    } finally {
      setExporting(false);
    }
  };

  const openRefundDialog = (refund) => {
    setSelectedRefund(refund);
    setRefundForm({
      status: refund.status,
      notes: refund.notes || '',
      reference_number: refund.reference_number || ''
    });
    setRefundDialogOpen(true);
  };

  const handleUpdateRefund = async () => {
    if (!selectedRefund) return;
    try {
      await api.put(`/finance/refund-requests/${selectedRefund.id}`, {
        status: refundForm.status,
        notes: refundForm.notes || null,
        reference_number: refundForm.reference_number || null
      });
      toast.success('Refund request updated');
      setRefundDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update refund');
    }
  };

  const openRpPaymentDialog = (payment) => {
    setSelectedRpPayment(payment);
    setRpPaymentForm({
      status: payment.status,
      notes: payment.notes || '',
      payment_reference: payment.payment_reference || '',
      payment_date: payment.payment_date ? payment.payment_date.split('T')[0] : new Date().toISOString().split('T')[0]
    });
    setRpPaymentDialogOpen(true);
  };

  const handleUpdateRpPayment = async () => {
    if (!selectedRpPayment) return;
    try {
      await api.put(`/finance/rp-payments/${selectedRpPayment.id}`, {
        status: rpPaymentForm.status,
        notes: rpPaymentForm.notes || null,
        payment_reference: rpPaymentForm.payment_reference || null,
        payment_date: rpPaymentForm.payment_date || null
      });
      toast.success('RP payment updated');
      setRpPaymentDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update RP payment');
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(amount || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const getRefundStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800'
    };
    const icons = {
      pending: <Clock className="h-3 w-3 mr-1" />,
      processing: <RefreshCw className="h-3 w-3 mr-1 animate-spin" />,
      completed: <CheckCircle className="h-3 w-3 mr-1" />,
      failed: <XCircle className="h-3 w-3 mr-1" />
    };
    return (
      <Badge className={styles[status] || 'bg-gray-100'}>
        {icons[status]}
        {status?.toUpperCase()}
      </Badge>
    );
  };

  const clientPayments = payments.filter(p => p.type === 'client');
  const vendorPayments = payments.filter(p => p.type === 'vendor');
  const pendingRefunds = refundRequests.filter(r => r.status === 'pending' || r.status === 'processing');
  const pendingRpPayments = rpPayments.filter(p => p.status === 'pending' || p.status === 'processing');
  const pendingCommissions = employeeCommissions.filter(c => c.status === 'pending' || c.status === 'calculated');

  const getRpPaymentStatusBadge = (status) => {
    const styles = {
      pending: 'bg-orange-100 text-orange-800',
      processing: 'bg-blue-100 text-blue-800',
      paid: 'bg-green-100 text-green-800'
    };
    const icons = {
      pending: <Clock className="h-3 w-3 mr-1" />,
      processing: <RefreshCw className="h-3 w-3 mr-1 animate-spin" />,
      paid: <CheckCircle className="h-3 w-3 mr-1" />
    };
    return (
      <Badge className={styles[status] || 'bg-gray-100'}>
        {icons[status]}
        {status?.toUpperCase()}
      </Badge>
    );
  };

  const getCommissionStatusBadge = (status) => {
    const styles = {
      pending: 'bg-gray-100 text-gray-800',
      calculated: 'bg-blue-100 text-blue-800',
      paid: 'bg-green-100 text-green-800'
    };
    const icons = {
      pending: <Clock className="h-3 w-3 mr-1" />,
      calculated: <DollarSign className="h-3 w-3 mr-1" />,
      paid: <CheckCircle className="h-3 w-3 mr-1" />
    };
    return (
      <Badge className={styles[status] || 'bg-gray-100'}>
        {icons[status]}
        {status?.toUpperCase()}
      </Badge>
    );
  };

  const handleMarkCommissionPaid = async (bookingId) => {
    try {
      await api.put(`/finance/employee-commissions/${bookingId}/mark-paid`);
      toast.success('Commission marked as paid');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark commission as paid');
    }
  };

  if (!hasFinanceAccess) {
    return (
      <div className="p-8 text-center">
        <h1 className="text-2xl font-bold text-red-600">Access Denied</h1>
        <p className="text-muted-foreground">Only PE Desk, PE Manager, or Finance can access finance data.</p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 space-y-6" data-testid="finance-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2">
            <Wallet className="h-6 w-6 md:h-8 md:w-8 text-primary" />
            Finance Dashboard
          </h1>
          <p className="text-muted-foreground text-sm md:text-base">Track payments, refunds, and cash flow</p>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <Button variant="outline" onClick={fetchData} className="flex-1 sm:flex-none">
            <RefreshCw className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
          <Button onClick={handleExport} disabled={exporting} className="flex-1 sm:flex-none" data-testid="export-excel-btn">
            {exporting ? (
              <RefreshCw className="h-4 w-4 animate-spin sm:mr-2" />
            ) : (
              <FileSpreadsheet className="h-4 w-4 sm:mr-2" />
            )}
            <span className="hidden sm:inline">Export Excel</span>
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="border-l-4 border-l-green-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Received</p>
                  <p className="text-lg md:text-xl font-bold text-green-600">{formatCurrency(summary.total_received)}</p>
                </div>
                <ArrowDownLeft className="h-6 w-6 text-green-500 opacity-50" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{summary.client_payments_count} payments</p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-red-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Sent</p>
                  <p className="text-lg md:text-xl font-bold text-red-600">{formatCurrency(summary.total_sent)}</p>
                </div>
                <ArrowUpRight className="h-6 w-6 text-red-500 opacity-50" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{summary.vendor_payments_count} payments</p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Net Flow</p>
                  <p className={`text-lg md:text-xl font-bold ${summary.net_flow >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(summary.net_flow)}
                  </p>
                </div>
                {summary.net_flow >= 0 ? (
                  <TrendingUp className="h-6 w-6 text-green-500 opacity-50" />
                ) : (
                  <TrendingDown className="h-6 w-6 text-red-500 opacity-50" />
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-orange-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Pending Refunds</p>
                  <p className="text-lg md:text-xl font-bold text-orange-600">{formatCurrency(summary.pending_refunds_amount)}</p>
                </div>
                <RotateCcw className="h-6 w-6 text-orange-500 opacity-50" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{summary.pending_refunds_count} requests</p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-purple-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Refunds Done</p>
                  <p className="text-lg md:text-xl font-bold text-purple-600">{formatCurrency(summary.completed_refunds_amount)}</p>
                </div>
                <CheckCircle className="h-6 w-6 text-purple-500 opacity-50" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{summary.completed_refunds_count} completed</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* RP Payments Summary */}
      {summary && (summary.pending_rp_payments_count > 0 || summary.paid_rp_payments_count > 0) && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Card className="border-l-4 border-l-pink-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Pending RP Payments</p>
                  <p className="text-lg md:text-xl font-bold text-pink-600">{formatCurrency(summary.pending_rp_payments_amount)}</p>
                </div>
                <Clock className="h-6 w-6 text-pink-500 opacity-50" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{summary.pending_rp_payments_count} to pay</p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-emerald-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">RP Payments Done</p>
                  <p className="text-lg md:text-xl font-bold text-emerald-600">{formatCurrency(summary.paid_rp_payments_amount)}</p>
                </div>
                <CheckCircle className="h-6 w-6 text-emerald-500 opacity-50" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{summary.paid_rp_payments_count} paid</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Employee Commissions Summary */}
      {commissionSummary.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Card className="border-l-4 border-l-indigo-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Employee Commissions</p>
                  <p className="text-lg md:text-xl font-bold text-indigo-600">
                    {formatCurrency(commissionSummary.reduce((sum, e) => sum + e.total_commission, 0))}
                  </p>
                </div>
                <Users className="h-6 w-6 text-indigo-500 opacity-50" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {commissionSummary.reduce((sum, e) => sum + e.total_bookings, 0)} bookings
              </p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-yellow-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Pending Commissions</p>
                  <p className="text-lg md:text-xl font-bold text-yellow-600">
                    {formatCurrency(commissionSummary.reduce((sum, e) => sum + e.pending_commission + e.calculated_commission, 0))}
                  </p>
                </div>
                <Clock className="h-6 w-6 text-yellow-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-teal-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Paid Commissions</p>
                  <p className="text-lg md:text-xl font-bold text-teal-600">
                    {formatCurrency(commissionSummary.reduce((sum, e) => sum + e.paid_commission, 0))}
                  </p>
                </div>
                <CheckCircle className="h-6 w-6 text-teal-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-1 min-w-[150px]">
              <Label className="text-xs">Payment Type</Label>
              <Select value={filters.type} onValueChange={(v) => setFilters({ ...filters, type: v })}>
                <SelectTrigger data-testid="filter-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Payments</SelectItem>
                  <SelectItem value="client">Client (Received)</SelectItem>
                  <SelectItem value="vendor">Vendor (Sent)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Start Date</Label>
              <Input
                type="date"
                value={filters.startDate}
                onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
                className="w-40"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">End Date</Label>
              <Input
                type="date"
                value={filters.endDate}
                onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
                className="w-40"
              />
            </div>
            <Button 
              variant="ghost" 
              onClick={() => setFilters({ type: 'all', startDate: '', endDate: '' })}
              className="text-sm"
            >
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Main Tabs */}
      <Tabs defaultValue="all" className="w-full">
        <TabsList className="grid w-full grid-cols-6 max-w-3xl">
          <TabsTrigger value="all">All ({payments.length})</TabsTrigger>
          <TabsTrigger value="client">
            <ArrowDownLeft className="h-3 w-3 mr-1" />
            Received
          </TabsTrigger>
          <TabsTrigger value="vendor">
            <ArrowUpRight className="h-3 w-3 mr-1" />
            Sent
          </TabsTrigger>
          <TabsTrigger value="refunds" data-testid="refunds-tab">
            <RotateCcw className="h-3 w-3 mr-1" />
            Refunds ({refundRequests.length})
          </TabsTrigger>
          <TabsTrigger value="rp-payments" data-testid="rp-payments-tab">
            <CreditCard className="h-3 w-3 mr-1" />
            RP Payments ({rpPayments.length})
          </TabsTrigger>
          <TabsTrigger value="commissions" data-testid="commissions-tab">
            <Users className="h-3 w-3 mr-1" />
            Commissions ({employeeCommissions.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all">
          <PaymentTable payments={payments} formatCurrency={formatCurrency} formatDate={formatDate} />
        </TabsContent>

        <TabsContent value="client">
          <PaymentTable payments={clientPayments} formatCurrency={formatCurrency} formatDate={formatDate} title="Client Payments (Received)" />
        </TabsContent>

        <TabsContent value="vendor">
          <PaymentTable payments={vendorPayments} formatCurrency={formatCurrency} formatDate={formatDate} title="Vendor Payments (Sent)" />
        </TabsContent>

        <TabsContent value="refunds">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <RotateCcw className="h-5 w-5" />
                Refund Requests
              </CardTitle>
              <CardDescription>
                Manage refunds for voided bookings with payments
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0 md:p-6">
              {refundRequests.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">No refund requests found.</p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Booking #</TableHead>
                        <TableHead>Client</TableHead>
                        <TableHead>Stock</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead>Bank Details</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {refundRequests.map((refund) => (
                        <TableRow key={refund.id} data-testid={`refund-row-${refund.id}`}>
                          <TableCell className="whitespace-nowrap">{formatDate(refund.created_at)}</TableCell>
                          <TableCell className="font-mono text-sm">{refund.booking_number}</TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{refund.client_name}</p>
                              <p className="text-xs text-muted-foreground">{refund.client_email}</p>
                            </div>
                          </TableCell>
                          <TableCell className="font-mono">{refund.stock_symbol}</TableCell>
                          <TableCell className="text-right font-bold text-orange-600">
                            {formatCurrency(refund.refund_amount)}
                          </TableCell>
                          <TableCell>
                            {refund.bank_details?.account_number ? (
                              <div className="text-xs">
                                <p className="font-medium">{refund.bank_details.bank_name}</p>
                                <p>A/C: {refund.bank_details.account_number}</p>
                                <p>IFSC: {refund.bank_details.ifsc_code}</p>
                              </div>
                            ) : (
                              <Badge variant="outline" className="text-orange-600">
                                <AlertCircle className="h-3 w-3 mr-1" />
                                No Bank Info
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>{getRefundStatusBadge(refund.status)}</TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openRefundDialog(refund)}
                              data-testid={`update-refund-${refund.id}`}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rp-payments">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <CreditCard className="h-5 w-5" />
                Referral Partner Payments
              </CardTitle>
              <CardDescription>
                Manage commission payments to referral partners
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0 md:p-6">
              {rpPayments.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">No RP payments found.</p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Booking #</TableHead>
                        <TableHead>Referral Partner</TableHead>
                        <TableHead>Stock</TableHead>
                        <TableHead className="text-right">Rev. Share %</TableHead>
                        <TableHead className="text-right">Payment Amount</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Reference</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rpPayments.map((payment) => (
                        <TableRow key={payment.id} data-testid={`rp-payment-row-${payment.id}`}>
                          <TableCell className="whitespace-nowrap">{formatDate(payment.created_at)}</TableCell>
                          <TableCell className="font-mono text-sm">{payment.booking_number}</TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{payment.rp_name}</p>
                              <p className="text-xs text-muted-foreground font-mono">{payment.rp_code}</p>
                            </div>
                          </TableCell>
                          <TableCell className="font-mono">{payment.stock_symbol}</TableCell>
                          <TableCell className="text-right">{payment.revenue_share_percent}%</TableCell>
                          <TableCell className="text-right font-bold text-pink-600">
                            {formatCurrency(payment.payment_amount)}
                          </TableCell>
                          <TableCell>{getRpPaymentStatusBadge(payment.status)}</TableCell>
                          <TableCell>
                            {payment.payment_reference ? (
                              <span className="font-mono text-xs">{payment.payment_reference}</span>
                            ) : (
                              <span className="text-muted-foreground text-sm">—</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openRpPaymentDialog(payment)}
                              data-testid={`update-rp-payment-${payment.id}`}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="commissions">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Users className="h-5 w-5" />
                Employee Commissions
              </CardTitle>
              <CardDescription>
                Track employee revenue share from confirmed bookings (reduced by RP allocations)
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0 md:p-6">
              {/* Commission Summary */}
              {commissionSummary.length > 0 && (
                <div className="mb-6 overflow-x-auto">
                  <h4 className="font-medium mb-2 px-4 md:px-0">Summary by Employee</h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Employee</TableHead>
                        <TableHead className="text-right">Total Profit</TableHead>
                        <TableHead className="text-right">RP Share</TableHead>
                        <TableHead className="text-right">Total Commission</TableHead>
                        <TableHead className="text-right">Pending</TableHead>
                        <TableHead className="text-right">Paid</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {commissionSummary.slice(0, 5).map((emp) => (
                        <TableRow key={emp.employee_id}>
                          <TableCell className="font-medium">{emp.employee_name}</TableCell>
                          <TableCell className="text-right">{formatCurrency(emp.total_profit)}</TableCell>
                          <TableCell className="text-right text-pink-600">{formatCurrency(emp.total_rp_share)}</TableCell>
                          <TableCell className="text-right font-bold text-green-600">{formatCurrency(emp.total_commission)}</TableCell>
                          <TableCell className="text-right text-yellow-600">{formatCurrency(emp.pending_commission + emp.calculated_commission)}</TableCell>
                          <TableCell className="text-right text-green-600">{formatCurrency(emp.paid_commission)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {/* Commission Details */}
              <h4 className="font-medium mb-2 px-4 md:px-0">Commission Details</h4>
              {employeeCommissions.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">No employee commissions found.</p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Booking #</TableHead>
                        <TableHead>Employee</TableHead>
                        <TableHead>Client</TableHead>
                        <TableHead>Stock</TableHead>
                        <TableHead className="text-right">Profit</TableHead>
                        <TableHead className="text-right">RP Share</TableHead>
                        <TableHead className="text-right">Emp Share</TableHead>
                        <TableHead className="text-right">Commission</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {employeeCommissions.map((comm) => (
                        <TableRow key={comm.booking_id} data-testid={`commission-row-${comm.booking_id}`}>
                          <TableCell className="font-mono text-sm">{comm.booking_number}</TableCell>
                          <TableCell className="font-medium">{comm.employee_name}</TableCell>
                          <TableCell>{comm.client_name}</TableCell>
                          <TableCell className="font-mono">{comm.stock_symbol}</TableCell>
                          <TableCell className="text-right">{formatCurrency(comm.profit)}</TableCell>
                          <TableCell className="text-right text-pink-600">
                            {comm.rp_share_percent > 0 ? (
                              <span>{comm.rp_share_percent}% ({formatCurrency(comm.rp_payment_amount)})</span>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell className="text-right">{comm.employee_share_percent}%</TableCell>
                          <TableCell className="text-right font-bold text-green-600">
                            {formatCurrency(comm.employee_commission_amount)}
                          </TableCell>
                          <TableCell>{getCommissionStatusBadge(comm.status)}</TableCell>
                          <TableCell>
                            {comm.status !== 'paid' && currentUser.role === 1 && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleMarkCommissionPaid(comm.booking_id)}
                                data-testid={`mark-paid-${comm.booking_id}`}
                              >
                                <CheckCircle className="h-4 w-4 mr-1" />
                                Mark Paid
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Refund Update Dialog */}
      <Dialog open={refundDialogOpen} onOpenChange={setRefundDialogOpen}>
        <DialogContent className="max-w-lg" data-testid="refund-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RotateCcw className="h-5 w-5" />
              Update Refund Request
            </DialogTitle>
            <DialogDescription>
              {selectedRefund?.booking_number} - {selectedRefund?.client_name}
            </DialogDescription>
          </DialogHeader>
          
          {selectedRefund && (
            <div className="space-y-4">
              {/* Refund Details */}
              <Card>
                <CardContent className="pt-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Refund Amount:</span>
                    <span className="font-bold text-orange-600">{formatCurrency(selectedRefund.refund_amount)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Stock:</span>
                    <span>{selectedRefund.stock_symbol}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Void Reason:</span>
                    <span className="text-sm">{selectedRefund.void_reason}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Bank Details */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Building className="h-4 w-4" />
                    Client Bank Details
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-1">
                  {selectedRefund.bank_details?.account_number ? (
                    <>
                      <p><strong>Bank:</strong> {selectedRefund.bank_details.bank_name}</p>
                      <p><strong>Account:</strong> {selectedRefund.bank_details.account_number}</p>
                      <p><strong>IFSC:</strong> {selectedRefund.bank_details.ifsc_code}</p>
                      <p><strong>Holder:</strong> {selectedRefund.bank_details.account_holder_name}</p>
                      {selectedRefund.bank_details.branch && <p><strong>Branch:</strong> {selectedRefund.bank_details.branch}</p>}
                    </>
                  ) : (
                    <p className="text-orange-600 flex items-center gap-1">
                      <AlertCircle className="h-4 w-4" />
                      No bank details available. Update client profile first.
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Update Form */}
              <div className="space-y-3">
                <div className="space-y-1">
                  <Label>Status</Label>
                  <Select value={refundForm.status} onValueChange={(v) => setRefundForm({ ...refundForm, status: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="processing">Processing</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="failed">Failed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Transaction Reference Number</Label>
                  <Input
                    value={refundForm.reference_number}
                    onChange={(e) => setRefundForm({ ...refundForm, reference_number: e.target.value })}
                    placeholder="e.g., UTR123456789"
                  />
                </div>
                <div className="space-y-1">
                  <Label>Notes</Label>
                  <Textarea
                    value={refundForm.notes}
                    onChange={(e) => setRefundForm({ ...refundForm, notes: e.target.value })}
                    placeholder="Add any notes about this refund..."
                    rows={2}
                  />
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setRefundDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleUpdateRefund} data-testid="save-refund-btn">
              <CheckCircle className="h-4 w-4 mr-2" />
              Update Refund
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* RP Payment Update Dialog */}
      <Dialog open={rpPaymentDialogOpen} onOpenChange={setRpPaymentDialogOpen}>
        <DialogContent className="max-w-lg" data-testid="rp-payment-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Update RP Payment
            </DialogTitle>
            <DialogDescription>
              {selectedRpPayment?.booking_number} - {selectedRpPayment?.rp_name}
            </DialogDescription>
          </DialogHeader>
          
          {selectedRpPayment && (
            <div className="space-y-4">
              {/* Payment Details */}
              <Card>
                <CardContent className="pt-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Payment Amount:</span>
                    <span className="font-bold text-pink-600">{formatCurrency(selectedRpPayment.payment_amount)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Stock:</span>
                    <span className="font-mono">{selectedRpPayment.stock_symbol}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Revenue Share:</span>
                    <span>{selectedRpPayment.revenue_share_percent}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Booking Profit:</span>
                    <span>{formatCurrency(selectedRpPayment.profit)}</span>
                  </div>
                </CardContent>
              </Card>

              {/* RP Details */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Building className="h-4 w-4" />
                    Referral Partner Details
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-1">
                  <p><strong>Name:</strong> {selectedRpPayment.rp_name}</p>
                  <p><strong>Code:</strong> <span className="font-mono">{selectedRpPayment.rp_code}</span></p>
                </CardContent>
              </Card>

              {/* Update Form */}
              <div className="space-y-3">
                <div className="space-y-1">
                  <Label>Status</Label>
                  <Select value={rpPaymentForm.status} onValueChange={(v) => setRpPaymentForm({ ...rpPaymentForm, status: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="processing">Processing</SelectItem>
                      <SelectItem value="paid">Paid</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Payment Date</Label>
                  <Input
                    type="date"
                    value={rpPaymentForm.payment_date}
                    onChange={(e) => setRpPaymentForm({ ...rpPaymentForm, payment_date: e.target.value })}
                  />
                </div>
                <div className="space-y-1">
                  <Label>Payment Reference Number</Label>
                  <Input
                    value={rpPaymentForm.payment_reference}
                    onChange={(e) => setRpPaymentForm({ ...rpPaymentForm, payment_reference: e.target.value })}
                    placeholder="e.g., UTR123456789"
                  />
                </div>
                <div className="space-y-1">
                  <Label>Notes</Label>
                  <Textarea
                    value={rpPaymentForm.notes}
                    onChange={(e) => setRpPaymentForm({ ...rpPaymentForm, notes: e.target.value })}
                    placeholder="Add any notes about this payment..."
                    rows={2}
                  />
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setRpPaymentDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleUpdateRpPayment} data-testid="save-rp-payment-btn">
              <CheckCircle className="h-4 w-4 mr-2" />
              Update Payment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Payment Table Component
const PaymentTable = ({ payments, formatCurrency, formatDate, title }) => {
  if (payments.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No payments found for the selected filters.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      {title && (
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent className="p-0 md:p-6">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Party</TableHead>
                <TableHead>Stock</TableHead>
                <TableHead>Tranche</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Proof</TableHead>
                <TableHead>Reference</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payments.map((payment) => (
                <TableRow key={payment.id} data-testid={`payment-row-${payment.id}`}>
                  <TableCell className="whitespace-nowrap">{formatDate(payment.payment_date)}</TableCell>
                  <TableCell>
                    <Badge className={payment.type === 'client' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                      {payment.type === 'client' ? (
                        <><ArrowDownLeft className="h-3 w-3 mr-1" />Received</>
                      ) : (
                        <><ArrowUpRight className="h-3 w-3 mr-1" />Sent</>
                      )}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium">{payment.party_name}</TableCell>
                  <TableCell>
                    <span className="font-mono text-sm">{payment.stock_symbol}</span>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">#{payment.tranche_number}</Badge>
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(payment.amount)}
                  </TableCell>
                  <TableCell>
                    <Badge 
                      variant="outline"
                      className={
                        payment.payment_status === 'completed' ? 'bg-green-50 text-green-700 border-green-200' :
                        payment.payment_status === 'partial' ? 'bg-yellow-50 text-yellow-700 border-yellow-200' :
                        'bg-gray-50 text-gray-700'
                      }
                    >
                      {payment.payment_status?.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {payment.proof_url ? (
                      <a 
                        href={payment.proof_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="flex items-center text-blue-600 hover:text-blue-800"
                      >
                        <FileText className="h-4 w-4 mr-1" />
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-muted-foreground text-sm">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-xs text-muted-foreground">{payment.reference_number}</span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
};

export default Finance;
