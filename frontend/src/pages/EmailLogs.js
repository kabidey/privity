import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { Mail, Search, Filter, Eye, RefreshCw, Trash2, CheckCircle, XCircle, AlertCircle, BarChart3 } from 'lucide-react';

const EmailLogs = () => {
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [selectedLog, setSelectedLog] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);
  
  // Filters
  const [filters, setFilters] = useState({
    status: '',
    template_key: '',
    to_email: '',
    related_entity_type: '',
    start_date: '',
    end_date: ''
  });
  const [pagination, setPagination] = useState({ limit: 50, skip: 0 });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPELevel = currentUser.role === 1 || currentUser.role === 2;
  const isPEDesk = currentUser.role === 1;

  useEffect(() => {
    if (!isPELevel) {
      toast.error('Access denied. Only PE Desk or PE Manager can view email logs.');
      navigate('/');
      return;
    }
    fetchLogs();
    fetchStats();
  }, [isPELevel, navigate]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.template_key) params.append('template_key', filters.template_key);
      if (filters.to_email) params.append('to_email', filters.to_email);
      if (filters.related_entity_type) params.append('related_entity_type', filters.related_entity_type);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      params.append('limit', pagination.limit);
      params.append('skip', pagination.skip);

      const response = await api.get(`/email-logs?${params.toString()}`);
      setLogs(response.data.logs);
      setTotal(response.data.total);
    } catch (error) {
      toast.error('Failed to load email logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/email-logs/stats?days=30');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const handleSearch = () => {
    setPagination({ ...pagination, skip: 0 });
    fetchLogs();
  };

  const handleClearFilters = () => {
    setFilters({
      status: '',
      template_key: '',
      to_email: '',
      related_entity_type: '',
      start_date: '',
      end_date: ''
    });
    setPagination({ limit: 50, skip: 0 });
  };

  const handleCleanup = async () => {
    if (!window.confirm('Are you sure you want to delete email logs older than 90 days? This action cannot be undone.')) {
      return;
    }
    try {
      const response = await api.delete('/email-logs/cleanup?days_to_keep=90');
      toast.success(response.data.message);
      fetchLogs();
      fetchStats();
    } catch (error) {
      toast.error('Failed to cleanup logs');
    }
  };

  const viewLogDetail = (log) => {
    setSelectedLog(log);
    setDetailOpen(true);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'sent':
        return <Badge className="bg-green-500 text-white"><CheckCircle className="w-3 h-3 mr-1" />Sent</Badge>;
      case 'failed':
        return <Badge className="bg-red-500 text-white"><XCircle className="w-3 h-3 mr-1" />Failed</Badge>;
      case 'skipped':
        return <Badge className="bg-yellow-500 text-white"><AlertCircle className="w-3 h-3 mr-1" />Skipped</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading && logs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="email-logs-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Email Audit Logs</h1>
          <p className="text-gray-500">Monitor and audit all email communications</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => { fetchLogs(); fetchStats(); }}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          {isPEDesk && (
            <Button variant="destructive" onClick={handleCleanup}>
              <Trash2 className="w-4 h-4 mr-2" />
              Cleanup Old Logs
            </Button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Emails Sent</p>
                  <p className="text-2xl font-bold text-green-600">{stats.total_sent}</p>
                </div>
                <CheckCircle className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Failed</p>
                  <p className="text-2xl font-bold text-red-600">{stats.total_failed}</p>
                </div>
                <XCircle className="w-8 h-8 text-red-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Skipped</p>
                  <p className="text-2xl font-bold text-yellow-600">{stats.total_skipped}</p>
                </div>
                <AlertCircle className="w-8 h-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Success Rate</p>
                  <p className="text-2xl font-bold text-emerald-600">
                    {stats.total_sent + stats.total_failed > 0 
                      ? Math.round((stats.total_sent / (stats.total_sent + stats.total_failed)) * 100) 
                      : 0}%
                  </p>
                </div>
                <BarChart3 className="w-8 h-8 text-emerald-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="logs" className="w-full">
        <TabsList>
          <TabsTrigger value="logs">Email Logs</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
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
              <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
                <div>
                  <Label>Status</Label>
                  <Select value={filters.status} onValueChange={(v) => setFilters({ ...filters, status: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="All Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Status</SelectItem>
                      <SelectItem value="sent">Sent</SelectItem>
                      <SelectItem value="failed">Failed</SelectItem>
                      <SelectItem value="skipped">Skipped</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Template</Label>
                  <Input
                    placeholder="Template key..."
                    value={filters.template_key}
                    onChange={(e) => setFilters({ ...filters, template_key: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Recipient Email</Label>
                  <Input
                    placeholder="Search email..."
                    value={filters.to_email}
                    onChange={(e) => setFilters({ ...filters, to_email: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Entity Type</Label>
                  <Select value={filters.related_entity_type} onValueChange={(v) => setFilters({ ...filters, related_entity_type: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="All Types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Types</SelectItem>
                      <SelectItem value="booking">Booking</SelectItem>
                      <SelectItem value="client">Client</SelectItem>
                      <SelectItem value="rp">Referral Partner</SelectItem>
                      <SelectItem value="user">User</SelectItem>
                    </SelectContent>
                  </Select>
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
                <Mail className="w-5 h-5" />
                Email Logs ({total})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Recipient</TableHead>
                      <TableHead>Subject</TableHead>
                      <TableHead>Template</TableHead>
                      <TableHead>Entity</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                          No email logs found
                        </TableCell>
                      </TableRow>
                    ) : (
                      logs.map((log) => (
                        <TableRow key={log.id} data-testid={`email-log-${log.id}`}>
                          <TableCell className="whitespace-nowrap text-sm">
                            {formatDate(log.created_at)}
                          </TableCell>
                          <TableCell>{getStatusBadge(log.status)}</TableCell>
                          <TableCell className="max-w-[200px] truncate" title={log.to_email}>
                            {log.to_email}
                            {log.cc_email && (
                              <span className="text-xs text-gray-400 block">CC: {log.cc_email}</span>
                            )}
                          </TableCell>
                          <TableCell className="max-w-[250px] truncate" title={log.subject}>
                            {log.subject}
                          </TableCell>
                          <TableCell>
                            {log.template_key ? (
                              <Badge variant="outline">{log.template_key}</Badge>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {log.related_entity_type ? (
                              <Badge variant="secondary">
                                {log.related_entity_type}
                              </Badge>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => viewLogDetail(log)}
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
          {stats && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* By Template */}
              <Card>
                <CardHeader>
                  <CardTitle>Emails by Template (Last 30 Days)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(stats.by_template).map(([template, count]) => (
                      <div key={template} className="flex items-center justify-between">
                        <span className="text-sm font-medium">{template || 'Direct Email'}</span>
                        <Badge variant="secondary">{count}</Badge>
                      </div>
                    ))}
                    {Object.keys(stats.by_template).length === 0 && (
                      <p className="text-gray-500 text-center py-4">No data available</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* By Entity Type */}
              <Card>
                <CardHeader>
                  <CardTitle>Emails by Entity Type (Last 30 Days)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(stats.by_entity_type).map(([entity, count]) => (
                      <div key={entity} className="flex items-center justify-between">
                        <span className="text-sm font-medium capitalize">{entity}</span>
                        <Badge variant="secondary">{count}</Badge>
                      </div>
                    ))}
                    {Object.keys(stats.by_entity_type).length === 0 && (
                      <p className="text-gray-500 text-center py-4">No data available</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Recent Failures */}
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-red-600">
                    <XCircle className="w-5 h-5" />
                    Recent Failures
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {stats.recent_failures.length > 0 ? (
                    <div className="space-y-3">
                      {stats.recent_failures.map((failure) => (
                        <div key={failure.id} className="border rounded-lg p-3 bg-red-50">
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-medium">{failure.to_email}</p>
                              <p className="text-sm text-gray-600">{failure.subject}</p>
                            </div>
                            <span className="text-xs text-gray-400">{formatDate(failure.created_at)}</span>
                          </div>
                          {failure.error_message && (
                            <p className="text-sm text-red-600 mt-2 bg-red-100 p-2 rounded">
                              Error: {failure.error_message}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No recent failures - great job!</p>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Mail className="w-5 h-5" />
              Email Log Details
            </DialogTitle>
          </DialogHeader>
          {selectedLog && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-500">Status</Label>
                  <div className="mt-1">{getStatusBadge(selectedLog.status)}</div>
                </div>
                <div>
                  <Label className="text-gray-500">Date</Label>
                  <p className="mt-1">{formatDate(selectedLog.created_at)}</p>
                </div>
              </div>

              <div>
                <Label className="text-gray-500">Recipient</Label>
                <p className="mt-1 font-medium">{selectedLog.to_email}</p>
                {selectedLog.cc_email && (
                  <p className="text-sm text-gray-500">CC: {selectedLog.cc_email}</p>
                )}
              </div>

              <div>
                <Label className="text-gray-500">Subject</Label>
                <p className="mt-1">{selectedLog.subject}</p>
              </div>

              {selectedLog.template_key && (
                <div>
                  <Label className="text-gray-500">Template</Label>
                  <Badge variant="outline" className="mt-1">{selectedLog.template_key}</Badge>
                </div>
              )}

              {selectedLog.related_entity_type && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-gray-500">Related Entity Type</Label>
                    <Badge variant="secondary" className="mt-1 capitalize">{selectedLog.related_entity_type}</Badge>
                  </div>
                  <div>
                    <Label className="text-gray-500">Entity ID</Label>
                    <p className="mt-1 text-sm font-mono">{selectedLog.related_entity_id || '-'}</p>
                  </div>
                </div>
              )}

              {selectedLog.error_message && (
                <div>
                  <Label className="text-gray-500">Error Message</Label>
                  <p className="mt-1 text-red-600 bg-red-50 p-3 rounded">{selectedLog.error_message}</p>
                </div>
              )}

              {selectedLog.variables && Object.keys(selectedLog.variables).length > 0 && (
                <div>
                  <Label className="text-gray-500">Template Variables</Label>
                  <pre className="mt-1 bg-gray-50 p-3 rounded text-sm overflow-x-auto">
                    {JSON.stringify(selectedLog.variables, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EmailLogs;
