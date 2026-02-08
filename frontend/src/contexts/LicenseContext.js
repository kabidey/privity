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

// Feature to module mapping for license checks
const FEATURE_MODULE_MAP = {
  // Private Equity features
  bookings: 'private_equity',
  inventory: 'private_equity',
  vendors: 'private_equity',
  purchases: 'private_equity',
  stocks: 'private_equity',
  referral_partners: 'private_equity',
  business_partners: 'private_equity',
  contract_notes: 'private_equity',
  
  // Fixed Income features
  fi_instruments: 'fixed_income',
  fi_orders: 'fixed_income',
  fi_reports: 'fixed_income',
  fi_primary_market: 'fixed_income',
  
  // Core features (check both modules)
  clients: 'core',
  reports: 'core',
  analytics: 'core',
  bi_reports: 'core',
  whatsapp: 'core',
  email: 'core',
  ocr: 'core',
  documents: 'core',
  user_management: 'core',
  role_management: 'core',
  audit_logs: 'core',
  database_backup: 'core',
  company_master: 'core',
  finance: 'core'
};

export const LicenseProvider = ({ children }) => {
  const [licenseStatus, setLicenseStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showLicenseModal, setShowLicenseModal] = useState(false);
  const [checkedOnce, setCheckedOnce] = useState(false);
  const [isExempt, setIsExempt] = useState(false);
  
  // V2 Granular License Status
  const [v2Status, setV2Status] = useState({
    private_equity: { is_licensed: false, features: [], modules: [], usage_limits: {} },
    fixed_income: { is_licensed: false, features: [], modules: [], usage_limits: {} }
  });

  const checkLicense = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
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

      // Check if user is SMIFS employee (exempt) or license admin
      if (isSmifsEmployee(userEmail)) {
        setIsExempt(true);
        
        // Still fetch V2 license status for feature gating
        try {
          const v2Response = await api.get('/licence/check/status');
          setV2Status({
            private_equity: v2Response.data.private_equity || { is_licensed: true, features: ['*'], modules: ['*'] },
            fixed_income: v2Response.data.fixed_income || { is_licensed: true, features: ['*'], modules: ['*'] }
          });
        } catch (e) {
          // If V2 check fails, assume all features licensed for exempt users
          setV2Status({
            private_equity: { is_licensed: true, features: ['*'], modules: ['*'], usage_limits: {} },
            fixed_income: { is_licensed: true, features: ['*'], modules: ['*'], usage_limits: {} }
          });
        }
        
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

      // For non-SMIFS users, check both old and V2 license
      const [oldResponse, v2Response] = await Promise.all([
        api.get('/license/status/me').catch(() => ({ data: { is_valid: true } })),
        api.get('/licence/check/status').catch(() => ({ data: {} }))
      ]);
      
      setLicenseStatus(oldResponse.data);
      setIsExempt(oldResponse.data?.exempt || false);
      
      // Set V2 status
      setV2Status({
        private_equity: v2Response.data?.private_equity || { is_licensed: false, features: [], modules: [] },
        fixed_income: v2Response.data?.fixed_income || { is_licensed: false, features: [], modules: [] }
      });
      
      // Show modal if license is invalid and user is NOT exempt
      if (!oldResponse.data.is_valid && !oldResponse.data.exempt) {
        setShowLicenseModal(true);
      }
      
      return oldResponse.data;
    } catch (error) {
      console.error('Failed to check license:', error);
      setLicenseStatus({ is_valid: true, status: 'unknown' });
      return null;
    } finally {
      setLoading(false);
      setCheckedOnce(true);
    }
  }, []);

  useEffect(() => {
    checkLicense();
  }, [checkLicense]);

  useEffect(() => {
    if (isExempt) return;
    const interval = setInterval(checkLicense, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [checkLicense, isExempt]);

  /**
   * Check if a specific feature is licensed
   * @param {string} feature - Feature key (e.g., 'bookings', 'fi_orders')
   * @returns {object} { isLicensed: boolean, message: string }
   */
  const isFeatureLicensed = useCallback((feature) => {
    // Exempt users have access to everything
    if (isExempt) {
      return { isLicensed: true, message: 'Access granted' };
    }
    
    const module = FEATURE_MODULE_MAP[feature];
    
    if (!module) {
      // Unknown feature, allow by default
      return { isLicensed: true, message: 'Feature not tracked' };
    }
    
    if (module === 'core') {
      // Core features - check if either PE or FI license has this feature
      const peHasFeature = v2Status.private_equity.features?.includes(feature) || 
                          v2Status.private_equity.features?.includes('*');
      const fiHasFeature = v2Status.fixed_income.features?.includes(feature) || 
                          v2Status.fixed_income.features?.includes('*');
      
      if (peHasFeature || fiHasFeature) {
        return { isLicensed: true, message: 'Feature licensed' };
      }
      
      return { 
        isLicensed: false, 
        message: `Feature "${feature}" is not included in your license. Contact admin to upgrade.`
      };
    }
    
    // Module-specific features
    const moduleStatus = v2Status[module];
    
    if (!moduleStatus?.is_licensed) {
      return { 
        isLicensed: false, 
        message: `${module === 'private_equity' ? 'Private Equity' : 'Fixed Income'} module is not licensed. Contact admin.`
      };
    }
    
    const hasFeature = moduleStatus.features?.includes(feature) || 
                      moduleStatus.features?.includes('*');
    
    if (hasFeature) {
      return { isLicensed: true, message: 'Feature licensed' };
    }
    
    return { 
      isLicensed: false, 
      message: `Feature "${feature}" is not included in your license. Contact admin to upgrade.`
    };
  }, [isExempt, v2Status]);

  /**
   * Check if a module is licensed
   * @param {string} module - Module key ('private_equity' or 'fixed_income')
   * @returns {object} { isLicensed: boolean, message: string, daysRemaining: number }
   */
  const isModuleLicensed = useCallback((module) => {
    if (isExempt) {
      return { isLicensed: true, message: 'Access granted', daysRemaining: 999 };
    }
    
    const moduleStatus = v2Status[module];
    
    if (!moduleStatus) {
      return { isLicensed: false, message: 'Unknown module', daysRemaining: 0 };
    }
    
    return {
      isLicensed: moduleStatus.is_licensed,
      message: moduleStatus.is_licensed 
        ? 'Module licensed' 
        : `${module === 'private_equity' ? 'Private Equity' : 'Fixed Income'} module is not licensed. Contact admin.`,
      daysRemaining: moduleStatus.days_remaining || 0,
      status: moduleStatus.status || 'no_license'
    };
  }, [isExempt, v2Status]);

  /**
   * Check usage limit
   * @param {string} limitType - Limit type (e.g., 'max_users', 'max_clients')
   * @param {string} module - Module to check
   * @param {number} currentCount - Current count
   * @returns {object} { allowed: boolean, limit: number, remaining: number, message: string }
   */
  const checkUsageLimit = useCallback((limitType, module, currentCount = 0) => {
    if (isExempt) {
      return { allowed: true, limit: -1, remaining: -1, message: 'Unlimited' };
    }
    
    const moduleStatus = v2Status[module];
    const limit = moduleStatus?.usage_limits?.[limitType] || 0;
    
    if (limit === -1) {
      return { allowed: true, limit: -1, remaining: -1, message: 'Unlimited' };
    }
    
    const remaining = limit - currentCount;
    
    return {
      allowed: remaining > 0,
      limit,
      remaining: Math.max(0, remaining),
      message: remaining > 0 ? `${remaining} remaining` : `Limit of ${limit} reached. Contact admin to upgrade.`
    };
  }, [isExempt, v2Status]);

  const handleLicenseActivated = (data) => {
    setLicenseStatus({
      is_valid: true,
      status: 'active',
      expires_at: data.expires_at,
      days_remaining: data.days_remaining
    });
    setShowLicenseModal(false);
    // Refresh V2 status
    checkLicense();
  };

  const openLicenseModal = () => setShowLicenseModal(true);
  const closeLicenseModal = () => {
    if (licenseStatus?.is_valid || isExempt) {
      setShowLicenseModal(false);
    }
  };

  const value = {
    // Legacy properties
    licenseStatus,
    loading,
    isValid: licenseStatus?.is_valid ?? true,
    isExempt,
    isExpiringSoon: licenseStatus?.status === 'expiring_soon',
    daysRemaining: licenseStatus?.days_remaining ?? 0,
    checkLicense,
    openLicenseModal,
    closeLicenseModal,
    
    // V2 Granular License properties
    v2Status,
    isFeatureLicensed,
    isModuleLicensed,
    checkUsageLimit,
    
    // Convenience getters
    peStatus: v2Status.private_equity,
    fiStatus: v2Status.fixed_income,
    isPELicensed: v2Status.private_equity?.is_licensed || isExempt,
    isFILicensed: v2Status.fixed_income?.is_licensed || isExempt
  };

  return (
    <LicenseContext.Provider value={value}>
      {children}
      
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
