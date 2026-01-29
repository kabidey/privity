import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  User, Wallet, TrendingUp, TrendingDown, FileText, RefreshCw,
  IndianRupee, PieChart, Clock, CheckCircle, AlertCircle, Package
} from 'lucide-react';

const ClientDashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    if (currentUser.role !== 6) {
      // Not a client - redirect to regular dashboard
      navigate('/');
      return;
    }
    fetchData();
  }, [currentUser.role, navigate]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/dashboard/client');
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div className="p-8 text-center">
        <AlertCircle className="w-16 h-16 mx-auto text-gray-300 mb-4" />
        <h2 className="text-xl font-semibold text-gray-700 mb-2">No Client Profile Found</h2>
        <p className="text-gray-500">{data?.error || 'Please contact support to link your account.'}</p>
      </div>
    );
  }

  const profitLoss = data.portfolio_summary.profit_loss;
  const profitLossPercent = data.portfolio_summary.total_invested > 0 
    ? ((profitLoss / data.portfolio_summary.total_invested) * 100).toFixed(2) 
    : 0;

  return (
    <div className="space-y-6" data-testid="client-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <User className="w-7 h-7 text-emerald-600" />
            Welcome, {data.client_info.name}
          </h1>
          <div className="flex items-center gap-3 mt-1">
            <Badge variant="outline" className="text-sm">OTC UCC: {data.client_info.otc_ucc || 'Pending'}</Badge>
            <Badge variant="outline" className="text-sm">PAN: {data.client_info.pan_number}</Badge>
            <Badge className={data.client_info.approval_status === 'approved' ? 'bg-green-500' : 'bg-orange-500'}>
              {data.client_info.approval_status}
            </Badge>
          </div>
        </div>
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Portfolio Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-blue-700 flex items-center gap-2">
              <Wallet className="w-4 h-4" />
              Total Invested
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-800">{formatCurrency(data.portfolio_summary.total_invested)}</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-emerald-50 to-green-50 border-emerald-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-emerald-700 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Current Value
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-emerald-800">{formatCurrency(data.portfolio_summary.current_value)}</p>
          </CardContent>
        </Card>

        <Card className={`bg-gradient-to-br ${profitLoss >= 0 ? 'from-green-50 to-emerald-50 border-green-200' : 'from-red-50 to-pink-50 border-red-200'}`}>
          <CardHeader className="pb-2">
            <CardTitle className={`text-sm flex items-center gap-2 ${profitLoss >= 0 ? 'text-green-700' : 'text-red-700'}`}>
              {profitLoss >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {profitLoss >= 0 ? 'Profit' : 'Loss'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${profitLoss >= 0 ? 'text-green-800' : 'text-red-800'}`}>
              {formatCurrency(Math.abs(profitLoss))}
            </p>
            <p className={`text-xs ${profitLoss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {profitLoss >= 0 ? '+' : '-'}{Math.abs(profitLossPercent)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-600 flex items-center gap-2">
              <Package className="w-4 h-4" />
              Stocks Held
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-gray-800">{data.portfolio_summary.stocks_count}</p>
          </CardContent>
        </Card>
      </div>

      {/* Booking & Payment Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-gray-800">{data.booking_summary.total}</p>
              <p className="text-xs text-gray-500">Total Bookings</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-blue-600">{data.booking_summary.open}</p>
              <p className="text-xs text-gray-500">Open</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-green-600">{data.booking_summary.closed}</p>
              <p className="text-xs text-gray-500">Closed</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-orange-600">{data.booking_summary.awaiting_confirmation}</p>
              <p className="text-xs text-gray-500">Awaiting Confirm</p>
            </div>
          </CardContent>
        </Card>
        <Card className={data.payment_summary.pending > 0 ? 'border-red-200 bg-red-50' : ''}>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className={`text-xl font-bold ${data.payment_summary.pending > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {formatCurrency(data.payment_summary.pending)}
              </p>
              <p className="text-xs text-gray-500">Payment Pending</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Portfolio Holdings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChart className="w-5 h-5" />
            My Portfolio Holdings
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.portfolio.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Stock</TableHead>
                    <TableHead className="text-right">Quantity</TableHead>
                    <TableHead className="text-right">Avg. Price</TableHead>
                    <TableHead className="text-right">Total Invested</TableHead>
                    <TableHead className="text-right">Current Value</TableHead>
                    <TableHead className="text-right">P&L</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.portfolio.map((holding, index) => {
                    const pnl = holding.current_value - holding.total_invested;
                    const pnlPercent = holding.total_invested > 0 ? ((pnl / holding.total_invested) * 100).toFixed(2) : 0;
                    return (
                      <TableRow key={index}>
                        <TableCell>
                          <div>
                            <p className="font-bold">{holding.stock_symbol}</p>
                            <p className="text-xs text-gray-500">{holding.stock_name}</p>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-medium">{holding.total_quantity}</TableCell>
                        <TableCell className="text-right">{formatCurrency(holding.avg_price)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(holding.total_invested)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(holding.current_value)}</TableCell>
                        <TableCell className="text-right">
                          <div className={pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                            <p className="font-bold">{formatCurrency(pnl)}</p>
                            <p className="text-xs">{pnl >= 0 ? '+' : ''}{pnlPercent}%</p>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Package className="w-12 h-12 mx-auto text-gray-300 mb-2" />
              <p>No holdings yet</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Bookings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Recent Bookings
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.recent_bookings.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Booking #</TableHead>
                    <TableHead>Stock</TableHead>
                    <TableHead className="text-right">Quantity</TableHead>
                    <TableHead className="text-right">Price</TableHead>
                    <TableHead className="text-right">Value</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.recent_bookings.map((booking) => (
                    <TableRow key={booking.id}>
                      <TableCell className="font-medium">{booking.booking_number}</TableCell>
                      <TableCell>{booking.stock_symbol}</TableCell>
                      <TableCell className="text-right">{booking.quantity}</TableCell>
                      <TableCell className="text-right">{formatCurrency(booking.buying_price)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(booking.quantity * booking.buying_price)}</TableCell>
                      <TableCell>{getStatusBadge(booking.status)}</TableCell>
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
            </div>
          )}
        </CardContent>
      </Card>

      {/* Payment Summary Card */}
      <Card className="bg-gradient-to-r from-gray-50 to-slate-50">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 font-medium">Total Payments Made</p>
              <p className="text-3xl font-bold text-gray-800">{formatCurrency(data.payment_summary.total_paid)}</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600 font-medium">Outstanding</p>
              <p className={`text-3xl font-bold ${data.payment_summary.pending > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {formatCurrency(data.payment_summary.pending)}
              </p>
            </div>
            <IndianRupee className="w-16 h-16 text-gray-200" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ClientDashboard;
