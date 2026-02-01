import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Users, TrendingUp, FileText, Package, Building2, ShoppingCart, Boxes, BookOpen, Sparkles, ChevronRight, FileSearch, Brain, AlertTriangle, Mail, X } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import api from '../utils/api';
import { toast } from 'sonner';
import SohiniAssistant from '../components/SohiniAssistant';

const Dashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [researchStats, setResearchStats] = useState(null);
  const [recentReports, setRecentReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [smtpWarning, setSmtpWarning] = useState(null);
  const [dismissedSmtpWarning, setDismissedSmtpWarning] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);
  
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPELevel = currentUser.role === 1 || currentUser.role === 2;
  const isPEDesk = currentUser.role === 1;
  const isNotBP = currentUser.role !== 8;

  useEffect(() => {
    fetchData();
    // Check SMTP status for PE Level users
    if (isPELevel) {
      checkSmtpStatus();
    }
  }, []);

  const checkSmtpStatus = async () => {
    try {
      const response = await api.get('/email-config/status');
      if (response.data.show_warning) {
        setSmtpWarning(response.data);
      }
    } catch (error) {
      // Silently fail - don't show error for this background check
      console.log('SMTP status check failed:', error);
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
      
      // Clear local storage cache
      localStorage.removeItem('privity_cache_dashboard_stats');
      localStorage.removeItem('privity_cache_dashboard_analytics');
      
      // Refresh dashboard data
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clear cache');
    } finally {
      setClearingCache(false);
    }
  };

  const fetchData = async () => {
    try {
      // Load from cache first for faster initial render
      const cachedStats = localStorage.getItem('privity_cache_dashboard_stats');
      const cachedAnalytics = localStorage.getItem('privity_cache_dashboard_analytics');
      
      if (cachedStats) {
        try {
          const { data, expiry } = JSON.parse(cachedStats);
          if (Date.now() < expiry) setStats(data);
        } catch (e) {}
      }
      if (cachedAnalytics) {
        try {
          const { data, expiry } = JSON.parse(cachedAnalytics);
          if (Date.now() < expiry) setAnalytics(data);
        } catch (e) {}
      }
      
      const requests = [
        api.get('/dashboard/stats'),
        api.get('/dashboard/analytics'),
      ];
      
      // Fetch research data for non-BP users
      if (isNotBP) {
        requests.push(api.get('/research/stats'));
        requests.push(api.get('/research/reports?limit=5'));
      }
      
      const responses = await Promise.all(requests);
      setStats(responses[0].data);
      setAnalytics(responses[1].data);
      
      if (isNotBP && responses.length > 2) {
        setResearchStats(responses[2].data);
        setRecentReports(responses[3].data.slice(0, 3));
      }
      
      // Cache for 5 minutes
      const ttl = 5 * 60 * 1000;
      localStorage.setItem('privity_cache_dashboard_stats', JSON.stringify({
        data: responses[0].data,
        expiry: Date.now() + ttl
      }));
      localStorage.setItem('privity_cache_dashboard_analytics', JSON.stringify({
        data: responses[1].data,
        expiry: Date.now() + ttl
      }));
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !stats) {
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

  const topStocksData = analytics?.top_stocks?.slice(0, 5) || [];

  const COLORS = ['#064E3B', '#10B981', '#34D399', '#6EE7B7', '#A7F3D0'];

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="dashboard">
      {/* SMTP Warning Banner for PE Level Users */}
      {isPELevel && smtpWarning && smtpWarning.show_warning && !dismissedSmtpWarning && (
        <div 
          className="mb-6 p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg flex items-start gap-3"
          data-testid="smtp-warning-banner"
        >
          <div className="flex-shrink-0 p-2 bg-amber-100 dark:bg-amber-900/50 rounded-full">
            <Mail className="h-5 w-5 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <h3 className="font-semibold text-amber-800 dark:text-amber-200">Email Service Not Configured</h3>
            </div>
            <p className="text-sm text-amber-700 dark:text-amber-300 mb-3">
              {smtpWarning.message}
            </p>
            {isPEDesk && (
              <Button 
                size="sm" 
                variant="outline"
                className="border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-200 hover:bg-amber-100 dark:hover:bg-amber-900/50"
                onClick={() => navigate('/smtp-config')}
              >
                <Mail className="h-4 w-4 mr-2" />
                Configure Email Settings
              </Button>
            )}
          </div>
          <button 
            onClick={() => setDismissedSmtpWarning(true)}
            className="flex-shrink-0 p-1 hover:bg-amber-200 dark:hover:bg-amber-800 rounded-full transition-colors"
            aria-label="Dismiss warning"
          >
            <X className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </button>
        </div>
      )}

      <div className="mb-6 md:mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold mb-2">Dashboard</h1>
          <p className="text-muted-foreground text-sm md:text-base">Overview of your private equity system</p>
        </div>
        {isPEDesk && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearCache}
            disabled={clearingCache}
            className="text-orange-600 border-orange-300 hover:bg-orange-50"
            data-testid="clear-cache-btn"
          >
            {clearingCache ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Clear Cache
          </Button>
        )}
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

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 mb-6 md:mb-8">
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
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-3 md:gap-4 mb-6 md:mb-8">
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

      {/* Research Dashboard Section */}
      {isNotBP && (
        <div className="mb-6 md:mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BookOpen className="h-6 w-6 text-emerald-600" />
              <h2 className="text-xl font-bold">Research Center</h2>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => navigate('/research')}
              className="gap-1"
            >
              View All <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Research Stats Card */}
            <Card className="border shadow-sm bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-950/20 dark:to-background">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <FileSearch className="h-5 w-5 text-emerald-600" />
                  Research Reports
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-3xl font-bold text-emerald-600">{researchStats?.total_reports || 0}</div>
                    <div className="text-xs text-muted-foreground">Total Reports</div>
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-blue-600">{researchStats?.by_type?.analysis || 0}</div>
                    <div className="text-xs text-muted-foreground">Analysis</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* AI Research Assistant Card */}
            <Card 
              className="border shadow-sm cursor-pointer hover:shadow-md transition-shadow bg-gradient-to-br from-purple-50 to-white dark:from-purple-950/20 dark:to-background"
              onClick={() => navigate('/research')}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <Brain className="h-5 w-5 text-purple-600" />
                  AI Research Assistant
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-3">
                  Get AI-powered insights on stocks and investment analysis
                </p>
                <Button size="sm" className="w-full gap-2 bg-purple-600 hover:bg-purple-700">
                  <Sparkles className="h-4 w-4" />
                  Start Research
                </Button>
              </CardContent>
            </Card>

            {/* Recent Reports Card */}
            <Card className="border shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold">Recent Reports</CardTitle>
              </CardHeader>
              <CardContent>
                {recentReports.length > 0 ? (
                  <div className="space-y-2">
                    {recentReports.map((report, idx) => (
                      <div 
                        key={idx} 
                        className="flex items-center gap-2 p-2 rounded-md hover:bg-muted/50 cursor-pointer text-sm"
                        onClick={() => navigate('/research')}
                      >
                        <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        <span className="truncate">{report.title}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 text-muted-foreground text-sm">
                    No reports uploaded yet
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

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
            {isPELevel && (
              <button
                data-testid="quick-add-vendor"
                onClick={() => (window.location.href = '/vendors')}
                className="p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
              >
                <Building2 className="h-5 w-5 mb-2 text-purple-600" strokeWidth={1.5} />
                <div className="font-semibold text-sm">Add Vendor</div>
              </button>
            )}
            {isPELevel && (
              <button
                data-testid="quick-add-purchase"
                onClick={() => (window.location.href = '/purchases')}
                className="p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
              >
                <ShoppingCart className="h-5 w-5 mb-2 text-cyan-600" strokeWidth={1.5} />
                <div className="font-semibold text-sm">Record Purchase</div>
              </button>
            )}
            <button
              data-testid="quick-add-booking"
              onClick={() => (window.location.href = '/bookings')}
              className="p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
            >
              <FileText className="h-5 w-5 mb-2 text-orange-600" strokeWidth={1.5} />
              <div className="font-semibold text-sm">Create Booking</div>
            </button>
            {isNotBP && (
              <button
                data-testid="quick-research"
                onClick={() => navigate('/research')}
                className="p-4 text-left border rounded-md hover:bg-muted/20 transition-colors duration-200"
              >
                <BookOpen className="h-5 w-5 mb-2 text-emerald-600" strokeWidth={1.5} />
                <div className="font-semibold text-sm">Research</div>
              </button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Sohini AI Assistant Section */}
      <Card className="border shadow-sm mt-6" data-testid="sohini-assistant-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-100 to-pink-100 flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-purple-600" />
            </div>
            Ask Sohini - AI Assistant
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Get instant help with features, workflows, and questions about Privity
          </p>
        </CardHeader>
        <CardContent>
          <SohiniAssistant embedded={true} />
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;
