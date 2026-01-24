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
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, Pencil, Trash2, PieChart, Upload, FileText, CreditCard, FileCheck, UserCog, Eye, Loader2 } from 'lucide-react';

const Clients = () => {
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
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
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    pan_number: '',
    dp_id: '',
    bank_name: '',
    account_number: '',
    ifsc_code: '',
  });
  const [docFiles, setDocFiles] = useState({
    pan_card: null,
    cml_copy: null,
    cancelled_cheque: null,
  });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isAdmin = currentUser.role <= 2;

  useEffect(() => {
    fetchClients();
    fetchEmployees();
  }, []);

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

  const fetchEmployees = async () => {
    try {
      const response = await api.get('/employees');
      setEmployees(response.data);
    } catch (error) {
      console.error('Failed to load employees');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      let clientId;
      if (editingClient) {
        await api.put(`/clients/${editingClient.id}`, formData);
        clientId = editingClient.id;
        toast.success('Client updated successfully');
      } else {
        const response = await api.post('/clients', formData);
        clientId = response.data.id;
        toast.success('Client created successfully');
      }
      
      // Upload documents if any
      const hasDocuments = Object.values(docFiles).some(f => f !== null);
      if (hasDocuments && clientId) {
        await uploadDocuments(clientId);
      }
      
      setDialogOpen(false);
      resetForm();
      fetchClients();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const uploadDocuments = async (clientId) => {
    setUploading(true);
    try {
      for (const [docType, file] of Object.entries(docFiles)) {
        if (file) {
          const formData = new FormData();
          formData.append('file', file);
          formData.append('doc_type', docType);
          
          await api.post(`/clients/${clientId}/documents`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
        }
      }
      toast.success('Documents uploaded and OCR processed');
    } catch (error) {
      toast.error('Failed to upload some documents');
    } finally {
      setUploading(false);
    }
  };

  const handleEdit = (client) => {
    setEditingClient(client);
    setFormData({
      name: client.name,
      email: client.email || '',
      phone: client.phone || '',
      pan_number: client.pan_number,
      dp_id: client.dp_id,
      bank_name: client.bank_name || '',
      account_number: client.account_number || '',
      ifsc_code: client.ifsc_code || '',
    });
    setDocFiles({ pan_card: null, cml_copy: null, cancelled_cheque: null });
    setDialogOpen(true);
  };

  const handleDelete = async (clientId) => {
    if (!window.confirm('Are you sure you want to delete this client?')) return;
    try {
      await api.delete(`/clients/${clientId}`);
      toast.success('Client deleted successfully');
      fetchClients();
    } catch (error) {
      toast.error('Failed to delete client');
    }
  };

  const handleUploadMore = (client) => {
    setSelectedClient(client);
    setDocFiles({ pan_card: null, cml_copy: null, cancelled_cheque: null });
    setDocDialogOpen(true);
  };

  const handleUploadSubmit = async () => {
    if (!selectedClient) return;
    await uploadDocuments(selectedClient.id);
    setDocDialogOpen(false);
    fetchClients();
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
      name: '',
      email: '',
      phone: '',
      pan_number: '',
      dp_id: '',
      bank_name: '',
      account_number: '',
      ifsc_code: '',
    });
    setDocFiles({ pan_card: null, cml_copy: null, cancelled_cheque: null });
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

  return (
    <div className="p-8 page-enter" data-testid="clients-page">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">Clients</h1>
          <p className="text-muted-foreground text-base">Manage clients with documents and employee mapping</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button className="rounded-sm" data-testid="add-client-button">
              <Plus className="mr-2 h-4 w-4" strokeWidth={1.5} />
              Add Client
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" aria-describedby="client-dialog-desc">
            <DialogHeader>
              <DialogTitle>{editingClient ? 'Edit Client' : 'Add New Client'}</DialogTitle>
            </DialogHeader>
            <p id="client-dialog-desc" className="sr-only">Form to add or edit client details</p>
            
            <Tabs defaultValue="details" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="details">Client Details</TabsTrigger>
                <TabsTrigger value="documents">Documents & OCR</TabsTrigger>
              </TabsList>
              
              <TabsContent value="details">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">Name *</Label>
                      <Input
                        id="name"
                        data-testid="client-name-input"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email">Email</Label>
                      <Input
                        id="email"
                        data-testid="client-email-input"
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="phone">Phone</Label>
                      <Input
                        id="phone"
                        data-testid="client-phone-input"
                        value={formData.phone}
                        onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="pan_number">PAN Number *</Label>
                      <Input
                        id="pan_number"
                        data-testid="client-pan-input"
                        value={formData.pan_number}
                        onChange={(e) => setFormData({ ...formData, pan_number: e.target.value.toUpperCase() })}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="dp_id">DP ID *</Label>
                      <Input
                        id="dp_id"
                        data-testid="client-dpid-input"
                        value={formData.dp_id}
                        onChange={(e) => setFormData({ ...formData, dp_id: e.target.value })}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="bank_name">Bank Name</Label>
                      <Input
                        id="bank_name"
                        data-testid="client-bank-input"
                        value={formData.bank_name}
                        onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="account_number">Account Number</Label>
                      <Input
                        id="account_number"
                        data-testid="client-account-input"
                        value={formData.account_number}
                        onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="ifsc_code">IFSC Code</Label>
                      <Input
                        id="ifsc_code"
                        data-testid="client-ifsc-input"
                        value={formData.ifsc_code}
                        onChange={(e) => setFormData({ ...formData, ifsc_code: e.target.value.toUpperCase() })}
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" className="rounded-sm" data-testid="save-client-button" disabled={uploading}>
                      {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      {editingClient ? 'Update' : 'Create'}
                    </Button>
                  </div>
                </form>
              </TabsContent>
              
              <TabsContent value="documents">
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    Upload JPG or PDF documents. OCR will automatically extract information.
                  </p>
                  
                  <div className="grid grid-cols-1 gap-4">
                    <div className="border rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <CreditCard className="h-5 w-5 text-blue-600" />
                        <Label className="font-semibold">PAN Card</Label>
                      </div>
                      <Input
                        type="file"
                        accept=".jpg,.jpeg,.pdf,.png"
                        data-testid="pan-card-upload"
                        onChange={(e) => setDocFiles({ ...docFiles, pan_card: e.target.files[0] })}
                      />
                      {docFiles.pan_card && (
                        <p className="text-xs text-green-600 mt-1">Selected: {docFiles.pan_card.name}</p>
                      )}
                    </div>
                    
                    <div className="border rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <FileCheck className="h-5 w-5 text-purple-600" />
                        <Label className="font-semibold">CML Copy</Label>
                      </div>
                      <Input
                        type="file"
                        accept=".jpg,.jpeg,.pdf,.png"
                        data-testid="cml-copy-upload"
                        onChange={(e) => setDocFiles({ ...docFiles, cml_copy: e.target.files[0] })}
                      />
                      {docFiles.cml_copy && (
                        <p className="text-xs text-green-600 mt-1">Selected: {docFiles.cml_copy.name}</p>
                      )}
                    </div>
                    
                    <div className="border rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-5 w-5 text-orange-600" />
                        <Label className="font-semibold">Cancelled Cheque</Label>
                      </div>
                      <Input
                        type="file"
                        accept=".jpg,.jpeg,.pdf,.png"
                        data-testid="cheque-upload"
                        onChange={(e) => setDocFiles({ ...docFiles, cancelled_cheque: e.target.files[0] })}
                      />
                      {docFiles.cancelled_cheque && (
                        <p className="text-xs text-green-600 mt-1">Selected: {docFiles.cancelled_cheque.name}</p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleSubmit} className="rounded-sm" disabled={uploading}>
                      {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      {editingClient ? 'Update & Upload' : 'Create & Upload'}
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
          <CardTitle>All Clients</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div>Loading...</div>
          ) : clients.length === 0 ? (
            <div className="text-center py-12" data-testid="no-clients-message">
              <p className="text-muted-foreground">No clients found.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">OTC UCC</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Name</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">PAN</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">DP ID</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Mapped To</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Documents</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clients.map((client) => (
                    <TableRow key={client.id} className="table-row" data-testid="client-row">
                      <TableCell className="font-mono text-sm font-bold text-primary">
                        {client.otc_ucc || 'N/A'}
                      </TableCell>
                      <TableCell className="font-medium">{client.name}</TableCell>
                      <TableCell className="mono text-sm">{client.pan_number}</TableCell>
                      <TableCell className="mono text-sm">{client.dp_id}</TableCell>
                      <TableCell>
                        {client.mapped_employee_name ? (
                          <Badge variant="secondary">{client.mapped_employee_name}</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">Not mapped</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          {client.documents?.map((doc, idx) => (
                            <button
                              key={idx}
                              onClick={() => viewOcrData(client, doc)}
                              className="p-1 hover:bg-muted rounded"
                              title={`${doc.doc_type} - Click to view OCR`}
                            >
                              {getDocIcon(doc.doc_type)}
                            </button>
                          ))}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleUploadMore(client)}
                            data-testid="upload-doc-button"
                            title="Upload documents"
                          >
                            <Upload className="h-4 w-4" strokeWidth={1.5} />
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/clients/${client.id}/portfolio`)}
                          data-testid="view-portfolio-button"
                          title="View Portfolio"
                        >
                          <PieChart className="h-4 w-4" strokeWidth={1.5} />
                        </Button>
                        {isAdmin && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleMapping(client)}
                            data-testid="map-employee-button"
                            title="Map to Employee"
                          >
                            <UserCog className="h-4 w-4" strokeWidth={1.5} />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(client)}
                          data-testid="edit-client-button"
                        >
                          <Pencil className="h-4 w-4" strokeWidth={1.5} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(client.id)}
                          data-testid="delete-client-button"
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

      {/* Document Upload Dialog */}
      <Dialog open={docDialogOpen} onOpenChange={setDocDialogOpen}>
        <DialogContent aria-describedby="doc-upload-desc">
          <DialogHeader>
            <DialogTitle>Upload Documents for {selectedClient?.name}</DialogTitle>
          </DialogHeader>
          <p id="doc-upload-desc" className="sr-only">Upload documents for client</p>
          <div className="space-y-4">
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <CreditCard className="h-5 w-5 text-blue-600" />
                <Label className="font-semibold">PAN Card</Label>
              </div>
              <Input
                type="file"
                accept=".jpg,.jpeg,.pdf,.png"
                onChange={(e) => setDocFiles({ ...docFiles, pan_card: e.target.files[0] })}
              />
            </div>
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <FileCheck className="h-5 w-5 text-purple-600" />
                <Label className="font-semibold">CML Copy</Label>
              </div>
              <Input
                type="file"
                accept=".jpg,.jpeg,.pdf,.png"
                onChange={(e) => setDocFiles({ ...docFiles, cml_copy: e.target.files[0] })}
              />
            </div>
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="h-5 w-5 text-orange-600" />
                <Label className="font-semibold">Cancelled Cheque</Label>
              </div>
              <Input
                type="file"
                accept=".jpg,.jpeg,.pdf,.png"
                onChange={(e) => setDocFiles({ ...docFiles, cancelled_cheque: e.target.files[0] })}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDocDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleUploadSubmit} disabled={uploading}>
                {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                Upload & Process OCR
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Employee Mapping Dialog */}
      <Dialog open={mappingDialogOpen} onOpenChange={setMappingDialogOpen}>
        <DialogContent aria-describedby="mapping-desc">
          <DialogHeader>
            <DialogTitle>Map Client to Employee</DialogTitle>
          </DialogHeader>
          <p id="mapping-desc" className="sr-only">Map or unmap client to employee</p>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Client: <span className="font-semibold">{selectedClient?.name}</span>
              {selectedClient?.mapped_employee_name && (
                <span className="ml-2">(Currently mapped to: {selectedClient.mapped_employee_name})</span>
              )}
            </p>
            <div className="space-y-2">
              <Label>Select Employee</Label>
              <Select onValueChange={(value) => handleMappingSubmit(value === 'unmap' ? null : value)}>
                <SelectTrigger data-testid="employee-select">
                  <SelectValue placeholder="Select an employee" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="unmap">-- Unmap (Remove Assignment) --</SelectItem>
                  {employees.map((emp) => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.name} ({emp.role_name})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* OCR Data Dialog */}
      <Dialog open={ocrDialogOpen} onOpenChange={setOcrDialogOpen}>
        <DialogContent className="max-w-2xl" aria-describedby="ocr-desc">
          <DialogHeader>
            <DialogTitle>OCR Extracted Data</DialogTitle>
          </DialogHeader>
          <p id="ocr-desc" className="sr-only">View OCR extracted data from document</p>
          {selectedOcrData && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                {getDocIcon(selectedOcrData.doc?.doc_type)}
                <span className="font-semibold capitalize">
                  {selectedOcrData.doc?.doc_type?.replace('_', ' ')}
                </span>
                <Badge variant="outline" className="ml-auto">
                  {selectedOcrData.doc?.ocr_data?.status || 'Unknown'}
                </Badge>
              </div>
              
              <div className="border rounded-lg p-4 bg-muted/30">
                <h4 className="font-semibold mb-3">Extracted Information</h4>
                {selectedOcrData.doc?.ocr_data?.extracted_data ? (
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(selectedOcrData.doc.ocr_data.extracted_data).map(([key, value]) => (
                      <div key={key} className="space-y-1">
                        <Label className="text-xs text-muted-foreground capitalize">
                          {key.replace(/_/g, ' ')}
                        </Label>
                        <p className="font-mono text-sm">{value || 'N/A'}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground">No OCR data available</p>
                )}
              </div>
              
              <p className="text-xs text-muted-foreground">
                Processed: {selectedOcrData.doc?.ocr_data?.processed_at 
                  ? new Date(selectedOcrData.doc.ocr_data.processed_at).toLocaleString() 
                  : 'N/A'}
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Clients;
