import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '../utils/api';
import { Users, Shield, Crown, Briefcase, Eye } from 'lucide-react';

const ROLES = {
  1: { name: 'PE Desk', icon: Crown, color: 'bg-amber-500', description: 'Full system access' },
  2: { name: 'Zonal Manager', icon: Shield, color: 'bg-purple-500', description: 'Manage users, clients, stocks, bookings' },
  3: { name: 'Manager', icon: Briefcase, color: 'bg-blue-500', description: 'Manage own clients and bookings' },
  4: { name: 'Employee', icon: Users, color: 'bg-green-500', description: 'Create bookings, view clients' },
  5: { name: 'Viewer', icon: Eye, color: 'bg-gray-500', description: 'Read-only access' },
};

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updatingUserId, setUpdatingUserId] = useState(null);
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.get('/users');
      setUsers(response.data);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('You do not have permission to manage users');
      } else {
        toast.error('Failed to load users');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    if (userId === currentUser.id) {
      toast.error('You cannot change your own role');
      return;
    }

    setUpdatingUserId(userId);
    try {
      await api.put(`/users/${userId}/role?role=${newRole}`);
      toast.success('User role updated successfully');
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    } finally {
      setUpdatingUserId(null);
    }
  };

  const getRoleBadge = (role) => {
    const roleInfo = ROLES[role] || ROLES[5];
    const Icon = roleInfo.icon;
    return (
      <Badge className={`${roleInfo.color} text-white flex items-center gap-1 w-fit`}>
        <Icon className="h-3 w-3" />
        {roleInfo.name}
      </Badge>
    );
  };

  return (
    <div className="p-8 page-enter" data-testid="user-management-page">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">User Management</h1>
        <p className="text-muted-foreground text-base">Manage user roles and permissions</p>
      </div>

      {/* Role Legend */}
      <Card className="border shadow-sm mb-6">
        <CardHeader className="pb-4">
          <CardTitle className="text-base font-semibold">Role Permissions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {Object.entries(ROLES).map(([roleId, roleInfo]) => {
              const Icon = roleInfo.icon;
              return (
                <div key={roleId} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30">
                  <div className={`p-2 rounded-md ${roleInfo.color}`}>
                    <Icon className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <div className="font-semibold text-sm">{roleInfo.name}</div>
                    <div className="text-xs text-muted-foreground">{roleInfo.description}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" strokeWidth={1.5} />
            All Users ({users.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-12 text-center text-muted-foreground">Loading users...</div>
          ) : users.length === 0 ? (
            <div className="text-center py-12" data-testid="no-users-message">
              <p className="text-muted-foreground">No users found or you don't have permission to view users.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">User</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Email</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Current Role</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Joined</TableHead>
                    <TableHead className="text-xs uppercase tracking-wider font-semibold">Change Role</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.id} className="table-row" data-testid="user-row">
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                            <span className="text-sm font-semibold text-primary">
                              {user.name?.charAt(0)?.toUpperCase() || 'U'}
                            </span>
                          </div>
                          <div>
                            <div className="font-medium">{user.name}</div>
                            {user.id === currentUser.id && (
                              <span className="text-xs text-muted-foreground">(You)</span>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">{user.email}</TableCell>
                      <TableCell>{getRoleBadge(user.role)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(user.created_at).toLocaleDateString('en-IN')}
                      </TableCell>
                      <TableCell>
                        {user.id === currentUser.id ? (
                          <span className="text-xs text-muted-foreground">Cannot modify</span>
                        ) : (
                          <Select
                            value={user.role.toString()}
                            onValueChange={(value) => handleRoleChange(user.id, parseInt(value))}
                            disabled={updatingUserId === user.id}
                          >
                            <SelectTrigger className="w-[160px]" data-testid={`role-select-${user.id}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {Object.entries(ROLES).map(([roleId, roleInfo]) => (
                                <SelectItem key={roleId} value={roleId}>
                                  {roleInfo.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default UserManagement;
