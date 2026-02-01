import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import { Package, TrendingUp, AlertTriangle, Trash2 } from 'lucide-react';

const Inventory = () => {
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalStocks: 0,
    totalValue: 0,
    totalQuantity: 0,
    lowStockCount: 0,
  });
  
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPEDesk = currentUser.role === 1;

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

  const getStockLevel = (quantity) => {
    if (quantity === 0) return { label: 'Out of Stock', color: 'text-red-600', progress: 0 };
    if (quantity < 50) return { label: 'Critical', color: 'text-red-600', progress: 10 };
    if (quantity < 100) return { label: 'Low', color: 'text-orange-600', progress: 25 };
    if (quantity < 500) return { label: 'Normal', color: 'text-green-600', progress: 60 };
    return { label: 'High', color: 'text-blue-600', progress: 100 };
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="inventory-page">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Inventory</h1>
        <p className="text-muted-foreground text-base">Track stock levels and weighted average pricing</p>
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
              ₹{stats.totalValue.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
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

      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle>Stock Inventory</CardTitle>
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
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Stock Symbol</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Stock Name</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Available Qty</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Blocked Qty</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Weighted Avg Price</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Total Value</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Stock Level</TableHead>
                    {isPEDesk && <TableHead className="text-xs uppercase tracking-wider font-semibold text-right">Actions</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {inventory.map((item) => {
                    const level = getStockLevel(item.available_quantity);
                    return (
                      <TableRow key={item.stock_id} className="table-row" data-testid="inventory-row">
                        <TableCell className="font-bold mono text-lg">{item.stock_symbol}</TableCell>
                        <TableCell className="font-medium">{item.stock_name}</TableCell>
                        <TableCell className="mono text-lg">{item.available_quantity.toLocaleString('en-IN')}</TableCell>
                        <TableCell className="mono text-orange-600">{(item.blocked_quantity || 0).toLocaleString('en-IN')}</TableCell>
                        <TableCell className="mono">₹{(item.weighted_avg_price || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</TableCell>
                        <TableCell className="mono font-semibold">₹{(item.total_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-3 min-w-[150px]">
                            <Progress value={level.progress} className="h-2 flex-1" />
                            <span className={`text-xs font-medium ${level.color} min-w-[70px]`}>{level.label}</span>
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
    </div>
  );
};

export default Inventory;
