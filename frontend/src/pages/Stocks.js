import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, Pencil, Trash2, Package, Split, Gift, Play, AlertCircle, Lock, Bell, DollarSign, Send } from 'lucide-react';

const SECTORS = [
  'Banking', 'IT', 'Pharma', 'FMCG', 'Auto', 'Realty', 'Energy', 'Metals', 
  'Telecom', 'Infrastructure', 'Media', 'Chemicals', 'Textiles', 'Others'
];

const PRODUCTS = ['Equity', 'Preference', 'Debenture', 'Warrant', 'Others'];

const ACTION_TYPES = [
  { value: 'dividend', label: 'Dividend', icon: DollarSign },
  { value: 'stock_split', label: 'Stock Split', icon: Split },
  { value: 'bonus', label: 'Bonus Issue', icon: Gift },
  { value: 'rights_issue', label: 'Rights Issue', icon: Plus },
  { value: 'buyback', label: 'Buyback', icon: Package },
];

const DIVIDEND_TYPES = [
  { value: 'interim', label: 'Interim Dividend' },
  { value: 'final', label: 'Final Dividend' },
  { value: 'special', label: 'Special Dividend' },
];

const Stocks = () => {
  const [stocks, setStocks] = useState([]);
  const [corporateActions, setCorporateActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [actionDialogOpen, setActionDialogOpen] = useState(false);
  const [editingStock, setEditingStock] = useState(null);
  const [activeTab, setActiveTab] = useState('stocks');
  const [sendingNotification, setSendingNotification] = useState(null);
  
  const [formData, setFormData] = useState({
    symbol: '',
    name: '',
    exchange: 'UNLISTED/CCPS',
    isin_number: '',
    sector: '',
    product: 'Equity',
    face_value: '',
  });
  
  const [actionFormData, setActionFormData] = useState({
    stock_id: '',
    action_type: 'dividend',
    ratio_from: '1',
    ratio_to: '2',
    dividend_amount: '',
    dividend_type: 'interim',
    new_face_value: '',
    record_date: '',
    ex_date: '',
    payment_date: '',
    notes: '',
  });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPEDesk = currentUser.role === 1;

  useEffect(() => {
    fetchStocks();
    if (isPEDesk) {
      fetchCorporateActions();
    }
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

  const fetchCorporateActions = async () => {
    try {
      const response = await api.get('/corporate-actions');
      setCorporateActions(response.data);
    } catch (error) {
      console.error('Failed to load corporate actions');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        face_value: formData.face_value ? parseFloat(formData.face_value) : null,
      };

      if (editingStock) {
        await api.put(`/stocks/${editingStock.id}`, payload);
        toast.success('Stock updated successfully');
      } else {
        await api.post('/stocks', payload);
        toast.success('Stock created successfully');
      }
      setDialogOpen(false);
      resetForm();
      fetchStocks();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const handleCorporateActionSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        stock_id: actionFormData.stock_id,
        action_type: actionFormData.action_type,
        record_date: actionFormData.record_date,
        notes: actionFormData.notes || null,
      };

      // Add fields based on action type
      if (actionFormData.action_type === 'dividend') {
        payload.dividend_amount = parseFloat(actionFormData.dividend_amount);
        payload.dividend_type = actionFormData.dividend_type;
        payload.ex_date = actionFormData.ex_date || null;
        payload.payment_date = actionFormData.payment_date || null;
      } else {
        payload.ratio_from = parseInt(actionFormData.ratio_from);
        payload.ratio_to = parseInt(actionFormData.ratio_to);
        payload.new_face_value = actionFormData.new_face_value ? parseFloat(actionFormData.new_face_value) : null;
      }

      await api.post('/corporate-actions', payload);
      toast.success('Corporate action created successfully');
      setActionDialogOpen(false);
      resetActionForm();
      fetchCorporateActions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const handleSendNotification = async (actionId) => {
    if (!window.confirm('Send email notifications to all clients holding this stock?')) return;
    setSendingNotification(actionId);
    try {
      await api.post(`/corporate-actions/${actionId}/notify`);
      toast.success('Notifications are being sent to clients');
      fetchCorporateActions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send notifications');
    } finally {
      setSendingNotification(null);
    }
  };

  const handleApplyAction = async (actionId) => {
    if (!window.confirm('Apply this corporate action? This will adjust all buy prices. This action cannot be undone.')) return;
    try {
      const response = await api.put(`/corporate-actions/${actionId}/apply`);
      toast.success(response.data.message);
      fetchCorporateActions();
      fetchStocks();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to apply action');
    }
  };

  const handleDeleteAction = async (actionId) => {
    if (!window.confirm('Delete this corporate action?')) return;
    try {
      await api.delete(`/corporate-actions/${actionId}`);
      toast.success('Corporate action deleted');
      fetchCorporateActions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete action');
    }
  };

  const handleEdit = (stock) => {
    setEditingStock(stock);
    setFormData({
      symbol: stock.symbol,
      name: stock.name,
      exchange: stock.exchange || 'UNLISTED/CCPS',
      isin_number: stock.isin_number || '',
      sector: stock.sector || '',
      product: stock.product || 'Equity',
      face_value: stock.face_value?.toString() || '',
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
      toast.error(error.response?.data?.detail || 'Failed to delete stock');
    }
  };

  const resetForm = () => {
    setFormData({
      symbol: '', name: '', exchange: 'UNLISTED/CCPS', isin_number: '', sector: '', product: 'Equity', face_value: '',
    });
    setEditingStock(null);
  };

  const resetActionForm = () => {
    setActionFormData({
      stock_id: '', action_type: 'stock_split', ratio_from: '1', ratio_to: '2', new_face_value: '', record_date: '', notes: '',
    });
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="stocks-page">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 md:mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold mb-2">Stocks</h1>
          <p className="text-muted-foreground text-sm md:text-base">
            {isPEDesk ? 'Manage stocks and corporate actions' : 'View available stocks'}
          </p>
        </div>
        {isPEDesk && (
          <div className="flex flex-wrap gap-2 w-full sm:w-auto">
            <Dialog open={actionDialogOpen} onOpenChange={(open) => { setActionDialogOpen(open); if (!open) resetActionForm(); }}>
              <DialogTrigger asChild>
                <Button variant="outline" className="rounded-sm flex-1 sm:flex-none" data-testid="add-corporate-action-button">
                  <Split className="mr-2 h-4 w-4" strokeWidth={1.5} />
                  <span className="hidden sm:inline">Corporate </span>Action
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" aria-describedby="action-dialog-desc">
                <DialogHeader>
                  <DialogTitle>Create Corporate Action</DialogTitle>
                </DialogHeader>
                <p id="action-dialog-desc" className="sr-only">Create stock split or bonus</p>
                
                <form onSubmit={handleCorporateActionSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label>Stock *</Label>
                    <Select value={actionFormData.stock_id} onValueChange={(v) => setActionFormData({ ...actionFormData, stock_id: v })} required>
                      <SelectTrigger><SelectValue placeholder="Select stock" /></SelectTrigger>
                      <SelectContent>
                        {stocks.map((stock) => (
                          <SelectItem key={stock.id} value={stock.id}>{stock.symbol} - {stock.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Action Type *</Label>
                    <Select value={actionFormData.action_type} onValueChange={(v) => setActionFormData({ ...actionFormData, action_type: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="stock_split"><Split className="inline h-4 w-4 mr-2" />Stock Split</SelectItem>
                        <SelectItem value="bonus"><Gift className="inline h-4 w-4 mr-2" />Bonus Shares</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>{actionFormData.action_type === 'stock_split' ? 'Old Ratio' : 'Existing Shares'} *</Label>
                      <Input
                        type="number"
                        min="1"
                        value={actionFormData.ratio_from}
                        onChange={(e) => setActionFormData({ ...actionFormData, ratio_from: e.target.value })}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{actionFormData.action_type === 'stock_split' ? 'New Ratio' : 'Bonus Shares'} *</Label>
                      <Input
                        type="number"
                        min="1"
                        value={actionFormData.ratio_to}
                        onChange={(e) => setActionFormData({ ...actionFormData, ratio_to: e.target.value })}
                        required
                      />
                    </div>
                  </div>
                  
                  <p className="text-sm text-muted-foreground">
                    {actionFormData.action_type === 'stock_split' 
                      ? `Split ratio: ${actionFormData.ratio_from}:${actionFormData.ratio_to} (1 share becomes ${actionFormData.ratio_to} shares)`
                      : `Bonus ratio: ${actionFormData.ratio_from}:${actionFormData.ratio_to} (For every ${actionFormData.ratio_from} shares, get ${actionFormData.ratio_to} bonus)`
                    }
                  </p>
                  
                  {actionFormData.action_type === 'stock_split' && (
                    <div className="space-y-2">
                      <Label>New Face Value (₹) *</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={actionFormData.new_face_value}
                        onChange={(e) => setActionFormData({ ...actionFormData, new_face_value: e.target.value })}
                        required={actionFormData.action_type === 'stock_split'}
                        placeholder="e.g., 1 or 2"
                      />
                    </div>
                  )}
                  
                  <div className="space-y-2">
                    <Label>Record Date *</Label>
                    <Input
                      type="date"
                      value={actionFormData.record_date}
                      onChange={(e) => setActionFormData({ ...actionFormData, record_date: e.target.value })}
                      required
                    />
                    <p className="text-xs text-muted-foreground">Action can only be applied on this date</p>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Notes</Label>
                    <Textarea
                      value={actionFormData.notes}
                      onChange={(e) => setActionFormData({ ...actionFormData, notes: e.target.value })}
                      rows={2}
                    />
                  </div>
                  
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => setActionDialogOpen(false)}>Cancel</Button>
                    <Button type="submit">Create Action</Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
            
            <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
              <DialogTrigger asChild>
                <Button className="rounded-sm" data-testid="add-stock-button">
                  <Plus className="mr-2 h-4 w-4" strokeWidth={1.5} />
                  Add Stock
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg" aria-describedby="stock-dialog-desc">
                <DialogHeader>
                  <DialogTitle>{editingStock ? 'Edit Stock' : 'Add New Stock'}</DialogTitle>
                </DialogHeader>
                <p id="stock-dialog-desc" className="sr-only">Form to add or edit stock</p>
                
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Symbol (Short Code) *</Label>
                      <Input
                        data-testid="stock-symbol-input"
                        value={formData.symbol}
                        onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                        placeholder="e.g., RELIANCE"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>ISIN Number</Label>
                      <Input
                        data-testid="stock-isin-input"
                        value={formData.isin_number}
                        onChange={(e) => setFormData({ ...formData, isin_number: e.target.value.toUpperCase() })}
                        placeholder="e.g., INE002A01018"
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Company Name *</Label>
                    <Input
                      data-testid="stock-name-input"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="e.g., Reliance Industries Ltd"
                      required
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Exchange / Status</Label>
                      <Select value={formData.exchange} onValueChange={(v) => setFormData({ ...formData, exchange: v })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="UNLISTED/CCPS">UNLISTED/CCPS</SelectItem>
                          <SelectItem value="DRHP Filed">DRHP Filed</SelectItem>
                          <SelectItem value="Blocked IPO/RTA">Blocked IPO/RTA</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Sector</Label>
                      <Select value={formData.sector} onValueChange={(v) => setFormData({ ...formData, sector: v })}>
                        <SelectTrigger><SelectValue placeholder="Select sector" /></SelectTrigger>
                        <SelectContent>
                          {SECTORS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Product</Label>
                      <Select value={formData.product} onValueChange={(v) => setFormData({ ...formData, product: v })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {PRODUCTS.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Face Value (₹)</Label>
                      <Input
                        type="number"
                        step="0.01"
                        data-testid="stock-facevalue-input"
                        value={formData.face_value}
                        onChange={(e) => setFormData({ ...formData, face_value: e.target.value })}
                        placeholder="e.g., 10"
                      />
                    </div>
                  </div>
                  
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button type="submit" data-testid="save-stock-button">{editingStock ? 'Update' : 'Create'}</Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </div>

      {!isPEDesk && (
        <div className="flex items-center gap-2 p-3 bg-muted rounded-lg mb-6">
          <Lock className="h-5 w-5 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Stock management is restricted to PE Desk only.</p>
        </div>
      )}

      {isPEDesk && (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-6">
          <TabsList>
            <TabsTrigger value="stocks"><Package className="h-4 w-4 mr-2" />Stocks ({stocks.length})</TabsTrigger>
            <TabsTrigger value="actions"><Split className="h-4 w-4 mr-2" />Corporate Actions ({corporateActions.length})</TabsTrigger>
          </TabsList>
        </Tabs>
      )}

      {activeTab === 'stocks' && (
        <Card className="border shadow-sm">
          <CardHeader>
            <CardTitle>All Stocks</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? <div>Loading...</div> : stocks.length === 0 ? (
              <div className="text-center py-12"><p className="text-muted-foreground">No stocks found.</p></div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs uppercase">Symbol</TableHead>
                      <TableHead className="text-xs uppercase">Name</TableHead>
                      <TableHead className="text-xs uppercase">ISIN</TableHead>
                      <TableHead className="text-xs uppercase">Sector</TableHead>
                      <TableHead className="text-xs uppercase">Product</TableHead>
                      <TableHead className="text-xs uppercase">Face Value</TableHead>
                      <TableHead className="text-xs uppercase">Exchange</TableHead>
                      {isPEDesk && <TableHead className="text-xs uppercase text-right">Actions</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {stocks.map((stock) => (
                      <TableRow key={stock.id} data-testid="stock-row">
                        <TableCell className="font-bold mono text-primary">{stock.symbol}</TableCell>
                        <TableCell className="font-medium">{stock.name}</TableCell>
                        <TableCell className="mono text-sm">{stock.isin_number || '-'}</TableCell>
                        <TableCell>{stock.sector ? <Badge variant="outline">{stock.sector}</Badge> : '-'}</TableCell>
                        <TableCell>{stock.product || 'Equity'}</TableCell>
                        <TableCell className="mono">{stock.face_value ? `₹${stock.face_value}` : '-'}</TableCell>
                        <TableCell>
                          <Badge 
                            variant="secondary" 
                            className={
                              stock.exchange === 'Blocked IPO/RTA' 
                                ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' 
                                : stock.exchange === 'DRHP Filed'
                                ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                                : ''
                            }
                          >
                            {stock.exchange || 'UNLISTED/CCPS'}
                          </Badge>
                        </TableCell>
                        {isPEDesk && (
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" onClick={() => handleEdit(stock)}><Pencil className="h-4 w-4" /></Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(stock.id)}><Trash2 className="h-4 w-4" /></Button>
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
      )}

      {isPEDesk && activeTab === 'actions' && (
        <Card className="border shadow-sm">
          <CardHeader>
            <CardTitle>Corporate Actions</CardTitle>
            <CardDescription>Stock splits and bonus shares - apply on record date</CardDescription>
          </CardHeader>
          <CardContent>
            {corporateActions.length === 0 ? (
              <div className="text-center py-12"><p className="text-muted-foreground">No corporate actions found.</p></div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs uppercase">Stock</TableHead>
                      <TableHead className="text-xs uppercase">Type</TableHead>
                      <TableHead className="text-xs uppercase">Ratio</TableHead>
                      <TableHead className="text-xs uppercase">New FV</TableHead>
                      <TableHead className="text-xs uppercase">Record Date</TableHead>
                      <TableHead className="text-xs uppercase">Status</TableHead>
                      <TableHead className="text-xs uppercase text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {corporateActions.map((action) => (
                      <TableRow key={action.id}>
                        <TableCell className="font-bold mono">{action.stock_symbol}</TableCell>
                        <TableCell>
                          <Badge variant={action.action_type === 'stock_split' ? 'default' : 'secondary'}>
                            {action.action_type === 'stock_split' ? <><Split className="h-3 w-3 mr-1" />Split</> : <><Gift className="h-3 w-3 mr-1" />Bonus</>}
                          </Badge>
                        </TableCell>
                        <TableCell className="mono font-semibold">{action.ratio_from}:{action.ratio_to}</TableCell>
                        <TableCell className="mono">{action.new_face_value ? `₹${action.new_face_value}` : '-'}</TableCell>
                        <TableCell className="font-medium">{action.record_date}</TableCell>
                        <TableCell>
                          <Badge variant={action.status === 'applied' ? 'outline' : 'default'} className={action.status === 'applied' ? 'text-green-600' : 'text-orange-600'}>
                            {action.status === 'applied' ? 'Applied' : 'Pending'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {action.status === 'pending' && (
                            <>
                              <Button variant="ghost" size="sm" onClick={() => handleApplyAction(action.id)} title="Apply on record date" className="text-green-600">
                                <Play className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => handleDeleteAction(action.id)} className="text-red-600">
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </>
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
      )}
    </div>
  );
};

export default Stocks;
