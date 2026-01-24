import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, ShoppingCart, TrendingUp } from 'lucide-react';

const Purchases = () => {
  const [purchases, setPurchases] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    vendor_id: '',
    stock_id: '',
    quantity: '',
    price_per_unit: '',
    purchase_date: new Date().toISOString().split('T')[0],
    notes: '',
  });
  const [stats, setStats] = useState({
    totalPurchases: 0,
    totalValue: 0,
    totalQuantity: 0,
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [purchasesRes, vendorsRes, stocksRes] = await Promise.all([
        api.get('/purchases'),
        api.get('/clients?is_vendor=true'),
        api.get('/stocks'),
      ]);
      setPurchases(purchasesRes.data);
      setVendors(vendorsRes.data);
      setStocks(stocksRes.data);

      // Calculate stats
      const totalValue = purchasesRes.data.reduce((acc, p) => acc + p.total_amount, 0);
      const totalQuantity = purchasesRes.data.reduce((acc, p) => acc + p.quantity, 0);
      setStats({
        totalPurchases: purchasesRes.data.length,
        totalValue,
        totalQuantity,
      });
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        quantity: parseInt(formData.quantity),
        price_per_unit: parseFloat(formData.price_per_unit),
      };

      await api.post('/purchases', payload);
      toast.success('Purchase recorded successfully');
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const resetForm = () => {
    setFormData({
      vendor_id: '',
      stock_id: '',
      quantity: '',
      price_per_unit: '',
      purchase_date: new Date().toISOString().split('T')[0],
      notes: '',
    });
  };

  return (
    <div className="p-8 page-enter" data-testid="purchases-page">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Purchases</h1>
          <p className="text-muted-foreground text-base">Record stock purchases from vendors</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button className="rounded-sm" data-testid="add-purchase-button">
              <Plus className="mr-2 h-4 w-4" strokeWidth={1.5} />
              Record Purchase
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg" aria-describedby="purchase-dialog-description">
            <DialogHeader>
              <DialogTitle>Record New Purchase</DialogTitle>
            </DialogHeader>
            <p id="purchase-dialog-description" className="sr-only">Form to record a stock purchase from vendor</p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="vendor_id">Vendor *</Label>
                <Select
                  value={formData.vendor_id}
                  onValueChange={(value) => setFormData({ ...formData, vendor_id: value })}
                  required
                >
                  <SelectTrigger data-testid="purchase-vendor-select">
                    <SelectValue placeholder="Select vendor" />
                  </SelectTrigger>
                  <SelectContent>
                    {vendors.map((vendor) => (
                      <SelectItem key={vendor.id} value={vendor.id}>
                        {vendor.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="stock_id">Stock *</Label>
                <Select
                  value={formData.stock_id}
                  onValueChange={(value) => setFormData({ ...formData, stock_id: value })}
                  required
                >
                  <SelectTrigger data-testid="purchase-stock-select">
                    <SelectValue placeholder="Select stock" />
                  </SelectTrigger>
                  <SelectContent>
                    {stocks.map((stock) => (
                      <SelectItem key={stock.id} value={stock.id}>
                        {stock.symbol} - {stock.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="quantity">Quantity *</Label>
                  <Input
                    id="quantity"
                    data-testid="purchase-quantity-input"
                    type="number"
                    min="1"
                    value={formData.quantity}
                    onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="price_per_unit">Price Per Unit *</Label>
                  <Input
                    id="price_per_unit"
                    data-testid="purchase-price-input"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.price_per_unit}
                    onChange={(e) => setFormData({ ...formData, price_per_unit: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="purchase_date">Purchase Date *</Label>
                <Input
                  id="purchase_date"
                  data-testid="purchase-date-input"
                  type="date"
                  value={formData.purchase_date}
                  onChange={(e) => setFormData({ ...formData, purchase_date: e.target.value })}
                  required
                />
              </div>
              {formData.quantity && formData.price_per_unit && (
                <div className="p-4 bg-secondary/30 rounded-md">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Total Amount:</span>
                    <span className="text-xl font-bold mono">
                      ₹{(parseFloat(formData.quantity) * parseFloat(formData.price_per_unit)).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea
                  id="notes"
                  data-testid="purchase-notes-input"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={2}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} data-testid="cancel-button">
                  Cancel
                </Button>
                <Button type="submit" className="rounded-sm" data-testid="save-purchase-button">
                  Record Purchase
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card className="border shadow-sm" data-testid="total-purchases-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <ShoppingCart className="h-4 w-4" />
              Total Purchases
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono">{stats.totalPurchases}</div>
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

        <Card className="border shadow-sm" data-testid="total-quantity-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Total Quantity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono">{stats.totalQuantity.toLocaleString('en-IN')}</div>
          </CardContent>
        </Card>
      </div>

      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle>Purchase History</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div>Loading...</div>
          ) : purchases.length === 0 ? (
            <div className="text-center py-12" data-testid="no-purchases-message">
              <p className="text-muted-foreground">No purchases recorded yet. Record your first purchase to build inventory.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Vendor</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Stock</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Quantity</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Price/Unit</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Total Amount</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {purchases.map((purchase) => (
                    <TableRow key={purchase.id} className="table-row" data-testid="purchase-row">
                      <TableCell className="font-medium">{purchase.vendor_name}</TableCell>
                      <TableCell className="mono text-sm font-semibold">{purchase.stock_symbol}</TableCell>
                      <TableCell className="mono">{purchase.quantity.toLocaleString('en-IN')}</TableCell>
                      <TableCell className="mono">₹{purchase.price_per_unit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</TableCell>
                      <TableCell className="mono font-semibold">₹{purchase.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</TableCell>
                      <TableCell className="text-sm">{new Date(purchase.purchase_date).toLocaleDateString('en-IN')}</TableCell>
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

export default Purchases;
