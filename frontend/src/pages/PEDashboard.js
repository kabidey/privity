import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import api from '../utils/api';
import { useProtectedPage } from '../hooks/useProtectedPage';
import { 
  Shield, Clock, Users, AlertTriangle, FileText, CheckCircle, 
  TrendingUp, Activity, RefreshCw, ArrowRight, UserCheck, Briefcase, IndianRupee,
  CalendarClock, Play
} from 'lucide-react';

const PEDashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [clearingCache, setClearingCache] = useState(false);
  const [scheduledJobs, setScheduledJobs] = useState(null);
  const [triggeringJob, setTriggeringJob] = useState(false);

  const { isLoading, isAuthorized, isPEDesk, hasPermission } = useProtectedPage({
    allowIf: ({ isPELevel, hasPermission }) => isPELevel || hasPermission('dashboard.pe_view'),
    deniedMessage: 'Access denied. You need PE Dashboard permission to view this page.'
  });

  useEffect(() => {
    if (!isAuthorized) return;
    fetchData();
    fetchScheduledJobs();
  }, [isAuthorized]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/dashboard/pe');
      setData(response.data);
    } catch (error) {
      toast.error('Failed to load PE dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchScheduledJobs = async () => {
    try {
      const response = await api.get('/dashboard/scheduled-jobs');
      setScheduledJobs(response.data);
    } catch (error) {
      console.error('Failed to fetch scheduled jobs:', error);
    }
  };

  const handleTriggerJob = async (jobId) => {
    if (!window.confirm('Are you sure you want to trigger this job now? This will send day-end reports to all users.')) {
      return;
    }
    
    setTriggeringJob(true);
    try {
      await api.post(`/dashboard/trigger-job/${jobId}`);
      toast.success('Job triggered successfully. Reports are being sent.');
      fetchScheduledJobs();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to trigger job');
    } finally {
      setTriggeringJob(false);
    }
  };

  const handleClearCache = async () => {
    if (!window.confirm('This will clear system cache, recalculate inventory averages, and clean up orphaned records. Continue?')) {
      return;
    }
    
    setClearingCache(true);
    try {
      const response = await api.post('/dashboard/clear-cache');
      toast.success(response.data.message);
      localStorage.removeItem('privity_cache_dashboard_stats');
      localStorage.removeItem('privity_cache_dashboard_analytics');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clear cache');
    } finally {
      setClearingCache(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Show loading while checking permissions
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

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
    <div className="space-y-6" data-testid="pe-dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Shield className="w-7 h-7 text-red-600" />
            PE Command Center
          </h1>
          <p className="text-gray-500">System-wide overview and pending actions</p>
        </div>
        <div className="flex gap-2">
          {isPEDesk && (
            <Button 
              variant="outline" 
              onClick={handleClearCache}
              disabled={clearingCache}
              className="text-orange-600 border-orange-300 hover:bg-orange-50"
              data-testid="pe-clear-cache-btn"
            >
              {clearingCache ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              Clear Cache
            </Button>
          )}
          <Button variant="outline" onClick={fetchData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Pending Actions Alert */}
      {data.pending_actions.total > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <AlertTriangle className="w-10 h-10 text-orange-500" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-orange-800">
                  {data.pending_actions.total} Pending Actions Require Attention
                </h3>
                <p className="text-orange-600 text-sm">
                  {data.pending_actions.bookings} bookings, {data.pending_actions.loss_approvals} loss approvals, {data.pending_actions.clients} clients, {data.pending_actions.rp_approvals} RP approvals{data.pending_actions.bp_overrides > 0 ? `, ${data.pending_actions.bp_overrides} BP overrides` : ''}
                </p>
              </div>
              <Button onClick={() => navigate('/bookings')} className="bg-orange-600 hover:bg-orange-700">
                Review Now
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/bookings')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Pending Bookings</p>
                <p className="text-3xl font-bold text-orange-600">{data.pending_actions.bookings}</p>
              </div>
              <FileText className="w-10 h-10 text-orange-200" />
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/bookings')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Loss Approvals</p>
                <p className="text-3xl font-bold text-red-600">{data.pending_actions.loss_approvals}</p>
              </div>
              <AlertTriangle className="w-10 h-10 text-red-200" />
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/clients')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Pending Clients</p>
                <p className="text-3xl font-bold text-blue-600">{data.pending_actions.clients}</p>
              </div>
              <Users className="w-10 h-10 text-blue-200" />
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/referral-partners')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">RP Approvals</p>
                <p className="text-3xl font-bold text-purple-600">{data.pending_actions.rp_approvals}</p>
              </div>
              <Briefcase className="w-10 h-10 text-purple-200" />
            </div>
          </CardContent>
        </Card>

        {/* BP Overrides Widget */}
        <Card 
          className="cursor-pointer hover:shadow-md transition-shadow border-2 border-blue-200 bg-blue-50/50" 
          onClick={() => navigate('/bookings?tab=bp-overrides')}
          data-testid="bp-overrides-widget"
        >
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-600 font-medium">BP Overrides</p>
                <p className="text-3xl font-bold text-blue-700">{data.pending_actions.bp_overrides || 0}</p>
              </div>
              <IndianRupee className="w-10 h-10 text-blue-300" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Today's Activity & User Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Today&apos;s Bookings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold text-emerald-600">{data.today_activity.bookings_created}</p>
            <p className="text-xs text-gray-500 mt-1">Bookings created today</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="w-4 h-4" />
              User Logins Today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold text-blue-600">{data.today_activity.user_logins}</p>
            <p className="text-xs text-gray-500 mt-1">Login events today</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Users className="w-4 h-4" />
              Active Users
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <p className="text-4xl font-bold text-green-600">{data.user_stats.online_users}</p>
              <p className="text-gray-500">/ {data.user_stats.total_users}</p>
            </div>
            <p className="text-xs text-gray-500 mt-1">Online in last 15 min</p>
          </CardContent>
        </Card>
      </div>

      {/* Total Bookings Value */}
      <Card className="bg-gradient-to-r from-emerald-50 to-teal-50 border-emerald-200">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-emerald-600 font-medium">Total Bookings Value</p>
              <p className="text-3xl font-bold text-emerald-800">{formatCurrency(data.total_bookings_value)}</p>
            </div>
            <TrendingUp className="w-12 h-12 text-emerald-300" />
          </div>
        </CardContent>
      </Card>

      {/* Scheduled Jobs */}
      {scheduledJobs && (
        <Card className="border-blue-200">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between text-lg">
              <span className="flex items-center gap-2">
                <CalendarClock className="w-5 h-5 text-blue-600" />
                Scheduled Jobs
              </span>
              <Badge variant="outline" className="text-blue-600">
                {scheduledJobs.timezone}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-3">
              Current time: {scheduledJobs.current_time_ist}
            </p>
            {scheduledJobs.jobs?.map((job) => (
              <div key={job.id} className="flex items-center justify-between p-3 bg-blue-50/50 rounded-lg">
                <div>
                  <p className="font-medium">{job.name}</p>
                  <p className="text-sm text-muted-foreground">
                    Next run: {new Date(job.next_run_time).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}
                  </p>
                </div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => handleTriggerJob(job.id)}
                  disabled={triggeringJob}
                  data-testid="trigger-job-btn"
                >
                  {triggeringJob ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 mr-1" />}
                  Run Now
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Recent Pending Items */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pending Bookings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Recent Pending Bookings
              </span>
              <Button variant="ghost" size="sm" onClick={() => navigate('/bookings')}>
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_pending_bookings.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Booking</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.recent_pending_bookings.map((booking) => (
                    <TableRow key={booking.id} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate('/bookings')}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{booking.booking_number}</p>
                          <p className="text-xs text-gray-500">{booking.stock_symbol}</p>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">{booking.client_name}</TableCell>
                      <TableCell>
                        <Badge className={booking.approval_status === 'pending_loss_approval' ? 'bg-red-500' : 'bg-orange-500'}>
                          {booking.approval_status === 'pending_loss_approval' ? 'Loss' : 'Pending'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="w-12 h-12 mx-auto text-green-300 mb-2" />
                <p>No pending bookings!</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pending Clients */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <UserCheck className="w-5 h-5" />
                Recent Pending Clients
              </span>
              <Button variant="ghost" size="sm" onClick={() => navigate('/clients')}>
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_pending_clients.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Client Name</TableHead>
                    <TableHead>PAN</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.recent_pending_clients.map((client) => (
                    <TableRow key={client.id} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate('/clients')}>
                      <TableCell className="font-medium">{client.name}</TableCell>
                      <TableCell className="text-sm font-mono">{client.pan_number}</TableCell>
                      <TableCell className="text-xs text-gray-500">{formatDate(client.created_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="w-12 h-12 mx-auto text-green-300 mb-2" />
                <p>No pending clients!</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default PEDashboard;
