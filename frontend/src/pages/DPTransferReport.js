import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import api from '../utils/api';
import { Download, FileSpreadsheet, CheckCircle, CreditCard, Building2, Calendar, Send, Check } from 'lucide-react';

const DPTransferReport = () => {
  const navigate = useNavigate();
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [transferDialog, setTransferDialog] = useState({ open: false, record: null });
  const [transferNotes, setTransferNotes] = useState('');
  const [transferLoading, setTransferLoading] = useState(false);

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const canAccess = currentUser.role === 1 || currentUser.role === 2;
  const isPEDesk = currentUser.role === 1;

  useEffect(() => {
    if (!canAccess) {
      toast.error('Access denied. Only PE Desk and Zonal Manager can access this report.');
      navigate('/');
      return;
    }
    fetchReport();
  }, [canAccess, navigate]);

  const fetchReport = async () => {
    try {
      const response = await api.get('/dp-transfer-report');
      setRecords(response.data);
    } catch (error) {
      toast.error('Failed to load DP transfer report');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    try {
      const response = await api.get(`/dp-transfer-report/export?format=${format}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `dp_transfer_report.${format === 'excel' ? 'xlsx' : 'csv'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success(`Report exported as ${format.toUpperCase()}`);
    } catch (error) {
      toast.error('Failed to export report');
    }
  };

  const handleTransferConfirm = async () => {
    if (!transferDialog.record) return;
    
    setTransferLoading(true);
    try {
      await api.put(`/bookings/${transferDialog.record.booking_id}/confirm-transfer`, {
        notes: transferNotes || null
      });
      toast.success('Stock transfer confirmed! Client has been notified via email.');
      setTransferDialog({ open: false, record: null });
      setTransferNotes('');
      fetchReport(); // Refresh to remove the transferred record
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to confirm transfer');
    } finally {
      setTransferLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="dp-transfer-report-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Building2 className="h-8 w-8" />
            DP Transfer Report
          </h1>
          <p className="text-muted-foreground">Bookings with full payment received - ready for stock transfer</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => handleExport('csv')} data-testid="export-csv">
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
          <Button onClick={() => handleExport('excel')} data-testid="export-excel">
            <FileSpreadsheet className="h-4 w-4 mr-2" />
            Export Excel
          </Button>
        </div>
      </div>

      {/* Summary Card */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="text-sm text-muted-foreground">Ready for Transfer</span>
            </div>
            <p className="text-2xl font-bold">{records.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-blue-500" />
              <span className="text-sm text-muted-foreground">Total Value</span>
            </div>
            <p className="text-2xl font-bold">
              {formatCurrency(records.reduce((sum, r) => sum + r.total_amount, 0))}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-purple-500" />
              <span className="text-sm text-muted-foreground">Unique Clients</span>
            </div>
            <p className="text-2xl font-bold">
              {new Set(records.map(r => r.pan_number)).size}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-orange-500" />
              <span className="text-sm text-muted-foreground">Latest Completion</span>
            </div>
            <p className="text-lg font-bold">
              {records.length > 0 ? formatDate(records[0].payment_completed_at) : 'N/A'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Report Table */}
      <Card>
        <CardHeader>
          <CardTitle>Transfer Records</CardTitle>
          <CardDescription>
            Bookings with full payment received are eligible for stock transfer to client's DP
          </CardDescription>
        </CardHeader>
        <CardContent>
          {records.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No bookings ready for DP transfer</p>
              <p className="text-sm">Full payment must be received before transfer</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Client Name</TableHead>
                    <TableHead>PAN Number</TableHead>
                    <TableHead>DP ID</TableHead>
                    <TableHead>Stock</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Payment Date</TableHead>
                    <TableHead>Status</TableHead>
                    {isPEDesk && <TableHead className="text-center">Action</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {records.map((record) => (
                    <TableRow key={record.booking_id}>
                      <TableCell className="font-medium">{record.client_name}</TableCell>
                      <TableCell>
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {record.pan_number}
                        </code>
                      </TableCell>
                      <TableCell>
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {record.dp_id}
                        </code>
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium">{record.stock_symbol}</p>
                          <p className="text-xs text-muted-foreground">{record.isin_number}</p>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">{record.quantity}</TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(record.total_amount)}
                      </TableCell>
                      <TableCell>{formatDate(record.payment_completed_at)}</TableCell>
                      <TableCell>
                        <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Ready
                        </Badge>
                      </TableCell>
                      {isPEDesk && (
                        <TableCell className="text-center">
                          <Button
                            size="sm"
                            onClick={() => setTransferDialog({ open: true, record })}
                            className="bg-emerald-600 hover:bg-emerald-700"
                            data-testid={`transfer-btn-${record.booking_id}`}
                          >
                            <Send className="h-3 w-3 mr-1" />
                            Transfer
                          </Button>
                        </TableCell>
                      )}
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

export default DPTransferReport;
