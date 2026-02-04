import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '../utils/api';
import { useProtectedPage } from '../hooks/useProtectedPage';
import { Mail, Edit, Eye, RotateCcw, Save, Code, FileText } from 'lucide-react';

const EmailTemplates = () => {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [formData, setFormData] = useState({
    subject: '',
    body: '',
    is_active: true
  });
  const [previewVariables, setPreviewVariables] = useState({});

  const { isLoading, isAuthorized, hasPermission } = useProtectedPage({
    allowIf: ({ isPELevel, hasPermission }) => isPELevel || hasPermission('email.view_templates'),
    deniedMessage: 'Access denied. You need Email Templates permission to access this page.'
  });

  useEffect(() => {
    if (!isAuthorized) return;
    fetchTemplates();
  }, [isAuthorized]);

  const fetchTemplates = async () => {
    try {
      const response = await api.get('/email-templates');
      setTemplates(response.data);
    } catch (error) {
      toast.error('Failed to load templates');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (template) => {
    setEditingTemplate(template);
    setFormData({
      subject: template.subject,
      body: template.body,
      is_active: template.is_active
    });
    // Initialize preview variables with placeholders
    const vars = {};
    template.variables?.forEach(v => {
      vars[v] = `[${v}]`;
    });
    setPreviewVariables(vars);
  };

  const handleSave = async () => {
    try {
      await api.put(`/email-templates/${editingTemplate.key}`, null, {
        params: {
          subject: formData.subject,
          body: formData.body,
          is_active: formData.is_active
        }
      });
      toast.success('Template saved successfully');
      setEditingTemplate(null);
      fetchTemplates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save template');
    }
  };

  const handleReset = async (templateKey) => {
    if (!confirm('Reset this template to default? This cannot be undone.')) return;
    
    try {
      await api.post(`/email-templates/${templateKey}/reset`);
      toast.success('Template reset to default');
      fetchTemplates();
    } catch (error) {
      toast.error('Failed to reset template');
    }
  };

  const handlePreview = async () => {
    try {
      const response = await api.post(`/email-templates/${editingTemplate.key}/preview`, previewVariables);
      setPreviewHtml(response.data.body);
      setPreviewOpen(true);
    } catch (error) {
      toast.error('Failed to generate preview');
    }
  };

  const templateIcons = {
    client_welcome: '👋',
    client_approved: '✅',
    booking_created: '📝',
    booking_approved: '✓',
    password_reset_otp: '🔑'
  };

  // Show loading while checking permissions
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 space-y-6" data-testid="email-templates-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Mail className="h-8 w-8" />
          Email Templates
        </h1>
        <p className="text-muted-foreground">Customize email notifications sent to clients and users</p>
      </div>

      {/* Templates Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates.map((template) => (
          <Card key={template.key} className={!template.is_active ? 'opacity-60' : ''}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <span>{templateIcons[template.key] || '📧'}</span>
                  {template.name}
                </CardTitle>
                <Badge variant={template.is_active ? 'default' : 'secondary'}>
                  {template.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>
              <CardDescription className="text-xs truncate">
                {template.subject}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-1 mb-3">
                {template.variables?.slice(0, 4).map((v) => (
                  <Badge key={v} variant="outline" className="text-xs">
                    {`{{${v}}}`}
                  </Badge>
                ))}
                {template.variables?.length > 4 && (
                  <Badge variant="outline" className="text-xs">
                    +{template.variables.length - 4} more
                  </Badge>
                )}
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => handleEdit(template)} data-testid={`edit-${template.key}`}>
                  <Edit className="h-4 w-4 mr-1" />
                  Edit
                </Button>
                <Button size="sm" variant="ghost" onClick={() => handleReset(template.key)}>
                  <RotateCcw className="h-4 w-4" />
                </Button>
              </div>
              {template.updated_at && (
                <p className="text-xs text-muted-foreground mt-2">
                  Modified: {new Date(template.updated_at).toLocaleDateString()}
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Edit Dialog */}
      <Dialog open={!!editingTemplate} onOpenChange={() => setEditingTemplate(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span>{templateIcons[editingTemplate?.key] || '📧'}</span>
              Edit: {editingTemplate?.name}
            </DialogTitle>
          </DialogHeader>

          <Tabs defaultValue="edit" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="edit">
                <Code className="h-4 w-4 mr-1" />
                Edit
              </TabsTrigger>
              <TabsTrigger value="variables">
                <FileText className="h-4 w-4 mr-1" />
                Variables
              </TabsTrigger>
              <TabsTrigger value="preview" onClick={handlePreview}>
                <Eye className="h-4 w-4 mr-1" />
                Preview
              </TabsTrigger>
            </TabsList>

            <TabsContent value="edit" className="space-y-4">
              <div className="space-y-2">
                <Label>Subject Line</Label>
                <Input
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  placeholder="Email subject..."
                  data-testid="template-subject"
                />
              </div>

              <div className="space-y-2">
                <Label>Email Body (HTML)</Label>
                <Textarea
                  value={formData.body}
                  onChange={(e) => setFormData({ ...formData, body: e.target.value })}
                  placeholder="Email HTML content..."
                  rows={15}
                  className="font-mono text-sm"
                  data-testid="template-body"
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={formData.is_active}
                    onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                    data-testid="template-active"
                  />
                  <Label>Active</Label>
                </div>
                <Button onClick={handleSave} data-testid="save-template">
                  <Save className="h-4 w-4 mr-1" />
                  Save Changes
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="variables" className="space-y-4">
              <div className="bg-muted p-4 rounded-lg">
                <h4 className="font-medium mb-2">Available Variables</h4>
                <p className="text-sm text-muted-foreground mb-4">
                  Use these placeholders in your template. They will be replaced with actual values when the email is sent.
                </p>
                <div className="space-y-3">
                  {editingTemplate?.variables?.map((variable) => (
                    <div key={variable} className="flex items-center gap-3">
                      <code className="bg-background px-2 py-1 rounded text-sm">{`{{${variable}}}`}</code>
                      <Input
                        value={previewVariables[variable] || ''}
                        onChange={(e) => setPreviewVariables({ ...previewVariables, [variable]: e.target.value })}
                        placeholder={`Sample ${variable}...`}
                        className="flex-1"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="preview">
              <div className="border rounded-lg p-4 bg-white dark:bg-gray-900">
                <div className="mb-4 pb-4 border-b">
                  <p className="text-sm text-muted-foreground">Subject:</p>
                  <p className="font-medium">{formData.subject}</p>
                </div>
                <div 
                  className="email-preview"
                  dangerouslySetInnerHTML={{ __html: previewHtml || formData.body }}
                />
              </div>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EmailTemplates;
