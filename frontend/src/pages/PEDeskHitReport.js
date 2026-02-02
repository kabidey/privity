import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '../utils/api';
import { TrendingUp, DollarSign, BarChart3, FileSpreadsheet, Calendar, Filter, Download, Package } from 'lucide-react';

const PEDeskHitReport = () => {
  const [loading, setLoading] = useState(true);
  const [reportData, setReportData] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    stock_id: ''
  });
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchStocks();
    fetchReport();
  }, []);

  const fetchStocks = async () => {
    try {
      const response = await api.get('/stocks');
      setStocks(response.data || []);
    } catch (error) {
      console.error('Failed to load stocks', error);
    }
  };

  const fetchReport = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.stock_id) params.append('stock_id', filters.stock_id);

      const response = await api.get(`/reports/pe-desk-hit?${params.toString()}`);
      setReportData(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load HIT report');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.stock_id) params.append('stock_id', filters.stock_id);
      params.append('format', format);

      const response = await api.get(`/reports/pe-desk-hit/export?${params.toString()}`, {
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `pe_desk_hit_report.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success(`Report exported as ${format.toUpperCase()}`);
    } catch (error) {
      toast.error('Failed to export report');
    } finally {
      setExporting(false);
    }
  };

  const formatCurrency = (value) => {
    return `₹${(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="pe-desk-hit-report-page">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-amber-100 rounded-lg">
            <DollarSign className="h-6 w-6 text-amber-600" />
          </div>
          <h1 className="text-4xl font-bold">PE Desk HIT Report</h1>
        </div>
        <p className="text-muted-foreground text-base">
          Track the margin captured between Landing Price (LP) and Weighted Average Price (WAP)
        </p>
        <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800 inline-block">
          <strong>HIT Formula:</strong> (LP - WAP) × Quantity
        </div>
      </div>

      {/* Filters */}
      <Card className="mb-6 border shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Start Date</label>
              <Input
                type="date"
                value={filters.start_date}
                onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
                data-testid="filter-start-date"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">End Date</label>
              <Input
                type="date"
                value={filters.end_date}
                onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
                data-testid="filter-end-date"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Stock</label>
              <Select
                value={filters.stock_id}
                onValueChange={(value) => setFilters({ ...filters, stock_id: value === 'all' ? '' : value })}
              >
                <SelectTrigger data-testid="filter-stock">
                  <SelectValue placeholder="All Stocks" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Stocks</SelectItem>
                  {stocks.map((stock) => (
                    <SelectItem key={stock.id} value={stock.id}>
                      {stock.symbol} - {stock.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button onClick={fetchReport} className="w-full" data-testid="apply-filters-btn">
                <Filter className="h-4 w-4 mr-2" />
                Apply Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="text-center py-12">Loading report...</div>
      ) : !reportData ? (
        <div className="text-center py-12">No data available</div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <Card className="border shadow-sm" data-testid="total-bookings-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Total Bookings
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold mono">{reportData.summary.total_bookings}</div>
              </CardContent>
            </Card>

            <Card className="border shadow-sm" data-testid="total-quantity-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Package className="h-4 w-4" />
                  Total Quantity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold mono">{reportData.summary.total_quantity.toLocaleString('en-IN')}</div>
              </CardContent>
            </Card>

            <Card className="border shadow-sm bg-gradient-to-br from-amber-50 to-orange-50" data-testid="total-hit-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-amber-700 uppercase tracking-wider flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  Total HIT
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold mono text-amber-700">
                  {formatCurrency(reportData.summary.total_hit)}
                </div>
              </CardContent>
            </Card>

            <Card className="border shadow-sm" data-testid="avg-hit-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Avg HIT/Share
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold mono text-emerald-600">
                  {formatCurrency(reportData.summary.avg_hit_per_share)}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Stock Summary */}
          {reportData.by_stock && reportData.by_stock.length > 0 && (
            <Card className="mb-6 border shadow-sm">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>HIT by Stock</span>
                  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                    {reportData.by_stock.length} Stocks
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {reportData.by_stock.map((stock, idx) => (
                    <div
                      key={idx}
                      className="p-4 border rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
                    >
                      <div className="font-bold text-lg mono">{stock.stock_symbol}</div>
                      <div className="text-sm text-muted-foreground mb-2">{stock.stock_name}</div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <span className="text-muted-foreground">Qty:</span>
                          <span className="font-semibold ml-1">{stock.total_quantity.toLocaleString('en-IN')}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Bookings:</span>
                          <span className="font-semibold ml-1">{stock.booking_count}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Avg Diff:</span>
                          <span className="font-semibold ml-1 text-emerald-600">{formatCurrency(stock.avg_lp_wap_diff)}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Total HIT:</span>
                          <span className="font-bold ml-1 text-amber-700">{formatCurrency(stock.total_hit)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Detailed Report Table */}
          <Card className="border shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center justify-between flex-wrap gap-4">
                <span>Detailed Report</span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleExport('xlsx')}
                    disabled={exporting}
                    data-testid="export-excel-btn"
                  >
                    <FileSpreadsheet className="h-4 w-4 mr-2" />
                    Export Excel
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleExport('pdf')}
                    disabled={exporting}
                    data-testid="export-pdf-btn"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Export PDF
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {reportData.details.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No completed DP transfers found for the selected filters
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold">Booking #</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold">Transfer Date</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold">Stock</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold">Client</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold text-right">Qty</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold text-right text-blue-600">WAP</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold text-right text-emerald-600">LP</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold text-right">LP - WAP</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold text-right text-amber-600">HIT</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {reportData.details.map((item) => (
                        <TableRow key={item.booking_id} className="table-row" data-testid="hit-report-row">
                          <TableCell className="font-mono font-semibold">{item.booking_number}</TableCell>
                          <TableCell className="text-sm">{formatDate(item.dp_transfer_date)}</TableCell>
                          <TableCell>
                            <div>
                              <span className="font-bold mono">{item.stock_symbol}</span>
                              <span className="text-xs text-muted-foreground block">{item.stock_name}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div>
                              <span className="font-medium">{item.client_name}</span>
                              {item.client_otc_ucc && (
                                <span className="text-xs text-muted-foreground block">{item.client_otc_ucc}</span>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-right mono">{item.quantity.toLocaleString('en-IN')}</TableCell>
                          <TableCell className="text-right mono text-blue-600">{formatCurrency(item.wap)}</TableCell>
                          <TableCell className="text-right mono text-emerald-600">{formatCurrency(item.lp)}</TableCell>
                          <TableCell className="text-right mono">
                            <span className={item.lp_wap_diff >= 0 ? 'text-green-600' : 'text-red-600'}>
                              {formatCurrency(item.lp_wap_diff)}
                            </span>
                          </TableCell>
                          <TableCell className="text-right mono font-bold">
                            <span className={item.hit >= 0 ? 'text-amber-700' : 'text-red-600'}>
                              {formatCurrency(item.hit)}
                            </span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Report Footer */}
          <div className="mt-4 text-sm text-muted-foreground flex items-center justify-between">
            <span>
              Generated by {reportData.generated_by} at {formatDate(reportData.generated_at)}
            </span>
            <span className="text-amber-600">
              PE Desk Confidential Report
            </span>
          </div>
        </>
      )}
    </div>
  );
};

export default PEDeskHitReport;
