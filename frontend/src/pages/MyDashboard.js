import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  User, Users, FileText, TrendingUp, Briefcase, RefreshCw, 
  ArrowRight, CheckCircle, Clock, IndianRupee, Target, Calendar
} from 'lucide-react';

const MyDashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/dashboard/employee');
      setData(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const getStatusBadge = (status) => {
    const colors = {
      'open': 'bg-blue-500',
      'closed': 'bg-green-500',
      'cancelled': 'bg-gray-500'
    };
    return <Badge className={colors[status] || 'bg-gray-500'}>{status}</Badge>;
  };

  const getApprovalBadge = (status) => {
    const colors = {
      'pending': 'bg-orange-500',
      'approved': 'bg-green-500',
      'rejected': 'bg-red-500',
      'pending_loss_approval': 'bg-red-400'
    };
    const labels = {
      'pending': 'Pending',
      'approved': 'Approved',
      'rejected': 'Rejected',
      'pending_loss_approval': 'Loss Pending'
    };
    return <Badge className={colors[status] || 'bg-gray-500'}>{labels[status] || status}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div className="p-8 text-center text-red-500">
        {data?.error || 'Failed to load dashboard'}
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="employee-dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <User className="w-7 h-7 text-blue-600" />
            My Dashboard
          </h1>
          <p className="text-gray-500">Welcome, {currentUser.name}</p>
        </div>
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card className="cursor-pointer hover:shadow-md" onClick={() => navigate('/clients')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">My Clients</p>
                <p className="text-2xl font-bold text-blue-600">{data.overview.total_clients}</p>
              </div>
              <Users className="w-8 h-8 text-blue-200" />
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md" onClick={() => navigate('/referral-partners')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">My RPs</p>
                <p className="text-2xl font-bold text-purple-600">{data.overview.total_rps}</p>
              </div>
              <Briefcase className="w-8 h-8 text-purple-200" />
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md" onClick={() => navigate('/bookings')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Total Bookings</p>
                <p className="text-2xl font-bold text-gray-800">{data.overview.total_bookings}</p>
              </div>
              <FileText className="w-8 h-8 text-gray-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Open</p>
                <p className="text-2xl font-bold text-blue-600">{data.overview.open_bookings}</p>
              </div>
              <Clock className="w-8 h-8 text-blue-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Closed</p>
                <p className="text-2xl font-bold text-green-600">{data.overview.closed_bookings}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Pending</p>
                <p className="text-2xl font-bold text-orange-600">{data.overview.pending_approval}</p>
              </div>
              <Clock className="w-8 h-8 text-orange-200" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-gradient-to-br from-emerald-50 to-green-50 border-emerald-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-emerald-700 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Total Revenue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-emerald-800">{formatCurrency(data.performance.total_revenue)}</p>
            <p className="text-xs text-emerald-600 mt-1">From all your bookings</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-blue-700 flex items-center gap-2">
              <IndianRupee className="w-4 h-4" />
              Total Profit
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${data.performance.total_profit >= 0 ? 'text-blue-800' : 'text-red-600'}`}>
              {formatCurrency(data.performance.total_profit)}
            </p>
            <p className="text-xs text-blue-600 mt-1">Net profit from bookings</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-50 to-pink-50 border-purple-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-purple-700 flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              This Month
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-800">{data.performance.this_month_bookings}</p>
            <p className="text-xs text-purple-600 mt-1">Bookings created this month</p>
          </CardContent>
        </Card>
      </div>

      {/* My Clients & RPs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* My Clients */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                My Clients
              </span>
              <Button variant="ghost" size="sm" onClick={() => navigate('/clients')}>
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.my_clients.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>PAN</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.my_clients.map((client) => (
                    <TableRow key={client.id}>
                      <TableCell className="font-medium">{client.name}</TableCell>
                      <TableCell className="text-sm font-mono">{client.pan_number}</TableCell>
                      <TableCell>
                        <Badge className={client.approval_status === 'approved' ? 'bg-green-500' : 'bg-orange-500'}>
                          {client.approval_status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Users className="w-12 h-12 mx-auto text-gray-300 mb-2" />
                <p>No clients assigned yet</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* My RPs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Briefcase className="w-5 h-5" />
                My Referral Partners
              </span>
              <Button variant="ghost" size="sm" onClick={() => navigate('/referral-partners')}>
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.my_rps.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.my_rps.map((rp) => (
                    <TableRow key={rp.id}>
                      <TableCell className="font-medium">{rp.name}</TableCell>
                      <TableCell className="text-sm font-mono">{rp.code}</TableCell>
                      <TableCell>
                        <Badge className={rp.approval_status === 'approved' ? 'bg-green-500' : 'bg-orange-500'}>
                          {rp.approval_status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Briefcase className="w-12 h-12 mx-auto text-gray-300 mb-2" />
                <p>No RPs assigned yet</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Bookings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Recent Bookings
            </span>
            <Button variant="ghost" size="sm" onClick={() => navigate('/bookings')}>
              View All <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.recent_bookings.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Booking #</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Stock</TableHead>
                    <TableHead>Qty</TableHead>
                    <TableHead>Value</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Approval</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.recent_bookings.map((booking) => (
                    <TableRow key={booking.id}>
                      <TableCell className="font-medium">{booking.booking_number}</TableCell>
                      <TableCell>{booking.client_name}</TableCell>
                      <TableCell>{booking.stock_symbol}</TableCell>
                      <TableCell>{booking.quantity}</TableCell>
                      <TableCell>{formatCurrency(booking.quantity * booking.buying_price)}</TableCell>
                      <TableCell>{getStatusBadge(booking.status)}</TableCell>
                      <TableCell>{getApprovalBadge(booking.approval_status)}</TableCell>
                      <TableCell className="text-xs text-gray-500">{formatDate(booking.created_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <FileText className="w-12 h-12 mx-auto text-gray-300 mb-2" />
              <p>No bookings yet</p>
              <Button className="mt-4" onClick={() => navigate('/bookings')}>
                Create First Booking
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default MyDashboard;
