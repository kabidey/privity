import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { useNotifications } from '../context/NotificationContext';
import NotificationBell from './NotificationBell';
import ThemeSelector from './ThemeSelector';
import KillSwitch from './KillSwitch';
import SystemFrozenOverlay from './SystemFrozenOverlay';
import ChangelogModal, { useChangelogModal } from './ChangelogModal';
import ContentProtection from './ContentProtection';
import { toast } from 'sonner';
import api from '../utils/api';
import { getFullVersion } from '../version';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { usePermissions } from '../hooks/usePermissions';
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
  ChevronRight,
  Upload,
  TrendingUp,
  Shield,
  ShieldCheck,
  User,
  ArrowDownToLine,
  Send,
  BookOpen,
  Phone,
  DollarSign,
  HardDrive,
  HelpCircle,
  MessageCircle,
  Bell
} from 'lucide-react';

const Layout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [peStatus, setPeStatus] = useState({ pe_online: false, message: 'Checking...', online_users: [] });
  
  // Use centralized role utility hook
  const { 
    user, 
    role,
    roleName,
    isPEDesk, 
    isPELevel, 
    isPEManager,
    isFinance, 
    isViewer, 
    isPartnersDesk, 
    isBusinessPartner, 
    isEmployee 
  } = useCurrentUser();
  
  // Use permissions hook for dynamic menu access
  const { hasPermission, canAccess } = usePermissions();
  
  const { theme } = useTheme();
  
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

  // Build menu items based on user role AND permissions
  // Uses both legacy role checks and new dynamic permissions
  const menuItems = [];
  
  // Role-specific dashboards as first item
  if (isPELevel || hasPermission('dashboard.pe_view')) {
    menuItems.push({ icon: Shield, label: 'PE Dashboard', path: '/pe-dashboard' });
  } else if (isFinance || hasPermission('finance.view')) {
    menuItems.push({ icon: Banknote, label: 'Finance Dashboard', path: '/finance-dashboard' });
  } else if (isViewer) {
    menuItems.push({ icon: LayoutDashboard, label: 'Overview Dashboard', path: '/pe-dashboard' });
  } else if (isEmployee || isPartnersDesk) {
    menuItems.push({ icon: User, label: 'My Dashboard', path: '/my-dashboard' });
  }
  
  // Research - at the top for all (not BP)
  if (!isBusinessPartner && (hasPermission('research.view') || !isBusinessPartner)) {
    menuItems.push({ icon: BookOpen, label: 'Research', path: '/research' });
  }
  
  // General Dashboard for all
  menuItems.push({ icon: LayoutDashboard, label: 'Dashboard', path: '/' });
  
  // Clients - based on permission
  if (hasPermission('clients.view') || isPELevel || isViewer || isEmployee || isPartnersDesk || isBusinessPartner) {
    menuItems.push({ icon: Users, label: 'Clients', path: '/clients' });
  }

  // Vendors - based on permission
  if (hasPermission('vendors.view') || isPELevel || isViewer) {
    menuItems.push({ icon: Building2, label: 'Vendors', path: '/vendors' });
  }
  
  // Stocks - based on permission
  if (hasPermission('stocks.view') || !isBusinessPartner) {
    menuItems.push({ icon: Package, label: 'Stocks', path: '/stocks' });
  }
  
  // Purchases - based on permission
  if (hasPermission('purchases.view') || isPELevel || isViewer) {
    menuItems.push({ icon: ShoppingCart, label: 'Purchases', path: '/purchases' });
  }
  
  // DP Operations - based on permissions
  if (hasPermission('dp.view_receivables') || isPELevel || isViewer) {
    menuItems.push({ icon: ArrowDownToLine, label: 'DP Receivables', path: '/dp-receivables' });
  }
  if (hasPermission('dp.transfer') || isPELevel || isViewer) {
    menuItems.push({ icon: Send, label: 'DP Transfer', path: '/dp-transfer-client' });
  }
  
  // Inventory - based on permission
  if (hasPermission('inventory.view') || !isBusinessPartner) {
    menuItems.push({ icon: Boxes, label: 'Inventory', path: '/inventory' });
  }
  
  // Bookings - based on permission
  if (hasPermission('bookings.view') || !isBusinessPartner) {
    menuItems.push({ icon: FileText, label: 'Bookings', path: '/bookings' });
  }
  
  // Reports - based on permission
  if (hasPermission('reports.view') || !isBusinessPartner) {
    menuItems.push({ icon: BarChart3, label: 'Reports', path: '/reports' });
  }

  // Finance - based on permission
  if (hasPermission('finance.view') || isFinance || isPELevel || isViewer) {
    menuItems.push({ icon: Banknote, label: 'Finance', path: '/finance' });
  }

  // User Management - based on permission
  if (hasPermission('users.view') || isPELevel || isViewer) {
    menuItems.push({ icon: UserCog, label: 'Users', path: '/users' });
  }

  // Role Management - based on permission (PE Desk only by default)
  if (hasPermission('roles.view') || isPEDesk) {
    menuItems.push({ icon: Shield, label: 'Role Management', path: '/roles' });
  }

  // Referral Partners - based on permission
  if (hasPermission('referral_partners.view') || isPELevel || isEmployee || isPartnersDesk || isViewer) {
    menuItems.push({ icon: UserPlus, label: 'Referral Partners', path: '/referral-partners' });
  }

  // Business Partners - based on permission
  if (hasPermission('business_partners.view') || isPELevel || isPartnersDesk || isViewer) {
    menuItems.push({ icon: Building2, label: 'Business Partners', path: '/business-partners' });
  }

  // Analytics - based on permission
  if (hasPermission('analytics.view') || isPELevel || isViewer) {
    menuItems.push({ icon: PieChart, label: 'Analytics', path: '/analytics' });
  }
  
  // Confirmation Notes - based on permission
  if (hasPermission('contract_notes.view') || isPELevel || isViewer) {
    menuItems.push({ icon: FileText, label: 'Confirmation Notes', path: '/contract-notes' });
  }
  
  // Email Templates - based on permission
  if (hasPermission('email.view_templates') || isPELevel || isViewer) {
    menuItems.push({ icon: Mail, label: 'Email Templates', path: '/email-templates' });
  }
  
  // Email Logs - based on permission
  if (hasPermission('email.view_logs') || isPELevel || isViewer) {
    menuItems.push({ icon: MailCheck, label: 'Email Logs', path: '/email-logs' });
  }
  
  // Audit Trail - based on permission
  if (hasPermission('security.view_audit') || isPELevel || isViewer) {
    menuItems.push({ icon: Shield, label: 'Audit Trail', path: '/audit-trail' });
  }
  
  // Email Server - based on permission
  if (hasPermission('email.server_config') || isPELevel || isViewer) {
    menuItems.push({ icon: Server, label: 'Email Server', path: '/email-server' });
  }

  // Company Master - based on permission
  if (hasPermission('company.view') || isPEDesk) {
    menuItems.push({ icon: Building2, label: 'Company Master', path: '/company-master' });
  }
  
  // Database Backup - based on permission
  if (hasPermission('database.view_backups') || isPEDesk) {
    menuItems.push({ icon: Database, label: 'Database Backup', path: '/database-backup' });
  }
  
  // Bulk Upload - based on permission
  if (hasPermission('bulk_upload.clients') || isPEDesk) {
    menuItems.push({ icon: Upload, label: 'Bulk Upload', path: '/bulk-upload' });
  }
  
  // Security Dashboard - based on permission
  if (hasPermission('security.view_dashboard') || isPEDesk) {
    menuItems.push({ icon: ShieldCheck, label: 'Security Dashboard', path: '/security' });
  }
  
  // BI Reports - based on any BI report permission
  const biPermissions = ['reports.bi_bookings', 'reports.bi_clients', 'reports.bi_revenue', 
                        'reports.bi_inventory', 'reports.bi_payments', 'reports.bi_pnl'];
  if (isPELevel || biPermissions.some(p => hasPermission(p))) {
    menuItems.push({ icon: BarChart3, label: 'BI Reports', path: '/bi-reports' });
  }
  
  // WhatsApp Notifications - based on any WhatsApp permission
  const waPermissions = ['notifications.whatsapp_view', 'notifications.whatsapp_connect', 
                        'notifications.whatsapp_templates', 'notifications.whatsapp_send'];
  if (isPEDesk || waPermissions.some(p => hasPermission(p))) {
    menuItems.push({ icon: MessageCircle, label: 'WhatsApp', path: '/whatsapp' });
  }
  
  // Notification Dashboard - visible to all users
  menuItems.push({ icon: Bell, label: 'Notifications', path: '/notifications' });
  
  // File Migration - PE Desk only
  if (isPEDesk) {
    menuItems.push({ icon: HardDrive, label: 'File Migration', path: '/file-migration' });
  }

  // PE Desk HIT Report - PE Level only
  if (isPELevel) {
    menuItems.push({ icon: DollarSign, label: 'PE HIT Report', path: '/pe-desk-hit' });
  }

  // Revenue Dashboards - visible to PE Level, Employee, Partners Desk, and Viewer
  if (isPELevel || isEmployee || isPartnersDesk || isViewer) {
    menuItems.push({ icon: TrendingUp, label: 'RP Revenue', path: '/rp-revenue' });
  }
  
  // Team Revenue - PE Level and Viewer
  if (isPELevel || isViewer) {
    menuItems.push({ icon: Users, label: 'Team Revenue', path: '/employee-revenue' });
  }

  // BP Dashboard - for Business Partners only
  if (isBusinessPartner) {
    // BP has their own limited menu
    menuItems.length = 0; // Clear existing menu
    menuItems.push({ icon: LayoutDashboard, label: 'My Dashboard', path: '/bp-dashboard' });
  }

  // Account Security - visible to all users (2FA settings, change password)
  menuItems.push({ icon: ShieldCheck, label: 'Account Security', path: '/account-security' });

  // Help & Tutorial - visible to all users
  menuItems.push({ icon: HelpCircle, label: 'Help & Tutorial', path: '/help' });
  
  // PE availability status (from server - are any PE users online?)
  const isPeAvailable = peStatus.pe_online;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* System Frozen Overlay - shows for all users except PE Desk when kill switch is active */}
      <SystemFrozenOverlay userRole={role} />
      
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
        
        {/* Navigation - Grid of Buttons (same as mobile) */}
        <nav className="flex-1 p-3 overflow-y-auto min-h-0" data-testid="sidebar-nav">
          <div className="grid grid-cols-3 gap-2">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || 
                (item.path !== '/' && location.pathname.startsWith(item.path));
              return (
                <button
                  key={item.path}
                  data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                  onClick={() => navigate(item.path)}
                  className={`flex flex-col items-center justify-center p-3 rounded-xl transition-all duration-200 active:scale-95 aspect-square ${
                    isActive
                      ? 'bg-gradient-to-br from-emerald-500 to-teal-500 text-white shadow-lg shadow-emerald-500/30'
                      : 'bg-gray-50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 hover:text-emerald-600 dark:hover:text-emerald-400'
                  }`}
                >
                  <Icon className={`h-6 w-6 ${isActive ? 'text-white' : ''}`} strokeWidth={1.5} />
                  <span className={`text-[10px] font-medium text-center leading-tight mt-1.5 line-clamp-2 ${isActive ? 'text-white' : ''}`}>
                    {item.label}
                  </span>
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
          <KillSwitch userRole={role} />
          
          {/* Compact user info row */}
          <div className="flex items-center justify-between mt-2 px-2 py-2 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ${
                isPELevel ? 'bg-gradient-to-br from-emerald-500 to-teal-500' : 'bg-gradient-to-br from-blue-500 to-indigo-500'
              }`}>
                {user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'U'}
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate max-w-[100px]">{user?.name?.split(' ')[0]}</span>
                <span className="text-[10px] text-gray-500">{roleName || 'User'}</span>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <NotificationBell />
              <ThemeSelector />
              <button onClick={handleLogout} className="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600" title="Logout">
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>

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
            <ThemeSelector />
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
                {user?.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-gray-900 dark:text-white truncate">{user?.name}</div>
                <div className="text-xs text-emerald-600 dark:text-emerald-400">{roleName}</div>
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
