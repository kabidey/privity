import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { LayoutDashboard, Users, Building2, Package, ShoppingCart, Boxes, FileText, BarChart3, LogOut, Menu, X } from 'lucide-react';

const Layout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
    { icon: Users, label: 'Clients', path: '/clients' },
    { icon: Building2, label: 'Vendors', path: '/vendors' },
    { icon: Package, label: 'Stocks', path: '/stocks' },
    { icon: ShoppingCart, label: 'Purchases', path: '/purchases' },
    { icon: Boxes, label: 'Inventory', path: '/inventory' },
    { icon: FileText, label: 'Bookings', path: '/bookings' },
    { icon: BarChart3, label: 'Reports', path: '/reports' },
  ];

  return (
    <div className="min-h-screen flex">
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex lg:flex-col w-64 bg-card border-r border-border fixed h-full">
        <div className="p-6 border-b border-border">
          <h1 className="text-2xl font-bold" data-testid="app-title">ShareBook</h1>
          <p className="text-xs text-muted-foreground mt-1">Share Booking System</p>
        </div>
        <nav className="flex-1 p-4" data-testid="sidebar-nav">
          <div className="space-y-1">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
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
          <div className="mb-3 px-4">
            <div className="text-sm font-medium" data-testid="user-name">{user.name}</div>
            <div className="text-xs text-muted-foreground" data-testid="user-email">{user.email}</div>
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
        <h1 className="text-xl font-bold" data-testid="app-title-mobile">ShareBook</h1>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          data-testid="mobile-menu-button"
          className="p-2 hover:bg-muted rounded-md"
        >
          {sidebarOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
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
                  const isActive = location.pathname === item.path;
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
                <div className="text-xs text-muted-foreground">{user.email}</div>
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
