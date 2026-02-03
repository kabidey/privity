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
  ArrowRight, CheckCircle, Clock, IndianRupee, Target, Calendar,
  UserCheck, Building2
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

  const hasTeam = data.user?.has_team || (data.team_stats?.direct_reports_count > 0);

  return (
    <div className="space-y-6" data-testid="employee-dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <User className="w-7 h-7 text-blue-600" />
            My Dashboard
          </h1>
          <p className="text-gray-500">Welcome, {data.user?.name || currentUser.name}</p>
          {hasTeam && (
            <Badge className="mt-1 bg-purple-100 text-purple-700">
              Team Manager - {data.team_stats?.direct_reports_count} Direct Reports
            </Badge>
          )}
        </div>
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* My Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card className="cursor-pointer hover:shadow-md" onClick={() => navigate('/clients')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">My Clients</p>
                <p className="text-2xl font-bold text-blue-600">{data.my_stats?.total_clients || 0}</p>
              </div>
              <Users className="w-8 h-8 text-blue-200" />
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md" onClick={() => navigate('/bookings')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">My Bookings</p>
                <p className="text-2xl font-bold text-gray-800">{data.my_stats?.total_bookings || 0}</p>
              </div>
              <FileText className="w-8 h-8 text-gray-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Pending Bookings</p>
                <p className="text-2xl font-bold text-orange-600">{data.my_stats?.pending_bookings || 0}</p>
              </div>
              <Clock className="w-8 h-8 text-orange-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Approved</p>
                <p className="text-2xl font-bold text-green-600">{data.my_stats?.approved_bookings || 0}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Pending Clients</p>
                <p className="text-2xl font-bold text-yellow-600">{data.my_stats?.pending_clients || 0}</p>
              </div>
              <UserCheck className="w-8 h-8 text-yellow-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">My Value</p>
                <p className="text-lg font-bold text-emerald-600">{formatCurrency(data.my_stats?.total_value || 0)}</p>
              </div>
              <IndianRupee className="w-8 h-8 text-emerald-200" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Team Stats - Only show if user has team */}
      {hasTeam && (
        <>
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2 mt-6">
            <Building2 className="w-5 h-5 text-purple-600" />
            Team Overview
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="bg-purple-50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-purple-600">Direct Reports</p>
                    <p className="text-2xl font-bold text-purple-700">{data.team_stats?.direct_reports_count || 0}</p>
                  </div>
                  <Users className="w-8 h-8 text-purple-300" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-purple-50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-purple-600">Team Clients</p>
                    <p className="text-2xl font-bold text-purple-700">{data.team_stats?.team_clients_count || 0}</p>
                  </div>
                  <Users className="w-8 h-8 text-purple-300" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-purple-50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-purple-600">Team Bookings</p>
                    <p className="text-2xl font-bold text-purple-700">{data.team_stats?.team_bookings_count || 0}</p>
                  </div>
                  <FileText className="w-8 h-8 text-purple-300" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-purple-50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-purple-600">Team Value</p>
                    <p className="text-lg font-bold text-purple-700">{formatCurrency(data.team_stats?.team_value || 0)}</p>
                  </div>
                  <IndianRupee className="w-8 h-8 text-purple-300" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Team Performance Table */}
          {data.team_performance && data.team_performance.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-purple-600" />
                  Team Performance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Team Member</TableHead>
                      <TableHead className="text-right">Clients</TableHead>
                      <TableHead className="text-right">Bookings</TableHead>
                      <TableHead className="text-right">Value</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.team_performance.map((member) => (
                      <TableRow key={member.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{member.name}</p>
                            <p className="text-xs text-gray-500">{member.email}</p>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">{member.clients_count}</TableCell>
                        <TableCell className="text-right">{member.bookings_count}</TableCell>
                        <TableCell className="text-right font-medium text-emerald-600">
                          {formatCurrency(member.bookings_value)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* My Recent Bookings */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            My Recent Bookings
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={() => navigate('/bookings')}>
            View All <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </CardHeader>
        <CardContent>
          {data.my_recent_bookings && data.my_recent_bookings.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Booking #</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead>Stock</TableHead>
                  <TableHead className="text-right">Qty</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.my_recent_bookings.map((booking) => (
                  <TableRow key={booking.id}>
                    <TableCell className="font-mono text-sm">{booking.booking_number}</TableCell>
                    <TableCell>{booking.client_name}</TableCell>
                    <TableCell>{booking.stock_symbol}</TableCell>
                    <TableCell className="text-right">{booking.quantity}</TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(booking.quantity * booking.selling_price)}
                    </TableCell>
                    <TableCell>{getApprovalBadge(booking.approval_status)}</TableCell>
                    <TableCell className="text-sm text-gray-500">{formatDate(booking.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-center text-gray-500 py-8">No bookings yet</p>
          )}
        </CardContent>
      </Card>

      {/* My Clients */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-600" />
            My Clients
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={() => navigate('/clients')}>
            View All <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </CardHeader>
        <CardContent>
          {data.my_clients && data.my_clients.length > 0 ? (
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
                    <TableCell className="font-mono text-sm">{client.pan_number}</TableCell>
                    <TableCell>{getApprovalBadge(client.approval_status)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-center text-gray-500 py-8">No clients mapped to you</p>
          )}
        </CardContent>
      </Card>

      {/* Pending Client Approvals */}
      {data.my_pending_clients && data.my_pending_clients.length > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-orange-700">
              <Clock className="w-5 h-5" />
              Pending Client Approvals ({data.my_pending_clients.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>PAN</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.my_pending_clients.map((client) => (
                  <TableRow key={client.id}>
                    <TableCell className="font-medium">{client.name}</TableCell>
                    <TableCell className="font-mono text-sm">{client.pan_number}</TableCell>
                    <TableCell>
                      <Button size="sm" variant="outline" onClick={() => navigate('/clients')}>
                        Review
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default MyDashboard;
