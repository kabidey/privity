import { useLicense } from '../contexts/LicenseContext';
import { Lock, AlertTriangle, Phone } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';

/**
 * LicenseGate - Wrapper component that checks if a feature is licensed
 * Shows "Contact Admin" overlay if feature is not licensed
 * 
 * @param {string} feature - Feature key to check (e.g., 'bookings', 'fi_orders')
 * @param {string} module - Optional module to check ('private_equity' or 'fixed_income')
 * @param {boolean} hideIfUnlicensed - If true, completely hides content instead of showing overlay
 * @param {React.ReactNode} children - Content to render if licensed
 * @param {string} fallbackMessage - Custom message to show if unlicensed
 */
const LicenseGate = ({ 
  feature, 
  module, 
  hideIfUnlicensed = false, 
  children, 
  fallbackMessage,
  className = ''
}) => {
  const { isFeatureLicensed, isModuleLicensed, isExempt } = useLicense();
  
  // Check license status
  let licenseCheck = { isLicensed: true, message: '' };
  
  if (module) {
    licenseCheck = isModuleLicensed(module);
  } else if (feature) {
    licenseCheck = isFeatureLicensed(feature);
  }
  
  // If licensed or exempt, render children normally
  if (licenseCheck.isLicensed || isExempt) {
    return children;
  }
  
  // If hideIfUnlicensed, don't render anything
  if (hideIfUnlicensed) {
    return null;
  }
  
  // Show "Contact Admin" overlay
  return (
    <div className={`relative ${className}`}>
      {/* Blurred/disabled content */}
      <div className="opacity-30 pointer-events-none select-none filter blur-[2px]">
        {children}
      </div>
      
      {/* Overlay */}
      <div className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm rounded-lg">
        <Card className="max-w-md mx-4 shadow-lg border-amber-200">
          <CardContent className="p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 flex items-center justify-center">
              <Lock className="w-8 h-8 text-amber-600" />
            </div>
            
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Feature Not Licensed
            </h3>
            
            <p className="text-gray-600 mb-4">
              {fallbackMessage || licenseCheck.message}
            </p>
            
            <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
              <Phone className="w-4 h-4" />
              <span>Contact your administrator to unlock this feature</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

/**
 * LicenseMenuItem - For use in navigation menus
 * Shows disabled state with lock icon if not licensed
 */
export const LicenseMenuItem = ({ 
  feature, 
  module, 
  children, 
  onClick,
  className = '',
  ...props 
}) => {
  const { isFeatureLicensed, isModuleLicensed, isExempt } = useLicense();
  
  let licenseCheck = { isLicensed: true, message: '' };
  
  if (module) {
    licenseCheck = isModuleLicensed(module);
  } else if (feature) {
    licenseCheck = isFeatureLicensed(feature);
  }
  
  const isLicensed = licenseCheck.isLicensed || isExempt;
  
  if (!isLicensed) {
    return (
      <div 
        className={`${className} opacity-50 cursor-not-allowed relative group`}
        title={licenseCheck.message}
        {...props}
      >
        {children}
        <Lock className="w-3 h-3 absolute top-1 right-1 text-amber-500" />
        
        {/* Tooltip on hover */}
        <div className="absolute left-full ml-2 top-0 hidden group-hover:block z-50">
          <div className="bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
            {licenseCheck.message}
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className={className} onClick={onClick} {...props}>
      {children}
    </div>
  );
};

/**
 * LicenseButton - Button that's disabled if feature is not licensed
 */
export const LicenseButton = ({ 
  feature, 
  module, 
  children, 
  onClick,
  disabled,
  ...props 
}) => {
  const { isFeatureLicensed, isModuleLicensed, isExempt } = useLicense();
  
  let licenseCheck = { isLicensed: true, message: '' };
  
  if (module) {
    licenseCheck = isModuleLicensed(module);
  } else if (feature) {
    licenseCheck = isFeatureLicensed(feature);
  }
  
  const isLicensed = licenseCheck.isLicensed || isExempt;
  
  return (
    <Button
      onClick={isLicensed ? onClick : undefined}
      disabled={disabled || !isLicensed}
      title={!isLicensed ? licenseCheck.message : undefined}
      {...props}
    >
      {children}
      {!isLicensed && <Lock className="w-3 h-3 ml-2" />}
    </Button>
  );
};

/**
 * useLicenseCheck - Hook for programmatic license checks
 */
export const useLicenseCheck = (feature, module) => {
  const { isFeatureLicensed, isModuleLicensed, isExempt } = useLicense();
  
  if (isExempt) {
    return { isLicensed: true, message: 'Access granted' };
  }
  
  if (module) {
    return isModuleLicensed(module);
  }
  
  if (feature) {
    return isFeatureLicensed(feature);
  }
  
  return { isLicensed: true, message: 'No check specified' };
};

export default LicenseGate;
