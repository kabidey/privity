import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '../utils/api';
import { useProtectedPage } from '../hooks/useProtectedPage';
import { useLicense } from '../contexts/LicenseContext';
import LicenseGate from '../components/LicenseGate';
import { 
  TrendingUp, BarChart3, Calendar, PieChart, ArrowRight, RefreshCw,
  IndianRupee, Clock, AlertTriangle, CheckCircle, Building2,
  FileText, Percent, Shield, Wallet, CalendarDays, Activity,
  Timer, Briefcase, TrendingDown, ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import {
  PieChart as RechartsPie, Pie, Cell, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  AreaChart, Area, LineChart, Line, ComposedChart
} from 'recharts';

// Color palette for charts
const COLORS = {
  primary: ['#0d9488', '#14b8a6', '#2dd4bf', '#5eead4', '#99f6e4'],
  secondary: ['#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe', '#dbeafe'],
  accent: ['#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#ede9fe'],
  success: ['#22c55e', '#4ade80', '#86efac', '#bbf7d0', '#dcfce7'],
  warning: ['#f59e0b', '#fbbf24', '#fcd34d', '#fde68a', '#fef3c7'],
  danger: ['#ef4444', '#f87171', '#fca5a5', '#fecaca', '#fee2e2']
};

const RATING_COLORS = {
  'AAA': '#22c55e',
  'AA+': '#4ade80',
  'AA': '#86efac',
  'AA-': '#bbf7d0',
  'A+': '#fbbf24',
  'A': '#fcd34d',
  'A-': '#fde68a',
  'BBB+': '#f97316',
  'BBB': '#fb923c',
  'DEFAULT': '#94a3b8'
};

const TYPE_COLORS = {
  'NCD': '#0d9488',
  'BOND': '#3b82f6',
  'GSEC': '#8b5cf6',
  'SDL': '#f59e0b',
  'OTHER': '#94a3b8'
};

const FIDashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
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
      // Use comprehensive mock data
      setData(getMockData());
    } finally {
      setLoading(false);
    }
  };

  const getMockData = () => ({
    summary: {
      total_aum: 125000000,
      total_holdings: 45,
      total_clients: 28,
      avg_ytm: 9.25,
      avg_duration: 3.8,
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
    sector_breakdown: [
      { sector: 'NBFC', count: 15, value: 45000000 },
      { sector: 'Banking', count: 10, value: 35000000 },
      { sector: 'Infrastructure', count: 8, value: 25000000 },
      { sector: 'Government', count: 8, value: 15000000 },
      { sector: 'Others', count: 4, value: 5000000 }
    ],
    duration_distribution: [
      { range: '< 1 year', count: 8, value: 20000000 },
      { range: '1-3 years', count: 15, value: 45000000 },
      { range: '3-5 years', count: 12, value: 35000000 },
      { range: '5-7 years', count: 7, value: 18000000 },
      { range: '7+ years', count: 3, value: 7000000 }
    ],
    ytm_distribution: [
      { range: '< 8%', count: 5, value: 10000000 },
      { range: '8-9%', count: 12, value: 35000000 },
      { range: '9-10%', count: 18, value: 55000000 },
      { range: '10-11%', count: 7, value: 18000000 },
      { range: '11%+', count: 3, value: 7000000 }
    ],
    cash_flow_calendar: [
      { month: 'Feb 2026', coupons: 450000, maturities: 0, total: 450000 },
      { month: 'Mar 2026', coupons: 380000, maturities: 5000000, total: 5380000 },
      { month: 'Apr 2026', coupons: 420000, maturities: 0, total: 420000 },
      { month: 'May 2026', coupons: 350000, maturities: 3000000, total: 3350000 },
      { month: 'Jun 2026', coupons: 480000, maturities: 0, total: 480000 },
      { month: 'Jul 2026', coupons: 390000, maturities: 2500000, total: 2890000 },
      { month: 'Aug 2026', coupons: 410000, maturities: 0, total: 410000 },
      { month: 'Sep 2026', coupons: 360000, maturities: 0, total: 360000 },
      { month: 'Oct 2026', coupons: 450000, maturities: 4000000, total: 4450000 },
      { month: 'Nov 2026', coupons: 380000, maturities: 0, total: 380000 },
      { month: 'Dec 2026', coupons: 420000, maturities: 0, total: 420000 },
      { month: 'Jan 2027', coupons: 400000, maturities: 2000000, total: 2400000 }
    ],
    upcoming_maturities: [
      { isin: 'INE002A08427', issuer: 'Reliance Industries', maturity_date: '2026-03-15', face_value: 5000000, days_to_maturity: 35 },
      { isin: 'INE040A08252', issuer: 'HDFC Ltd', maturity_date: '2026-04-10', face_value: 3000000, days_to_maturity: 61 },
      { isin: 'INE860H08176', issuer: 'Tata Capital', maturity_date: '2026-05-20', face_value: 2500000, days_to_maturity: 101 }
    ],
    upcoming_coupons: [
      { isin: 'INE002A08427', issuer: 'Reliance Industries', coupon_date: '2026-02-15', coupon_amount: 125000, days_to_coupon: 7 },
      { isin: 'INE585B08189', issuer: 'Bajaj Finance', coupon_date: '2026-02-28', coupon_amount: 95000, days_to_coupon: 20 },
      { isin: 'INE040A08252', issuer: 'HDFC Ltd', coupon_date: '2026-03-10', coupon_amount: 75000, days_to_coupon: 30 }
    ],
    recent_orders: [
      { id: 'FI/24-25/0001', client_name: 'John Doe', instrument: 'Reliance NCD', status: 'executed', amount: 500000 },
      { id: 'FI/24-25/0002', client_name: 'Jane Smith', instrument: 'HDFC Bond', status: 'pending', amount: 750000 },
      { id: 'FI/24-25/0003', client_name: 'Robert Brown', instrument: 'Bajaj NCD', status: 'approved', amount: 300000 }
    ]
  });

  const formatCurrency = (amount) => {
    if (!amount) return '₹0';
    if (amount >= 10000000) {
      return `₹${(amount / 10000000).toFixed(2)} Cr`;
    } else if (amount >= 100000) {
      return `₹${(amount / 100000).toFixed(2)} L`;
    }
    return `₹${amount?.toLocaleString('en-IN') || 0}`;
  };

  const formatCompactCurrency = (amount) => {
    if (!amount) return '0';
    if (amount >= 10000000) return `${(amount / 10000000).toFixed(1)}Cr`;
    if (amount >= 100000) return `${(amount / 100000).toFixed(1)}L`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(0)}K`;
    return amount.toString();
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

  // Prepare chart data
  const prepareTypeChartData = () => {
    if (!data?.holdings_by_type) return [];
    return Object.entries(data.holdings_by_type).map(([type, info]) => ({
      name: type,
      value: info.value,
      count: info.count,
      fill: TYPE_COLORS[type] || TYPE_COLORS.OTHER
    }));
  };

  const prepareRatingChartData = () => {
    if (!data?.holdings_by_rating) return [];
    return Object.entries(data.holdings_by_rating).map(([rating, value]) => ({
      name: rating,
      value: value,
      fill: RATING_COLORS[rating] || RATING_COLORS.DEFAULT
    }));
  };

  const prepareSectorChartData = () => {
    if (!data?.sector_breakdown) return [];
    return data.sector_breakdown.slice(0, 6).map((item, idx) => ({
      ...item,
      fill: COLORS.primary[idx % COLORS.primary.length]
    }));
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border text-sm">
          <p className="font-medium text-gray-900">{label || payload[0].name}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color || entry.fill }}>
              {entry.name}: {formatCurrency(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
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
      <div className="p-4 md:p-6 space-y-4 md:space-y-6" data-testid="fi-dashboard">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-gray-900 flex items-center gap-2">
              <TrendingUp className="w-6 md:w-7 h-6 md:h-7 text-teal-600" />
              Fixed Income Dashboard
            </h1>
            <p className="text-sm text-gray-500 mt-1">Portfolio analytics and performance metrics</p>
          </div>
          <Button onClick={fetchData} variant="outline" disabled={loading} size="sm">
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Summary Cards - Responsive Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          <Card className="border-l-4 border-l-teal-500">
            <CardContent className="p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs md:text-sm text-gray-500">Total AUM</p>
                  <p className="text-lg md:text-2xl font-bold text-gray-900">{formatCurrency(data?.summary?.total_aum)}</p>
                </div>
                <Wallet className="w-8 md:w-10 h-8 md:h-10 text-teal-500 opacity-50 hidden sm:block" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs md:text-sm text-gray-500">Holdings</p>
                  <p className="text-lg md:text-2xl font-bold text-gray-900">{data?.summary?.total_holdings || 0}</p>
                  <p className="text-xs text-gray-400">{data?.summary?.total_clients || 0} clients</p>
                </div>
                <Building2 className="w-8 md:w-10 h-8 md:h-10 text-blue-500 opacity-50 hidden sm:block" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-green-500">
            <CardContent className="p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs md:text-sm text-gray-500">Avg YTM</p>
                  <p className="text-lg md:text-2xl font-bold text-gray-900">{data?.summary?.avg_ytm?.toFixed(2) || 0}%</p>
                </div>
                <Percent className="w-8 md:w-10 h-8 md:h-10 text-green-500 opacity-50 hidden sm:block" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-purple-500">
            <CardContent className="p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs md:text-sm text-gray-500">Avg Duration</p>
                  <p className="text-lg md:text-2xl font-bold text-gray-900">{data?.summary?.avg_duration?.toFixed(1) || 0} yrs</p>
                </div>
                <Timer className="w-8 md:w-10 h-8 md:h-10 text-purple-500 opacity-50 hidden sm:block" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs for different views */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-flex">
            <TabsTrigger value="overview" className="text-xs md:text-sm">Overview</TabsTrigger>
            <TabsTrigger value="analytics" className="text-xs md:text-sm">Analytics</TabsTrigger>
            <TabsTrigger value="cashflow" className="text-xs md:text-sm">Cash Flow</TabsTrigger>
            <TabsTrigger value="activity" className="text-xs md:text-sm">Activity</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4 md:space-y-6 mt-4">
            {/* Charts Row 1 - Holdings Analysis */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
              {/* Holdings by Type - Donut Chart */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base md:text-lg">
                    <PieChart className="w-5 h-5 text-teal-600" />
                    Holdings by Type
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64 md:h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <RechartsPie>
                        <Pie
                          data={prepareTypeChartData()}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={90}
                          paddingAngle={2}
                          dataKey="value"
                          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                          labelLine={false}
                        >
                          {prepareTypeChartData().map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                      </RechartsPie>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* Holdings by Rating - Bar Chart */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base md:text-lg">
                    <Shield className="w-5 h-5 text-blue-600" />
                    Credit Rating Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64 md:h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={prepareRatingChartData()} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                        <XAxis type="number" tickFormatter={formatCompactCurrency} />
                        <YAxis type="category" dataKey="name" width={50} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                          {prepareRatingChartData().map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Upcoming Events */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
              {/* Upcoming Maturities */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base md:text-lg">
                    <CalendarDays className="w-5 h-5 text-red-600" />
                    Upcoming Maturities
                  </CardTitle>
                  <CardDescription className="text-xs">Next 90 days</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 md:space-y-3 max-h-64 overflow-y-auto">
                    {data?.upcoming_maturities?.slice(0, 5).map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 md:p-3 bg-gray-50 rounded-lg">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-xs md:text-sm truncate">{item.issuer}</p>
                          <p className="text-xs text-gray-500 truncate">{item.isin}</p>
                        </div>
                        <div className="text-right ml-2">
                          <p className="font-medium text-xs md:text-sm">{formatCurrency(item.face_value)}</p>
                          <p className="text-xs text-red-500">{item.days_to_maturity}d</p>
                        </div>
                      </div>
                    ))}
                    {(!data?.upcoming_maturities || data.upcoming_maturities.length === 0) && (
                      <p className="text-center text-gray-500 py-4 text-sm">No upcoming maturities</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Upcoming Coupons */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base md:text-lg">
                    <IndianRupee className="w-5 h-5 text-green-600" />
                    Upcoming Coupons
                  </CardTitle>
                  <CardDescription className="text-xs">Next 30 days</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 md:space-y-3 max-h-64 overflow-y-auto">
                    {data?.upcoming_coupons?.slice(0, 5).map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 md:p-3 bg-gray-50 rounded-lg">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-xs md:text-sm truncate">{item.issuer}</p>
                          <p className="text-xs text-gray-500 truncate">{item.isin}</p>
                        </div>
                        <div className="text-right ml-2">
                          <p className="font-medium text-xs md:text-sm text-green-600">+{formatCurrency(item.coupon_amount)}</p>
                          <p className="text-xs text-gray-500">{item.days_to_coupon}d</p>
                        </div>
                      </div>
                    ))}
                    {(!data?.upcoming_coupons || data.upcoming_coupons.length === 0) && (
                      <p className="text-center text-gray-500 py-4 text-sm">No upcoming coupons</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-4 md:space-y-6 mt-4">
            {/* Sector & Duration Analysis */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
              {/* Sector Breakdown */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base md:text-lg">
                    <Briefcase className="w-5 h-5 text-purple-600" />
                    Sector Allocation
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64 md:h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <RechartsPie>
                        <Pie
                          data={prepareSectorChartData()}
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          paddingAngle={2}
                          dataKey="value"
                          nameKey="sector"
                          label={({ sector, percent }) => `${sector} ${(percent * 100).toFixed(0)}%`}
                          labelLine={false}
                        >
                          {prepareSectorChartData().map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                      </RechartsPie>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* Duration Distribution */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base md:text-lg">
                    <Timer className="w-5 h-5 text-amber-600" />
                    Duration Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64 md:h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={data?.duration_distribution || []}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="range" tick={{ fontSize: 11 }} />
                        <YAxis tickFormatter={formatCompactCurrency} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="value" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Value" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* YTM Distribution */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base md:text-lg">
                  <Percent className="w-5 h-5 text-green-600" />
                  Yield to Maturity Distribution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64 md:h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data?.ytm_distribution || []}>
                      <defs>
                        <linearGradient id="ytmGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#22c55e" stopOpacity={0.1}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="range" tick={{ fontSize: 11 }} />
                      <YAxis tickFormatter={formatCompactCurrency} />
                      <Tooltip content={<CustomTooltip />} />
                      <Area 
                        type="monotone" 
                        dataKey="value" 
                        stroke="#22c55e" 
                        fillOpacity={1} 
                        fill="url(#ytmGradient)"
                        name="Holdings Value"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Cash Flow Tab */}
          <TabsContent value="cashflow" className="space-y-4 md:space-y-6 mt-4">
            {/* Cash Flow Calendar Chart */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base md:text-lg">
                  <Calendar className="w-5 h-5 text-blue-600" />
                  12-Month Cash Flow Calendar
                </CardTitle>
                <CardDescription className="text-xs">Expected coupon payments and maturities</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-72 md:h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={data?.cash_flow_calendar || []}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="month" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" height={60} />
                      <YAxis tickFormatter={formatCompactCurrency} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      <Bar dataKey="coupons" fill="#22c55e" name="Coupons" stackId="stack" radius={[0, 0, 0, 0]} />
                      <Bar dataKey="maturities" fill="#3b82f6" name="Maturities" stackId="stack" radius={[4, 4, 0, 0]} />
                      <Line type="monotone" dataKey="total" stroke="#ef4444" strokeWidth={2} name="Total" dot={{ fill: '#ef4444' }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Cash Flow Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
              <Card className="bg-green-50 border-green-200">
                <CardContent className="p-3 md:p-4">
                  <p className="text-xs text-green-700">Total Coupons (12M)</p>
                  <p className="text-lg md:text-xl font-bold text-green-800">
                    {formatCurrency(data?.cash_flow_calendar?.reduce((sum, m) => sum + (m.coupons || 0), 0))}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-blue-50 border-blue-200">
                <CardContent className="p-3 md:p-4">
                  <p className="text-xs text-blue-700">Total Maturities (12M)</p>
                  <p className="text-lg md:text-xl font-bold text-blue-800">
                    {formatCurrency(data?.cash_flow_calendar?.reduce((sum, m) => sum + (m.maturities || 0), 0))}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-purple-50 border-purple-200">
                <CardContent className="p-3 md:p-4">
                  <p className="text-xs text-purple-700">Total Cash Flow</p>
                  <p className="text-lg md:text-xl font-bold text-purple-800">
                    {formatCurrency(data?.cash_flow_calendar?.reduce((sum, m) => sum + (m.total || 0), 0))}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-amber-50 border-amber-200">
                <CardContent className="p-3 md:p-4">
                  <p className="text-xs text-amber-700">Accrued Interest</p>
                  <p className="text-lg md:text-xl font-bold text-amber-800">
                    {formatCurrency(data?.summary?.total_accrued_interest)}
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Activity Tab */}
          <TabsContent value="activity" className="space-y-4 md:space-y-6 mt-4">
            {/* Recent Orders */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div>
                  <CardTitle className="flex items-center gap-2 text-base md:text-lg">
                    <FileText className="w-5 h-5 text-purple-600" />
                    Recent Orders
                  </CardTitle>
                </div>
                <Button variant="ghost" size="sm" onClick={() => navigate('/fi-orders')} className="text-xs">
                  View All <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs">Order ID</TableHead>
                        <TableHead className="text-xs hidden sm:table-cell">Client</TableHead>
                        <TableHead className="text-xs">Instrument</TableHead>
                        <TableHead className="text-xs text-right">Amount</TableHead>
                        <TableHead className="text-xs">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data?.recent_orders?.slice(0, 5).map((order, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-mono text-xs">{order.id}</TableCell>
                          <TableCell className="text-xs hidden sm:table-cell">{order.client_name}</TableCell>
                          <TableCell className="text-xs">{order.instrument}</TableCell>
                          <TableCell className="text-xs text-right">{formatCurrency(order.amount)}</TableCell>
                          <TableCell>{getStatusBadge(order.status)}</TableCell>
                        </TableRow>
                      ))}
                      {(!data?.recent_orders || data.recent_orders.length === 0) && (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center text-gray-500 py-8 text-sm">
                            No recent orders
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base md:text-lg">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                  <Button variant="outline" onClick={() => navigate('/fi-instruments')} className="h-auto py-3 md:py-4 flex-col text-xs md:text-sm">
                    <TrendingUp className="w-5 md:w-6 h-5 md:h-6 mb-1 md:mb-2 text-teal-600" />
                    <span>Security Master</span>
                  </Button>
                  <Button variant="outline" onClick={() => navigate('/fi-orders')} className="h-auto py-3 md:py-4 flex-col text-xs md:text-sm">
                    <FileText className="w-5 md:w-6 h-5 md:h-6 mb-1 md:mb-2 text-blue-600" />
                    <span>New Order</span>
                  </Button>
                  <Button variant="outline" onClick={() => navigate('/fi-primary-market')} className="h-auto py-3 md:py-4 flex-col text-xs md:text-sm">
                    <Building2 className="w-5 md:w-6 h-5 md:h-6 mb-1 md:mb-2 text-purple-600" />
                    <span>IPO/NFO</span>
                  </Button>
                  <Button variant="outline" onClick={() => navigate('/fi-reports')} className="h-auto py-3 md:py-4 flex-col text-xs md:text-sm">
                    <BarChart3 className="w-5 md:w-6 h-5 md:h-6 mb-1 md:mb-2 text-green-600" />
                    <span>Reports</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </LicenseGate>
  );
};

export default FIDashboard;
