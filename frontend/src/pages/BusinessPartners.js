import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  Users, 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw, 
  Mail, 
  Phone, 
  Percent, 
  UserCheck,
  Building2,
  Search,
  Upload,
  FileCheck,
  FileX,
  Eye,
  X
} from 'lucide-react';

const BusinessPartners = () => {
  const navigate = useNavigate();
  const [partners, setPartners] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPartner, setEditingPartner] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterEmployee, setFilterEmployee] = useState('');
  
  // Document upload state
  const [docDialogOpen, setDocDialogOpen] = useState(false);
  const [selectedPartnerForDocs, setSelectedPartnerForDocs] = useState(null);
  const [uploadingDoc, setUploadingDoc] = useState(null);
  const fileInputRefs = {
    pan_card: useRef(null),
    aadhaar_card: useRef(null),
    cancelled_cheque: useRef(null)
  };

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPELevel = currentUser.role === 1 || currentUser.role === 2;
  const isPEDesk = currentUser.role === 1;

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    mobile: '',
    pan_number: '',
    address: '',
    revenue_share_percent: '',
    linked_employee_id: '',
    notes: '',
    is_active: true
  });

  useEffect(() => {
    if (!isPELevel) {
      navigate('/');
      return;
    }
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [partnersRes, usersRes] = await Promise.all([
        api.get('/business-partners'),
        api.get('/users')
      ]);
      setPartners(partnersRes.data);
      // Filter to get only employees (roles 3-7)
      setEmployees(usersRes.data.filter(u => u.role >= 3 && u.role <= 7));
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      phone: '',
      mobile: '',
      pan_number: '',
      address: '',
      revenue_share_percent: '',
      linked_employee_id: '',
      notes: '',
      is_active: true
    });
    setEditingPartner(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name || !formData.email || !formData.revenue_share_percent || !formData.linked_employee_id) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      const payload = {
        ...formData,
        revenue_share_percent: parseFloat(formData.revenue_share_percent)
      };

      if (editingPartner) {
        await api.put(`/business-partners/${editingPartner.id}`, payload);
        toast.success('Business Partner updated successfully');
      } else {
        await api.post('/business-partners', payload);
        toast.success('Business Partner created successfully');
      }

      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const handleEdit = (partner) => {
    setEditingPartner(partner);
    setFormData({
      name: partner.name,
      email: partner.email,
      phone: partner.phone || '',
      mobile: partner.mobile || '',
      pan_number: partner.pan_number || '',
      address: partner.address || '',
      revenue_share_percent: partner.revenue_share_percent?.toString() || '',
      linked_employee_id: partner.linked_employee_id || '',
      notes: partner.notes || '',
      is_active: partner.is_active !== false
    });
    setDialogOpen(true);
  };

  const handleDelete = async (partnerId) => {
    if (!window.confirm('Are you sure you want to delete this Business Partner?')) return;
    
    try {
      await api.delete(`/business-partners/${partnerId}`);
      toast.success('Business Partner deleted');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete');
    }
  };

  // Document upload functions
  const openDocDialog = (partner) => {
    setSelectedPartnerForDocs(partner);
    setDocDialogOpen(true);
  };

  const handleDocUpload = async (docType) => {
    const file = fileInputRefs[docType].current?.files[0];
    if (!file) {
      toast.error('Please select a file');
      return;
    }
    
    // Validate file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Only PDF, JPG, and PNG files are allowed');
      return;
    }
    
    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File size must be less than 5MB');
      return;
    }
    
    setUploadingDoc(docType);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.post(
        `/business-partners/${selectedPartnerForDocs.id}/documents/${docType}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      
      toast.success(`${docType.replace(/_/g, ' ')} uploaded successfully`);
      
      // Update local state with new documents
      setSelectedPartnerForDocs(prev => ({
        ...prev,
        documents: response.data.all_documents,
        documents_verified: response.data.documents_verified
      }));
      
      // Update partners list
      setPartners(prev => prev.map(p => 
        p.id === selectedPartnerForDocs.id 
          ? { ...p, documents: response.data.all_documents, documents_verified: response.data.documents_verified }
          : p
      ));
      
      // Clear file input
      if (fileInputRefs[docType].current) {
        fileInputRefs[docType].current.value = '';
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploadingDoc(null);
    }
  };

  const getDocumentByType = (documents, docType) => {
    return documents?.find(d => d.doc_type === docType);
  };

  const getDocTypeLabel = (docType) => {
    const labels = {
      pan_card: 'PAN Card',
      aadhaar_card: 'Aadhaar Card',
      cancelled_cheque: 'Cancelled Cheque'
    };
    return labels[docType] || docType;
  };

  const filteredPartners = partners.filter(p => {
    const matchesSearch = !searchTerm || 
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.pan_number && p.pan_number.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesEmployee = !filterEmployee || filterEmployee === 'all' || p.linked_employee_id === filterEmployee;
    
    return matchesSearch && matchesEmployee;
  });

  if (!isPELevel) return null;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="ios-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 page-enter" data-testid="business-partners-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Building2 className="h-7 w-7 text-emerald-500" />
            Business Partners
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Manage external business partners and revenue sharing</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchData} className="rounded-xl">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button className="rounded-xl bg-emerald-500 hover:bg-emerald-600" data-testid="add-bp-btn">
                <Plus className="h-4 w-4 mr-2" />
                Add Partner
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{editingPartner ? 'Edit Business Partner' : 'Add Business Partner'}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2 col-span-2">
                    <Label>Name *</Label>
                    <Input
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="Partner name"
                      required
                    />
                  </div>
                  
                  <div className="space-y-2 col-span-2">
                    <Label>Email *</Label>
                    <Input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="partner@example.com"
                      required
                      disabled={editingPartner}
                    />
                    {!editingPartner && (
                      <p className="text-xs text-muted-foreground">This email will be used for OTP login</p>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Phone</Label>
                    <Input
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      placeholder="Landline"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Mobile</Label>
                    <Input
                      value={formData.mobile}
                      onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                      placeholder="Mobile number"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>PAN Number</Label>
                    <Input
                      value={formData.pan_number}
                      onChange={(e) => setFormData({ ...formData, pan_number: e.target.value.toUpperCase() })}
                      placeholder="ABCDE1234F"
                      maxLength={10}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Revenue Share % *</Label>
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      value={formData.revenue_share_percent}
                      onChange={(e) => setFormData({ ...formData, revenue_share_percent: e.target.value })}
                      placeholder="e.g., 30"
                      required
                    />
                  </div>
                  
                  <div className="space-y-2 col-span-2">
                    <Label>Linked Employee *</Label>
                    <Select 
                      value={formData.linked_employee_id} 
                      onValueChange={(v) => setFormData({ ...formData, linked_employee_id: v })}
                      required
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select employee" />
                      </SelectTrigger>
                      <SelectContent>
                        {employees.map((emp) => (
                          <SelectItem key={emp.id} value={emp.id}>
                            {emp.name} ({emp.role_name || 'Employee'})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">BP's revenue is calculated from this employee's bookings</p>
                  </div>
                  
                  <div className="space-y-2 col-span-2">
                    <Label>Address</Label>
                    <Textarea
                      value={formData.address}
                      onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                      placeholder="Full address"
                      rows={2}
                    />
                  </div>
                  
                  <div className="space-y-2 col-span-2">
                    <Label>Notes</Label>
                    <Textarea
                      value={formData.notes}
                      onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                      placeholder="Internal notes"
                      rows={2}
                    />
                  </div>
                  
                  {editingPartner && (
                    <div className="flex items-center justify-between col-span-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <div>
                        <Label>Active Status</Label>
                        <p className="text-xs text-muted-foreground">Inactive partners cannot login</p>
                      </div>
                      <Switch
                        checked={formData.is_active}
                        onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                      />
                    </div>
                  )}
                </div>
                
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" className="bg-emerald-500 hover:bg-emerald-600">
                    {editingPartner ? 'Update Partner' : 'Create Partner'}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 text-emerald-500">
                <Users className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold">{partners.length}</p>
                <p className="text-xs text-muted-foreground">Total Partners</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-green-50 dark:bg-green-900/20 text-green-500">
                <UserCheck className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold">{partners.filter(p => p.is_active !== false).length}</p>
                <p className="text-xs text-muted-foreground">Active</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-500">
                <Percent className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {partners.length > 0 
                    ? (partners.reduce((sum, p) => sum + (p.revenue_share_percent || 0), 0) / partners.length).toFixed(1)
                    : 0}%
                </p>
                <p className="text-xs text-muted-foreground">Avg Revenue Share</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-purple-50 dark:bg-purple-900/20 text-purple-500">
                <Building2 className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {new Set(partners.map(p => p.linked_employee_id)).size}
                </p>
                <p className="text-xs text-muted-foreground">Linked Employees</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name, email, or PAN..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={filterEmployee} onValueChange={setFilterEmployee}>
          <SelectTrigger className="w-full sm:w-[200px]">
            <SelectValue placeholder="Filter by employee" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Employees</SelectItem>
            {employees.map((emp) => (
              <SelectItem key={emp.id} value={emp.id}>{emp.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Partners Table */}
      <Card>
        <CardHeader>
          <CardTitle>Business Partners ({filteredPartners.length})</CardTitle>
          <CardDescription>Partners can login using OTP sent to their email</CardDescription>
        </CardHeader>
        <CardContent>
          {filteredPartners.length === 0 ? (
            <div className="text-center py-12">
              <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No business partners found</p>
              <Button 
                variant="outline" 
                className="mt-4"
                onClick={() => setDialogOpen(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Partner
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Partner</TableHead>
                    <TableHead>Contact</TableHead>
                    <TableHead>Revenue Share</TableHead>
                    <TableHead>Linked Employee</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPartners.map((partner) => (
                    <TableRow key={partner.id} data-testid="bp-row">
                      <TableCell>
                        <div>
                          <p className="font-semibold">{partner.name}</p>
                          {partner.pan_number && (
                            <p className="text-xs text-muted-foreground mono">{partner.pan_number}</p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="flex items-center gap-1 text-sm">
                            <Mail className="h-3 w-3" />
                            {partner.email}
                          </div>
                          {partner.mobile && (
                            <div className="flex items-center gap-1 text-sm text-muted-foreground">
                              <Phone className="h-3 w-3" />
                              {partner.mobile}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                          <Percent className="h-3 w-3 mr-1" />
                          {partner.revenue_share_percent}%
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <UserCheck className="h-4 w-4 text-muted-foreground" />
                          <span>{partner.linked_employee_name || 'Not Set'}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={partner.is_active !== false ? 'default' : 'secondary'}>
                          {partner.is_active !== false ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(partner)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        {isPEDesk && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(partner.id)}
                            className="text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
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

      {/* Info Card */}
      <Card className="border-dashed">
        <CardContent className="p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-3">How Business Partner Login Works</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
            <div className="flex items-start gap-2">
              <div className="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 flex items-center justify-center flex-shrink-0">1</div>
              <p className="text-muted-foreground">Partner enters their email on the login page and selects "Business Partner Login"</p>
            </div>
            <div className="flex items-start gap-2">
              <div className="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 flex items-center justify-center flex-shrink-0">2</div>
              <p className="text-muted-foreground">A 6-digit OTP is sent to their email (valid for 10 minutes)</p>
            </div>
            <div className="flex items-start gap-2">
              <div className="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 flex items-center justify-center flex-shrink-0">3</div>
              <p className="text-muted-foreground">Partner enters OTP and gains access to their dashboard with revenue reports</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default BusinessPartners;
