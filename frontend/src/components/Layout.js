import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useTheme } from '../context/ThemeContext';
import { useNotifications } from '../context/NotificationContext';
import NotificationBell from './NotificationBell';
import KillSwitch from './KillSwitch';
import SystemFrozenOverlay from './SystemFrozenOverlay';
import ChangelogModal, { useChangelogModal } from './ChangelogModal';
import { toast } from 'sonner';
import api from '../utils/api';
import { getVersion } from '../version';
import { 
  LayoutDashboard, 
  Users, 
  Building2, 
  Package, 
  ShoppingCart, 
  Boxes, 
  FileText, 
  BarChart3, 
  LogOut, 
  Menu, 
  X,
  Sun,
  Moon,
  Settings,
  UserCog,
  PieChart,
  Mail,
  MailCheck,
  Banknote,
  Server,
  Database,
  Plus,
  Wallet,
  UserPlus,
  Key,
  ChevronRight,
  Upload,
  TrendingUp,
  Shield,
  User
} from 'lucide-react';

const Layout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [peStatus, setPeStatus] = useState({ pe_online: false, message: 'Checking...', online_users: [] });
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const { theme, toggleTheme } = useTheme();
  
  // Changelog modal hook
  const { showChangelog, setShowChangelog, openChangelog } = useChangelogModal();
  
  // Get notification context for WebSocket PE status updates
  const { peStatus: wsPeStatus, onPeStatusChange, isConnected } = useNotifications();

  // Subscribe to WebSocket PE status updates
  useEffect(() => {
    // Register callback to receive PE status updates via WebSocket
    onPeStatusChange((status) => {
      console.log('PE Status update received via WebSocket:', status);
      setPeStatus(status);
    });
  }, [onPeStatusChange]);

  // Update from WebSocket PE status when it changes
  useEffect(() => {
    if (wsPeStatus && wsPeStatus.message !== 'Checking...') {
      setPeStatus(wsPeStatus);
    }
  }, [wsPeStatus]);

  // Poll PE online status and send heartbeat (fallback when WebSocket is not connected)
  useEffect(() => {
    const checkPeStatus = async () => {
      try {
        // Send heartbeat (will only track if current user is PE level)
        await api.post('/users/heartbeat');
        
        // Get PE status (only if WebSocket is not connected or as initial fetch)
        if (!isConnected) {
          const response = await api.get('/users/pe-status');
          setPeStatus(response.data);
        }
      } catch (error) {
        console.error('Failed to check PE status:', error);
      }
    };

    // Check immediately
    checkPeStatus();
    
    // Then poll every 30 seconds (heartbeat) - status updates come via WebSocket when connected
    const interval = setInterval(checkPeStatus, 30000);
    
    return () => clearInterval(interval);
  }, [isConnected]);

  // Close sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  // Prevent body scroll when sidebar is open
  useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [sidebarOpen]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const handleChangePassword = async () => {
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('New passwords do not match');
      return;
    }
    if (passwordData.new_password.length < 8) {
      toast.error('New password must be at least 8 characters');
      return;
    }

    setChangingPassword(true);
    try {
      await api.post('/auth/change-password', {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      toast.success('Password changed successfully');
      setShowChangePassword(false);
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setChangingPassword(false);
    }
  };

  // Build menu items based on user role
  const menuItems = [];
  
  // Role-specific dashboards as first item
  if (user.role === 1 || user.role === 2) {
    menuItems.push({ icon: Shield, label: 'PE Dashboard', path: '/pe-dashboard' });
  } else if (user.role === 7) {
    menuItems.push({ icon: Banknote, label: 'Finance Dashboard', path: '/finance-dashboard' });
  } else if (user.role === 6) {
    menuItems.push({ icon: Wallet, label: 'My Portfolio', path: '/client-dashboard' });
  } else if (user.role === 3 || user.role === 4 || user.role === 5) {
    menuItems.push({ icon: User, label: 'My Dashboard', path: '/my-dashboard' });
  }
  
  // General Dashboard for all
  menuItems.push({ icon: LayoutDashboard, label: 'Dashboard', path: '/' });
  menuItems.push({ icon: Users, label: 'Clients', path: '/clients' });

  // Vendors - PE Level only (roles 1 & 2)
  if (user.role === 1 || user.role === 2) {
    menuItems.push({ icon: Building2, label: 'Vendors', path: '/vendors' });
  }
  
  menuItems.push({ icon: Package, label: 'Stocks', path: '/stocks' });
  
  // Purchases - PE Desk and PE Manager only (roles 1 & 2)
  if (user.role === 1 || user.role === 2) {
    menuItems.push({ icon: ShoppingCart, label: 'Purchases', path: '/purchases' });
  }
  
  menuItems.push(
    { icon: Boxes, label: 'Inventory', path: '/inventory' },
    { icon: FileText, label: 'Bookings', path: '/bookings' },
    { icon: BarChart3, label: 'Reports', path: '/reports' }
  );

  // Add finance for Finance role or PE level
  if (user.role === 7 || user.role === 1 || user.role === 2) {
    menuItems.push({ icon: Banknote, label: 'Finance', path: '/finance' });
  }

  // Add user management for PE level
  if (user.role === 1 || user.role === 2) {
    menuItems.push({ icon: UserCog, label: 'Users', path: '/users' });
  }

  // Add Referral Partners for PE level, Manager, and Employees
  if (user.role === 1 || user.role === 2 || user.role === 4 || user.role === 5) {
    menuItems.push({ icon: UserPlus, label: 'Referral Partners', path: '/referral-partners' });
  }

  // Add Analytics and Email Templates for PE Level (roles 1 and 2)
  if (user.role === 1 || user.role === 2) {
    menuItems.push({ icon: PieChart, label: 'Analytics', path: '/analytics' });
    menuItems.push({ icon: FileText, label: 'Contract Notes', path: '/contract-notes' });
    menuItems.push({ icon: Mail, label: 'Email Templates', path: '/email-templates' });
    menuItems.push({ icon: MailCheck, label: 'Email Logs', path: '/email-logs' });
    menuItems.push({ icon: Shield, label: 'Audit Trail', path: '/audit-trail' });
    menuItems.push({ icon: Server, label: 'Email Server', path: '/email-server' });
    menuItems.push({ icon: Database, label: 'DB Backup', path: '/database-backup' });
  }

  // Company Master & Bulk Upload - PE Desk only (role 1)
  if (user.role === 1) {
    menuItems.push({ icon: Building2, label: 'Company Master', path: '/company-master' });
    menuItems.push({ icon: Upload, label: 'Bulk Upload', path: '/bulk-upload' });
  }

  // Business Partners - PE Level and Partners Desk (roles 1, 2 & 9)
  if (user.role === 1 || user.role === 2 || user.role === 9) {
    menuItems.push({ icon: Building2, label: 'Business Partners', path: '/business-partners' });
  }

  // Revenue Dashboards - visible based on hierarchy
  // RP Revenue: Employee, Manager, Zonal Manager, and PE Level
  if (user.role >= 1 && user.role <= 5) {
    menuItems.push({ icon: TrendingUp, label: 'RP Revenue', path: '/rp-revenue' });
  }
  
  // Employee Revenue: Manager, Zonal Manager, and PE Level
  if (user.role >= 1 && user.role <= 4) {
    menuItems.push({ icon: Users, label: 'Team Revenue', path: '/employee-revenue' });
  }

  // BP Dashboard - for Business Partners only (role 8)
  if (user.role === 8) {
    // BP has their own limited menu
    menuItems.length = 0; // Clear existing menu
    menuItems.push({ icon: LayoutDashboard, label: 'My Dashboard', path: '/bp-dashboard' });
  }

  // Determine if current user is PE level (for styling user avatar)
  const isPELevel = user.role === 1 || user.role === 2;
  
  // PE availability status (from server - are any PE users online?)
  const isPeAvailable = peStatus.pe_online;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* System Frozen Overlay - shows for all users except PE Desk when kill switch is active */}
      <SystemFrozenOverlay userRole={user.role} />
      
      {/* iOS-style Desktop Sidebar */}
      <aside className="hidden lg:flex lg:flex-col w-72 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-r border-gray-200/50 dark:border-gray-800/50 fixed h-full z-40">
        {/* Header with Logo and Status Indicator */}
        <div className="p-6 border-b border-gray-200/50 dark:border-gray-800/50">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold bg-gradient-to-r from-emerald-600 to-teal-500 bg-clip-text text-transparent" data-testid="app-title">
              PRIVITY
            </h1>
            <span className="text-xs font-medium text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full" data-testid="app-version">
              {getVersion()}
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 font-medium">Private Equity System</p>
          
          {/* PE Availability Indicator - Shows if ANY PE Desk/Manager is online */}
          <div className="flex items-center gap-2 mt-3">
            <div className="relative">
              {/* Glow effect */}
              <div 
                className={`absolute inset-0 rounded-full blur-md ${
                  isPeAvailable 
                    ? 'bg-green-500 animate-pulse' 
                    : 'bg-red-500 animate-pulse'
                }`}
                style={{ opacity: 0.6 }}
              />
              {/* Main indicator */}
              <div 
                className={`relative w-3 h-3 rounded-full ${
                  isPeAvailable 
                    ? 'bg-green-500 shadow-lg shadow-green-500/50' 
                    : 'bg-red-500 shadow-lg shadow-red-500/50'
                }`}
                style={{
                  boxShadow: isPeAvailable 
                    ? '0 0 10px #22c55e, 0 0 20px #22c55e, 0 0 30px #22c55e' 
                    : '0 0 10px #ef4444, 0 0 20px #ef4444, 0 0 30px #ef4444'
                }}
              />
            </div>
            <div className="flex flex-col">
              <span className={`text-xs font-medium ${
                isPeAvailable 
                  ? 'text-green-600 dark:text-green-400' 
                  : 'text-red-600 dark:text-red-400'
              }`}>
                {peStatus.message || (isPeAvailable ? 'PE Support Available' : 'PE Support Offline')}
              </span>
              {isPeAvailable && peStatus.online_users?.length > 0 && (
                <span className="text-[10px] text-gray-500 dark:text-gray-400">
                  {peStatus.online_users.map(u => u.name.split(' ')[0]).join(', ')} online
                </span>
              )}
            </div>
          </div>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 p-3 overflow-y-auto" data-testid="sidebar-nav">
          <div className="space-y-0.5">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || 
                (item.path !== '/' && location.pathname.startsWith(item.path));
              return (
                <button
                  key={item.path}
                  data-testid={`nav-${item.label.toLowerCase()}`}
                  onClick={() => navigate(item.path)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200 ${
                    isActive
                      ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/25'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50 active:scale-[0.98]'
                  }`}
                >
                  <Icon className="h-5 w-5" strokeWidth={1.5} />
                  <span className="font-medium text-sm">{item.label}</span>
                </button>
              );
            })}
          </div>
        </nav>
        
        {/* Footer */}
        <div className="p-4 border-t border-gray-200/50 dark:border-gray-800/50 space-y-2">
          {/* Kill Switch - PE Desk Only */}
          <KillSwitch userRole={user.role} />
          
          {/* Notifications */}
          <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
            <span className="text-sm text-gray-600 dark:text-gray-400 font-medium">Notifications</span>
            <NotificationBell />
          </div>
          
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="w-full flex items-center justify-between px-4 py-2.5 rounded-xl bg-gray-50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            data-testid="theme-toggle"
          >
            <span className="flex items-center gap-3">
              {theme === 'light' ? (
                <Moon className="h-5 w-5" strokeWidth={1.5} />
              ) : (
                <Sun className="h-5 w-5" strokeWidth={1.5} />
              )}
              <span className="text-sm font-medium">{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
            </span>
            <ChevronRight className="h-4 w-4 text-gray-400" />
          </button>
          
          {/* User Info - Enhanced */}
          <div className="px-4 py-3 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 rounded-xl">
            <div className="flex items-center gap-3">
              {/* User Avatar */}
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-sm ${
                isPELevel 
                  ? 'bg-gradient-to-br from-emerald-500 to-teal-600' 
                  : 'bg-gradient-to-br from-blue-500 to-indigo-600'
              }`}>
                {user.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-gray-900 dark:text-white truncate" data-testid="user-name">
                  {user.name || 'User'}
                </div>
                <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium" data-testid="user-role">
                  {user.role_name || 'Unknown Role'}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user.email || ''}
                </div>
              </div>
              {/* Online indicator */}
              <div className="relative">
                <div className={`w-2.5 h-2.5 rounded-full ${isPELevel ? 'bg-green-500' : 'bg-blue-500'}`} />
                <div className={`absolute inset-0 w-2.5 h-2.5 rounded-full ${isPELevel ? 'bg-green-500' : 'bg-blue-500'} animate-ping opacity-75`} />
              </div>
            </div>
          </div>
          
          {/* Action Buttons */}
          <button
            onClick={() => setShowChangePassword(true)}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors"
            data-testid="change-password-button"
          >
            <Key className="h-5 w-5" strokeWidth={1.5} />
            <span className="text-sm font-medium">Change Password</span>
          </button>
          
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            data-testid="logout-button"
          >
            <LogOut className="h-5 w-5" strokeWidth={1.5} />
            <span className="text-sm font-medium">Logout</span>
          </button>
        </div>
      </aside>

      {/* Change Password Dialog */}
      <Dialog open={showChangePassword} onOpenChange={setShowChangePassword}>
        <DialogContent className="sm:max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle>Change Password</DialogTitle>
            <DialogDescription>
              Enter your current password and a new password to update your credentials.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="current_password">Current Password</Label>
              <Input
                id="current_password"
                type="password"
                value={passwordData.current_password}
                onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
                placeholder="Enter current password"
                className="rounded-xl"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new_password">New Password</Label>
              <Input
                id="new_password"
                type="password"
                value={passwordData.new_password}
                onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                placeholder="Min 8 characters"
                className="rounded-xl"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm_password">Confirm New Password</Label>
              <Input
                id="confirm_password"
                type="password"
                value={passwordData.confirm_password}
                onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                placeholder="Confirm new password"
                className="rounded-xl"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowChangePassword(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button onClick={handleChangePassword} disabled={changingPassword} className="rounded-xl bg-emerald-500 hover:bg-emerald-600">
              {changingPassword ? 'Changing...' : 'Change Password'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* iOS-style Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50">
        <div className="h-14 bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl border-b border-gray-200 dark:border-gray-800 shadow-sm flex items-center justify-between px-4 safe-area-inset-top">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold bg-gradient-to-r from-emerald-600 to-teal-500 bg-clip-text text-transparent" data-testid="app-title-mobile">
              PRIVITY
            </h1>
            <span className="text-[10px] font-medium text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-full" data-testid="app-version-mobile">
              {getVersion()}
            </span>
            {/* PE Availability Indicator for Mobile */}
            <div 
              className={`w-2.5 h-2.5 rounded-full ${
                isPeAvailable 
                  ? 'bg-green-500' 
                  : 'bg-red-500'
              }`}
              style={{
                boxShadow: isPeAvailable 
                  ? '0 0 6px #22c55e, 0 0 12px #22c55e' 
                  : '0 0 6px #ef4444, 0 0 12px #ef4444'
              }}
              title={peStatus.message}
            />
          </div>
          <div className="flex items-center gap-1">
            <NotificationBell />
            <button
              onClick={toggleTheme}
              className="p-2.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              data-testid="mobile-theme-toggle"
            >
              {theme === 'light' ? <Moon className="h-5 w-5 text-gray-600" /> : <Sun className="h-5 w-5 text-gray-300" />}
            </button>
            <button
              onClick={() => setSidebarOpen(true)}
              data-testid="mobile-menu-button"
              className="p-2.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Menu className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            </button>
          </div>
        </div>
      </div>

      {/* iOS-style Mobile Sidebar Overlay */}
      <div 
        className={`lg:hidden fixed inset-0 z-50 transition-opacity duration-300 ${
          sidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      >
        {/* Backdrop */}
        <div 
          className="absolute inset-0 bg-black/40 backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
        
        {/* Slide-over Panel */}
        <aside
          className={`absolute right-0 top-0 bottom-0 w-80 max-w-[85vw] bg-white dark:bg-gray-900 shadow-2xl transform transition-transform duration-300 ease-out ${
            sidebarOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Panel Header */}
          <div className="h-14 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-800 safe-area-inset-top">
            <span className="font-semibold text-gray-900 dark:text-white">Menu</span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              data-testid="close-menu-button"
            >
              <X className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            </button>
          </div>
          
          {/* User Card */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-800">
            <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/30 dark:to-teal-900/30 rounded-2xl">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-semibold text-lg ${
                isPELevel 
                  ? 'bg-gradient-to-br from-emerald-400 to-teal-500' 
                  : 'bg-gradient-to-br from-blue-400 to-indigo-500'
              }`}>
                {user.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'}
              </div>
              <div className="flex-1">
                <div className="font-semibold text-gray-900 dark:text-white">{user.name}</div>
                <div className="text-sm text-emerald-600 dark:text-emerald-400">{user.role_name}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">{user.email}</div>
              </div>
              {/* PE Availability indicator */}
              <div 
                className={`w-3 h-3 rounded-full ${isPeAvailable ? 'bg-green-500' : 'bg-red-500'}`}
                style={{
                  boxShadow: isPeAvailable 
                    ? '0 0 8px #22c55e, 0 0 16px #22c55e' 
                    : '0 0 8px #ef4444, 0 0 16px #ef4444'
                }}
                title={peStatus.message}
              />
            </div>
            {/* PE Status Message */}
            <div className={`mt-2 text-xs text-center ${isPeAvailable ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {peStatus.message}
            </div>
          </div>
          
          {/* Navigation */}
          <nav className="flex-1 p-3 overflow-y-auto max-h-[calc(100vh-220px)]" data-testid="mobile-sidebar-nav">
            <div className="space-y-0.5">
              {menuItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path ||
                  (item.path !== '/' && location.pathname.startsWith(item.path));
                return (
                  <button
                    key={item.path}
                    data-testid={`mobile-nav-${item.label.toLowerCase()}`}
                    onClick={() => {
                      navigate(item.path);
                      setSidebarOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 active:scale-[0.98] ${
                      isActive
                        ? 'bg-emerald-500 text-white'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}
                  >
                    <span className="flex items-center gap-3">
                      <Icon className="h-5 w-5" strokeWidth={1.5} />
                      <span className="font-medium">{item.label}</span>
                    </span>
                    <ChevronRight className={`h-4 w-4 ${isActive ? 'text-white/70' : 'text-gray-400'}`} />
                  </button>
                );
              })}
            </div>
          </nav>
          
          {/* Footer Actions */}
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 safe-area-inset-bottom">
            <div className="space-y-2">
              <button
                onClick={() => {
                  setShowChangePassword(true);
                  setSidebarOpen(false);
                }}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                <Key className="h-5 w-5" strokeWidth={1.5} />
                <span className="font-medium">Change Password</span>
              </button>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                data-testid="mobile-logout-button"
              >
                <LogOut className="h-5 w-5" strokeWidth={1.5} />
                <span className="font-medium">Logout</span>
              </button>
            </div>
          </div>
        </aside>
      </div>

      {/* iOS-style Floating Action Button */}
      <div className="lg:hidden fixed bottom-20 right-4 z-40 safe-area-inset-bottom">
        <button
          onClick={() => navigate('/bookings?openForm=true')}
          className="flex items-center gap-2 px-5 py-3.5 bg-emerald-500 text-white rounded-full shadow-lg shadow-emerald-500/30 hover:bg-emerald-600 active:scale-95 transition-all duration-200"
          data-testid="fab-bookings"
        >
          <Plus className="h-5 w-5" strokeWidth={2} />
          <span className="font-semibold">New Booking</span>
        </button>
      </div>

      {/* Main Content */}
      <main className="lg:ml-72 min-h-screen">
        <div className="pt-14 lg:pt-0 pb-24 lg:pb-6 px-4 lg:px-6">
          <div className="max-w-7xl mx-auto py-4 lg:py-6">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Layout;
