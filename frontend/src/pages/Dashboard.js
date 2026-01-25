import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, TrendingUp, FileText, Package, Building2, ShoppingCart, Boxes, IndianRupee } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import api from '../utils/api';
import { toast } from 'sonner';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, analyticsRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/dashboard/analytics'),
      ]);
      setStats(statsRes.data);
      setAnalytics(analyticsRes.data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="text-muted-foreground">Loading dashboard...</div>
      </div>
    );
  }

  const statCards = [
    { title: 'Total Clients', value: stats?.total_clients || 0, icon: Users, color: 'text-blue-600' },
    { title: 'Total Vendors', value: stats?.total_vendors || 0, icon: Building2, color: 'text-purple-600' },
    { title: 'Total Stocks', value: stats?.total_stocks || 0, icon: Package, color: 'text-indigo-600' },
    { title: 'Total Purchases', value: stats?.total_purchases || 0, icon: ShoppingCart, color: 'text-cyan-600' },
    { title: 'Total Bookings', value: stats?.total_bookings || 0, icon: FileText, color: 'text-orange-600' },
    { title: 'Open Bookings', value: stats?.open_bookings || 0, icon: TrendingUp, color: 'text-green-600' },
  ];

  const formatMonth = (monthStr) => {
    const [year, month] = monthStr.split('-');
    const date = new Date(year, parseInt(month) - 1);
    return date.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' });
  };

  const chartData = analytics?.monthly_pnl?.map(item => ({
    month: formatMonth(item.month),
    pnl: item.pnl,
  })) || [];

  const topStocksData = analytics?.top_stocks?.slice(0, 5) || [];

  const COLORS = ['#064E3B', '#10B981', '#34D399', '#6EE7B7', '#A7F3D0'];

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="dashboard">
      <div className="mb-6 md:mb-8">
        <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted-foreground text-sm md:text-base">Overview of your private equity system</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 md:gap-4 mb-6 md:mb-8">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index} className="stat-card border shadow-sm" data-testid={`stat-card-${index}`}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {stat.title}
                </CardTitle>
                <Icon className={`h-4 w-4 ${stat.color}`} strokeWidth={1.5} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold mono">{stat.value}</div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Revenue Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4 mb-6 md:mb-8">
        <Card className="border shadow-sm" data-testid="inventory-value-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs md:text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Boxes className="h-4 w-4" />
              Inventory Value
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl md:text-2xl lg:text-3xl font-bold mono text-primary">
              ₹{(stats?.total_inventory_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="closed-bookings-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs md:text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Closed Bookings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl md:text-2xl lg:text-3xl font-bold mono">{stats?.closed_bookings || 0}</div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="pnl-summary-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs md:text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <IndianRupee className="h-4 w-4" />
              Total Revenue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-xl md:text-2xl lg:text-3xl font-bold mono ${(stats?.total_profit_loss || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              ₹{(stats?.total_profit_loss || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-4 mb-6 md:mb-8">
        {/* Revenue Trend Chart */}
        <Card className="border shadow-sm" data-testid="pnl-chart-card">
          <CardHeader>
            <CardTitle className="text-xl font-bold">Revenue Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#064E3B" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#064E3B" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis 
                    dataKey="month" 
                    tick={{ fontSize: 12 }} 
                    tickLine={false}
                    axisLine={{ stroke: '#e5e7eb' }}
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }} 
                    tickLine={false}
                    axisLine={{ stroke: '#e5e7eb' }}
                    tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`}
                  />
                  <Tooltip 
                    formatter={(value) => [`₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`, 'Revenue']}
                    contentStyle={{ 
                      backgroundColor: 'white', 
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="pnl" 
                    stroke="#064E3B" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorPnl)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-muted-foreground">
                No Revenue data available yet
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Performing Stocks */}
        <Card className="border shadow-sm" data-testid="top-stocks-card">
          <CardHeader>
            <CardTitle className="text-xl font-bold">Top Performing Stocks</CardTitle>
          </CardHeader>
          <CardContent>
            {topStocksData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={topStocksData} layout="vertical" margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                  <XAxis 
                    type="number" 
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={{ stroke: '#e5e7eb' }}
                    tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`}
                  />
                  <YAxis 
                    type="category" 
                    dataKey="stock_symbol" 
                    tick={{ fontSize: 12, fontWeight: 600 }}
                    tickLine={false}
                    axisLine={{ stroke: '#e5e7eb' }}
                    width={80}
                  />
                  <Tooltip 
                    formatter={(value) => [`₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`, 'Revenue']}
                    contentStyle={{ 
                      backgroundColor: 'white', 
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}
                  />
                  <Bar dataKey="pnl" radius={[0, 4, 4, 0]}>
                    {topStocksData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-muted-foreground">
                No stock performance data available yet
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="border shadow-sm" data-testid="quick-actions-card">
        <CardHeader>
          <CardTitle className="text-xl font-bold">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <button
              data-testid="quick-add-client"
              onClick={() => (window.location.href = '/clients')}
              className="p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
            >
              <Users className="h-5 w-5 mb-2 text-blue-600" strokeWidth={1.5} />
              <div className="font-semibold text-sm">Add Client</div>
            </button>
            <button
              data-testid="quick-add-vendor"
              onClick={() => (window.location.href = '/vendors')}
              className="p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
            >
              <Building2 className="h-5 w-5 mb-2 text-purple-600" strokeWidth={1.5} />
              <div className="font-semibold text-sm">Add Vendor</div>
            </button>
            <button
              data-testid="quick-add-purchase"
              onClick={() => (window.location.href = '/purchases')}
              className="p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
            >
              <ShoppingCart className="h-5 w-5 mb-2 text-cyan-600" strokeWidth={1.5} />
              <div className="font-semibold text-sm">Record Purchase</div>
            </button>
            <button
              data-testid="quick-add-booking"
              onClick={() => (window.location.href = '/bookings')}
              className="p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
            >
              <FileText className="h-5 w-5 mb-2 text-orange-600" strokeWidth={1.5} />
              <div className="font-semibold text-sm">Create Booking</div>
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;
