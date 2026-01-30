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
import { toast } from 'sonner';
import api from '../utils/api';
import { Database, Download, Upload, Trash2, Plus, RefreshCw, AlertTriangle, HardDrive, Clock, FileArchive, XCircle } from 'lucide-react';

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
  const [restoring, setRestoring] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [backupName, setBackupName] = useState('');
  const [backupDescription, setBackupDescription] = useState('');
  const [clearConfirmText, setClearConfirmText] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const fileInputRef = useRef(null);

  // Get current user for role check - only PE Desk (role 1) can clear DB
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPEDesk = currentUser.role === 1;

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
    
    setClearing(true);
    try {
      const response = await api.delete('/database/clear');
      toast.success(`Database cleared! ${response.data.total_deleted} records deleted.`);
      setClearDialogOpen(false);
      setClearConfirmText('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clear database');
    } finally {
      setClearing(false);
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
            <Button variant="destructive" onClick={() => setClearDialogOpen(true)} className="flex-1 sm:flex-none" data-testid="clear-database-btn">
              <XCircle className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Clear </span>DB
            </Button>
          )}
        </div>
      </div>

      {/* Database Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
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
                          onClick={() => handleDownloadBackup(backup)}
                          title="Download backup as ZIP"
                          data-testid={`download-backup-${backup.id}`}
                        >
                          <Download className="h-4 w-4" />
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
      <Dialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
        <DialogContent data-testid="clear-database-dialog">
          <DialogHeader>
            <DialogTitle className="text-red-600 flex items-center gap-2">
              <XCircle className="h-5 w-5" />
              Clear Database
            </DialogTitle>
            <DialogDescription>
              This will permanently delete all data except user accounts.
            </DialogDescription>
          </DialogHeader>
          
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Danger: This Cannot Be Undone!</AlertTitle>
            <AlertDescription>
              This will <strong>permanently delete</strong> all clients, vendors, stocks, bookings, purchases, inventory, and other data.
              <br /><br />
              <strong>User accounts will be preserved.</strong>
              <br /><br />
              Consider creating a backup first before clearing the database.
            </AlertDescription>
          </Alert>
          
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
            <Button variant="outline" onClick={() => { setClearDialogOpen(false); setClearConfirmText(''); }}>Cancel</Button>
            <Button 
              variant="destructive" 
              onClick={handleClearDatabase} 
              disabled={clearing || clearConfirmText !== 'CLEAR DATABASE'}
              data-testid="confirm-clear-database"
            >
              {clearing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Clearing...
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 mr-2" />
                  Clear Database
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
