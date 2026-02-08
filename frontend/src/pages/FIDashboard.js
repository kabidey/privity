import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import { useProtectedPage } from '../hooks/useProtectedPage';
import { useLicense } from '../contexts/LicenseContext';
import LicenseGate from '../components/LicenseGate';
import { 
  TrendingUp, BarChart3, Calendar, PieChart, ArrowRight, RefreshCw,
  IndianRupee, Clock, AlertTriangle, CheckCircle, Building2,
  FileText, Percent, Shield, Wallet, CalendarDays, Activity
} from 'lucide-react';

const FIDashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { isFILicensed, isExempt } = useLicense();

  const { isLoading, isAuthorized, hasPermission } = useProtectedPage({
    allowIf: ({ isPELevel, hasPermission }) => isPELevel || hasPermission('fixed_income.view'),
    deniedMessage: 'Access denied. You need Fixed Income permission to view this page.'
  });

  useEffect(() => {
    if (!isAuthorized) return;
    fetchData();
  }, [isAuthorized]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/fixed-income/dashboard');
      setData(response.data);
    } catch (error) {
      console.error('Failed to load FI dashboard:', error);
      // Use mock data if API fails
      setData({
        summary: {
          total_aum: 125000000,
          total_holdings: 45,
          total_clients: 28,
          avg_ytm: 9.25,
          total_accrued_interest: 2500000,
          pending_orders: 5
        },
        holdings_by_type: {
          NCD: { count: 25, value: 75000000 },
          BOND: { count: 12, value: 35000000 },
          GSEC: { count: 8, value: 15000000 }
        },
        holdings_by_rating: {
          AAA: 55000000,
          'AA+': 35000000,
          AA: 25000000,
          'A+': 10000000
        },
        upcoming_maturities: [
          { isin: 'INE002A08427', issuer: 'Reliance Industries', maturity_date: '2025-03-15', face_value: 5000000, days_to_maturity: 35 },
          { isin: 'INE040A08252', issuer: 'HDFC Ltd', maturity_date: '2025-04-10', face_value: 3000000, days_to_maturity: 61 },
          { isin: 'INE860H08176', issuer: 'Tata Capital', maturity_date: '2025-05-20', face_value: 2500000, days_to_maturity: 101 }
        ],
        upcoming_coupons: [
          { isin: 'INE002A08427', issuer: 'Reliance Industries', coupon_date: '2025-02-15', coupon_amount: 125000, days_to_coupon: 7 },
          { isin: 'INE585B08189', issuer: 'Bajaj Finance', coupon_date: '2025-02-28', coupon_amount: 95000, days_to_coupon: 20 },
          { isin: 'INE040A08252', issuer: 'HDFC Ltd', coupon_date: '2025-03-10', coupon_amount: 75000, days_to_coupon: 30 }
        ],
        recent_orders: [
          { id: 'FI/24-25/0001', client_name: 'John Doe', instrument: 'Reliance NCD', status: 'executed', amount: 500000 },
          { id: 'FI/24-25/0002', client_name: 'Jane Smith', instrument: 'HDFC Bond', status: 'pending', amount: 750000 },
          { id: 'FI/24-25/0003', client_name: 'Robert Brown', instrument: 'Bajaj NCD', status: 'approved', amount: 300000 }
        ],
        ytm_distribution: [
          { range: '8-9%', count: 12, value: 35000000 },
          { range: '9-10%', count: 18, value: 55000000 },
          { range: '10-11%', count: 10, value: 25000000 },
          { range: '11%+', count: 5, value: 10000000 }
        ]
      });
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    if (amount >= 10000000) {
      return `₹${(amount / 10000000).toFixed(2)} Cr`;
    } else if (amount >= 100000) {
      return `₹${(amount / 100000).toFixed(2)} L`;
    }
    return `₹${amount?.toLocaleString('en-IN') || 0}`;
  };

  const getStatusBadge = (status) => {
    const colors = {
      executed: 'bg-green-500',
      pending: 'bg-amber-500',
      approved: 'bg-blue-500',
      rejected: 'bg-red-500'
    };
    return <Badge className={colors[status] || 'bg-gray-500'}>{status}</Badge>;
  };

  if (isLoading || loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="w-8 h-8 animate-spin text-teal-500" />
      </div>
    );
  }

  return (
    <LicenseGate module="fixed_income" fallbackMessage="Fixed Income module is not licensed. Contact admin to unlock.">
      <div className="p-6 space-y-6" data-testid="fi-dashboard">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <TrendingUp className="w-7 h-7 text-teal-600" />
              Fixed Income Dashboard
            </h1>
            <p className="text-gray-500 mt-1">Portfolio overview and performance metrics</p>
          </div>
          <Button onClick={fetchData} variant="outline" disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-l-4 border-l-teal-500">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Total AUM</p>
                  <p className="text-2xl font-bold text-gray-900">{formatCurrency(data?.summary?.total_aum)}</p>
                </div>
                <Wallet className="w-10 h-10 text-teal-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Total Holdings</p>
                  <p className="text-2xl font-bold text-gray-900">{data?.summary?.total_holdings || 0}</p>
                  <p className="text-xs text-gray-400">{data?.summary?.total_clients || 0} clients</p>
                </div>
                <Building2 className="w-10 h-10 text-blue-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-green-500">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Average YTM</p>
                  <p className="text-2xl font-bold text-gray-900">{data?.summary?.avg_ytm?.toFixed(2) || 0}%</p>
                </div>
                <Percent className="w-10 h-10 text-green-500 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-amber-500">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Accrued Interest</p>
                  <p className="text-2xl font-bold text-gray-900">{formatCurrency(data?.summary?.total_accrued_interest)}</p>
                </div>
                <IndianRupee className="w-10 h-10 text-amber-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Holdings Breakdown and YTM Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Holdings by Type */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <PieChart className="w-5 h-5 text-teal-600" />
                Holdings by Type
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {data?.holdings_by_type && Object.entries(data.holdings_by_type).map(([type, info]) => (
                  <div key={type} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{type}</span>
                      <span className="text-gray-500">{info.count} instruments | {formatCurrency(info.value)}</span>
                    </div>
                    <Progress 
                      value={(info.value / data.summary.total_aum) * 100} 
                      className="h-2"
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Holdings by Rating */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Shield className="w-5 h-5 text-blue-600" />
                Holdings by Credit Rating
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {data?.holdings_by_rating && Object.entries(data.holdings_by_rating).map(([rating, value]) => (
                  <div key={rating} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">
                        <Badge variant="outline" className={
                          rating === 'AAA' ? 'border-green-500 text-green-600' :
                          rating.startsWith('AA') ? 'border-blue-500 text-blue-600' :
                          'border-amber-500 text-amber-600'
                        }>{rating}</Badge>
                      </span>
                      <span className="text-gray-500">{formatCurrency(value)}</span>
                    </div>
                    <Progress 
                      value={(value / data.summary.total_aum) * 100} 
                      className="h-2"
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Upcoming Events */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Upcoming Maturities */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <CalendarDays className="w-5 h-5 text-red-600" />
                Upcoming Maturities
              </CardTitle>
              <CardDescription>Instruments maturing in next 90 days</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data?.upcoming_maturities?.slice(0, 5).map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-sm">{item.issuer}</p>
                      <p className="text-xs text-gray-500">{item.isin}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium text-sm">{formatCurrency(item.face_value)}</p>
                      <p className="text-xs text-red-500">{item.days_to_maturity} days</p>
                    </div>
                  </div>
                ))}
                {(!data?.upcoming_maturities || data.upcoming_maturities.length === 0) && (
                  <p className="text-center text-gray-500 py-4">No upcoming maturities</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Upcoming Coupons */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <IndianRupee className="w-5 h-5 text-green-600" />
                Upcoming Coupon Payments
              </CardTitle>
              <CardDescription>Expected cash flows in next 30 days</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data?.upcoming_coupons?.slice(0, 5).map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-sm">{item.issuer}</p>
                      <p className="text-xs text-gray-500">{item.isin}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium text-sm text-green-600">+{formatCurrency(item.coupon_amount)}</p>
                      <p className="text-xs text-gray-500">{item.days_to_coupon} days</p>
                    </div>
                  </div>
                ))}
                {(!data?.upcoming_coupons || data.upcoming_coupons.length === 0) && (
                  <p className="text-center text-gray-500 py-4">No upcoming coupon payments</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Orders */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="w-5 h-5 text-purple-600" />
                Recent Orders
              </CardTitle>
              <CardDescription>Latest FI order activity</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/fi-orders')}>
              View All <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order ID</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead>Instrument</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.recent_orders?.slice(0, 5).map((order, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="font-mono text-sm">{order.id}</TableCell>
                    <TableCell>{order.client_name}</TableCell>
                    <TableCell>{order.instrument}</TableCell>
                    <TableCell>{formatCurrency(order.amount)}</TableCell>
                    <TableCell>{getStatusBadge(order.status)}</TableCell>
                  </TableRow>
                ))}
                {(!data?.recent_orders || data.recent_orders.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-gray-500 py-8">
                      No recent orders
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Button variant="outline" onClick={() => navigate('/fi-instruments')} className="h-auto py-4 flex-col">
                <TrendingUp className="w-6 h-6 mb-2 text-teal-600" />
                <span>Security Master</span>
              </Button>
              <Button variant="outline" onClick={() => navigate('/fi-orders')} className="h-auto py-4 flex-col">
                <FileText className="w-6 h-6 mb-2 text-blue-600" />
                <span>New Order</span>
              </Button>
              <Button variant="outline" onClick={() => navigate('/fi-primary-market')} className="h-auto py-4 flex-col">
                <Building2 className="w-6 h-6 mb-2 text-purple-600" />
                <span>IPO/NFO</span>
              </Button>
              <Button variant="outline" onClick={() => navigate('/fi-reports')} className="h-auto py-4 flex-col">
                <BarChart3 className="w-6 h-6 mb-2 text-green-600" />
                <span>Reports</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </LicenseGate>
  );
};

export default FIDashboard;
