import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { ThemeProvider } from './context/ThemeContext';
import { NotificationProvider } from './context/NotificationContext';
import { LicenseProvider } from './contexts/LicenseContext';
import { DemoProvider } from './contexts/DemoContext';
import { checkVersionAndClearCache } from './version';
import FloatingNotifications from './components/FloatingNotifications';
import NotificationDialog from './components/NotificationDialog';
import NotificationPermissionBanner from './components/NotificationPermissionBanner';
import ProxyBanner from './components/ProxyBanner';
import FeatureShowcase from './components/demo/FeatureShowcase';
import DemoTour from './components/demo/DemoTour';
import DemoModeBar from './components/demo/DemoModeBar';
import FloatingProgressWidget from './components/demo/FloatingProgressWidget';
import Login from './pages/Login';
import ForgotPassword from './pages/ForgotPassword';
import BookingConfirm from './pages/BookingConfirm';
import Dashboard from './pages/Dashboard';
import Clients from './pages/Clients';
import ClientPortfolio from './pages/ClientPortfolio';
import Vendors from './pages/Vendors';
import Stocks from './pages/Stocks';
import Purchases from './pages/Purchases';
import Inventory from './pages/Inventory';
import Bookings from './pages/Bookings';
import Reports from './pages/Reports';
import UserManagement from './pages/UserManagement';
import Analytics from './pages/Analytics';
import EmailTemplates from './pages/EmailTemplates';
import EmailLogs from './pages/EmailLogs';

// Check version and clear cache on app load
checkVersionAndClearCache();
import EmailServerConfig from './pages/EmailServerConfig';
import DPReceivables from './pages/DPReceivables';
import DPTransferClient from './pages/DPTransferClient';
import DatabaseBackup from './pages/DatabaseBackup';
import Finance from './pages/Finance';
import ReferralPartners from './pages/ReferralPartners';
import CompanyMaster from './pages/CompanyMaster';
import ContractNotes from './pages/ContractNotes';
import BulkUpload from './pages/BulkUpload';
import BusinessPartners from './pages/BusinessPartners';
import BPDashboard from './pages/BPDashboard';
import RPRevenueDashboard from './pages/RPRevenueDashboard';
import EmployeeRevenueDashboard from './pages/EmployeeRevenueDashboard';
import AuditTrail from './pages/AuditTrail';
import PEDashboard from './pages/PEDashboard';
import FinanceDashboard from './pages/FinanceDashboard';
import MyDashboard from './pages/MyDashboard';
import Research from './pages/Research';
import ClientDashboard from './pages/ClientDashboard';
import SecurityDashboard from './pages/SecurityDashboard';
import PEDeskHitReport from './pages/PEDeskHitReport';
import FileMigration from './pages/FileMigration';
import HelpTutorial from './pages/HelpTutorial';
import AccountSecurity from './pages/AccountSecurity';
import TwoFactorSetupPage from './pages/TwoFactorSetupPage';
import RoleManagement from './pages/RoleManagement';
import BIReports from './pages/BIReports';
import WhatsAppNotifications from './pages/WhatsAppNotifications';
import NotificationDashboard from './pages/NotificationDashboard';
import FISecurityMaster from './pages/FISecurityMaster';
import FIOrders from './pages/FIOrders';
import FIReports from './pages/FIReports';
import FIPrimaryMarket from './pages/FIPrimaryMarket';
import LicenseManagement from './pages/LicenseManagement';
import Layout from './components/Layout';
import GroupChat from './components/GroupChat';
import InstallPWA from './components/InstallPWA';
import UserAgreementModal from './components/UserAgreementModal';
import { useState, useEffect } from 'react';
import api from './utils/api';
import './App.css';

const PrivateRoute = ({ children }) => {
  const token = localStorage.getItem('token');
  return token ? children : <Navigate to="/login" />;
};

// Proxy session wrapper - checks and displays proxy banner
const ProxyWrapper = ({ children }) => {
  const [proxySession, setProxySession] = useState(null);

  useEffect(() => {
    // Check proxy status on mount
    const checkProxyStatus = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;
        
        const response = await api.get('/auth/proxy-status');
        if (response.data.is_proxy) {
          setProxySession(response.data);
          // Store in localStorage for other components
          localStorage.setItem('proxy_session', JSON.stringify(response.data));
        } else {
          localStorage.removeItem('proxy_session');
        }
      } catch (error) {
        console.error('Error checking proxy status:', error);
      }
    };

    checkProxyStatus();
  }, []);

  const handleEndProxy = (data) => {
    setProxySession(null);
  };

  return (
    <>
      <ProxyBanner proxySession={proxySession} onEndProxy={handleEndProxy} />
      <div style={{ marginTop: proxySession?.is_proxy ? '40px' : '0' }}>
        {children}
      </div>
    </>
  );
};

