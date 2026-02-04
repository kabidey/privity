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

// Check if user is SMIFS employee (exempt from license)
const isSmifsEmployee = (email) => {
  return email && email.toLowerCase().endsWith('@smifs.com');
};

export const LicenseProvider = ({ children }) => {
  const [licenseStatus, setLicenseStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showLicenseModal, setShowLicenseModal] = useState(false);
  const [checkedOnce, setCheckedOnce] = useState(false);
  const [isExempt, setIsExempt] = useState(false);

  const checkLicense = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
        // Not logged in, skip license check
        setLicenseStatus({ is_valid: true, status: 'not_logged_in' });
        setLoading(false);
        setCheckedOnce(true);
        return null;
      }

      // Get current user info to check if they're exempt
      let userEmail = '';
      try {
        const userResponse = await api.get('/auth/me');
        userEmail = userResponse.data?.email || '';
      } catch (e) {
        console.error('Failed to get user info:', e);
      }

      // Check if user is SMIFS employee (exempt)
      if (isSmifsEmployee(userEmail)) {
        setIsExempt(true);
        setLicenseStatus({
          is_valid: true,
          status: 'exempt',
          message: 'SMIFS employees are exempt from license requirements.',
          exempt: true
        });
        setLoading(false);
        setCheckedOnce(true);
        return { is_valid: true, exempt: true };
      }

      // For non-SMIFS users (Business Partners), check license
      const response = await api.get('/license/status/me');
      setLicenseStatus(response.data);
      setIsExempt(response.data?.exempt || false);
      
      // Show modal if license is invalid and user is NOT exempt
      if (!response.data.is_valid && !response.data.exempt) {
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

  // Recheck license periodically (every 5 minutes) only for non-exempt users
  useEffect(() => {
    if (isExempt) return; // Don't poll for exempt users
    
    const interval = setInterval(checkLicense, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [checkLicense, isExempt]);

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
    // Only allow closing if license is valid or user is exempt
    if (licenseStatus?.is_valid || isExempt) {
      setShowLicenseModal(false);
    }
  };

  const value = {
    licenseStatus,
    loading,
    isValid: licenseStatus?.is_valid ?? true,
    isExempt,
    isExpiringSoon: licenseStatus?.status === 'expiring_soon',
    daysRemaining: licenseStatus?.days_remaining ?? 0,
    checkLicense,
    openLicenseModal,
    closeLicenseModal
  };

  return (
    <LicenseContext.Provider value={value}>
      {children}
      
      {/* License Modal - shown only for non-exempt users when license is invalid */}
      {checkedOnce && !isExempt && (
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
