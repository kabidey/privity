import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import api from '../utils/api';
import { useProtectedPage } from '../hooks/useProtectedPage';
import { 
  Send, 
  CheckCircle2, 
  User, 
  Calendar, 
  Package,
  Clock,
  IndianRupee,
  Loader2,
  ArrowUpFromLine,
  Download
} from 'lucide-react';

const DPTransfer = () => {
  const [ready, setReady] = useState([]);
  const [transferred, setTransferred] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('ready');
  const [exporting, setExporting] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState({ open: false, booking: null });
  const [selectedDPType, setSelectedDPType] = useState('');
  const [transferring, setTransferring] = useState(false);

  const { isLoading, isAuthorized, isPELevel, hasPermission } = useProtectedPage({
    allowIf: ({ isPELevel, hasPermission }) => isPELevel || hasPermission('dp.transfer') || hasPermission('dp.view_transfers'),
    deniedMessage: 'Access denied. You need DP Transfer permission to access this page.'
  });

  // Check if user can perform transfers (needs dp.transfer permission)
  const canTransfer = isPELevel || hasPermission('dp.transfer');

  useEffect(() => {
    if (!isAuthorized) return;
    fetchData();
  }, [isAuthorized]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [readyRes, transferredRes] = await Promise.all([
        api.get('/bookings/dp-ready'),
        api.get('/bookings/dp-transferred')
      ]);
      setReady(readyRes.data);
      setTransferred(transferredRes.data);
    } catch (error) {
      toast.error('Failed to load DP transfer data');
    } finally {
      setLoading(false);
    }
  };

  const handleTransfer = async () => {
    if (!confirmDialog.booking || !selectedDPType) {
      toast.error('Please select DP type (NSDL or CDSL)');
      return;
    }

    setTransferring(true);
    try {
      await api.put(`/bookings/${confirmDialog.booking.id}/dp-transfer?dp_type=${selectedDPType}`);
      toast.success(`Stock transferred via ${selectedDPType}. Client notified about T+2 settlement.`);
      setConfirmDialog({ open: false, booking: null });
      setSelectedDPType('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to transfer stock');
    } finally {
      setTransferring(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await api.get(`/bookings/dp-export?status=${activeTab === 'ready' ? 'ready' : activeTab === 'transferred' ? 'transferred' : 'all'}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `dp_transfer_${activeTab}_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Export downloaded successfully');
    } catch (error) {
      toast.error('Failed to export data');
    } finally {
      setExporting(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };

  // Show loading while checking permissions
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="dp-transfer-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">DP Transfer (Client)</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
            Transfer stocks to clients after full payment
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Export Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={exporting || (ready.length === 0 && transferred.length === 0)}
            className="border-blue-500 text-blue-600 hover:bg-blue-50"
            data-testid="export-btn"
          >
            {exporting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            Export Excel
          </Button>
          
          {/* Summary Cards */}
          <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
            <CardContent className="p-3 flex items-center gap-2">
              <Clock className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-xs text-blue-600 dark:text-blue-400">Ready</p>
                <p className="text-lg font-bold text-blue-700 dark:text-blue-300">{ready.length}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800">
            <CardContent className="p-3 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              <div>
                <p className="text-xs text-emerald-600 dark:text-emerald-400">Transferred</p>
                <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300">{transferred.length}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="ready" className="flex items-center gap-2">
            <ArrowUpFromLine className="h-4 w-4" />
            DP Ready ({ready.length})
          </TabsTrigger>
          <TabsTrigger value="transferred" className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            Transferred ({transferred.length})
          </TabsTrigger>
        </TabsList>

        {/* Ready Tab */}
        <TabsContent value="ready">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ArrowUpFromLine className="h-5 w-5 text-blue-600" />
                Ready for Transfer
              </CardTitle>
              <CardDescription>
                Fully paid bookings ready for stock transfer to clients
              </CardDescription>
            </CardHeader>
            <CardContent>
              {ready.length === 0 ? (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No bookings ready for DP transfer</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Booking #</TableHead>
                        <TableHead>Client</TableHead>
                        <TableHead>PAN No</TableHead>
                        <TableHead>DP ID</TableHead>
                        <TableHead>Stock</TableHead>
                        <TableHead className="text-right">Qty</TableHead>
                        <TableHead className="text-right">Sell Rate</TableHead>
                        <TableHead className="text-right">Amount Received</TableHead>
                        <TableHead className="text-center">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {ready.map((booking) => (
                        <TableRow key={booking.id}>
                          <TableCell className="font-mono font-medium text-sm">
                            {booking.booking_number}
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{booking.client_name}</p>
                              <p className="text-xs text-gray-500">{booking.client_email}</p>
                            </div>
                          </TableCell>
                          <TableCell className="font-mono text-sm">
                            {booking.client_pan || '-'}
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-mono text-sm">{booking.client_dp_id || '-'}</p>
                              {booking.client_depository && (
                                <Badge variant="outline" className="text-xs mt-1">
                                  {booking.client_depository}
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{booking.stock_symbol || '-'}</p>
                              <p className="text-xs text-gray-500">{booking.stock_name}</p>
                            </div>
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            {booking.quantity?.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            {formatCurrency(booking.selling_price || 0)}
                          </TableCell>
                          <TableCell className="text-right font-medium text-emerald-600">
                            {formatCurrency(booking.total_paid || booking.total_amount)}
                          </TableCell>
                          <TableCell className="text-center">
                            {canTransfer && (
                              <Button
                                size="sm"
                                onClick={() => setConfirmDialog({ open: true, booking })}
                                className="bg-blue-600 hover:bg-blue-700"
                                data-testid={`transfer-btn-${booking.id}`}
                              >
                                <Send className="h-4 w-4 mr-1" />
                                Transfer
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

        {/* Transferred Tab */}
        <TabsContent value="transferred">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                Transferred Stocks
              </CardTitle>
              <CardDescription>
                Stocks successfully transferred to clients
              </CardDescription>
            </CardHeader>
            <CardContent>
              {transferred.length === 0 ? (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No transferred stocks yet</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Booking #</TableHead>
                        <TableHead>Client</TableHead>
                        <TableHead>PAN No</TableHead>
                        <TableHead>DP ID</TableHead>
                        <TableHead>Stock</TableHead>
                        <TableHead className="text-right">Qty</TableHead>
                        <TableHead className="text-right">Sell Rate</TableHead>
                        <TableHead className="text-right">Amount Received</TableHead>
                        <TableHead className="text-center">DP Type</TableHead>
                        <TableHead>Transferred At</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {transferred.map((booking) => (
                        <TableRow key={booking.id}>
                          <TableCell className="font-mono font-medium text-sm">
                            {booking.booking_number}
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{booking.client_name}</p>
                              <p className="text-xs text-gray-500">{booking.client_email}</p>
                            </div>
                          </TableCell>
                          <TableCell className="font-mono text-sm">
                            {booking.client_pan || '-'}
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-mono text-sm">{booking.client_dp_id || '-'}</p>
                              {booking.client_depository && (
                                <Badge variant="outline" className="text-xs mt-1">
                                  {booking.client_depository}
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{booking.stock_symbol || '-'}</p>
                              <p className="text-xs text-gray-500">{booking.stock_name}</p>
                            </div>
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            {booking.quantity?.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            {formatCurrency(booking.selling_price || 0)}
                          </TableCell>
                          <TableCell className="text-right font-medium text-emerald-600">
                            {formatCurrency(booking.total_paid || booking.total_amount)}
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge 
                              variant="outline" 
                              className={
                                booking.dp_type === 'NSDL' 
                                  ? 'bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-900/30 dark:text-blue-300'
                                  : 'bg-purple-100 text-purple-700 border-purple-300 dark:bg-purple-900/30 dark:text-purple-300'
                              }
                            >
                              {booking.dp_type}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm">
                            {formatDate(booking.dp_transferred_at)}
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

      {/* Confirm Transfer Dialog */}
      <Dialog open={confirmDialog.open} onOpenChange={(open) => !open && setConfirmDialog({ open: false, booking: null })}>
        <DialogContent className="sm:max-w-md" data-testid="dp-transfer-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Send className="h-5 w-5 text-blue-600" />
              Transfer Stock to Client
            </DialogTitle>
            <DialogDescription>
              Transfer shares to the client&apos;s demat account
            </DialogDescription>
          </DialogHeader>

          {confirmDialog.booking && (
            <div className="space-y-4">
              {/* Booking Details */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-500">Booking #</span>
                  <span className="font-mono font-medium">{confirmDialog.booking.booking_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Client</span>
                  <span className="font-medium">{confirmDialog.booking.client_name}</span>
                </div>
                {confirmDialog.booking.client_otc_ucc && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Demat Account</span>
                    <span className="font-mono text-blue-600">{confirmDialog.booking.client_otc_ucc}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-500">Stock</span>
                  <span className="font-medium">{confirmDialog.booking.stock_symbol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Quantity</span>
                  <span className="font-bold text-lg">{confirmDialog.booking.quantity?.toLocaleString()} shares</span>
                </div>
              </div>

              {/* DP Type Selection */}
              <div className="space-y-2">
                <Label>Select DP Type <span className="text-red-500">*</span></Label>
                <Select value={selectedDPType} onValueChange={setSelectedDPType}>
                  <SelectTrigger data-testid="dp-type-select">
                    <SelectValue placeholder="Choose NSDL or CDSL" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NSDL">
                      <div className="flex items-center gap-2">
                        <Badge className="bg-blue-100 text-blue-700">NSDL</Badge>
                        <span>National Securities Depository</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="CDSL">
                      <div className="flex items-center gap-2">
                        <Badge className="bg-purple-100 text-purple-700">CDSL</Badge>
                        <span>Central Depository Services</span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  <strong>Note:</strong> The client will receive an email notification that their stock has been transferred and will appear in their demat account within T+2 business days.
                </p>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setConfirmDialog({ open: false, booking: null });
                setSelectedDPType('');
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleTransfer}
              disabled={!selectedDPType || transferring}
              className="bg-blue-600 hover:bg-blue-700"
              data-testid="confirm-transfer-btn"
            >
              {transferring ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Transferring...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Transfer Stock
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DPTransfer;
