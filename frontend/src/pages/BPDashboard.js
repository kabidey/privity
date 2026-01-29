import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  TrendingUp, 
  Wallet, 
  FileText, 
  DollarSign,
  CheckCircle,
  Clock,
  Building2,
  UserCheck,
  Percent,
  AlertTriangle,
  FileCheck
} from 'lucide-react';

const BPDashboard = () => {
  const [stats, setStats] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, bookingsRes] = await Promise.all([
        api.get('/business-partners/dashboard/stats'),
        api.get('/business-partners/dashboard/bookings?limit=20')
      ]);
      setStats(statsRes.data);
      setBookings(bookingsRes.data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="ios-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 page-enter" data-testid="bp-dashboard">
      {/* Welcome Header */}
      <div className="bg-gradient-to-r from-emerald-500 to-teal-500 rounded-2xl p-6 text-white">
        <div className="flex items-center gap-3 mb-2">
          <Building2 className="h-8 w-8" />
          <div>
            <h1 className="text-2xl font-bold">Welcome, {stats?.bp_name || currentUser.name}</h1>
            <p className="text-emerald-100">Business Partner Dashboard</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2 bg-white/20 rounded-lg px-3 py-1">
            <UserCheck className="h-4 w-4" />
            <span>Linked to: {stats?.linked_employee_name || 'N/A'}</span>
          </div>
          <div className="flex items-center gap-2 bg-white/20 rounded-lg px-3 py-1">
            <Percent className="h-4 w-4" />
            <span>Revenue Share: {stats?.revenue_share_percent || 0}%</span>
          </div>
          <div className={`flex items-center gap-2 rounded-lg px-3 py-1 ${stats?.documents_verified ? 'bg-green-500/30' : 'bg-amber-500/30'}`}>
            {stats?.documents_verified ? (
              <FileCheck className="h-4 w-4" />
            ) : (
              <AlertTriangle className="h-4 w-4" />
            )}
            <span>{stats?.documents_verified ? 'Documents Verified' : 'Documents Pending'}</span>
          </div>
        </div>
      </div>

      {/* Document Warning Alert */}
      {stats && !stats.documents_verified && (
        <Alert variant="destructive" className="border-amber-500 bg-amber-50 dark:bg-amber-900/20">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          <AlertTitle className="text-amber-800 dark:text-amber-300">Document Upload Required</AlertTitle>
          <AlertDescription className="text-amber-700 dark:text-amber-400">
            Please contact your PE Desk representative to complete the mandatory document uploads (PAN Card, Aadhaar Card, Cancelled Cheque). Your account features may be limited until documents are verified.
          </AlertDescription>
        </Alert>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="ios-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Bookings</p>
                <p className="text-3xl font-bold mt-1">{stats?.total_bookings || 0}</p>
              </div>
              <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-500">
                <FileText className="h-6 w-6" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="ios-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Completed</p>
                <p className="text-3xl font-bold mt-1">{stats?.completed_bookings || 0}</p>
              </div>
              <div className="p-3 rounded-xl bg-green-50 dark:bg-green-900/20 text-green-500">
                <CheckCircle className="h-6 w-6" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="ios-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Revenue</p>
                <p className="text-2xl font-bold mt-1">{formatCurrency(stats?.total_revenue)}</p>
              </div>
              <div className="p-3 rounded-xl bg-purple-50 dark:bg-purple-900/20 text-purple-500">
                <TrendingUp className="h-6 w-6" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="ios-card border-emerald-200 dark:border-emerald-800">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">Your Share</p>
                <p className="text-2xl font-bold mt-1 text-emerald-600 dark:text-emerald-400">{formatCurrency(stats?.bp_share)}</p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600">
                <Wallet className="h-6 w-6" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">SMIFS Share: {formatCurrency(stats?.smifs_share)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Revenue Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-emerald-500" />
            Revenue Breakdown
          </CardTitle>
          <CardDescription>Based on {stats?.revenue_share_percent || 0}% revenue share agreement</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
              <div>
                <p className="text-sm text-muted-foreground">Total Profit from Completed Bookings</p>
                <p className="text-xl font-bold">{formatCurrency(stats?.total_revenue)}</p>
              </div>
              <Badge variant="outline">100%</Badge>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl border border-emerald-200 dark:border-emerald-800">
                <p className="text-sm text-emerald-700 dark:text-emerald-400">Your Share ({stats?.revenue_share_percent || 0}%)</p>
                <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(stats?.bp_share)}</p>
              </div>
              
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
                <p className="text-sm text-blue-700 dark:text-blue-400">SMIFS Share ({100 - (stats?.revenue_share_percent || 0)}%)</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{formatCurrency(stats?.smifs_share)}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Bookings */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Bookings</CardTitle>
          <CardDescription>Bookings created by your linked employee</CardDescription>
        </CardHeader>
        <CardContent>
          {bookings.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No bookings yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Booking #</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Stock</TableHead>
                    <TableHead>Qty</TableHead>
                    <TableHead>Profit</TableHead>
                    <TableHead>Your Share</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bookings.map((booking) => (
                    <TableRow key={booking.id}>
                      <TableCell className="font-mono text-sm">{booking.booking_number}</TableCell>
                      <TableCell>{booking.client_name}</TableCell>
                      <TableCell className="font-semibold">{booking.stock_symbol}</TableCell>
                      <TableCell>{booking.quantity?.toLocaleString()}</TableCell>
                      <TableCell className={booking.profit >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {formatCurrency(booking.profit)}
                      </TableCell>
                      <TableCell className="font-semibold text-emerald-600">
                        {booking.status === 'completed' ? formatCurrency(booking.bp_share) : '-'}
                      </TableCell>
                      <TableCell>
                        <Badge variant={
                          booking.status === 'completed' ? 'default' :
                          booking.status === 'open' ? 'secondary' : 'outline'
                        } className={
                          booking.status === 'completed' ? 'bg-green-100 text-green-700' : ''
                        }>
                          {booking.status === 'completed' && <CheckCircle className="h-3 w-3 mr-1" />}
                          {booking.status === 'open' && <Clock className="h-3 w-3 mr-1" />}
                          {booking.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default BPDashboard;
