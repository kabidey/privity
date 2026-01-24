import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, TrendingUp, FileText, Package } from 'lucide-react';
import api from '../utils/api';
import { toast } from 'sonner';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await api.get('/dashboard/stats');
      setStats(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard stats');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  const statCards = [
    {
      title: 'Total Clients',
      value: stats?.total_clients || 0,
      icon: Users,
      color: 'text-blue-600',
    },
    {
      title: 'Total Stocks',
      value: stats?.total_stocks || 0,
      icon: Package,
      color: 'text-purple-600',
    },
    {
      title: 'Total Bookings',
      value: stats?.total_bookings || 0,
      icon: FileText,
      color: 'text-orange-600',
    },
    {
      title: 'Open Bookings',
      value: stats?.open_bookings || 0,
      icon: TrendingUp,
      color: 'text-green-600',
    },
  ];

  return (
    <div className="p-8 page-enter" data-testid="dashboard">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted-foreground text-base">Overview of your share booking system</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index} className="stat-card border shadow-sm" data-testid={`stat-card-${index}`}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                  {stat.title}
                </CardTitle>
                <Icon className={`h-5 w-5 ${stat.color}`} strokeWidth={1.5} />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold mono">{stat.value}</div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="border shadow-sm" data-testid="pnl-summary-card">
          <CardHeader>
            <CardTitle className="text-xl font-bold">Profit & Loss Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-4 bg-secondary/30 rounded-md">
                <span className="text-sm font-medium">Total Closed Bookings</span>
                <span className="text-2xl font-bold mono">{stats?.closed_bookings || 0}</span>
              </div>
              <div className="flex justify-between items-center p-4 bg-secondary/30 rounded-md">
                <span className="text-sm font-medium">Total P&L</span>
                <span className={`text-2xl font-bold mono ${stats?.total_profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  ₹{stats?.total_profit_loss?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="quick-actions-card">
          <CardHeader>
            <CardTitle className="text-xl font-bold">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <button
                data-testid="quick-add-client"
                onClick={() => (window.location.href = '/clients')}
                className="w-full p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
              >
                <div className="font-semibold">Add New Client</div>
                <div className="text-sm text-muted-foreground">Register a new client</div>
              </button>
              <button
                data-testid="quick-add-booking"
                onClick={() => (window.location.href = '/bookings')}
                className="w-full p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
              >
                <div className="font-semibold">Create Booking</div>
                <div className="text-sm text-muted-foreground">Book shares for a client</div>
              </button>
              <button
                data-testid="quick-view-reports"
                onClick={() => (window.location.href = '/reports')}
                className="w-full p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
              >
                <div className="font-semibold">View Reports</div>
                <div className="text-sm text-muted-foreground">Check P&L reports</div>
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
