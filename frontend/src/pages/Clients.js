import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, Pencil, Trash2, PieChart, Upload, FileText, CreditCard, FileCheck, UserCog, Loader2, Sparkles, Check, Clock, CheckCircle, XCircle, Download, Eye, FolderOpen } from 'lucide-react';

const Clients = () => {
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [pendingClients, setPendingClients] = useState([]);
  const [documentsDialogOpen, setDocumentsDialogOpen] = useState(false);
  const [selectedClientDocs, setSelectedClientDocs] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [docDialogOpen, setDocDialogOpen] = useState(false);
  const [mappingDialogOpen, setMappingDialogOpen] = useState(false);
  const [ocrDialogOpen, setOcrDialogOpen] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [selectedClient, setSelectedClient] = useState(null);
  const [selectedOcrData, setSelectedOcrData] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [processingOcr, setProcessingOcr] = useState({});
  const [ocrResults, setOcrResults] = useState({});
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    mobile: '',
    pan_number: '',
    dp_id: '',
    dp_type: 'outside',
    trading_ucc: '',
    address: '',
    pin_code: '',
    bank_accounts: [],
  });
  
  const [newBankAccount, setNewBankAccount] = useState({
    bank_name: '',
    account_number: '',
    ifsc_code: '',
    branch_name: '',
    source: 'manual'
  });
  
  const [docFiles, setDocFiles] = useState({
    pan_card: null,
    cml_copy: null,
    cancelled_cheque: null,
  });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPEDesk = currentUser.role === 1;
  const isAdmin = currentUser.role <= 2;
  const isManager = currentUser.role <= 3;
  const isEmployee = currentUser.role === 4;

  useEffect(() => {
    fetchClients();
    if (!isEmployee) {
      fetchEmployees();
      if (isManager) fetchPendingClients();
    }
  }, []);

  // Filter clients based on search query
  const filteredClients = clients.filter(client => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      client.name?.toLowerCase().includes(query) ||
      client.pan_number?.toLowerCase().includes(query)
    );
  });

  const filteredPendingClients = pendingClients.filter(client => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      client.name?.toLowerCase().includes(query) ||
      client.pan_number?.toLowerCase().includes(query)
    );
  });

  const fetchClients = async () => {
    try {
      const response = await api.get('/clients?is_vendor=false');
      setClients(response.data);
    } catch (error) {
      toast.error('Failed to load clients');
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingClients = async () => {
    try {
      const response = await api.get('/clients/pending-approval');
      setPendingClients(response.data);
    } catch (error) {
      console.error('Failed to load pending clients');
    }
  };

  const fetchEmployees = async () => {
    try {
      const response = await api.get('/employees');
      setEmployees(response.data);
    } catch (error) {
      console.error('Failed to load employees');
    }
  };

  const processOcrAndAutofill = async (docType, file) => {
    if (!file) return;
    
    setProcessingOcr(prev => ({ ...prev, [docType]: true }));
    
    try {
      const formDataUpload = new FormData();
      formDataUpload.append('file', file);
      formDataUpload.append('doc_type', docType);
      
      const response = await api.post('/ocr/preview', formDataUpload, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const ocrData = response.data;
      setOcrResults(prev => ({ ...prev, [docType]: ocrData }));
      
      if (ocrData?.extracted_data) {
        const extracted = ocrData.extracted_data;
        
        if (docType === 'pan_card') {
          setFormData(prev => ({
            ...prev,
            name: extracted.name || prev.name,
            pan_number: extracted.pan_number || prev.pan_number,
          }));
          if (extracted.name || extracted.pan_number) {
            toast.success('PAN card data auto-filled!');
          }
        } else if (docType === 'cancelled_cheque') {
          // Add as new bank account if different from existing
          if (extracted.account_number && extracted.ifsc_code) {
            const newBank = {
              bank_name: extracted.bank_name || '',
              account_number: extracted.account_number,
              ifsc_code: extracted.ifsc_code,
              branch_name: extracted.branch_name || '',
              account_holder_name: extracted.account_holder_name || '',
              source: 'cancelled_cheque'
            };
            
            setFormData(prev => {
              const exists = prev.bank_accounts.some(b => b.account_number === newBank.account_number);
              if (!exists) {
                toast.success('Bank account added from cheque!');
                return { ...prev, bank_accounts: [...prev.bank_accounts, newBank] };
              }
              return prev;
            });
          }
        } else if (docType === 'cml_copy') {
          // Check if we got actual extracted data (not just raw_text)
          const hasValidData = extracted.dp_id || extracted.client_id || extracted.full_dp_client_id ||
                               extracted.client_name || extracted.pan_number || extracted.email || extracted.mobile;
          
          if (hasValidData) {
            // Construct full DP ID: prefer full_dp_client_id, else combine dp_id + client_id
            let fullDpId = extracted.full_dp_client_id;
            if (!fullDpId && extracted.dp_id && extracted.client_id) {
              fullDpId = `${extracted.dp_id}${extracted.client_id}`;
            } else if (!fullDpId) {
              fullDpId = extracted.dp_id || extracted.client_id;
            }
            
            // Clean mobile number - remove ISD codes and keep only 10 digits
            let cleanMobile = extracted.mobile || '';
            if (cleanMobile) {
              // Remove +91, 91, 0 prefix and any spaces/dashes
              cleanMobile = cleanMobile.replace(/[\s\-\(\)]/g, '');
              cleanMobile = cleanMobile.replace(/^\+?91/, '');
              cleanMobile = cleanMobile.replace(/^0/, '');
              // Keep only last 10 digits if longer
              if (cleanMobile.length > 10) {
                cleanMobile = cleanMobile.slice(-10);
              }
            }
            
            setFormData(prev => ({
              ...prev,
              dp_id: fullDpId || prev.dp_id,
              name: extracted.client_name || prev.name,
              pan_number: extracted.pan_number || prev.pan_number,
              email: extracted.email || prev.email,
              mobile: cleanMobile || prev.mobile,
              address: extracted.address || prev.address,
              pin_code: extracted.pin_code || prev.pin_code,
            }));
            
            // Add bank from CML if present
            if (extracted.account_number && extracted.ifsc_code) {
              const newBank = {
                bank_name: extracted.bank_name || '',
                account_number: extracted.account_number,
                ifsc_code: extracted.ifsc_code,
                branch_name: extracted.branch_name || '',
                source: 'cml_copy'
              };
              
              setFormData(prev => {
                const exists = prev.bank_accounts.some(b => b.account_number === newBank.account_number);
                if (!exists) {
                  return { ...prev, bank_accounts: [...prev.bank_accounts, newBank] };
                }
                return prev;
              });
            }
            
            toast.success('CML data auto-filled!');
          } else if (extracted.raw_text) {
            toast.warning('Could not extract structured data from CML. Please fill fields manually.');
          } else {
            toast.warning('No data could be extracted from CML.');
          }
        }
      }
    } catch (error) {
      console.error('OCR preview error:', error);
      const errorMsg = error.response?.data?.detail || 'OCR processing failed';
      toast.error(`OCR Error: ${errorMsg}`);
    } finally {
      setProcessingOcr(prev => ({ ...prev, [docType]: false }));
    }
  };

  const handleFileChange = async (docType, file) => {
    setDocFiles(prev => ({ ...prev, [docType]: file }));
    if (file) {
      await processOcrAndAutofill(docType, file);
    }
  };

  const addBankAccount = () => {
    if (newBankAccount.bank_name && newBankAccount.account_number && newBankAccount.ifsc_code) {
      setFormData(prev => ({
        ...prev,
        bank_accounts: [...prev.bank_accounts, { ...newBankAccount }]
      }));
      setNewBankAccount({ bank_name: '', account_number: '', ifsc_code: '', branch_name: '', source: 'manual' });
      toast.success('Bank account added');
    } else {
      toast.error('Please fill bank name, account number and IFSC');
    }
  };

  const removeBankAccount = (index) => {
    setFormData(prev => ({
      ...prev,
      bank_accounts: prev.bank_accounts.filter((_, i) => i !== index)
    }));
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    
    // Validate required fields
    if (!formData.name || !formData.name.trim()) {
      toast.error('Client name is required');
      return;
    }
    if (!formData.pan_number || !formData.pan_number.trim()) {
      toast.error('PAN number is required');
      return;
    }
    if (!formData.dp_id || !formData.dp_id.trim()) {
      toast.error('DP ID is required');
      return;
    }
    // Validate Trading UCC if DP is with SMIFS
    if (formData.dp_type === 'smifs' && !formData.trading_ucc?.trim()) {
      toast.error('Trading UCC is required when DP is with SMIFS');
      return;
    }
    
    try {
      let clientId;
      if (editingClient) {
        await api.put(`/clients/${editingClient.id}`, formData);
        clientId = editingClient.id;
        toast.success('Client updated successfully');
      } else {
        const response = await api.post('/clients', formData);
        clientId = response.data.id;
        if (isEmployee) {
          toast.success('Client created - pending approval');
        } else {
          toast.success('Client created successfully');
        }
      }
      
      const hasDocuments = Object.values(docFiles).some(f => f !== null);
      if (hasDocuments && clientId) {
        await uploadDocuments(clientId);
      }
      
      setDialogOpen(false);
      resetForm();
      fetchClients();
      if (isManager) fetchPendingClients();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const uploadDocuments = async (clientId) => {
    setUploading(true);
    try {
      for (const [docType, file] of Object.entries(docFiles)) {
        if (file) {
          const fd = new FormData();
          fd.append('file', file);
          fd.append('doc_type', docType);
          await api.post(`/clients/${clientId}/documents`, fd, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
        }
      }
      toast.success('Documents uploaded successfully');
    } catch (error) {
      toast.error('Failed to upload some documents');
    } finally {
      setUploading(false);
    }
  };

  const handleViewDocuments = (client) => {
    setSelectedClientDocs(client);
    setDocumentsDialogOpen(true);
  };

  const handleDownloadDocument = async (clientId, filename) => {
    try {
      const response = await api.get(`/clients/${clientId}/documents/${filename}`, {
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

  const handleApprove = async (clientId, approve) => {
    try {
      await api.put(`/clients/${clientId}/approve?approve=${approve}`);
      toast.success(approve ? 'Client approved' : 'Client rejected');
      fetchClients();
      fetchPendingClients();
    } catch (error) {
      toast.error('Failed to update approval status');
    }
  };

  const handleEdit = (client) => {
    if (!isPEDesk) {
      toast.error('Only PE Desk can modify clients');
      return;
    }
    setEditingClient(client);
    setFormData({
      name: client.name,
      email: client.email || '',
      phone: client.phone || '',
      mobile: client.mobile || '',
      pan_number: client.pan_number,
      dp_id: client.dp_id,
      dp_type: client.dp_type || 'outside',
      trading_ucc: client.trading_ucc || '',
      address: client.address || '',
      pin_code: client.pin_code || '',
      bank_accounts: client.bank_accounts || [],
    });
    setDocFiles({ pan_card: null, cml_copy: null, cancelled_cheque: null });
    setOcrResults({});
    setDialogOpen(true);
  };

  const handleDelete = async (clientId) => {
    if (!isPEDesk) {
      toast.error('Only PE Desk can delete clients');
      return;
    }
    if (!window.confirm('Are you sure you want to delete this client?')) return;
    try {
      await api.delete(`/clients/${clientId}`);
      toast.success('Client deleted successfully');
      fetchClients();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete client');
    }
  };

  const handleMapping = (client) => {
    setSelectedClient(client);
    setMappingDialogOpen(true);
  };

  const handleMappingSubmit = async (employeeId) => {
    try {
      await api.put(`/clients/${selectedClient.id}/employee-mapping`, null, {
        params: { employee_id: employeeId || null }
      });
      toast.success(employeeId ? 'Client mapped to employee' : 'Client unmapped');
      setMappingDialogOpen(false);
      fetchClients();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update mapping');
    }
  };

  const viewOcrData = (client, doc) => {
    setSelectedOcrData({ client, doc });
    setOcrDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '', email: '', phone: '', mobile: '', pan_number: '', dp_id: '',
      dp_type: 'outside', trading_ucc: '',
      address: '', pin_code: '', bank_accounts: [],
    });
    setDocFiles({ pan_card: null, cml_copy: null, cancelled_cheque: null });
    setOcrResults({});
    setEditingClient(null);
  };

  const getDocIcon = (docType) => {
    switch (docType) {
      case 'pan_card': return <CreditCard className="h-4 w-4" />;
      case 'cml_copy': return <FileCheck className="h-4 w-4" />;
      case 'cancelled_cheque': return <FileText className="h-4 w-4" />;
      default: return <FileText className="h-4 w-4" />;
    }
  };

  const getStatusBadge = (client) => {
    if (client.approval_status === 'pending') {
      return <Badge variant="outline" className="text-orange-600 border-orange-600"><Clock className="h-3 w-3 mr-1" />Pending</Badge>;
    }
    if (client.approval_status === 'rejected') {
      return <Badge variant="outline" className="text-red-600 border-red-600"><XCircle className="h-3 w-3 mr-1" />Rejected</Badge>;
    }
    if (client.is_active) {
      return <Badge variant="outline" className="text-green-600 border-green-600"><CheckCircle className="h-3 w-3 mr-1" />Active</Badge>;
    }
    return null;
  };

  const hasValidOcrData = (docType) => {
    const data = ocrResults[docType]?.extracted_data;
    if (!data || data.raw_text) return false;
    
    if (docType === 'pan_card') {
      return data.name || data.pan_number;
    } else if (docType === 'cml_copy') {
      return data.dp_id || data.client_id || data.client_name || data.pan_number || data.email || data.mobile;
    } else if (docType === 'cancelled_cheque') {
      return data.account_number || data.ifsc_code;
    }
    return false;
  };

  const DocumentUploadCard = ({ docType, label, icon: Icon, color, description }) => (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-5 w-5 ${color}`} />
          <Label className="font-semibold">{label}</Label>
        </div>
        {processingOcr[docType] && (
          <div className="flex items-center gap-1 text-xs text-blue-600">
            <Loader2 className="h-3 w-3 animate-spin" />
            Processing OCR...
          </div>
        )}
        {hasValidOcrData(docType) && !processingOcr[docType] && (
          <div className="flex items-center gap-1 text-xs text-green-600">
            <Check className="h-3 w-3" />
            Auto-filled
          </div>
        )}
        {ocrResults[docType]?.extracted_data?.raw_text && !processingOcr[docType] && (
          <div className="flex items-center gap-1 text-xs text-orange-600">
            <Clock className="h-3 w-3" />
            Manual entry needed
          </div>
        )}
      </div>
      <p className="text-xs text-muted-foreground mb-2">{description}</p>
      <Input
        type="file"
        accept=".jpg,.jpeg,.pdf,.png"
        data-testid={`${docType}-upload`}
        onChange={(e) => handleFileChange(docType, e.target.files[0])}
      />
      {docFiles[docType] && (
        <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
          <Check className="h-3 w-3" />
          {docFiles[docType].name}
        </p>
      )}
    </div>
  );

  // Use filtered clients based on search
  const displayedClients = activeTab === 'pending' ? filteredPendingClients : filteredClients;

  return (
    <div className="p-8 page-enter" data-testid="clients-page">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Clients</h1>
          <p className="text-muted-foreground text-base">
            {isEmployee ? 'Manage your clients' : 'Manage clients with documents and employee mapping'}
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
          <DialogTrigger asChild>
            <Button className="rounded-sm" data-testid="add-client-button">
              <Plus className="mr-2 h-4 w-4" strokeWidth={1.5} />
              Add Client
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" aria-describedby="client-dialog-desc">
            <DialogHeader>
              <DialogTitle>{editingClient ? 'Edit Client' : 'Add New Client'}</DialogTitle>
            </DialogHeader>
            <p id="client-dialog-desc" className="sr-only">Form to add or edit client details</p>
            
            <Tabs defaultValue="details" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="details">Client Details</TabsTrigger>
                <TabsTrigger value="bank">Bank Accounts</TabsTrigger>
                <TabsTrigger value="documents">Documents & OCR</TabsTrigger>
              </TabsList>
              
              <TabsContent value="details">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Name *</Label>
                      <Input data-testid="client-name-input" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
                    </div>
                    <div className="space-y-2">
                      <Label>Email</Label>
                      <Input type="email" data-testid="client-email-input" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} />
                    </div>
                    <div className="space-y-2">
                      <Label>Phone</Label>
                      <Input data-testid="client-phone-input" value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} />
                    </div>
                    <div className="space-y-2">
                      <Label>Mobile</Label>
                      <Input data-testid="client-mobile-input" value={formData.mobile} onChange={(e) => setFormData({ ...formData, mobile: e.target.value })} />
                    </div>
                    <div className="space-y-2">
                      <Label>PAN Number *</Label>
                      <Input data-testid="client-pan-input" value={formData.pan_number} onChange={(e) => setFormData({ ...formData, pan_number: e.target.value.toUpperCase() })} required />
                    </div>
                    <div className="space-y-2">
                      <Label>DP ID *</Label>
                      <Input data-testid="client-dpid-input" value={formData.dp_id} onChange={(e) => setFormData({ ...formData, dp_id: e.target.value })} required />
                    </div>
                    <div className="space-y-2">
                      <Label>DP Type *</Label>
                      <Select 
                        value={formData.dp_type} 
                        onValueChange={(value) => setFormData({ ...formData, dp_type: value, trading_ucc: value === 'outside' ? '' : formData.trading_ucc })}
                      >
                        <SelectTrigger data-testid="dp-type-select">
                          <SelectValue placeholder="Select DP Type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="smifs">DP With SMIFS</SelectItem>
                          <SelectItem value="outside">DP Outside</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    {formData.dp_type === 'smifs' && (
                      <div className="space-y-2">
                        <Label>Trading UCC *</Label>
                        <Input 
                          data-testid="trading-ucc-input" 
                          value={formData.trading_ucc} 
                          onChange={(e) => setFormData({ ...formData, trading_ucc: e.target.value.toUpperCase() })} 
                          required={formData.dp_type === 'smifs'}
                          placeholder="Enter Trading UCC"
                        />
                      </div>
                    )}
                    <div className={`space-y-2 ${formData.dp_type === 'smifs' ? '' : 'col-span-2'}`}>
                      <Label>Address</Label>
                      <Textarea data-testid="client-address-input" value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} rows={2} />
                    </div>
                    <div className="space-y-2">
                      <Label>Pin Code</Label>
                      <Input data-testid="client-pincode-input" value={formData.pin_code} onChange={(e) => setFormData({ ...formData, pin_code: e.target.value })} />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button type="submit" className="rounded-sm" data-testid="save-client-button" disabled={uploading}>
                      {uploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {editingClient ? 'Update' : 'Create'}
                    </Button>
                  </div>
                </form>
              </TabsContent>
              
              <TabsContent value="bank">
                <div className="space-y-4">
                  <div className="border rounded-lg p-4">
                    <h4 className="font-semibold mb-3">Add Bank Account</h4>
                    <div className="grid grid-cols-2 gap-3">
                      <Input placeholder="Bank Name" value={newBankAccount.bank_name} onChange={(e) => setNewBankAccount({ ...newBankAccount, bank_name: e.target.value })} />
                      <Input placeholder="Account Number" value={newBankAccount.account_number} onChange={(e) => setNewBankAccount({ ...newBankAccount, account_number: e.target.value })} />
                      <Input placeholder="IFSC Code" value={newBankAccount.ifsc_code} onChange={(e) => setNewBankAccount({ ...newBankAccount, ifsc_code: e.target.value.toUpperCase() })} />
                      <Input placeholder="Branch Name" value={newBankAccount.branch_name} onChange={(e) => setNewBankAccount({ ...newBankAccount, branch_name: e.target.value })} />
                    </div>
                    <Button type="button" onClick={addBankAccount} className="mt-3" variant="outline" size="sm">
                      <Plus className="h-4 w-4 mr-1" /> Add Bank Account
                    </Button>
                  </div>
                  
                  {formData.bank_accounts.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-semibold">Bank Accounts ({formData.bank_accounts.length})</h4>
                      {formData.bank_accounts.map((bank, idx) => (
                        <div key={idx} className="border rounded-lg p-3 flex justify-between items-start">
                          <div>
                            <p className="font-medium">{bank.bank_name}</p>
                            <p className="text-sm text-muted-foreground">A/C: {bank.account_number} | IFSC: {bank.ifsc_code}</p>
                            <Badge variant="outline" className="text-xs mt-1">{bank.source}</Badge>
                          </div>
                          <Button type="button" variant="ghost" size="sm" onClick={() => removeBankAccount(idx)}>
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>
              
              <TabsContent value="documents">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
                    <Sparkles className="h-5 w-5 text-blue-600" />
                    <p className="text-sm text-blue-800 dark:text-blue-200">
                      <strong>AI Auto-fill:</strong> Upload documents and OCR will extract and fill form fields. Different bank accounts are automatically added.
                    </p>
                  </div>
                  
                  <div className="grid grid-cols-1 gap-4">
                    <DocumentUploadCard docType="pan_card" label="PAN Card" icon={CreditCard} color="text-blue-600" description="Extracts: Name, PAN Number" />
                    <DocumentUploadCard docType="cml_copy" label="CML Copy" icon={FileCheck} color="text-purple-600" description="Extracts: DP ID, Name, PAN, Email, Mobile, Address, Bank Details" />
                    <DocumentUploadCard docType="cancelled_cheque" label="Cancelled Cheque" icon={FileText} color="text-orange-600" description="Extracts: Bank Name, Account Number, IFSC Code (adds as separate bank account)" />
                  </div>
                  
                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleSubmit} disabled={uploading || Object.values(processingOcr).some(v => v)}>
                      {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                      {editingClient ? 'Update & Upload' : 'Create & Upload'}
                    </Button>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </DialogContent>
        </Dialog>
      </div>

      {isManager && pendingClients.length > 0 && (
        <div className="mb-4">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="all">All Clients ({filteredClients.length})</TabsTrigger>
              <TabsTrigger value="pending" className="text-orange-600">
                <Clock className="h-4 w-4 mr-1" />
                Pending Approval ({filteredPendingClients.length})
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      )}

      <Card className="border shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle>{activeTab === 'pending' ? 'Pending Approval' : 'All Clients'}</CardTitle>
          <div className="w-72">
            <Input 
              placeholder="Search by Name or PAN..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              data-testid="client-search-input"
              className="h-9"
            />
          </div>
        </CardHeader>
        <CardContent>
          {loading ? <div>Loading...</div> : displayedClients.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                {searchQuery ? `No clients found matching "${searchQuery}"` : 'No clients found.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase">OTC UCC</TableHead>
                    <TableHead className="text-xs uppercase">Name</TableHead>
                    <TableHead className="text-xs uppercase">PAN</TableHead>
                    <TableHead className="text-xs uppercase">DP Type</TableHead>
                    <TableHead className="text-xs uppercase">Mobile</TableHead>
                    <TableHead className="text-xs uppercase">Status</TableHead>
                    {!isEmployee && <TableHead className="text-xs uppercase">Mapped To</TableHead>}
                    <TableHead className="text-xs uppercase">Banks</TableHead>
                    <TableHead className="text-xs uppercase">Docs</TableHead>
                    <TableHead className="text-xs uppercase text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedClients.map((client) => (
                    <TableRow key={client.id} data-testid="client-row">
                      <TableCell className="font-mono text-sm font-bold text-primary">{client.otc_ucc || 'N/A'}</TableCell>
                      <TableCell className="font-medium">{client.name}</TableCell>
                      <TableCell className="mono text-sm">{client.pan_number}</TableCell>
                      <TableCell>
                        <Badge variant={client.dp_type === 'smifs' ? 'default' : 'outline'} className="text-xs">
                          {client.dp_type === 'smifs' ? 'SMIFS' : 'Outside'}
                        </Badge>
                        {client.dp_type === 'smifs' && client.trading_ucc && (
                          <span className="text-xs text-muted-foreground ml-1">({client.trading_ucc})</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">{client.mobile || client.phone || '-'}</TableCell>
                      <TableCell>{getStatusBadge(client)}</TableCell>
                      {!isEmployee && (
                        <TableCell>
                          {client.mapped_employee_name ? <Badge variant="secondary">{client.mapped_employee_name}</Badge> : <span className="text-xs text-muted-foreground">Not mapped</span>}
                        </TableCell>
                      )}
                      <TableCell>
                        <Badge variant="outline">{client.bank_accounts?.length || 0}</Badge>
                      </TableCell>
                      <TableCell>
                        {client.documents && client.documents.length > 0 ? (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={() => handleViewDocuments(client)}
                            className="text-blue-600 hover:text-blue-700"
                            title="View Documents"
                          >
                            <FolderOpen className="h-4 w-4 mr-1" />
                            <span className="text-xs">{client.documents.length}</span>
                          </Button>
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {activeTab === 'pending' && isManager && (
                          <>
                            <Button variant="ghost" size="sm" onClick={() => handleApprove(client.id, true)} className="text-green-600">
                              <CheckCircle className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleApprove(client.id, false)} className="text-red-600">
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        <Button variant="ghost" size="sm" onClick={() => navigate(`/clients/${client.id}/portfolio`)} title="View Portfolio">
                          <PieChart className="h-4 w-4" />
                        </Button>
                        {isAdmin && (
                          <Button variant="ghost" size="sm" onClick={() => handleMapping(client)} title="Map to Employee">
                            <UserCog className="h-4 w-4" />
                          </Button>
                        )}
                        {isPEDesk && (
                          <>
                            <Button variant="ghost" size="sm" onClick={() => handleEdit(client)} title="Edit Client"><Pencil className="h-4 w-4" /></Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(client.id)} title="Delete Client"><Trash2 className="h-4 w-4" /></Button>
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

      {/* Dialogs */}
      <Dialog open={mappingDialogOpen} onOpenChange={setMappingDialogOpen}>
        <DialogContent aria-describedby="mapping-desc">
          <DialogHeader><DialogTitle>Map Client to Employee</DialogTitle></DialogHeader>
          <p id="mapping-desc" className="sr-only">Map or unmap client to employee</p>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Client: <span className="font-semibold">{selectedClient?.name}</span></p>
            <Select onValueChange={(value) => handleMappingSubmit(value === 'unmap' ? null : value)}>
              <SelectTrigger><SelectValue placeholder="Select an employee" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="unmap">-- Unmap --</SelectItem>
                {employees.map((emp) => (
                  <SelectItem key={emp.id} value={emp.id}>{emp.name} ({emp.role_name})</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={ocrDialogOpen} onOpenChange={setOcrDialogOpen}>
        <DialogContent className="max-w-2xl" aria-describedby="ocr-desc">
          <DialogHeader><DialogTitle>OCR Extracted Data</DialogTitle></DialogHeader>
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

      {/* Documents View Dialog */}
      <Dialog open={documentsDialogOpen} onOpenChange={setDocumentsDialogOpen}>
        <DialogContent className="max-w-2xl" aria-describedby="docs-desc">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5" />
              Client Documents
            </DialogTitle>
          </DialogHeader>
          <p id="docs-desc" className="sr-only">View and download client documents</p>
          {selectedClientDocs && (
            <div className="space-y-4">
              <div className="border-b pb-3">
                <p className="font-semibold">{selectedClientDocs.name}</p>
                <p className="text-sm text-muted-foreground">OTC UCC: {selectedClientDocs.otc_ucc}</p>
              </div>
              
              {selectedClientDocs.documents && selectedClientDocs.documents.length > 0 ? (
                <div className="space-y-3">
                  {selectedClientDocs.documents.map((doc, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                      <div className="flex items-center gap-3">
                        {doc.doc_type === 'pan_card' && <CreditCard className="h-5 w-5 text-blue-600" />}
                        {doc.doc_type === 'cml_copy' && <FileCheck className="h-5 w-5 text-green-600" />}
                        {doc.doc_type === 'cancelled_cheque' && <FileText className="h-5 w-5 text-orange-600" />}
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
                          onClick={() => handleDownloadDocument(selectedClientDocs.id, doc.filename)}
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
                <p className="text-center text-muted-foreground py-8">No documents uploaded for this client.</p>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Clients;
