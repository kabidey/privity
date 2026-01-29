import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { ThemeProvider } from './context/ThemeContext';
import { NotificationProvider } from './context/NotificationContext';
import FloatingNotifications from './components/FloatingNotifications';
import NotificationDialog from './components/NotificationDialog';
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
import EmailServerConfig from './pages/EmailServerConfig';
import DPTransferReport from './pages/DPTransferReport';
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
import ClientDashboard from './pages/ClientDashboard';
import Layout from './components/Layout';
import SohiniAssistant from './components/SohiniAssistant';
import './App.css';

const PrivateRoute = ({ children }) => {
  const token = localStorage.getItem('token');
  return token ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <ThemeProvider>
      <div className="App">
        <BrowserRouter>
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
                        <Route path="/analytics" element={<Analytics />} />
                        <Route path="/email-templates" element={<EmailTemplates />} />
                        <Route path="/email-logs" element={<EmailLogs />} />
                        <Route path="/email-server" element={<EmailServerConfig />} />
                        <Route path="/dp-transfer" element={<DPTransferReport />} />
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
                      </Routes>
                    </Layout>
                    {/* Floating Notifications at bottom right */}
                    <FloatingNotifications />
                    {/* Dialog for important notifications */}
                    <NotificationDialog />
                    {/* Sohini AI Assistant */}
                    <SohiniAssistant />
                  </NotificationProvider>
                </PrivateRoute>
              }
            />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </div>
    </ThemeProvider>
  );
}

export default App;
