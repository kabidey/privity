import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '../utils/api';
import { useProtectedPage } from '../hooks/useProtectedPage';
import { 
  History, Search, Filter, Eye, RefreshCw, User, Calendar, 
  Activity, FileText, Users, BarChart3, Clock, Shield
} from 'lucide-react';

const AuditTrail = () => {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [selectedLog, setSelectedLog] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [entityTypes, setEntityTypes] = useState([]);
  const [actions, setActions] = useState({});
  
  // Filters
  const [filters, setFilters] = useState({
    entity_type: '',
    action: '',
    user_name: '',
    start_date: '',
    end_date: ''
  });
  const [pagination, setPagination] = useState({ limit: 50, skip: 0 });
  const [statsDays, setStatsDays] = useState(7);

  const { isLoading, isAuthorized, hasPermission } = useProtectedPage({
    allowIf: ({ isPELevel, hasPermission }) => isPELevel || hasPermission('security.view_audit'),
    deniedMessage: 'Access denied. You need Audit Trail permission to view this page.'
  });

  useEffect(() => {
    if (!isAuthorized) return;
    fetchLogs();
    fetchStats();
    fetchEntityTypes();
    fetchActions();
  }, [isAuthorized]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filters.entity_type) params.append('entity_type', filters.entity_type);
      if (filters.action) params.append('action', filters.action);
      if (filters.user_name) params.append('user_name', filters.user_name);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      params.append('limit', pagination.limit);
      params.append('skip', pagination.skip);

      const response = await api.get(`/audit-logs?${params.toString()}`);
      setLogs(response.data.logs);
      setTotal(response.data.total);
    } catch (error) {
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get(`/audit-logs/stats?days=${statsDays}`);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const fetchEntityTypes = async () => {
    try {
      const response = await api.get('/audit-logs/entity-types');
      setEntityTypes(response.data.entity_types);
    } catch (error) {
      console.error('Failed to load entity types:', error);
    }
  };

  const fetchActions = async () => {
    try {
      const response = await api.get('/audit-logs/actions');
      setActions(response.data.actions);
    } catch (error) {
      console.error('Failed to load actions:', error);
    }
  };

  const handleSearch = () => {
    setPagination({ ...pagination, skip: 0 });
    fetchLogs();
  };

  const handleClearFilters = () => {
    setFilters({
      entity_type: '',
      action: '',
      user_name: '',
      start_date: '',
      end_date: ''
    });
    setPagination({ limit: 50, skip: 0 });
  };

  const viewLogDetail = (log) => {
    setSelectedLog(log);
    setDetailOpen(true);
  };

  const getActionBadge = (action) => {
    const colors = {
      'USER_LOGIN': 'bg-blue-500',
      'USER_REGISTER': 'bg-green-500',
      'CLIENT_CREATE': 'bg-emerald-500',
      'CLIENT_APPROVE': 'bg-green-600',
      'CLIENT_REJECT': 'bg-red-500',
      'BOOKING_CREATE': 'bg-purple-500',
      'BOOKING_APPROVE': 'bg-green-500',
      'BOOKING_REJECT': 'bg-red-500',
      'PAYMENT_RECORDED': 'bg-amber-500',
      'STOCK_CREATE': 'bg-indigo-500',
      'PURCHASE_CREATE': 'bg-cyan-500',
    };
    const color = colors[action] || 'bg-gray-500';
    const label = actions[action] || action?.replace(/_/g, ' ') || 'Unknown';
    return <Badge className={`${color} text-white text-xs`}>{label}</Badge>;
  };

  const getEntityBadge = (entityType) => {
    const colors = {
      'user': 'bg-blue-100 text-blue-800',
      'client': 'bg-green-100 text-green-800',
      'booking': 'bg-purple-100 text-purple-800',
      'stock': 'bg-indigo-100 text-indigo-800',
      'purchase': 'bg-cyan-100 text-cyan-800',
      'vendor': 'bg-orange-100 text-orange-800',
      'rp': 'bg-pink-100 text-pink-800',
    };
    const color = colors[entityType] || 'bg-gray-100 text-gray-800';
    return <Badge variant="outline" className={color}>{entityType?.toUpperCase() || '-'}</Badge>;
  };

  const getRoleBadge = (roleName) => {
    const colors = {
      'PE Desk': 'bg-purple-100 text-purple-800',
      'PE Manager': 'bg-indigo-100 text-indigo-800',
      'Finance': 'bg-emerald-100 text-emerald-800',
      'Viewer': 'bg-gray-100 text-gray-800',
      'Partners Desk': 'bg-pink-100 text-pink-800',
      'Business Partner': 'bg-orange-100 text-orange-800',
      'Employee': 'bg-blue-100 text-blue-800',
    };
    const color = colors[roleName] || 'bg-gray-100 text-gray-800';
    return <Badge variant="outline" className={color}>{roleName}</Badge>;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Show loading while checking permissions
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  if (loading && logs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="audit-trail-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Shield className="w-7 h-7 text-emerald-600" />
            Audit Trail
          </h1>
          <p className="text-gray-500">Track all user activities and system changes</p>
        </div>
        <Button variant="outline" onClick={() => { fetchLogs(); fetchStats(); }}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Total Activities</p>
                  <p className="text-2xl font-bold text-emerald-600">{stats.total_logs}</p>
                </div>
                <Activity className="w-8 h-8 text-emerald-500" />
              </div>
              <p className="text-xs text-gray-400 mt-1">Last {statsDays} days</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Unique Actions</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {Object.keys(stats.by_action || {}).length}
                  </p>
                </div>
                <FileText className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Entity Types</p>
                  <p className="text-2xl font-bold text-purple-600">
                    {Object.keys(stats.by_entity_type || {}).length}
                  </p>
                </div>
                <BarChart3 className="w-8 h-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Active Users</p>
                  <p className="text-2xl font-bold text-amber-600">
                    {(stats.by_user || []).length}
                  </p>
                </div>
                <Users className="w-8 h-8 text-amber-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="logs" className="w-full">
        <TabsList>
          <TabsTrigger value="logs" data-testid="logs-tab">Activity Logs</TabsTrigger>
          <TabsTrigger value="analytics" data-testid="analytics-tab">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="logs">
          {/* Filters */}
          <Card className="mb-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Filter className="w-5 h-5" />
                Filters
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div>
                  <Label>Entity Type</Label>
                  <Select value={filters.entity_type || "all"} onValueChange={(v) => setFilters({ ...filters, entity_type: v === "all" ? "" : v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="All Types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      {entityTypes.map((type) => (
                        <SelectItem key={type} value={type}>{type.toUpperCase()}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Action</Label>
                  <Select value={filters.action || "all"} onValueChange={(v) => setFilters({ ...filters, action: v === "all" ? "" : v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="All Actions" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Actions</SelectItem>
                      {Object.entries(actions).map(([key, label]) => (
                        <SelectItem key={key} value={key}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>User Name</Label>
                  <Input
                    placeholder="Search user..."
                    value={filters.user_name}
                    onChange={(e) => setFilters({ ...filters, user_name: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={filters.start_date}
                    onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
                  />
                </div>
                <div>
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={filters.end_date}
                    onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <Button onClick={handleSearch}>
                  <Search className="w-4 h-4 mr-2" />
                  Search
                </Button>
                <Button variant="outline" onClick={handleClearFilters}>
                  Clear Filters
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Logs Table */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="w-5 h-5" />
                Activity Logs ({total})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Entity</TableHead>
                      <TableHead>Entity Name/ID</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                          No audit logs found
                        </TableCell>
                      </TableRow>
                    ) : (
                      logs.map((log) => (
                        <TableRow key={log.id} data-testid={`audit-log-${log.id}`}>
                          <TableCell className="whitespace-nowrap text-sm">
                            <div className="flex items-center gap-1">
                              <Clock className="w-3 h-3 text-gray-400" />
                              {formatDate(log.timestamp)}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <User className="w-4 h-4 text-gray-400" />
                              <span className="font-medium">{log.user_name || '-'}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            {getRoleBadge(log.role_name)}
                          </TableCell>
                          <TableCell>
                            {getActionBadge(log.action)}
                          </TableCell>
                          <TableCell>
                            {getEntityBadge(log.entity_type)}
                          </TableCell>
                          <TableCell className="max-w-[200px]">
                            {log.entity_name ? (
                              <span className="font-medium">{log.entity_name}</span>
                            ) : (
                              <span className="text-gray-400 text-xs font-mono truncate block" title={log.entity_id}>
                                {log.entity_id?.substring(0, 12)}...
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => viewLogDetail(log)}
                              title="View Details"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {total > pagination.limit && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-gray-500">
                    Showing {pagination.skip + 1} to {Math.min(pagination.skip + pagination.limit, total)} of {total}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={pagination.skip === 0}
                      onClick={() => {
                        setPagination({ ...pagination, skip: Math.max(0, pagination.skip - pagination.limit) });
                        fetchLogs();
                      }}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={pagination.skip + pagination.limit >= total}
                      onClick={() => {
                        setPagination({ ...pagination, skip: pagination.skip + pagination.limit });
                        fetchLogs();
                      }}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics">
          {/* Period Selector */}
          <div className="flex items-center gap-4 mb-4">
            <Label>Period:</Label>
            <Select value={statsDays.toString()} onValueChange={(v) => { setStatsDays(parseInt(v)); }}>
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="14">Last 14 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="60">Last 60 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={fetchStats}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh Stats
            </Button>
          </div>

          {stats && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* By Action */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="w-5 h-5" />
                    Activities by Action
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 max-h-[400px] overflow-y-auto">
                    {Object.entries(stats.by_action || {}).map(([action, count]) => (
                      <div key={action} className="flex items-center justify-between">
                        {getActionBadge(action)}
                        <Badge variant="secondary" className="ml-2">{count}</Badge>
                      </div>
                    ))}
                    {Object.keys(stats.by_action || {}).length === 0 && (
                      <p className="text-gray-500 text-center py-4">No data available</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* By Entity Type */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Activities by Entity Type
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(stats.by_entity_type || {}).map(([entity, count]) => (
                      <div key={entity} className="flex items-center justify-between">
                        {getEntityBadge(entity)}
                        <Badge variant="secondary">{count}</Badge>
                      </div>
                    ))}
                    {Object.keys(stats.by_entity_type || {}).length === 0 && (
                      <p className="text-gray-500 text-center py-4">No data available</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Top Active Users */}
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="w-5 h-5" />
                    Most Active Users (Last {statsDays} Days)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {(stats.by_user || []).length > 0 ? (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Rank</TableHead>
                            <TableHead>User</TableHead>
                            <TableHead className="text-right">Activities</TableHead>
                            <TableHead className="text-right">% of Total</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {stats.by_user.map((user, index) => (
                            <TableRow key={user.user_id}>
                              <TableCell>
                                <Badge variant={index < 3 ? "default" : "secondary"}>
                                  #{index + 1}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  <User className="w-4 h-4 text-gray-400" />
                                  <span className="font-medium">{user.user_name}</span>
                                </div>
                              </TableCell>
                              <TableCell className="text-right font-bold">{user.count}</TableCell>
                              <TableCell className="text-right text-gray-500">
                                {stats.total_logs > 0 ? ((user.count / stats.total_logs) * 100).toFixed(1) : 0}%
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No user activity data available</p>
                  )}
                </CardContent>
              </Card>

              {/* Daily Activity */}
              {stats.daily_activity && stats.daily_activity.length > 0 && (
                <Card className="md:col-span-2">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Calendar className="w-5 h-5" />
                      Daily Activity
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-end gap-1 h-32 overflow-x-auto pb-2">
                      {stats.daily_activity.map((day) => {
                        const maxCount = Math.max(...stats.daily_activity.map(d => d.count));
                        const height = maxCount > 0 ? (day.count / maxCount) * 100 : 0;
                        return (
                          <div key={day.date} className="flex flex-col items-center min-w-[40px]">
                            <div 
                              className="w-8 bg-emerald-500 rounded-t transition-all hover:bg-emerald-600"
                              style={{ height: `${Math.max(height, 4)}%` }}
                              title={`${day.date}: ${day.count} activities`}
                            />
                            <span className="text-xs text-gray-500 mt-1 transform -rotate-45 origin-top-left">
                              {day.date.substring(5)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="w-5 h-5" />
              Audit Log Details
            </DialogTitle>
          </DialogHeader>
          {selectedLog && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-500">Timestamp</Label>
                  <p className="mt-1 flex items-center gap-1">
                    <Clock className="w-4 h-4 text-gray-400" />
                    {formatDate(selectedLog.timestamp)}
                  </p>
                </div>
                <div>
                  <Label className="text-gray-500">Action</Label>
                  <div className="mt-1">{getActionBadge(selectedLog.action)}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-500">User</Label>
                  <p className="mt-1 font-medium flex items-center gap-1">
                    <User className="w-4 h-4 text-gray-400" />
                    {selectedLog.user_name}
                  </p>
                </div>
                <div>
                  <Label className="text-gray-500">Role</Label>
                  <div className="mt-1">{getRoleBadge(selectedLog.role_name)}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-500">Entity Type</Label>
                  <div className="mt-1">{getEntityBadge(selectedLog.entity_type)}</div>
                </div>
                <div>
                  <Label className="text-gray-500">Entity ID</Label>
                  <p className="mt-1 text-sm font-mono bg-gray-50 p-2 rounded truncate" title={selectedLog.entity_id}>
                    {selectedLog.entity_id}
                  </p>
                </div>
              </div>

              {selectedLog.entity_name && (
                <div>
                  <Label className="text-gray-500">Entity Name</Label>
                  <p className="mt-1 font-medium">{selectedLog.entity_name}</p>
                </div>
              )}

              {selectedLog.ip_address && (
                <div>
                  <Label className="text-gray-500">IP Address</Label>
                  <p className="mt-1 font-mono text-sm">{selectedLog.ip_address}</p>
                </div>
              )}

              {selectedLog.details && Object.keys(selectedLog.details).length > 0 && (
                <div>
                  <Label className="text-gray-500">Additional Details</Label>
                  <pre className="mt-1 bg-gray-50 p-3 rounded text-sm overflow-x-auto">
                    {JSON.stringify(selectedLog.details, null, 2)}
                  </pre>
                </div>
              )}

              <div>
                <Label className="text-gray-500">Action Description</Label>
                <p className="mt-1 text-gray-700">
                  {selectedLog.action_description || actions[selectedLog.action] || selectedLog.action}
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AuditTrail;
