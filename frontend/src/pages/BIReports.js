import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '../utils/api';
import { useProtectedPage } from '../hooks/useProtectedPage';
import { 
  BarChart3, Download, RefreshCw, Plus, Filter, Save, 
  FileSpreadsheet, TrendingUp, Users, Package, IndianRupee, 
  Calendar, X, Play, Trash2
} from 'lucide-react';

const BIReports = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  
  // Report configuration state
  const [reportType, setReportType] = useState('');
  const [selectedDimensions, setSelectedDimensions] = useState([]);
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [filters, setFilters] = useState([]);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [sortBy, setSortBy] = useState('');
  const [sortOrder, setSortOrder] = useState('desc');
  const [limit, setLimit] = useState(100);
  
  // Report results
  const [reportData, setReportData] = useState(null);
  
  // Saved reports
  const [savedReports, setSavedReports] = useState([]);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveDescription, setSaveDescription] = useState('');
  
  const { isLoading, isAuthorized, hasPermission } = useProtectedPage({
    allowIf: ({ isPELevel, hasPermission }) => isPELevel || hasPermission('reports.bi_builder'),
    deniedMessage: 'Access denied. You need BI Report Builder permission.'
  });

  useEffect(() => {
    if (!isAuthorized) return;
    fetchConfig();
    fetchSavedReports();
  }, [isAuthorized]);

  const fetchConfig = async () => {
    try {
      const response = await api.get('/bi-reports/config');
      setConfig(response.data);
    } catch (error) {
      toast.error('Failed to load report configuration');
    } finally {
      setLoading(false);
    }
  };

  const fetchSavedReports = async () => {
    try {
      const response = await api.get('/bi-reports/saved');
      setSavedReports(response.data);
    } catch (error) {
      console.error('Failed to load saved reports');
    }
  };

  const handleGenerateReport = async () => {
    if (!reportType) {
      toast.error('Please select a report type');
      return;
    }
    if (selectedDimensions.length === 0) {
      toast.error('Please select at least one dimension');
      return;
    }
    if (selectedMetrics.length === 0) {
      toast.error('Please select at least one metric');
      return;
    }

    setGenerating(true);
    try {
      const response = await api.post('/bi-reports/generate', {
        report_type: reportType,
        dimensions: selectedDimensions,
        metrics: selectedMetrics,
        filters: filters,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        sort_by: sortBy || null,
        sort_order: sortOrder,
        limit: limit
      });
      setReportData(response.data);
      toast.success(`Report generated: ${response.data.total_rows} rows`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async () => {
    if (!reportType) {
      toast.error('Please configure a report first');
      return;
    }

    setExporting(true);
    try {
      const response = await api.post('/bi-reports/export', {
        report_type: reportType,
        dimensions: selectedDimensions,
        metrics: selectedMetrics,
        filters: filters,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        sort_by: sortBy || null,
        sort_order: sortOrder,
        limit: limit
      }, { responseType: 'blob' });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `bi_report_${reportType}_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Report exported successfully');
    } catch (error) {
      toast.error('Failed to export report');
    } finally {
      setExporting(false);
    }
  };

  const handleSaveReport = async () => {
    if (!saveName.trim()) {
      toast.error('Please enter a report name');
      return;
    }

    try {
      await api.post(`/bi-reports/save?name=${encodeURIComponent(saveName)}&description=${encodeURIComponent(saveDescription)}`, {
        report_type: reportType,
        dimensions: selectedDimensions,
        metrics: selectedMetrics,
        filters: filters,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        sort_by: sortBy || null,
        sort_order: sortOrder,
        limit: limit
      });
      toast.success('Report template saved');
      setSaveDialogOpen(false);
      setSaveName('');
      setSaveDescription('');
      fetchSavedReports();
    } catch (error) {
      toast.error('Failed to save report template');
    }
  };

  const loadSavedReport = (template) => {
    const cfg = template.config;
    setReportType(cfg.report_type);
    setSelectedDimensions(cfg.dimensions || []);
    setSelectedMetrics(cfg.metrics || []);
    setFilters(cfg.filters || []);
    setDateFrom(cfg.date_from || '');
    setDateTo(cfg.date_to || '');
    setSortBy(cfg.sort_by || '');
    setSortOrder(cfg.sort_order || 'desc');
    setLimit(cfg.limit || 100);
    toast.success(`Loaded: ${template.name}`);
  };

  const addFilter = () => {
    setFilters([...filters, { field: '', operator: 'eq', value: '' }]);
  };

  const updateFilter = (index, key, value) => {
    const updated = [...filters];
    updated[index][key] = value;
    setFilters(updated);
  };

  const removeFilter = (index) => {
    setFilters(filters.filter((_, i) => i !== index));
  };

  const toggleDimension = (dim) => {
    if (selectedDimensions.includes(dim)) {
      setSelectedDimensions(selectedDimensions.filter(d => d !== dim));
    } else {
      setSelectedDimensions([...selectedDimensions, dim]);
    }
  };

  const toggleMetric = (metric) => {
    if (selectedMetrics.includes(metric)) {
      setSelectedMetrics(selectedMetrics.filter(m => m !== metric));
    } else {
      setSelectedMetrics([...selectedMetrics, metric]);
    }
  };

  const formatValue = (value) => {
    if (typeof value === 'number') {
      if (value > 1000000) return `₹${(value / 10000000).toFixed(2)}Cr`;
      if (value > 1000) return `₹${(value / 100000).toFixed(2)}L`;
      return value.toFixed(2);
    }
    return value || '-';
  };

  const getReportIcon = (type) => {
    const icons = {
      bookings: <FileSpreadsheet className="h-5 w-5" />,
      clients: <Users className="h-5 w-5" />,
      revenue: <IndianRupee className="h-5 w-5" />,
      inventory: <Package className="h-5 w-5" />,
      payments: <IndianRupee className="h-5 w-5" />,
      pnl: <TrendingUp className="h-5 w-5" />
    };
    return icons[type] || <BarChart3 className="h-5 w-5" />;
  };

  if (isLoading || loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  const currentConfig = config?.configs?.[reportType];

  return (
    <div className="space-y-6" data-testid="bi-reports-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="w-7 h-7 text-emerald-600" />
            Business Intelligence
          </h1>
          <p className="text-muted-foreground">Build custom reports with multiple dimensions and filters</p>
        </div>
        <div className="flex gap-2">
          {reportData && (
            <>
              <Button variant="outline" onClick={() => setSaveDialogOpen(true)}>
                <Save className="w-4 h-4 mr-2" />
                Save Template
              </Button>
              <Button onClick={handleExport} disabled={exporting} className="bg-green-600 hover:bg-green-700">
                {exporting ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
                Export Excel
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Report Configuration Panel */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Report Type</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {config?.report_types?.map((type) => (
                <div
                  key={type.key}
                  className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                    reportType === type.key 
                      ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950' 
                      : 'border-transparent hover:border-gray-200'
                  }`}
                  onClick={() => {
                    setReportType(type.key);
                    setSelectedDimensions([]);
                    setSelectedMetrics([]);
                    setReportData(null);
                  }}
                  data-testid={`report-type-${type.key}`}
                >
                  <div className="flex items-center gap-2">
                    {getReportIcon(type.key)}
                    <span className="font-medium">{type.label}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{type.description}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Saved Reports */}
          {savedReports.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Saved Templates</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 max-h-48 overflow-y-auto">
                {savedReports.map((template) => (
                  <div
                    key={template.id}
                    className="p-2 rounded border hover:bg-gray-50 cursor-pointer"
                    onClick={() => loadSavedReport(template)}
                  >
                    <p className="font-medium text-sm">{template.name}</p>
                    <p className="text-xs text-muted-foreground">{template.config?.report_type}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Configuration Details */}
        <div className="lg:col-span-3 space-y-4">
          {reportType && currentConfig && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Filter className="w-5 h-5" />
                    Report Configuration
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="dimensions">
                    <TabsList className="mb-4">
                      <TabsTrigger value="dimensions">Dimensions ({selectedDimensions.length})</TabsTrigger>
                      <TabsTrigger value="metrics">Metrics ({selectedMetrics.length})</TabsTrigger>
                      <TabsTrigger value="filters">Filters ({filters.length})</TabsTrigger>
                      <TabsTrigger value="options">Options</TabsTrigger>
                    </TabsList>

                    <TabsContent value="dimensions" className="space-y-4">
                      <p className="text-sm text-muted-foreground">Select fields to group your data by:</p>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {currentConfig.dimensions?.map((dim) => (
                          <div
                            key={dim.key}
                            className={`flex items-center gap-2 p-2 rounded border cursor-pointer ${
                              selectedDimensions.includes(dim.key) ? 'bg-emerald-50 border-emerald-300' : ''
                            }`}
                            onClick={() => toggleDimension(dim.key)}
                          >
                            <Checkbox checked={selectedDimensions.includes(dim.key)} />
                            <span className="text-sm">{dim.label}</span>
                          </div>
                        ))}
                      </div>
                    </TabsContent>

                    <TabsContent value="metrics" className="space-y-4">
                      <p className="text-sm text-muted-foreground">Select values to calculate:</p>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {currentConfig.metrics?.map((metric) => (
                          <div
                            key={metric.key}
                            className={`flex items-center gap-2 p-2 rounded border cursor-pointer ${
                              selectedMetrics.includes(metric.key) ? 'bg-blue-50 border-blue-300' : ''
                            }`}
                            onClick={() => toggleMetric(metric.key)}
                          >
                            <Checkbox checked={selectedMetrics.includes(metric.key)} />
                            <span className="text-sm">{metric.label}</span>
                          </div>
                        ))}
                      </div>
                    </TabsContent>

                    <TabsContent value="filters" className="space-y-4">
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-muted-foreground">Add conditions to filter data:</p>
                        <Button variant="outline" size="sm" onClick={addFilter}>
                          <Plus className="w-4 h-4 mr-1" /> Add Filter
                        </Button>
                      </div>
                      {filters.map((filter, index) => (
                        <div key={index} className="flex gap-2 items-center">
                          <Select value={filter.field} onValueChange={(v) => updateFilter(index, 'field', v)}>
                            <SelectTrigger className="w-40">
                              <SelectValue placeholder="Field" />
                            </SelectTrigger>
                            <SelectContent>
                              {currentConfig.dimensions?.map((d) => (
                                <SelectItem key={d.key} value={d.key}>{d.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Select value={filter.operator} onValueChange={(v) => updateFilter(index, 'operator', v)}>
                            <SelectTrigger className="w-32">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="eq">Equals</SelectItem>
                              <SelectItem value="ne">Not Equals</SelectItem>
                              <SelectItem value="contains">Contains</SelectItem>
                              <SelectItem value="gt">Greater Than</SelectItem>
                              <SelectItem value="lt">Less Than</SelectItem>
                            </SelectContent>
                          </Select>
                          <Input
                            value={filter.value}
                            onChange={(e) => updateFilter(index, 'value', e.target.value)}
                            placeholder="Value"
                            className="flex-1"
                          />
                          <Button variant="ghost" size="icon" onClick={() => removeFilter(index)}>
                            <X className="w-4 h-4 text-red-500" />
                          </Button>
                        </div>
                      ))}
                    </TabsContent>

                    <TabsContent value="options" className="space-y-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <Label>Date From</Label>
                          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
                        </div>
                        <div>
                          <Label>Date To</Label>
                          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
                        </div>
                        <div>
                          <Label>Sort By</Label>
                          <Select value={sortBy} onValueChange={setSortBy}>
                            <SelectTrigger>
                              <SelectValue placeholder="Select..." />
                            </SelectTrigger>
                            <SelectContent>
                              {selectedMetrics.map((m) => (
                                <SelectItem key={m} value={m}>{m}</SelectItem>
                              ))}
                              <SelectItem value="count">Count</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label>Limit</Label>
                          <Input type="number" value={limit} onChange={(e) => setLimit(parseInt(e.target.value) || 100)} />
                        </div>
                      </div>
                    </TabsContent>
                  </Tabs>

                  <div className="mt-4 flex justify-end">
                    <Button 
                      onClick={handleGenerateReport} 
                      disabled={generating || selectedDimensions.length === 0 || selectedMetrics.length === 0}
                      className="bg-emerald-600 hover:bg-emerald-700"
                      data-testid="generate-report-btn"
                    >
                      {generating ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
                      Generate Report
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Report Results */}
              {reportData && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>Results ({reportData.total_rows} rows)</span>
                      <Badge variant="outline">{reportData.report_type}</Badge>
                    </CardTitle>
                    {reportData.date_range?.from && (
                      <CardDescription>
                        {reportData.date_range.from} to {reportData.date_range.to || 'Present'}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                    {/* Summary */}
                    {Object.keys(reportData.summary || {}).length > 0 && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        {Object.entries(reportData.summary).map(([key, stats]) => (
                          <div key={key} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                            <p className="text-xs text-muted-foreground">{key.replace(/_/g, ' ').toUpperCase()}</p>
                            <p className="text-xl font-bold">{formatValue(stats.total)}</p>
                            <p className="text-xs">Avg: {formatValue(stats.avg)}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Data Table */}
                    <div className="border rounded-lg overflow-hidden">
                      <div className="overflow-x-auto max-h-96">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              {reportData.dimensions?.map((dim) => (
                                <TableHead key={dim}>{dim.replace(/_/g, ' ')}</TableHead>
                              ))}
                              {reportData.metrics?.map((metric) => (
                                <TableHead key={metric} className="text-right">{metric.replace(/_/g, ' ')}</TableHead>
                              ))}
                              <TableHead className="text-right">Count</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {reportData.data?.slice(0, 50).map((row, idx) => (
                              <TableRow key={idx}>
                                {reportData.dimensions?.map((dim) => (
                                  <TableCell key={dim}>{row[dim] || '-'}</TableCell>
                                ))}
                                {reportData.metrics?.map((metric) => (
                                  <TableCell key={metric} className="text-right font-mono">
                                    {formatValue(row[metric])}
                                  </TableCell>
                                ))}
                                <TableCell className="text-right font-mono">{row.count || 0}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                      {reportData.data?.length > 50 && (
                        <div className="p-2 text-center text-sm text-muted-foreground bg-gray-50">
                          Showing 50 of {reportData.total_rows} rows. Export to Excel for full data.
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {!reportType && (
            <Card className="flex items-center justify-center h-64">
              <div className="text-center text-muted-foreground">
                <BarChart3 className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>Select a report type to begin</p>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Save Template Dialog */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Report Template</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Template Name</Label>
              <Input value={saveName} onChange={(e) => setSaveName(e.target.value)} placeholder="My Custom Report" />
            </div>
            <div>
              <Label>Description (Optional)</Label>
              <Input value={saveDescription} onChange={(e) => setSaveDescription(e.target.value)} placeholder="Description..." />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveReport}>Save Template</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default BIReports;
