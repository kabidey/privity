import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { 
  FileText, 
  Search, 
  Filter, 
  Eye, 
  Download, 
  Mail, 
  RefreshCw,
  CheckCircle,
  Clock,
  FileCheck
} from 'lucide-react';

const ContractNotes = () => {
  const navigate = useNavigate();
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [selectedNote, setSelectedNote] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [regenerating, setRegenerating] = useState(null);
  
  // Filters
  const [filters, setFilters] = useState({
    status: '',
    start_date: '',
    end_date: ''
  });
  const [pagination, setPagination] = useState({ limit: 50, skip: 0 });

  const { user, isPELevel, isPEDesk } = useCurrentUser();

  useEffect(() => {
    // Wait for user to load before checking permissions
    if (user === null) return;
    
    if (!isPELevel) {
      toast.error('Access denied. Only PE Desk or PE Manager can view contract notes.');
      navigate('/');
      return;
    }
    fetchNotes();
  }, [user, isPELevel, navigate]);

  const fetchNotes = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      params.append('limit', pagination.limit);
      params.append('skip', pagination.skip);

      const response = await api.get(`/contract-notes?${params.toString()}`);
      setNotes(response.data.notes);
      setTotal(response.data.total);
    } catch (error) {
      toast.error('Failed to load contract notes');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPagination({ ...pagination, skip: 0 });
    fetchNotes();
  };

  const handleClearFilters = () => {
    setFilters({
      status: '',
      start_date: '',
      end_date: ''
    });
    setPagination({ limit: 50, skip: 0 });
  };

  const handleDownload = async (noteId, noteNumber) => {
    try {
      const response = await api.get(`/contract-notes/download/${noteId}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Contract_Note_${noteNumber.replace(/\//g, '_')}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Contract note downloaded');
    } catch (error) {
      toast.error('Failed to download contract note');
    }
  };

  const handleSendEmail = async (noteId) => {
    setSendingEmail(true);
    try {
      const response = await api.post(`/contract-notes/send-email/${noteId}`);
      toast.success(response.data.message);
      fetchNotes(); // Refresh to show email_sent status
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send email');
    } finally {
      setSendingEmail(false);
    }
  };

  const handleRegenerate = async (noteId) => {
    if (!window.confirm('Are you sure you want to regenerate this contract note? The existing PDF will be replaced.')) {
      return;
    }
    
    setRegenerating(noteId);
    try {
      const response = await api.post(`/contract-notes/regenerate/${noteId}`);
      toast.success(response.data.message);
      fetchNotes(); // Refresh to show updated data
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to regenerate contract note');
    } finally {
      setRegenerating(null);
    }
  };

  const viewNoteDetail = (note) => {
    setSelectedNote(note);
    setDetailOpen(true);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(amount || 0);
  };

  if (loading && notes.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="contract-notes-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileText className="w-7 h-7 text-emerald-600" />
            Contract Notes
          </h1>
          <p className="text-gray-500 mt-1">
            Manage contract notes generated after DP transfer
          </p>
        </div>
        <Button variant="outline" onClick={fetchNotes}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Contract Notes</p>
                <p className="text-2xl font-bold text-emerald-600">{total}</p>
              </div>
              <FileCheck className="w-8 h-8 text-emerald-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Emails Sent</p>
                <p className="text-2xl font-bold text-blue-600">
                  {notes.filter(n => n.email_sent).length}
                </p>
              </div>
              <Mail className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Pending Email</p>
                <p className="text-2xl font-bold text-yellow-600">
                  {notes.filter(n => !n.email_sent).length}
                </p>
              </div>
              <Clock className="w-8 h-8 text-yellow-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label>Status</Label>
              <Select 
                value={filters.status || "all"} 
                onValueChange={(v) => setFilters({ ...filters, status: v === "all" ? "" : v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="generated">Generated</SelectItem>
                  <SelectItem value="sent">Sent</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Start Date</Label>
              <Input
                type="date"
                value={filters.start_date}
                onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
              />
            </div>
            <div>
              <Label>End Date</Label>
              <Input
                type="date"
                value={filters.end_date}
                onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
              />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={handleSearch}>
                <Search className="w-4 h-4 mr-2" />
                Search
              </Button>
              <Button variant="outline" onClick={handleClearFilters}>
                Clear
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Contract Notes Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Contract Notes ({total})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Contract Note #</TableHead>
                  <TableHead>Booking #</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead>Stock</TableHead>
                  <TableHead>Qty</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {notes.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-gray-500">
                      No contract notes found
                    </TableCell>
                  </TableRow>
                ) : (
                  notes.map((note) => (
                    <TableRow key={note.id} data-testid={`contract-note-${note.id}`}>
                      <TableCell className="font-mono text-sm">
                        {note.contract_note_number}
                      </TableCell>
                      <TableCell>{note.booking_number}</TableCell>
                      <TableCell className="max-w-[150px] truncate" title={note.client_name}>
                        {note.client_name}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{note.stock_symbol}</Badge>
                      </TableCell>
                      <TableCell>{note.quantity}</TableCell>
                      <TableCell className="font-medium">
                        {formatCurrency(note.net_amount)}
                      </TableCell>
                      <TableCell>
                        {note.email_sent ? (
                          <Badge className="bg-green-500 text-white">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Sent
                          </Badge>
                        ) : (
                          <Badge variant="secondary">
                            <Clock className="w-3 h-3 mr-1" />
                            Pending
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDate(note.created_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => viewNoteDetail(note)}
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDownload(note.id, note.contract_note_number)}
                            title="Download PDF"
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                          {!note.email_sent && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleSendEmail(note.id)}
                              disabled={sendingEmail}
                              title="Send Email"
                            >
                              <Mail className="w-4 h-4" />
                            </Button>
                          )}
                          {isPEDesk && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRegenerate(note.id)}
                              disabled={regenerating === note.id}
                              title="Regenerate Contract Note"
                              className="text-orange-600 hover:text-orange-700"
                            >
                              {regenerating === note.id ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <RefreshCw className="w-4 h-4" />
                              )}
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {total > pagination.limit && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-gray-500">
                Showing {pagination.skip + 1} to {Math.min(pagination.skip + pagination.limit, total)} of {total}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pagination.skip === 0}
                  onClick={() => {
                    setPagination({ ...pagination, skip: Math.max(0, pagination.skip - pagination.limit) });
                    fetchNotes();
                  }}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pagination.skip + pagination.limit >= total}
                  onClick={() => {
                    setPagination({ ...pagination, skip: pagination.skip + pagination.limit });
                    fetchNotes();
                  }}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Contract Note Details
            </DialogTitle>
          </DialogHeader>
          {selectedNote && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-500">Contract Note #</Label>
                  <p className="font-mono font-medium">{selectedNote.contract_note_number}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Booking #</Label>
                  <p className="font-medium">{selectedNote.booking_number}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-500">Client</Label>
                  <p className="font-medium">{selectedNote.client_name}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Stock</Label>
                  <Badge variant="outline">{selectedNote.stock_symbol}</Badge>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label className="text-gray-500">Quantity</Label>
                  <p className="font-medium">{selectedNote.quantity}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Rate</Label>
                  <p className="font-medium">{formatCurrency(selectedNote.rate)}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Net Amount</Label>
                  <p className="font-bold text-emerald-600">{formatCurrency(selectedNote.net_amount)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-500">Email Status</Label>
                  <div className="mt-1">
                    {selectedNote.email_sent ? (
                      <Badge className="bg-green-500 text-white">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Sent
                      </Badge>
                    ) : (
                      <Badge variant="secondary">
                        <Clock className="w-3 h-3 mr-1" />
                        Pending
                      </Badge>
                    )}
                  </div>
                </div>
                <div>
                  <Label className="text-gray-500">Created</Label>
                  <p className="text-sm">{formatDate(selectedNote.created_at)}</p>
                  <p className="text-xs text-gray-400">By: {selectedNote.created_by_name}</p>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => handleDownload(selectedNote.id, selectedNote.contract_note_number)}
            >
              <Download className="w-4 h-4 mr-2" />
              Download PDF
            </Button>
            {selectedNote && !selectedNote.email_sent && (
              <Button
                onClick={() => {
                  handleSendEmail(selectedNote.id);
                  setDetailOpen(false);
                }}
                disabled={sendingEmail}
              >
                <Mail className="w-4 h-4 mr-2" />
                Send to Client
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ContractNotes;
