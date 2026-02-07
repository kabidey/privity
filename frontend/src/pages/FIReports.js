import { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { 
  Download, RefreshCw, Calendar, TrendingUp, TrendingDown,
  PieChart, BarChart3, Wallet, DollarSign, Clock, FileText,
  ArrowUpRight, ArrowDownRight, Building2, Shield
} from 'lucide-react';

const FIReports = () => {
  const [activeTab, setActiveTab] = useState('holdings');
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Holdings data
  const [holdingsData, setHoldingsData] = useState(null);
  
  // Cash flow data
  const [cashFlowData, setCashFlowData] = useState(null);
  const [cashFlowMonths, setCashFlowMonths] = useState(12);
  
  // Maturity data
  const [maturityData, setMaturityData] = useState(null);
  
  // Analytics data
  const [analyticsData, setAnalyticsData] = useState(null);
  
  // Transactions
  const [transactions, setTransactions] = useState([]);

  const { isPELevel } = useCurrentUser();

  const fetchClients = async () => {
    try {
      const response = await api.get('/api/clients?limit=500');
      setClients(response.data.clients || []);
    } catch (error) {
      console.error('Error fetching clients:', error);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  const fetchHoldings = async () => {
    if (!selectedClient) {
      toast.error('Please select a client');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.get(`/api/fixed-income/reports/holdings?client_id=${selectedClient}`);
      setHoldingsData(response.data);
    } catch (error) {
      console.error('Error fetching holdings:', error);
      toast.error('Failed to load holdings');
    } finally {
      setLoading(false);
    }
  };

  const fetchCashFlow = async () => {
    if (!selectedClient) {
      toast.error('Please select a client');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.get(`/api/fixed-income/reports/cash-flow-calendar?client_id=${selectedClient}&months_ahead=${cashFlowMonths}`);
      setCashFlowData(response.data);
    } catch (error) {
      console.error('Error fetching cash flow:', error);
      toast.error('Failed to load cash flow');
    } finally {
      setLoading(false);
    }
  };

  const fetchMaturity = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedClient) params.append('client_id', selectedClient);
      params.append('months_ahead', '24');
      
      const response = await api.get(`/api/fixed-income/reports/maturity-schedule?${params}`);
      setMaturityData(response.data);
    } catch (error) {
      console.error('Error fetching maturity:', error);
      toast.error('Failed to load maturity schedule');
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedClient) params.append('client_id', selectedClient);
      
      const response = await api.get(`/api/fixed-income/reports/analytics/portfolio-summary?${params}`);
      setAnalyticsData(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedClient) params.append('client_id', selectedClient);
      params.append('limit', '100');
      
      const response = await api.get(`/api/fixed-income/reports/transactions?${params}`);
      setTransactions(response.data.transactions || []);
    } catch (error) {
      console.error('Error fetching transactions:', error);
      toast.error('Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async (type) => {
    if (!selectedClient) {
      toast.error('Please select a client');
      return;
    }

    try {
      const url = type === 'holdings' 
        ? `/api/fixed-income/reports/export/holdings-csv?client_id=${selectedClient}`
        : `/api/fixed-income/reports/export/cash-flow-csv?client_id=${selectedClient}&months_ahead=${cashFlowMonths}`;
      
      const response = await api.get(url, { responseType: 'blob' });
      
      const blob = new Blob([response.data], { type: 'text/csv' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `fi_${type}_${selectedClient}_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      a.remove();
      
      toast.success('Export downloaded');
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    
    // Fetch data based on tab
    switch (tab) {
      case 'holdings':
        if (selectedClient) fetchHoldings();
        break;
      case 'cashflow':
        if (selectedClient) fetchCashFlow();
        break;
      case 'maturity':
        fetchMaturity();
        break;
      case 'analytics':
        fetchAnalytics();
        break;
      case 'transactions':
        fetchTransactions();
        break;
    }
  };

  useEffect(() => {
    if (selectedClient) {
      handleTabChange(activeTab);
    }
  }, [selectedClient]);

  const formatCurrency = (value) => {
    return `₹${parseFloat(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  };

  const getRatingColor = (rating) => {
    if (!rating) return 'bg-gray-200';
    if (rating.startsWith('AAA')) return 'bg-emerald-500';
    if (rating.startsWith('AA')) return 'bg-emerald-400';
    if (rating.startsWith('A')) return 'bg-yellow-400';
    if (rating.startsWith('BBB')) return 'bg-orange-400';
    return 'bg-red-400';
  };

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="fi-reports">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-emerald-600" />
            Fixed Income - Reports
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Portfolio analytics, cash flows and maturity schedules
          </p>
        </div>
      </div>

      {/* Client Selector */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <Label>Select Client</Label>
              <Select value={selectedClient} onValueChange={setSelectedClient}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a client" />
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
            <Button variant="outline" onClick={() => handleTabChange(activeTab)}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="holdings">Holdings</TabsTrigger>
          <TabsTrigger value="cashflow">Cash Flow</TabsTrigger>
          <TabsTrigger value="maturity">Maturity</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="transactions">Transactions</TabsTrigger>
        </TabsList>

        {/* Holdings Tab */}
        <TabsContent value="holdings" className="space-y-4">
          {loading ? (
            <div className="space-y-4">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          ) : holdingsData ? (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Total Cost</p>
                        <p className="text-xl font-bold">{formatCurrency(holdingsData.summary?.total_cost)}</p>
                      </div>
                      <Wallet className="h-8 w-8 text-gray-300" />
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Current Value</p>
                        <p className="text-xl font-bold">{formatCurrency(holdingsData.summary?.total_current_value)}</p>
                      </div>
                      <TrendingUp className="h-8 w-8 text-emerald-300" />
                    </div>
                  </CardContent>
                </Card>
                <Card className={parseFloat(holdingsData.summary?.total_unrealized_pnl || 0) >= 0 ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-red-50 dark:bg-red-900/20'}>
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Unrealized P&L</p>
                        <p className={`text-xl font-bold ${parseFloat(holdingsData.summary?.total_unrealized_pnl || 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                          {formatCurrency(holdingsData.summary?.total_unrealized_pnl)}
                        </p>
                      </div>
                      {parseFloat(holdingsData.summary?.total_unrealized_pnl || 0) >= 0 ? (
                        <ArrowUpRight className="h-8 w-8 text-emerald-500" />
                      ) : (
                        <ArrowDownRight className="h-8 w-8 text-red-500" />
                      )}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Return</p>
                        <p className={`text-xl font-bold ${parseFloat(holdingsData.summary?.pnl_percentage || 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                          {holdingsData.summary?.pnl_percentage}%
                        </p>
                      </div>
                      <PieChart className="h-8 w-8 text-gray-300" />
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Holdings Table */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-lg">Holdings ({holdingsData.holdings?.length || 0})</CardTitle>
                  <Button variant="outline" size="sm" onClick={() => handleExportCSV('holdings')}>
                    <Download className="h-4 w-4 mr-2" />
                    Export CSV
                  </Button>
                </CardHeader>
                <CardContent className="p-0">
                  <ScrollArea className="h-[400px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Issuer</TableHead>
                          <TableHead>ISIN</TableHead>
                          <TableHead className="text-right">Qty</TableHead>
                          <TableHead className="text-right">Avg Cost</TableHead>
                          <TableHead className="text-right">Current</TableHead>
                          <TableHead className="text-right">Value</TableHead>
                          <TableHead className="text-right">P&L</TableHead>
                          <TableHead>Rating</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {holdingsData.holdings?.map((h, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-medium max-w-[150px] truncate">
                              {h.issuer_name}
                            </TableCell>
                            <TableCell className="font-mono text-xs">{h.isin}</TableCell>
                            <TableCell className="text-right">{parseInt(h.quantity).toLocaleString()}</TableCell>
                            <TableCell className="text-right font-mono">₹{h.average_cost}</TableCell>
                            <TableCell className="text-right font-mono">₹{h.current_price}</TableCell>
                            <TableCell className="text-right font-mono">{formatCurrency(h.current_value)}</TableCell>
                            <TableCell className={`text-right font-mono ${parseFloat(h.unrealized_pnl) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                              {formatCurrency(h.unrealized_pnl)}
                              <br />
                              <span className="text-xs">({h.pnl_percentage}%)</span>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{h.credit_rating}</Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-gray-500">
                Select a client to view holdings
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Cash Flow Tab */}
        <TabsContent value="cashflow" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-emerald-600" />
                  Cash Flow Calendar
                </CardTitle>
                <CardDescription>
                  Upcoming coupon payments and principal redemptions
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Select value={cashFlowMonths.toString()} onValueChange={(v) => setCashFlowMonths(parseInt(v))}>
                  <SelectTrigger className="w-[120px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="6">6 months</SelectItem>
                    <SelectItem value="12">12 months</SelectItem>
                    <SelectItem value="24">24 months</SelectItem>
                    <SelectItem value="36">36 months</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline" size="sm" onClick={() => handleExportCSV('cashflow')}>
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-2">
                  {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-12 w-full" />)}
                </div>
              ) : cashFlowData ? (
                <>
                  {/* Summary */}
                  <div className="grid grid-cols-3 gap-4 mb-6">
                    <Card className="bg-emerald-50 dark:bg-emerald-900/20">
                      <CardContent className="pt-4">
                        <p className="text-sm text-gray-500">Total Coupon Income</p>
                        <p className="text-xl font-bold text-emerald-600">
                          {formatCurrency(cashFlowData.summary?.total_coupon_income)}
                        </p>
                      </CardContent>
                    </Card>
                    <Card className="bg-blue-50 dark:bg-blue-900/20">
                      <CardContent className="pt-4">
                        <p className="text-sm text-gray-500">Principal Redemptions</p>
                        <p className="text-xl font-bold text-blue-600">
                          {formatCurrency(cashFlowData.summary?.total_principal_redemptions)}
                        </p>
                      </CardContent>
                    </Card>
                    <Card className="bg-purple-50 dark:bg-purple-900/20">
                      <CardContent className="pt-4">
                        <p className="text-sm text-gray-500">Total Cash Flows</p>
                        <p className="text-xl font-bold text-purple-600">
                          {formatCurrency(cashFlowData.summary?.total_cash_flows)}
                        </p>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Cash Flow List */}
                  <ScrollArea className="h-[400px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Date</TableHead>
                          <TableHead>Issuer</TableHead>
                          <TableHead>ISIN</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead className="text-right">Amount</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {cashFlowData.cash_flows?.map((cf, idx) => (
                          <TableRow key={idx}>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Calendar className="h-4 w-4 text-gray-400" />
                                {new Date(cf.date).toLocaleDateString('en-IN', { 
                                  day: '2-digit', 
                                  month: 'short', 
                                  year: 'numeric' 
                                })}
                              </div>
                            </TableCell>
                            <TableCell className="max-w-[150px] truncate">{cf.issuer_name}</TableCell>
                            <TableCell className="font-mono text-xs">{cf.isin}</TableCell>
                            <TableCell>
                              <Badge variant={cf.type === 'coupon' ? 'default' : cf.type === 'principal' ? 'secondary' : 'outline'}>
                                {cf.type}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-mono font-semibold text-emerald-600">
                              {formatCurrency(cf.amount)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </>
              ) : (
                <p className="text-center text-gray-500 py-8">Select a client to view cash flows</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Maturity Tab */}
        <TabsContent value="maturity" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-amber-600" />
                Maturity Schedule
              </CardTitle>
              <CardDescription>
                Bonds maturing in the next 24 months
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-2">
                  {[1,2,3].map(i => <Skeleton key={i} className="h-16 w-full" />)}
                </div>
              ) : maturityData ? (
                <>
                  <div className="mb-4 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                    <p className="text-sm text-gray-600">Total Principal Maturing</p>
                    <p className="text-2xl font-bold text-amber-600">{formatCurrency(maturityData.total_principal)}</p>
                    <p className="text-sm text-gray-500">{maturityData.count} instruments</p>
                  </div>

                  <ScrollArea className="h-[350px]">
                    <div className="space-y-3">
                      {maturityData.maturities?.map((m, idx) => (
                        <Card key={idx} className="p-4">
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-semibold">{m.issuer_name}</p>
                              <p className="text-sm text-gray-500">{m.isin}</p>
                            </div>
                            <div className="text-right">
                              <p className="font-mono font-bold">{formatCurrency(m.principal_amount)}</p>
                              <p className="text-sm text-amber-600 flex items-center gap-1 justify-end">
                                <Calendar className="h-3 w-3" />
                                {new Date(m.maturity_date).toLocaleDateString('en-IN', { 
                                  day: '2-digit', 
                                  month: 'short', 
                                  year: 'numeric' 
                                })}
                              </p>
                            </div>
                          </div>
                          <div className="mt-2 flex gap-4 text-xs text-gray-500">
                            <span>Qty: {m.quantity?.toLocaleString()}</span>
                            <span>Face Value: ₹{m.face_value}</span>
                            <span>Coupon: {m.coupon_rate}%</span>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </ScrollArea>
                </>
              ) : (
                <p className="text-center text-gray-500 py-8">No maturity data available</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-4">
          {loading ? (
            <div className="grid grid-cols-2 gap-4">
              {[1,2,3,4].map(i => <Skeleton key={i} className="h-48 w-full" />)}
            </div>
          ) : analyticsData ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Portfolio Value */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-gray-500">Portfolio Value</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-emerald-600">{formatCurrency(analyticsData.total_portfolio_value)}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Weighted Avg Yield: <span className="font-semibold">{analyticsData.weighted_average_yield}%</span>
                  </p>
                </CardContent>
              </Card>

              {/* Rating Distribution */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
                    <Shield className="h-4 w-4" />
                    Rating Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(analyticsData.rating_distribution || {}).map(([rating, pct]) => (
                      <div key={rating} className="flex items-center gap-2">
                        <span className="w-12 text-xs font-medium">{rating}</span>
                        <Progress value={parseFloat(pct)} className="flex-1" />
                        <span className="w-12 text-xs text-right">{pct}%</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Maturity Distribution */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Maturity Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(analyticsData.maturity_distribution || {}).map(([bucket, pct]) => (
                      <div key={bucket} className="flex items-center gap-2">
                        <span className="w-12 text-xs font-medium">{bucket}</span>
                        <Progress value={parseFloat(pct)} className="flex-1" />
                        <span className="w-12 text-xs text-right">{pct}%</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Issuer Concentration */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
                    <Building2 className="h-4 w-4" />
                    Issuer Concentration (Top 5)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(analyticsData.issuer_concentration || {}).slice(0, 5).map(([issuer, pct]) => (
                      <div key={issuer} className="flex items-center gap-2">
                        <span className="flex-1 text-xs truncate">{issuer}</span>
                        <Progress value={parseFloat(pct)} className="w-24" />
                        <span className="w-12 text-xs text-right">{pct}%</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-gray-500">
                Select a client to view analytics
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Transactions Tab */}
        <TabsContent value="transactions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-blue-600" />
                Transaction History
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {loading ? (
                <div className="p-4 space-y-2">
                  {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-12 w-full" />)}
                </div>
              ) : (
                <ScrollArea className="h-[450px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Txn No.</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Issuer</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead className="text-right">Qty</TableHead>
                        <TableHead className="text-right">Price</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {transactions.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={8} className="text-center py-8 text-gray-500">
                            No transactions found
                          </TableCell>
                        </TableRow>
                      ) : (
                        transactions.map((txn) => (
                          <TableRow key={txn.id}>
                            <TableCell className="font-mono text-xs">{txn.transaction_number}</TableCell>
                            <TableCell>{txn.transaction_date}</TableCell>
                            <TableCell className="max-w-[120px] truncate">{txn.issuer_name}</TableCell>
                            <TableCell>
                              <Badge variant={txn.transaction_type?.includes('buy') ? 'default' : 'secondary'}>
                                {txn.transaction_type?.replace('_', ' ')}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">{txn.quantity?.toLocaleString()}</TableCell>
                            <TableCell className="text-right font-mono">₹{txn.dirty_price}</TableCell>
                            <TableCell className="text-right font-mono">{formatCurrency(txn.net_amount)}</TableCell>
                            <TableCell>
                              <Badge variant={txn.settlement_status === 'deal_closed' ? 'default' : 'outline'}>
                                {txn.settlement_status?.replace('_', ' ')}
                              </Badge>
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
    </div>
  );
};

export default FIReports;
