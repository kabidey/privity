import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, Pencil, Trash2, PieChart, Upload, FileText, CreditCard, FileCheck, UserCog, Loader2, Sparkles, Check, Clock, CheckCircle, XCircle, Download, Eye, FolderOpen, Copy, AlertCircle, Ban, ShieldOff, AlertTriangle } from 'lucide-react';

const Clients = () => {
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [pendingClients, setPendingClients] = useState([]);
  const [documentsDialogOpen, setDocumentsDialogOpen] = useState(false);
  const [selectedClientDocs, setSelectedClientDocs] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [cloning, setCloning] = useState(false);
  const [docDialogOpen, setDocDialogOpen] = useState(false);
  const [mappingDialogOpen, setMappingDialogOpen] = useState(false);
  const [ocrDialogOpen, setOcrDialogOpen] = useState(false);
  const [suspendDialogOpen, setSuspendDialogOpen] = useState(false);
  const [suspensionReasonDialogOpen, setSuspensionReasonDialogOpen] = useState(false);
  const [selectedSuspendClient, setSelectedSuspendClient] = useState(null);
  const [suspensionReason, setSuspensionReason] = useState('');
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
    email: '',  // Primary email (from CML)
    email_secondary: '',  // Secondary email (PE Desk can add)
    email_tertiary: '',  // Third email (PE Desk can add)
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
  
  // Wizard step state
  const [wizardStep, setWizardStep] = useState(1); // 1: Documents, 2: Review/Edit, 3: Bank & Submit
  const [ocrCompleted, setOcrCompleted] = useState({ pan_card: false, cml_copy: false, cancelled_cheque: false });
  const [fieldsFromOcr, setFieldsFromOcr] = useState({}); // Track which fields came from OCR
  const [extractedNames, setExtractedNames] = useState({ pan_card: '', cml_copy: '', cancelled_cheque: '' }); // Track names from each document
  
  // Name mismatch and proprietor workflow states
  const [nameMismatchDetected, setNameMismatchDetected] = useState(false);
  const [isProprietor, setIsProprietor] = useState(null); // null = not asked, true/false = answered
  const [proprietorDialogOpen, setProprietorDialogOpen] = useState(false);
  
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
    bank_declaration: null,  // Required if proprietor with name mismatch
  });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPEDesk = currentUser.role === 1;
  const isPELevel = currentUser.role === 1 || currentUser.role === 2;
  const isAdmin = currentUser.role <= 2;
  const isManager = currentUser.role <= 3;
  const isEmployee = currentUser.role === 5;

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

  // Calculate similarity between two strings (Levenshtein-based percentage)
  const calculateNameSimilarity = (name1, name2) => {
    if (!name1 || !name2) return 0;
    
    // Normalize names: lowercase, remove extra spaces, remove special chars
    const normalize = (str) => str.toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ').trim();
    const s1 = normalize(name1);
    const s2 = normalize(name2);
    
    if (s1 === s2) return 100;
    if (!s1 || !s2) return 0;
    
    // Levenshtein distance calculation
    const len1 = s1.length;
    const len2 = s2.length;
    const matrix = Array(len1 + 1).fill(null).map(() => Array(len2 + 1).fill(0));
    
    for (let i = 0; i <= len1; i++) matrix[i][0] = i;
    for (let j = 0; j <= len2; j++) matrix[0][j] = j;
    
    for (let i = 1; i <= len1; i++) {
      for (let j = 1; j <= len2; j++) {
        const cost = s1[i - 1] === s2[j - 1] ? 0 : 1;
        matrix[i][j] = Math.min(
          matrix[i - 1][j] + 1,      // deletion
          matrix[i][j - 1] + 1,      // insertion
          matrix[i - 1][j - 1] + cost // substitution
        );
      }
    }
    
    const distance = matrix[len1][len2];
    const maxLen = Math.max(len1, len2);
    return Math.round(((maxLen - distance) / maxLen) * 100);
  };

  // Validate name matching across documents
  const validateNameMatching = () => {
    const names = Object.entries(extractedNames).filter(([_, name]) => name && name.trim());
    
    if (names.length < 2) {
      // Less than 2 documents have names - can't compare
      return { valid: true, message: '' };
    }
    
    const comparisons = [];
    for (let i = 0; i < names.length; i++) {
      for (let j = i + 1; j < names.length; j++) {
        const [doc1, name1] = names[i];
        const [doc2, name2] = names[j];
        const similarity = calculateNameSimilarity(name1, name2);
        comparisons.push({
          doc1: doc1.replace('_', ' ').toUpperCase(),
          doc2: doc2.replace('_', ' ').toUpperCase(),
          name1,
          name2,
          similarity
        });
      }
    }
    
    // Check if any comparison is below 30% threshold
    const NAME_MATCH_THRESHOLD = 30;
    const failedComparisons = comparisons.filter(c => c.similarity < NAME_MATCH_THRESHOLD);
    
    if (failedComparisons.length > 0) {
      const failed = failedComparisons[0];
      return {
        valid: false,
        message: `Name mismatch detected! "${failed.name1}" (${failed.doc1}) vs "${failed.name2}" (${failed.doc2}) - Only ${failed.similarity}% match. Names must match at least ${NAME_MATCH_THRESHOLD}%.`
      };
    }
    
    return { valid: true, message: '' };
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
          const newOcrFields = {};
          if (extracted.name) newOcrFields.name = true;
          if (extracted.pan_number) newOcrFields.pan_number = true;
          
          // Store extracted name for comparison
          if (extracted.name) {
            setExtractedNames(prev => ({ ...prev, pan_card: extracted.name }));
          }
          
          setFieldsFromOcr(prev => ({ ...prev, ...newOcrFields }));
          setFormData(prev => ({
            ...prev,
            name: extracted.name || prev.name,
            pan_number: extracted.pan_number || prev.pan_number,
          }));
          setOcrCompleted(prev => ({ ...prev, pan_card: true }));
          if (extracted.name || extracted.pan_number) {
            toast.success('PAN card data auto-filled!');
          }
        } else if (docType === 'cancelled_cheque') {
          // Store account holder name for comparison
          if (extracted.account_holder_name) {
            setExtractedNames(prev => ({ ...prev, cancelled_cheque: extracted.account_holder_name }));
          }
          
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
          setOcrCompleted(prev => ({ ...prev, cancelled_cheque: true }));
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
              cleanMobile = cleanMobile.replace(/[\s\-\(\)]/g, '');
              cleanMobile = cleanMobile.replace(/^\+?91/, '');
              cleanMobile = cleanMobile.replace(/^0/, '');
              if (cleanMobile.length > 10) {
                cleanMobile = cleanMobile.slice(-10);
              }
            }
            
            // Store extracted name for comparison
            if (extracted.client_name) {
              setExtractedNames(prev => ({ ...prev, cml_copy: extracted.client_name }));
            }
            
            // Track which fields came from OCR
            const newOcrFields = {};
            if (fullDpId) newOcrFields.dp_id = true;
            if (extracted.client_name) newOcrFields.name = true;
            if (extracted.pan_number) newOcrFields.pan_number = true;
            if (extracted.email) newOcrFields.email = true;
            if (cleanMobile) newOcrFields.mobile = true;
            if (extracted.address) newOcrFields.address = true;
            if (extracted.pin_code) newOcrFields.pin_code = true;
            
            setFieldsFromOcr(prev => ({ ...prev, ...newOcrFields }));
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
            
            setOcrCompleted(prev => ({ ...prev, cml_copy: true }));
            toast.success('CML data auto-filled!');
          } else if (extracted.raw_text) {
            setOcrCompleted(prev => ({ ...prev, cml_copy: true }));
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

  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    
    // Prevent double submission
    if (isSubmitting) return;
    setIsSubmitting(true);
    
    // Validate required fields
    if (!formData.name || !formData.name.trim()) {
      toast.error('Client name is required');
      setIsSubmitting(false);
      return;
    }
    if (!formData.pan_number || !formData.pan_number.trim()) {
      toast.error('PAN number is required');
      setIsSubmitting(false);
      return;
    }
    if (!formData.dp_id || !formData.dp_id.trim()) {
      toast.error('DP ID is required');
      setIsSubmitting(false);
      return;
    }
    // Validate Trading UCC if DP is with SMIFS
    if (formData.dp_type === 'smifs' && !formData.trading_ucc?.trim()) {
      toast.error('Trading UCC is required when DP is with SMIFS');
      setIsSubmitting(false);
      return;
    }
    
    // Check for duplicate client (by PAN number or DP ID) - only for new clients
    if (!editingClient) {
      const duplicateClient = clients.find(c => 
        c.pan_number?.toUpperCase() === formData.pan_number?.toUpperCase() ||
        c.dp_id === formData.dp_id
      );
      
      if (duplicateClient) {
        const duplicateField = duplicateClient.pan_number?.toUpperCase() === formData.pan_number?.toUpperCase() 
          ? 'PAN number' 
          : 'DP ID';
        toast.error(`Client with this ${duplicateField} already exists: ${duplicateClient.name} (${duplicateClient.otc_ucc})`);
        setIsSubmitting(false);
        return;
      }
    }
    
    // Validate name matching across documents (only for new clients with OCR)
    if (!editingClient) {
      const nameValidation = validateNameMatching();
      if (!nameValidation.valid) {
        toast.error(nameValidation.message);
        setIsSubmitting(false);
        return;
      }
    }
    
    // Validate mandatory documents for new clients
    if (!editingClient) {
      const missingDocs = [];
      if (!docFiles.pan_card) missingDocs.push('PAN Card');
      if (!docFiles.cml_copy) missingDocs.push('CML Copy');
      if (!docFiles.cancelled_cheque) missingDocs.push('Cancelled Cheque');
      
      if (missingDocs.length > 0) {
        toast.error(`Please upload: ${missingDocs.join(', ')}`);
        setIsSubmitting(false);
        return;
      }
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
    } finally {
      setIsSubmitting(false);
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
    if (!isPELevel) {
      toast.error('Only PE Desk or PE Manager can modify clients');
      return;
    }
    setEditingClient(client);
    setFormData({
      name: client.name,
      email: client.email || '',
      email_secondary: client.email_secondary || '',
      email_tertiary: client.email_tertiary || '',
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
    setWizardStep(2); // Skip document upload step when editing
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

  const handleSuspendClient = async () => {
    if (!selectedSuspendClient || !suspensionReason.trim()) {
      toast.error('Please provide a suspension reason');
      return;
    }
    try {
      await api.put(`/clients/${selectedSuspendClient.id}/suspend`, { reason: suspensionReason });
      toast.success(`Client ${selectedSuspendClient.name} has been suspended`);
      setSuspendDialogOpen(false);
      setSelectedSuspendClient(null);
      setSuspensionReason('');
      fetchClients();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to suspend client');
    }
  };

  const handleUnsuspendClient = async (client) => {
    if (!window.confirm(`Are you sure you want to unsuspend "${client.name}"?`)) return;
    try {
      await api.put(`/clients/${client.id}/unsuspend`);
      toast.success(`Client ${client.name} has been unsuspended`);
      fetchClients();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to unsuspend client');
    }
  };

  const openSuspendDialog = (client) => {
    setSelectedSuspendClient(client);
    setSuspensionReason('');
    setSuspendDialogOpen(true);
  };

  const viewSuspensionReason = (client) => {
    setSelectedSuspendClient(client);
    setSuspensionReasonDialogOpen(true);
  };

  const handleCloneToVendor = async (client) => {
    if (!isPELevel) {
      toast.error('Only PE Desk or PE Manager can clone clients');
      return;
    }
    if (!window.confirm(`Clone client "${client.name}" as a Vendor?\n\nThis will create a new vendor entry with the same details.`)) return;
    setCloning(true);
    try {
      const response = await api.post(`/clients/${client.id}/clone?target_type=vendor`);
      toast.success(response.data.message);
      if (window.confirm('Clone successful! Do you want to view the new vendor?')) {
        navigate('/vendors');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clone client as vendor');
    } finally {
      setCloning(false);
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
      name: '', email: '', email_secondary: '', email_tertiary: '',
      phone: '', mobile: '', pan_number: '', dp_id: '',
      dp_type: 'outside', trading_ucc: '',
      address: '', pin_code: '', bank_accounts: [],
    });
    setDocFiles({ pan_card: null, cml_copy: null, cancelled_cheque: null });
    setOcrResults({});
    setOcrCompleted({ pan_card: false, cml_copy: false, cancelled_cheque: false });
    setFieldsFromOcr({});
    setExtractedNames({ pan_card: '', cml_copy: '', cancelled_cheque: '' });
    setWizardStep(1);
    setEditingClient(null);
    setIsSubmitting(false);
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
    // Check suspension first
    if (client.is_suspended) {
      return (
        <div className="flex flex-col gap-1">
          <Badge variant="outline" className="text-red-600 border-red-600 bg-red-50">
            <Ban className="h-3 w-3 mr-1" />Suspended
          </Badge>
          {/* Show reason button for employees */}
          {!isPEDesk && client.suspension_reason && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-6 px-1 text-xs text-red-600"
              onClick={() => viewSuspensionReason(client)}
            >
              <Eye className="h-3 w-3 mr-1" />View Reason
            </Button>
          )}
        </div>
      );
    }
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

  const renderDocumentUploadCard = (docType, label, IconComponent, color, description) => (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <IconComponent className={`h-5 w-5 ${color}`} />
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
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="clients-page">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 md:mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold mb-2">Clients</h1>
          <p className="text-muted-foreground text-sm md:text-base">
            {isEmployee ? 'Manage your clients' : 'Manage clients with documents and employee mapping'}
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
          <DialogTrigger asChild>
            <Button className="rounded-sm w-full sm:w-auto" data-testid="add-client-button">
              <Plus className="mr-2 h-4 w-4" strokeWidth={1.5} />
              Add Client
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto sm:max-w-[95vw] md:max-w-4xl" aria-describedby="client-dialog-desc">
            <DialogHeader>
              <DialogTitle>{editingClient ? 'Edit Client' : 'Add New Client'}</DialogTitle>
              {!editingClient && (
                <div className="flex items-center gap-2 mt-2">
                  <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${wizardStep >= 1 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>1</div>
                  <div className={`flex-1 h-1 ${wizardStep >= 2 ? 'bg-primary' : 'bg-muted'}`}></div>
                  <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${wizardStep >= 2 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>2</div>
                  <div className={`flex-1 h-1 ${wizardStep >= 3 ? 'bg-primary' : 'bg-muted'}`}></div>
                  <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${wizardStep >= 3 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>3</div>
                </div>
              )}
              {!editingClient && (
                <p className="text-sm text-muted-foreground mt-1">
                  {wizardStep === 1 && 'Step 1: Upload Documents for OCR'}
                  {wizardStep === 2 && 'Step 2: Review & Edit Details'}
                  {wizardStep === 3 && 'Step 3: Bank Accounts & Submit'}
                </p>
              )}
            </DialogHeader>
            <p id="client-dialog-desc" className="sr-only">Form to add or edit client details</p>
            
            {/* Wizard Step 1: Document Upload - Only for new clients */}
            {!editingClient && wizardStep === 1 && (
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    <strong>Upload all 3 documents to auto-fill client details via OCR.</strong> All documents are mandatory. CML is required to extract email.
                  </p>
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {/* CML Copy Upload */}
                  <Card className={`border-2 ${ocrCompleted.cml_copy ? 'border-green-500' : docFiles.cml_copy ? 'border-blue-500' : 'border-dashed'}`}>
                    <CardHeader className="pb-2 px-3">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <FileCheck className="h-4 w-4 flex-shrink-0" />
                        CML Copy *
                        {ocrCompleted.cml_copy && <Check className="h-4 w-4 text-green-500 flex-shrink-0" />}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3">
                      <div className="space-y-2">
                        <label className="flex items-center justify-center w-full px-3 py-2 text-xs font-medium text-center border rounded-md cursor-pointer bg-secondary hover:bg-secondary/80 transition-colors">
                          <Upload className="h-4 w-4 mr-2 flex-shrink-0" />
                          <span className="truncate">{docFiles.cml_copy ? docFiles.cml_copy.name : 'Choose File'}</span>
                          <Input
                            type="file"
                            accept="image/*,.pdf"
                            onChange={(e) => handleFileChange('cml_copy', e.target.files?.[0])}
                            disabled={processingOcr.cml_copy}
                            className="hidden"
                          />
                        </label>
                        {processingOcr.cml_copy && (
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Processing OCR...
                          </div>
                        )}
                        {ocrResults.cml_copy && (
                          <p className="text-xs text-green-600">
                            ✓ Extracted: {ocrResults.cml_copy.extracted_data?.client_name ? 'Name, ' : ''}{ocrResults.cml_copy.extracted_data?.email ? 'Email, ' : ''}{ocrResults.cml_copy.extracted_data?.dp_id ? 'DP ID' : ''}
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* PAN Card Upload */}
                  <Card className={`border-2 ${ocrCompleted.pan_card ? 'border-green-500' : docFiles.pan_card ? 'border-blue-500' : 'border-dashed'}`}>
                    <CardHeader className="pb-2 px-3">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <CreditCard className="h-4 w-4 flex-shrink-0" />
                        PAN Card *
                        {ocrCompleted.pan_card && <Check className="h-4 w-4 text-green-500 flex-shrink-0" />}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3">
                      <div className="space-y-2">
                        <label className="flex items-center justify-center w-full px-3 py-2 text-xs font-medium text-center border rounded-md cursor-pointer bg-secondary hover:bg-secondary/80 transition-colors">
                          <Upload className="h-4 w-4 mr-2 flex-shrink-0" />
                          <span className="truncate">{docFiles.pan_card ? docFiles.pan_card.name : 'Choose File'}</span>
                          <Input
                            type="file"
                            accept="image/*,.pdf"
                            onChange={(e) => handleFileChange('pan_card', e.target.files?.[0])}
                            disabled={processingOcr.pan_card}
                            className="hidden"
                          />
                        </label>
                        {processingOcr.pan_card && (
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Processing OCR...
                          </div>
                        )}
                        {ocrResults.pan_card && (
                          <p className="text-xs text-green-600">
                            ✓ Extracted: {ocrResults.pan_card.extracted_data?.name ? 'Name, ' : ''}{ocrResults.pan_card.extracted_data?.pan_number ? 'PAN' : ''}
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Cancelled Cheque Upload */}
                  <Card className={`border-2 ${ocrCompleted.cancelled_cheque ? 'border-green-500' : docFiles.cancelled_cheque ? 'border-blue-500' : 'border-dashed'}`}>
                    <CardHeader className="pb-2 px-3">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <FileText className="h-4 w-4 flex-shrink-0" />
                        Cancelled Cheque *
                        {ocrCompleted.cancelled_cheque && <Check className="h-4 w-4 text-green-500 flex-shrink-0" />}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3">
                      <div className="space-y-2">
                        <label className="flex items-center justify-center w-full px-3 py-2 text-xs font-medium text-center border rounded-md cursor-pointer bg-secondary hover:bg-secondary/80 transition-colors">
                          <Upload className="h-4 w-4 mr-2 flex-shrink-0" />
                          <span className="truncate">{docFiles.cancelled_cheque ? docFiles.cancelled_cheque.name : 'Choose File'}</span>
                          <Input
                            type="file"
                            accept="image/*,.pdf"
                            onChange={(e) => handleFileChange('cancelled_cheque', e.target.files?.[0])}
                            disabled={processingOcr.cancelled_cheque}
                            className="hidden"
                          />
                        </label>
                        {processingOcr.cancelled_cheque && (
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Processing OCR...
                          </div>
                        )}
                        {ocrResults.cancelled_cheque && (
                          <p className="text-xs text-green-600">
                            ✓ Bank account extracted
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Name Matching Status */}
                {Object.values(extractedNames).filter(n => n).length >= 2 && (
                  <div className={`p-3 rounded-lg border ${validateNameMatching().valid ? 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800' : 'bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800'}`}>
                    <div className="flex items-center gap-2">
                      {validateNameMatching().valid ? (
                        <>
                          <Check className="h-4 w-4 text-green-600" />
                          <span className="text-sm text-green-800 dark:text-green-200 font-medium">Name matching verified across documents</span>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="h-4 w-4 text-red-600" />
                          <span className="text-sm text-red-800 dark:text-red-200 font-medium">Name mismatch detected</span>
                        </>
                      )}
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {extractedNames.pan_card && <span className="block">PAN Card: {extractedNames.pan_card}</span>}
                      {extractedNames.cml_copy && <span className="block">CML: {extractedNames.cml_copy}</span>}
                      {extractedNames.cancelled_cheque && <span className="block">Cheque: {extractedNames.cancelled_cheque}</span>}
                    </div>
                  </div>
                )}

                <div className="flex justify-between pt-4">
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                  <div className="flex gap-2">
                    <Button 
                      type="button"
                      onClick={() => {
                        // Validate all documents are uploaded
                        const missingDocs = [];
                        if (!docFiles.cml_copy) missingDocs.push('CML Copy');
                        if (!docFiles.pan_card) missingDocs.push('PAN Card');
                        if (!docFiles.cancelled_cheque) missingDocs.push('Cancelled Cheque');
                        
                        if (missingDocs.length > 0) {
                          toast.error(`Please upload: ${missingDocs.join(', ')}`);
                          return;
                        }
                        setWizardStep(2);
                      }}
                      disabled={Object.values(processingOcr).some(p => p) || !docFiles.cml_copy || !docFiles.pan_card || !docFiles.cancelled_cheque}
                    >
                      Next: Review Details
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Wizard Step 2 & 3 or Edit Mode - Use Tabs */}
            {(editingClient || wizardStep >= 2) && (
            <Tabs defaultValue="details" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="details">Client Details</TabsTrigger>
                <TabsTrigger value="bank">Bank Accounts</TabsTrigger>
                <TabsTrigger value="documents" disabled={!editingClient}>Documents</TabsTrigger>
              </TabsList>
              
              <TabsContent value="details">
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* OCR Fields Notice for Employees */}
                  {isEmployee && Object.keys(fieldsFromOcr).length > 0 && (
                    <div className="p-3 bg-amber-50 dark:bg-amber-950 rounded-lg border border-amber-200 dark:border-amber-800">
                      <p className="text-sm text-amber-800 dark:text-amber-200">
                        <strong>Note:</strong> Fields marked with 🔒 were extracted from documents and cannot be edited by employees.
                      </p>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Name * {isEmployee && fieldsFromOcr.name && '🔒'}</Label>
                      <Input 
                        data-testid="client-name-input" 
                        value={formData.name} 
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })} 
                        required 
                        disabled={isEmployee && fieldsFromOcr.name}
                        className={isEmployee && fieldsFromOcr.name ? 'bg-muted' : ''}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Primary Email (from CML) {isEmployee && fieldsFromOcr.email && '🔒'}</Label>
                      <Input 
                        type="email" 
                        data-testid="client-email-input" 
                        value={formData.email} 
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })} 
                        disabled={isEmployee && fieldsFromOcr.email}
                        className={isEmployee && fieldsFromOcr.email ? 'bg-muted' : ''}
                        placeholder="Primary email from CML"
                      />
                    </div>
                    
                    {/* Secondary and Tertiary emails - PE Desk only */}
                    {!isEmployee && (
                      <>
                        <div className="space-y-2">
                          <Label>Secondary Email</Label>
                          <Input 
                            type="email" 
                            data-testid="client-email-secondary-input" 
                            value={formData.email_secondary} 
                            onChange={(e) => setFormData({ ...formData, email_secondary: e.target.value })} 
                            placeholder="Additional email (PE Desk only)"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Tertiary Email</Label>
                          <Input 
                            type="email" 
                            data-testid="client-email-tertiary-input" 
                            value={formData.email_tertiary} 
                            onChange={(e) => setFormData({ ...formData, email_tertiary: e.target.value })} 
                            placeholder="Third email (PE Desk only)"
                          />
                        </div>
                      </>
                    )}
                    
                    <div className="space-y-2">
                      <Label>Phone</Label>
                      <Input data-testid="client-phone-input" value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} />
                    </div>
                    <div className="space-y-2">
                      <Label>Mobile {isEmployee && fieldsFromOcr.mobile && '🔒'}</Label>
                      <Input 
                        data-testid="client-mobile-input" 
                        value={formData.mobile} 
                        onChange={(e) => setFormData({ ...formData, mobile: e.target.value })} 
                        disabled={isEmployee && fieldsFromOcr.mobile}
                        className={isEmployee && fieldsFromOcr.mobile ? 'bg-muted' : ''}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>PAN Number * {isEmployee && fieldsFromOcr.pan_number && '🔒'}</Label>
                      <Input 
                        data-testid="client-pan-input" 
                        value={formData.pan_number} 
                        onChange={(e) => setFormData({ ...formData, pan_number: e.target.value.toUpperCase() })} 
                        required 
                        disabled={isEmployee && fieldsFromOcr.pan_number}
                        className={isEmployee && fieldsFromOcr.pan_number ? 'bg-muted' : ''}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>DP ID * {isEmployee && fieldsFromOcr.dp_id && '🔒'}</Label>
                      <Input 
                        data-testid="client-dpid-input" 
                        value={formData.dp_id} 
                        onChange={(e) => setFormData({ ...formData, dp_id: e.target.value })} 
                        required 
                        disabled={isEmployee && fieldsFromOcr.dp_id}
                        className={isEmployee && fieldsFromOcr.dp_id ? 'bg-muted' : ''}
                      />
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
                    <Button type="submit" className="rounded-sm" data-testid="save-client-button" disabled={isSubmitting || uploading}>
                      {(isSubmitting || uploading) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {isSubmitting ? 'Creating...' : (editingClient ? 'Update' : 'Create')}
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
                  {!editingClient && (
                    <div className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                      <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-amber-800 dark:text-amber-200">All documents are mandatory</p>
                        <p className="text-xs text-amber-700 dark:text-amber-300">Please upload PAN Card, CML Copy, and Cancelled Cheque to create a client.</p>
                      </div>
                    </div>
                  )}
                  
                  <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
                    <Sparkles className="h-5 w-5 text-blue-600" />
                    <p className="text-sm text-blue-800 dark:text-blue-200">
                      <strong>AI Auto-fill:</strong> Upload documents and OCR will extract and fill form fields. Different bank accounts are automatically added.
                    </p>
                  </div>
                  
                  <div className="grid grid-cols-1 gap-4">
                    {renderDocumentUploadCard('pan_card', `PAN Card${!editingClient ? ' *' : ''}`, CreditCard, 'text-blue-600', 'Extracts: Name, PAN Number')}
                    {renderDocumentUploadCard('cml_copy', `CML Copy${!editingClient ? ' *' : ''}`, FileCheck, 'text-purple-600', 'Extracts: DP ID, Name, PAN, Email, Mobile, Address, Bank Details')}
                    {renderDocumentUploadCard('cancelled_cheque', `Cancelled Cheque${!editingClient ? ' *' : ''}`, FileText, 'text-orange-600', 'Extracts: Bank Name, Account Number, IFSC Code (adds as separate bank account)')}
                  </div>
                  
                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleSubmit} disabled={isSubmitting || uploading || Object.values(processingOcr).some(v => v)}>
                      {isSubmitting || uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                      {isSubmitting ? 'Creating...' : (editingClient ? 'Update & Upload' : 'Create & Upload')}
                    </Button>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
            )}
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
            <div className="overflow-x-auto -mx-4 md:mx-0">
              <Table className="min-w-[900px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase">OTC UCC</TableHead>
                    <TableHead className="text-xs uppercase">Name</TableHead>
                    <TableHead className="text-xs uppercase">PAN</TableHead>
                    <TableHead className="text-xs uppercase hidden md:table-cell">DP Type</TableHead>
                    <TableHead className="text-xs uppercase hidden lg:table-cell">Mobile</TableHead>
                    <TableHead className="text-xs uppercase">Status</TableHead>
                    {!isEmployee && <TableHead className="text-xs uppercase hidden lg:table-cell">Mapped To</TableHead>}
                    <TableHead className="text-xs uppercase hidden md:table-cell">Banks</TableHead>
                    <TableHead className="text-xs uppercase hidden md:table-cell">Docs</TableHead>
                    <TableHead className="text-xs uppercase text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedClients.map((client) => (
                    <TableRow key={client.id} data-testid="client-row">
                      <TableCell className="font-mono text-xs md:text-sm font-bold text-primary">{client.otc_ucc || 'N/A'}</TableCell>
                      <TableCell className="font-medium text-sm">{client.name}</TableCell>
                      <TableCell className="mono text-xs md:text-sm">{client.pan_number}</TableCell>
                      <TableCell className="hidden md:table-cell">
                        <Badge variant={client.dp_type === 'smifs' ? 'default' : 'outline'} className="text-xs">
                          {client.dp_type === 'smifs' ? 'SMIFS' : 'Outside'}
                        </Badge>
                        {client.dp_type === 'smifs' && client.trading_ucc && (
                          <span className="text-xs text-muted-foreground ml-1">({client.trading_ucc})</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm hidden lg:table-cell">{client.mobile || client.phone || '-'}</TableCell>
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
                            {/* Suspend/Unsuspend button */}
                            {client.is_suspended ? (
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => handleUnsuspendClient(client)} 
                                title="Unsuspend Client"
                                className="text-green-600 hover:text-green-700"
                              >
                                <ShieldOff className="h-4 w-4" />
                              </Button>
                            ) : (
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => openSuspendDialog(client)} 
                                title="Suspend Client"
                                className="text-orange-600 hover:text-orange-700"
                              >
                                <Ban className="h-4 w-4" />
                              </Button>
                            )}
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              onClick={() => handleCloneToVendor(client)} 
                              title="Clone as Vendor"
                              disabled={cloning}
                              className="text-blue-600 hover:text-blue-700"
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
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

      {/* Suspend Client Dialog */}
      <Dialog open={suspendDialogOpen} onOpenChange={setSuspendDialogOpen}>
        <DialogContent className="max-w-md" data-testid="suspend-client-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-orange-600">
              <Ban className="h-5 w-5" />
              Suspend Client
            </DialogTitle>
            <DialogDescription>
              {selectedSuspendClient && `Suspend "${selectedSuspendClient.name}" from the system`}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="p-3 bg-orange-50 dark:bg-orange-950 rounded-lg border border-orange-200 dark:border-orange-800">
              <p className="text-sm text-orange-700 dark:text-orange-300">
                <strong>Warning:</strong> Suspended clients cannot be used for new bookings. Employees will see the suspension reason.
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="suspension-reason">Suspension Reason *</Label>
              <Textarea
                id="suspension-reason"
                placeholder="Enter reason for suspension..."
                value={suspensionReason}
                onChange={(e) => setSuspensionReason(e.target.value)}
                rows={3}
                data-testid="suspension-reason-input"
              />
            </div>
          </div>
          
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setSuspendDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSuspendClient}
              disabled={!suspensionReason.trim()}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="confirm-suspend-btn"
            >
              <Ban className="h-4 w-4 mr-2" />
              Suspend Client
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Suspension Reason Dialog (for Employees) */}
      <Dialog open={suspensionReasonDialogOpen} onOpenChange={setSuspensionReasonDialogOpen}>
        <DialogContent className="max-w-md" data-testid="suspension-reason-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Ban className="h-5 w-5" />
              Client Suspended
            </DialogTitle>
            <DialogDescription>
              {selectedSuspendClient && `"${selectedSuspendClient.name}" has been suspended`}
            </DialogDescription>
          </DialogHeader>
          
          {selectedSuspendClient && (
            <div className="space-y-4">
              <div className="p-4 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800">
                <Label className="text-sm font-medium text-red-700 dark:text-red-300">Suspension Reason:</Label>
                <p className="mt-2 text-red-800 dark:text-red-200">
                  {selectedSuspendClient.suspension_reason || 'No reason provided'}
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <Label className="text-muted-foreground">Suspended By</Label>
                  <p className="font-medium">{selectedSuspendClient.suspended_by_name || 'Unknown'}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Suspended At</Label>
                  <p className="font-medium">
                    {selectedSuspendClient.suspended_at 
                      ? new Date(selectedSuspendClient.suspended_at).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })
                      : 'Unknown'}
                  </p>
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter className="mt-4">
            <Button onClick={() => setSuspensionReasonDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Clients;
