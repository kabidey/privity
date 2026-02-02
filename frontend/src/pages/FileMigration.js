import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  HardDrive, 
  AlertTriangle, 
  Upload, 
  RefreshCw, 
  FileCheck, 
  FileX,
  Database,
  Check
} from 'lucide-react';

const FileMigration = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [missingFiles, setMissingFiles] = useState([]);
  const [uploading, setUploading] = useState(null);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    fetchStats();
    scanMissingFiles();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await api.get('/files/storage-stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch storage stats', error);
    }
  };

  const scanMissingFiles = async () => {
    setScanning(true);
    try {
      const response = await api.get('/files/scan-missing');
      setMissingFiles(response.data.missing_files || []);
    } catch (error) {
      toast.error('Failed to scan for missing files');
    } finally {
      setScanning(false);
      setLoading(false);
    }
  };

  const handleFileUpload = async (file, entityType, entityId, docType) => {
    const formData = new FormData();
    formData.append('file', file);

    setUploading(`${entityId}-${docType}`);
    try {
      await api.post(`/files/reupload/${entityType}/${entityId}?doc_type=${encodeURIComponent(docType)}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('File uploaded successfully!');
      // Refresh the list
      await scanMissingFiles();
      await fetchStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload file');
    } finally {
      setUploading(null);
    }
  };

  const formatSize = (bytes) => {
    if (!bytes) return '0 KB';
    const mb = bytes / (1024 * 1024);
    if (mb > 1) return `${mb.toFixed(2)} MB`;
    return `${(bytes / 1024).toFixed(2)} KB`;
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="file-migration-page">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-blue-100 rounded-lg">
            <HardDrive className="h-6 w-6 text-blue-600" />
          </div>
          <h1 className="text-4xl font-bold">File Storage Migration</h1>
        </div>
        <p className="text-muted-foreground text-base">
          Manage and migrate uploaded files to persistent storage (MongoDB GridFS)
        </p>
      </div>

      {/* Storage Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="border shadow-sm" data-testid="total-files-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Database className="h-4 w-4" />
              Files in GridFS
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono text-blue-600">
              {stats?.total_files || 0}
            </div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="storage-size-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <HardDrive className="h-4 w-4" />
              Total Size
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mono">
              {stats?.total_size_mb?.toFixed(2) || '0.00'} MB
            </div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm bg-gradient-to-br from-orange-50 to-amber-50" data-testid="missing-files-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-orange-700 uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              Missing Files
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold mono ${missingFiles.length > 0 ? 'text-orange-600' : 'text-green-600'}`}>
              {missingFiles.length}
            </div>
          </CardContent>
        </Card>

        <Card className="border shadow-sm" data-testid="action-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Button 
              onClick={scanMissingFiles} 
              disabled={scanning}
              className="w-full"
              variant="outline"
              data-testid="scan-btn"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${scanning ? 'animate-spin' : ''}`} />
              {scanning ? 'Scanning...' : 'Scan Files'}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Files by Category */}
      {stats?.by_category && stats.by_category.length > 0 && (
        <Card className="mb-6 border shadow-sm">
          <CardHeader>
            <CardTitle>Files by Category</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {stats.by_category.map((cat, idx) => (
                <div key={idx} className="p-4 bg-gray-50 rounded-lg text-center">
                  <div className="font-bold text-lg capitalize">{cat.category || 'Unknown'}</div>
                  <div className="text-sm text-muted-foreground">{cat.count} files</div>
                  <div className="text-xs text-gray-500">{cat.size_mb?.toFixed(2)} MB</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Missing Files Table */}
      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <FileX className="h-5 w-5 text-orange-500" />
              Missing Files Requiring Re-upload
            </span>
            {missingFiles.length === 0 && !loading && (
              <Badge className="bg-green-100 text-green-700 border-green-200">
                <Check className="h-3 w-3 mr-1" />
                All files migrated
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">Scanning for missing files...</div>
          ) : missingFiles.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileCheck className="h-12 w-12 mx-auto mb-3 text-green-500" />
              <p>No missing files found. All documents are stored in GridFS.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Entity Type</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Entity Name</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Document Type</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Original File</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {missingFiles.map((file, idx) => (
                    <TableRow key={idx} data-testid="missing-file-row">
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {file.entity_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{file.entity_name || 'Unknown'}</TableCell>
                      <TableCell className="capitalize">{file.doc_type?.replace(/_/g, ' ')}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{file.original_filename || '-'}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Input
                            type="file"
                            className="max-w-[200px]"
                            accept=".pdf,.png,.jpg,.jpeg"
                            onChange={(e) => {
                              if (e.target.files?.[0]) {
                                handleFileUpload(
                                  e.target.files[0], 
                                  file.entity_type, 
                                  file.entity_id, 
                                  file.doc_type
                                );
                              }
                            }}
                            disabled={uploading === `${file.entity_id}-${file.doc_type}`}
                            data-testid={`upload-input-${idx}`}
                          />
                          {uploading === `${file.entity_id}-${file.doc_type}` && (
                            <RefreshCw className="h-4 w-4 animate-spin text-blue-500" />
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

      {/* Help Info */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
        <strong>Why migrate to GridFS?</strong>
        <ul className="mt-2 ml-4 list-disc">
          <li>Files stored locally are lost when the app is redeployed</li>
          <li>GridFS stores files directly in MongoDB, ensuring persistence</li>
          <li>Files are automatically backed up with database backups</li>
          <li>Better scalability for multi-instance deployments</li>
        </ul>
      </div>
    </div>
  );
};

export default FileMigration;
