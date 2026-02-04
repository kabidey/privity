import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { Package, TrendingUp, TrendingDown, AlertTriangle, Trash2, Edit2, Check, X, DollarSign, RefreshCw, ArrowUpDown, LineChart, ArrowUp, ArrowDown, Minus } from 'lucide-react';

const Inventory = () => {
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [editingLP, setEditingLP] = useState(null); // stock_id being edited
  const [newLP, setNewLP] = useState('');
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [stockToEdit, setStockToEdit] = useState(null);
  
  // Sorting state
  const [sortBy, setSortBy] = useState('stock_symbol'); // default sort by stock name
  const [sortOrder, setSortOrder] = useState('asc');
  
  // LP History state
  const [lpHistoryDialogOpen, setLpHistoryDialogOpen] = useState(false);
  const [selectedStockForHistory, setSelectedStockForHistory] = useState(null);
  const [lpHistory, setLpHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  const [stats, setStats] = useState({
    totalStocks: 0,
    totalValue: 0,
    totalQuantity: 0,
    lowStockCount: 0,
  });
  
  const { isPEDesk, isPEManager, isPELevel } = useCurrentUser();

  useEffect(() => {
    fetchInventory();
  }, []);

  const fetchInventory = async () => {
    try {
      const response = await api.get('/inventory');
      const data = response.data;
      setInventory(data);

      // Calculate stats
      const totalValue = data.reduce((acc, item) => acc + (item.total_value || 0), 0);
      const totalQuantity = data.reduce((acc, item) => acc + (item.available_quantity || 0), 0);
      const lowStockCount = data.filter(item => item.available_quantity < 100).length;

      setStats({
        totalStocks: data.length,
        totalValue,
        totalQuantity,
        lowStockCount,
      });
    } catch (error) {
      toast.error('Failed to load inventory');
    } finally {
      setLoading(false);
    }
  };

  // Fetch LP history for a stock
  const fetchLPHistory = async (stockId, stockSymbol) => {
    setLoadingHistory(true);
    setSelectedStockForHistory({ stock_id: stockId, stock_symbol: stockSymbol });
    setLpHistoryDialogOpen(true);
    
    try {
      const response = await api.get(`/inventory/${stockId}/lp-history`);
      setLpHistory(response.data.history || []);
    } catch (error) {
      toast.error('Failed to load LP history');
      setLpHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Sorting function
  const sortedInventory = [...inventory].sort((a, b) => {
    let aVal, bVal;
    
    switch (sortBy) {
      case 'stock_symbol':
        aVal = a.stock_symbol || '';
        bVal = b.stock_symbol || '';
        break;
      case 'available_quantity':
        aVal = a.available_quantity || 0;
        bVal = b.available_quantity || 0;
        break;
      case 'landing_price':
        aVal = a.landing_price || 0;
        bVal = b.landing_price || 0;
        break;
      case 'lp_change':
        aVal = (a.landing_price || 0) - (a.previous_landing_price || a.landing_price || 0);
        bVal = (b.landing_price || 0) - (b.previous_landing_price || b.landing_price || 0);
        break;
      case 'total_value':
        aVal = a.total_value || 0;
        bVal = b.total_value || 0;
        break;
      case 'has_inventory':
        aVal = a.available_quantity > 0 ? 1 : 0;
        bVal = b.available_quantity > 0 ? 1 : 0;
        break;
      default:
        aVal = a.stock_symbol || '';
        bVal = b.stock_symbol || '';
    }
    
    if (typeof aVal === 'string') {
      return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
  });

  // Get LP change indicator
  const getLPChangeIndicator = (item) => {
    const currentLP = item.landing_price || 0;
    const previousLP = item.previous_landing_price;
    
    if (previousLP === undefined || previousLP === null || previousLP === currentLP) {
      return { type: 'neutral', color: 'bg-gray-100 text-gray-600', icon: Minus };
    }
    
    if (currentLP > previousLP) {
      return { type: 'up', color: 'bg-green-100 text-green-700 border-green-300', icon: ArrowUp };
    }
    
    return { type: 'down', color: 'bg-red-100 text-red-700 border-red-300', icon: ArrowDown };
  };

  const handleDeleteInventory = async (stockId, stockSymbol) => {
    if (!window.confirm(`Are you sure you want to delete inventory for ${stockSymbol}? This will remove all inventory records for this stock.`)) {
      return;
    }
    
    try {
      await api.delete(`/inventory/${stockId}`);
      toast.success(`Inventory for ${stockSymbol} deleted successfully`);
      fetchInventory();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete inventory');
    }
  };

  const handleRecalculateInventory = async () => {
    if (!window.confirm('Are you sure you want to recalculate inventory for ALL stocks? This will update available quantities, blocked quantities, and weighted average prices based on actual purchases and bookings.')) {
      return;
    }
    
    setRecalculating(true);
    try {
      const response = await api.post('/inventory/recalculate');
      toast.success(response.data.message || 'Inventory recalculated successfully');
      fetchInventory();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to recalculate inventory');
    } finally {
      setRecalculating(false);
    }
  };

  const startEditLP = (item) => {
    setEditingLP(item.stock_id);
    setNewLP(item.landing_price?.toString() || item.weighted_avg_price?.toString() || '');
  };

  const cancelEditLP = () => {
    setEditingLP(null);
    setNewLP('');
  };

  const openConfirmDialog = (item) => {
    setStockToEdit(item);
    setConfirmDialogOpen(true);
  };

  const handleUpdateLP = async () => {
    if (!stockToEdit) return;
    
    const lpValue = parseFloat(newLP);
    if (isNaN(lpValue) || lpValue <= 0) {
      toast.error('Please enter a valid landing price');
      return;
    }

    try {
      await api.put(`/inventory/${stockToEdit.stock_id}/landing-price`, {
        landing_price: lpValue
      });
      toast.success(`Landing price updated for ${stockToEdit.stock_symbol}`);
      setEditingLP(null);
      setNewLP('');
      setConfirmDialogOpen(false);
      setStockToEdit(null);
      fetchInventory();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update landing price');
    }
  };

  const getStockLevel = (quantity) => {
    if (quantity === 0) return { label: 'Out of Stock', color: 'text-red-600', progress: 0 };
    if (quantity < 50) return { label: 'Critical', color: 'text-red-600', progress: 10 };
    if (quantity < 100) return { label: 'Low', color: 'text-orange-600', progress: 25 };
    if (quantity < 500) return { label: 'Normal', color: 'text-green-600', progress: 60 };
    return { label: 'High', color: 'text-blue-600', progress: 100 };
  };

  const formatCurrency = (value) => {
    return `₹${(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="inventory-page">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Inventory</h1>
        <p className="text-muted-foreground text-base">
          {isPELevel 
            ? 'Track stock levels with WAP (Weighted Avg Price) and LP (Landing Price)'
            : 'Track stock levels and pricing'
          }
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card className="border shadow-sm" data-testid="total-stocks-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Package className="h-4 w-4" />
              Total Stocks
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono">{stats.totalStocks}</div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="total-quantity-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Total Units
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono">{stats.totalQuantity.toLocaleString('en-IN')}</div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="total-value-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Total Value
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono text-primary">
              {formatCurrency(stats.totalValue)}
            </div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="low-stock-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              Low Stock Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold mono ${stats.lowStockCount > 0 ? 'text-orange-600' : 'text-green-600'}`}>
              {stats.lowStockCount}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Legend for PE Level */}
      {isPELevel && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm">
          <div className="flex items-center gap-4 flex-wrap">
            <span className="font-semibold text-amber-800">Legend:</span>
            <span><strong>WAP</strong> = Weighted Average Price (actual cost)</span>
            <span><strong>LP</strong> = Landing Price (shown to users, used for booking)</span>
            <span className="text-amber-700"><strong>HIT</strong> = (LP - WAP) × Qty (PE margin)</span>
          </div>
        </div>
      )}

      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Stock Inventory</span>
            <div className="flex items-center gap-3">
              {isPEDesk && (
                <Button
                  onClick={handleRecalculateInventory}
                  disabled={recalculating}
                  variant="outline"
                  size="sm"
                  className="text-blue-600 border-blue-300 hover:bg-blue-50"
                  data-testid="recalculate-inventory-btn"
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${recalculating ? 'animate-spin' : ''}`} />
                  {recalculating ? 'Recalculating...' : 'Recalculate Inventory'}
                </Button>
              )}
              {isPELevel && (
                <span className="text-xs font-normal text-muted-foreground bg-gray-100 px-2 py-1 rounded">
                  PE View: Shows both WAP & LP
                </span>
              )}
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div>Loading...</div>
          ) : inventory.length === 0 ? (
            <div className="text-center py-12" data-testid="no-inventory-message">
              <p className="text-muted-foreground">No inventory data available. Record purchases to build inventory.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Stock</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Available</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Blocked</TableHead>
                    {isPELevel ? (
                      <>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold text-blue-600">WAP</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold text-emerald-600">LP</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold">WAP Value</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold text-emerald-600">LP Value</TableHead>
                      </>
                    ) : (
                      <>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold">Price</TableHead>
                        <TableHead className="text-xs uppercase tracking-wider font-semibold">Total Value</TableHead>
                      </>
                    )}
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Level</TableHead>
                    {isPEDesk && <TableHead className="text-xs uppercase tracking-wider font-semibold text-right">Actions</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {inventory.map((item) => {
                    const level = getStockLevel(item.available_quantity);
                    const isEditing = editingLP === item.stock_id;
                    
                    return (
                      <TableRow key={item.stock_id} className="table-row" data-testid="inventory-row">
                        <TableCell>
                          <div>
                            <span className="font-bold mono text-lg">{item.stock_symbol}</span>
                            <span className="text-xs text-muted-foreground block">{item.stock_name}</span>
                          </div>
                        </TableCell>
                        <TableCell className="mono text-lg">{item.available_quantity.toLocaleString('en-IN')}</TableCell>
                        <TableCell className="mono text-orange-600">{(item.blocked_quantity || 0).toLocaleString('en-IN')}</TableCell>
                        
                        {isPELevel ? (
                          <>
                            {/* WAP - PE Level sees actual weighted average */}
                            <TableCell className="mono text-blue-600">
                              {formatCurrency(item.weighted_avg_price)}
                            </TableCell>
                            
                            {/* LP - Editable for PE Desk */}
                            <TableCell className="mono">
                              {isEditing ? (
                                <div className="flex items-center gap-1">
                                  <Input
                                    type="number"
                                    value={newLP}
                                    onChange={(e) => setNewLP(e.target.value)}
                                    className="w-24 h-8 text-sm"
                                    step="0.01"
                                    autoFocus
                                  />
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => openConfirmDialog(item)}
                                    className="h-8 w-8 p-0 text-green-600"
                                  >
                                    <Check className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={cancelEditLP}
                                    className="h-8 w-8 p-0 text-red-600"
                                  >
                                    <X className="h-4 w-4" />
                                  </Button>
                                </div>
                              ) : (
                                <div className="flex items-center gap-2">
                                  <span className="text-emerald-600 font-semibold">
                                    {formatCurrency(item.landing_price)}
                                  </span>
                                  {isPEDesk && (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => startEditLP(item)}
                                      className="h-6 w-6 p-0 text-gray-400 hover:text-emerald-600"
                                      title="Edit Landing Price"
                                    >
                                      <Edit2 className="h-3 w-3" />
                                    </Button>
                                  )}
                                </div>
                              )}
                            </TableCell>
                            
                            {/* WAP Value */}
                            <TableCell className="mono text-sm">
                              {formatCurrency(item.total_value)}
                            </TableCell>
                            
                            {/* LP Value */}
                            <TableCell className="mono font-semibold text-emerald-600">
                              {formatCurrency(item.lp_total_value || (item.available_quantity * item.landing_price))}
                            </TableCell>
                          </>
                        ) : (
                          <>
                            {/* Non-PE users see LP as "Price" */}
                            <TableCell className="mono">
                              {formatCurrency(item.weighted_avg_price)}
                            </TableCell>
                            <TableCell className="mono font-semibold">
                              {formatCurrency(item.total_value)}
                            </TableCell>
                          </>
                        )}
                        
                        <TableCell>
                          <div className="flex items-center gap-3 min-w-[120px]">
                            <Progress value={level.progress} className="h-2 flex-1" />
                            <span className={`text-xs font-medium ${level.color} min-w-[60px]`}>{level.label}</span>
                          </div>
                        </TableCell>
                        
                        {isPEDesk && (
                          <TableCell className="text-right">
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              onClick={() => handleDeleteInventory(item.stock_id, item.stock_symbol)}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              data-testid={`delete-inventory-${item.stock_id}`}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        )}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Confirm LP Update Dialog */}
      <Dialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-emerald-600" />
              Confirm Landing Price Update
            </DialogTitle>
            <DialogDescription>
              You are about to update the Landing Price for <strong>{stockToEdit?.stock_symbol}</strong>.
            </DialogDescription>
          </DialogHeader>
          
          {stockToEdit && (
            <div className="py-4 space-y-3">
              <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <span className="text-sm text-gray-500">Current WAP</span>
                  <p className="font-mono font-semibold text-blue-600">
                    {formatCurrency(stockToEdit.weighted_avg_price)}
                  </p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Current LP</span>
                  <p className="font-mono font-semibold">
                    {formatCurrency(stockToEdit.landing_price)}
                  </p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">New LP</span>
                  <p className="font-mono font-semibold text-emerald-600">
                    {formatCurrency(parseFloat(newLP) || 0)}
                  </p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">New HIT/Share</span>
                  <p className="font-mono font-semibold text-amber-600">
                    {formatCurrency((parseFloat(newLP) || 0) - (stockToEdit.weighted_avg_price || 0))}
                  </p>
                </div>
              </div>
              
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                <strong>Note:</strong> Landing Price is what non-PE users see and what bookings use for revenue calculation.
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleUpdateLP} className="bg-emerald-600 hover:bg-emerald-700">
              Update Landing Price
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Inventory;
