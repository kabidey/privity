import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, Pencil, Trash2, Building2, Copy, Upload, FileText, CreditCard, FileCheck, Loader2, Sparkles, FolderOpen, Download, Eye, AlertCircle } from 'lucide-react';

const Vendors = () => {
  const navigate = useNavigate();
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState(null);
  const [cloning, setCloning] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [processingOcr, setProcessingOcr] = useState({});
  const [documentsDialogOpen, setDocumentsDialogOpen] = useState(false);
  const [selectedVendorDocs, setSelectedVendorDocs] = useState(null);
  const [ocrDialogOpen, setOcrDialogOpen] = useState(false);
  const [selectedOcrData, setSelectedOcrData] = useState(null);
  
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

  const [docFiles, setDocFiles] = useState({
    pan_card: null,
    cml_copy: null,
    cancelled_cheque: null,
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

  const handleFileChange = async (docType, file) => {
    if (!file) return;
    
    setDocFiles(prev => ({ ...prev, [docType]: file }));
    
    // Process OCR automatically
    if (['pan_card', 'cml_copy', 'cancelled_cheque'].includes(docType)) {
      setProcessingOcr(prev => ({ ...prev, [docType]: true }));
      try {
        const formDataUpload = new FormData();
        formDataUpload.append('file', file);
        formDataUpload.append('doc_type', docType);
        
        // Upload to temp and get OCR
        const response = await api.post('/clients/temp-upload', formDataUpload, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        if (response.data.ocr_data?.extracted_data) {
          const extracted = response.data.ocr_data.extracted_data;
          
          // Auto-fill form based on OCR data
          if (docType === 'pan_card' && extracted.pan_number) {
            setFormData(prev => ({
              ...prev,
              pan_number: extracted.pan_number || prev.pan_number,
              name: extracted.name || prev.name,
            }));
            toast.success('PAN card data extracted');
          } else if (docType === 'cancelled_cheque') {
            setFormData(prev => ({
              ...prev,
              bank_name: extracted.bank_name || prev.bank_name,
              account_number: extracted.account_number || prev.account_number,
              ifsc_code: extracted.ifsc_code || prev.ifsc_code,
            }));
            toast.success('Bank details extracted from cheque');
          } else if (docType === 'cml_copy') {
            setFormData(prev => ({
              ...prev,
              dp_id: extracted.full_dp_client_id || extracted.dp_id || prev.dp_id,
              pan_number: extracted.pan_number || prev.pan_number,
              name: extracted.client_name || prev.name,
              email: extracted.email || prev.email,
              phone: extracted.mobile || prev.phone,
            }));
            toast.success('CML data extracted');
          }
        }
      } catch (error) {
        console.error('OCR processing failed:', error);
      } finally {
        setProcessingOcr(prev => ({ ...prev, [docType]: false }));
      }
    }
  };

  const uploadDocuments = async (vendorId) => {
    const docTypes = ['pan_card', 'cml_copy', 'cancelled_cheque'];
    
    for (const docType of docTypes) {
      if (docFiles[docType]) {
        const formDataUpload = new FormData();
        formDataUpload.append('file', docFiles[docType]);
        formDataUpload.append('doc_type', docType);
        
        try {
          await api.post(`/clients/${vendorId}/documents`, formDataUpload, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
        } catch (error) {
          console.error(`Failed to upload ${docType}:`, error);
        }
      }
    }
  };

  const validateDocuments = () => {
    // For new vendors, all documents are mandatory
    if (!editingVendor) {
      const missingDocs = [];
      if (!docFiles.pan_card) missingDocs.push('PAN Card');
      if (!docFiles.cml_copy) missingDocs.push('CML Copy');
      if (!docFiles.cancelled_cheque) missingDocs.push('Cancelled Cheque');
      
      if (missingDocs.length > 0) {
        toast.error(`Please upload: ${missingDocs.join(', ')}`);
        return false;
      }
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate mandatory documents for new vendors
    if (!validateDocuments()) {
      return;
    }
    
    setUploading(true);
    try {
      const payload = { ...formData, is_vendor: true };
      let vendorId;
      
      if (editingVendor) {
        await api.put(`/clients/${editingVendor.id}`, payload);
        vendorId = editingVendor.id;
        toast.success('Vendor updated successfully');
      } else {
        const response = await api.post('/clients', payload);
        vendorId = response.data.id;
        toast.success('Vendor created successfully');
      }
      
      // Upload documents
      const hasDocuments = Object.values(docFiles).some(f => f !== null);
      if (hasDocuments && vendorId) {
        await uploadDocuments(vendorId);
        toast.success('Documents uploaded successfully');
      }
      
      setDialogOpen(false);
      resetForm();
      fetchVendors();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    } finally {
      setUploading(false);
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
    setDocFiles({ pan_card: null, cml_copy: null, cancelled_cheque: null });
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
      if (window.confirm('Clone successful! Do you want to view the new client?')) {
        navigate('/clients');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clone vendor as client');
    } finally {
      setCloning(false);
    }
  };

  const handleViewDocuments = (vendor) => {
    setSelectedVendorDocs(vendor);
    setDocumentsDialogOpen(true);
  };

  const handleDownloadDocument = async (vendorId, filename) => {
    try {
      const response = await api.get(`/clients/${vendorId}/documents/${filename}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Document downloaded');
    } catch (error) {
      toast.error('Failed to download document');
    }
  };

  const getDocTypeLabel = (docType) => {
    const labels = {
      'pan_card': 'PAN Card',
      'cml_copy': 'CML Copy',
      'cancelled_cheque': 'Cancelled Cheque'
    };
    return labels[docType] || docType;
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
    setDocFiles({ pan_card: null, cml_copy: null, cancelled_cheque: null });
    setEditingVendor(null);
  };

  const getDocIcon = (docType) => {
    switch (docType) {
      case 'pan_card': return <CreditCard className="h-5 w-5 text-blue-600" />;
      case 'cml_copy': return <FileCheck className="h-5 w-5 text-green-600" />;
      case 'cancelled_cheque': return <FileText className="h-5 w-5 text-orange-600" />;
      default: return <FileText className="h-5 w-5" />;
    }
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="vendors-page">
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
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" aria-describedby="vendor-dialog-description">
            <DialogHeader>
              <DialogTitle>{editingVendor ? 'Edit Vendor' : 'Add New Vendor'}</DialogTitle>
            </DialogHeader>
            <p id="vendor-dialog-description" className="sr-only">Form to add or edit vendor details</p>
            
            <Tabs defaultValue="details" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="details">Vendor Details</TabsTrigger>
                <TabsTrigger value="documents">
                  Documents {!editingVendor && <span className="text-red-500 ml-1">*</span>}
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="details">
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
                  </div>

                  <div className="border-t pt-4 mt-4">
                    <h4 className="font-semibold mb-3">Bank Details</h4>
                    <div className="grid grid-cols-3 gap-4">
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
                  </div>

                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" data-testid="save-vendor-button" disabled={uploading}>
                      {uploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {editingVendor ? 'Update' : 'Create'} Vendor
                    </Button>
                  </div>
                </form>
              </TabsContent>
              
              <TabsContent value="documents">
                <div className="space-y-4">
                  {!editingVendor && (
                    <div className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                      <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-amber-800 dark:text-amber-200">All documents are mandatory</p>
                        <p className="text-xs text-amber-700 dark:text-amber-300">Please upload PAN Card, CML Copy, and Cancelled Cheque to create a vendor.</p>
                      </div>
                    </div>
                  )}
                  
                  {/* PAN Card Upload */}
                  <div className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <CreditCard className="h-5 w-5 text-blue-600" />
                        <span className="font-medium">PAN Card {!editingVendor && <span className="text-red-500">*</span>}</span>
                      </div>
                      {processingOcr.pan_card && (
                        <Badge variant="secondary" className="animate-pulse">
                          <Sparkles className="h-3 w-3 mr-1" /> Processing OCR...
                        </Badge>
                      )}
                      {docFiles.pan_card && !processingOcr.pan_card && (
                        <Badge variant="outline" className="text-green-600 border-green-600">
                          ✓ {docFiles.pan_card.name}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        type="file"
                        accept="image/*,.pdf"
                        onChange={(e) => handleFileChange('pan_card', e.target.files[0])}
                        className="flex-1"
                        data-testid="vendor-pan-upload"
                      />
                      <Upload className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">Upload PAN card image or PDF. OCR will auto-fill vendor details.</p>
                  </div>

                  {/* CML Copy Upload */}
                  <div className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <FileCheck className="h-5 w-5 text-green-600" />
                        <span className="font-medium">CML Copy {!editingVendor && <span className="text-red-500">*</span>}</span>
                      </div>
                      {processingOcr.cml_copy && (
                        <Badge variant="secondary" className="animate-pulse">
                          <Sparkles className="h-3 w-3 mr-1" /> Processing OCR...
                        </Badge>
                      )}
                      {docFiles.cml_copy && !processingOcr.cml_copy && (
                        <Badge variant="outline" className="text-green-600 border-green-600">
                          ✓ {docFiles.cml_copy.name}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        type="file"
                        accept="image/*,.pdf"
                        onChange={(e) => handleFileChange('cml_copy', e.target.files[0])}
                        className="flex-1"
                        data-testid="vendor-cml-upload"
                      />
                      <Upload className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">Upload CML (Client Master List) copy. OCR will extract DP ID and other details.</p>
                  </div>

                  {/* Cancelled Cheque Upload */}
                  <div className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <FileText className="h-5 w-5 text-orange-600" />
                        <span className="font-medium">Cancelled Cheque {!editingVendor && <span className="text-red-500">*</span>}</span>
                      </div>
                      {processingOcr.cancelled_cheque && (
                        <Badge variant="secondary" className="animate-pulse">
                          <Sparkles className="h-3 w-3 mr-1" /> Processing OCR...
                        </Badge>
                      )}
                      {docFiles.cancelled_cheque && !processingOcr.cancelled_cheque && (
                        <Badge variant="outline" className="text-green-600 border-green-600">
                          ✓ {docFiles.cancelled_cheque.name}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        type="file"
                        accept="image/*,.pdf"
                        onChange={(e) => handleFileChange('cancelled_cheque', e.target.files[0])}
                        className="flex-1"
                        data-testid="vendor-cheque-upload"
                      />
                      <Upload className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">Upload cancelled cheque image. OCR will extract bank account details.</p>
                  </div>

                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleSubmit} 
                      data-testid="save-vendor-with-docs-button" 
                      disabled={uploading || Object.values(processingOcr).some(v => v)}
                    >
                      {uploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {editingVendor ? 'Update' : 'Create'} Vendor
                    </Button>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle>All Vendors</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">Loading vendors...</div>
          ) : vendors.length === 0 ? (
            <div className="text-center py-12">
              <Building2 className="mx-auto h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-lg font-medium">No vendors found</p>
              <p className="text-muted-foreground">Add your first vendor to get started.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs uppercase">OTC UCC</TableHead>
                  <TableHead className="text-xs uppercase">Name</TableHead>
                  <TableHead className="text-xs uppercase">PAN</TableHead>
                  <TableHead className="text-xs uppercase">DP ID</TableHead>
                  <TableHead className="text-xs uppercase">Bank</TableHead>
                  <TableHead className="text-xs uppercase">Docs</TableHead>
                  <TableHead className="text-xs uppercase text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {vendors.map((vendor) => (
                  <TableRow key={vendor.id} data-testid="vendor-row">
                    <TableCell className="font-mono text-sm font-bold text-primary">{vendor.otc_ucc || 'N/A'}</TableCell>
                    <TableCell className="font-medium">{vendor.name}</TableCell>
                    <TableCell className="font-mono text-sm">{vendor.pan_number}</TableCell>
                    <TableCell className="text-sm">{vendor.dp_id}</TableCell>
                    <TableCell className="text-sm">{vendor.bank_name || '-'}</TableCell>
                    <TableCell>
                      {vendor.documents && vendor.documents.length > 0 ? (
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleViewDocuments(vendor)}
                          className="text-blue-600 hover:text-blue-700"
                          title="View Documents"
                        >
                          <FolderOpen className="h-4 w-4 mr-1" />
                          <span className="text-xs">{vendor.documents.length}</span>
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
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
          )}
        </CardContent>
      </Card>

      {/* Documents View Dialog */}
      <Dialog open={documentsDialogOpen} onOpenChange={setDocumentsDialogOpen}>
        <DialogContent className="max-w-2xl" aria-describedby="docs-desc">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5" />
              Vendor Documents
            </DialogTitle>
          </DialogHeader>
          <p id="docs-desc" className="sr-only">View and download vendor documents</p>
          {selectedVendorDocs && (
            <div className="space-y-4">
              <div className="border-b pb-3">
                <p className="font-semibold">{selectedVendorDocs.name}</p>
                <p className="text-sm text-muted-foreground">OTC UCC: {selectedVendorDocs.otc_ucc}</p>
              </div>
              
              {selectedVendorDocs.documents && selectedVendorDocs.documents.length > 0 ? (
                <div className="space-y-3">
                  {selectedVendorDocs.documents.map((doc, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                      <div className="flex items-center gap-3">
                        {getDocIcon(doc.doc_type)}
                        <div>
                          <p className="font-medium">{getDocTypeLabel(doc.doc_type)}</p>
                          <p className="text-xs text-muted-foreground">{doc.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            Uploaded: {new Date(doc.upload_date).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {doc.ocr_data?.status === 'processed' && (
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => {
                              setSelectedOcrData({ doc });
                              setOcrDialogOpen(true);
                            }}
                            title="View OCR Data"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        )}
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleDownloadDocument(selectedVendorDocs.id, doc.filename)}
                          className="text-blue-600 hover:text-blue-700"
                        >
                          <Download className="h-4 w-4 mr-1" />
                          Download
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-8">No documents uploaded for this vendor.</p>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* OCR Data Dialog */}
      <Dialog open={ocrDialogOpen} onOpenChange={setOcrDialogOpen}>
        <DialogContent className="max-w-2xl" aria-describedby="ocr-desc">
          <DialogHeader>
            <DialogTitle>OCR Extracted Data</DialogTitle>
          </DialogHeader>
          <p id="ocr-desc" className="sr-only">View OCR data</p>
          {selectedOcrData && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                {getDocIcon(selectedOcrData.doc?.doc_type)}
                <span className="font-semibold capitalize">{selectedOcrData.doc?.doc_type?.replace('_', ' ')}</span>
              </div>
              <div className="border rounded-lg p-4 bg-muted/30">
                {selectedOcrData.doc?.ocr_data?.extracted_data ? (
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(selectedOcrData.doc.ocr_data.extracted_data).map(([key, value]) => (
                      <div key={key} className="space-y-1">
                        <Label className="text-xs text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</Label>
                        <p className="font-mono text-sm">{String(value) || 'N/A'}</p>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-muted-foreground">No OCR data available</p>}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Vendors;
