import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../utils/api';
import LicenseModal from '../components/LicenseModal';

const LicenseContext = createContext(null);

export const useLicense = () => {
  const context = useContext(LicenseContext);
  if (!context) {
    throw new Error('useLicense must be used within a LicenseProvider');
  }
  return context;
};

export const LicenseProvider = ({ children }) => {
  const [licenseStatus, setLicenseStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showLicenseModal, setShowLicenseModal] = useState(false);
  const [checkedOnce, setCheckedOnce] = useState(false);

  const checkLicense = useCallback(async () => {
    try {
      const response = await api.get('/license/status');
      setLicenseStatus(response.data);
      
      // Show modal if license is invalid and user is logged in
      const token = localStorage.getItem('token');
      if (token && !response.data.is_valid) {
        setShowLicenseModal(true);
      }
      
      return response.data;
    } catch (error) {
      console.error('Failed to check license:', error);
      // Don't block on network errors
      setLicenseStatus({ is_valid: true, status: 'unknown' });
      return null;
    } finally {
      setLoading(false);
      setCheckedOnce(true);
    }
  }, []);

  // Check license on mount
  useEffect(() => {
    checkLicense();
  }, [checkLicense]);

  // Recheck license periodically (every 5 minutes)
  useEffect(() => {
    const interval = setInterval(checkLicense, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [checkLicense]);

  const handleLicenseActivated = (data) => {
    setLicenseStatus({
      is_valid: true,
      status: 'active',
      expires_at: data.expires_at,
      days_remaining: data.days_remaining
    });
    setShowLicenseModal(false);
  };

  const openLicenseModal = () => setShowLicenseModal(true);
  const closeLicenseModal = () => {
    // Only allow closing if license is valid
    if (licenseStatus?.is_valid) {
      setShowLicenseModal(false);
    }
  };

  const value = {
    licenseStatus,
    loading,
    isValid: licenseStatus?.is_valid ?? true,
    isExpiringSoon: licenseStatus?.status === 'expiring_soon',
    daysRemaining: licenseStatus?.days_remaining ?? 0,
    checkLicense,
    openLicenseModal,
    closeLicenseModal
  };

  return (
    <LicenseContext.Provider value={value}>
      {children}
      
      {/* License Modal - shown when license is invalid */}
      {checkedOnce && (
        <LicenseModal
          open={showLicenseModal}
          onClose={closeLicenseModal}
          onLicenseActivated={handleLicenseActivated}
        />
      )}
    </LicenseContext.Provider>
  );
};

export default LicenseProvider;
