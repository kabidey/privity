import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '../utils/api';
import { FileDown, FileSpreadsheet, Filter, X } from 'lucide-react';

const Reports = () => {
  const [reportData, setReportData] = useState([]);
  const [clients, setClients] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    client_id: '',
    stock_id: '',
  });
  const [stats, setStats] = useState({
    totalProfit: 0,
    totalLoss: 0,
    netPL: 0,
    totalTransactions: 0,
  });

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const [clientsRes, stocksRes] = await Promise.all([
        api.get('/clients'),
        api.get('/stocks'),
      ]);
      setClients(clientsRes.data);
      setStocks(stocksRes.data);
      await fetchReport();
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const fetchReport = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.client_id) params.append('client_id', filters.client_id);
      if (filters.stock_id) params.append('stock_id', filters.stock_id);

      const response = await api.get(`/reports/pnl?${params.toString()}`);
      const data = response.data;
      
      // Handle both array response and object with items
      const items = Array.isArray(data) ? data : (data.items || []);
      const summaryFromApi = !Array.isArray(data) ? data.summary : null;
      
      setReportData(items);

      // Use summary from API if available, otherwise calculate
      if (summaryFromApi) {
        setStats({
          totalProfit: summaryFromApi.total_profit || 0,
          totalLoss: summaryFromApi.total_loss || 0,
          netPL: summaryFromApi.net_pl || 0,
          totalTransactions: items.length,
        });
      } else {
        // Calculate stats
        let totalProfit = 0;
        let totalLoss = 0;
        items.forEach((item) => {
          if (item.profit_loss) {
            if (item.profit_loss > 0) {
              totalProfit += item.profit_loss;
            } else {
              totalLoss += Math.abs(item.profit_loss);
            }
          }
        });

        setStats({
          totalProfit,
          totalLoss,
          netPL: totalProfit - totalLoss,
          totalTransactions: items.length,
        });
      }
    } catch (error) {
      toast.error('Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const applyFilters = () => {
    fetchReport();
  };

  const clearFilters = () => {
    setFilters({
      start_date: '',
      end_date: '',
      client_id: '',
      stock_id: '',
    });
    setTimeout(() => fetchReport(), 0);
  };

  const handleExportExcel = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);

      const response = await api.get(`/reports/export/excel?${params.toString()}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'pnl_report.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Excel report downloaded');
    } catch (error) {
      toast.error('Failed to export Excel');
    }
  };

  const handleExportPDF = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);

      const response = await api.get(`/reports/export/pdf?${params.toString()}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'pnl_report.pdf');
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('PDF report downloaded');
    } catch (error) {
      toast.error('Failed to export PDF');
    }
  };

  const hasActiveFilters = filters.start_date || filters.end_date || filters.client_id || filters.stock_id;

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="reports-page">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Revenue Reports</h1>
          <p className="text-muted-foreground text-base">Comprehensive revenue analysis of all bookings</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="rounded-sm"
            onClick={handleExportExcel}
            data-testid="export-excel-button"
          >
            <FileSpreadsheet className="mr-2 h-4 w-4" strokeWidth={1.5} />
            Export Excel
          </Button>
          <Button
            variant="outline"
            className="rounded-sm"
            onClick={handleExportPDF}
            data-testid="export-pdf-button"
          >
            <FileDown className="mr-2 h-4 w-4" strokeWidth={1.5} />
            Export PDF
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="border shadow-sm mb-6">
        <CardHeader className="pb-4">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 items-end">
            <div className="space-y-2">
              <Label htmlFor="start_date" className="text-xs">Start Date</Label>
              <Input
                id="start_date"
                data-testid="filter-start-date"
                type="date"
                value={filters.start_date}
                onChange={(e) => handleFilterChange('start_date', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end_date" className="text-xs">End Date</Label>
              <Input
                id="end_date"
                data-testid="filter-end-date"
                type="date"
                value={filters.end_date}
                onChange={(e) => handleFilterChange('end_date', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Client</Label>
              <Select
                value={filters.client_id}
                onValueChange={(value) => handleFilterChange('client_id', value === 'all' ? '' : value)}
              >
                <SelectTrigger data-testid="filter-client-select">
                  <SelectValue placeholder="All Clients" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Clients</SelectItem>
                  {clients.map((client) => (
                    <SelectItem key={client.id} value={client.id}>
                      {client.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Stock</Label>
              <Select
                value={filters.stock_id}
                onValueChange={(value) => handleFilterChange('stock_id', value === 'all' ? '' : value)}
              >
                <SelectTrigger data-testid="filter-stock-select">
                  <SelectValue placeholder="All Stocks" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Stocks</SelectItem>
                  {stocks.map((stock) => (
                    <SelectItem key={stock.id} value={stock.id}>
                      {stock.symbol}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Button onClick={applyFilters} className="rounded-sm flex-1" data-testid="apply-filters-button">
                Apply
              </Button>
              {hasActiveFilters && (
                <Button variant="outline" onClick={clearFilters} className="rounded-sm" data-testid="clear-filters-button">
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card className="border shadow-sm" data-testid="transactions-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Transactions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono">{stats.totalTransactions}</div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="profit-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Total Profit
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono text-green-600">
              ₹{stats.totalProfit.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="loss-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Total Loss
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono text-red-600">
              ₹{stats.totalLoss.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="net-pnl-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Net Revenue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold mono ${stats.netPL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              ₹{stats.netPL.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Report Table */}
      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle>Detailed Revenue Report</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-12 text-center text-muted-foreground">Loading...</div>
          ) : reportData.length === 0 ? (
            <div className="text-center py-12" data-testid="no-report-data-message">
              <p className="text-muted-foreground">No booking data available for the selected filters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Client</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Stock</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Quantity</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Landing Price</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Sell Price</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Date</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Status</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Revenue</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reportData.map((item, index) => (
                    <TableRow key={item.booking_id || index} className="table-row" data-testid="report-row">
                      <TableCell className="font-medium">{item.client_name}</TableCell>
                      <TableCell className="mono text-sm font-semibold">{item.stock_symbol}</TableCell>
                      <TableCell className="mono">{item.quantity}</TableCell>
                      <TableCell className="mono">₹{item.buying_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</TableCell>
                      <TableCell className="mono">
                        {item.selling_price ? `₹${item.selling_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}
                      </TableCell>
                      <TableCell className="text-sm">{item.booking_date ? new Date(item.booking_date).toLocaleDateString('en-IN') : '-'}</TableCell>
                      <TableCell>
                        <Badge variant={item.status === 'open' ? 'default' : 'secondary'}>
                          {(item.status || 'unknown').toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="mono font-semibold">
                        {item.profit_loss !== null && item.profit_loss !== undefined ? (
                          <span className={item.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}>
                            ₹{item.profit_loss.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </span>
                        ) : (
                          '-'
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
    </div>
  );
};

export default Reports;
