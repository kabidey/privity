import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';
import { useProtectedPage } from '../hooks/useProtectedPage';
import { 
  TrendingUp, 
  Plus, 
  Calendar, 
  Clock, 
  IndianRupee, 
  Users, 
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  Search,
  RefreshCw,
  Eye,
  Send,
  Building2
} from 'lucide-react';

const STATUS_COLORS = {
  draft: 'bg-gray-100 text-gray-800',
  upcoming: 'bg-blue-100 text-blue-800',
  open: 'bg-green-100 text-green-800',
  closed: 'bg-yellow-100 text-yellow-800',
  allotment_done: 'bg-purple-100 text-purple-800',
  listed: 'bg-emerald-100 text-emerald-800',
  cancelled: 'bg-red-100 text-red-800'
};

const BID_STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800',
  confirmed: 'bg-blue-100 text-blue-800',
  partially_allotted: 'bg-purple-100 text-purple-800',
  fully_allotted: 'bg-green-100 text-green-800',
  not_allotted: 'bg-red-100 text-red-800',
  refund_initiated: 'bg-orange-100 text-orange-800',
  completed: 'bg-emerald-100 text-emerald-800'
};

const FIPrimaryMarket = () => {
  const { isAuthorized, isLoading: authLoading } = useProtectedPage('fixed_income.view');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('active');
  const [issues, setIssues] = useState([]);
  const [bids, setBids] = useState([]);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [showCreateIssue, setShowCreateIssue] = useState(false);
  const [showSubmitBid, setShowSubmitBid] = useState(false);
  const [clients, setClients] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Form states
  const [issueForm, setIssueForm] = useState({
    isin: '',
    issuer_name: '',
    issue_name: '',
    issue_type: 'NCD',
    face_value: '1000',
    issue_price: '1000',
    coupon_rate: '10',
    coupon_frequency: 'annual',
    tenure_years: '3',
    maturity_date: '',
    credit_rating: 'AA',
    rating_agency: 'CRISIL',
    issue_open_date: '',
    issue_close_date: '',
    min_application_size: '10',
    lot_size: '1',
    base_issue_size: '100',
    notes: ''
  });
  
  const [bidForm, setBidForm] = useState({
    issue_id: '',
    client_id: '',
    category: 'retail',
    quantity: '',
    price: '',
    payment_mode: 'upi',
    upi_id: ''
  });

  useEffect(() => {
    if (!isAuthorized) return;
    fetchIssues();
    fetchClients();
  }, [isAuthorized]);

  useEffect(() => {
    if (activeTab === 'bids') {
      fetchBids();
    }
  }, [activeTab]);

  const fetchIssues = async (status = null) => {
    try {
      setLoading(true);
      const params = status ? `?status=${status}` : '';
      const response = await api.get(`/fixed-income/primary-market/issues${params}`);
      setIssues(response.data.issues || []);
    } catch (error) {
      toast.error('Failed to load issues');
    } finally {
      setLoading(false);
    }
  };

  const fetchActiveIssues = async () => {
    try {
      const response = await api.get('/fixed-income/primary-market/active-issues');
      setIssues(response.data.issues || []);
    } catch (error) {
      toast.error('Failed to load active issues');
    }
  };

  const fetchBids = async () => {
    try {
      setLoading(true);
      const response = await api.get('/fixed-income/primary-market/bids');
      setBids(response.data.bids || []);
    } catch (error) {
      toast.error('Failed to load bids');
    } finally {
      setLoading(false);
    }
  };

  const fetchClients = async () => {
    try {
      // Fetch only clients with Fixed Income module access
      const response = await api.get('/clients/by-module/fixed_income');
      setClients(response.data || []);
    } catch (error) {
      console.error('Failed to load clients');
      // Fallback to all clients if new endpoint fails
      try {
        const fallback = await api.get('/clients?limit=500');
        setClients(fallback.data.clients || []);
      } catch (e) {
        console.error('Fallback also failed');
      }
    }
  };

  const handleCreateIssue = async () => {
    try {
      setLoading(true);
      await api.post('/fixed-income/primary-market/issues', issueForm);
      toast.success('Issue created successfully');
      setShowCreateIssue(false);
      fetchIssues();
      setIssueForm({
        isin: '',
        issuer_name: '',
        issue_name: '',
        issue_type: 'NCD',
        face_value: '1000',
        issue_price: '1000',
        coupon_rate: '10',
        coupon_frequency: 'annual',
        tenure_years: '3',
        maturity_date: '',
        credit_rating: 'AA',
        rating_agency: 'CRISIL',
        issue_open_date: '',
        issue_close_date: '',
        min_application_size: '10',
        lot_size: '1',
        base_issue_size: '100',
        notes: ''
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create issue');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitBid = async () => {
    try {
      setLoading(true);
      const response = await api.post('/fixed-income/primary-market/bids', {
        ...bidForm,
        quantity: parseInt(bidForm.quantity),
        price: parseFloat(bidForm.price)
      });
      toast.success(`Bid submitted! Bid Number: ${response.data.bid_number}`);
      setShowSubmitBid(false);
      fetchBids();
      setBidForm({
        issue_id: '',
        client_id: '',
        category: 'retail',
        quantity: '',
        price: '',
        payment_mode: 'upi',
        upi_id: ''
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit bid');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (issueId, newStatus) => {
    try {
      await api.patch(`/fixed-income/primary-market/issues/${issueId}/status?new_status=${newStatus}`);
      toast.success(`Status updated to ${newStatus}`);
      fetchIssues();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const handleProcessAllotment = async (issueId) => {
    try {
      setLoading(true);
      const response = await api.post(`/fixed-income/primary-market/issues/${issueId}/process-allotment`);
      toast.success(`Allotment processed: ${response.data.allotted_bids}/${response.data.total_bids} bids allotted`);
      fetchIssues();
      fetchBids();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process allotment');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  if (authLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  if (!isAuthorized) {
    return <div className="text-center py-10">Access denied</div>;
  }

  const activeIssues = issues.filter(i => i.status === 'open');
  const upcomingIssues = issues.filter(i => i.status === 'upcoming' || i.status === 'draft');

  return (
    <div className="space-y-6" data-testid="fi-primary-market-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <TrendingUp className="w-7 h-7 text-teal-600" />
            Primary Market - IPO/NFO
          </h1>
          <p className="text-gray-500 mt-1">
            Subscribe to new NCD, Bond, and G-Sec issues
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => fetchIssues()} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Dialog open={showCreateIssue} onOpenChange={setShowCreateIssue}>
            <DialogTrigger asChild>
              <Button className="bg-teal-600 hover:bg-teal-700" data-testid="create-issue-btn">
                <Plus className="w-4 h-4 mr-2" />
                Create Issue
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Create New IPO/NFO Issue</DialogTitle>
                <DialogDescription>Enter the details for the new primary market issue</DialogDescription>
              </DialogHeader>
              <div className="grid grid-cols-2 gap-4 py-4">
                <div>
                  <Label>ISIN *</Label>
                  <Input 
                    value={issueForm.isin}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, isin: e.target.value.toUpperCase() }))}
                    placeholder="INE123A01234"
                  />
                </div>
                <div>
                  <Label>Issue Type</Label>
                  <Select value={issueForm.issue_type} onValueChange={(v) => setIssueForm(prev => ({ ...prev, issue_type: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="NCD">NCD</SelectItem>
                      <SelectItem value="BOND">Bond</SelectItem>
                      <SelectItem value="GSEC">G-Sec</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="col-span-2">
                  <Label>Issuer Name *</Label>
                  <Input 
                    value={issueForm.issuer_name}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, issuer_name: e.target.value }))}
                    placeholder="Company Name Ltd."
                  />
                </div>
                <div className="col-span-2">
                  <Label>Issue Name *</Label>
                  <Input 
                    value={issueForm.issue_name}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, issue_name: e.target.value }))}
                    placeholder="Tranche I - Series A NCD"
                  />
                </div>
                <div>
                  <Label>Face Value (₹)</Label>
                  <Input 
                    type="number"
                    value={issueForm.face_value}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, face_value: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>Issue Price (₹)</Label>
                  <Input 
                    type="number"
                    value={issueForm.issue_price}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, issue_price: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>Coupon Rate (%)</Label>
                  <Input 
                    type="number"
                    step="0.01"
                    value={issueForm.coupon_rate}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, coupon_rate: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>Coupon Frequency</Label>
                  <Select value={issueForm.coupon_frequency} onValueChange={(v) => setIssueForm(prev => ({ ...prev, coupon_frequency: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="monthly">Monthly</SelectItem>
                      <SelectItem value="quarterly">Quarterly</SelectItem>
                      <SelectItem value="semi_annual">Semi-Annual</SelectItem>
                      <SelectItem value="annual">Annual</SelectItem>
                      <SelectItem value="cumulative">Cumulative</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Tenure (Years)</Label>
                  <Input 
                    type="number"
                    value={issueForm.tenure_years}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, tenure_years: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>Maturity Date</Label>
                  <Input 
                    type="date"
                    value={issueForm.maturity_date}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, maturity_date: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>Credit Rating</Label>
                  <Select value={issueForm.credit_rating} onValueChange={(v) => setIssueForm(prev => ({ ...prev, credit_rating: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="AAA">AAA</SelectItem>
                      <SelectItem value="AA+">AA+</SelectItem>
                      <SelectItem value="AA">AA</SelectItem>
                      <SelectItem value="AA-">AA-</SelectItem>
                      <SelectItem value="A+">A+</SelectItem>
                      <SelectItem value="A">A</SelectItem>
                      <SelectItem value="BBB">BBB</SelectItem>
                      <SelectItem value="UNRATED">Unrated</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Rating Agency</Label>
                  <Input 
                    value={issueForm.rating_agency}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, rating_agency: e.target.value }))}
                    placeholder="CRISIL, ICRA, etc."
                  />
                </div>
                <div>
                  <Label>Issue Open Date *</Label>
                  <Input 
                    type="date"
                    value={issueForm.issue_open_date}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, issue_open_date: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>Issue Close Date *</Label>
                  <Input 
                    type="date"
                    value={issueForm.issue_close_date}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, issue_close_date: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>Min Application Size</Label>
                  <Input 
                    type="number"
                    value={issueForm.min_application_size}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, min_application_size: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>Lot Size</Label>
                  <Input 
                    type="number"
                    value={issueForm.lot_size}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, lot_size: e.target.value }))}
                  />
                </div>
                <div className="col-span-2">
                  <Label>Base Issue Size (₹ Cr.)</Label>
                  <Input 
                    type="number"
                    value={issueForm.base_issue_size}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, base_issue_size: e.target.value }))}
                  />
                </div>
                <div className="col-span-2">
                  <Label>Notes</Label>
                  <Textarea 
                    value={issueForm.notes}
                    onChange={(e) => setIssueForm(prev => ({ ...prev, notes: e.target.value }))}
                    placeholder="Additional notes about the issue..."
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateIssue(false)}>Cancel</Button>
                <Button onClick={handleCreateIssue} disabled={loading} className="bg-teal-600 hover:bg-teal-700">
                  {loading ? 'Creating...' : 'Create Issue'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Open Issues</p>
                <p className="text-2xl font-bold text-green-600">{activeIssues.length}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Upcoming</p>
                <p className="text-2xl font-bold text-blue-600">{upcomingIssues.length}</p>
              </div>
              <Clock className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Issues</p>
                <p className="text-2xl font-bold">{issues.length}</p>
              </div>
              <FileText className="h-8 w-8 text-gray-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">My Bids</p>
                <p className="text-2xl font-bold text-purple-600">{bids.length}</p>
              </div>
              <Users className="h-8 w-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="active">Active Issues</TabsTrigger>
          <TabsTrigger value="all">All Issues</TabsTrigger>
          <TabsTrigger value="bids">My Bids</TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="mt-4">
          {activeIssues.length === 0 ? (
            <Card>
              <CardContent className="py-10 text-center text-muted-foreground">
                No active issues available for subscription
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {activeIssues.map((issue) => (
                <Card key={issue.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="text-lg font-semibold">{issue.issue_name}</h3>
                          <Badge className={STATUS_COLORS[issue.status]}>{issue.status}</Badge>
                          <Badge variant="outline">{issue.issue_type}</Badge>
                        </div>
                        <p className="text-muted-foreground mb-3">{issue.issuer_name}</p>
                        <div className="grid grid-cols-5 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">Coupon:</span>
                            <span className="ml-2 font-medium">{issue.coupon_rate}% {issue.coupon_frequency}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Rating:</span>
                            <span className="ml-2 font-medium">{issue.credit_rating}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Face Value:</span>
                            <span className="ml-2 font-medium">{formatCurrency(issue.face_value)}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Close Date:</span>
                            <span className="ml-2 font-medium">{formatDate(issue.issue_close_date)}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Issue Size:</span>
                            <span className="ml-2 font-medium">₹{issue.base_issue_size} Cr.</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        <Button 
                          className="bg-teal-600 hover:bg-teal-700"
                          onClick={() => {
                            setBidForm(prev => ({
                              ...prev,
                              issue_id: issue.id,
                              price: issue.issue_price
                            }));
                            setShowSubmitBid(true);
                          }}
                        >
                          <Send className="w-4 h-4 mr-2" />
                          Subscribe
                        </Button>
                        <Button variant="outline" onClick={() => setSelectedIssue(issue)}>
                          <Eye className="w-4 h-4 mr-2" />
                          Details
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="all" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Issue Number</TableHead>
                    <TableHead>Issuer</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Coupon</TableHead>
                    <TableHead>Rating</TableHead>
                    <TableHead>Open Date</TableHead>
                    <TableHead>Close Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {issues.map((issue) => (
                    <TableRow key={issue.id}>
                      <TableCell className="font-medium">{issue.issue_number}</TableCell>
                      <TableCell>{issue.issuer_name}</TableCell>
                      <TableCell>{issue.issue_type}</TableCell>
                      <TableCell>{issue.coupon_rate}%</TableCell>
                      <TableCell>{issue.credit_rating}</TableCell>
                      <TableCell>{formatDate(issue.issue_open_date)}</TableCell>
                      <TableCell>{formatDate(issue.issue_close_date)}</TableCell>
                      <TableCell>
                        <Badge className={STATUS_COLORS[issue.status]}>{issue.status}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          {issue.status === 'draft' && (
                            <Button size="sm" variant="outline" onClick={() => handleUpdateStatus(issue.id, 'open')}>
                              Open
                            </Button>
                          )}
                          {issue.status === 'open' && (
                            <Button size="sm" variant="outline" onClick={() => handleUpdateStatus(issue.id, 'closed')}>
                              Close
                            </Button>
                          )}
                          {issue.status === 'closed' && (
                            <Button size="sm" variant="outline" onClick={() => handleProcessAllotment(issue.id)}>
                              Allot
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="bids" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {bids.length === 0 ? (
                <div className="text-center py-10 text-muted-foreground">
                  No bids submitted yet
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Bid Number</TableHead>
                      <TableHead>Issue</TableHead>
                      <TableHead>Client</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Quantity</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Allotted</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {bids.map((bid) => (
                      <TableRow key={bid.id}>
                        <TableCell className="font-medium">{bid.bid_number}</TableCell>
                        <TableCell>{bid.issue_number}</TableCell>
                        <TableCell>{bid.client_name}</TableCell>
                        <TableCell className="capitalize">{bid.category}</TableCell>
                        <TableCell>{bid.quantity}</TableCell>
                        <TableCell>{formatCurrency(bid.amount)}</TableCell>
                        <TableCell>{bid.allotted_quantity || 0}</TableCell>
                        <TableCell>
                          <Badge className={BID_STATUS_COLORS[bid.status]}>{bid.status?.replace(/_/g, ' ')}</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Submit Bid Dialog */}
      <Dialog open={showSubmitBid} onOpenChange={setShowSubmitBid}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Subscribe to Issue</DialogTitle>
            <DialogDescription>Submit your bid for the selected issue</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div>
              <Label>Client *</Label>
              <Select value={bidForm.client_id} onValueChange={(v) => setBidForm(prev => ({ ...prev, client_id: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select client" />
                </SelectTrigger>
                <SelectContent>
                  {clients.map((client) => (
                    <SelectItem key={client.id} value={client.id}>
                      {client.name} ({client.pan_number})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Category</Label>
              <Select value={bidForm.category} onValueChange={(v) => setBidForm(prev => ({ ...prev, category: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="retail">Retail</SelectItem>
                  <SelectItem value="hni">HNI</SelectItem>
                  <SelectItem value="qib">QIB</SelectItem>
                  <SelectItem value="non_institutional">Non-Institutional</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Quantity *</Label>
              <Input 
                type="number"
                value={bidForm.quantity}
                onChange={(e) => setBidForm(prev => ({ ...prev, quantity: e.target.value }))}
                placeholder="Number of units"
              />
            </div>
            <div>
              <Label>Price (₹)</Label>
              <Input 
                type="number"
                value={bidForm.price}
                onChange={(e) => setBidForm(prev => ({ ...prev, price: e.target.value }))}
                disabled
              />
            </div>
            <div>
              <Label>Payment Mode</Label>
              <Select value={bidForm.payment_mode} onValueChange={(v) => setBidForm(prev => ({ ...prev, payment_mode: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="upi">UPI</SelectItem>
                  <SelectItem value="netbanking">Net Banking</SelectItem>
                  <SelectItem value="neft">NEFT/RTGS</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {bidForm.payment_mode === 'upi' && (
              <div>
                <Label>UPI ID</Label>
                <Input 
                  value={bidForm.upi_id}
                  onChange={(e) => setBidForm(prev => ({ ...prev, upi_id: e.target.value }))}
                  placeholder="yourname@upi"
                />
              </div>
            )}
            {bidForm.quantity && bidForm.price && (
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-muted-foreground">Total Amount:</p>
                <p className="text-xl font-bold text-teal-600">
                  {formatCurrency(parseInt(bidForm.quantity || 0) * parseFloat(bidForm.price || 0))}
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSubmitBid(false)}>Cancel</Button>
            <Button onClick={handleSubmitBid} disabled={loading || !bidForm.client_id || !bidForm.quantity} className="bg-teal-600 hover:bg-teal-700">
              {loading ? 'Submitting...' : 'Submit Bid'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Issue Details Dialog */}
      <Dialog open={!!selectedIssue} onOpenChange={() => setSelectedIssue(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{selectedIssue?.issue_name}</DialogTitle>
            <DialogDescription>{selectedIssue?.issuer_name}</DialogDescription>
          </DialogHeader>
          {selectedIssue && (
            <div className="grid grid-cols-2 gap-4 py-4">
              <div>
                <p className="text-sm text-muted-foreground">ISIN</p>
                <p className="font-medium">{selectedIssue.isin}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Issue Type</p>
                <p className="font-medium">{selectedIssue.issue_type}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Face Value</p>
                <p className="font-medium">{formatCurrency(selectedIssue.face_value)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Issue Price</p>
                <p className="font-medium">{formatCurrency(selectedIssue.issue_price)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Coupon Rate</p>
                <p className="font-medium">{selectedIssue.coupon_rate}% {selectedIssue.coupon_frequency}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Credit Rating</p>
                <p className="font-medium">{selectedIssue.credit_rating} ({selectedIssue.rating_agency})</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Tenure</p>
                <p className="font-medium">{selectedIssue.tenure_years} years</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Maturity Date</p>
                <p className="font-medium">{formatDate(selectedIssue.maturity_date)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Issue Period</p>
                <p className="font-medium">{formatDate(selectedIssue.issue_open_date)} - {formatDate(selectedIssue.issue_close_date)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Issue Size</p>
                <p className="font-medium">₹{selectedIssue.base_issue_size} Cr.</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Min Application</p>
                <p className="font-medium">{selectedIssue.min_application_size} units</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Lot Size</p>
                <p className="font-medium">{selectedIssue.lot_size} units</p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedIssue(null)}>Close</Button>
            {selectedIssue?.status === 'open' && (
              <Button 
                className="bg-teal-600 hover:bg-teal-700"
                onClick={() => {
                  setBidForm(prev => ({
                    ...prev,
                    issue_id: selectedIssue.id,
                    price: selectedIssue.issue_price
                  }));
                  setSelectedIssue(null);
                  setShowSubmitBid(true);
                }}
              >
                Subscribe Now
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default FIPrimaryMarket;
