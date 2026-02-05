import { useEffect, useState } from 'react';
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
import { useProtectedPage } from '../hooks/useProtectedPage';
import { Plus, Pencil, Trash2, Building2, Copy, Upload, FileText, CreditCard, FileCheck, Loader2, Sparkles, FolderOpen, Download, Eye, AlertCircle, AlertTriangle, CheckCircle, Search } from 'lucide-react';

const Vendors = () => {
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState(null);
  const [cloning, setCloning] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [processingOcr, setProcessingOcr] = useState({});
  const [documentsDialogOpen, setDocumentsDialogOpen] = useState(false);
  const [selectedVendorDocs, setSelectedVendorDocs] = useState(null);
  const [ocrDialogOpen, setOcrDialogOpen] = useState(false);
  const [selectedOcrData, setSelectedOcrData] = useState(null);
  
  // Name mismatch and proprietor workflow states
  const [ocrExtractedName, setOcrExtractedName] = useState('');
  const [nameMismatchDetected, setNameMismatchDetected] = useState(false);
  const [isProprietor, setIsProprietor] = useState(null); // null = not asked, true/false = answered
  const [proprietorDialogOpen, setProprietorDialogOpen] = useState(false);
  const [uploadingBankProof, setUploadingBankProof] = useState(null); // vendor ID being uploaded to
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',  // Primary email
    email_secondary: '',  // Secondary email
    email_tertiary: '',  // Third email
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
    bank_declaration: null,  // Required if proprietor with name mismatch
  });

  const { isLoading, isAuthorized, isPEDesk, isPEManager, isPELevel, hasPermission } = useProtectedPage({
    allowIf: ({ isPELevel, hasPermission }) => isPELevel || hasPermission('vendors.view'),
    deniedMessage: 'Access denied. You need Vendors permission to access this page.'
  });
  
  // Permission-based action controls
  const canCreateVendor = isPELevel || hasPermission('vendors.create');
  const canEditVendor = isPELevel || hasPermission('vendors.edit');
  const canDeleteVendor = isPELevel || hasPermission('vendors.delete');

  useEffect(() => {
    if (!isAuthorized) return;
    fetchVendors();
  }, [isAuthorized]);

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
            const extractedName = extracted.name || '';
            setOcrExtractedName(extractedName);
            
            setFormData(prev => {
              // Check for name mismatch if name was already entered
              if (prev.name && extractedName && prev.name.toLowerCase().trim() !== extractedName.toLowerCase().trim()) {
                setNameMismatchDetected(true);
                setProprietorDialogOpen(true);
              }
              return {
                ...prev,
                pan_number: extracted.pan_number || prev.pan_number,
                name: prev.name || extractedName, // Don't overwrite if already entered
              };
            });
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
            const extractedName = extracted.client_name || '';
            
            setFormData(prev => {
              // Check for name mismatch with OCR extracted name from PAN
              if (ocrExtractedName && extractedName && ocrExtractedName.toLowerCase().trim() !== extractedName.toLowerCase().trim()) {
                setNameMismatchDetected(true);
                setProprietorDialogOpen(true);
              }
              return {
                ...prev,
                dp_id: extracted.full_dp_client_id || extracted.dp_id || prev.dp_id,
                pan_number: extracted.pan_number || prev.pan_number,
                name: prev.name || extractedName,
                email: extracted.email || prev.email,
                phone: extracted.mobile || prev.phone,
              };
            });
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
  
  // Check name mismatch when user manually changes the name
  const handleNameChange = (newName) => {
    setFormData(prev => ({ ...prev, name: newName }));
    
    // Check against OCR extracted name
    if (ocrExtractedName && newName && ocrExtractedName.toLowerCase().trim() !== newName.toLowerCase().trim()) {
      if (!nameMismatchDetected) {
        setNameMismatchDetected(true);
        setProprietorDialogOpen(true);
      }
    } else {
      // Names match now, reset proprietor state
      setNameMismatchDetected(false);
      setIsProprietor(null);
    }
  };
  
  // Handle proprietor confirmation
  const handleProprietorResponse = (response) => {
    setIsProprietor(response);
    setProprietorDialogOpen(false);
    
    if (response) {
      toast.info('Please upload the Bank Declaration document to proceed.');
    } else {
      toast.warning('Please ensure the vendor name matches the PAN card name, or confirm as proprietor.');
    }
  };

  const uploadDocuments = async (vendorId) => {
    const docTypes = ['pan_card', 'cml_copy', 'cancelled_cheque', 'bank_declaration'];
    
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
      
      // If name mismatch detected, require proprietor confirmation
      if (nameMismatchDetected && isProprietor === null) {
        toast.error('Please confirm if this is a proprietorship entity');
        setProprietorDialogOpen(true);
        return false;
      }
      
      // If proprietor with name mismatch, require bank declaration
      if (nameMismatchDetected && isProprietor === true && !docFiles.bank_declaration) {
        missingDocs.push('Bank Declaration (required for proprietorship)');
      }
      
      // If not a proprietor but name mismatch exists, block creation
      if (nameMismatchDetected && isProprietor === false) {
        toast.error('Name mismatch detected. Please correct the vendor name to match the PAN card or confirm as proprietorship.');
        return false;
      }
      
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
      // Prepare submission data with proprietor flags
      const payload = { 
        ...formData, 
        is_vendor: true,
        is_proprietor: isProprietor === true,
        has_name_mismatch: nameMismatchDetected
      };
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
      email_secondary: vendor.email_secondary || '',
      email_tertiary: vendor.email_tertiary || '',
      phone: vendor.phone || '',
      pan_number: vendor.pan_number,
      dp_id: vendor.dp_id,
      bank_name: vendor.bank_name || '',
      account_number: vendor.account_number || '',
      ifsc_code: vendor.ifsc_code || '',
      is_vendor: true,
    });
    setDocFiles({ pan_card: null, cml_copy: null, cancelled_cheque: null, bank_declaration: null });
    // Reset name mismatch states for edit mode
    setOcrExtractedName('');
    setNameMismatchDetected(false);
    setIsProprietor(null);
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

  // Handle bank proof upload for proprietor vendors
  const handleBankProofUpload = async (vendorId, file) => {
    if (!file) return;
    
    setUploadingBankProof(vendorId);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      await api.post(`/clients/${vendorId}/bank-proof`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      toast.success('Bank proof uploaded successfully');
      fetchVendors();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload bank proof');
    } finally {
      setUploadingBankProof(null);
    }
  };

  const handleCloneToClient = async (vendor) => {
    if (!window.confirm(`Clone vendor "${vendor.name}" as a Client?\n\nThis will create a new client entry with the same details.`)) return;
    setCloning(true);
    try {
      const response = await api.post(`/clients/${vendor.id}/clone?target_type=client`);
      toast.success(response.data.message);
      if (window.confirm('Clone successful! Do you want to view the new client?')) {
        window.location.href = '/clients';
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

  const handleDownloadDocument = async (vendorId, filename, fileId = null) => {
    try {
      let response;
      
      // If we have a file ID, use the files endpoint directly
      if (fileId) {
        response = await api.get(`/files/${fileId}`, {
          responseType: 'blob'
        });
      } else {
        // Fall back to client document endpoint
        response = await api.get(`/clients/${vendorId}/documents/${encodeURIComponent(filename)}`, {
          responseType: 'blob'
        });
      }
      
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
      console.error('Download error:', error);
      toast.error('Failed to download document');
    }
  };

  const getDocTypeLabel = (docType) => {
    const labels = {
      'pan_card': 'PAN Card',
      'cml_copy': 'CML Copy',
      'cancelled_cheque': 'Cancelled Cheque',
      'bank_declaration': 'Bank Declaration'
    };
    return labels[docType] || docType;
  };

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      email_secondary: '',
      email_tertiary: '',
      phone: '',
      pan_number: '',
      dp_id: '',
      bank_name: '',
      account_number: '',
      ifsc_code: '',
      is_vendor: true,
    });
    setDocFiles({ pan_card: null, cml_copy: null, cancelled_cheque: null, bank_declaration: null });
    setEditingVendor(null);
    // Reset name mismatch states
    setOcrExtractedName('');
    setNameMismatchDetected(false);
    setIsProprietor(null);
  };

  const getDocIcon = (docType) => {
    switch (docType) {
      case 'pan_card': return <CreditCard className="h-5 w-5 text-blue-600" />;
      case 'cml_copy': return <FileCheck className="h-5 w-5 text-green-600" />;
      case 'cancelled_cheque': return <FileText className="h-5 w-5 text-orange-600" />;
      case 'bank_declaration': return <FileText className="h-5 w-5 text-purple-600" />;
      default: return <FileText className="h-5 w-5" />;
    }
  };

  // Show loading while checking permissions
  if (isLoading || loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="vendors-page">
      <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Vendors</h1>
          <p className="text-muted-foreground text-base">Manage your stock vendors and suppliers</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search vendors..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
              data-testid="vendor-search-input"
            />
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
                  {/* Name Mismatch Warning */}
                  {nameMismatchDetected && (
                    <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
                        <div className="flex-1">
                          <p className="font-medium text-amber-800 dark:text-amber-200">Name Mismatch Detected</p>
                          <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                            The vendor name &ldquo;<span className="font-semibold">{formData.name}</span>&rdquo; does not match 
                            the PAN card name &ldquo;<span className="font-semibold">{ocrExtractedName}</span>&rdquo;.
                          </p>
                          {isProprietor === true && (
                            <p className="text-sm text-emerald-700 dark:text-emerald-300 mt-2 flex items-center gap-1">
                              <FileCheck className="h-4 w-4" /> Proprietorship confirmed - Bank Declaration required
                            </p>
                          )}
                          {isProprietor === false && (
                            <p className="text-sm text-red-700 dark:text-red-300 mt-2">
                              Please correct the name or confirm as proprietorship to proceed.
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">Company/Vendor Name *</Label>
                      <Input
                        id="name"
                        data-testid="vendor-name-input"
                        value={formData.name}
                        onChange={(e) => handleNameChange(e.target.value)}
                        required
                      />
                      {/* Proprietorship checkbox - shown when PAN name is extracted */}
                      {ocrExtractedName && (
                        <div className="mt-2 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                          <p className="text-xs text-amber-700 dark:text-amber-300 mb-2">
                            <strong>PAN Name:</strong> {ocrExtractedName}
                          </p>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={isProprietor === true}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setIsProprietor(true);
                                  setNameMismatchDetected(true);
                                } else {
                                  setIsProprietor(null);
                                  // Re-check for actual mismatch
                                  const panName = ocrExtractedName?.toLowerCase().trim();
                                  const formName = formData.name?.toLowerCase().trim();
                                  if (panName && formName && panName !== formName) {
                                    setNameMismatchDetected(true);
                                  } else {
                                    setNameMismatchDetected(false);
                                  }
                                }
                              }}
                              className="w-4 h-4 text-emerald-600 rounded border-amber-300 focus:ring-emerald-500"
                              data-testid="vendor-proprietor-checkbox"
                            />
                            <span className="text-sm text-amber-800 dark:text-amber-200">
                              This is a <strong>Proprietorship</strong> (business name differs from proprietor&apos;s PAN name)
                            </span>
                          </label>
                          {isProprietor === true && (
                            <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1">
                              <FileCheck className="h-3 w-3" />
                              Proprietorship selected - Bank Declaration document will be required
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email">Primary Email</Label>
                      <Input
                        id="email"
                        data-testid="vendor-email-input"
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        placeholder="Primary email"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email_secondary">Secondary Email</Label>
                      <Input
                        id="email_secondary"
                        data-testid="vendor-email-secondary-input"
                        type="email"
                        value={formData.email_secondary}
                        onChange={(e) => setFormData({ ...formData, email_secondary: e.target.value })}
                        placeholder="Additional email"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email_tertiary">Tertiary Email</Label>
                      <Input
                        id="email_tertiary"
                        data-testid="vendor-email-tertiary-input"
                        type="email"
                        value={formData.email_tertiary}
                        onChange={(e) => setFormData({ ...formData, email_tertiary: e.target.value })}
                        placeholder="Third email"
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
                      <Label htmlFor="dp_id">DP ID</Label>
                      <Input
                        id="dp_id"
                        data-testid="vendor-dpid-input"
                        value={formData.dp_id}
                        onChange={(e) => setFormData({ ...formData, dp_id: e.target.value })}
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
                        <p className="text-xs text-amber-700 dark:text-amber-300">
                          Please upload PAN Card, CML Copy, and Cancelled Cheque to create a vendor.
                          {nameMismatchDetected && isProprietor === true && (
                            <span className="block mt-1 text-purple-700 dark:text-purple-300 font-medium">
                              + Bank Declaration (required for proprietorship with name mismatch)
                            </span>
                          )}
                        </p>
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

                  {/* Bank Declaration Upload - Required for Proprietorship with Name Mismatch */}
                  {nameMismatchDetected && isProprietor === true && (
                    <div className="border-2 border-purple-300 dark:border-purple-700 rounded-lg p-4 bg-purple-50 dark:bg-purple-900/20">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <FileText className="h-5 w-5 text-purple-600" />
                          <span className="font-medium text-purple-800 dark:text-purple-200">
                            Bank Declaration <span className="text-red-500">*</span>
                          </span>
                        </div>
                        {docFiles.bank_declaration && (
                          <Badge variant="outline" className="text-green-600 border-green-600">
                            ✓ {docFiles.bank_declaration.name}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Input
                          type="file"
                          accept="image/*,.pdf"
                          onChange={(e) => setDocFiles(prev => ({ ...prev, bank_declaration: e.target.files[0] }))}
                          className="flex-1"
                          data-testid="vendor-bank-declaration-upload"
                        />
                        <Upload className="h-5 w-5 text-purple-600" />
                      </div>
                      <p className="text-xs text-purple-700 dark:text-purple-300 mt-2">
                        Required for proprietorship entities where the business name differs from the PAN card name.
                        This declaration confirms the business operates under the proprietor&apos;s PAN.
                      </p>
                    </div>
                  )}

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

        {/* Proprietor Confirmation Dialog */}
        <Dialog open={proprietorDialogOpen} onOpenChange={setProprietorDialogOpen}>
          <DialogContent className="max-w-md" aria-describedby="proprietor-dialog-desc">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-amber-500" />
                Name Mismatch Detected
              </DialogTitle>
            </DialogHeader>
            <p id="proprietor-dialog-desc" className="sr-only">Confirm if this is a proprietorship entity</p>
            
            <div className="space-y-4">
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  The vendor name &ldquo;<strong>{formData.name}</strong>&rdquo; does not match 
                  the PAN card name &ldquo;<strong>{ocrExtractedName}</strong>&rdquo;.
                </p>
              </div>
              
              <p className="text-sm text-muted-foreground">
                Is this vendor a <strong>Proprietorship</strong> entity where the business operates 
                under the proprietor&apos;s personal PAN?
              </p>
              
              <div className="flex gap-3 pt-2">
                <Button 
                  onClick={() => handleProprietorResponse(true)}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                  data-testid="confirm-proprietor-yes"
                >
                  Yes, Proprietorship
                </Button>
                <Button 
                  onClick={() => handleProprietorResponse(false)}
                  variant="outline"
                  className="flex-1"
                  data-testid="confirm-proprietor-no"
                >
                  No, Correct Name
                </Button>
              </div>
            </div>
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
                {vendors
                  .filter(vendor => {
                    if (!searchQuery) return true;
                    const query = searchQuery.toLowerCase();
                    return (
                      vendor.name?.toLowerCase().includes(query) ||
                      vendor.email?.toLowerCase().includes(query) ||
                      vendor.pan_number?.toLowerCase().includes(query) ||
                      vendor.otc_ucc?.toLowerCase().includes(query) ||
                      vendor.phone?.toLowerCase().includes(query)
                    );
                  })
                  .map((vendor) => (
                  <TableRow key={vendor.id} data-testid="vendor-row">
                    <TableCell className="font-mono text-sm font-bold text-primary">{vendor.otc_ucc || 'N/A'}</TableCell>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2 flex-wrap">
                        {vendor.name}
                        {/* Cloned badge - visible to all */}
                        {vendor.is_cloned && (
                          <span 
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800"
                            title={`Cloned from ${vendor.cloned_from_type || 'client/vendor'}`}
                          >
                            <Copy className="h-3 w-3" />
                            Cloned
                          </span>
                        )}
                        {/* Red flag for proprietor with name mismatch - visible to PE Desk/Manager */}
                        {isPELevel && vendor.is_proprietor && vendor.has_name_mismatch && (
                          <div className="flex items-center gap-1">
                            <span 
                              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800"
                              title="Proprietorship - Name mismatch detected during creation"
                            >
                              <AlertTriangle className="h-3 w-3" />
                              Proprietor
                            </span>
                            {/* Bank proof status and upload button */}
                            {vendor.bank_proof_url ? (
                              <span 
                                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800"
                                title="Bank proof uploaded"
                              >
                                <CheckCircle className="h-3 w-3" />
                                Proof
                              </span>
                            ) : (
                              <label 
                                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border border-orange-200 dark:border-orange-800 cursor-pointer hover:bg-orange-200 dark:hover:bg-orange-900/50 transition-colors"
                                title="Upload bank proof document"
                              >
                                {uploadingBankProof === vendor.id ? (
                                  <Loader2 className="h-3 w-3 animate-spin" />
                                ) : (
                                  <Upload className="h-3 w-3" />
                                )}
                                <span>{uploadingBankProof === vendor.id ? 'Uploading...' : 'Upload Proof'}</span>
                                <input 
                                  type="file" 
                                  className="hidden" 
                                  accept=".pdf,.jpg,.jpeg,.png"
                                  onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) handleBankProofUpload(vendor.id, file);
                                    e.target.value = ''; // Reset input
                                  }}
                                  disabled={uploadingBankProof === vendor.id}
                                />
                              </label>
                            )}
                          </div>
                        )}
                      </div>
                    </TableCell>
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
                      {isPEDesk && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(vendor.id)}
                          data-testid="delete-vendor-button"
                        >
                          <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                        </Button>
                      )}
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
                          onClick={() => handleDownloadDocument(
                            selectedVendorDocs.id, 
                            doc.filename || doc.original_filename || doc.doc_type,
                            doc.file_id || doc.gridfs_id
                          )}
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
