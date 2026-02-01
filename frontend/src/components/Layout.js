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
import { getFullVersion } from '../version';
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
  User,
  ArrowDownToLine,
  Send,
  BookOpen,
  Phone
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

  // Poll PE online status and send heartbeat (reduced frequency)
  useEffect(() => {
    const checkPeStatus = async () => {
      try {
        // Send heartbeat (will only track if current user is PE level)
        await api.post('/users/heartbeat');
        
        // Get PE status only if WebSocket is not connected
        if (!isConnected) {
          const response = await api.get('/users/pe-status');
          setPeStatus(response.data);
        }
      } catch (error) {
        console.error('Failed to check PE status:', error);
      }
    };

    // Check immediately on mount
    checkPeStatus();
    
    // Heartbeat every 60 seconds (was 30s) - status updates come via WebSocket when connected
    const interval = setInterval(checkPeStatus, 60000);
    
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
  const isViewer = user.role === 6;
  
  // Role-specific dashboards as first item
  if (user.role === 1 || user.role === 2) {
    menuItems.push({ icon: Shield, label: 'PE Dashboard', path: '/pe-dashboard' });
  } else if (user.role === 7) {
    menuItems.push({ icon: Banknote, label: 'Finance Dashboard', path: '/finance-dashboard' });
  } else if (user.role === 6) {
    menuItems.push({ icon: LayoutDashboard, label: 'Overview Dashboard', path: '/pe-dashboard' });
  } else if (user.role === 3 || user.role === 4 || user.role === 5 || user.role === 10 || user.role === 11) {
    menuItems.push({ icon: User, label: 'My Dashboard', path: '/my-dashboard' });
  }
  
  // Research - at the top for all employees (not BP)
  if (user.role !== 8) {
    menuItems.push({ icon: BookOpen, label: 'Research', path: '/research' });
  }
  
  // General Dashboard for all
  menuItems.push({ icon: LayoutDashboard, label: 'Dashboard', path: '/' });
  menuItems.push({ icon: Users, label: 'Clients', path: '/clients' });

  // Vendors - PE Level and Viewer (view-only for Viewer)
  if (user.role === 1 || user.role === 2 || isViewer) {
    menuItems.push({ icon: Building2, label: 'Vendors', path: '/vendors' });
  }
  
  menuItems.push({ icon: Package, label: 'Stocks', path: '/stocks' });
  
  // Purchases - PE Desk, PE Manager, and Viewer (view-only)
  if (user.role === 1 || user.role === 2 || isViewer) {
    menuItems.push({ icon: ShoppingCart, label: 'Purchases', path: '/purchases' });
    menuItems.push({ icon: ArrowDownToLine, label: 'DP Receivables', path: '/dp-receivables' });
    menuItems.push({ icon: Send, label: 'DP Transfer', path: '/dp-transfer-client' });
  }
  
  menuItems.push(
    { icon: Boxes, label: 'Inventory', path: '/inventory' },
    { icon: FileText, label: 'Bookings', path: '/bookings' },
    { icon: BarChart3, label: 'Reports', path: '/reports' }
  );

  // Add finance for Finance role, PE level, or Viewer
  if (user.role === 7 || user.role === 1 || user.role === 2 || isViewer) {
    menuItems.push({ icon: Banknote, label: 'Finance', path: '/finance' });
  }

  // Add user management for PE level or Viewer
  if (user.role === 1 || user.role === 2 || isViewer) {
    menuItems.push({ icon: UserCog, label: 'Users', path: '/users' });
  }

  // Add Referral Partners for PE level, Manager, Employees, or Viewer
  if (user.role === 1 || user.role === 2 || user.role === 4 || user.role === 5 || isViewer) {
    menuItems.push({ icon: UserPlus, label: 'Referral Partners', path: '/referral-partners' });
  }

  // Add Analytics and Email Templates for PE Level and Viewer (view-only for viewer)
  if (user.role === 1 || user.role === 2 || isViewer) {
    menuItems.push({ icon: PieChart, label: 'Analytics', path: '/analytics' });
    menuItems.push({ icon: FileText, label: 'Contract Notes', path: '/contract-notes' });
    menuItems.push({ icon: Mail, label: 'Email Templates', path: '/email-templates' });
    menuItems.push({ icon: MailCheck, label: 'Email Logs', path: '/email-logs' });
    menuItems.push({ icon: Shield, label: 'Audit Trail', path: '/audit-trail' });
    menuItems.push({ icon: Server, label: 'Email Server', path: '/email-server' });
  }

  // Company Master & Bulk Upload & Database Backup & Security Dashboard - PE Desk only (role 1)
  if (user.role === 1) {
    menuItems.push({ icon: Building2, label: 'Company Master', path: '/company-master' });
    menuItems.push({ icon: Database, label: 'Database Backup', path: '/database-backup' });
    menuItems.push({ icon: Upload, label: 'Bulk Upload', path: '/bulk-upload' });
    menuItems.push({ icon: Shield, label: 'Security Dashboard', path: '/security' });
  }

  // Business Partners - PE Level, Partners Desk, and Viewer
  if (user.role === 1 || user.role === 2 || user.role === 9 || isViewer) {
    menuItems.push({ icon: Building2, label: 'Business Partners', path: '/business-partners' });
  }

  // Revenue Dashboards - visible based on hierarchy (Viewer sees all)
  // RP Revenue: Employee, Manager, Zonal Manager, PE Level, Regional Manager, Business Head, and Viewer
  if ((user.role >= 1 && user.role <= 5) || user.role === 10 || user.role === 11 || isViewer) {
    menuItems.push({ icon: TrendingUp, label: 'RP Revenue', path: '/rp-revenue' });
  }
  
  // Employee Revenue: Manager, Zonal Manager, PE Level, Regional Manager, Business Head, and Viewer
  if ((user.role >= 1 && user.role <= 4) || user.role === 10 || user.role === 11 || isViewer) {
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
      <aside className="hidden lg:flex lg:flex-col w-72 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-r border-gray-200/50 dark:border-gray-800/50 fixed h-screen z-40 overflow-hidden">
        {/* Header with Logo and Status Indicator */}
        <div className="p-6 border-b border-gray-200/50 dark:border-gray-800/50 flex-shrink-0">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold bg-gradient-to-r from-emerald-600 to-teal-500 bg-clip-text text-transparent" data-testid="app-title">
              PRIVITY
            </h1>
            <button
              onClick={openChangelog}
              className="text-xs font-medium text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full hover:bg-emerald-100 hover:text-emerald-600 dark:hover:bg-emerald-900/30 dark:hover:text-emerald-400 transition-colors cursor-pointer"
              data-testid="app-version"
              title="View changelog"
            >
              {getFullVersion()}
            </button>
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
        
        {/* Navigation - Scrollable area */}
        <nav className="flex-1 p-3 overflow-y-auto min-h-0" data-testid="sidebar-nav">
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
        
        {/* Footer - Compact fixed at bottom */}
        <div className="p-3 border-t border-gray-200/50 dark:border-gray-800/50 flex-shrink-0 bg-white/80 dark:bg-gray-900/80">
          {/* Contact Info */}
          <div className="flex items-center justify-center gap-4 mb-2 text-xs text-gray-500 dark:text-gray-400">
            <a href="tel:9088963000" className="flex items-center gap-1 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
              <Phone className="h-3 w-3" />
              <span>9088963000</span>
            </a>
            <a href="mailto:pe@smifs.com" className="flex items-center gap-1 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
              <Mail className="h-3 w-3" />
              <span>pe@smifs.com</span>
            </a>
          </div>
          
          {/* Kill Switch - PE Desk Only - Inline */}
          <KillSwitch userRole={user.role} />
          
          {/* Compact user info row */}
          <div className="flex items-center justify-between mt-2 px-2 py-2 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ${
                isPELevel ? 'bg-gradient-to-br from-emerald-500 to-teal-500' : 'bg-gradient-to-br from-blue-500 to-indigo-500'
              }`}>
                {user.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'U'}
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate max-w-[100px]">{user.name?.split(' ')[0]}</span>
                <span className="text-[10px] text-gray-500">{user.role_name || 'User'}</span>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <NotificationBell />
              <button onClick={toggleTheme} className="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700" title="Toggle theme">
                {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
              </button>
              <button onClick={() => navigate('/change-password')} className="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700" title="Change Password">
                <Key className="h-4 w-4" />
              </button>
              <button onClick={handleLogout} className="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600" title="Logout">
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
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
            <button
              onClick={openChangelog}
              className="text-[10px] font-medium text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-full hover:bg-emerald-100 hover:text-emerald-600 dark:hover:bg-emerald-900/30 dark:hover:text-emerald-400 transition-colors"
              data-testid="app-version-mobile"
            >
              {getFullVersion()}
            </button>
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
              onClick={() => {
                console.log('Menu button clicked!');
                setSidebarOpen(true);
              }}
              data-testid="mobile-menu-button"
              className="p-2.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors relative z-[100]"
            >
              <Menu className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            </button>
          </div>
        </div>
      </div>

      {/* iOS-style Mobile Sidebar Overlay */}
      <div 
        className={`lg:hidden fixed inset-0 z-[10000] transition-opacity duration-300 ${
          sidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      >
        {/* Backdrop */}
        <div 
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
        
        {/* Slide-over Panel - Full Height Flex Layout */}
        <aside
          className={`absolute right-0 top-0 bottom-0 w-80 max-w-[85vw] bg-white dark:bg-gray-900 shadow-2xl transform transition-transform duration-300 ease-out flex flex-col ${
            sidebarOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Panel Header */}
          <div className="h-12 flex items-center justify-between px-3 border-b border-gray-200 dark:border-gray-800 safe-area-inset-top flex-shrink-0">
            <span className="font-semibold text-gray-900 dark:text-white">Menu</span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              data-testid="close-menu-button"
            >
              <X className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            </button>
          </div>
          
          {/* Compact User Card */}
          <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-800">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold text-sm ${
                isPELevel 
                  ? 'bg-gradient-to-br from-emerald-400 to-teal-500' 
                  : 'bg-gradient-to-br from-blue-400 to-indigo-500'
              }`}>
                {user.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-gray-900 dark:text-white truncate">{user.name}</div>
                <div className="text-xs text-emerald-600 dark:text-emerald-400">{user.role_name}</div>
              </div>
              <div 
                className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${isPeAvailable ? 'bg-green-500' : 'bg-red-500'}`}
                style={{
                  boxShadow: isPeAvailable 
                    ? '0 0 6px #22c55e' 
                    : '0 0 6px #ef4444'
                }}
              />
            </div>
          </div>
          
          {/* Navigation - Dynamic Grid of Buttons */}
          <nav className="flex-1 p-2 overflow-y-auto" data-testid="mobile-sidebar-nav">
            <div className="grid grid-cols-4 gap-1.5">
              {menuItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path ||
                  (item.path !== '/' && location.pathname.startsWith(item.path));
                return (
                  <button
                    key={item.path}
                    data-testid={`mobile-nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                    onClick={() => {
                      navigate(item.path);
                      setSidebarOpen(false);
                    }}
                    className={`flex flex-col items-center justify-center p-2 rounded-xl transition-all duration-200 active:scale-95 aspect-square ${
                      isActive
                        ? 'bg-gradient-to-br from-emerald-500 to-teal-500 text-white shadow-md shadow-emerald-500/30'
                        : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 hover:text-emerald-600 dark:hover:text-emerald-400'
                    }`}
                  >
                    <Icon className={`h-5 w-5 ${isActive ? 'text-white' : ''}`} strokeWidth={1.5} />
                    <span className={`text-[8px] font-medium text-center leading-tight mt-1 line-clamp-2 ${isActive ? 'text-white' : ''}`}>
                      {item.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </nav>
          
          {/* Compact Footer Actions */}
          <div className="p-2 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 safe-area-inset-bottom flex-shrink-0 relative z-[60]">
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setShowChangePassword(true);
                  setSidebarOpen(false);
                }}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors text-xs font-medium"
              >
                <Key className="h-4 w-4" strokeWidth={1.5} />
                <span>Password</span>
              </button>
              <button
                onClick={handleLogout}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors text-xs font-medium"
                data-testid="mobile-logout-button"
              >
                <LogOut className="h-4 w-4" strokeWidth={1.5} />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </aside>
      </div>

      {/* Main Content */}
      <main className="lg:ml-72 min-h-screen">
        <div className="pt-14 lg:pt-0 pb-24 lg:pb-6 px-4 lg:px-6">
          <div className="max-w-7xl mx-auto py-4 lg:py-6">
            {children}
          </div>
        </div>
      </main>

      {/* Changelog Modal */}
      <ChangelogModal 
        isOpen={showChangelog} 
        onClose={() => setShowChangelog(false)} 
      />
    </div>
  );
};

export default Layout;
