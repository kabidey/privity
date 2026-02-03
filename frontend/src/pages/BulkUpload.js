import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { 
  Upload, 
  Download, 
  Users, 
  Building2, 
  Package, 
  ShoppingCart, 
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  FileSpreadsheet,
  RefreshCw
} from 'lucide-react';

const BulkUpload = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [stats, setStats] = useState({});
  const [uploadResults, setUploadResults] = useState(null);
  const [activeTab, setActiveTab] = useState('clients');
  const fileInputRef = useRef(null);

  const { user, isPEDesk } = useCurrentUser();

  const entityConfig = {
    clients: {
      icon: Users,
      title: 'Clients',
      description: 'Upload client data with PAN, DP ID, and contact information',
      color: 'text-blue-500',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
      endpoint: '/bulk-upload/clients',
      templateEndpoint: '/bulk-upload/template/clients'
    },
    vendors: {
      icon: Building2,
      title: 'Vendors',
      description: 'Upload vendor/supplier data for stock purchases',
      color: 'text-purple-500',
      bgColor: 'bg-purple-50 dark:bg-purple-900/20',
      endpoint: '/bulk-upload/vendors',
      templateEndpoint: '/bulk-upload/template/vendors'
    },
    stocks: {
      icon: Package,
      title: 'Stocks',
      description: 'Upload stock master data with symbols and ISIN',
      color: 'text-emerald-500',
      bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
      endpoint: '/bulk-upload/stocks',
      templateEndpoint: '/bulk-upload/template/stocks'
    },
    purchases: {
      icon: ShoppingCart,
      title: 'Purchases',
      description: 'Upload purchase records (requires existing vendors & stocks)',
      color: 'text-orange-500',
      bgColor: 'bg-orange-50 dark:bg-orange-900/20',
      endpoint: '/bulk-upload/purchases',
      templateEndpoint: '/bulk-upload/template/purchases'
    },
    bookings: {
      icon: FileText,
      title: 'Bookings',
      description: 'Upload booking records (requires existing clients & stocks)',
      color: 'text-pink-500',
      bgColor: 'bg-pink-50 dark:bg-pink-900/20',
      endpoint: '/bulk-upload/bookings',
      templateEndpoint: '/bulk-upload/template/bookings'
    }
  };

  useEffect(() => {
    // Wait for user to load before checking permissions
    if (user === null) return;
    
    if (!isPEDesk) {
      navigate('/');
      return;
    }
    fetchStats();
  }, [user, isPEDesk]);

  const fetchStats = async () => {
    try {
      const response = await api.get('/bulk-upload/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats');
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = async (entityType) => {
    try {
      const response = await api.get(`/bulk-upload/template/${entityType}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `sample_${entityType}_upload.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success(`Downloaded ${entityType} template`);
    } catch (error) {
      toast.error('Failed to download template');
    }
  };

  const handleFileSelect = (entityType) => {
    setActiveTab(entityType);
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      toast.error('Please select a CSV file');
      return;
    }

    const config = entityConfig[activeTab];
    setUploading(true);
    setUploadResults(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post(config.endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setUploadResults({
        entityType: activeTab,
        ...response.data
      });

      if (response.data.added > 0) {
        toast.success(`Successfully added ${response.data.added} ${activeTab}`);
        fetchStats();
      } else if (response.data.skipped > 0) {
        toast.info(`All ${response.data.skipped} records were duplicates and skipped`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed');
      setUploadResults({
        entityType: activeTab,
        error: error.response?.data?.detail || 'Upload failed'
      });
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  if (!isPEDesk) return null;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="ios-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 page-enter" data-testid="bulk-upload-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">Bulk Upload</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Import data from CSV files</p>
        </div>
        <Button variant="outline" onClick={fetchStats} className="rounded-xl">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh Stats
        </Button>
      </div>

      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".csv"
        className="hidden"
      />

      {/* Current Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
        {Object.entries(entityConfig).map(([key, config]) => {
          const Icon = config.icon;
          return (
            <Card key={key} className={`${config.bgColor} border-0`}>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-xl bg-white dark:bg-gray-800 ${config.color}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {stats[key] ?? 0}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{config.title}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Upload Results */}
      {uploadResults && (
        <Card className={uploadResults.error ? 'border-red-200 dark:border-red-800' : 'border-emerald-200 dark:border-emerald-800'}>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              {uploadResults.error ? (
                <XCircle className="h-5 w-5 text-red-500" />
              ) : uploadResults.added > 0 ? (
                <CheckCircle className="h-5 w-5 text-emerald-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-amber-500" />
              )}
              Upload Results - {entityConfig[uploadResults.entityType]?.title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {uploadResults.error ? (
              <p className="text-red-600 dark:text-red-400">{uploadResults.error}</p>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-3">
                  <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                    Added: {uploadResults.added}
                  </Badge>
                  {uploadResults.skipped > 0 && (
                    <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                      Skipped (duplicates): {uploadResults.skipped}
                    </Badge>
                  )}
                </div>
                
                {uploadResults.errors?.length > 0 && (
                  <div className="mt-3">
                    <p className="text-sm font-medium text-red-600 dark:text-red-400 mb-2">Errors:</p>
                    <ul className="text-sm text-red-600 dark:text-red-400 space-y-1 max-h-32 overflow-y-auto">
                      {uploadResults.errors.map((err, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <XCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                          {err}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {uploadResults.skipped_pans?.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-gray-500">Skipped PANs: {uploadResults.skipped_pans.join(', ')}</p>
                  </div>
                )}
                
                {uploadResults.skipped_symbols?.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-gray-500">Skipped Symbols: {uploadResults.skipped_symbols.join(', ')}</p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Upload Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-5 h-auto p-1 bg-gray-100 dark:bg-gray-800 rounded-xl">
          {Object.entries(entityConfig).map(([key, config]) => {
            const Icon = config.icon;
            return (
              <TabsTrigger 
                key={key} 
                value={key}
                className="flex flex-col sm:flex-row items-center gap-1 sm:gap-2 py-2 px-2 sm:px-4 rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-gray-700"
              >
                <Icon className="h-4 w-4" />
                <span className="text-xs sm:text-sm hidden sm:inline">{config.title}</span>
              </TabsTrigger>
            );
          })}
        </TabsList>

        {Object.entries(entityConfig).map(([key, config]) => {
          const Icon = config.icon;
          return (
            <TabsContent key={key} value={key} className="mt-4">
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className={`p-3 rounded-xl ${config.bgColor}`}>
                      <Icon className={`h-6 w-6 ${config.color}`} />
                    </div>
                    <div>
                      <CardTitle>{config.title} Bulk Upload</CardTitle>
                      <CardDescription>{config.description}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Instructions */}
                  <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                    <h4 className="font-medium text-gray-900 dark:text-white mb-2">Instructions</h4>
                    <ol className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-decimal list-inside">
                      <li>Download the sample CSV template below</li>
                      <li>Fill in your data following the template format</li>
                      <li>Save the file as CSV (UTF-8 encoding recommended)</li>
                      <li>Upload the file - duplicates will be automatically skipped</li>
                    </ol>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-col sm:flex-row gap-3">
                    <Button 
                      variant="outline" 
                      onClick={() => downloadTemplate(key)}
                      className="flex-1 rounded-xl"
                      data-testid={`download-${key}-template`}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Download Sample Template
                    </Button>
                    <Button 
                      onClick={() => handleFileSelect(key)}
                      disabled={uploading}
                      className="flex-1 rounded-xl bg-emerald-500 hover:bg-emerald-600"
                      data-testid={`upload-${key}-btn`}
                    >
                      {uploading && activeTab === key ? (
                        <>
                          <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <Upload className="h-4 w-4 mr-2" />
                          Upload CSV File
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Tips */}
                  <div className="border-t pt-4">
                    <h4 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-amber-500" />
                      Tips
                    </h4>
                    <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                      {key === 'clients' && (
                        <>
                          <li>• PAN number and DP ID are required fields</li>
                          <li>• Duplicate PANs will be skipped automatically</li>
                          <li>• dp_type should be 'smifs' or 'outside'</li>
                        </>
                      )}
                      {key === 'vendors' && (
                        <>
                          <li>• Vendors are stored separately from clients</li>
                          <li>• PAN number and DP ID are required</li>
                          <li>• Use vendors for purchase records</li>
                        </>
                      )}
                      {key === 'stocks' && (
                        <>
                          <li>• Symbol and Name are required fields</li>
                          <li>• Duplicate symbols or ISINs will be skipped</li>
                          <li>• ISIN format: INE followed by 9 alphanumeric characters</li>
                        </>
                      )}
                      {key === 'purchases' && (
                        <>
                          <li>• Vendor PAN and Stock Symbol must already exist</li>
                          <li>• Date format: YYYY-MM-DD (e.g., 2026-01-15)</li>
                          <li>• Inventory is automatically updated</li>
                        </>
                      )}
                      {key === 'bookings' && (
                        <>
                          <li>• Client PAN and Stock Symbol must already exist</li>
                          <li>• Bookings are created in 'open' status</li>
                          <li>• booking_type: 'client', 'team', or 'own'</li>
                        </>
                      )}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          );
        })}
      </Tabs>

      {/* Recommended Order */}
      <Card className="border-dashed">
        <CardContent className="p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Recommended Upload Order</h3>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant="outline" className="bg-emerald-50 dark:bg-emerald-900/20">1. Stocks</Badge>
            <span className="text-gray-400">→</span>
            <Badge variant="outline" className="bg-purple-50 dark:bg-purple-900/20">2. Vendors</Badge>
            <span className="text-gray-400">→</span>
            <Badge variant="outline" className="bg-blue-50 dark:bg-blue-900/20">3. Clients</Badge>
            <span className="text-gray-400">→</span>
            <Badge variant="outline" className="bg-orange-50 dark:bg-orange-900/20">4. Purchases</Badge>
            <span className="text-gray-400">→</span>
            <Badge variant="outline" className="bg-pink-50 dark:bg-pink-900/20">5. Bookings</Badge>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Follow this order to ensure all references (vendor PAN, client PAN, stock symbol) exist before uploading dependent data.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default BulkUpload;
