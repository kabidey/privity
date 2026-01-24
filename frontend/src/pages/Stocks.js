import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, Pencil, Trash2 } from 'lucide-react';

const Stocks = () => {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingStock, setEditingStock] = useState(null);
  const [formData, setFormData] = useState({
    symbol: '',
    name: '',
    exchange: '',
  });

  useEffect(() => {
    fetchStocks();
  }, []);

  const fetchStocks = async () => {
    try {
      const response = await api.get('/stocks');
      setStocks(response.data);
    } catch (error) {
      toast.error('Failed to load stocks');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingStock) {
        await api.put(`/stocks/${editingStock.id}`, formData);
        toast.success('Stock updated successfully');
      } else {
        await api.post('/stocks', formData);
        toast.success('Stock created successfully');
      }
      setDialogOpen(false);
      resetForm();
      fetchStocks();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const handleEdit = (stock) => {
    setEditingStock(stock);
    setFormData({
      symbol: stock.symbol,
      name: stock.name,
      exchange: stock.exchange || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = async (stockId) => {
    if (!window.confirm('Are you sure you want to delete this stock?')) return;
    try {
      await api.delete(`/stocks/${stockId}`);
      toast.success('Stock deleted successfully');
      fetchStocks();
    } catch (error) {
      toast.error('Failed to delete stock');
    }
  };

  const resetForm = () => {
    setFormData({
      symbol: '',
      name: '',
      exchange: '',
    });
    setEditingStock(null);
  };

  return (
    <div className="p-8 page-enter" data-testid="stocks-page">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Stocks</h1>
          <p className="text-muted-foreground text-base">Manage stock information</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button className="rounded-sm" data-testid="add-stock-button">
              <Plus className="mr-2 h-4 w-4" strokeWidth={1.5} />
              Add Stock
            </Button>
          </DialogTrigger>
          <DialogContent aria-describedby="stock-dialog-description">
            <DialogHeader>
              <DialogTitle>{editingStock ? 'Edit Stock' : 'Add New Stock'}</DialogTitle>
            </DialogHeader>
            <p id="stock-dialog-description" className="sr-only">Form to add or edit stock information</p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="symbol">Stock Symbol *</Label>
                <Input
                  id="symbol"
                  data-testid="stock-symbol-input"
                  placeholder="e.g., RELIANCE"
                  value={formData.symbol}
                  onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Company Name *</Label>
                <Input
                  id="name"
                  data-testid="stock-name-input"
                  placeholder="e.g., Reliance Industries Ltd"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="exchange">Exchange</Label>
                <Input
                  id="exchange"
                  data-testid="stock-exchange-input"
                  placeholder="e.g., NSE, BSE"
                  value={formData.exchange}
                  onChange={(e) => setFormData({ ...formData, exchange: e.target.value.toUpperCase() })}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} data-testid="cancel-button">
                  Cancel
                </Button>
                <Button type="submit" className="rounded-sm" data-testid="save-stock-button">
                  {editingStock ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle>All Stocks</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div>Loading...</div>
          ) : stocks.length === 0 ? (
            <div className="text-center py-12" data-testid="no-stocks-message">
              <p className="text-muted-foreground">No stocks found. Add your first stock to get started.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Symbol</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Company Name</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Exchange</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {stocks.map((stock) => (
                    <TableRow key={stock.id} className="table-row" data-testid="stock-row">
                      <TableCell className="font-bold mono">{stock.symbol}</TableCell>
                      <TableCell>{stock.name}</TableCell>
                      <TableCell className="mono text-sm">{stock.exchange || '-'}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(stock)}
                          data-testid="edit-stock-button"
                        >
                          <Pencil className="h-4 w-4" strokeWidth={1.5} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(stock.id)}
                          data-testid="delete-stock-button"
                        >
                          <Trash2 className="h-4 w-4" strokeWidth={1.5} />
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
    </div>
  );
};

export default Stocks;
