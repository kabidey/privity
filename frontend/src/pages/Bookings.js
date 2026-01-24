import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, Pencil, Trash2, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

const Bookings = () => {
  const [bookings, setBookings] = useState([]);
  const [pendingBookings, setPendingBookings] = useState([]);
  const [clients, setClients] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBooking, setEditingBooking] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [formData, setFormData] = useState({
    client_id: '',
    stock_id: '',
    quantity: '',
    buying_price: '',
    selling_price: '',
    booking_date: new Date().toISOString().split('T')[0],
    status: 'open',
    notes: '',
  });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPEDesk = currentUser.role === 1;
  const isEmployee = currentUser.role === 4;

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [bookingsRes, clientsRes, stocksRes] = await Promise.all([
        api.get('/bookings'),
        api.get('/clients'),
        api.get('/stocks'),
      ]);
      setBookings(bookingsRes.data);
      setClients(clientsRes.data);
      setStocks(stocksRes.data);
      
      // Fetch pending bookings if PE Desk
      if (isPEDesk) {
        try {
          const pendingRes = await api.get('/bookings/pending-approval');
          setPendingBookings(pendingRes.data);
        } catch (e) {
          console.error('Failed to fetch pending bookings');
        }
      }
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
        buying_price: formData.buying_price ? parseFloat(formData.buying_price) : null,
        selling_price: formData.selling_price ? parseFloat(formData.selling_price) : null,
      };

      if (editingBooking) {
        await api.put(`/bookings/${editingBooking.id}`, payload);
        toast.success('Booking updated successfully');
      } else {
        await api.post('/bookings', payload);
        toast.success('Booking created - pending PE Desk approval');
      }
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const handleApprove = async (bookingId, approve) => {
    try {
      await api.put(`/bookings/${bookingId}/approve?approve=${approve}`);
      toast.success(approve ? 'Booking approved - inventory adjusted' : 'Booking rejected');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process approval');
    }
  };

  const handleEdit = (booking) => {
    // Employees cannot edit buying_price
    setEditingBooking(booking);
    setFormData({
      client_id: booking.client_id,
      stock_id: booking.stock_id,
      quantity: booking.quantity.toString(),
      buying_price: booking.buying_price.toString(),
      selling_price: booking.selling_price?.toString() || '',
      booking_date: booking.booking_date,
      status: booking.status,
      notes: booking.notes || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = async (bookingId) => {
    if (!window.confirm('Are you sure you want to delete this booking?')) return;
    try {
      await api.delete(`/bookings/${bookingId}`);
      toast.success('Booking deleted successfully');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete booking');
    }
  };

  const resetForm = () => {
    setFormData({
      client_id: '',
      stock_id: '',
      quantity: '',
      buying_price: '',
      selling_price: '',
      booking_date: new Date().toISOString().split('T')[0],
      status: 'open',
      notes: '',
    });
    setEditingBooking(null);
  };

  const getApprovalBadge = (status) => {
    switch (status) {
      case 'pending':
        return <Badge variant="outline" className="text-orange-600 border-orange-600"><Clock className="h-3 w-3 mr-1" />Pending</Badge>;
      case 'approved':
        return <Badge variant="outline" className="text-green-600 border-green-600"><CheckCircle className="h-3 w-3 mr-1" />Approved</Badge>;
      case 'rejected':
        return <Badge variant="outline" className="text-red-600 border-red-600"><XCircle className="h-3 w-3 mr-1" />Rejected</Badge>;
      default:
        return null;
    }
  };

  const displayedBookings = activeTab === 'pending' ? pendingBookings : bookings;

  return (
    <div className="p-8 page-enter" data-testid="bookings-page">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Bookings</h1>
          <p className="text-muted-foreground text-base">
            {isEmployee ? 'Create bookings for your clients' : 'Manage share bookings'}
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
          <DialogTrigger asChild>
            <Button className="rounded-sm" data-testid="add-booking-button">
              <Plus className="mr-2 h-4 w-4" strokeWidth={1.5} />
              Create Booking
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg" aria-describedby="booking-dialog-desc">
            <DialogHeader>
              <DialogTitle>{editingBooking ? 'Edit Booking' : 'Create New Booking'}</DialogTitle>
            </DialogHeader>
            <p id="booking-dialog-desc" className="sr-only">Form to create or edit booking</p>
            
            {!editingBooking && (
              <div className="flex items-center gap-2 p-3 bg-orange-50 dark:bg-orange-950 rounded-lg mb-4">
                <AlertCircle className="h-5 w-5 text-orange-600" />
                <p className="text-sm text-orange-800 dark:text-orange-200">
                  Bookings require <strong>PE Desk approval</strong> before inventory is adjusted.
                </p>
              </div>
            )}
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label>Client *</Label>
                <Select value={formData.client_id} onValueChange={(value) => setFormData({ ...formData, client_id: value })} required>
                  <SelectTrigger data-testid="booking-client-select">
                    <SelectValue placeholder="Select client" />
                  </SelectTrigger>
                  <SelectContent>
                    {clients.filter(c => !c.is_vendor && c.is_active).map((client) => (
                      <SelectItem key={client.id} value={client.id}>
                        {client.name} ({client.otc_ucc || 'N/A'})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Stock *</Label>
                <Select value={formData.stock_id} onValueChange={(value) => setFormData({ ...formData, stock_id: value })} required>
                  <SelectTrigger data-testid="booking-stock-select">
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
                  <Label>Quantity *</Label>
                  <Input
                    type="number"
                    min="1"
                    data-testid="booking-quantity-input"
                    value={formData.quantity}
                    onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Buying Price {isEmployee ? '(Auto)' : ''}</Label>
                  <Input
                    type="number"
                    step="0.01"
                    data-testid="booking-buying-price-input"
                    value={formData.buying_price}
                    onChange={(e) => setFormData({ ...formData, buying_price: e.target.value })}
                    disabled={isEmployee}
                    placeholder={isEmployee ? 'Weighted avg' : 'Optional'}
                  />
                  {isEmployee && (
                    <p className="text-xs text-muted-foreground">Uses weighted average from inventory</p>
                  )}
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Selling Price</Label>
                  <Input
                    type="number"
                    step="0.01"
                    data-testid="booking-selling-price-input"
                    value={formData.selling_price}
                    onChange={(e) => setFormData({ ...formData, selling_price: e.target.value })}
                    placeholder="Optional"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Booking Date *</Label>
                  <Input
                    type="date"
                    data-testid="booking-date-input"
                    value={formData.booking_date}
                    onChange={(e) => setFormData({ ...formData, booking_date: e.target.value })}
                    required
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={formData.status} onValueChange={(value) => setFormData({ ...formData, status: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="open">Open</SelectItem>
                    <SelectItem value="closed">Closed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Notes</Label>
                <Textarea
                  data-testid="booking-notes-input"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={2}
                />
              </div>
              
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                <Button type="submit" data-testid="save-booking-button">
                  {editingBooking ? 'Update' : 'Create Booking'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isPEDesk && pendingBookings.length > 0 && (
        <div className="mb-4">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="all">All Bookings ({bookings.length})</TabsTrigger>
              <TabsTrigger value="pending" className="text-orange-600">
                <Clock className="h-4 w-4 mr-1" />
                Pending Approval ({pendingBookings.length})
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      )}

      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle>{activeTab === 'pending' ? 'Pending Approval' : 'All Bookings'}</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? <div>Loading...</div> : displayedBookings.length === 0 ? (
            <div className="text-center py-12"><p className="text-muted-foreground">No bookings found.</p></div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase">Client</TableHead>
                    <TableHead className="text-xs uppercase">Stock</TableHead>
                    <TableHead className="text-xs uppercase">Qty</TableHead>
                    <TableHead className="text-xs uppercase">Buy Price</TableHead>
                    <TableHead className="text-xs uppercase">Sell Price</TableHead>
                    <TableHead className="text-xs uppercase">Date</TableHead>
                    <TableHead className="text-xs uppercase">Status</TableHead>
                    <TableHead className="text-xs uppercase">Approval</TableHead>
                    <TableHead className="text-xs uppercase text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedBookings.map((booking) => (
                    <TableRow key={booking.id} data-testid="booking-row">
                      <TableCell className="font-medium">{booking.client_name}</TableCell>
                      <TableCell className="mono font-semibold">{booking.stock_symbol}</TableCell>
                      <TableCell className="mono">{booking.quantity}</TableCell>
                      <TableCell className="mono">₹{booking.buying_price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</TableCell>
                      <TableCell className="mono">
                        {booking.selling_price ? `₹${booking.selling_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}
                      </TableCell>
                      <TableCell className="text-sm">{new Date(booking.booking_date).toLocaleDateString('en-IN')}</TableCell>
                      <TableCell>
                        <Badge variant={booking.status === 'open' ? 'default' : 'secondary'}>
                          {booking.status.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell>{getApprovalBadge(booking.approval_status)}</TableCell>
                      <TableCell className="text-right">
                        {isPEDesk && booking.approval_status === 'pending' && (
                          <>
                            <Button variant="ghost" size="sm" onClick={() => handleApprove(booking.id, true)} className="text-green-600" title="Approve">
                              <CheckCircle className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleApprove(booking.id, false)} className="text-red-600" title="Reject">
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        {!isEmployee && (
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(booking)}><Pencil className="h-4 w-4" /></Button>
                        )}
                        {!isEmployee && (
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(booking.id)}><Trash2 className="h-4 w-4" /></Button>
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

export default Bookings;
