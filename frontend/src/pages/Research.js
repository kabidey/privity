import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { ScrollArea } from '../components/ui/scroll-area';
import { toast } from 'sonner';
import api from '../services/api';
import { 
  Upload, FileText, Search, Trash2, Eye, Download, 
  Bot, Send, Loader2, FileSpreadsheet, FileCheck,
  TrendingUp, BarChart3, BookOpen, RefreshCw
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Research = () => {
  const [loading, setLoading] = useState(true);
  const [reports, setReports] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [stats, setStats] = useState(null);
  const [userRole, setUserRole] = useState(6);
  
  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    stock_id: '',
    title: '',
    description: '',
    report_type: 'general'
  });
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);
  
  // AI Chat state
  const [aiQuery, setAiQuery] = useState('');
  const [aiStockId, setAiStockId] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  
  // Filter state
  const [filterStock, setFilterStock] = useState('all');
  const [filterType, setFilterType] = useState('all');

  const isPELevel = userRole <= 2;

  useEffect(() => {
    fetchData();
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    setUserRole(user.role || 6);
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [reportsRes, stocksRes, statsRes] = await Promise.all([
        api.get('/research/reports'),
        api.get('/stocks'),
        api.get('/research/stats')
      ]);
      setReports(reportsRes.data);
      setStocks(stocksRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load research data');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const maxSize = 50 * 1024 * 1024; // 50MB
      if (file.size > maxSize) {
        toast.error('File size exceeds 50MB limit');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!uploadForm.stock_id || !uploadForm.title || !selectedFile) {
      toast.error('Please fill all required fields and select a file');
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('stock_id', uploadForm.stock_id);
      formData.append('title', uploadForm.title);
      formData.append('description', uploadForm.description);
      formData.append('report_type', uploadForm.report_type);
      formData.append('file', selectedFile);

      await api.post('/research/reports', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast.success('Research report uploaded successfully');
      setUploadForm({ stock_id: '', title: '', description: '', report_type: 'general' });
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload report');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (reportId) => {
    if (!window.confirm('Are you sure you want to delete this report?')) return;

    try {
      await api.delete(`/research/reports/${reportId}`);
      toast.success('Report deleted successfully');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete report');
    }
  };

  const handleAIQuery = async () => {
    if (!aiQuery.trim()) {
      toast.error('Please enter a question');
      return;
    }

    try {
      setAiLoading(true);
      const formData = new FormData();
      formData.append('query', aiQuery);
      if (aiStockId) formData.append('stock_id', aiStockId);

      const response = await api.post('/research/ai-research', formData);
      
      setAiResponse(response.data);
      setChatHistory(prev => [...prev, {
        query: aiQuery,
        response: response.data.response,
        stock_id: aiStockId,
        timestamp: new Date().toISOString()
      }]);
      setAiQuery('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'AI research failed');
    } finally {
      setAiLoading(false);
    }
  };

  const getFullUrl = (url) => {
    if (!url) return null;
    if (url.startsWith('http')) return url;
    return `${API_URL}/api${url}`;
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const getReportTypeColor = (type) => {
    const colors = {
      general: 'bg-gray-100 text-gray-700',
      quarterly: 'bg-blue-100 text-blue-700',
      annual: 'bg-purple-100 text-purple-700',
      analysis: 'bg-emerald-100 text-emerald-700',
      recommendation: 'bg-amber-100 text-amber-700'
    };
    return colors[type] || colors.general;
  };

  const filteredReports = reports.filter(report => {
    if (filterStock !== 'all' && report.stock_id !== filterStock) return false;
    if (filterType !== 'all' && report.report_type !== filterType) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="research-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-emerald-600" />
            Research Center
          </h1>
          <p className="text-muted-foreground">Access research reports and AI-powered stock analysis</p>
        </div>
        <Button onClick={fetchData} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-100 dark:bg-emerald-900 rounded-full">
                  <FileText className="h-5 w-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Reports</p>
                  <p className="text-2xl font-bold">{stats.total_reports}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-full">
                  <BarChart3 className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Analysis Reports</p>
                  <p className="text-2xl font-bold">{stats.by_type?.analysis || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-full">
                  <FileSpreadsheet className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Quarterly Reports</p>
                  <p className="text-2xl font-bold">{stats.by_type?.quarterly || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 dark:bg-amber-900 rounded-full">
                  <TrendingUp className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Recommendations</p>
                  <p className="text-2xl font-bold">{stats.by_type?.recommendation || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="reports" className="space-y-4">
        <TabsList>
          <TabsTrigger value="reports" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Research Reports
          </TabsTrigger>
          <TabsTrigger value="ai" className="flex items-center gap-2">
            <Bot className="h-4 w-4" />
            AI Research Assistant
          </TabsTrigger>
          {isPELevel && (
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              Upload Report
            </TabsTrigger>
          )}
        </TabsList>

        {/* Research Reports Tab */}
        <TabsContent value="reports">
          <Card>
            <CardHeader>
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <CardTitle>Research Reports</CardTitle>
                  <CardDescription>Browse and access research reports for all stocks</CardDescription>
                </div>
                <div className="flex gap-2">
                  <Select value={filterStock} onValueChange={setFilterStock}>
                    <SelectTrigger className="w-[180px]">
                      <SelectValue placeholder="Filter by Stock" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Stocks</SelectItem>
                      {stocks.map(stock => (
                        <SelectItem key={stock.id} value={stock.id}>
                          {stock.symbol}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select value={filterType} onValueChange={setFilterType}>
                    <SelectTrigger className="w-[150px]">
                      <SelectValue placeholder="Filter by Type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="general">General</SelectItem>
                      <SelectItem value="quarterly">Quarterly</SelectItem>
                      <SelectItem value="annual">Annual</SelectItem>
                      <SelectItem value="analysis">Analysis</SelectItem>
                      <SelectItem value="recommendation">Recommendation</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {filteredReports.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No research reports found</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Title</TableHead>
                        <TableHead>Stock</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Size</TableHead>
                        <TableHead>Uploaded By</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredReports.map((report) => (
                        <TableRow key={report.id}>
                          <TableCell>
                            <div>
                              <p className="font-medium">{report.title}</p>
                              {report.description && (
                                <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                  {report.description}
                                </p>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="font-mono">
                              {report.stock_symbol}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge className={getReportTypeColor(report.report_type)}>
                              {report.report_type}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm">
                            {formatFileSize(report.file_size)}
                          </TableCell>
                          <TableCell className="text-sm">
                            {report.uploaded_by_name}
                          </TableCell>
                          <TableCell className="text-sm">
                            {formatDate(report.created_at)}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => window.open(getFullUrl(report.file_url), '_blank')}
                                title="View Report"
                                data-testid={`view-report-${report.id}`}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const link = document.createElement('a');
                                  link.href = getFullUrl(report.file_url);
                                  link.download = report.file_name;
                                  link.click();
                                }}
                                title="Download Report"
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                              {isPELevel && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDelete(report.id)}
                                  className="text-red-600"
                                  title="Delete Report"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI Research Assistant Tab */}
        <TabsContent value="ai">
          <div className="grid md:grid-cols-2 gap-6">
            {/* AI Chat Input */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-emerald-600" />
                  AI Research Assistant
                </CardTitle>
                <CardDescription>
                  Ask questions about stocks, market trends, and investment analysis
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Select Stock (Optional)</Label>
                  <Select value={aiStockId} onValueChange={setAiStockId}>
                    <SelectTrigger>
                      <SelectValue placeholder="General research or select a stock" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">General Research</SelectItem>
                      {stocks.map(stock => (
                        <SelectItem key={stock.id} value={stock.id}>
                          {stock.symbol} - {stock.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Your Question</Label>
                  <Textarea
                    placeholder="Ask about market analysis, investment strategies, stock fundamentals..."
                    value={aiQuery}
                    onChange={(e) => setAiQuery(e.target.value)}
                    rows={4}
                    data-testid="ai-query-input"
                  />
                </div>

                <Button 
                  onClick={handleAIQuery} 
                  disabled={aiLoading || !aiQuery.trim()}
                  className="w-full"
                  data-testid="ai-query-submit"
                >
                  {aiLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Get Analysis
                    </>
                  )}
                </Button>

                {/* Sample Questions */}
                <div className="pt-4 border-t">
                  <p className="text-sm text-muted-foreground mb-2">Sample questions:</p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      "What are key factors for analyzing unlisted stocks?",
                      "Explain PE ratio and its significance",
                      "How to evaluate management quality?"
                    ].map((q, i) => (
                      <Button
                        key={i}
                        variant="outline"
                        size="sm"
                        className="text-xs"
                        onClick={() => setAiQuery(q)}
                      >
                        {q.slice(0, 30)}...
                      </Button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* AI Response */}
            <Card>
              <CardHeader>
                <CardTitle>Analysis Response</CardTitle>
              </CardHeader>
              <CardContent>
                {aiResponse ? (
                  <div className="space-y-4">
                    <ScrollArea className="h-[400px] pr-4">
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <div className="whitespace-pre-wrap text-sm">
                          {aiResponse.response}
                        </div>
                      </div>
                    </ScrollArea>
                    <div className="pt-4 border-t">
                      <p className="text-xs text-muted-foreground italic">
                        {aiResponse.disclaimer}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Ask a question to get AI-powered research insights</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Chat History */}
          {chatHistory.length > 0 && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Recent Queries</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {chatHistory.slice(-5).reverse().map((item, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <Search className="h-4 w-4 mt-1 text-emerald-600" />
                        <div className="flex-1">
                          <p className="font-medium text-sm">{item.query}</p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {new Date(item.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Upload Tab (PE Level only) */}
        {isPELevel && (
          <TabsContent value="upload">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="h-5 w-5 text-emerald-600" />
                  Upload Research Report
                </CardTitle>
                <CardDescription>
                  Upload research reports for stocks. Supported formats: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV (Max 50MB)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label>Stock *</Label>
                      <Select 
                        value={uploadForm.stock_id} 
                        onValueChange={(v) => setUploadForm(p => ({...p, stock_id: v}))}
                      >
                        <SelectTrigger data-testid="upload-stock-select">
                          <SelectValue placeholder="Select a stock" />
                        </SelectTrigger>
                        <SelectContent>
                          {stocks.map(stock => (
                            <SelectItem key={stock.id} value={stock.id}>
                              {stock.symbol} - {stock.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label>Report Title *</Label>
                      <Input
                        placeholder="e.g., Q3 2024 Financial Analysis"
                        value={uploadForm.title}
                        onChange={(e) => setUploadForm(p => ({...p, title: e.target.value}))}
                        data-testid="upload-title-input"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Report Type</Label>
                      <Select 
                        value={uploadForm.report_type} 
                        onValueChange={(v) => setUploadForm(p => ({...p, report_type: v}))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="general">General</SelectItem>
                          <SelectItem value="quarterly">Quarterly Report</SelectItem>
                          <SelectItem value="annual">Annual Report</SelectItem>
                          <SelectItem value="analysis">Analysis</SelectItem>
                          <SelectItem value="recommendation">Recommendation</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label>Description (Optional)</Label>
                      <Textarea
                        placeholder="Brief description of the report..."
                        value={uploadForm.description}
                        onChange={(e) => setUploadForm(p => ({...p, description: e.target.value}))}
                        rows={3}
                      />
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label>Select File *</Label>
                      <div className="border-2 border-dashed rounded-lg p-6 text-center">
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv"
                          onChange={handleFileChange}
                          className="hidden"
                          data-testid="upload-file-input"
                        />
                        {selectedFile ? (
                          <div className="space-y-2">
                            <FileCheck className="h-12 w-12 mx-auto text-emerald-600" />
                            <p className="font-medium">{selectedFile.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {formatFileSize(selectedFile.size)}
                            </p>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedFile(null);
                                if (fileInputRef.current) fileInputRef.current.value = '';
                              }}
                            >
                              Remove
                            </Button>
                          </div>
                        ) : (
                          <div 
                            className="cursor-pointer"
                            onClick={() => fileInputRef.current?.click()}
                          >
                            <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-2" />
                            <p className="text-muted-foreground">
                              Click to select a file or drag and drop
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                              PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV
                            </p>
                          </div>
                        )}
                      </div>
                    </div>

                    <Button
                      onClick={handleUpload}
                      disabled={uploading || !uploadForm.stock_id || !uploadForm.title || !selectedFile}
                      className="w-full"
                      data-testid="upload-submit-btn"
                    >
                      {uploading ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <Upload className="h-4 w-4 mr-2" />
                          Upload Report
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
};

export default Research;
