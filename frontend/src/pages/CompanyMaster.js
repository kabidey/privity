import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  Building2, 
  Save, 
  Upload, 
  Trash2, 
  FileText, 
  CreditCard,
  Landmark,
  FileCheck,
  Eye,
  RefreshCw,
  ImageIcon
} from 'lucide-react';

const CompanyMaster = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState({});
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [logoUrl, setLogoUrl] = useState(null);
  /**
   * CRITICAL FIX - DO NOT MODIFY
   * logoKey is used for cache-busting to force logo refresh after upload.
   * Without this, uploaded logos won't display until page hard-refresh.
   * Fixed: Jan 30, 2026
   */
  const [logoKey, setLogoKey] = useState(Date.now());
  const [formData, setFormData] = useState({
    company_name: '',
    company_address: '',
    company_cin: '',
    company_gst: '',
    company_pan: '',
    cdsl_dp_id: '',
    nsdl_dp_id: '',
    company_tan: '',
    company_bank_name: '',
    company_bank_account: '',
    company_bank_ifsc: '',
    company_bank_branch: '',
    user_agreement_text: ''
  });
  const [documents, setDocuments] = useState({
    cml_cdsl_url: null,
    cml_nsdl_url: null,
    cancelled_cheque_url: null,
    pan_card_url: null
  });
  const [lastUpdated, setLastUpdated] = useState({ at: null, by: null });

  // File input refs
  const logoInputRef = useRef(null);
  const fileInputRefs = {
    cml_cdsl: useRef(null),
    cml_nsdl: useRef(null),
    cancelled_cheque: useRef(null),
    pan_card: useRef(null)
  };

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPEDesk = currentUser.role === 1;

  useEffect(() => {
    if (!isPEDesk) {
      toast.error('Access denied. Only PE Desk can access Company Master settings.');
      navigate('/');
      return;
    }
    fetchCompanyMaster();
  }, [isPEDesk, navigate]);

  const fetchCompanyMaster = async () => {
    try {
      setLoading(true);
      const response = await api.get('/company-master');
      const data = response.data;
      
      setFormData({
        company_name: data.company_name || '',
        company_address: data.company_address || '',
        company_cin: data.company_cin || '',
        company_gst: data.company_gst || '',
        company_pan: data.company_pan || '',
        cdsl_dp_id: data.cdsl_dp_id || '',
        nsdl_dp_id: data.nsdl_dp_id || '',
        company_tan: data.company_tan || '',
        company_bank_name: data.company_bank_name || '',
        company_bank_account: data.company_bank_account || '',
        company_bank_ifsc: data.company_bank_ifsc || '',
        company_bank_branch: data.company_bank_branch || '',
        user_agreement_text: data.user_agreement_text || ''
      });
      
      setDocuments({
        cml_cdsl_url: data.cml_cdsl_url,
        cml_nsdl_url: data.cml_nsdl_url,
        cancelled_cheque_url: data.cancelled_cheque_url,
        pan_card_url: data.pan_card_url
      });
      
      setLogoUrl(data.logo_url);
      
      setLastUpdated({
        at: data.updated_at,
        by: data.updated_by
      });
    } catch (error) {
      toast.error('Failed to load company master settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/company-master', formData);
      toast.success('Company master settings saved successfully');
      fetchCompanyMaster();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleFileUpload = async (documentType, file) => {
    if (!file) return;

    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Invalid file type. Please upload PDF, JPG, or PNG files.');
      return;
    }

    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      toast.error('File size exceeds 10MB limit.');
      return;
    }

    setUploading(prev => ({ ...prev, [documentType]: true }));
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.post(`/company-master/upload/${documentType}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      toast.success(response.data.message);
      setDocuments(prev => ({ ...prev, [`${documentType}_url`]: response.data.url }));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
    } finally {
      setUploading(prev => ({ ...prev, [documentType]: false }));
    }
  };

  const handleLogoUpload = async (file) => {
    if (!file) return;

    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Invalid file type. Please upload PNG, JPG, SVG, or WEBP files.');
      return;
    }

    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      toast.error('Logo file size must be less than 5MB.');
      return;
    }

    setUploadingLogo(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.post('/company-master/upload-logo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      toast.success(response.data.message);
      setLogoUrl(response.data.url);
      // CRITICAL: Update logoKey to force image re-render with new URL
      setLogoKey(Date.now());
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload logo');
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleDeleteLogo = async () => {
    if (!window.confirm('Are you sure you want to delete the company logo?')) {
      return;
    }

    try {
      await api.delete('/company-master/logo');
      toast.success('Logo deleted successfully');
      setLogoUrl(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete logo');
    }
  };

  const handleDeleteDocument = async (documentType) => {
    if (!window.confirm(`Are you sure you want to delete this document?`)) {
      return;
    }

    try {
      await api.delete(`/company-master/document/${documentType}`);
      toast.success('Document deleted successfully');
      setDocuments(prev => ({ ...prev, [`${documentType}_url`]: null }));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete document');
    }
  };

  const triggerFileInput = (documentType) => {
    fileInputRefs[documentType].current?.click();
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

  /**
   * CRITICAL FIX - DO NOT MODIFY
   * This helper function constructs full URLs for uploaded files.
   * Without this, document View buttons will show blank screens.
   * Fixed: Jan 30, 2026
   * @param {string} url - Relative URL like "/uploads/company/file.pdf"
   * @returns {string} Full URL with API base
   */
  const getFullUrl = (url) => {
    if (!url) return null;
    // If URL already starts with http, return as is
    if (url.startsWith('http')) return url;
    // Otherwise, construct full URL with API prefix
    return `${process.env.REACT_APP_BACKEND_URL}/api${url}`;
  };

  const DocumentCard = ({ title, icon: Icon, documentType, url }) => (
    <Card className="relative">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Icon className="w-4 h-4 text-emerald-600" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <input
          type="file"
          ref={fileInputRefs[documentType]}
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={(e) => handleFileUpload(documentType, e.target.files[0])}
        />
        
        {url ? (
          <div className="space-y-3">
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              <FileCheck className="w-3 h-3 mr-1" />
              Uploaded
            </Badge>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(getFullUrl(url), '_blank')}
                data-testid={`view-${documentType}-btn`}
              >
                <Eye className="w-4 h-4 mr-1" />
                View
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => triggerFileInput(documentType)}
                disabled={uploading[documentType]}
              >
                <RefreshCw className="w-4 h-4 mr-1" />
                Replace
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleDeleteDocument(documentType)}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ) : (
          <Button
            variant="outline"
            className="w-full border-dashed"
            onClick={() => triggerFileInput(documentType)}
            disabled={uploading[documentType]}
          >
            {uploading[documentType] ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                Upload Document
              </>
            )}
          </Button>
        )}
        <p className="text-xs text-gray-400 mt-2">PDF, JPG, PNG (Max 10MB)</p>
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="company-master-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Building2 className="w-7 h-7 text-emerald-600" />
            Company Master Settings
          </h1>
          <p className="text-gray-500 mt-1">
            Configure company details and upload required documents
          </p>
        </div>
        <div className="text-right text-sm text-gray-500">
          {lastUpdated.at && (
            <>
              <p>Last updated: {formatDate(lastUpdated.at)}</p>
              <p>By: {lastUpdated.by}</p>
            </>
          )}
        </div>
      </div>

      {/* Company Logo Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ImageIcon className="w-5 h-5" />
            Company Logo
          </CardTitle>
          <CardDescription>
            Upload your company logo (PNG, JPG, SVG, WEBP - Max 5MB)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <input
            type="file"
            ref={logoInputRef}
            className="hidden"
            accept=".png,.jpg,.jpeg,.svg,.webp"
            onChange={(e) => handleLogoUpload(e.target.files[0])}
          />
          
          <div className="flex items-start gap-8">
            {/* Logo Preview */}
            <div className="flex-shrink-0">
              {/* 
                CRITICAL FIX - DO NOT MODIFY the img tag below
                - key={logoKey} forces React re-render when logo changes
                - getFullUrl() constructs proper API URL
                - ?t=${logoKey} cache-busting prevents browser caching
                Fixed: Jan 30, 2026
              */}
              <div 
                className="w-48 h-48 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center bg-gray-50 overflow-hidden"
                data-testid="logo-preview-container"
              >
                {logoUrl ? (
                  <img 
                    key={logoKey}
                    src={`${getFullUrl(logoUrl)}?t=${logoKey}`} 
                    alt="Company Logo" 
                    className="max-w-full max-h-full object-contain p-2"
                    data-testid="company-logo-preview"
                    onError={(e) => {
                      console.error('Logo load failed:', e.target.src);
                      // Try without cache-busting as fallback
                      if (e.target.src.includes('?t=')) {
                        e.target.src = getFullUrl(logoUrl);
                      }
                    }}
                  />
                ) : (
                  <div className="text-center text-gray-400">
                    <ImageIcon className="w-12 h-12 mx-auto mb-2" />
                    <p className="text-sm">No logo uploaded</p>
                  </div>
                )}
              </div>
            </div>
            
            {/* Logo Actions */}
            <div className="flex-grow space-y-4">
              <div>
                <h4 className="font-medium text-gray-700 mb-2">Logo Guidelines</h4>
                <ul className="text-sm text-gray-500 space-y-1">
                  <li>• Recommended size: 400x400 pixels or higher</li>
                  <li>• Supported formats: PNG, JPG, SVG, WEBP</li>
                  <li>• Maximum file size: 5MB</li>
                  <li>• Transparent background recommended for PNG</li>
                </ul>
              </div>
              
              <div className="flex gap-3">
                <Button
                  onClick={() => logoInputRef.current?.click()}
                  disabled={uploadingLogo}
                  className="bg-emerald-600 hover:bg-emerald-700"
                  data-testid="upload-logo-btn"
                >
                  {uploadingLogo ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2" />
                      {logoUrl ? 'Change Logo' : 'Upload Logo'}
                    </>
                  )}
                </Button>
                
                {logoUrl && (
                  <Button
                    variant="destructive"
                    onClick={handleDeleteLogo}
                    data-testid="delete-logo-btn"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Remove Logo
                  </Button>
                )}
              </div>
              
              {logoUrl && (
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  <FileCheck className="w-3 h-3 mr-1" />
                  Logo uploaded successfully
                </Badge>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Company Details Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="w-5 h-5" />
            Company Information
          </CardTitle>
          <CardDescription>
            Basic company details and registration information
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <Label htmlFor="company_name">Company Name *</Label>
              <Input
                id="company_name"
                value={formData.company_name}
                onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                placeholder="Enter company name"
                data-testid="company-name-input"
              />
            </div>
            <div className="md:col-span-2">
              <Label htmlFor="company_address">Company Address</Label>
              <Textarea
                id="company_address"
                value={formData.company_address}
                onChange={(e) => setFormData({ ...formData, company_address: e.target.value })}
                placeholder="Enter complete company address"
                rows={3}
                data-testid="company-address-input"
              />
            </div>
          </div>

          <Separator />

          {/* Registration Numbers */}
          <div>
            <h3 className="font-medium mb-4 text-gray-700">Registration & Tax Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="company_cin">CIN (Corporate Identification Number)</Label>
                <Input
                  id="company_cin"
                  value={formData.company_cin}
                  onChange={(e) => setFormData({ ...formData, company_cin: e.target.value.toUpperCase() })}
                  placeholder="e.g., U12345MH2020PTC123456"
                  maxLength={21}
                  data-testid="company-cin-input"
                />
              </div>
              <div>
                <Label htmlFor="company_gst">GST Number</Label>
                <Input
                  id="company_gst"
                  value={formData.company_gst}
                  onChange={(e) => setFormData({ ...formData, company_gst: e.target.value.toUpperCase() })}
                  placeholder="e.g., 27AABCU9603R1ZM"
                  maxLength={15}
                  data-testid="company-gst-input"
                />
              </div>
              <div>
                <Label htmlFor="company_pan">PAN Number</Label>
                <Input
                  id="company_pan"
                  value={formData.company_pan}
                  onChange={(e) => setFormData({ ...formData, company_pan: e.target.value.toUpperCase() })}
                  placeholder="e.g., AABCU9603R"
                  maxLength={10}
                  data-testid="company-pan-input"
                />
              </div>
              <div>
                <Label htmlFor="company_tan">TAN Number</Label>
                <Input
                  id="company_tan"
                  value={formData.company_tan}
                  onChange={(e) => setFormData({ ...formData, company_tan: e.target.value.toUpperCase() })}
                  placeholder="e.g., MUMB12345F"
                  maxLength={10}
                  data-testid="company-tan-input"
                />
              </div>
              <div>
                <Label htmlFor="cdsl_dp_id">CDSL DP ID</Label>
                <Input
                  id="cdsl_dp_id"
                  value={formData.cdsl_dp_id}
                  onChange={(e) => setFormData({ ...formData, cdsl_dp_id: e.target.value })}
                  placeholder="e.g., 12345678"
                  data-testid="cdsl-dp-id-input"
                />
              </div>
              <div>
                <Label htmlFor="nsdl_dp_id">NSDL DP ID</Label>
                <Input
                  id="nsdl_dp_id"
                  value={formData.nsdl_dp_id}
                  onChange={(e) => setFormData({ ...formData, nsdl_dp_id: e.target.value })}
                  placeholder="e.g., IN300000"
                  data-testid="nsdl-dp-id-input"
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Bank Details */}
          <div>
            <h3 className="font-medium mb-4 text-gray-700 flex items-center gap-2">
              <Landmark className="w-4 h-4" />
              Bank Account Details
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="company_bank_name">Bank Name</Label>
                <Input
                  id="company_bank_name"
                  value={formData.company_bank_name}
                  onChange={(e) => setFormData({ ...formData, company_bank_name: e.target.value })}
                  placeholder="e.g., HDFC Bank"
                  data-testid="bank-name-input"
                />
              </div>
              <div>
                <Label htmlFor="company_bank_branch">Branch Name</Label>
                <Input
                  id="company_bank_branch"
                  value={formData.company_bank_branch}
                  onChange={(e) => setFormData({ ...formData, company_bank_branch: e.target.value })}
                  placeholder="e.g., Fort Branch, Mumbai"
                  data-testid="bank-branch-input"
                />
              </div>
              <div>
                <Label htmlFor="company_bank_account">Account Number</Label>
                <Input
                  id="company_bank_account"
                  value={formData.company_bank_account}
                  onChange={(e) => setFormData({ ...formData, company_bank_account: e.target.value })}
                  placeholder="e.g., 50100123456789"
                  data-testid="bank-account-input"
                />
              </div>
              <div>
                <Label htmlFor="company_bank_ifsc">IFSC Code</Label>
                <Input
                  id="company_bank_ifsc"
                  value={formData.company_bank_ifsc}
                  onChange={(e) => setFormData({ ...formData, company_bank_ifsc: e.target.value.toUpperCase() })}
                  placeholder="e.g., HDFC0000001"
                  maxLength={11}
                  data-testid="bank-ifsc-input"
                />
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end pt-4">
            <Button 
              onClick={handleSave} 
              disabled={saving}
              className="bg-emerald-600 hover:bg-emerald-700"
              data-testid="save-settings-btn"
            >
              {saving ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Settings
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Document Uploads */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Company Documents
          </CardTitle>
          <CardDescription>
            Upload required company documents for verification and reference
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <DocumentCard
              title="CML - CDSL"
              icon={FileText}
              documentType="cml_cdsl"
              url={documents.cml_cdsl_url}
            />
            <DocumentCard
              title="CML - NSDL"
              icon={FileText}
              documentType="cml_nsdl"
              url={documents.cml_nsdl_url}
            />
            <DocumentCard
              title="Cancelled Cheque"
              icon={CreditCard}
              documentType="cancelled_cheque"
              url={documents.cancelled_cheque_url}
            />
            <DocumentCard
              title="PAN Card"
              icon={CreditCard}
              documentType="pan_card"
              url={documents.pan_card_url}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default CompanyMaster;
