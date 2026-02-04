import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '../utils/api';
import { useProtectedPage } from '../hooks/useProtectedPage';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart
} from 'recharts';
import {
  TrendingUp, TrendingDown, Users, FileText, DollarSign,
  PieChartIcon, BarChart3, Activity, Award, Briefcase
} from 'lucide-react';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

const Analytics = () => {
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState('30');
  const [summary, setSummary] = useState(null);
  const [stockPerformance, setStockPerformance] = useState([]);
  const [employeePerformance, setEmployeePerformance] = useState([]);
  const [dailyTrend, setDailyTrend] = useState([]);
  const [sectorDistribution, setSectorDistribution] = useState([]);

  const { isLoading, isAuthorized, hasPermission } = useProtectedPage({
    allowIf: ({ isPELevel, hasPermission }) => isPELevel || hasPermission('analytics.view'),
    deniedMessage: 'Access denied. You need Analytics permission to access this page.'
  });

  useEffect(() => {
    if (!isAuthorized) return;
    fetchAnalytics();
  }, [days, isAuthorized]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [summaryRes, stockRes, empRes, trendRes, sectorRes] = await Promise.all([
        api.get(`/analytics/summary?days=${days}`),
        api.get(`/analytics/stock-performance?days=${days}&limit=10`),
        api.get(`/analytics/employee-performance?days=${days}&limit=10`),
        api.get(`/analytics/daily-trend?days=${days}`),
        api.get('/analytics/sector-distribution')
      ]);

      setSummary(summaryRes.data);
      setStockPerformance(stockRes.data);
      setEmployeePerformance(empRes.data);
      setDailyTrend(trendRes.data);
      setSectorDistribution(sectorRes.data);
    } catch (error) {
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(value);
  };

  // Show loading while checking permissions
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 space-y-6" data-testid="analytics-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Advanced Analytics</h1>
          <p className="text-muted-foreground">Comprehensive business insights</p>
        </div>
        <Select value={days} onValueChange={setDays}>
          <SelectTrigger className="w-40" data-testid="days-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
            <SelectItem value="365">Last year</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-green-500" />
              <span className="text-xs text-muted-foreground">Revenue</span>
            </div>
            <p className="text-xl font-bold">{formatCurrency(summary?.total_revenue || 0)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              {(summary?.total_profit || 0) >= 0 ? (
                <TrendingUp className="h-4 w-4 text-green-500" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-500" />
              )}
              <span className="text-xs text-muted-foreground">Profit</span>
            </div>
            <p className={`text-xl font-bold ${(summary?.total_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(summary?.total_profit || 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-500" />
              <span className="text-xs text-muted-foreground">Bookings</span>
            </div>
            <p className="text-xl font-bold">{summary?.total_bookings || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-purple-500" />
              <span className="text-xs text-muted-foreground">Clients</span>
            </div>
            <p className="text-xl font-bold">{summary?.total_clients || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-orange-500" />
              <span className="text-xs text-muted-foreground">Avg Booking</span>
            </div>
            <p className="text-xl font-bold">{formatCurrency(summary?.avg_booking_value || 0)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-cyan-500" />
              <span className="text-xs text-muted-foreground">Margin</span>
            </div>
            <p className={`text-xl font-bold ${(summary?.profit_margin || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {(summary?.profit_margin || 0).toFixed(1)}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Daily Trend */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Daily Trend
            </CardTitle>
            <CardDescription>Bookings and profit over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={dailyTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(v) => new Date(v).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                  fontSize={12}
                />
                <YAxis fontSize={12} />
                <Tooltip 
                  formatter={(value, name) => [
                    name === 'profit_loss' || name === 'bookings_value' ? formatCurrency(value) : value,
                    name === 'bookings_count' ? 'Bookings' : name === 'profit_loss' ? 'Profit/Loss' : 'Value'
                  ]}
                  labelFormatter={(v) => new Date(v).toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short' })}
                />
                <Legend />
                <Area type="monotone" dataKey="bookings_value" stackId="1" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} name="Value" />
                <Area type="monotone" dataKey="profit_loss" stackId="2" stroke="#10b981" fill="#10b981" fillOpacity={0.3} name="Profit" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Sector Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChartIcon className="h-5 w-5" />
              Sector Distribution
            </CardTitle>
            <CardDescription>Revenue by sector</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={sectorDistribution}
                  dataKey="total_value"
                  nameKey="sector"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ sector, percent }) => `${sector} (${(percent * 100).toFixed(0)}%)`}
                >
                  {sectorDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatCurrency(value)} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Stocks */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Briefcase className="h-5 w-5" />
              Top Performing Stocks
            </CardTitle>
            <CardDescription>By profit generated</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={stockPerformance} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} fontSize={12} />
                <YAxis type="category" dataKey="stock_symbol" width={80} fontSize={12} />
                <Tooltip formatter={(value) => formatCurrency(value)} />
                <Legend />
                <Bar dataKey="profit_loss" fill="#10b981" name="Profit" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Top Employees */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="h-5 w-5" />
              Top Employees
            </CardTitle>
            <CardDescription>By profit generated</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={employeePerformance} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} fontSize={12} />
                <YAxis type="category" dataKey="user_name" width={100} fontSize={12} />
                <Tooltip formatter={(value) => formatCurrency(value)} />
                <Legend />
                <Bar dataKey="total_profit" fill="#3b82f6" name="Profit" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Tables */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Stock Performance Table */}
        <Card>
          <CardHeader>
            <CardTitle>Stock Performance Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {stockPerformance.map((stock, idx) => (
                <div key={stock.stock_id} className="flex items-center justify-between p-2 rounded hover:bg-muted">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-muted-foreground">{idx + 1}</span>
                    <div>
                      <p className="font-medium">{stock.stock_symbol}</p>
                      <p className="text-xs text-muted-foreground">{stock.sector}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`font-semibold ${stock.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(stock.profit_loss)}
                    </p>
                    <Badge variant={stock.profit_margin >= 0 ? 'default' : 'destructive'} className="text-xs">
                      {stock.profit_margin.toFixed(1)}%
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Employee Performance Table */}
        <Card>
          <CardHeader>
            <CardTitle>Employee Performance Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {employeePerformance.map((emp, idx) => (
                <div key={emp.user_id} className="flex items-center justify-between p-2 rounded hover:bg-muted">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-muted-foreground">{idx + 1}</span>
                    <div>
                      <p className="font-medium">{emp.user_name}</p>
                      <p className="text-xs text-muted-foreground">{emp.role_name} • {emp.clients_count} clients</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`font-semibold ${emp.total_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(emp.total_profit)}
                    </p>
                    <p className="text-xs text-muted-foreground">{emp.total_bookings} bookings</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Analytics;