// Component to check and show user agreement
const AgreementChecker = ({ children }) => {
  const [showAgreement, setShowAgreement] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // Small delay to ensure localStorage is ready
    const timer = setTimeout(() => {
      try {
        const userStr = localStorage.getItem('user');
        const isDemoMode = localStorage.getItem('demo_token') === 'true';
        
        // Skip agreement check for demo users
        if (isDemoMode) {
          setChecking(false);
          return;
        }
        
        if (userStr) {
          const user = JSON.parse(userStr);
          // Show agreement if user exists and hasn't accepted it yet
          if (user && user.id && user.agreement_accepted !== true) {
            setShowAgreement(true);
          }
        }
      } catch (error) {
        console.error('Error checking agreement:', error);
      }
      setChecking(false);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  const handleAccept = () => {
    setShowAgreement(false);
  };

  const handleDecline = () => {
    // Will redirect to login via the modal
  };

  // Don't block rendering - show content immediately
  // Agreement modal will overlay if needed
  return (
    <>
      {showAgreement && (
        <UserAgreementModal 
          isOpen={showAgreement} 
          onAccept={handleAccept} 
          onDecline={handleDecline} 
        />
      )}
      {children}
    </>
  );
};

function App() {
  // Listen for service worker updates and auto-refresh
  useEffect(() => {
    // Handle SW_UPDATED message from service worker
    const handleSWUpdate = (event) => {
      if (event.data && event.data.type === 'SW_UPDATED') {
        console.log(`[App] Service Worker updated to version ${event.data.version}`);
        // Force reload to get latest assets
        window.location.reload();
      }
    };

    // Listen for messages from service worker
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.addEventListener('message', handleSWUpdate);
    }

    // Also check for waiting service worker on page load
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready.then((registration) => {
        if (registration.waiting) {
          // New service worker is waiting, tell it to take over
          registration.waiting.postMessage({ type: 'SKIP_WAITING' });
        }
        
        // Listen for new service worker installing
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // New content available, refresh to get it
                console.log('[App] New content available, reloading...');
                window.location.reload();
              }
            });
          }
        });
      });
    }

    return () => {
      if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        navigator.serviceWorker.removeEventListener('message', handleSWUpdate);
      }
    };
  }, []);

  return (
    <DemoProvider>
      <ThemeProvider>
        <div className="App">
          <BrowserRouter>
            {/* Demo Mode Components */}
            <DemoModeBar />
            <FeatureShowcase />
            <DemoTour />
            <FloatingProgressWidget />
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              {/* Public route for client booking confirmation */}
              <Route path="/booking-confirm/:bookingId/:token/:action" element={<BookingConfirm />} />
              <Route
                path="/*"
                element={
                  <PrivateRoute>
                    <NotificationProvider>
                      <LicenseProvider>
                        <ProxyWrapper>
                          <AgreementChecker>
                            <Layout>
                              <Routes>
                          <Route path="/" element={<Dashboard />} />
                          <Route path="/clients" element={<Clients />} />
                          <Route path="/clients/:clientId/portfolio" element={<ClientPortfolio />} />
                          <Route path="/vendors" element={<Vendors />} />
                          <Route path="/stocks" element={<Stocks />} />
                          <Route path="/purchases" element={<Purchases />} />
                          <Route path="/inventory" element={<Inventory />} />
                          <Route path="/bookings" element={<Bookings />} />
                          <Route path="/reports" element={<Reports />} />
                          <Route path="/users" element={<UserManagement />} />
                          <Route path="/roles" element={<RoleManagement />} />
                          <Route path="/analytics" element={<Analytics />} />
                          <Route path="/email-templates" element={<EmailTemplates />} />
                          <Route path="/email-logs" element={<EmailLogs />} />
                          <Route path="/email-server" element={<EmailServerConfig />} />
                          <Route path="/dp-transfer" element={<DPTransferClient />} />
                          <Route path="/dp-receivables" element={<DPReceivables />} />
                          <Route path="/dp-transfer-client" element={<DPTransferClient />} />
                          <Route path="/database-backup" element={<DatabaseBackup />} />
                          <Route path="/finance" element={<Finance />} />
                          <Route path="/referral-partners" element={<ReferralPartners />} />
                          <Route path="/company-master" element={<CompanyMaster />} />
                          <Route path="/contract-notes" element={<ContractNotes />} />
                          <Route path="/bulk-upload" element={<BulkUpload />} />
                        <Route path="/business-partners" element={<BusinessPartners />} />
                        <Route path="/bp-dashboard" element={<BPDashboard />} />
                        <Route path="/rp-revenue" element={<RPRevenueDashboard />} />
                        <Route path="/employee-revenue" element={<EmployeeRevenueDashboard />} />
                        <Route path="/audit-trail" element={<AuditTrail />} />
                        <Route path="/pe-dashboard" element={<PEDashboard />} />
                          <Route path="/finance-dashboard" element={<FinanceDashboard />} />
                          <Route path="/my-dashboard" element={<MyDashboard />} />
                          <Route path="/client-dashboard" element={<ClientDashboard />} />
                          <Route path="/research" element={<Research />} />
                          <Route path="/security" element={<SecurityDashboard />} />
                          <Route path="/pe-desk-hit" element={<PEDeskHitReport />} />
                          <Route path="/file-migration" element={<FileMigration />} />
                          <Route path="/help" element={<HelpTutorial />} />
                          <Route path="/account-security" element={<AccountSecurity />} />
                          <Route path="/2fa-setup" element={<TwoFactorSetupPage />} />
                          <Route path="/bi-reports" element={<BIReports />} />
                          <Route path="/whatsapp" element={<WhatsAppNotifications />} />
                          <Route path="/notifications" element={<NotificationDashboard />} />
                          {/* Fixed Income Module */}
                          <Route path="/fi-instruments" element={<FISecurityMaster />} />
                          <Route path="/fi-orders" element={<FIOrders />} />
                          <Route path="/fi-reports" element={<FIReports />} />
                          <Route path="/fi-primary-market" element={<FIPrimaryMarket />} />
                        </Routes>
                        </Layout>
                        {/* Notification Permission Banner */}
                        <NotificationPermissionBanner />
                        {/* Floating Notifications at bottom right */}
                        <FloatingNotifications />
                        {/* Dialog for important notifications */}
                        <NotificationDialog />
                        {/* Team Group Chat */}
                        <GroupChat />
                        {/* PWA Install Prompt */}
                        <InstallPWA />
                      </AgreementChecker>
                      </ProxyWrapper>
                    </LicenseProvider>
                  </NotificationProvider>
                </PrivateRoute>
              }
            />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </div>
    </ThemeProvider>
    </DemoProvider>
  );
}

export default App;
