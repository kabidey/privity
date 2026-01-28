import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  Wallet, ArrowDownLeft, ArrowUpRight, FileSpreadsheet, Download, 
  RefreshCw, Calendar, TrendingUp, TrendingDown, DollarSign, FileText,
  ExternalLink
} from 'lucide-react';

const Finance = () => {
  const [payments, setPayments] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [filters, setFilters] = useState({
    type: 'all',
    startDate: '',
    endDate: ''
  });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPELevel = currentUser.role === 1 || currentUser.role === 2;

  useEffect(() => {
    if (isPELevel) {
      fetchData();
    }
  }, [filters, isPELevel]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.type !== 'all') params.append('payment_type', filters.type);
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);

      const [paymentsRes, summaryRes] = await Promise.all([
        api.get(`/finance/payments?${params.toString()}`),
        api.get(`/finance/summary?${params.toString()}`)
      ]);

      setPayments(paymentsRes.data);
      setSummary(summaryRes.data);
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

  const clientPayments = payments.filter(p => p.type === 'client');
  const vendorPayments = payments.filter(p => p.type === 'vendor');

  if (!isPELevel) {
    return (
      <div className="p-8 text-center">
        <h1 className="text-2xl font-bold text-red-600">Access Denied</h1>
        <p className="text-muted-foreground">Only PE Desk or PE Manager can access finance data.</p>
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
          <p className="text-muted-foreground text-sm md:text-base">Track all payments sent and received</p>
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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="border-l-4 border-l-green-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Received</p>
                  <p className="text-xl md:text-2xl font-bold text-green-600">{formatCurrency(summary.total_received)}</p>
                </div>
                <ArrowDownLeft className="h-8 w-8 text-green-500 opacity-50" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{summary.client_payments_count} payments</p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-red-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Sent</p>
                  <p className="text-xl md:text-2xl font-bold text-red-600">{formatCurrency(summary.total_sent)}</p>
                </div>
                <ArrowUpRight className="h-8 w-8 text-red-500 opacity-50" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{summary.vendor_payments_count} payments</p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Net Flow</p>
                  <p className={`text-xl md:text-2xl font-bold ${summary.net_flow >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(summary.net_flow)}
                  </p>
                </div>
                {summary.net_flow >= 0 ? (
                  <TrendingUp className="h-8 w-8 text-green-500 opacity-50" />
                ) : (
                  <TrendingDown className="h-8 w-8 text-red-500 opacity-50" />
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Received - Sent</p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-purple-500">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Transactions</p>
                  <p className="text-xl md:text-2xl font-bold">{payments.length}</p>
                </div>
                <DollarSign className="h-8 w-8 text-purple-500 opacity-50" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">All payment tranches</p>
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
                data-testid="filter-start-date"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">End Date</Label>
              <Input
                type="date"
                value={filters.endDate}
                onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
                className="w-40"
                data-testid="filter-end-date"
              />
            </div>
            <Button 
              variant="ghost" 
              onClick={() => setFilters({ type: 'all', startDate: '', endDate: '' })}
              className="text-sm"
            >
              Clear Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Payments Tabs */}
      <Tabs defaultValue="all" className="w-full">
        <TabsList className="grid w-full grid-cols-3 max-w-md">
          <TabsTrigger value="all" data-testid="tab-all">All ({payments.length})</TabsTrigger>
          <TabsTrigger value="client" data-testid="tab-client">
            <ArrowDownLeft className="h-3 w-3 mr-1" />
            Received ({clientPayments.length})
          </TabsTrigger>
          <TabsTrigger value="vendor" data-testid="tab-vendor">
            <ArrowUpRight className="h-3 w-3 mr-1" />
            Sent ({vendorPayments.length})
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
      </Tabs>
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
