import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '../utils/api';
import { ArrowLeft, User, TrendingUp, TrendingDown, FileText, IndianRupee } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

const ClientPortfolio = () => {
  const { clientId } = useParams();
  const navigate = useNavigate();
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPortfolio();
  }, [clientId]);

  const fetchPortfolio = async () => {
    try {
      const response = await api.get(`/clients/${clientId}/portfolio`);
      setPortfolio(response.data);
    } catch (error) {
      toast.error('Failed to load portfolio');
      navigate('/clients');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="text-muted-foreground">Loading portfolio...</div>
      </div>
    );
  }

  if (!portfolio) {
    return null;
  }

  // Prepare chart data for stock distribution
  const stockDistribution = portfolio.bookings.reduce((acc, booking) => {
    const existing = acc.find(s => s.stock_symbol === booking.stock_symbol);
    if (existing) {
      existing.value += booking.quantity;
    } else {
      acc.push({ stock_symbol: booking.stock_symbol, value: booking.quantity });
    }
    return acc;
  }, []);

  const COLORS = ['#064E3B', '#10B981', '#34D399', '#6EE7B7', '#A7F3D0', '#D97706', '#F59E0B'];

  return (
    <div className="p-8 page-enter" data-testid="client-portfolio-page">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/clients')}
          data-testid="back-button"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Clients
        </Button>
      </div>

      {/* Client Info */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
          <User className="h-8 w-8 text-primary" strokeWidth={1.5} />
        </div>
        <div>
          <h1 className="text-4xl font-bold">{portfolio.client_name}</h1>
          <p className="text-muted-foreground text-base">Client Portfolio Overview</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card className="border shadow-sm" data-testid="total-bookings-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Total Bookings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono">{portfolio.total_bookings}</div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="open-bookings-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-blue-600" />
              Open Positions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono text-blue-600">{portfolio.open_bookings}</div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="closed-bookings-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Closed Positions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono">{portfolio.closed_bookings}</div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="total-pnl-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <IndianRupee className="h-4 w-4" />
              Total P&L
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold mono ${portfolio.total_profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {portfolio.total_profit_loss >= 0 ? (
                <TrendingUp className="inline h-6 w-6 mr-1" />
              ) : (
                <TrendingDown className="inline h-6 w-6 mr-1" />
              )}
              ₹{Math.abs(portfolio.total_profit_loss).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts and Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        {/* Stock Distribution Chart */}
        <Card className="border shadow-sm" data-testid="stock-distribution-card">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Stock Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {stockDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={stockDistribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    fill="#8884d8"
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="stock_symbol"
                    label={({ stock_symbol }) => stock_symbol}
                  >
                    {stockDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value) => [`${value} units`, 'Quantity']}
                    contentStyle={{ 
                      backgroundColor: 'white', 
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                No stock data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Bookings Table - spans 2 columns */}
        <Card className="border shadow-sm lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Booking History</CardTitle>
          </CardHeader>
          <CardContent>
            {portfolio.bookings.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                No bookings found for this client
              </div>
            ) : (
              <div className="overflow-x-auto max-h-[300px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs uppercase tracking-wider font-semibold">Stock</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider font-semibold">Qty</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider font-semibold">Buy</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider font-semibold">Sell</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider font-semibold">Status</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider font-semibold">P&L</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {portfolio.bookings.map((booking) => (
                      <TableRow key={booking.id} className="table-row" data-testid="portfolio-booking-row">
                        <TableCell className="font-bold mono">{booking.stock_symbol}</TableCell>
                        <TableCell className="mono">{booking.quantity}</TableCell>
                        <TableCell className="mono text-sm">₹{booking.buying_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</TableCell>
                        <TableCell className="mono text-sm">
                          {booking.selling_price ? `₹${booking.selling_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}
                        </TableCell>
                        <TableCell>
                          <Badge variant={booking.status === 'open' ? 'default' : 'secondary'}>
                            {booking.status.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="mono font-semibold">
                          {booking.profit_loss !== null && booking.profit_loss !== undefined ? (
                            <span className={booking.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}>
                              ₹{booking.profit_loss.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </span>
                          ) : (
                            '-'
                          )}
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
    </div>
  );
};

export default ClientPortfolio;
