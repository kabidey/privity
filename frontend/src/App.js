import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { ThemeProvider } from './context/ThemeContext';
import { NotificationProvider } from './context/NotificationContext';
import Login from './pages/Login';
import ForgotPassword from './pages/ForgotPassword';
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
import Layout from './components/Layout';
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
                      </Routes>
                    </Layout>
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
