import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, Pencil, Trash2, Building2, Copy } from 'lucide-react';

const Vendors = () => {
  const navigate = useNavigate();
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState(null);
  const [cloning, setCloning] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    pan_number: '',
    dp_id: '',
    bank_name: '',
    account_number: '',
    ifsc_code: '',
    is_vendor: true,
  });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPEDesk = currentUser.role === 1;

  useEffect(() => {
    // Only PE Desk can access vendors
    if (!isPEDesk) {
      toast.error('Access denied. Only PE Desk can manage vendors.');
      navigate('/');
      return;
    }
    fetchVendors();
  }, [isPEDesk, navigate]);

  const fetchVendors = async () => {
    try {
      const response = await api.get('/clients?is_vendor=true');
      setVendors(response.data);
    } catch (error) {
      toast.error('Failed to load vendors');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...formData, is_vendor: true };
      if (editingVendor) {
        await api.put(`/clients/${editingVendor.id}`, payload);
        toast.success('Vendor updated successfully');
      } else {
        await api.post('/clients', payload);
        toast.success('Vendor created successfully');
      }
      setDialogOpen(false);
      resetForm();
      fetchVendors();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const handleEdit = (vendor) => {
    setEditingVendor(vendor);
    setFormData({
      name: vendor.name,
      email: vendor.email || '',
      phone: vendor.phone || '',
      pan_number: vendor.pan_number,
      dp_id: vendor.dp_id,
      bank_name: vendor.bank_name || '',
      account_number: vendor.account_number || '',
      ifsc_code: vendor.ifsc_code || '',
      is_vendor: true,
    });
    setDialogOpen(true);
  };

  const handleDelete = async (vendorId) => {
    if (!window.confirm('Are you sure you want to delete this vendor?')) return;
    try {
      await api.delete(`/clients/${vendorId}`);
      toast.success('Vendor deleted successfully');
      fetchVendors();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete vendor');
    }
  };

  const handleCloneToClient = async (vendor) => {
    if (!window.confirm(`Clone vendor "${vendor.name}" as a Client?\n\nThis will create a new client entry with the same details.`)) return;
    setCloning(true);
    try {
      const response = await api.post(`/clients/${vendor.id}/clone?target_type=client`);
      toast.success(response.data.message);
      // Optionally navigate to clients page
      if (window.confirm('Clone successful! Do you want to view the new client?')) {
        navigate('/clients');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clone vendor as client');
    } finally {
      setCloning(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      phone: '',
      pan_number: '',
      dp_id: '',
      bank_name: '',
      account_number: '',
      ifsc_code: '',
      is_vendor: true,
    });
    setEditingVendor(null);
  };

  return (
    <div className="p-8 page-enter" data-testid="vendors-page">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Vendors</h1>
          <p className="text-muted-foreground text-base">Manage your stock vendors and suppliers</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button className="rounded-sm" data-testid="add-vendor-button">
              <Plus className="mr-2 h-4 w-4" strokeWidth={1.5} />
              Add Vendor
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" aria-describedby="vendor-dialog-description">
            <DialogHeader>
              <DialogTitle>{editingVendor ? 'Edit Vendor' : 'Add New Vendor'}</DialogTitle>
            </DialogHeader>
            <p id="vendor-dialog-description" className="sr-only">Form to add or edit vendor details</p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Company/Vendor Name *</Label>
                  <Input
                    id="name"
                    data-testid="vendor-name-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    data-testid="vendor-email-input"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    data-testid="vendor-phone-input"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pan_number">PAN Number *</Label>
                  <Input
                    id="pan_number"
                    data-testid="vendor-pan-input"
                    value={formData.pan_number}
                    onChange={(e) => setFormData({ ...formData, pan_number: e.target.value.toUpperCase() })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dp_id">DP ID *</Label>
                  <Input
                    id="dp_id"
                    data-testid="vendor-dpid-input"
                    value={formData.dp_id}
                    onChange={(e) => setFormData({ ...formData, dp_id: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="bank_name">Bank Name</Label>
                  <Input
                    id="bank_name"
                    data-testid="vendor-bank-input"
                    value={formData.bank_name}
                    onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="account_number">Account Number</Label>
                  <Input
                    id="account_number"
                    data-testid="vendor-account-input"
                    value={formData.account_number}
                    onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ifsc_code">IFSC Code</Label>
                  <Input
                    id="ifsc_code"
                    data-testid="vendor-ifsc-input"
                    value={formData.ifsc_code}
                    onChange={(e) => setFormData({ ...formData, ifsc_code: e.target.value.toUpperCase() })}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} data-testid="cancel-button">
                  Cancel
                </Button>
                <Button type="submit" className="rounded-sm" data-testid="save-vendor-button">
                  {editingVendor ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" strokeWidth={1.5} />
            All Vendors
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div>Loading...</div>
          ) : vendors.length === 0 ? (
            <div className="text-center py-12" data-testid="no-vendors-message">
              <p className="text-muted-foreground">No vendors found. Add your first vendor to start purchasing stocks.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Name</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Email</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Phone</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">PAN</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">DP ID</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Type</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {vendors.map((vendor) => (
                    <TableRow key={vendor.id} className="table-row" data-testid="vendor-row">
                      <TableCell className="font-medium">{vendor.name}</TableCell>
                      <TableCell>{vendor.email || '-'}</TableCell>
                      <TableCell>{vendor.phone || '-'}</TableCell>
                      <TableCell className="mono text-sm">{vendor.pan_number}</TableCell>
                      <TableCell className="mono text-sm">{vendor.dp_id}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">Vendor</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCloneToClient(vendor)}
                          disabled={cloning}
                          title="Clone as Client"
                          className="text-blue-600 hover:text-blue-700"
                        >
                          <Copy className="h-4 w-4" strokeWidth={1.5} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(vendor)}
                          data-testid="edit-vendor-button"
                        >
                          <Pencil className="h-4 w-4" strokeWidth={1.5} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(vendor.id)}
                          data-testid="delete-vendor-button"
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

export default Vendors;
