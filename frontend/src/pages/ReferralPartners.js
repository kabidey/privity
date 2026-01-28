import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { toast } from 'sonner';
import { Users, Plus, Search, Edit, Upload, Eye, FileText, CreditCard, Wallet, CheckCircle, XCircle, Clock } from 'lucide-react';
import api from '../utils/api';

const ReferralPartners = () => {
  const [rps, setRps] = useState([]);
  const [pendingRps, setPendingRps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showViewDialog, setShowViewDialog] = useState(false);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [selectedRp, setSelectedRp] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    pan_number: '',
    aadhar_number: '',
    address: ''
  });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPELevel = currentUser.role === 1 || currentUser.role === 2;

  useEffect(() => {
    fetchRps();
    if (isPELevel) {
      fetchPendingRps();
    }
  }, [isPELevel]);

  const fetchRps = async () => {
    setLoading(true);
    try {
      const response = await api.get('/referral-partners?active_only=false');
      setRps(response.data);
    } catch (error) {
      toast.error('Failed to fetch referral partners');
    } finally {
      setLoading(false);
    }
  };

  const handleAddRp = async () => {
    // Validate all required fields
    if (!formData.name.trim()) {
      toast.error('Name is required');
      return;
    }
    if (!formData.email.trim()) {
      toast.error('Email is required');
      return;
    }
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      toast.error('Please enter a valid email address');
      return;
    }
    if (!formData.phone.trim()) {
      toast.error('Phone number is required');
      return;
    }
    // Validate 10-digit phone (without +91)
    const phoneDigits = formData.phone.replace(/\D/g, '');
    if (phoneDigits.length !== 10) {
      toast.error('Phone number must be exactly 10 digits (without +91)');
      return;
    }
    if (!formData.pan_number.trim() || formData.pan_number.length !== 10) {
      toast.error('PAN Number must be exactly 10 characters');
      return;
    }
    if (!formData.aadhar_number.trim()) {
      toast.error('Aadhar Number is required');
      return;
    }
    const aadharDigits = formData.aadhar_number.replace(/\D/g, '');
    if (aadharDigits.length !== 12) {
      toast.error('Aadhar Number must be exactly 12 digits');
      return;
    }
    if (!formData.address.trim()) {
      toast.error('Address is required');
      return;
    }

    setSubmitting(true);
    try {
      // Submit with cleaned phone number
      const submitData = {
        ...formData,
        phone: phoneDigits,
        aadhar_number: aadharDigits
      };
      const response = await api.post('/referral-partners', submitData);
      toast.success(`Referral Partner created with code: ${response.data.rp_code}. Please upload all required documents.`);
      setShowAddDialog(false);
      resetForm();
      fetchRps();
      // Open upload dialog for new RP
      setSelectedRp(response.data);
      setShowUploadDialog(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create referral partner');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditRp = async () => {
    // Validate all required fields
    if (!formData.name.trim()) {
      toast.error('Name is required');
      return;
    }
    if (!formData.email.trim()) {
      toast.error('Email is required');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      toast.error('Please enter a valid email address');
      return;
    }
    if (!formData.phone.trim()) {
      toast.error('Phone number is required');
      return;
    }
    const phoneDigits = formData.phone.replace(/\D/g, '');
    if (phoneDigits.length !== 10) {
      toast.error('Phone number must be exactly 10 digits (without +91)');
      return;
    }
    if (!formData.pan_number.trim() || formData.pan_number.length !== 10) {
      toast.error('PAN Number must be exactly 10 characters');
      return;
    }
    if (!formData.aadhar_number.trim()) {
      toast.error('Aadhar Number is required');
      return;
    }
    const aadharDigits = formData.aadhar_number.replace(/\D/g, '');
    if (aadharDigits.length !== 12) {
      toast.error('Aadhar Number must be exactly 12 digits');
      return;
    }
    if (!formData.address.trim()) {
      toast.error('Address is required');
      return;
    }

    setSubmitting(true);
    try {
      const submitData = {
        ...formData,
        phone: phoneDigits,
        aadhar_number: aadharDigits
      };
      await api.put(`/referral-partners/${selectedRp.id}`, submitData);
      toast.success('Referral Partner updated successfully');
      setShowEditDialog(false);
      resetForm();
      fetchRps();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update referral partner');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUploadDocument = async (documentType, file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    try {
      await api.post(`/referral-partners/${selectedRp.id}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success(`${documentType.replace('_', ' ')} uploaded successfully`);
      fetchRps();
      // Refresh selected RP
      const response = await api.get(`/referral-partners/${selectedRp.id}`);
      setSelectedRp(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
    }
  };

  const handleToggleActive = async (rp) => {
    try {
      await api.put(`/referral-partners/${rp.id}/toggle-active?is_active=${!rp.is_active}`);
      toast.success(`RP ${!rp.is_active ? 'activated' : 'deactivated'} successfully`);
      fetchRps();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      phone: '',
      pan_number: '',
      aadhar_number: '',
      address: ''
    });
    setSelectedRp(null);
  };

  const openEditDialog = (rp) => {
    setSelectedRp(rp);
    setFormData({
      name: rp.name,
      email: rp.email || '',
      phone: rp.phone || '',
      pan_number: rp.pan_number,
      aadhar_number: rp.aadhar_number,
      address: rp.address || ''
    });
    setShowEditDialog(true);
  };

  const openUploadDialog = (rp) => {
    setSelectedRp(rp);
    setShowUploadDialog(true);
  };

  const openViewDialog = async (rp) => {
    setSelectedRp(rp);
    setShowViewDialog(true);
  };

  const filteredRps = rps.filter(rp => {
    const search = searchTerm.toLowerCase();
    return (
      rp.name?.toLowerCase().includes(search) ||
      rp.rp_code?.toLowerCase().includes(search) ||
      rp.pan_number?.toLowerCase().includes(search) ||
      rp.phone?.includes(search)
    );
  });

  return (
    <div className="p-4 md:p-6 lg:p-8 space-y-6" data-testid="referral-partners-page">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="h-6 w-6" />
            Referral Partners
          </h1>
          <p className="text-muted-foreground">Manage referral partners and their revenue share</p>
        </div>
        <Button onClick={() => setShowAddDialog(true)} data-testid="add-rp-btn">
          <Plus className="h-4 w-4 mr-2" />
          Add Referral Partner
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <CardTitle>All Referral Partners</CardTitle>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name, code, PAN..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
                data-testid="rp-search"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">Loading...</div>
          ) : filteredRps.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No referral partners found
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>RP Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Mobile</TableHead>
                    <TableHead>PAN</TableHead>
                    <TableHead>Documents</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRps.map((rp) => (
                    <TableRow key={rp.id} data-testid={`rp-row-${rp.id}`}>
                      <TableCell>
                        <span className="font-mono font-bold text-primary">{rp.rp_code}</span>
                      </TableCell>
                      <TableCell className="font-medium">{rp.name}</TableCell>
                      <TableCell className="text-sm">{rp.email || '-'}</TableCell>
                      <TableCell className="font-mono">{rp.phone || '-'}</TableCell>
                      <TableCell className="font-mono text-sm">{rp.pan_number}</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          {rp.pan_card_url && (
                            <Badge variant="outline" className="text-xs bg-green-50 text-green-700">PAN</Badge>
                          )}
                          {rp.aadhar_card_url && (
                            <Badge variant="outline" className="text-xs bg-green-50 text-green-700">Aadhar</Badge>
                          )}
                          {rp.cancelled_cheque_url && (
                            <Badge variant="outline" className="text-xs bg-green-50 text-green-700">Cheque</Badge>
                          )}
                          {(!rp.pan_card_url || !rp.aadhar_card_url || !rp.cancelled_cheque_url) && (
                            <Badge variant="outline" className="text-xs bg-red-50 text-red-700">Incomplete</Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={rp.is_active ? 'default' : 'secondary'}>
                          {rp.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openViewDialog(rp)}
                            data-testid={`view-rp-${rp.id}`}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openUploadDialog(rp)}
                            data-testid={`upload-rp-${rp.id}`}
                          >
                            <Upload className="h-4 w-4" />
                          </Button>
                          {isPELevel && (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openEditDialog(rp)}
                                data-testid={`edit-rp-${rp.id}`}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleToggleActive(rp)}
                              >
                                {rp.is_active ? 'Deactivate' : 'Activate'}
                              </Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add RP Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Referral Partner</DialogTitle>
            <DialogDescription>
              Create a new referral partner. All fields are mandatory. Documents must be uploaded after creation.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name <span className="text-red-500">*</span></Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="Full name"
                data-testid="rp-name-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Email <span className="text-red-500">*</span></Label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  placeholder="email@example.com"
                  data-testid="rp-email-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Mobile (10 digits) <span className="text-red-500">*</span></Label>
                <Input
                  value={formData.phone}
                  onChange={(e) => {
                    // Allow only digits, max 10
                    const digits = e.target.value.replace(/\D/g, '').slice(0, 10);
                    setFormData({...formData, phone: digits});
                  }}
                  placeholder="9876543210"
                  maxLength={10}
                  data-testid="rp-phone-input"
                />
                <p className="text-xs text-muted-foreground">Enter 10 digit number without +91</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>PAN Number <span className="text-red-500">*</span></Label>
                <Input
                  value={formData.pan_number}
                  onChange={(e) => setFormData({...formData, pan_number: e.target.value.toUpperCase()})}
                  placeholder="ABCDE1234F"
                  maxLength={10}
                  data-testid="rp-pan-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Aadhar Number <span className="text-red-500">*</span></Label>
                <Input
                  value={formData.aadhar_number}
                  onChange={(e) => {
                    const digits = e.target.value.replace(/\D/g, '').slice(0, 12);
                    setFormData({...formData, aadhar_number: digits});
                  }}
                  placeholder="123456789012"
                  maxLength={12}
                  data-testid="rp-aadhar-input"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Address <span className="text-red-500">*</span></Label>
              <Textarea
                value={formData.address}
                onChange={(e) => setFormData({...formData, address: e.target.value})}
                placeholder="Full address"
                rows={2}
                data-testid="rp-address-input"
              />
            </div>
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
              <p className="text-sm text-yellow-800">
                <strong>Important:</strong> After creating the RP, you must upload the following mandatory documents:
              </p>
              <ul className="text-sm text-yellow-700 mt-1 list-disc list-inside">
                <li>PAN Card</li>
                <li>Aadhar Card</li>
                <li>Cancelled Cheque</li>
              </ul>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowAddDialog(false); resetForm(); }}>
              Cancel
            </Button>
            <Button onClick={handleAddRp} disabled={submitting} data-testid="save-rp-btn">
              {submitting ? 'Creating...' : 'Create RP'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit RP Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Referral Partner</DialogTitle>
            <DialogDescription>
              Update referral partner details. Code: {selectedRp?.rp_code}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name <span className="text-red-500">*</span></Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="Full name"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Email <span className="text-red-500">*</span></Label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  placeholder="email@example.com"
                />
              </div>
              <div className="space-y-2">
                <Label>Mobile (10 digits) <span className="text-red-500">*</span></Label>
                <Input
                  value={formData.phone}
                  onChange={(e) => {
                    const digits = e.target.value.replace(/\D/g, '').slice(0, 10);
                    setFormData({...formData, phone: digits});
                  }}
                  placeholder="9876543210"
                  maxLength={10}
                />
                <p className="text-xs text-muted-foreground">Enter 10 digit number without +91</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>PAN Number <span className="text-red-500">*</span></Label>
                <Input
                  value={formData.pan_number}
                  onChange={(e) => setFormData({...formData, pan_number: e.target.value.toUpperCase()})}
                  placeholder="ABCDE1234F"
                  maxLength={10}
                />
              </div>
              <div className="space-y-2">
                <Label>Aadhar Number <span className="text-red-500">*</span></Label>
                <Input
                  value={formData.aadhar_number}
                  onChange={(e) => {
                    const digits = e.target.value.replace(/\D/g, '').slice(0, 12);
                    setFormData({...formData, aadhar_number: digits});
                  }}
                  placeholder="123456789012"
                  maxLength={12}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Address <span className="text-red-500">*</span></Label>
              <Textarea
                value={formData.address}
                onChange={(e) => setFormData({...formData, address: e.target.value})}
                placeholder="Full address"
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowEditDialog(false); resetForm(); }}>
              Cancel
            </Button>
            <Button onClick={handleEditRp} disabled={submitting}>
              {submitting ? 'Updating...' : 'Update RP'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Documents Dialog */}
      <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Upload Documents</DialogTitle>
            <DialogDescription>
              Upload KYC documents for {selectedRp?.name} ({selectedRp?.rp_code}). All documents are mandatory.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <CreditCard className="h-4 w-4" />
                PAN Card <span className="text-red-500">*</span>
                {selectedRp?.pan_card_url && <Badge variant="outline" className="ml-2 bg-green-50 text-green-700">Uploaded</Badge>}
              </Label>
              <Input
                type="file"
                accept="image/*,.pdf"
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    handleUploadDocument('pan_card', e.target.files[0]);
                  }
                }}
              />
            </div>
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Aadhar Card <span className="text-red-500">*</span>
                {selectedRp?.aadhar_card_url && <Badge variant="outline" className="ml-2 bg-green-50 text-green-700">Uploaded</Badge>}
              </Label>
              <Input
                type="file"
                accept="image/*,.pdf"
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    handleUploadDocument('aadhar_card', e.target.files[0]);
                  }
                }}
              />
            </div>
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Wallet className="h-4 w-4" />
                Cancelled Cheque <span className="text-red-500">*</span>
                {selectedRp?.cancelled_cheque_url && <Badge variant="outline" className="ml-2 bg-green-50 text-green-700">Uploaded</Badge>}
              </Label>
              <Input
                type="file"
                accept="image/*,.pdf"
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    handleUploadDocument('cancelled_cheque', e.target.files[0]);
                  }
                }}
              />
            </div>
            {selectedRp && (!selectedRp.pan_card_url || !selectedRp.aadhar_card_url || !selectedRp.cancelled_cheque_url) && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-sm text-red-700">
                  <strong>Warning:</strong> All documents are mandatory. Please upload all pending documents.
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View RP Dialog */}
      <Dialog open={showViewDialog} onOpenChange={setShowViewDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Referral Partner Details</DialogTitle>
          </DialogHeader>
          {selectedRp && (
            <div className="space-y-4">
              <div className="bg-primary/10 p-4 rounded-lg text-center">
                <p className="text-sm text-muted-foreground">RP Code</p>
                <p className="text-2xl font-mono font-bold text-primary">{selectedRp.rp_code}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Name</p>
                  <p className="font-medium">{selectedRp.name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <Badge variant={selectedRp.is_active ? 'default' : 'secondary'}>
                    {selectedRp.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">PAN Number</p>
                  <p className="font-mono">{selectedRp.pan_number}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Aadhar Number</p>
                  <p className="font-mono">{selectedRp.aadhar_number}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Email</p>
                  <p>{selectedRp.email || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Phone</p>
                  <p>{selectedRp.phone || '-'}</p>
                </div>
              </div>
              {selectedRp.address && (
                <div>
                  <p className="text-sm text-muted-foreground">Address</p>
                  <p>{selectedRp.address}</p>
                </div>
              )}
              <div>
                <p className="text-sm text-muted-foreground mb-2">Documents</p>
                <div className="flex gap-2">
                  {selectedRp.pan_card_url && (
                    <Button variant="outline" size="sm" asChild>
                      <a href={selectedRp.pan_card_url} target="_blank" rel="noopener noreferrer">
                        View PAN Card
                      </a>
                    </Button>
                  )}
                  {selectedRp.aadhar_card_url && (
                    <Button variant="outline" size="sm" asChild>
                      <a href={selectedRp.aadhar_card_url} target="_blank" rel="noopener noreferrer">
                        View Aadhar
                      </a>
                    </Button>
                  )}
                  {selectedRp.cancelled_cheque_url && (
                    <Button variant="outline" size="sm" asChild>
                      <a href={selectedRp.cancelled_cheque_url} target="_blank" rel="noopener noreferrer">
                        View Cheque
                      </a>
                    </Button>
                  )}
                </div>
              </div>
              <div className="text-xs text-muted-foreground">
                Created by {selectedRp.created_by_name} on {new Date(selectedRp.created_at).toLocaleDateString()}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowViewDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ReferralPartners;
