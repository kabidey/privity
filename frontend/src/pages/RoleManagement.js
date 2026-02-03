import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { 
  Shield, Plus, Pencil, Trash2, Users, Lock, Unlock, 
  Check, X, ChevronRight, Settings, Eye, Save
} from 'lucide-react';

const RoleManagement = () => {
  const navigate = useNavigate();
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState({});
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [roleToDelete, setRoleToDelete] = useState(null);
  const [saving, setSaving] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    permissions: [],
    color: 'bg-gray-100 text-gray-800'
  });

  const { isPEDesk, user: currentUser } = useCurrentUser();

  const colorOptions = [
    { value: 'bg-purple-100 text-purple-800', label: 'Purple' },
    { value: 'bg-indigo-100 text-indigo-800', label: 'Indigo' },
    { value: 'bg-blue-100 text-blue-800', label: 'Blue' },
    { value: 'bg-emerald-100 text-emerald-800', label: 'Green' },
    { value: 'bg-orange-100 text-orange-800', label: 'Orange' },
    { value: 'bg-pink-100 text-pink-800', label: 'Pink' },
    { value: 'bg-gray-100 text-gray-800', label: 'Gray' },
    { value: 'bg-red-100 text-red-800', label: 'Red' },
  ];

  useEffect(() => {
    // Wait for user to be loaded before checking access
    if (currentUser === null) return;
    
    if (!isPEDesk) {
      toast.error('Access denied. Only PE Desk can manage roles.');
      navigate('/');
      return;
    }
    fetchData();
  }, [isPEDesk, currentUser, navigate]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [rolesRes, permsRes] = await Promise.all([
        api.get('/roles'),
        api.get('/roles/permissions')
      ]);
      setRoles(rolesRes.data);
      setPermissions(permsRes.data);
    } catch (error) {
      toast.error('Failed to load roles');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (role = null) => {
    if (role) {
      setEditingRole(role);
      setFormData({
        name: role.name,
        description: role.description || '',
        permissions: role.permissions || [],
        color: role.color || 'bg-gray-100 text-gray-800'
      });
    } else {
      setEditingRole(null);
      setFormData({
        name: '',
        description: '',
        permissions: [],
        color: 'bg-gray-100 text-gray-800'
      });
    }
    setDialogOpen(true);
  };

  const handleSaveRole = async () => {
    if (!formData.name.trim()) {
      toast.error('Role name is required');
      return;
    }

    setSaving(true);
    try {
      if (editingRole) {
        // For system roles, don't send the name field (can't be renamed)
        const updateData = editingRole.is_system 
          ? { 
              description: formData.description,
              permissions: formData.permissions,
              color: formData.color
            }
          : formData;
        
        await api.put(`/roles/${editingRole.id}`, updateData);
        toast.success('Role updated successfully');
      } else {
        await api.post('/roles', formData);
        toast.success('Role created successfully');
      }
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save role');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRole = async () => {
    if (!roleToDelete) return;
    
    try {
      await api.delete(`/roles/${roleToDelete.id}`);
      toast.success('Role deleted successfully');
      setDeleteDialogOpen(false);
      setRoleToDelete(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete role');
    }
  };

  const togglePermission = (permKey) => {
    setFormData(prev => {
      const perms = [...prev.permissions];
      const index = perms.indexOf(permKey);
      if (index > -1) {
        perms.splice(index, 1);
      } else {
        perms.push(permKey);
      }
      return { ...prev, permissions: perms };
    });
  };

  const toggleCategoryPermissions = (categoryKey, categoryPerms) => {
    setFormData(prev => {
      const perms = new Set(prev.permissions);
      const allSelected = categoryPerms.every(p => perms.has(p.key));
      
      if (allSelected) {
        // Remove all
        categoryPerms.forEach(p => perms.delete(p.key));
      } else {
        // Add all
        categoryPerms.forEach(p => perms.add(p.key));
      }
      
      return { ...prev, permissions: Array.from(perms) };
    });
  };

  const isPermissionSelected = (permKey) => {
    if (formData.permissions.includes('*')) return true;
    const category = permKey.split('.')[0];
    if (formData.permissions.includes(`${category}.*`)) return true;
    return formData.permissions.includes(permKey);
  };

  const isCategoryFullySelected = (categoryPerms) => {
    return categoryPerms.every(p => isPermissionSelected(p.key));
  };

  const countSelectedInCategory = (categoryPerms) => {
    return categoryPerms.filter(p => isPermissionSelected(p.key)).length;
  };

  const getUserCount = (roleId) => {
    // This would need a backend call, for now return N/A
    return '-';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Get permission display for a role
  const getPermissionSummary = (role) => {
    if (!role.permissions || role.permissions.length === 0) return [];
    if (role.permissions.includes('*')) return ['All Access'];
    
    // Group by category
    const categories = {};
    role.permissions.forEach(p => {
      const cat = p.split('.')[0];
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(p);
    });
    return Object.keys(categories);
  };

  // Visual permission card component
  const PermissionCard = ({ role }) => {
    const perms = role.permissions || [];
    const hasAll = perms.includes('*');
    
    // Map categories to their display info
    const categoryInfo = {
      dashboard: { icon: '📊', label: 'Dashboard', color: 'bg-blue-100 text-blue-800' },
      bookings: { icon: '📝', label: 'Bookings', color: 'bg-green-100 text-green-800' },
      clients: { icon: '👥', label: 'Clients', color: 'bg-purple-100 text-purple-800' },
      client_approval: { icon: '✅', label: 'Client Approval', color: 'bg-teal-100 text-teal-800' },
      stocks: { icon: '📈', label: 'Stocks', color: 'bg-orange-100 text-orange-800' },
      inventory: { icon: '📦', label: 'Inventory', color: 'bg-yellow-100 text-yellow-800' },
      purchases: { icon: '🛒', label: 'Purchases', color: 'bg-pink-100 text-pink-800' },
      vendors: { icon: '🏪', label: 'Vendors', color: 'bg-indigo-100 text-indigo-800' },
      contract_notes: { icon: '📄', label: 'Confirmation Notes', color: 'bg-cyan-100 text-cyan-800' },
      finance: { icon: '💰', label: 'Finance', color: 'bg-emerald-100 text-emerald-800' },
      analytics: { icon: '📉', label: 'Analytics', color: 'bg-violet-100 text-violet-800' },
      users: { icon: '👤', label: 'Users', color: 'bg-rose-100 text-rose-800' },
      roles: { icon: '🔐', label: 'Roles', color: 'bg-amber-100 text-amber-800' },
      business_partners: { icon: '🤝', label: 'Business Partners', color: 'bg-lime-100 text-lime-800' },
      referral_partners: { icon: '🔗', label: 'Referral Partners', color: 'bg-sky-100 text-sky-800' },
      reports: { icon: '📊', label: 'Reports', color: 'bg-fuchsia-100 text-fuchsia-800' },
      dp: { icon: '🏦', label: 'DP Operations', color: 'bg-stone-100 text-stone-800' },
      email: { icon: '📧', label: 'Email', color: 'bg-red-100 text-red-800' },
      company: { icon: '🏢', label: 'Company Master', color: 'bg-blue-100 text-blue-800' },
      security: { icon: '🛡️', label: 'Security', color: 'bg-gray-100 text-gray-800' },
      database: { icon: '💾', label: 'Database', color: 'bg-slate-100 text-slate-800' },
      bulk_upload: { icon: '📤', label: 'Bulk Upload', color: 'bg-zinc-100 text-zinc-800' },
      research: { icon: '🔬', label: 'Research', color: 'bg-neutral-100 text-neutral-800' },
    };
    
    if (hasAll) {
      return (
        <div className="p-4 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <Badge className={role.color || 'bg-gray-100'}>{role.name}</Badge>
            <Badge className="bg-emerald-500 text-white">Full Access</Badge>
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(categoryInfo).map(([key, info]) => (
              <div key={key} className={`px-2 py-1 rounded text-xs ${info.color} flex items-center gap-1`}>
                <span>{info.icon}</span>
                <span>{info.label}</span>
                <Check className="h-3 w-3" />
              </div>
            ))}
          </div>
        </div>
      );
    }
    
    // Get categories this role has access to
    const categories = new Set();
    perms.forEach(p => {
      const cat = p.split('.')[0];
      categories.add(cat);
    });
    
    return (
      <div className="p-4 bg-white border rounded-lg">
        <div className="flex items-center gap-2 mb-3">
          <Badge className={role.color || 'bg-gray-100'}>{role.name}</Badge>
          <span className="text-xs text-muted-foreground">{perms.length} permissions</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(categoryInfo).map(([key, info]) => {
            const hasCategory = categories.has(key) || perms.includes(`${key}.*`);
            return (
              <div 
                key={key} 
                className={`px-2 py-1 rounded text-xs flex items-center gap-1 ${
                  hasCategory ? info.color : 'bg-gray-100 text-gray-400'
                }`}
              >
                <span>{info.icon}</span>
                <span>{info.label}</span>
                {hasCategory ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Shield className="h-8 w-8 text-primary" />
            Role & Permission Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Define roles and assign granular permissions
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()} data-testid="create-role-btn">
          <Plus className="h-4 w-4 mr-2" />
          Create Role
        </Button>
      </div>

      {/* Tabs for different views */}
      <Tabs defaultValue="list" className="w-full">
        <TabsList>
          <TabsTrigger value="list">Role List</TabsTrigger>
          <TabsTrigger value="visual">Visual Permissions</TabsTrigger>
          <TabsTrigger value="matrix">Permission Matrix</TabsTrigger>
        </TabsList>
        
        {/* List View */}
        <TabsContent value="list">
          <Card>
            <CardHeader>
              <CardTitle>System & Custom Roles</CardTitle>
              <CardDescription>
                System roles (1-7) cannot be deleted but their permissions can be customized.
              </CardDescription>
            </CardHeader>
            <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">ID</TableHead>
                <TableHead>Role Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Permissions</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {roles.map((role) => (
                <TableRow key={role.id} className="group">
                  <TableCell className="font-mono text-muted-foreground">{role.id}</TableCell>
                  <TableCell>
                    <Badge className={role.color || 'bg-gray-100 text-gray-800'}>
                      {role.name}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground max-w-xs truncate">
                    {role.description || '-'}
                  </TableCell>
                  <TableCell>
                    {role.is_system ? (
                      <Badge variant="outline" className="gap-1">
                        <Lock className="h-3 w-3" />
                        System
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="gap-1">
                        <Unlock className="h-3 w-3" />
                        Custom
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {role.permissions?.includes('*') ? (
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-600 font-medium">All Permissions</span>
                        <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                          Full Access
                        </Badge>
                      </div>
                    ) : role.permissions?.length > 0 ? (
                      <div className="flex flex-col gap-1">
                        <span className="text-sm font-medium">{role.permissions?.length || 0} permissions</span>
                        <div className="flex flex-wrap gap-1 max-w-[300px]">
                          {role.permissions?.slice(0, 4).map(p => {
                            const category = p.split('.')[0];
                            return (
                              <Badge key={p} variant="outline" className="text-[10px] px-1.5 py-0">
                                {category}
                              </Badge>
                            );
                          })}
                          {role.permissions?.length > 4 && (
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                              +{role.permissions.length - 4} more
                            </Badge>
                          )}
                        </div>
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-sm">No permissions</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2 opacity-70 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenDialog(role)}
                        data-testid={`edit-role-${role.id}`}
                        title="Edit role permissions"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      {!role.is_system && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500 hover:text-red-700"
                          onClick={() => {
                            setRoleToDelete(role);
                            setDeleteDialogOpen(true);
                          }}
                          data-testid={`delete-role-${role.id}`}
                          title="Delete role"
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
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Visual Permissions View */}
        <TabsContent value="visual">
          <div className="grid gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Visual Permission Overview</CardTitle>
                <CardDescription>
                  See at a glance what each role can access. Green items are accessible, gray items are restricted.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {roles.map(role => (
                  <PermissionCard key={role.id} role={role} />
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        {/* Permission Matrix View */}
        <TabsContent value="matrix">
          <Card>
            <CardHeader>
              <CardTitle>Permission Matrix</CardTitle>
              <CardDescription>
                Complete view of all permissions across all roles.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky left-0 bg-white z-10 min-w-[200px]">Permission Category</TableHead>
                      {roles.map(role => (
                        <TableHead key={role.id} className="text-center min-w-[100px]">
                          <Badge className={role.color || 'bg-gray-100'} variant="outline">
                            {role.name}
                          </Badge>
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(permissions).map(([catKey, category]) => (
                      <TableRow key={catKey}>
                        <TableCell className="sticky left-0 bg-white font-medium">
                          {category.name}
                          <span className="text-xs text-muted-foreground ml-2">
                            ({category.permissions.length})
                          </span>
                        </TableCell>
                        {roles.map(role => {
                          const rolePerms = role.permissions || [];
                          const hasAll = rolePerms.includes('*');
                          const hasCategoryWildcard = rolePerms.includes(`${catKey}.*`);
                          const categoryPermKeys = category.permissions.map(p => p.key);
                          const matchedPerms = categoryPermKeys.filter(pk => rolePerms.includes(pk));
                          const hasPartial = matchedPerms.length > 0;
                          const hasFull = hasAll || hasCategoryWildcard || matchedPerms.length === categoryPermKeys.length;
                          
                          return (
                            <TableCell key={role.id} className="text-center">
                              {hasFull ? (
                                <Badge className="bg-emerald-100 text-emerald-800">
                                  <Check className="h-3 w-3 mr-1" />
                                  Full
                                </Badge>
                              ) : hasPartial ? (
                                <Badge className="bg-yellow-100 text-yellow-800">
                                  {matchedPerms.length}/{categoryPermKeys.length}
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="text-gray-400">
                                  <X className="h-3 w-3" />
                                </Badge>
                              )}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create/Edit Role Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle>
              {editingRole ? `Edit Role: ${editingRole.name}` : 'Create New Role'}
            </DialogTitle>
            <DialogDescription>
              {editingRole?.is_system 
                ? 'System roles cannot be renamed or deleted, but you can customize their permissions.'
                : 'Define the role name and assign permissions.'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-6">
            {/* Left Column - Role Details */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Role Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Regional Manager"
                  disabled={editingRole?.is_system}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Describe what this role can do..."
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label>Badge Color</Label>
                <div className="flex flex-wrap gap-2">
                  {colorOptions.map((color) => (
                    <button
                      key={color.value}
                      type="button"
                      onClick={() => setFormData({ ...formData, color: color.value })}
                      className={`px-3 py-1 rounded-full text-sm transition-all ${color.value} ${
                        formData.color === color.value ? 'ring-2 ring-offset-2 ring-primary' : ''
                      }`}
                    >
                      {color.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  <strong>Selected Permissions:</strong> {formData.permissions.length}
                </div>
              </div>
            </div>

            {/* Right Column - Permissions */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Permissions</Label>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      // Select all permissions
                      const allPerms = Object.values(permissions).flatMap(cat => cat.permissions.map(p => p.key));
                      setFormData(prev => ({ ...prev, permissions: allPerms }));
                    }}
                    className="text-xs"
                  >
                    Select All
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setFormData(prev => ({ ...prev, permissions: [] }))}
                    className="text-xs"
                  >
                    Clear All
                  </Button>
                </div>
              </div>
              
              {/* Quick Presets */}
              <div className="flex flex-wrap gap-1 pb-2">
                <span className="text-xs text-muted-foreground mr-2">Presets:</span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => {
                    // View-only preset
                    const viewPerms = Object.values(permissions)
                      .flatMap(cat => cat.permissions)
                      .filter(p => p.key.includes('.view') || p.key.includes('.view_'))
                      .map(p => p.key);
                    setFormData(prev => ({ ...prev, permissions: viewPerms }));
                  }}
                >
                  View Only
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => {
                    // Standard user preset
                    setFormData(prev => ({
                      ...prev,
                      permissions: [
                        'dashboard.view', 'bookings.view', 'bookings.create',
                        'clients.view', 'clients.create', 'stocks.view',
                        'inventory.view', 'reports.view'
                      ]
                    }));
                  }}
                >
                  Standard User
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => {
                    // Manager preset
                    setFormData(prev => ({
                      ...prev,
                      permissions: [
                        'dashboard.view', 'dashboard.pe_view',
                        'bookings.view', 'bookings.view_all', 'bookings.create', 'bookings.edit', 'bookings.approve', 'bookings.record_payment',
                        'clients.view', 'clients.create', 'clients.edit', 'client_approval.view', 'client_approval.approve',
                        'stocks.view', 'inventory.view', 'inventory.edit_landing_price',
                        'purchases.view', 'purchases.create',
                        'finance.view', 'finance.view_reports',
                        'reports.view', 'reports.pnl', 'analytics.view',
                        'users.view', 'dp.view_receivables', 'dp.transfer'
                      ]
                    }));
                  }}
                >
                  Manager
                </Button>
              </div>
              
              <ScrollArea className="h-[350px] border rounded-md p-4">
                <Accordion type="multiple" className="w-full" defaultValue={Object.keys(permissions).slice(0, 3)}>
                  {Object.entries(permissions).map(([categoryKey, category]) => (
                    <AccordionItem key={categoryKey} value={categoryKey}>
                      <AccordionTrigger className="hover:no-underline">
                        <div className="flex items-center justify-between w-full pr-4">
                          <span className="font-medium">{category.name}</span>
                          <Badge variant="secondary" className="ml-2">
                            {countSelectedInCategory(category.permissions)}/{category.permissions.length}
                          </Badge>
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-2 pl-2">
                          {/* Select All for Category */}
                          <div className="flex items-center space-x-2 pb-2 border-b">
                            <Checkbox
                              id={`${categoryKey}-all`}
                              checked={isCategoryFullySelected(category.permissions)}
                              onCheckedChange={() => toggleCategoryPermissions(categoryKey, category.permissions)}
                            />
                            <label
                              htmlFor={`${categoryKey}-all`}
                              className="text-sm font-medium cursor-pointer"
                            >
                              Select All
                            </label>
                          </div>
                          
                          {/* Individual Permissions */}
                          {category.permissions.map((perm) => (
                            <div key={perm.key} className="flex items-start space-x-2 py-1">
                              <Checkbox
                                id={perm.key}
                                checked={isPermissionSelected(perm.key)}
                                onCheckedChange={() => togglePermission(perm.key)}
                              />
                              <div className="grid gap-0.5 leading-none">
                                <label
                                  htmlFor={perm.key}
                                  className="text-sm font-medium cursor-pointer"
                                >
                                  {perm.name}
                                </label>
                                <p className="text-xs text-muted-foreground">
                                  {perm.description}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              </ScrollArea>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveRole} disabled={saving}>
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  {editingRole ? 'Update Role' : 'Create Role'}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Role</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the role "{roleToDelete?.name}"? 
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteRole}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Role
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RoleManagement;
