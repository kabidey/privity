import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  Shield, AlertTriangle, MapPin, Lock, Unlock, Ban, CheckCircle2,
  Activity, Globe, Server, Users, Clock, TrendingUp, RefreshCw,
  XCircle, Eye, ChevronRight, Wifi, WifiOff
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Area, AreaChart
} from 'recharts';

// Leaflet imports
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icons in Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom hook for security data
const useSecurityData = () => {
  const [securityStatus, setSecurityStatus] = useState(null);
  const [loginLocations, setLoginLocations] = useState([]);
  const [mapData, setMapData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [statusRes, locationsRes, mapRes] = await Promise.all([
        api.get('/dashboard/security-status'),
        api.get('/dashboard/login-locations?hours=168'), // Last 7 days
        api.get('/dashboard/login-locations/map-data')
      ]);

      if (statusRes.data.error) {
        setError(statusRes.data.error);
        return;
      }

      setSecurityStatus(statusRes.data);
      setLoginLocations(locationsRes.data.locations || []);
      setMapData(mapRes.data.markers || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load security data');
      toast.error('Failed to load security dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return { securityStatus, loginLocations, mapData, loading, error, refetch: fetchData };
};

// Risk level colors
const RISK_COLORS = {
  low: '#22c55e',
  medium: '#f59e0b', 
  high: '#ef4444',
  critical: '#7c3aed'
};

const RISK_BG = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-amber-100 text-amber-800',
  high: 'bg-red-100 text-red-800',
  critical: 'bg-purple-100 text-purple-800'
};

// Chart color palette
const CHART_COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const SecurityDashboard = () => {
  const navigate = useNavigate();
  const { securityStatus, loginLocations, mapData, loading, error, refetch } = useSecurityData();
  const [timeRange, setTimeRange] = useState('24h');
  const [activeTab, setActiveTab] = useState('overview');

  const { isPEDesk } = useCurrentUser();

  // Redirect non-PE users
  useEffect(() => {
    if (!isPEDesk) {
      toast.error('Access denied. Only PE Desk can view Security Dashboard.');
      navigate('/');
    }
  }, [isPEDesk, navigate]);

  // Process chart data
  const chartData = useMemo(() => {
    if (!securityStatus) return {};

    // Events by type for pie chart
    const eventTypes = {};
    securityStatus.recent_security_events?.forEach(event => {
      const type = event.event_type || 'UNKNOWN';
      eventTypes[type] = (eventTypes[type] || 0) + 1;
    });

    const eventsByType = Object.entries(eventTypes).map(([name, value]) => ({
      name: name.replace(/_/g, ' '),
      value
    }));

    // Risk level distribution
    const riskLevels = { low: 0, medium: 0, high: 0, critical: 0 };
    loginLocations.forEach(loc => {
      const level = loc.risk_level || 'low';
      riskLevels[level]++;
    });

    const riskDistribution = Object.entries(riskLevels).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
      fill: RISK_COLORS[name]
    }));

    // Login timeline (group by hour)
    const timeline = {};
    loginLocations.forEach(loc => {
      if (loc.timestamp) {
        const hour = loc.timestamp.substring(0, 13) + ':00';
        if (!timeline[hour]) {
          timeline[hour] = { successful: 0, failed: 0, unusual: 0 };
        }
        if (loc.is_unusual) {
          timeline[hour].unusual++;
        } else {
          timeline[hour].successful++;
        }
      }
    });

    const loginTimeline = Object.entries(timeline)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-24)
      .map(([time, data]) => ({
        time: new Date(time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
        ...data
      }));

    // Country distribution
    const countries = {};
    loginLocations.forEach(loc => {
      const country = loc.country || 'Unknown';
      countries[country] = (countries[country] || 0) + 1;
    });

    const countryDistribution = Object.entries(countries)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([name, value]) => ({ name, value }));

    return { eventsByType, riskDistribution, loginTimeline, countryDistribution };
  }, [securityStatus, loginLocations]);

  // Handle unblock IP
  const handleUnblockIP = async (ip) => {
    try {
      await api.post(`/dashboard/unblock-ip?ip_address=${ip}`);
      toast.success(`IP ${ip} unblocked`);
      refetch();
    } catch (err) {
      toast.error('Failed to unblock IP');
    }
  };

  // Handle unlock account
  const handleUnlockAccount = async (email) => {
    try {
      await api.post(`/dashboard/unlock-account?email=${email}`);
      toast.success(`Account ${email} unlocked`);
      refetch();
    } catch (err) {
      toast.error('Failed to unlock account');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="security-loading">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center" data-testid="security-error">
        <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Access Denied</h2>
        <p className="text-gray-500">{error}</p>
        <Button className="mt-4" onClick={() => navigate('/')}>Go to Dashboard</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="security-dashboard">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Shield className="w-7 h-7 text-emerald-600" />
            Security Dashboard
          </h1>
          <p className="text-gray-500 text-sm">Monitor login activity, threats, and system security</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32" data-testid="time-range-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">Last 24h</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={refetch} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Security Status Overview Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-emerald-600 font-medium">Successful Logins</p>
                <p className="text-3xl font-bold text-emerald-700" data-testid="successful-logins">
                  {securityStatus?.statistics?.successful_logins_today || 0}
                </p>
                <p className="text-xs text-emerald-500 mt-1">Today</p>
              </div>
              <CheckCircle2 className="w-10 h-10 text-emerald-300" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-red-200 bg-gradient-to-br from-red-50 to-orange-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-red-600 font-medium">Failed Logins</p>
                <p className="text-3xl font-bold text-red-700" data-testid="failed-logins">
                  {securityStatus?.statistics?.failed_logins_today || 0}
                </p>
                <p className="text-xs text-red-500 mt-1">Today</p>
              </div>
              <XCircle className="w-10 h-10 text-red-300" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-amber-200 bg-gradient-to-br from-amber-50 to-yellow-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-amber-600 font-medium">Blocked IPs</p>
                <p className="text-3xl font-bold text-amber-700" data-testid="blocked-ips">
                  {securityStatus?.statistics?.blocked_ips_count || 0}
                </p>
                <p className="text-xs text-amber-500 mt-1">Currently blocked</p>
              </div>
              <Ban className="w-10 h-10 text-amber-300" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-purple-200 bg-gradient-to-br from-purple-50 to-pink-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-purple-600 font-medium">Locked Accounts</p>
                <p className="text-3xl font-bold text-purple-700" data-testid="locked-accounts">
                  {securityStatus?.statistics?.locked_accounts_count || 0}
                </p>
                <p className="text-xs text-purple-500 mt-1">Currently locked</p>
              </div>
              <Lock className="w-10 h-10 text-purple-300" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Protections Banner */}
      <Card className="bg-gradient-to-r from-slate-900 to-slate-800 text-white border-0">
        <CardContent className="py-4">
          <div className="flex items-center gap-6 flex-wrap">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-emerald-400" />
              <span className="text-sm font-medium">Active Protections:</span>
            </div>
            {securityStatus?.protections && Object.entries(securityStatus.protections)
              .filter(([, active]) => active)
              .map(([name]) => (
                <Badge key={name} variant="outline" className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  {name.replace(/_/g, ' ')}
                </Badge>
              ))
            }
          </div>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-white border">
          <TabsTrigger value="overview" data-testid="tab-overview">
            <Activity className="w-4 h-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="map" data-testid="tab-map">
            <Globe className="w-4 h-4 mr-2" />
            Login Map
          </TabsTrigger>
          <TabsTrigger value="events" data-testid="tab-events">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Events
          </TabsTrigger>
          <TabsTrigger value="management" data-testid="tab-management">
            <Lock className="w-4 h-4 mr-2" />
            Management
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Login Activity Timeline */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                  Login Activity
                </CardTitle>
                <CardDescription>Login attempts over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64" data-testid="login-timeline-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData.loginTimeline || []}>
                      <defs>
                        <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="colorUnusual" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="time" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <YAxis tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: 'white', borderRadius: '8px', border: '1px solid #e5e7eb' }}
                      />
                      <Legend />
                      <Area 
                        type="monotone" 
                        dataKey="successful" 
                        name="Successful"
                        stroke="#10b981" 
                        fill="url(#colorSuccess)"
                        strokeWidth={2}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="unusual" 
                        name="Unusual"
                        stroke="#ef4444" 
                        fill="url(#colorUnusual)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Risk Level Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                  Risk Distribution
                </CardTitle>
                <CardDescription>Login attempts by risk level</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64" data-testid="risk-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData.riskDistribution || []}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {(chartData.riskDistribution || []).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Security Events by Type */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Activity className="w-5 h-5 text-blue-600" />
                  Event Types
                </CardTitle>
                <CardDescription>Recent security events breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64" data-testid="events-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData.eventsByType || []} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis type="number" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={100} stroke="#9ca3af" />
                      <Tooltip />
                      <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]}>
                        {(chartData.eventsByType || []).map((_, index) => (
                          <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Top Countries */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Globe className="w-5 h-5 text-indigo-600" />
                  Login Locations
                </CardTitle>
                <CardDescription>Top countries by login count</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64" data-testid="countries-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData.countryDistribution || []}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="#9ca3af" />
                      <YAxis tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <Tooltip />
                      <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]}>
                        {(chartData.countryDistribution || []).map((_, index) => (
                          <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Map Tab */}
        <TabsContent value="map" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-blue-600" />
                Global Login Map
              </CardTitle>
              <CardDescription>
                Geographic distribution of login attempts. Click markers for details.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[500px] rounded-lg overflow-hidden border" data-testid="login-map">
                <MapContainer 
                  center={[20.5937, 78.9629]} // India center
                  zoom={4} 
                  style={{ height: '100%', width: '100%' }}
                  scrollWheelZoom={true}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {mapData.map((location, index) => (
                    <CircleMarker
                      key={index}
                      center={[location.lat, location.lon]}
                      radius={8 + Math.min(location.logins?.length || 1, 10) * 2}
                      fillColor={
                        location.logins?.some(l => l.risk_level === 'critical') ? RISK_COLORS.critical :
                        location.logins?.some(l => l.risk_level === 'high') ? RISK_COLORS.high :
                        location.logins?.some(l => l.risk_level === 'medium') ? RISK_COLORS.medium :
                        RISK_COLORS.low
                      }
                      color="#fff"
                      weight={2}
                      opacity={1}
                      fillOpacity={0.7}
                    >
                      <Popup>
                        <div className="p-2 min-w-[200px]">
                          <h3 className="font-semibold text-gray-900">
                            {location.city}, {location.country}
                          </h3>
                          <p className="text-sm text-gray-500 mb-2">
                            {location.logins?.length || 0} login(s)
                          </p>
                          <div className="space-y-1 max-h-32 overflow-y-auto">
                            {location.logins?.slice(0, 5).map((login, i) => (
                              <div key={i} className="text-xs flex items-center justify-between gap-2 py-1 border-b">
                                <span className="truncate">{login.user}</span>
                                <span className={`px-1.5 py-0.5 rounded text-[10px] ${RISK_BG[login.risk_level || 'low']}`}>
                                  {login.risk_level || 'low'}
                                </span>
                              </div>
                            ))}
                            {(location.logins?.length || 0) > 5 && (
                              <p className="text-xs text-gray-400 pt-1">
                                +{location.logins.length - 5} more
                              </p>
                            )}
                          </div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  ))}
                </MapContainer>
              </div>

              {/* Map Legend */}
              <div className="mt-4 flex items-center justify-center gap-6 text-sm">
                {Object.entries(RISK_COLORS).map(([level, color]) => (
                  <div key={level} className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full" style={{ backgroundColor: color }}></div>
                    <span className="capitalize">{level} Risk</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Events Tab */}
        <TabsContent value="events" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
                Recent Security Events
              </CardTitle>
              <CardDescription>Last 50 security events from the system</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table data-testid="events-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Event</TableHead>
                      <TableHead>IP Address</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Details</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {securityStatus?.recent_security_events?.length > 0 ? (
                      securityStatus.recent_security_events.map((event, index) => (
                        <TableRow key={index}>
                          <TableCell className="text-xs text-gray-500 whitespace-nowrap">
                            {event.timestamp ? new Date(event.timestamp).toLocaleString('en-IN', {
                              day: '2-digit',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit'
                            }) : '-'}
                          </TableCell>
                          <TableCell>
                            <Badge 
                              className={
                                event.event_type?.includes('FAILED') || event.event_type?.includes('LOCKED') 
                                  ? 'bg-red-100 text-red-800' 
                                  : event.event_type?.includes('SUCCESS')
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-blue-100 text-blue-800'
                              }
                            >
                              {event.event_type?.replace(/_/g, ' ') || 'Unknown'}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-xs">{event.ip_address || '-'}</TableCell>
                          <TableCell className="text-sm">{event.user_id || event.details?.email || '-'}</TableCell>
                          <TableCell className="text-xs text-gray-500 max-w-[200px] truncate">
                            {event.details ? JSON.stringify(event.details).substring(0, 50) : '-'}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-8 text-gray-500">
                          <Shield className="w-12 h-12 mx-auto text-gray-300 mb-2" />
                          No security events recorded
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          {/* Unusual Logins */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-red-600" />
                Unusual Login Locations
              </CardTitle>
              <CardDescription>Logins flagged as unusual based on location analysis</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table data-testid="unusual-logins-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Location</TableHead>
                      <TableHead>ISP</TableHead>
                      <TableHead>Risk</TableHead>
                      <TableHead>Alerts</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loginLocations.filter(l => l.is_unusual).length > 0 ? (
                      loginLocations
                        .filter(l => l.is_unusual)
                        .slice(0, 20)
                        .map((loc, index) => (
                          <TableRow key={index} className="bg-red-50/50">
                            <TableCell className="text-xs text-gray-500 whitespace-nowrap">
                              {loc.timestamp ? new Date(loc.timestamp).toLocaleString('en-IN', {
                                day: '2-digit',
                                month: 'short',
                                hour: '2-digit',
                                minute: '2-digit'
                              }) : '-'}
                            </TableCell>
                            <TableCell className="font-medium">{loc.user_email}</TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <MapPin className="w-3 h-3 text-gray-400" />
                                {loc.city}, {loc.country}
                              </div>
                            </TableCell>
                            <TableCell className="text-xs">
                              {loc.is_hosting && <Badge className="bg-purple-100 text-purple-800 mr-1">Hosting</Badge>}
                              {loc.is_proxy && <Badge className="bg-amber-100 text-amber-800 mr-1">Proxy</Badge>}
                              <span className="text-gray-500">{loc.isp}</span>
                            </TableCell>
                            <TableCell>
                              <Badge className={RISK_BG[loc.risk_level || 'low']}>
                                {loc.risk_level || 'low'}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-xs">
                              {loc.alerts?.map((alert, i) => (
                                <div key={i} className="text-red-600">{alert.message}</div>
                              ))}
                            </TableCell>
                          </TableRow>
                        ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                          <CheckCircle2 className="w-12 h-12 mx-auto text-green-300 mb-2" />
                          No unusual logins detected
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Management Tab */}
        <TabsContent value="management" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Blocked IPs */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Ban className="w-5 h-5 text-red-600" />
                  Blocked IP Addresses
                </CardTitle>
                <CardDescription>IPs currently blocked due to suspicious activity</CardDescription>
              </CardHeader>
              <CardContent>
                {securityStatus?.blocked_ips?.length > 0 ? (
                  <div className="space-y-2" data-testid="blocked-ips-list">
                    {securityStatus.blocked_ips.map((ip, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100">
                        <div className="flex items-center gap-3">
                          <Server className="w-5 h-5 text-red-500" />
                          <span className="font-mono text-sm">{ip}</span>
                        </div>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          onClick={() => handleUnblockIP(ip)}
                          className="text-green-600 hover:bg-green-50"
                          data-testid={`unblock-ip-${ip}`}
                        >
                          <Unlock className="w-4 h-4 mr-1" />
                          Unblock
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <CheckCircle2 className="w-12 h-12 mx-auto text-green-300 mb-2" />
                    <p>No blocked IPs</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Locked Accounts */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Lock className="w-5 h-5 text-amber-600" />
                  Locked Accounts
                </CardTitle>
                <CardDescription>Accounts locked due to failed login attempts</CardDescription>
              </CardHeader>
              <CardContent>
                {securityStatus?.locked_accounts?.length > 0 ? (
                  <div className="space-y-2" data-testid="locked-accounts-list">
                    {securityStatus.locked_accounts.map((email, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg border border-amber-100">
                        <div className="flex items-center gap-3">
                          <Users className="w-5 h-5 text-amber-500" />
                          <span className="text-sm">{email}</span>
                        </div>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          onClick={() => handleUnlockAccount(email)}
                          className="text-green-600 hover:bg-green-50"
                          data-testid={`unlock-account-${index}`}
                        >
                          <Unlock className="w-4 h-4 mr-1" />
                          Unlock
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <CheckCircle2 className="w-12 h-12 mx-auto text-green-300 mb-2" />
                    <p>No locked accounts</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Security Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-emerald-600" />
                Security Configuration
              </CardTitle>
              <CardDescription>Current security settings and thresholds</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Max Login Attempts</p>
                  <p className="text-2xl font-bold text-gray-900">5</p>
                  <p className="text-xs text-gray-400">before lockout</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Lockout Duration</p>
                  <p className="text-2xl font-bold text-gray-900">15</p>
                  <p className="text-xs text-gray-400">minutes</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">CAPTCHA Threshold</p>
                  <p className="text-2xl font-bold text-gray-900">3</p>
                  <p className="text-xs text-gray-400">failed attempts</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Rate Limit</p>
                  <p className="text-2xl font-bold text-gray-900">10</p>
                  <p className="text-xs text-gray-400">login/min</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SecurityDashboard;
