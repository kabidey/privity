import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { 
  Banknote, TrendingUp, TrendingDown, RefreshCw, ArrowRight,
  Wallet, CreditCard, AlertCircle, CheckCircle, Clock, IndianRupee
} from 'lucide-react';

const FinanceDashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const { hasFinanceAccess } = useCurrentUser();
  const hasAccess = hasFinanceAccess;

  useEffect(() => {
    if (!hasAccess) {
      toast.error('Access denied. Only PE Desk, PE Manager, or Finance can view this dashboard.');
      navigate('/');
      return;
    }
    fetchData();
  }, [hasAccess, navigate]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/dashboard/finance');
      setData(response.data);
    } catch (error) {
      toast.error('Failed to load finance dashboard');
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
    <div className="space-y-6" data-testid="finance-dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Banknote className="w-7 h-7 text-green-600" />
            Finance Dashboard
          </h1>
          <p className="text-gray-500">Payment tracking and financial overview</p>
        </div>
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Receivables Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="md:col-span-2 bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-green-700 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Total Receivables
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-800">{formatCurrency(data.receivables.total)}</p>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-green-600">Collection Rate</span>
                <span className="font-bold text-green-700">{data.receivables.collection_rate}%</span>
              </div>
              <Progress value={data.receivables.collection_rate} className="h-2" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              Received
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">{formatCurrency(data.receivables.received)}</p>
            <p className="text-xs text-gray-500 mt-1">Collected from clients</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
              <Clock className="w-4 h-4 text-orange-500" />
              Pending
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-orange-600">{formatCurrency(data.receivables.pending)}</p>
            <p className="text-xs text-gray-500 mt-1">Yet to be collected</p>
          </CardContent>
        </Card>
      </div>

      {/* Payables Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-blue-700 flex items-center gap-2">
              <TrendingDown className="w-4 h-4" />
              Total Payables (Vendors)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-800">{formatCurrency(data.payables.total)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              Paid to Vendors
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">{formatCurrency(data.payables.paid)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-500" />
              Pending to Vendors
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-600">{formatCurrency(data.payables.pending)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Refunds Alert */}
      {data.pending_refunds > 0 && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <AlertCircle className="w-10 h-10 text-yellow-600" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-yellow-800">
                  {data.pending_refunds} Pending Refund Request(s)
                </h3>
                <p className="text-yellow-600 text-sm">Refunds awaiting processing</p>
              </div>
              <Button variant="outline" className="border-yellow-400 text-yellow-700 hover:bg-yellow-100">
                Review Refunds
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Net Position */}
      <Card className={`${(data.receivables.received - data.payables.paid) >= 0 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Net Cash Position</p>
              <p className={`text-4xl font-bold ${(data.receivables.received - data.payables.paid) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                {formatCurrency(data.receivables.received - data.payables.paid)}
              </p>
              <p className="text-xs text-gray-500 mt-1">Received from clients - Paid to vendors</p>
            </div>
            <Wallet className={`w-16 h-16 ${(data.receivables.received - data.payables.paid) >= 0 ? 'text-green-200' : 'text-red-200'}`} />
          </div>
        </CardContent>
      </Card>

      {/* Tables */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pending Collections */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <CreditCard className="w-5 h-5" />
                Top Pending Collections
              </span>
              <Button variant="ghost" size="sm" onClick={() => navigate('/finance')}>
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.pending_collections.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Booking</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead className="text-right">Pending</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.pending_collections.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <div>
                          <p className="font-medium text-sm">{item.booking_number}</p>
                          <p className="text-xs text-gray-500">{item.stock_symbol}</p>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">{item.client_name}</TableCell>
                      <TableCell className="text-right">
                        <Badge variant="outline" className="text-red-600 border-red-200">
                          {formatCurrency(item.pending_amount)}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="w-12 h-12 mx-auto text-green-300 mb-2" />
                <p>All payments collected!</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Payments */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <IndianRupee className="w-5 h-5" />
                Recent Payments
              </span>
              <Button variant="ghost" size="sm" onClick={() => navigate('/finance')}>
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_payments.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Booking</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.recent_payments.map((payment, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <div>
                          <p className="font-medium text-sm">{payment.booking_number}</p>
                          <p className="text-xs text-gray-500">{payment.client_name}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className="bg-green-500">
                          {formatCurrency(payment.amount)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-gray-500">
                        {formatDate(payment.payment_date)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Clock className="w-12 h-12 mx-auto text-gray-300 mb-2" />
                <p>No recent payments</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default FinanceDashboard;
