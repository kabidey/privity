import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { 
  ArrowDownToLine, 
  CheckCircle2, 
  Building2, 
  Calendar, 
  Package,
  Clock,
  User,
  IndianRupee,
  Loader2,
  Download
} from 'lucide-react';

const DPReceivables = () => {
  const navigate = useNavigate();
  const [receivables, setReceivables] = useState([]);
  const [received, setReceived] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('receivable');
  const [exporting, setExporting] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState({ open: false, purchase: null });
  const [selectedDPType, setSelectedDPType] = useState('');
  const [confirming, setConfirming] = useState(false);

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const canAccess = currentUser.role === 1 || currentUser.role === 2;

  useEffect(() => {
    if (!canAccess) {
      toast.error('Access denied. Only PE Desk and PE Manager can access this page.');
      navigate('/');
      return;
    }
    fetchData();
  }, [canAccess, navigate]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [receivablesRes, receivedRes] = await Promise.all([
        api.get('/purchases/dp-receivables'),
        api.get('/purchases/dp-received')
      ]);
      setReceivables(receivablesRes.data);
      setReceived(receivedRes.data);
    } catch (error) {
      toast.error('Failed to load DP data');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkReceived = async () => {
    if (!confirmDialog.purchase || !selectedDPType) {
      toast.error('Please select DP type (NSDL or CDSL)');
      return;
    }

    setConfirming(true);
    try {
      await api.put(`/purchases/${confirmDialog.purchase.id}/mark-dp-received?dp_type=${selectedDPType}`);
      toast.success(`Stock marked as received via ${selectedDPType}. Inventory updated.`);
      setConfirmDialog({ open: false, purchase: null });
      setSelectedDPType('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark as received');
    } finally {
      setConfirming(false);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="dp-receivables-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">DP Receivables</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
            Track stock transfers from vendors after payment completion
          </p>
        </div>
        
        {/* Summary Cards */}
        <div className="flex gap-3">
          <Card className="bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800">
            <CardContent className="p-3 flex items-center gap-2">
              <Clock className="h-5 w-5 text-amber-600" />
              <div>
                <p className="text-xs text-amber-600 dark:text-amber-400">Pending</p>
                <p className="text-lg font-bold text-amber-700 dark:text-amber-300">{receivables.length}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800">
            <CardContent className="p-3 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              <div>
                <p className="text-xs text-emerald-600 dark:text-emerald-400">Received</p>
                <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300">{received.length}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="receivable" className="flex items-center gap-2">
            <ArrowDownToLine className="h-4 w-4" />
            Receivable ({receivables.length})
          </TabsTrigger>
          <TabsTrigger value="received" className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            Received ({received.length})
          </TabsTrigger>
        </TabsList>

        {/* Receivable Tab */}
        <TabsContent value="receivable">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ArrowDownToLine className="h-5 w-5 text-amber-600" />
                Pending Stock Transfers
              </CardTitle>
              <CardDescription>
                Stocks awaiting transfer from vendors after full payment
              </CardDescription>
            </CardHeader>
            <CardContent>
              {receivables.length === 0 ? (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No pending DP receivables</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Purchase #</TableHead>
                        <TableHead>Vendor</TableHead>
                        <TableHead>Stock</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead>Payment Date</TableHead>
                        <TableHead className="text-center">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {receivables.map((purchase) => (
                        <TableRow key={purchase.id}>
                          <TableCell className="font-mono font-medium">
                            {purchase.purchase_number}
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{purchase.vendor_name}</p>
                              <p className="text-xs text-gray-500">{purchase.vendor_email}</p>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{purchase.stock_symbol}</p>
                              <p className="text-xs text-gray-500">{purchase.stock_name}</p>
                            </div>
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            {purchase.quantity?.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            {formatCurrency(purchase.total_amount)}
                          </TableCell>
                          <TableCell className="text-sm">
                            {formatDate(purchase.dp_receivable_at)}
                          </TableCell>
                          <TableCell className="text-center">
                            <Button
                              size="sm"
                              onClick={() => setConfirmDialog({ open: true, purchase })}
                              className="bg-emerald-600 hover:bg-emerald-700"
                              data-testid={`receive-btn-${purchase.id}`}
                            >
                              <CheckCircle2 className="h-4 w-4 mr-1" />
                              Received
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

        {/* Received Tab */}
        <TabsContent value="received">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                Received Stocks
              </CardTitle>
              <CardDescription>
                Stock transfers completed and added to inventory
              </CardDescription>
            </CardHeader>
            <CardContent>
              {received.length === 0 ? (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No received stocks yet</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Purchase #</TableHead>
                        <TableHead>Vendor</TableHead>
                        <TableHead>Stock</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                        <TableHead className="text-center">DP Type</TableHead>
                        <TableHead>Received By</TableHead>
                        <TableHead>Received At</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {received.map((purchase) => (
                        <TableRow key={purchase.id}>
                          <TableCell className="font-mono font-medium">
                            {purchase.purchase_number}
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{purchase.vendor_name}</p>
                              <p className="text-xs text-gray-500">{purchase.vendor_email}</p>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{purchase.stock_symbol}</p>
                              <p className="text-xs text-gray-500">{purchase.stock_name}</p>
                            </div>
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            {purchase.quantity?.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge 
                              variant="outline" 
                              className={
                                purchase.dp_type === 'NSDL' 
                                  ? 'bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-900/30 dark:text-blue-300'
                                  : 'bg-purple-100 text-purple-700 border-purple-300 dark:bg-purple-900/30 dark:text-purple-300'
                              }
                            >
                              {purchase.dp_type}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <User className="h-3 w-3 text-gray-400" />
                              <span className="text-sm">{purchase.dp_received_by_name}</span>
                            </div>
                          </TableCell>
                          <TableCell className="text-sm">
                            {formatDate(purchase.dp_received_at)}
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

      {/* Confirm Received Dialog */}
      <Dialog open={confirmDialog.open} onOpenChange={(open) => !open && setConfirmDialog({ open: false, purchase: null })}>
        <DialogContent className="sm:max-w-md" data-testid="dp-received-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              Confirm Stock Received
            </DialogTitle>
            <DialogDescription>
              Mark this stock transfer as received and update inventory
            </DialogDescription>
          </DialogHeader>

          {confirmDialog.purchase && (
            <div className="space-y-4">
              {/* Purchase Details */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-500">Purchase #</span>
                  <span className="font-mono font-medium">{confirmDialog.purchase.purchase_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Vendor</span>
                  <span className="font-medium">{confirmDialog.purchase.vendor_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Stock</span>
                  <span className="font-medium">{confirmDialog.purchase.stock_symbol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Quantity</span>
                  <span className="font-bold text-lg">{confirmDialog.purchase.quantity?.toLocaleString()} shares</span>
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

              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  <strong>Note:</strong> This will add {confirmDialog.purchase.quantity?.toLocaleString()} shares to the available inventory for {confirmDialog.purchase.stock_symbol}.
                </p>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setConfirmDialog({ open: false, purchase: null });
                setSelectedDPType('');
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleMarkReceived}
              disabled={!selectedDPType || confirming}
              className="bg-emerald-600 hover:bg-emerald-700"
              data-testid="confirm-received-btn"
            >
              {confirming ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Confirm Received
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DPReceivables;
