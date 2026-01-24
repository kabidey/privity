import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useTheme } from '../context/ThemeContext';
import NotificationBell from './NotificationBell';
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
  Banknote,
  Server
} from 'lucide-react';

const Layout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const { theme, toggleTheme } = useTheme();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  // Base menu items visible to all
  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
    { icon: Users, label: 'Clients', path: '/clients' },
  ];

  // PE Desk only modules (role 1): Vendors, Stocks, Purchases
  if (user.role === 1) {
    menuItems.push({ icon: Building2, label: 'Vendors', path: '/vendors' });
    menuItems.push({ icon: Package, label: 'Stocks', path: '/stocks' });
    menuItems.push({ icon: ShoppingCart, label: 'Purchases', path: '/purchases' });
  }

  // Common modules for all roles
  menuItems.push({ icon: Boxes, label: 'Inventory', path: '/inventory' });
  menuItems.push({ icon: FileText, label: 'Bookings', path: '/bookings' });
  menuItems.push({ icon: BarChart3, label: 'Reports', path: '/reports' });

  // Add user management for admin roles (1 and 2)
  if (user.role <= 2) {
    menuItems.push({ icon: UserCog, label: 'Users', path: '/users' });
  }

  // Add DP Transfer Report for PE Desk and Zonal Manager (roles 1 and 2)
  if (user.role === 1 || user.role === 2) {
    menuItems.push({ icon: Banknote, label: 'DP Transfer', path: '/dp-transfer' });
  }

  // Add Analytics and Email Templates for PE Desk only (role 1)
  if (user.role === 1) {
    menuItems.push({ icon: PieChart, label: 'Analytics', path: '/analytics' });
    menuItems.push({ icon: Mail, label: 'Email Templates', path: '/email-templates' });
    menuItems.push({ icon: Server, label: 'Email Server', path: '/email-server' });
  }

  return (
    <div className="min-h-screen flex bg-background">
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex lg:flex-col w-64 bg-card border-r border-border fixed h-full">
        <div className="p-6 border-b border-border">
          <h1 className="text-2xl font-bold" data-testid="app-title">PRIVITY</h1>
          <p className="text-xs text-muted-foreground mt-1">Private Equity System</p>
        </div>
        <nav className="flex-1 p-4 overflow-y-auto" data-testid="sidebar-nav">
          <div className="space-y-1">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || 
                (item.path !== '/' && location.pathname.startsWith(item.path));
              return (
                <button
                  key={item.path}
                  data-testid={`nav-${item.label.toLowerCase()}`}
                  onClick={() => navigate(item.path)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors duration-200 ${
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-muted text-foreground'
                  }`}
                >
                  <Icon className="h-5 w-5" strokeWidth={1.5} />
                  <span className="font-medium">{item.label}</span>
                </button>
              );
            })}
          </div>
        </nav>
        <div className="p-4 border-t border-border">
          {/* Notifications */}
          <div className="flex items-center justify-between mb-3 px-2">
            <span className="text-sm text-muted-foreground">Notifications</span>
            <NotificationBell />
          </div>
          
          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleTheme}
            className="w-full justify-start mb-3"
            data-testid="theme-toggle"
          >
            {theme === 'light' ? (
              <>
                <Moon className="mr-2 h-4 w-4" strokeWidth={1.5} />
                Dark Mode
              </>
            ) : (
              <>
                <Sun className="mr-2 h-4 w-4" strokeWidth={1.5} />
                Light Mode
              </>
            )}
          </Button>
          
          <div className="mb-3 px-4">
            <div className="text-sm font-medium" data-testid="user-name">{user.name}</div>
            <div className="text-xs text-muted-foreground" data-testid="user-role">{user.role_name}</div>
          </div>
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={handleLogout}
            data-testid="logout-button"
          >
            <LogOut className="mr-2 h-4 w-4" strokeWidth={1.5} />
            Logout
          </Button>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-card border-b border-border z-40 flex items-center justify-between px-4">
        <h1 className="text-xl font-bold" data-testid="app-title-mobile">PRIVITY</h1>
        <div className="flex items-center gap-2">
          <NotificationBell />
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            data-testid="mobile-theme-toggle"
          >
            {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
          </Button>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            data-testid="mobile-menu-button"
            className="p-2 hover:bg-muted rounded-md"
          >
            {sidebarOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Sidebar */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-30 bg-background/80 backdrop-blur-sm" onClick={() => setSidebarOpen(false)}>
          <aside
            className="fixed left-0 top-16 bottom-0 w-64 bg-card border-r border-border"
            onClick={(e) => e.stopPropagation()}
          >
            <nav className="p-4" data-testid="mobile-sidebar-nav">
              <div className="space-y-1">
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
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors duration-200 ${
                        isActive
                          ? 'bg-primary text-primary-foreground'
                          : 'hover:bg-muted text-foreground'
                      }`}
                    >
                      <Icon className="h-5 w-5" strokeWidth={1.5} />
                      <span className="font-medium">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </nav>
            <div className="p-4 border-t border-border absolute bottom-0 left-0 right-0">
              <div className="mb-3 px-4">
                <div className="text-sm font-medium">{user.name}</div>
                <div className="text-xs text-muted-foreground">{user.role_name}</div>
              </div>
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={handleLogout}
                data-testid="mobile-logout-button"
              >
                <LogOut className="mr-2 h-4 w-4" strokeWidth={1.5} />
                Logout
              </Button>
            </div>
          </aside>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 lg:ml-64 mt-16 lg:mt-0">
        <div className="min-h-screen bg-background">{children}</div>
      </main>
    </div>
  );
};

export default Layout;
