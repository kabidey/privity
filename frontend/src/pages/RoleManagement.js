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

  const { isPEDesk } = useCurrentUser();

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
    if (!isPEDesk) {
      toast.error('Access denied. Only PE Desk can manage roles.');
      navigate('/');
      return;
    }
    fetchData();
  }, [isPEDesk, navigate]);

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
        await api.put(`/roles/${editingRole.id}`, formData);
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

      {/* Roles List */}
      <Card>
        <CardHeader>
          <CardTitle>System & Custom Roles</CardTitle>
          <CardDescription>
            System roles (1-7) cannot be deleted but their permissions can be customized
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
                <TableRow key={role.id}>
                  <TableCell className="font-mono">{role.id}</TableCell>
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
                      <span className="text-emerald-600 font-medium">All Permissions</span>
                    ) : (
                      <span className="text-muted-foreground">
                        {role.permissions?.length || 0} permissions
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenDialog(role)}
                        data-testid={`edit-role-${role.id}`}
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
              <Label>Permissions</Label>
              <ScrollArea className="h-[400px] border rounded-md p-4">
                <Accordion type="multiple" className="w-full">
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
