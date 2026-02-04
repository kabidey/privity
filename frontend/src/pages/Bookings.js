import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { 
  Plus, Pencil, Trash2, Clock, CheckCircle, XCircle, AlertCircle, 
  CreditCard, IndianRupee, Calendar, Receipt, Building2, TrendingDown, Download, FileSpreadsheet,
  AlertTriangle, Upload, UserCircle, Mail, FileText, Info, Ban, RefreshCw, Users
} from 'lucide-react';

const Bookings = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [bookings, setBookings] = useState([]);
  const [pendingBookings, setPendingBookings] = useState([]);
  const [pendingLossBookings, setPendingLossBookings] = useState([]);
  const [clients, setClients] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [editingBooking, setEditingBooking] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [insiderWarningOpen, setInsiderWarningOpen] = useState(false);
  const [insiderFormDialogOpen, setInsiderFormDialogOpen] = useState(false);
  const [selectedInsiderBooking, setSelectedInsiderBooking] = useState(null);
  const [insiderFormFile, setInsiderFormFile] = useState(null);
  const [uploadingForm, setUploadingForm] = useState(false);
  const [referralPartners, setReferralPartners] = useState([]);
  const [showRpWarning, setShowRpWarning] = useState(false);
  const [showHighRpShareWarning, setShowHighRpShareWarning] = useState(false);
  const [clientIsRpWarning, setClientIsRpWarning] = useState(null); // Stores RP info if client matches an RP
  const [refreshingBooking, setRefreshingBooking] = useState(null); // Track which booking is being refreshed
  const [rpMappingDialogOpen, setRpMappingDialogOpen] = useState(false); // RP mapping dialog
  const [rpMappingBooking, setRpMappingBooking] = useState(null); // Booking being mapped to RP
  const [rpMappingData, setRpMappingData] = useState({ referral_partner_id: '', rp_revenue_share_percent: 30 });
  const [updatingRpMapping, setUpdatingRpMapping] = useState(false);
  const [formData, setFormData] = useState({
    client_id: '',
    stock_id: '',
    quantity: '',
    buying_price: '',
    selling_price: '',
    booking_date: new Date().toISOString().split('T')[0],
    status: 'open',
    notes: '',
    booking_type: 'client',  // client, team, own
    referral_partner_id: '',
    rp_revenue_share_percent: '',
    bp_revenue_share_override: '',  // BP revenue share override (for BP/Partners Desk)
  });
  const [pendingBpOverrides, setPendingBpOverrides] = useState([]); // Bookings with pending BP overrides
  const [bpOverrideDialogOpen, setBpOverrideDialogOpen] = useState(false);
  const [selectedBpOverrideBooking, setSelectedBpOverrideBooking] = useState(null);
  const [bpOverrideRejectionReason, setBpOverrideRejectionReason] = useState('');
  const [processingBpOverride, setProcessingBpOverride] = useState(false);
  const [paymentForm, setPaymentForm] = useState({
    amount: '',
    payment_date: new Date().toISOString().split('T')[0],
    notes: '',
    proof_url: ''
  });
  const [uploadingProof, setUploadingProof] = useState(false);

  // Use centralized role utility
  const {
    user: currentUser,
    isPEDesk,
    isPEManager,
    isPELevel,
    isFinance,
    isViewer,
    isPartnersDesk,
    isBusinessPartner,
    isEmployee,
    canRecordPayments,
    canEditLandingPrice,
    canDelete,
    canModify,
    hasPermission,
  } = useCurrentUser();
  
  // Permission checks for BP override feature
  const canOverrideRevenueShare = hasPermission('bookings.override_revenue_share');
  const canApproveRevenueOverride = hasPermission('bookings.approve_revenue_override');

  useEffect(() => {
    fetchData();
  }, []);

  // Check for openForm query parameter to auto-open booking dialog
  useEffect(() => {
    if (searchParams.get('openForm') === 'true') {
      setDialogOpen(true);
      // Clear the query parameter
      setSearchParams({});
    }
  }, [searchParams, setSearchParams]);

  const fetchData = async () => {
    try {
      const [bookingsRes, clientsRes, stocksRes, inventoryRes, rpRes] = await Promise.all([
        api.get('/bookings'),
        api.get('/clients'),
        api.get('/stocks'),
        api.get('/inventory'),
        api.get('/referral-partners-approved'),  // Only approved and active RPs for booking form
      ]);
      setBookings(bookingsRes.data);
      setClients(clientsRes.data);
      setStocks(stocksRes.data);
      setInventory(inventoryRes.data);
      setReferralPartners(rpRes.data || []);
      
      // Fetch pending bookings and loss bookings if PE Desk
      if (isPEDesk) {
        try {
          const [pendingRes, pendingLossRes] = await Promise.all([
            api.get('/bookings/pending-approval'),
            api.get('/bookings/pending-loss-approval')
          ]);
          setPendingBookings(pendingRes.data);
          setPendingLossBookings(pendingLossRes.data);
        } catch (e) {
          console.error('Failed to fetch pending bookings');
        }
      }
      
      // Fetch pending BP overrides if user has approval permission
      if (canApproveRevenueOverride) {
        try {
          const bpOverridesRes = await api.get('/bookings/pending-bp-overrides');
          setPendingBpOverrides(bpOverridesRes.data || []);
        } catch (e) {
          console.error('Failed to fetch pending BP overrides');
        }
      }
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  // Get Landing Price (LP) for selected stock - this is what's used for booking
  // For non-PE users, the backend already returns LP as weighted_avg_price
  // For PE users, we use landing_price if available, otherwise weighted_avg_price
  const getLandingPrice = (stockId) => {
    const inv = inventory.find(i => i.stock_id === stockId);
    // Use landing_price if available (PE users see this), otherwise use weighted_avg_price
    return inv?.landing_price || inv?.weighted_avg_price || 0;
  };

  // Get inventory info for selected stock
  const getInventoryInfo = (stockId) => {
    const inv = inventory.find(i => i.stock_id === stockId);
    return {
      availableQty: inv?.available_quantity || 0,
      blockedQty: inv?.blocked_quantity || 0,
      landingPrice: inv?.landing_price || inv?.weighted_avg_price || 0,
      weightedAvgPrice: inv?.weighted_avg_price || 0,
      stockSymbol: inv?.stock_symbol || ''
    };
  };

  // Check if quantity exceeds available inventory
  const selectedInventory = formData.stock_id ? getInventoryInfo(formData.stock_id) : null;
  const isLowInventory = selectedInventory && formData.quantity && 
    parseInt(formData.quantity) > selectedInventory.availableQty;

  // Calculate real-time Revenue for form
  const calculateFormPnL = () => {
    if (!formData.stock_id || !formData.quantity || !formData.selling_price) {
      return null;
    }
    
    const qty = parseInt(formData.quantity) || 0;
    const sellingPrice = parseFloat(formData.selling_price) || 0;
    const buyingPrice = formData.buying_price 
      ? parseFloat(formData.buying_price) 
      : getLandingPrice(formData.stock_id);
    
    if (buyingPrice === 0 || qty === 0) return null;
    
    const pnl = (sellingPrice - buyingPrice) * qty;
    const pnlPercentage = ((sellingPrice - buyingPrice) / buyingPrice) * 100;
    const isLoss = sellingPrice < buyingPrice;
    
    return { pnl, pnlPercentage, isLoss, buyingPrice, sellingPrice, qty };
  };

  const formPnL = calculateFormPnL();

  // Handle booking type change
  const handleBookingTypeChange = (value) => {
    setFormData({ ...formData, booking_type: value });
    if (value === 'own') {
      setInsiderWarningOpen(true);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate required fields
    if (!formData.client_id) {
      toast.error('Please select a client');
      return;
    }
    if (!formData.stock_id) {
      toast.error('Please select a stock');
      return;
    }
    if (!formData.quantity || parseInt(formData.quantity) <= 0) {
      toast.error('Please enter a valid quantity');
      return;
    }
    if (!formData.buying_price || parseFloat(formData.buying_price) <= 0) {
      toast.error('Landing price is required');
      return;
    }
    if (!formData.selling_price || parseFloat(formData.selling_price) <= 0) {
      toast.error('Selling price is required');
      return;
    }
    
    // Show warning if no RP selected (cannot be added later)
    if (!formData.referral_partner_id && !showRpWarning) {
      setShowRpWarning(true);
      return;
    }
    
    // Validate RP revenue share if RP is selected
    if (formData.referral_partner_id && !formData.rp_revenue_share_percent) {
      toast.error('Please enter revenue share % for the Referral Partner');
      return;
    }
    
    // For "own" bookings, require form upload acknowledgement
    if (formData.booking_type === 'own' && !formData.insider_form_acknowledged) {
      toast.error('Please acknowledge the Insider Trading Policy first');
      setInsiderWarningOpen(true);
      return;
    }
    
    try {
      const payload = {
        ...formData,
        quantity: parseInt(formData.quantity),
        buying_price: parseFloat(formData.buying_price),
        selling_price: parseFloat(formData.selling_price),
        rp_revenue_share_percent: formData.rp_revenue_share_percent ? parseFloat(formData.rp_revenue_share_percent) : null,
        insider_form_uploaded: false,
      };
      
      // Remove frontend-only fields
      delete payload.insider_form_acknowledged;

      if (editingBooking) {
        await api.put(`/bookings/${editingBooking.id}`, payload);
        toast.success('Booking updated successfully');
      } else {
        const response = await api.post('/bookings', payload);
        toast.success('Booking created - pending PE Desk approval');
        
        // If "own" booking, prompt to upload insider form
        if (formData.booking_type === 'own' && response.data.id) {
          setSelectedInsiderBooking(response.data);
          setInsiderFormDialogOpen(true);
        }
      }
      setDialogOpen(false);
      setShowRpWarning(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    }
  };

  const handleInsiderFormUpload = async () => {
    if (!insiderFormFile || !selectedInsiderBooking) {
      toast.error('Please select a file to upload');
      return;
    }
    
    setUploadingForm(true);
    try {
      const formDataObj = new FormData();
      formDataObj.append('file', insiderFormFile);
      
      await api.post(`/bookings/${selectedInsiderBooking.id}/insider-form`, formDataObj, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      toast.success('Insider trading form uploaded successfully');
      setInsiderFormDialogOpen(false);
      setInsiderFormFile(null);
      setSelectedInsiderBooking(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload form');
    } finally {
      setUploadingForm(false);
    }
  };

  const handleApprove = async (bookingId, approve) => {
    try {
      await api.put(`/bookings/${bookingId}/approve?approve=${approve}`);
      toast.success(approve ? 'Booking approved - inventory adjusted' : 'Booking rejected');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process approval');
    }
  };

  const handleLossApprove = async (bookingId, approve) => {
    try {
      await api.put(`/bookings/${bookingId}/approve-loss?approve=${approve}`);
      toast.success(approve ? 'Loss booking approved' : 'Loss booking rejected');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process loss approval');
    }
  };

  const handleEdit = (booking) => {
    setEditingBooking(booking);
    setFormData({
      client_id: booking.client_id,
      stock_id: booking.stock_id,
      quantity: booking.quantity.toString(),
      buying_price: booking.buying_price.toString(),
      selling_price: booking.selling_price?.toString() || '',
      booking_date: booking.booking_date,
      status: booking.status,
      notes: booking.notes || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = async (bookingId) => {
    if (!window.confirm('Are you sure you want to delete this booking? This will release blocked inventory.')) return;
    try {
      await api.delete(`/bookings/${bookingId}`);
      toast.success('Booking deleted successfully. Inventory released.');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete booking');
    }
  };

  const handleVoidBooking = async (bookingId, bookingNumber) => {
    const reason = window.prompt(`Enter reason for voiding booking ${bookingNumber}:`);
    if (reason === null) return; // User cancelled
    if (!reason.trim()) {
      toast.error('Please provide a reason for voiding');
      return;
    }
    try {
      await api.put(`/bookings/${bookingId}/void?reason=${encodeURIComponent(reason)}`);
      toast.success('Booking voided successfully. Inventory released.');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to void booking');
    }
  };

  const handleExportBookings = async (format = 'xlsx') => {
    try {
      const response = await api.get(`/bookings-export?format=${format}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], {
        type: format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `bookings_export_${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(`Bookings exported to ${format.toUpperCase()} successfully`);
    } catch (error) {
      toast.error('Failed to export bookings');
    }
  };

  // Refresh booking status - checks payments, client approval, etc.
  const handleRefreshBookingStatus = async (bookingId) => {
    if (!bookingId) {
      toast.error('No booking ID provided');
      return;
    }
    setRefreshingBooking(bookingId);
    try {
      const response = await api.post(`/bookings/${bookingId}/refresh-status`);
      const { actions_taken } = response.data;
      
      // Show actions taken
      if (actions_taken && actions_taken.length > 0) {
        actions_taken.forEach(action => {
          if (action.includes('No status changes')) {
            toast.info(action);
          } else {
            toast.success(action);
          }
        });
      } else {
        toast.info('Booking status checked - no changes needed');
      }
      
      // Refresh bookings list to show updated data
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to refresh booking status');
    } finally {
      setRefreshingBooking(null);
    }
  };

  // Open RP mapping dialog for a booking
  const handleOpenRpMapping = (booking) => {
    if (booking.stock_transferred) {
      toast.error('Cannot change RP mapping after stock has been transferred');
      return;
    }
    if (booking.is_bp_booking) {
      toast.error('Cannot assign RP to a Business Partner booking');
      return;
    }
    setRpMappingBooking(booking);
    setRpMappingData({
      referral_partner_id: booking.referral_partner_id || '',
      rp_revenue_share_percent: booking.rp_revenue_share_percent || 30
    });
    setRpMappingDialogOpen(true);
  };

  // Update RP mapping for a booking
  const handleUpdateRpMapping = async () => {
    if (!rpMappingBooking) return;
    
    setUpdatingRpMapping(true);
    try {
      const params = new URLSearchParams();
      if (rpMappingData.referral_partner_id) {
        params.append('referral_partner_id', rpMappingData.referral_partner_id);
        params.append('rp_revenue_share_percent', rpMappingData.rp_revenue_share_percent.toString());
      }
      
      await api.put(`/bookings/${rpMappingBooking.id}/referral-partner?${params.toString()}`);
      
      toast.success('Referral Partner mapping updated successfully');
      setRpMappingDialogOpen(false);
      setRpMappingBooking(null);
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update RP mapping');
    } finally {
      setUpdatingRpMapping(false);
    }
  };

  const handleOpenPaymentDialog = (booking) => {
    setSelectedBooking(booking);
    setPaymentForm({
      amount: '',
      payment_date: new Date().toISOString().split('T')[0],
      notes: '',
      proof_url: ''
    });
    setPaymentDialogOpen(true);
  };

  const handleUploadPaymentProof = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadingProof(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await api.post('/payments/upload-proof', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setPaymentForm({ ...paymentForm, proof_url: response.data.url });
      toast.success('Payment proof uploaded');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload proof');
    } finally {
      setUploadingProof(false);
    }
  };

  const handleAddPayment = async (e) => {
    e.preventDefault();
    if (!selectedBooking) return;

    try {
      const response = await api.post(`/bookings/${selectedBooking.id}/payments`, {
        amount: parseFloat(paymentForm.amount),
        payment_date: paymentForm.payment_date,
        notes: paymentForm.notes || null,
        proof_url: paymentForm.proof_url || null
      });
      
      toast.success(response.data.message);
      
      if (response.data.dp_transfer_ready) {
        toast.success('Full payment received! Booking ready for DP transfer.', {
          duration: 5000,
          icon: '✅'
        });
      }
      
      setPaymentDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    }
  };

  const handleDeletePayment = async (bookingId, trancheNumber) => {
    if (!window.confirm(`Are you sure you want to delete payment tranche ${trancheNumber}?`)) {
      return;
    }
    
    try {
      await api.delete(`/bookings/${bookingId}/payments/${trancheNumber}`);
      toast.success(`Payment tranche ${trancheNumber} deleted successfully`);
      
      // Refresh booking data
      const response = await api.get(`/bookings/${bookingId}`);
      setSelectedBooking(response.data);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete payment');
    }
  };

  const resetForm = () => {
    setFormData({
      client_id: '',
      stock_id: '',
      quantity: '',
      buying_price: '',
      selling_price: '',
      booking_date: new Date().toISOString().split('T')[0],
      status: 'open',
      notes: '',
      booking_type: 'client',
      insider_form_acknowledged: false,
    });
    setEditingBooking(null);
  };

  const getApprovalBadge = (status) => {
    switch (status) {
      case 'pending':
        return <Badge variant="outline" className="text-orange-600 border-orange-600"><Clock className="h-3 w-3 mr-1" />Pending</Badge>;
      case 'approved':
        return <Badge variant="outline" className="text-green-600 border-green-600"><CheckCircle className="h-3 w-3 mr-1" />Approved</Badge>;
      case 'rejected':
        return <Badge variant="outline" className="text-red-600 border-red-600"><XCircle className="h-3 w-3 mr-1" />Rejected</Badge>;
      default:
        return null;
    }
  };

  const getLossApprovalBadge = (booking) => {
    if (!booking.is_loss_booking) return null;
    
    const status = booking.loss_approval_status || 'not_required';
    switch (status) {
      case 'pending':
        return <Badge className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"><TrendingDown className="h-3 w-3 mr-1" />Loss Pending</Badge>;
      case 'approved':
        return <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"><TrendingDown className="h-3 w-3 mr-1" />Loss Approved</Badge>;
      case 'rejected':
        return <Badge className="bg-red-200 text-red-900 dark:bg-red-800 dark:text-red-100"><XCircle className="h-3 w-3 mr-1" />Loss Rejected</Badge>;
      default:
        return null;
    }
  };

  const getClientConfirmationBadge = (booking) => {
    const status = booking.client_confirmation_status || 'pending';
    switch (status) {
      case 'pending':
        return <Badge variant="outline" className="text-purple-600 border-purple-600"><Clock className="h-3 w-3 mr-1" />Client Pending</Badge>;
      case 'accepted':
        return <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"><CheckCircle className="h-3 w-3 mr-1" />Client Accepted</Badge>;
      case 'denied':
        return <Badge className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"><XCircle className="h-3 w-3 mr-1" />Client Denied</Badge>;
      default:
        return null;
    }
  };

  const getPaymentBadge = (booking) => {
    const status = booking.payment_status || 'pending';
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-100 text-green-800"><CheckCircle className="h-3 w-3 mr-1" />Paid</Badge>;
      case 'partial':
        return <Badge className="bg-blue-100 text-blue-800"><Clock className="h-3 w-3 mr-1" />Partial</Badge>;
      default:
        return <Badge variant="outline"><IndianRupee className="h-3 w-3 mr-1" />Pending</Badge>;
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value || 0);
  };

  const displayedBookings = activeTab === 'pending' ? pendingBookings : (activeTab === 'loss' ? pendingLossBookings : bookings);

  // Calculate payment progress
  const getPaymentProgress = (booking) => {
    const total = (booking.selling_price || 0) * booking.quantity;
    const paid = booking.total_paid || 0;
    return total > 0 ? (paid / total) * 100 : 0;
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="bookings-page">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 md:mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold mb-2">Bookings</h1>
          <p className="text-muted-foreground text-sm md:text-base">
            {isEmployee ? 'Create bookings for your clients' : 'Manage private equity bookings and payments'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          {/* Export Buttons - Hidden for Viewers */}
          {!isViewer && (
            <>
              <Button 
                variant="outline" 
                size="sm"
                className="flex-1 sm:flex-none"
                onClick={() => handleExportBookings('xlsx')}
                data-testid="export-excel-button"
              >
                <FileSpreadsheet className="mr-2 h-4 w-4" />
                <span className="hidden sm:inline">Export </span>Excel
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                className="flex-1 sm:flex-none"
                onClick={() => handleExportBookings('csv')}
                data-testid="export-csv-button"
              >
                <Download className="mr-2 h-4 w-4" />
                <span className="hidden sm:inline">Export </span>CSV
              </Button>
            </>
          )}
          
          {/* Add Booking Button - Hidden for Viewers */}
          {!isViewer && (
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button className="rounded-sm flex-1 sm:flex-none" data-testid="add-booking-button">
                <Plus className="mr-2 h-4 w-4" strokeWidth={1.5} />
                Create Booking
              </Button>
            </DialogTrigger>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" aria-describedby="booking-dialog-desc">
            <DialogHeader>
              <DialogTitle>{editingBooking ? 'Edit Booking' : 'Create New Booking'}</DialogTitle>
            </DialogHeader>
            <p id="booking-dialog-desc" className="sr-only">Form to create or edit booking</p>
            
            {!editingBooking && (
              <div className="flex items-center gap-2 p-3 bg-orange-50 dark:bg-orange-950 rounded-lg mb-4">
                <AlertCircle className="h-5 w-5 text-orange-600" />
                <p className="text-sm text-orange-800 dark:text-orange-200">
                  Bookings require <strong>PE Desk approval</strong> before inventory is adjusted.
                </p>
              </div>
            )}
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label>Client * <span className="text-xs text-muted-foreground">(Approved clients only)</span></Label>
                <Select 
                  value={formData.client_id} 
                  onValueChange={async (value) => {
                    setFormData({ ...formData, client_id: value });
                    // Check for Client-RP conflict
                    if (value) {
                      try {
                        const response = await api.get(`/bookings/check-client-rp-conflict/${value}`);
                        if (response.data.has_conflict) {
                          setClientIsRpWarning(response.data);
                          // Auto-clear RP selection if there's a conflict
                          setFormData(prev => ({ ...prev, client_id: value, referral_partner_id: '', rp_revenue_share_percent: '' }));
                        } else {
                          setClientIsRpWarning(null);
                        }
                      } catch (error) {
                        console.error('Error checking client-RP conflict:', error);
                        setClientIsRpWarning(null);
                      }
                    } else {
                      setClientIsRpWarning(null);
                    }
                  }} 
                  required
                >
                  <SelectTrigger data-testid="booking-client-select">
                    <SelectValue placeholder="Select approved client" />
                  </SelectTrigger>
                  <SelectContent>
                    {clients.filter(c => !c.is_vendor && c.is_active && c.approval_status === 'approved' && c.can_book !== false).map((client) => (
                      <SelectItem key={client.id} value={client.id}>
                        {client.name} ({client.otc_ucc || 'N/A'})
                      </SelectItem>
                    ))}
                    {clients.filter(c => !c.is_vendor && c.is_active && c.approval_status === 'approved' && c.can_book !== false).length === 0 && (
                      <div className="px-2 py-4 text-sm text-muted-foreground text-center">
                        No clients available for booking. Only clients mapped to you can be booked.
                      </div>
                    )}
                  </SelectContent>
                </Select>
                
                {/* Client is RP Warning */}
                {clientIsRpWarning && (
                  <div className="p-3 rounded-lg bg-red-100 dark:bg-red-900/50 border-2 border-red-500">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="font-semibold text-red-800 dark:text-red-200">Client is also a Referral Partner</p>
                        <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                          {clientIsRpWarning.message}
                        </p>
                        <p className="text-xs text-red-600 dark:text-red-400 mt-2 font-medium">
                          RP Code: {clientIsRpWarning.rp_code} | RP Name: {clientIsRpWarning.rp_name}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="space-y-2">
                <Label>Stock *</Label>
                <Select 
                  value={formData.stock_id} 
                  onValueChange={(value) => {
                    const landingPrice = getLandingPrice(value);
                    setFormData({ 
                      ...formData, 
                      stock_id: value,
                      buying_price: landingPrice > 0 ? landingPrice.toFixed(2) : ''
                    });
                  }} 
                  required
                >
                  <SelectTrigger data-testid="booking-stock-select">
                    <SelectValue placeholder="Select stock" />
                  </SelectTrigger>
                  <SelectContent>
                    {stocks
                      .filter((stock) => stock.exchange !== 'Blocked IPO/RTA')
                      .map((stock) => (
                      <SelectItem key={stock.id} value={stock.id}>
                        {stock.symbol} - {stock.name}
                        {stock.exchange === 'DRHP Filed' && ' (DRHP Filed)'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Show Landing Price prominently when stock is selected */}
              {formData.stock_id && selectedInventory && (
                <div className="p-4 rounded-lg bg-gradient-to-r from-emerald-500 to-emerald-600 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium opacity-90">Landing Price (Buying Price)</p>
                      <p className="text-3xl font-bold">
                        {formatCurrency(selectedInventory.landingPrice)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium opacity-90">Available Stock</p>
                      <p className="text-2xl font-bold">
                        {selectedInventory.availableQty.toLocaleString()} units
                      </p>
                      {selectedInventory.blockedQty > 0 && (
                        <p className="text-xs opacity-75">
                          ({selectedInventory.blockedQty.toLocaleString()} blocked)
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Quantity *</Label>
                  <Input
                    type="number"
                    min="1"
                    data-testid="booking-quantity-input"
                    value={formData.quantity}
                    onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                    required
                    className={isLowInventory ? 'border-red-500 focus:ring-red-500' : ''}
                  />
                  {/* Low Inventory Warning */}
                  {isLowInventory && (
                    <div className="flex items-start gap-2 p-2 bg-red-100 dark:bg-red-900/50 rounded border border-red-300 dark:border-red-700">
                      <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-red-700 dark:text-red-300">
                        <strong>Low Inventory:</strong> Requested quantity ({formData.quantity}) exceeds available stock ({selectedInventory?.availableQty}). 
                        <span className="block mt-1 font-semibold">Landing price might change based on new purchases.</span>
                      </p>
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  <Label>Landing Price (Buying Price) {!canEditLandingPrice ? '' : '(Editable)'}</Label>
                  <Input
                    type="number"
                    step="0.01"
                    data-testid="booking-buying-price-input"
                    value={formData.buying_price}
                    onChange={(e) => setFormData({ ...formData, buying_price: e.target.value })}
                    readOnly={!canEditLandingPrice}
                    disabled={!canEditLandingPrice}
                    className={!canEditLandingPrice ? 'bg-muted cursor-not-allowed' : ''}
                    placeholder={!canEditLandingPrice ? 'Select stock first' : 'Optional'}
                  />
                  {!canEditLandingPrice && formData.buying_price && (
                    <p className="text-xs text-muted-foreground">
                      Based on Landing Price (set by PE Desk)
                    </p>
                  )}
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Selling Price</Label>
                  <Input
                    type="number"
                    step="0.01"
                    data-testid="booking-selling-price-input"
                    value={formData.selling_price}
                    onChange={(e) => setFormData({ ...formData, selling_price: e.target.value })}
                    placeholder="Price per share"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Booking Date</Label>
                  <Input
                    type="date"
                    data-testid="booking-date-input"
                    value={formData.booking_date}
                    onChange={(e) => setFormData({ ...formData, booking_date: e.target.value })}
                  />
                </div>
              </div>
              
              {/* Real-time Revenue Calculation */}
              {formPnL && (
                <div className={`p-4 rounded-lg border-2 ${formPnL.isLoss ? 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800' : 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-muted-foreground">Estimated Revenue</span>
                    <div className={`flex items-center gap-1 ${formPnL.isLoss ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                      {formPnL.isLoss ? <TrendingDown className="h-4 w-4" /> : <CheckCircle className="h-4 w-4" />}
                      <span className="text-lg font-bold">
                        {formPnL.pnl >= 0 ? '+' : ''}{formatCurrency(formPnL.pnl)}
                      </span>
                      <span className="text-sm">
                        ({formPnL.pnlPercentage >= 0 ? '+' : ''}{formPnL.pnlPercentage.toFixed(2)}%)
                      </span>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
                    <div>
                      <span className="block">Landing Price</span>
                      <span className="font-medium text-foreground">{formatCurrency(formPnL.buyingPrice)}</span>
                    </div>
                    <div>
                      <span className="block">Sell Price</span>
                      <span className="font-medium text-foreground">{formatCurrency(formPnL.sellingPrice)}</span>
                    </div>
                    <div>
                      <span className="block">Quantity</span>
                      <span className="font-medium text-foreground">{formPnL.qty}</span>
                    </div>
                  </div>
                  
                  {/* Loss Warning */}
                  {formPnL.isLoss && (
                    <div className="mt-3 p-2 bg-red-100 dark:bg-red-900/50 rounded flex items-start gap-2">
                      <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-red-700 dark:text-red-300">
                        <strong>Loss Booking:</strong> This booking will require <strong>PE Desk approval</strong> due to selling below landing price.
                      </p>
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={formData.status} onValueChange={(value) => setFormData({ ...formData, status: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="open">Open</SelectItem>
                    <SelectItem value="closed">Closed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {/* Referral Partner Selection */}
              <div className="space-y-3 p-4 rounded-lg border-2 border-dashed border-purple-200 dark:border-purple-800 bg-purple-50/50 dark:bg-purple-950/20">
                <div className="flex items-center gap-2 mb-2">
                  <Users className="h-4 w-4 text-purple-600" />
                  <Label className="text-purple-700 dark:text-purple-400 font-medium">Referral Partner (Optional)</Label>
                </div>
                
                {/* Business Partner Logged In - RP Selection Disabled */}
                {isBusinessPartner ? (
                  <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border-2 border-emerald-300 dark:border-emerald-700">
                    <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
                      <Users className="h-5 w-5" />
                      <span className="font-medium">Business Partner Booking</span>
                    </div>
                    <p className="text-sm text-emerald-600 dark:text-emerald-400 mt-2">
                      You are logged in as a Business Partner. Your revenue share of <strong>{currentUser.revenue_share_percent || 0}%</strong> will be automatically applied to this booking.
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">
                      Referral Partner selection is disabled for Business Partners.
                    </p>
                  </div>
                ) : clientIsRpWarning ? (
                  /* Client is RP - RP Selection Disabled */
                  <div className="p-4 rounded-lg bg-gray-100 dark:bg-gray-800 border-2 border-dashed border-gray-300 dark:border-gray-600">
                    <div className="flex items-center gap-2 text-gray-500">
                      <Users className="h-5 w-5" />
                      <span className="font-medium">RP Selection Disabled</span>
                    </div>
                    <p className="text-sm text-gray-500 mt-2">
                      This client ({clientIsRpWarning.client_name}) is registered as RP {clientIsRpWarning.rp_code}. 
                      A client cannot earn RP commission on their own booking.
                    </p>
                  </div>
                ) : (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Select RP</Label>
                    <Select 
                      value={formData.referral_partner_id} 
                      onValueChange={(value) => setFormData({ ...formData, referral_partner_id: value === 'none' ? '' : value })}
                    >
                      <SelectTrigger data-testid="rp-select">
                        <SelectValue placeholder="Select Referral Partner" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">No RP</SelectItem>
                        {referralPartners.map((rp) => (
                          <SelectItem key={rp.id} value={rp.id}>
                            {rp.rp_code} - {rp.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {referralPartners.length === 0 && (
                      <p className="text-xs text-muted-foreground">No approved RPs available. RPs must be approved by PE Desk/PE Manager first.</p>
                    )}
                  </div>
                  {formData.referral_partner_id && (
                    <div className="space-y-2">
                      <Label>Revenue Share % (Max 30%)</Label>
                      <Input
                        type="number"
                        min="0"
                        max="30"
                        step="0.1"
                        data-testid="rp-revenue-share-input"
                        value={formData.rp_revenue_share_percent}
                        onChange={(e) => {
                          let val = parseFloat(e.target.value);
                          // Show warning if trying to enter more than 30%
                          if (val > 30) {
                            setShowHighRpShareWarning(true);
                            val = 30;
                          }
                          if (val < 0) val = 0;
                          setFormData({ ...formData, rp_revenue_share_percent: isNaN(val) ? '' : val.toString() });
                        }}
                        placeholder="e.g., 10 (max 30)"
                      />
                    </div>
                  )}
                </div>
                )}
                
                {/* High RP Share Warning Popup Dialog */}
                <Dialog open={showHighRpShareWarning} onOpenChange={setShowHighRpShareWarning}>
                  <DialogContent 
                    className="max-w-lg border-4 border-red-600"
                    style={{
                      background: 'linear-gradient(135deg, #fef08a 0%, #fecaca 50%, #fef08a 100%)',
                    }}
                  >
                    <DialogHeader className="space-y-3">
                      <div className="flex items-center justify-center">
                        <div className="p-3 bg-red-600 rounded-full animate-pulse">
                          <AlertTriangle className="h-8 w-8 text-white" />
                        </div>
                      </div>
                      <DialogTitle className="text-center text-2xl font-bold text-red-800">
                        ⚠️ WARNING
                      </DialogTitle>
                      <DialogDescription className="text-center text-red-700 font-semibold text-base">
                        High Revenue Share Detected
                      </DialogDescription>
                    </DialogHeader>
                    
                    <div className="space-y-4 py-4">
                      <p className="text-red-900 leading-relaxed">
                        You have chosen an RP to share <strong className="text-red-700 text-lg">{formData.rp_revenue_share_percent || 30}%</strong> of the booking revenue. 
                        It will be verified by PE Desk if the client was sourced by the RP.
                      </p>
                      
                      <div className="p-3 bg-red-700 rounded-lg">
                        <p className="text-white font-bold text-center">
                          If this booking is found to be dubious, disciplinary action will be initiated against you.
                        </p>
                      </div>
                      
                      <p className="text-red-900 leading-relaxed">
                        If you still want to share more than 30% of the revenue, please connect with{' '}
                        <a 
                          href="mailto:partnersdesk@smifs.com" 
                          className="font-bold underline text-red-700 hover:text-red-900"
                        >
                          partnersdesk@smifs.com
                        </a>{' '}
                        to initiate and convert RP to BP.
                      </p>
                      
                      <p className="font-semibold text-red-800 text-center">
                        If you have chosen by mistake, please immediately remove the selection.
                      </p>
                    </div>
                    
                    <DialogFooter className="flex gap-3 sm:justify-center">
                      <Button
                        type="button"
                        variant="destructive"
                        className="bg-red-700 hover:bg-red-800"
                        onClick={() => {
                          setFormData({ ...formData, referral_partner_id: '', rp_revenue_share_percent: '' });
                          setShowHighRpShareWarning(false);
                        }}
                      >
                        Remove RP Selection
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        className="border-red-600 text-red-700 hover:bg-red-100"
                        onClick={() => setShowHighRpShareWarning(false)}
                      >
                        I Understand, Continue
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
                {!editingBooking && (
                  <p className="text-xs text-muted-foreground">
                    <AlertCircle className="h-3 w-3 inline mr-1" />
                    Note: Referral Partner cannot be added after booking is created.
                  </p>
                )}
              </div>
              
              {/* RP Warning Dialog */}
              {showRpWarning && (
                <div className="p-4 rounded-lg bg-yellow-50 dark:bg-yellow-950 border-2 border-yellow-400 dark:border-yellow-600">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                    <div>
                      <p className="font-medium text-yellow-800 dark:text-yellow-200">No Referral Partner Selected</p>
                      <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                        You have not selected a Referral Partner. Once the booking is created, you <strong>cannot add an RP later</strong>.
                      </p>
                      <div className="flex gap-2 mt-3">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setShowRpWarning(false)}
                        >
                          Go Back & Select RP
                        </Button>
                        <Button
                          type="submit"
                          size="sm"
                          className="bg-yellow-600 hover:bg-yellow-700"
                        >
                          Continue Without RP
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="space-y-2">
                <Label>Notes</Label>
                <Textarea
                  data-testid="booking-notes-input"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={2}
                />
              </div>
              
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                <Button type="submit" data-testid="save-booking-button">
                  {editingBooking ? 'Update' : 'Create Booking'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
          )}
        </div>
      </div>

      {isPEDesk && (pendingBookings.length > 0 || pendingLossBookings.length > 0) && (
        <div className="mb-4">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="all">All Bookings ({bookings.length})</TabsTrigger>
              {pendingBookings.length > 0 && (
                <TabsTrigger value="pending" className="text-orange-600">
                  <Clock className="h-4 w-4 mr-1" />
                  Pending Approval ({pendingBookings.length})
                </TabsTrigger>
              )}
              {pendingLossBookings.length > 0 && (
                <TabsTrigger value="loss" className="text-red-600">
                  <TrendingDown className="h-4 w-4 mr-1" />
                  Loss Approval ({pendingLossBookings.length})
                </TabsTrigger>
              )}
            </TabsList>
          </Tabs>
        </div>
      )}

      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle>{activeTab === 'pending' ? 'Pending Approval' : (activeTab === 'loss' ? 'Loss Bookings - Pending Approval' : 'All Bookings')}</CardTitle>
          <CardDescription>
            {activeTab === 'loss' 
              ? 'These bookings have selling price lower than landing price - requires PE Desk approval'
              : (canRecordPayments && 'Record payments for approved bookings to enable DP transfer')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? <div>Loading...</div> : displayedBookings.length === 0 ? (
            <div className="text-center py-12"><p className="text-muted-foreground">No bookings found.</p></div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase">Booking ID</TableHead>
                    <TableHead className="text-xs uppercase">Client</TableHead>
                    <TableHead className="text-xs uppercase">Stock</TableHead>
                    <TableHead className="text-xs uppercase">Qty</TableHead>
                    <TableHead className="text-xs uppercase">Landing Price</TableHead>
                    <TableHead className="text-xs uppercase">Sell Price</TableHead>
                    <TableHead className="text-xs uppercase">Revenue</TableHead>
                    <TableHead className="text-xs uppercase">Status</TableHead>
                    <TableHead className="text-xs uppercase">Payment</TableHead>
                    <TableHead className="text-xs uppercase">Created By</TableHead>
                    <TableHead className="text-xs uppercase text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedBookings.map((booking) => {
                    const totalAmount = (booking.selling_price || 0) * booking.quantity;
                    const buyTotal = booking.buying_price * booking.quantity;
                    const profitLoss = booking.selling_price ? (booking.selling_price - booking.buying_price) * booking.quantity : null;
                    const isLoss = profitLoss !== null && profitLoss < 0;
                    
                    return (
                      <TableRow key={booking.id} data-testid="booking-row" className={isLoss ? 'bg-red-50/50 dark:bg-red-950/20' : ''}>
                        <TableCell>
                          <span className="font-mono text-sm font-semibold text-primary">
                            {booking.booking_number || booking.id.substring(0, 8).toUpperCase()}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div>
                            <p className="font-medium">{booking.client_name}</p>
                            <p className="text-xs text-muted-foreground">{booking.client_pan || ''}</p>
                          </div>
                        </TableCell>
                        <TableCell className="mono font-semibold">{booking.stock_symbol}</TableCell>
                        <TableCell className="mono">{booking.quantity}</TableCell>
                        <TableCell className="mono">
                          {formatCurrency(booking.buying_price)}
                        </TableCell>
                        <TableCell className="mono">
                          {booking.selling_price ? formatCurrency(booking.selling_price) : '-'}
                        </TableCell>
                        <TableCell className={`mono font-medium ${profitLoss !== null ? (profitLoss >= 0 ? 'text-green-600' : 'text-red-600') : ''}`}>
                          {profitLoss !== null ? (
                            <span>{profitLoss >= 0 ? '+' : ''}{formatCurrency(profitLoss)}</span>
                          ) : '-'}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            {getClientConfirmationBadge(booking)}
                            {booking.client_confirmation_status === 'accepted' && getApprovalBadge(booking.approval_status)}
                            {getLossApprovalBadge(booking)}
                            {booking.client_confirmation_status === 'denied' && booking.client_denial_reason && (
                              <span className="text-xs text-red-600" title={booking.client_denial_reason}>
                                Reason: {booking.client_denial_reason.substring(0, 20)}...
                              </span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {booking.approval_status === 'approved' && booking.selling_price ? (
                            <div className="space-y-1">
                              {getPaymentBadge(booking)}
                              <Progress value={getPaymentProgress(booking)} className="h-1.5 w-20" />
                              <p className="text-xs text-muted-foreground">
                                {formatCurrency(booking.total_paid || 0)} / {formatCurrency(totalAmount)}
                              </p>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="text-sm">{booking.created_by_name || '-'}</span>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {/* Loss booking approval buttons */}
                            {isPELevel && booking.is_loss_booking && booking.loss_approval_status === 'pending' && (
                              <>
                                <Button variant="ghost" size="sm" onClick={() => handleLossApprove(booking.id, true)} className="text-yellow-600" title="Approve Loss">
                                  <TrendingDown className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="sm" onClick={() => handleLossApprove(booking.id, false)} className="text-red-600" title="Reject Loss">
                                  <XCircle className="h-4 w-4" />
                                </Button>
                              </>
                            )}
                            {/* Regular booking approval buttons */}
                            {isPELevel && booking.approval_status === 'pending' && (
                              <>
                                <Button variant="ghost" size="sm" onClick={() => handleApprove(booking.id, true)} className="text-green-600" title="Approve">
                                  <CheckCircle className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="sm" onClick={() => handleApprove(booking.id, false)} className="text-red-600" title="Reject">
                                  <XCircle className="h-4 w-4" />
                                </Button>
                              </>
                            )}
                            {!isViewer && canRecordPayments && booking.approval_status === 'approved' && 
                             booking.selling_price && !booking.dp_transfer_ready && (
                              <Button 
                                variant="outline" 
                                size="sm" 
                                onClick={() => handleOpenPaymentDialog(booking)}
                                className="text-blue-600 border-blue-300 hover:bg-blue-50 dark:hover:bg-blue-950"
                                title="Record Payment"
                                data-testid="record-payment-button"
                              >
                                <CreditCard className="h-4 w-4 mr-1" />
                                Pay
                              </Button>
                            )}
                            {booking.dp_transfer_ready && (
                              <Badge className="bg-green-100 text-green-800 text-xs">
                                <Building2 className="h-3 w-3 mr-1" />
                                DP Ready
                              </Badge>
                            )}
                            {/* Edit button - not for employees or viewers */}
                            {!isEmployee && !isViewer && (
                              <Button variant="ghost" size="sm" onClick={() => handleEdit(booking)}><Pencil className="h-4 w-4" /></Button>
                            )}
                            {/* Edit RP Mapping button - PE Level only, not for BP bookings or transferred */}
                            {isPELevel && !booking.is_bp_booking && !booking.stock_transferred && !booking.is_voided && (
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => handleOpenRpMapping(booking)}
                                title="Edit Referral Partner Mapping"
                                className="text-purple-600"
                                data-testid="edit-rp-mapping-btn"
                              >
                                <Users className="h-4 w-4" />
                              </Button>
                            )}
                            {/* Refresh Status button - PE Level only */}
                            {isPELevel && (
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => handleRefreshBookingStatus(booking.id)}
                                disabled={refreshingBooking === booking.id}
                                title="Refresh Status (checks payments, client approval, DP status)"
                                className="text-blue-600"
                              >
                                <RefreshCw className={`h-4 w-4 ${refreshingBooking === booking.id ? 'animate-spin' : ''}`} />
                              </Button>
                            )}
                            {/* Void button - PE Desk only, not for transferred bookings */}
                            {isPEDesk && !isViewer && !booking.stock_transferred && !booking.is_voided && (
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => handleVoidBooking(booking.id, booking.booking_number)} 
                                className="text-orange-600"
                                title="Void Booking (keeps record, releases inventory)"
                              >
                                <Ban className="h-4 w-4" />
                              </Button>
                            )}
                            {/* Delete button - PE Desk only, not for transferred bookings */}
                            {isPEDesk && !booking.stock_transferred && (
                              <Button variant="ghost" size="sm" onClick={() => handleDelete(booking.id)} className="text-red-600" title="Delete Booking"><Trash2 className="h-4 w-4" /></Button>
                            )}
                            {/* Show voided badge */}
                            {booking.is_voided && (
                              <Badge variant="outline" className="text-gray-500 border-gray-400">
                                <Ban className="h-3 w-3 mr-1" />Voided
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Payment Dialog */}
      <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Record Payment
            </DialogTitle>
          </DialogHeader>
          
          {selectedBooking && (
            <div className="space-y-4">
              {/* Booking Summary */}
              <div className="bg-muted p-4 rounded-lg space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Client</span>
                  <span className="font-medium">{selectedBooking.client_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Stock</span>
                  <span className="font-medium">{selectedBooking.stock_symbol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Quantity</span>
                  <span>{selectedBooking.quantity}</span>
                </div>
                <div className="flex justify-between border-t pt-2">
                  <span className="text-muted-foreground">Total Amount</span>
                  <span className="font-bold">
                    {formatCurrency((selectedBooking.selling_price || 0) * selectedBooking.quantity)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Paid</span>
                  <span className="text-green-600">{formatCurrency(selectedBooking.total_paid || 0)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Remaining</span>
                  <span className="text-orange-600 font-medium">
                    {formatCurrency((selectedBooking.selling_price || 0) * selectedBooking.quantity - (selectedBooking.total_paid || 0))}
                  </span>
                </div>
                <Progress value={getPaymentProgress(selectedBooking)} className="h-2" />
                <p className="text-xs text-muted-foreground text-center">
                  Tranche {(selectedBooking.payments?.length || 0) + 1} of 4
                </p>
              </div>

              {/* Payment History */}
              {selectedBooking.payments && selectedBooking.payments.length > 0 && (
                <div className="space-y-2">
                  <Label>Payment History</Label>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {selectedBooking.payments.map((p, idx) => (
                      <div key={idx} className="flex items-center justify-between text-sm p-2 bg-muted/50 rounded">
                        <div className="flex-1">
                          <span>Tranche {p.tranche_number}: {formatCurrency(p.amount)}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">{new Date(p.payment_date).toLocaleDateString('en-IN')}</span>
                          {isPELevel && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-red-500 hover:text-red-700 hover:bg-red-100"
                              onClick={() => handleDeletePayment(selectedBooking.id, p.tranche_number)}
                              data-testid={`delete-payment-${p.tranche_number}`}
                              title="Delete payment"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Payment Form */}
              <form onSubmit={handleAddPayment} className="space-y-4">
                <div className="space-y-2">
                  <Label>Payment Amount (INR) *</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max={(selectedBooking.selling_price || 0) * selectedBooking.quantity - (selectedBooking.total_paid || 0)}
                    value={paymentForm.amount}
                    onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                    placeholder="Enter amount"
                    required
                    data-testid="payment-amount-input"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Payment Date *</Label>
                  <Input
                    type="date"
                    value={paymentForm.payment_date}
                    onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })}
                    required
                    data-testid="payment-date-input"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea
                    value={paymentForm.notes}
                    onChange={(e) => setPaymentForm({ ...paymentForm, notes: e.target.value })}
                    placeholder="Payment reference, bank details, etc."
                    rows={2}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Upload Payment Proof (Optional)</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                      onChange={handleUploadPaymentProof}
                      disabled={uploadingProof}
                      className="flex-1"
                      data-testid="payment-proof-input"
                    />
                    {uploadingProof && <RefreshCw className="h-4 w-4 animate-spin" />}
                  </div>
                  {paymentForm.proof_url && (
                    <p className="text-xs text-green-600 flex items-center gap-1">
                      <CheckCircle className="h-3 w-3" />
                      Proof uploaded successfully
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Supported: PDF, JPG, PNG, DOC, DOCX
                  </p>
                </div>
                
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setPaymentDialogOpen(false)}>Cancel</Button>
                  <Button type="submit" data-testid="save-payment-button">
                    <Receipt className="h-4 w-4 mr-2" />
                    Record Payment
                  </Button>
                </div>
              </form>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Insider Trading Warning Dialog */}
      <Dialog open={insiderWarningOpen} onOpenChange={setInsiderWarningOpen}>
        <DialogContent className="max-w-md" data-testid="insider-warning-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-orange-600">
              <AlertTriangle className="h-5 w-5" />
              Insider Trading Policy Warning
            </DialogTitle>
            <DialogDescription>
              Important compliance information for personal bookings
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <Alert variant="destructive" className="bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800">
              <AlertTriangle className="h-4 w-4 text-orange-600" />
              <AlertTitle className="text-orange-800 dark:text-orange-200">Compliance Required</AlertTitle>
              <AlertDescription className="text-orange-700 dark:text-orange-300">
                <p className="mt-2">
                  As per regulatory requirements, booking shares for your <strong>own account</strong> requires compliance with the <strong>Insider Trading Policy</strong>.
                </p>
              </AlertDescription>
            </Alert>
            
            <div className="p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
              <h4 className="font-semibold text-blue-800 dark:text-blue-200 flex items-center gap-2 mb-2">
                <Mail className="h-4 w-4" />
                Request Requisite Forms
              </h4>
              <p className="text-sm text-blue-700 dark:text-blue-300 mb-2">
                Please write to the PE Desk to obtain the necessary compliance forms:
              </p>
              <a 
                href="mailto:pe@smifs.com?subject=Request for Insider Trading Compliance Forms&body=Dear PE Desk,%0D%0A%0D%0AI am requesting the requisite forms for personal booking as per the Insider Trading Policy.%0D%0A%0D%0ARegards"
                className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline font-medium"
              >
                <Mail className="h-4 w-4" />
                pe@smifs.com
              </a>
            </div>
            
            <div className="p-4 bg-muted rounded-lg">
              <h4 className="font-semibold flex items-center gap-2 mb-2">
                <FileText className="h-4 w-4" />
                Upload Facility
              </h4>
              <p className="text-sm text-muted-foreground">
                After receiving and completing the requisite forms, you can upload them when creating the booking or afterwards from the bookings list.
              </p>
            </div>
          </div>
          
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => {
                setInsiderWarningOpen(false);
                setFormData({ ...formData, booking_type: 'client' });
              }}
              data-testid="insider-warning-cancel-btn"
            >
              Cancel
            </Button>
            <Button 
              onClick={() => {
                setInsiderWarningOpen(false);
                setFormData({ ...formData, insider_form_acknowledged: true });
              }}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="insider-warning-acknowledge-btn"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              I Acknowledge & Continue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Insider Form Upload Dialog */}
      <Dialog open={insiderFormDialogOpen} onOpenChange={setInsiderFormDialogOpen}>
        <DialogContent className="max-w-md" data-testid="insider-form-upload-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-blue-600" />
              Upload Insider Trading Form
            </DialogTitle>
            <DialogDescription>
              Upload the completed compliance form for your personal booking
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {selectedInsiderBooking && (
              <div className="p-3 bg-muted rounded-lg text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Booking ID</span>
                  <span className="font-mono font-semibold">{selectedInsiderBooking.booking_number || selectedInsiderBooking.id?.substring(0, 8).toUpperCase()}</span>
                </div>
              </div>
            )}
            
            <div className="space-y-2">
              <Label>Select Form (PDF, JPG, PNG)</Label>
              <Input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(e) => setInsiderFormFile(e.target.files[0])}
                data-testid="insider-form-file-input"
              />
              {insiderFormFile && (
                <p className="text-sm text-green-600 flex items-center gap-1">
                  <CheckCircle className="h-3 w-3" />
                  {insiderFormFile.name}
                </p>
              )}
            </div>
            
            <Alert className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <Info className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-700 dark:text-blue-300 text-sm">
                You can also upload the form later from the bookings list by clicking on the booking.
              </AlertDescription>
            </Alert>
          </div>
          
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => {
                setInsiderFormDialogOpen(false);
                setInsiderFormFile(null);
                setSelectedInsiderBooking(null);
              }}
            >
              Upload Later
            </Button>
            <Button 
              onClick={handleInsiderFormUpload}
              disabled={!insiderFormFile || uploadingForm}
              data-testid="upload-insider-form-btn"
            >
              {uploadingForm ? (
                <>Uploading...</>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Form
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* RP Mapping Edit Dialog */}
      <Dialog open={rpMappingDialogOpen} onOpenChange={setRpMappingDialogOpen}>
        <DialogContent className="max-w-md" data-testid="rp-mapping-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-purple-600" />
              Edit Referral Partner Mapping
            </DialogTitle>
            <DialogDescription>
              Update the referral partner assigned to this booking
            </DialogDescription>
          </DialogHeader>
          
          {rpMappingBooking && (
            <div className="space-y-4">
              {/* Booking Info */}
              <div className="p-3 bg-muted rounded-lg text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Booking ID</span>
                  <span className="font-mono font-semibold">{rpMappingBooking.booking_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Client</span>
                  <span className="font-medium">{rpMappingBooking.client_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Stock</span>
                  <span className="font-medium">{rpMappingBooking.stock_symbol}</span>
                </div>
                {rpMappingBooking.rp_name && (
                  <div className="flex justify-between border-t pt-1 mt-1">
                    <span className="text-muted-foreground">Current RP</span>
                    <span className="font-medium text-purple-600">{rpMappingBooking.rp_code} - {rpMappingBooking.rp_name}</span>
                  </div>
                )}
              </div>
              
              {/* RP Selection */}
              <div className="space-y-2">
                <Label>Referral Partner</Label>
                <Select
                  value={rpMappingData.referral_partner_id || "none"}
                  onValueChange={(value) => setRpMappingData({ ...rpMappingData, referral_partner_id: value === "none" ? "" : value })}
                  data-testid="rp-mapping-select"
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Referral Partner (or leave empty to remove)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">-- Remove RP Assignment --</SelectItem>
                    {referralPartners.map((rp) => (
                      <SelectItem key={rp.id} value={rp.id}>
                        {rp.rp_code} - {rp.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Revenue Share - only show if RP selected */}
              {rpMappingData.referral_partner_id && (
                <div className="space-y-2">
                  <Label>Revenue Share % (Max 30%)</Label>
                  <Input
                    type="number"
                    min="0"
                    max="30"
                    step="0.1"
                    value={rpMappingData.rp_revenue_share_percent}
                    onChange={(e) => {
                      let val = parseFloat(e.target.value);
                      if (val > 30) val = 30;
                      if (val < 0) val = 0;
                      setRpMappingData({ ...rpMappingData, rp_revenue_share_percent: isNaN(val) ? 0 : val });
                    }}
                    placeholder="e.g., 10 (max 30)"
                    data-testid="rp-mapping-share-input"
                  />
                  <p className="text-xs text-muted-foreground">
                    Employee share will be: {(100 - (rpMappingData.rp_revenue_share_percent || 0)).toFixed(1)}%
                  </p>
                </div>
              )}
              
              {/* Warning about removing RP */}
              {!rpMappingData.referral_partner_id && rpMappingBooking.referral_partner_id && (
                <Alert className="bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800">
                  <AlertTriangle className="h-4 w-4 text-yellow-600" />
                  <AlertDescription className="text-yellow-700 dark:text-yellow-300 text-sm">
                    You are about to remove the RP assignment. The employee will receive 100% revenue share.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
          
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => {
                setRpMappingDialogOpen(false);
                setRpMappingBooking(null);
              }}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleUpdateRpMapping}
              disabled={updatingRpMapping}
              className="bg-purple-600 hover:bg-purple-700"
              data-testid="save-rp-mapping-btn"
            >
              {updatingRpMapping ? (
                <>Updating...</>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Update RP Mapping
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Bookings;
