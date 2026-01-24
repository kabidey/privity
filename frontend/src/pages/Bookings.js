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
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, Pencil, Trash2 } from 'lucide-react';

const Bookings = () => {
  const [bookings, setBookings] = useState([]);
  const [clients, setClients] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBooking, setEditingBooking] = useState(null);
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
        buying_price: parseFloat(formData.buying_price),
        selling_price: formData.selling_price ? parseFloat(formData.selling_price) : null,
      };

      if (editingBooking) {
        await api.put(`/bookings/${editingBooking.id}`, payload);
        toast.success('Booking updated successfully');
      } else {
        await api.post('/bookings', payload);
        toast.success('Booking created successfully');
      }
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const handleEdit = (booking) => {
    setEditingBooking(booking);
    setFormData({
      client_id: booking.client_id,
      stock_id: booking.stock_id,
      quantity: booking.quantity.toString(),
      buying_price: booking.buying_price.toString(),
      selling_price: booking.selling_price ? booking.selling_price.toString() : '',
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

  return (
    <div className="p-8 page-enter" data-testid="bookings-page">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Bookings</h1>
          <p className="text-muted-foreground text-base">Manage share bookings for clients</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button className="rounded-sm" data-testid="add-booking-button">
              <Plus className="mr-2 h-4 w-4" strokeWidth={1.5} />
              Create Booking
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl" aria-describedby="booking-dialog-description">
            <DialogHeader>
              <DialogTitle>{editingBooking ? 'Edit Booking' : 'Create New Booking'}</DialogTitle>
            </DialogHeader>
            <p id="booking-dialog-description" className="sr-only">Form to create or edit share booking with client, stock, quantity and pricing details</p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="client_id">Client *</Label>
                  <Select
                    value={formData.client_id}
                    onValueChange={(value) => setFormData({ ...formData, client_id: value })}
                    required
                  >
                    <SelectTrigger data-testid="booking-client-select">
                      <SelectValue placeholder="Select client" />
                    </SelectTrigger>
                    <SelectContent>
                      {clients.map((client) => (
                        <SelectItem key={client.id} value={client.id}>
                          {client.name}
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
                <div className="space-y-2">
                  <Label htmlFor="quantity">Quantity *</Label>
                  <Input
                    id="quantity"
                    data-testid="booking-quantity-input"
                    type="number"
                    min="1"
                    value={formData.quantity}
                    onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="buying_price">Buying Price *</Label>
                  <Input
                    id="buying_price"
                    data-testid="booking-buying-price-input"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.buying_price}
                    onChange={(e) => setFormData({ ...formData, buying_price: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="selling_price">Selling Price</Label>
                  <Input
                    id="selling_price"
                    data-testid="booking-selling-price-input"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.selling_price}
                    onChange={(e) => setFormData({ ...formData, selling_price: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="booking_date">Booking Date *</Label>
                  <Input
                    id="booking_date"
                    data-testid="booking-date-input"
                    type="date"
                    value={formData.booking_date}
                    onChange={(e) => setFormData({ ...formData, booking_date: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2 col-span-2">
                  <Label htmlFor="status">Status *</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(value) => setFormData({ ...formData, status: value })}
                  >
                    <SelectTrigger data-testid="booking-status-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">Open</SelectItem>
                      <SelectItem value="closed">Closed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2 col-span-2">
                  <Label htmlFor="notes">Notes</Label>
                  <Textarea
                    id="notes"
                    data-testid="booking-notes-input"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={3}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} data-testid="cancel-button">
                  Cancel
                </Button>
                <Button type="submit" className="rounded-sm" data-testid="save-booking-button">
                  {editingBooking ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle>All Bookings</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div>Loading...</div>
          ) : bookings.length === 0 ? (
            <div className="text-center py-12" data-testid="no-bookings-message">
              <p className="text-muted-foreground">No bookings found. Create your first booking to get started.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Client</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Stock</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Quantity</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Buy Price</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Sell Price</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Date</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Status</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">P&L</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bookings.map((booking) => (
                    <TableRow key={booking.id} className="table-row" data-testid="booking-row">
                      <TableCell className="font-medium">{booking.client_name}</TableCell>
                      <TableCell className="mono text-sm font-semibold">{booking.stock_symbol}</TableCell>
                      <TableCell className="mono">{booking.quantity}</TableCell>
                      <TableCell className="mono">₹{booking.buying_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</TableCell>
                      <TableCell className="mono">{booking.selling_price ? `₹${booking.selling_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}</TableCell>
                      <TableCell className="text-sm">{new Date(booking.booking_date).toLocaleDateString('en-IN')}</TableCell>
                      <TableCell>
                        <Badge variant={booking.status === 'open' ? 'default' : 'secondary'} data-testid="booking-status-badge">
                          {booking.status.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="mono font-semibold">
                        {booking.profit_loss !== null && booking.profit_loss !== undefined ? (
                          <span className={booking.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}>
                            ₹{booking.profit_loss.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </span>
                        ) : (
                          '-'
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(booking)}
                          data-testid="edit-booking-button"
                        >
                          <Pencil className="h-4 w-4" strokeWidth={1.5} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(booking.id)}
                          data-testid="delete-booking-button"
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

export default Bookings;
