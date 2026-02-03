import { useEffect, useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { Database, Download, Upload, Trash2, Plus, RefreshCw, AlertTriangle, HardDrive, Clock, FileArchive, XCircle, Eye, FolderX, Layers, FileX } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';

const DatabaseBackup = () => {
  const [backups, setBackups] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState(null);
  const [creating, setCreating] = useState(false);
  const [creatingFull, setCreatingFull] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [backupName, setBackupName] = useState('');
  const [backupDescription, setBackupDescription] = useState('');
  const [clearConfirmText, setClearConfirmText] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [clearableCollections, setClearableCollections] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCollections, setSelectedCollections] = useState([]);
  const [excludedRecords, setExcludedRecords] = useState([]);
  const [excludeInput, setExcludeInput] = useState('');
  const [loadingCollections, setLoadingCollections] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [clearMode, setClearMode] = useState('collections'); // 'collections', 'categories', 'files'
  const [fileStats, setFileStats] = useState(null);
  const [selectedFileTypes, setSelectedFileTypes] = useState([]);
  const [clearingFiles, setClearingFiles] = useState(false);
  const fileInputRef = useRef(null);

  // Get current user for role check - only PE Desk (role 1) can clear DB
  const { isPEDesk } = useCurrentUser();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [backupsRes, statsRes] = await Promise.all([
        api.get('/database/backups'),
        api.get('/database/stats')
      ]);
      setBackups(backupsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to fetch backup data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBackup = async () => {
    if (!backupName.trim()) {
      toast.error('Please enter a backup name');
      return;
    }
    
    setCreating(true);
    try {
      // Use include_all=true to backup all collections
      const response = await api.post(`/database/backups?name=${encodeURIComponent(backupName)}&description=${encodeURIComponent(backupDescription)}&include_all=true`);
      toast.success(`Backup created successfully! ${response.data.backup.total_records} records from ${response.data.backup.collections_count} collections`);
      setCreateDialogOpen(false);
      setBackupName('');
      setBackupDescription('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create backup');
    } finally {
      setCreating(false);
    }
  };

  const handleCreateFullBackup = async () => {
    if (!window.confirm('This will create a FULL backup of all database collections. The backup can be downloaded with all uploaded files. Continue?')) {
      return;
    }
    
    setCreatingFull(true);
    try {
      const response = await api.post('/database/backups/full');
      toast.success(`Full backup created! ${response.data.backup.total_records} records from ${response.data.backup.collections_count} collections`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create full backup');
    } finally {
      setCreatingFull(false);
    }
  };

  const handleRestore = async () => {
    if (!selectedBackup) return;
    
    setRestoring(true);
    try {
      const response = await api.post('/database/restore', { backup_id: selectedBackup.id });
      if (response.data.errors?.length > 0) {
        toast.warning(`Restored with some errors: ${response.data.errors.join(', ')}`);
      } else {
        toast.success('Database restored successfully');
      }
      setRestoreDialogOpen(false);
      setSelectedBackup(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to restore database');
    } finally {
      setRestoring(false);
    }
  };

  const handleDeleteBackup = async (backupId) => {
    if (!window.confirm('Are you sure you want to delete this backup?')) return;
    
    try {
      await api.delete(`/database/backups/${backupId}`);
      toast.success('Backup deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete backup');
    }
  };

  const handleClearDatabase = async () => {
    if (clearConfirmText !== 'CLEAR DATABASE') {
      toast.error('Please type "CLEAR DATABASE" to confirm');
      return;
    }
    
    if (selectedCollections.length === 0) {
      toast.error('Please select at least one collection to clear');
      return;
    }
    
    setClearing(true);
    try {
      const params = new URLSearchParams();
      selectedCollections.forEach(c => params.append('collections', c));
      excludedRecords.forEach(e => params.append('exclude_ids', e));
      
      const response = await api.delete(`/database/clear?${params.toString()}`);
      const preserved = response.data.total_preserved || 0;
      toast.success(`Cleared ${response.data.collections_cleared} collections! ${response.data.total_deleted} records deleted${preserved > 0 ? `, ${preserved} preserved` : ''}.`);
      setClearDialogOpen(false);
      setClearConfirmText('');
      setSelectedCollections([]);
      setExcludedRecords([]);
      setPreviewData(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clear database');
    } finally {
      setClearing(false);
    }
  };

  const handleClearFiles = async () => {
    if (clearConfirmText !== 'CLEAR DATABASE') {
      toast.error('Please type "CLEAR DATABASE" to confirm');
      return;
    }
    
    if (selectedFileTypes.length === 0) {
      toast.error('Please select at least one file type to clear');
      return;
    }
    
    setClearingFiles(true);
    try {
      const params = new URLSearchParams();
      selectedFileTypes.forEach(f => params.append('file_types', f));
      
      const response = await api.delete(`/database/clear/files?${params.toString()}`);
      toast.success(`Cleared ${response.data.total_cleared} files successfully!`);
      setClearDialogOpen(false);
      setClearConfirmText('');
      setSelectedFileTypes([]);
      // Refresh file stats
      const filesRes = await api.get('/database/files/stats');
      setFileStats(filesRes.data.file_stats);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clear files');
    } finally {
      setClearingFiles(false);
    }
  };

  const handleDownloadBackup = async (backup, includeFiles = true) => {
    try {
      toast.info(includeFiles ? 'Preparing download with files...' : 'Preparing download...');
      const response = await api.get(`/database/backups/${backup.id}/download?include_files=${includeFiles}`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const safeName = backup.name.replace(/[^a-zA-Z0-9-_]/g, '_');
      const fileSuffix = includeFiles ? '_with_files' : '';
      link.setAttribute('download', `backup_${safeName}${fileSuffix}_${backup.created_at.slice(0, 10)}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(includeFiles ? 'Backup with files downloaded successfully' : 'Backup downloaded successfully');
    } catch (error) {
      toast.error('Failed to download backup');
    }
  };

  const handleUploadRestore = async () => {
    if (!uploadFile) {
      toast.error('Please select a backup file');
      return;
    }
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      
      const response = await api.post('/database/restore-from-file', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (response.data.errors?.length > 0) {
        toast.warning(`Restored with some errors: ${response.data.errors.join(', ')}`);
      } else {
        toast.success('Database restored from uploaded file successfully');
      }
      setUploadDialogOpen(false);
      setUploadFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to restore from file');
    } finally {
      setUploading(false);
    }
  };

  const openRestoreDialog = (backup) => {
    setSelectedBackup(backup);
    setRestoreDialogOpen(true);
  };

  const openClearDialog = async () => {
    setClearDialogOpen(true);
    setLoadingCollections(true);
    setClearMode('collections');
    setPreviewData(null);
    setExcludedRecords([]);
    setExcludeInput('');
    try {
      const [collectionsRes, filesRes] = await Promise.all([
        api.get('/database/clearable-collections'),
        api.get('/database/files/stats')
      ]);
      setClearableCollections(collectionsRes.data.collections);
      setCategories(collectionsRes.data.categories || []);
      setFileStats(filesRes.data.file_stats);
      setSelectedCollections([]);
      setSelectedFileTypes([]);
    } catch (error) {
      toast.error('Failed to fetch collections');
      setClearableCollections([]);
      setCategories([]);
    } finally {
      setLoadingCollections(false);
    }
  };

  const toggleCollection = (collectionName) => {
    setSelectedCollections(prev => 
      prev.includes(collectionName) 
        ? prev.filter(c => c !== collectionName)
        : [...prev, collectionName]
    );
    setPreviewData(null); // Reset preview when selection changes
  };

  const toggleCategory = (categoryKey) => {
    const category = categories.find(c => c.key === categoryKey);
    if (!category) return;
    
    const categoryCollections = category.collections;
    const allSelected = categoryCollections.every(c => selectedCollections.includes(c));
    
    if (allSelected) {
      setSelectedCollections(prev => prev.filter(c => !categoryCollections.includes(c)));
    } else {
      setSelectedCollections(prev => [...new Set([...prev, ...categoryCollections])]);
    }
    setPreviewData(null);
  };

  const toggleAllCollections = () => {
    if (selectedCollections.length === clearableCollections.length) {
      setSelectedCollections([]);
    } else {
      setSelectedCollections(clearableCollections.map(c => c.name));
    }
    setPreviewData(null);
  };

  const toggleFileType = (fileType) => {
    setSelectedFileTypes(prev => 
      prev.includes(fileType) 
        ? prev.filter(f => f !== fileType)
        : [...prev, fileType]
    );
  };

  const addExcludedRecord = () => {
    if (!excludeInput.trim()) return;
    // Format: collection:id
    if (!excludeInput.includes(':')) {
      toast.error('Format: collection_name:record_id');
      return;
    }
    if (!excludedRecords.includes(excludeInput.trim())) {
      setExcludedRecords(prev => [...prev, excludeInput.trim()]);
      setExcludeInput('');
      setPreviewData(null);
    }
  };

  const removeExcludedRecord = (record) => {
    setExcludedRecords(prev => prev.filter(r => r !== record));
    setPreviewData(null);
  };

  const getSelectedRecordCount = () => {
    return clearableCollections
      .filter(c => selectedCollections.includes(c.name))
      .reduce((sum, c) => sum + c.count, 0);
  };

  const handlePreview = async () => {
    if (selectedCollections.length === 0) {
      toast.error('Please select at least one collection');
      return;
    }
    
    setPreviewLoading(true);
    try {
      const params = new URLSearchParams();
      selectedCollections.forEach(c => params.append('collections', c));
      excludedRecords.forEach(e => params.append('exclude_ids', e));
      
      const response = await api.post(`/database/clear/preview?${params.toString()}`);
      setPreviewData(response.data);
    } catch (error) {
      toast.error('Failed to generate preview');
    } finally {
      setPreviewLoading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 space-y-6" data-testid="database-backup-page">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-xl md:text-2xl lg:text-3xl font-bold flex items-center gap-2">
            <Database className="h-6 w-6 md:h-8 md:w-8 text-primary" />
            <span className="hidden sm:inline">Database </span>Backup & Restore
          </h1>
          <p className="text-muted-foreground text-sm md:text-base">Manage database backups for disaster recovery</p>
        </div>
        <div className="flex flex-wrap gap-2 w-full sm:w-auto">
          <Button variant="outline" onClick={fetchData} className="flex-1 sm:flex-none">
            <RefreshCw className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
          <Button variant="outline" onClick={() => setUploadDialogOpen(true)} className="flex-1 sm:flex-none" data-testid="upload-restore-btn">
            <Upload className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Upload </span>Restore
          </Button>
          <Button onClick={() => setCreateDialogOpen(true)} className="flex-1 sm:flex-none" data-testid="create-backup-btn">
            <Plus className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Create </span>Backup
          </Button>
          {isPEDesk && (
            <Button 
              onClick={handleCreateFullBackup} 
              disabled={creatingFull}
              className="flex-1 sm:flex-none bg-green-600 hover:bg-green-700" 
              data-testid="full-backup-btn"
            >
              {creatingFull ? (
                <RefreshCw className="h-4 w-4 sm:mr-2 animate-spin" />
              ) : (
                <FileArchive className="h-4 w-4 sm:mr-2" />
              )}
              <span className="hidden sm:inline">Full </span>Backup
            </Button>
          )}
          {isPEDesk && (
            <Button variant="destructive" onClick={openClearDialog} className="flex-1 sm:flex-none" data-testid="clear-database-btn">
              <XCircle className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Clear </span>DB
            </Button>
          )}
        </div>
      </div>

      {/* Database Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 md:gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-full">
                  <HardDrive className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Records</p>
                  <p className="text-2xl font-bold">{stats.total_records?.toLocaleString()}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-100 dark:bg-green-900 rounded-full">
                  <FileArchive className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Backups</p>
                  <p className="text-2xl font-bold">{stats.backup_count}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-100 dark:bg-purple-900 rounded-full">
                  <Database className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Collections</p>
                  <p className="text-2xl font-bold">{Object.keys(stats.collections || {}).length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-amber-100 dark:bg-amber-900 rounded-full">
                  <Upload className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Uploaded Files</p>
                  <p className="text-2xl font-bold">{stats.uploaded_files?.total_count || 0}</p>
                  <p className="text-xs text-muted-foreground">{stats.uploaded_files?.total_size_mb || 0} MB</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-orange-100 dark:bg-orange-900 rounded-full">
                  <Clock className="h-6 w-6 text-orange-600 dark:text-orange-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Backup</p>
                  <p className="text-sm font-medium">
                    {backups.length > 0 ? formatDate(backups[0].created_at) : 'Never'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Uploaded Files Stats */}
      {stats?.uploaded_files?.by_category && Object.keys(stats.uploaded_files.by_category).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Uploaded Files by Category
            </CardTitle>
            <CardDescription>Documents, logos, and other uploaded files that will be included in backups</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {Object.entries(stats.uploaded_files.by_category).map(([name, data]) => (
                <div key={name} className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                  <p className="text-xs text-muted-foreground capitalize">{name.replace(/_/g, ' ')}</p>
                  <p className="text-lg font-semibold">{data.count} files</p>
                  <p className="text-xs text-muted-foreground">{data.size_mb} MB</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Collection Stats */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>Collection Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {Object.entries(stats.collections || {}).map(([name, count]) => (
                <div key={name} className="p-3 bg-muted rounded-lg">
                  <p className="text-xs text-muted-foreground capitalize">{name.replace('_', ' ')}</p>
                  <p className="text-lg font-semibold">{count.toLocaleString()}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Backups List */}
      <Card>
        <CardHeader>
          <CardTitle>Backup History</CardTitle>
          <CardDescription>Last 10 backups are retained automatically</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-center py-8 text-muted-foreground">Loading...</p>
          ) : backups.length === 0 ? (
            <div className="text-center py-8">
              <Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No backups yet. Create your first backup to protect your data.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Created By</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Records</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {backups.map((backup) => (
                  <TableRow key={backup.id} data-testid={`backup-row-${backup.id}`}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{backup.name}</p>
                        {backup.description && (
                          <p className="text-xs text-muted-foreground">{backup.description}</p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{formatDate(backup.created_at)}</TableCell>
                    <TableCell>{backup.created_by_name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{formatBytes(backup.size_bytes)}</Badge>
                    </TableCell>
                    <TableCell>
                      {Object.values(backup.record_counts || {}).reduce((a, b) => a + b, 0).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDownloadBackup(backup, true)}
                          title="Download backup with files"
                          data-testid={`download-backup-${backup.id}`}
                        >
                          <Download className="h-4 w-4 mr-1" />
                          <span className="hidden md:inline text-xs">+ Files</span>
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDownloadBackup(backup, false)}
                          title="Download database only (no files)"
                          className="text-muted-foreground"
                        >
                          <Database className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openRestoreDialog(backup)}
                          title="Restore from this backup"
                        >
                          <Upload className="h-4 w-4 mr-1" />
                          Restore
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteBackup(backup.id)}
                          className="text-red-600"
                          title="Delete backup"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Backup Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent data-testid="create-backup-dialog">
          <DialogHeader>
            <DialogTitle>Create Database Backup</DialogTitle>
            <DialogDescription>
              Create a snapshot of all database collections
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Backup Name *</Label>
              <Input
                value={backupName}
                onChange={(e) => setBackupName(e.target.value)}
                placeholder="e.g., Pre-deployment backup"
                data-testid="backup-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Description (optional)</Label>
              <Textarea
                value={backupDescription}
                onChange={(e) => setBackupDescription(e.target.value)}
                placeholder="Add notes about this backup..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateBackup} disabled={creating || !backupName.trim()} data-testid="confirm-create-backup">
              {creating ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 mr-2" />
                  Create Backup
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Restore Dialog */}
      <Dialog open={restoreDialogOpen} onOpenChange={setRestoreDialogOpen}>
        <DialogContent data-testid="restore-dialog">
          <DialogHeader>
            <DialogTitle className="text-orange-600 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Restore Database
            </DialogTitle>
            <DialogDescription>
              Restore from backup: <strong>{selectedBackup?.name}</strong>
            </DialogDescription>
          </DialogHeader>
          
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Warning: Destructive Action</AlertTitle>
            <AlertDescription>
              This will <strong>replace all current data</strong> with the backup data. 
              This action cannot be undone. The super admin account (pedesk@smifs.com) will be preserved.
            </AlertDescription>
          </Alert>
          
          {selectedBackup && (
            <div className="space-y-2 text-sm">
              <p><strong>Backup Date:</strong> {formatDate(selectedBackup.created_at)}</p>
              <p><strong>Total Records:</strong> {Object.values(selectedBackup.record_counts || {}).reduce((a, b) => a + b, 0).toLocaleString()}</p>
              <p><strong>Collections:</strong> {selectedBackup.collections?.join(', ')}</p>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreDialogOpen(false)}>Cancel</Button>
            <Button 
              variant="destructive" 
              onClick={handleRestore} 
              disabled={restoring}
              data-testid="confirm-restore"
            >
              {restoring ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Restoring...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Restore Database
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Clear Database Dialog */}
      <Dialog open={clearDialogOpen} onOpenChange={(open) => { setClearDialogOpen(open); if (!open) { setClearConfirmText(''); setSelectedCollections([]); } }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="clear-database-dialog">
          <DialogHeader>
            <DialogTitle className="text-red-600 flex items-center gap-2">
              <XCircle className="h-5 w-5" />
              Clear Database - Selective
            </DialogTitle>
            <DialogDescription>
              Select specific collections to clear. User accounts and backups are always protected.
            </DialogDescription>
          </DialogHeader>
          
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Danger: This Cannot Be Undone!</AlertTitle>
            <AlertDescription>
              Selected data will be <strong>permanently deleted</strong>.
              Consider creating a backup first before clearing any data.
            </AlertDescription>
          </Alert>
          
          {/* Collection Selection */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Select Collections to Clear:</Label>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={toggleAllCollections}
                disabled={loadingCollections}
                className="text-xs"
              >
                {selectedCollections.length === clearableCollections.length ? 'Deselect All' : 'Select All'}
              </Button>
            </div>
            
            {loadingCollections ? (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Loading collections...</span>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-64 overflow-y-auto p-2 border rounded-lg bg-muted/30">
                {clearableCollections.map((collection) => (
                  <div 
                    key={collection.name}
                    className={`flex items-center space-x-2 p-2 rounded cursor-pointer hover:bg-muted transition-colors ${
                      selectedCollections.includes(collection.name) ? 'bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700' : 'bg-background'
                    }`}
                    onClick={() => toggleCollection(collection.name)}
                  >
                    <Checkbox 
                      checked={selectedCollections.includes(collection.name)}
                      onCheckedChange={() => toggleCollection(collection.name)}
                      data-testid={`collection-checkbox-${collection.name}`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{collection.display_name}</p>
                      <p className="text-xs text-muted-foreground">{collection.count.toLocaleString()} records</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {/* Selection Summary */}
            {selectedCollections.length > 0 && (
              <div className="p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm font-medium text-red-700 dark:text-red-300">
                  <strong>{selectedCollections.length}</strong> collection(s) selected
                </p>
                <p className="text-xs text-red-600 dark:text-red-400">
                  {getSelectedRecordCount().toLocaleString()} records will be permanently deleted
                </p>
              </div>
            )}
          </div>
          
          <div className="space-y-2">
            <Label>Type <strong>CLEAR DATABASE</strong> to confirm:</Label>
            <Input
              value={clearConfirmText}
              onChange={(e) => setClearConfirmText(e.target.value)}
              placeholder="CLEAR DATABASE"
              data-testid="clear-confirm-input"
            />
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => { setClearDialogOpen(false); setClearConfirmText(''); setSelectedCollections([]); }}>Cancel</Button>
            <Button 
              variant="destructive" 
              onClick={handleClearDatabase} 
              disabled={clearing || clearConfirmText !== 'CLEAR DATABASE' || selectedCollections.length === 0}
              data-testid="confirm-clear-database"
            >
              {clearing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Clearing...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Clear {selectedCollections.length} Collection(s)
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Restore Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent data-testid="upload-restore-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Restore from Backup File
            </DialogTitle>
            <DialogDescription>
              Upload a previously downloaded backup ZIP file to restore.
            </DialogDescription>
          </DialogHeader>
          
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Warning: Destructive Action</AlertTitle>
            <AlertDescription>
              This will replace all current data with the uploaded backup data.
              The super admin account (pedesk@smifs.com) will be preserved.
            </AlertDescription>
          </Alert>
          
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Select Backup File (.zip)</Label>
              <Input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                onChange={(e) => setUploadFile(e.target.files[0])}
                data-testid="upload-file-input"
              />
            </div>
            {uploadFile && (
              <div className="p-3 bg-muted rounded-lg text-sm">
                <p><strong>File:</strong> {uploadFile.name}</p>
                <p><strong>Size:</strong> {formatBytes(uploadFile.size)}</p>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => { setUploadDialogOpen(false); setUploadFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}>Cancel</Button>
            <Button 
              variant="destructive" 
              onClick={handleUploadRestore} 
              disabled={uploading || !uploadFile}
              data-testid="confirm-upload-restore"
            >
              {uploading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Restoring...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Restore from File
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DatabaseBackup;
