import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '../utils/api';
import { Plus, Trash2, Key, UserX, UserCheck, Users, Shield, Link2, Unlink, ChevronRight, Building, LogIn, Eye } from 'lucide-react';

const ROLES = {
  1: { name: 'PE Desk', color: 'bg-purple-100 text-purple-800' },
  2: { name: 'PE Manager', color: 'bg-indigo-100 text-indigo-800' },
  3: { name: 'Finance', color: 'bg-emerald-100 text-emerald-800' },
  4: { name: 'Viewer', color: 'bg-gray-100 text-gray-800' },
  5: { name: 'Partners Desk', color: 'bg-pink-100 text-pink-800' },
  6: { name: 'Business Partner', color: 'bg-orange-100 text-orange-800' },
};

const HIERARCHY_LEVELS = {
  1: { name: 'Employee', color: 'bg-gray-100 text-gray-700' },
  2: { name: 'Manager', color: 'bg-green-100 text-green-700' },
  3: { name: 'Zonal Head', color: 'bg-blue-100 text-blue-700' },
  4: { name: 'Regional Manager', color: 'bg-cyan-100 text-cyan-700' },
  5: { name: 'Business Head', color: 'bg-purple-100 text-purple-700' }
};

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [managers, setManagers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [hierarchyDialogOpen, setHierarchyDialogOpen] = useState(false);
  const [proxyDialogOpen, setProxyDialogOpen] = useState(false);
  const [proxyLoading, setProxyLoading] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedManagerId, setSelectedManagerId] = useState('');
  const [selectedHierarchyLevel, setSelectedHierarchyLevel] = useState(1);
  const [availableManagers, setAvailableManagers] = useState([]);
  const [potentialManagers, setPotentialManagers] = useState([]);
  const [newPassword, setNewPassword] = useState('');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    role: 5,
    hierarchy_level: 1,
    reports_to: ''
  });

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isPEDesk = currentUser.role === 1;

  useEffect(() => {
    fetchUsers();
    fetchPotentialManagers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.get('/users/hierarchy');
      setUsers(response.data);
    } catch (error) {
      toast.error('Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const fetchPotentialManagers = async () => {
    try {
      const response = await api.get('/users/hierarchy/potential-managers');
      setPotentialManagers(response.data);
    } catch (error) {
      console.error('Failed to fetch potential managers');
    }
  };

  const fetchAvailableManagers = async (userRole) => {
    try {
      const response = await api.get(`/users/managers-list?role=${userRole}`);
      setAvailableManagers(response.data);
    } catch (error) {
      toast.error('Failed to fetch managers');
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await api.post('/users', formData);
      toast.success('User created successfully');
      setDialogOpen(false);
      resetForm();
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleUpdateHierarchy = async () => {
    if (!selectedUser) return;
    try {
      await api.put(`/users/${selectedUser.id}/hierarchy`, {
        hierarchy_level: selectedHierarchyLevel,
        reports_to: selectedManagerId || null
      });
      toast.success('Hierarchy updated successfully');
      setHierarchyDialogOpen(false);
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update hierarchy');
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    try {
      await api.delete(`/users/${selectedUser.id}`);
      toast.success('User deleted successfully');
      setDeleteDialogOpen(false);
      setSelectedUser(null);
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete user');
    }
  };

  const handleResetPassword = async () => {
    if (!selectedUser || !newPassword) return;
    try {
      await api.post(`/users/${selectedUser.id}/reset-password?new_password=${encodeURIComponent(newPassword)}`);
      toast.success('Password reset successfully');
      setResetPasswordDialogOpen(false);
      setSelectedUser(null);
      setNewPassword('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset password');
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    try {
      await api.put(`/users/${userId}/role?role=${newRole}`);
      toast.success('Role updated successfully');
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleAssignManager = async () => {
    if (!selectedUser) return;
    try {
      const managerId = selectedManagerId === 'none' ? '' : selectedManagerId;
      await api.put(`/users/${selectedUser.id}/assign-manager?manager_id=${managerId}`);
      toast.success(managerId ? 'Manager assigned successfully' : 'Manager assignment removed');
      setAssignDialogOpen(false);
      setSelectedUser(null);
      setSelectedManagerId('');
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign manager');
    }
  };

  const openAssignDialog = async (user) => {
    setSelectedUser(user);
    setSelectedManagerId(user.manager_id || 'none');
    await fetchAvailableManagers(user.role);
    setAssignDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({ email: '', password: '', name: '', role: 5, hierarchy_level: 1, reports_to: '' });
  };

  const openHierarchyDialog = (user) => {
    setSelectedUser(user);
    setSelectedHierarchyLevel(user.hierarchy_level || 1);
    setSelectedManagerId(user.reports_to || user.manager_id || '');
    setHierarchyDialogOpen(true);
  };

  const openDeleteDialog = (user) => {
    setSelectedUser(user);
    setDeleteDialogOpen(true);
  };

  const openResetPasswordDialog = (user) => {
    setSelectedUser(user);
    setNewPassword('');
    setResetPasswordDialogOpen(true);
  };

  // Proxy Login Handler
  const handleProxyLogin = async () => {
    if (!selectedUser) return;
    
    setProxyLoading(true);
    try {
      const response = await api.post('/auth/proxy-login', {
        target_user_id: selectedUser.id
      });
      
      // Store original user info for return
      const originalUser = JSON.parse(localStorage.getItem('user') || '{}');
      localStorage.setItem('original_user', JSON.stringify(originalUser));
      
      // Update token and user info
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      localStorage.setItem('proxy_session', JSON.stringify(response.data.proxy_session));
      
      toast.success(`Now viewing as ${selectedUser.name}`);
      setProxyDialogOpen(false);
      
      // Reload the page to refresh all components with new user context
      window.location.href = '/';
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to proxy login');
    } finally {
      setProxyLoading(false);
    }
  };

  // Group users by hierarchy for the hierarchy view
  const buildHierarchy = () => {
    const businessHeads = users.filter(u => u.role === 11);
    const regionalManagers = users.filter(u => u.role === 10);
    const zonalManagers = users.filter(u => u.role === 3);
    const managersData = users.filter(u => u.role === 4);
    const employees = users.filter(u => u.role === 5);
    const peUsers = users.filter(u => u.role <= 2);
    const viewers = users.filter(u => u.role === 6);
    const financeUsers = users.filter(u => u.role === 7);
    const partnersDesk = users.filter(u => u.role === 9);

    return { businessHeads, regionalManagers, zonalManagers, managers: managersData, employees, peUsers, viewers, financeUsers, partnersDesk };
  };

  const hierarchy = buildHierarchy();

  const getSubordinates = (managerId) => {
    return users.filter(u => u.manager_id === managerId);
  };

  const canAssignManager = (user) => {
    // Only Employees and Managers can be assigned to a manager
    return user.role === 4 || user.role === 5;
  };

  const getAssignmentLabel = (role) => {
    if (role === 5) return 'Assign to Manager';
    if (role === 4) return 'Assign to Zonal Manager';
    return 'Assign';
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 space-y-6" data-testid="user-management-page">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2">
            <Users className="h-6 w-6 md:h-8 md:w-8 text-primary" />
            User Management
          </h1>
          <p className="text-muted-foreground text-sm md:text-base">Manage users, roles, and team hierarchy</p>
        </div>
        <Button onClick={() => setDialogOpen(true)} className="w-full sm:w-auto" data-testid="add-user-btn">
          <Plus className="h-4 w-4 mr-2" />
          Add User
        </Button>
      </div>

      <Tabs defaultValue="users" className="w-full">
        <TabsList className="grid w-full grid-cols-2 max-w-md">
          <TabsTrigger value="users" data-testid="users-tab">All Users</TabsTrigger>
          <TabsTrigger value="hierarchy" data-testid="hierarchy-tab">Team Hierarchy</TabsTrigger>
        </TabsList>

        {/* All Users Tab */}
        <TabsContent value="users">
          <Card>
            <CardHeader>
              <CardTitle>System Users</CardTitle>
              <CardDescription>Total: {users.length} users</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-center py-8 text-muted-foreground">Loading...</p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>PAN</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Hierarchy Level</TableHead>
                        <TableHead>Reports To</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {users.map((user) => (
                        <TableRow key={user.id} data-testid={`user-row-${user.id}`}>
                          <TableCell className="font-medium">{user.name}</TableCell>
                          <TableCell className="text-sm">{user.email}</TableCell>
                          <TableCell className="font-mono text-xs">{user.pan_number || '-'}</TableCell>
                          <TableCell>
                            <Select
                              value={String(user.role)}
                              onValueChange={(value) => handleRoleChange(user.id, parseInt(value))}
                              disabled={user.email === 'pe@smifs.com'}
                            >
                              <SelectTrigger className="w-36">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {Object.entries(ROLES).map(([key, { name }]) => (
                                  <SelectItem key={key} value={key}>{name}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </TableCell>
                          <TableCell>
                            {/* Show hierarchy level with color badge */}
                            {user.role && ![1, 2, 6, 7, 8, 9].includes(user.role) ? (
                              <Badge className={HIERARCHY_LEVELS[user.hierarchy_level || 1]?.color || 'bg-gray-100'}>
                                {HIERARCHY_LEVELS[user.hierarchy_level || 1]?.name || 'Employee'}
                              </Badge>
                            ) : (
                              <span className="text-muted-foreground text-sm">N/A</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {user.reports_to_name || user.manager_name ? (
                              <Badge variant="outline" className="font-normal">
                                <Link2 className="h-3 w-3 mr-1" />
                                {user.reports_to_name || user.manager_name}
                              </Badge>
                            ) : (
                              <span className="text-muted-foreground text-sm">—</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {user.is_active !== false ? (
                              <Badge className="bg-green-100 text-green-800">
                                <UserCheck className="h-3 w-3 mr-1" />Active
                              </Badge>
                            ) : (
                              <Badge className="bg-red-100 text-red-800">
                                <UserX className="h-3 w-3 mr-1" />Inactive
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              {/* Hierarchy Management Button - for Employee/Manager/etc roles */}
                              {![1, 2, 6, 7, 8, 9].includes(user.role) && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => openHierarchyDialog(user)}
                                  title="Manage Hierarchy"
                                  data-testid={`hierarchy-${user.id}`}
                                  className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                >
                                  <Users className="h-4 w-4" />
                                </Button>
                              )}
                              {canAssignManager(user) && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => openAssignDialog(user)}
                                  title={getAssignmentLabel(user.role)}
                                  data-testid={`assign-manager-${user.id}`}
                                >
                                  <Link2 className="h-4 w-4" />
                                </Button>
                              )}
                              {/* Proxy Login - PE Desk only, not for self or other PE Desk */}
                              {isPEDesk && user.id !== currentUser.id && user.role !== 1 && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    setSelectedUser(user);
                                    setProxyDialogOpen(true);
                                  }}
                                  className="text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                                  title={`Login as ${user.name}`}
                                  data-testid={`proxy-login-${user.id}`}
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                              )}
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openResetPasswordDialog(user)}
                                title="Reset Password"
                              >
                                <Key className="h-4 w-4" />
                              </Button>
                              {user.email !== 'pe@smifs.com' && isPEDesk && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => openDeleteDialog(user)}
                                  className="text-red-600"
                                  title="Delete User"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              )}
                              {user.email === 'pe@smifs.com' && (
                                <Badge variant="outline" className="ml-2">
                                  <Shield className="h-3 w-3 mr-1" />Super Admin
                                </Badge>
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

        {/* Hierarchy Tab */}
        <TabsContent value="hierarchy">
          <div className="space-y-6">
            {/* PE Users */}
            {hierarchy.peUsers.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Shield className="h-5 w-5 text-purple-600" />
                    PE Level Users
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {hierarchy.peUsers.map(user => (
                      <Badge key={user.id} className={ROLES[user.role]?.color || 'bg-gray-100'}>
                        {user.name} ({ROLES[user.role]?.name})
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Zonal Managers with their teams */}
            {hierarchy.zonalManagers.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Building className="h-5 w-5 text-blue-600" />
                    Zonal Managers & Teams
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {hierarchy.zonalManagers.map(zm => {
                    const zmManagers = getSubordinates(zm.id);
                    return (
                      <div key={zm.id} className="border rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-3">
                          <Badge className={ROLES[3]?.color}>{zm.name}</Badge>
                          <span className="text-sm text-muted-foreground">
                            ({zmManagers.length} direct reports)
                          </span>
                        </div>
                        
                        {zmManagers.length > 0 ? (
                          <div className="ml-4 space-y-3">
                            {zmManagers.map(manager => {
                              const managerEmployees = getSubordinates(manager.id);
                              return (
                                <div key={manager.id} className="border-l-2 border-green-300 pl-4">
                                  <div className="flex items-center gap-2 mb-2">
                                    <ChevronRight className="h-4 w-4 text-green-600" />
                                    <Badge className={ROLES[4]?.color}>{manager.name}</Badge>
                                    <span className="text-sm text-muted-foreground">
                                      ({managerEmployees.length} employees)
                                    </span>
                                  </div>
                                  {managerEmployees.length > 0 && (
                                    <div className="ml-6 flex flex-wrap gap-1">
                                      {managerEmployees.map(emp => (
                                        <Badge key={emp.id} variant="outline" className="text-xs">
                                          {emp.name}
                                        </Badge>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="ml-4 text-sm text-muted-foreground">No managers assigned</p>
                        )}
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            )}

            {/* Unassigned Managers */}
            {(() => {
              const unassignedManagers = hierarchy.managers.filter(m => !m.manager_id);
              if (unassignedManagers.length === 0) return null;
              return (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2 text-amber-600">
                      <Unlink className="h-5 w-5" />
                      Unassigned Managers
                    </CardTitle>
                    <CardDescription>These managers are not assigned to any Zonal Manager</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {unassignedManagers.map(manager => {
                        const managerEmployees = getSubordinates(manager.id);
                        return (
                          <div key={manager.id} className="border rounded-lg p-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Badge className={ROLES[4]?.color}>{manager.name}</Badge>
                                <span className="text-sm text-muted-foreground">
                                  ({managerEmployees.length} employees)
                                </span>
                              </div>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => openAssignDialog(manager)}
                              >
                                <Link2 className="h-3 w-3 mr-1" />
                                Assign
                              </Button>
                            </div>
                            {managerEmployees.length > 0 && (
                              <div className="mt-2 ml-4 flex flex-wrap gap-1">
                                {managerEmployees.map(emp => (
                                  <Badge key={emp.id} variant="outline" className="text-xs">
                                    {emp.name}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              );
            })()}

            {/* Unassigned Employees */}
            {(() => {
              const unassignedEmployees = hierarchy.employees.filter(e => !e.manager_id);
              if (unassignedEmployees.length === 0) return null;
              return (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2 text-amber-600">
                      <Unlink className="h-5 w-5" />
                      Unassigned Employees
                    </CardTitle>
                    <CardDescription>These employees are not assigned to any Manager</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {unassignedEmployees.map(emp => (
                        <div key={emp.id} className="flex items-center gap-1 border rounded-lg px-3 py-2">
                          <Badge className={ROLES[5]?.color}>{emp.name}</Badge>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => openAssignDialog(emp)}
                            className="h-6 w-6 p-0"
                          >
                            <Link2 className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })()}
          </div>
        </TabsContent>
      </Tabs>

      {/* Create User Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid="create-user-dialog">
          <DialogHeader>
            <DialogTitle>Create New User</DialogTitle>
            <DialogDescription>Add a new user to the system</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateUser} className="space-y-4">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Full name"
                required
                data-testid="user-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Email *</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="user@smifs.com"
                required
                data-testid="user-email-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Password *</Label>
              <Input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder="Minimum 6 characters"
                required
                minLength={6}
                data-testid="user-password-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Role *</Label>
              <Select
                value={String(formData.role)}
                onValueChange={(value) => setFormData({ ...formData, role: parseInt(value) })}
              >
                <SelectTrigger data-testid="user-role-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(ROLES).map(([key, { name }]) => (
                    <SelectItem key={key} value={key}>{name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button type="submit" data-testid="create-user-submit">Create User</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Assign Manager Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent data-testid="assign-manager-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Link2 className="h-5 w-5" />
              {selectedUser?.role === 5 ? 'Assign to Manager' : 'Assign to Zonal Manager'}
            </DialogTitle>
            <DialogDescription>
              Assign <strong>{selectedUser?.name}</strong> to a {selectedUser?.role === 5 ? 'Manager' : 'Zonal Manager'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{selectedUser?.role === 5 ? 'Select Manager' : 'Select Zonal Manager'}</Label>
              <Select value={selectedManagerId} onValueChange={setSelectedManagerId}>
                <SelectTrigger data-testid="manager-select">
                  <SelectValue placeholder="Select..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">
                    <span className="text-muted-foreground">— No Assignment —</span>
                  </SelectItem>
                  {availableManagers.map(manager => (
                    <SelectItem key={manager.id} value={manager.id}>
                      {manager.name} ({manager.role_name})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {selectedUser?.manager_name && (
              <p className="text-sm text-muted-foreground">
                Currently assigned to: <strong>{selectedUser.manager_name}</strong>
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAssignManager} data-testid="confirm-assign">
              <Link2 className="h-4 w-4 mr-2" />
              {selectedManagerId === 'none' ? 'Remove Assignment' : 'Assign'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete User Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600">Delete User</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{selectedUser?.name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteUser} data-testid="confirm-delete-user">
              <Trash2 className="h-4 w-4 mr-2" />Delete User
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={resetPasswordDialogOpen} onOpenChange={setResetPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              Set a new password for <strong>{selectedUser?.name}</strong>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>New Password *</Label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Minimum 6 characters"
                minLength={6}
                data-testid="new-password-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResetPasswordDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleResetPassword} disabled={newPassword.length < 6} data-testid="confirm-reset-password">
              <Key className="h-4 w-4 mr-2" />Reset Password
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Proxy Login Dialog */}
      <Dialog open={proxyDialogOpen} onOpenChange={setProxyDialogOpen}>
        <DialogContent data-testid="proxy-login-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5 text-amber-600" />
              Login as User
            </DialogTitle>
            <DialogDescription>
              You are about to view the application as another user. All your actions will be logged.
            </DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="py-4">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
                <p className="text-sm text-amber-800">
                  <strong>Warning:</strong> While in proxy mode, you will see the app exactly as{' '}
                  <strong>{selectedUser.name}</strong> sees it. You can make changes on their behalf.
                </p>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center py-2 border-b">
                  <span className="text-sm text-gray-500">User</span>
                  <span className="font-medium">{selectedUser.name}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b">
                  <span className="text-sm text-gray-500">Email</span>
                  <span className="text-sm">{selectedUser.email}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b">
                  <span className="text-sm text-gray-500">Role</span>
                  <Badge className={ROLES[selectedUser.role]?.color}>
                    {ROLES[selectedUser.role]?.name || 'Unknown'}
                  </Badge>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setProxyDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleProxyLogin} 
              disabled={proxyLoading}
              className="bg-amber-600 hover:bg-amber-700"
              data-testid="confirm-proxy-login"
            >
              <LogIn className="h-4 w-4 mr-2" />
              {proxyLoading ? 'Switching...' : `Login as ${selectedUser?.name}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Hierarchy Management Dialog */}
      <Dialog open={hierarchyDialogOpen} onOpenChange={setHierarchyDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-blue-600" />
              Manage Hierarchy for {selectedUser?.name}
            </DialogTitle>
            <DialogDescription>
              Set the hierarchy level and reporting structure for this user.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Hierarchy Level</Label>
              <Select
                value={String(selectedHierarchyLevel)}
                onValueChange={(value) => setSelectedHierarchyLevel(parseInt(value))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select level" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(HIERARCHY_LEVELS).map(([level, { name }]) => (
                    <SelectItem key={level} value={level}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Employee → Manager → Zonal Head → Regional Manager → Business Head
              </p>
            </div>
            <div className="space-y-2">
              <Label>Reports To</Label>
              <Select
                value={selectedManagerId || 'none'}
                onValueChange={(value) => setSelectedManagerId(value === 'none' ? '' : value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select manager" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">— No Manager —</SelectItem>
                  {potentialManagers
                    .filter(m => m.id !== selectedUser?.id)
                    .map((manager) => (
                      <SelectItem key={manager.id} value={manager.id}>
                        {manager.name} ({manager.hierarchy_level_name})
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Select who this user reports to in the organizational hierarchy.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setHierarchyDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateHierarchy} className="bg-blue-600 hover:bg-blue-700">
              Save Hierarchy
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default UserManagement;
