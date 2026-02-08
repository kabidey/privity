import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import api from '../utils/api';
import { Shield, LogOut, Check, Briefcase, TrendingUp, Building2 } from 'lucide-react';

const UserAgreementModal = ({ isOpen, onAccept, onDecline }) => {
  const [agreements, setAgreements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [acceptedAgreements, setAcceptedAgreements] = useState({});

  useEffect(() => {
    if (isOpen) {
      fetchAgreements();
    }
  }, [isOpen]);

  const fetchAgreements = async () => {
    try {
      setLoading(true);
      const response = await api.get('/company-master/agreements');
      const agreementsList = response.data.agreements || [];
      setAgreements(agreementsList);
      
      // Initialize accepted state for each agreement
      const initialAccepted = {};
      agreementsList.forEach(a => {
        initialAccepted[a.company_id] = false;
      });
      setAcceptedAgreements(initialAccepted);
    } catch (error) {
      console.error('Failed to fetch agreements:', error);
      // Fallback to single agreement
      try {
        const fallback = await api.get('/company-master/user-agreement');
        setAgreements([{
          company_id: 'default',
          company_name: 'SMIFS',
          company_type: 'default',
          agreement_text: fallback.data.user_agreement_text || 'No agreement text configured.',
          logo_url: null
        }]);
        setAcceptedAgreements({ default: false });
      } catch (e) {
        setAgreements([{
          company_id: 'error',
          company_name: 'Error',
          company_type: 'error',
          agreement_text: 'Unable to load agreement text. Please contact support.',
          logo_url: null
        }]);
      }
    } finally {
      setLoading(false);
    }
  };

  const allAccepted = Object.values(acceptedAgreements).every(v => v === true) && agreements.length > 0;

  const handleAcceptChange = (companyId, checked) => {
    setAcceptedAgreements(prev => ({
      ...prev,
      [companyId]: checked
    }));
  };

  const handleAccept = async () => {
    if (!allAccepted) {
      toast.error('Please accept all company agreements to continue');
      return;
    }

    try {
      setAccepting(true);
      await api.post('/company-master/accept-agreement');
      
      // Update local storage user data
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      user.agreement_accepted = true;
      user.agreement_accepted_at = new Date().toISOString();
      localStorage.setItem('user', JSON.stringify(user));
      
      toast.success('Agreements accepted successfully');
      onAccept();
    } catch (error) {
      toast.error('Failed to accept agreement. Please try again.');
    } finally {
      setAccepting(false);
    }
  };

  const handleDecline = async () => {
    try {
      await api.post('/company-master/decline-agreement');
      toast.info('You have declined the agreement. Logging out...');
      
      // Clear auth and redirect to login
      setTimeout(() => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }, 1500);
      
      onDecline();
    } catch (error) {
      toast.error('Failed to process. Please try again.');
    }
  };

  const getCompanyIcon = (type) => {
    switch (type) {
      case 'private_equity':
        return <Briefcase className="h-4 w-4" />;
      case 'fixed_income':
        return <TrendingUp className="h-4 w-4" />;
      default:
        return <Building2 className="h-4 w-4" />;
    }
  };

  const getCompanyColor = (type) => {
    switch (type) {
      case 'private_equity':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'fixed_income':
        return 'bg-teal-100 text-teal-800 border-teal-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const isSingleAgreement = agreements.length === 1;

  return (
    <Dialog open={isOpen} onOpenChange={() => {}}>
      <DialogContent 
        className={`${isSingleAgreement ? 'sm:max-w-xl' : 'sm:max-w-4xl'} w-[95vw] max-h-[85vh] p-0 overflow-hidden flex flex-col`}
        onInteractOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
        hideCloseButton
        data-testid="user-agreement-modal"
      >
        {/* Header - Fixed at top */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 p-3 sm:p-4 text-white flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/20 rounded-xl flex-shrink-0">
              <Shield className="h-4 w-4 sm:h-5 sm:w-5" />
            </div>
            <div>
              <DialogTitle className="text-base sm:text-lg font-bold text-white">
                User Agreement{agreements.length > 1 ? 's' : ''}
              </DialogTitle>
              <DialogDescription className="text-slate-300 text-xs">
                {agreements.length > 1 
                  ? 'Please read and accept all company agreements to continue'
                  : 'Please read and accept the terms to continue'
                }
              </DialogDescription>
            </div>
          </div>
        </div>

        {/* Agreement Content - Scrollable, takes remaining space */}
        <div className="p-3 sm:p-4 overflow-y-auto flex-1 min-h-0">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500" />
            </div>
          ) : (
            <div className={`${isSingleAgreement ? '' : 'grid grid-cols-1 md:grid-cols-2 gap-4'}`}>
              {agreements.map((agreement) => (
                <div 
                  key={agreement.company_id} 
                  className={`border rounded-lg overflow-hidden ${acceptedAgreements[agreement.company_id] ? 'border-emerald-300 bg-emerald-50/30' : 'border-gray-200'}`}
                >
                  {/* Company Header */}
                  <div className={`p-3 border-b flex items-center gap-2 ${getCompanyColor(agreement.company_type)}`}>
                    {getCompanyIcon(agreement.company_type)}
                    <span className="font-semibold text-sm">{agreement.company_name}</span>
                    <Badge variant="outline" className="text-xs ml-auto">
                      {agreement.company_type === 'private_equity' ? 'PE Module' : 
                       agreement.company_type === 'fixed_income' ? 'FI Module' : 'General'}
                    </Badge>
                  </div>
                  
                  {/* Agreement Text */}
                  <ScrollArea className={`${isSingleAgreement ? 'h-[180px]' : 'h-[150px]'} p-3 bg-white`}>
                    <div className="prose prose-sm max-w-none">
                      <pre className="whitespace-pre-wrap font-sans text-xs text-gray-700">
                        {agreement.agreement_text}
                      </pre>
                    </div>
                  </ScrollArea>
                  
                  {/* Acceptance Checkbox */}
                  <div className={`p-2.5 border-t flex items-start gap-2 ${acceptedAgreements[agreement.company_id] ? 'bg-emerald-50' : 'bg-amber-50'}`}>
                    <Checkbox 
                      id={`agreement-${agreement.company_id}`}
                      checked={acceptedAgreements[agreement.company_id]}
                      onCheckedChange={(checked) => handleAcceptChange(agreement.company_id, checked)}
                      className="mt-0.5 flex-shrink-0"
                      data-testid={`agreement-checkbox-${agreement.company_type}`}
                    />
                    <label 
                      htmlFor={`agreement-${agreement.company_id}`}
                      className={`text-xs cursor-pointer leading-tight ${acceptedAgreements[agreement.company_id] ? 'text-emerald-800' : 'text-amber-800'}`}
                    >
                      I accept the terms of <strong>{agreement.company_name}</strong>
                    </label>
                    {acceptedAgreements[agreement.company_id] && (
                      <Check className="h-4 w-4 text-emerald-600 ml-auto flex-shrink-0" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer - Always visible at bottom */}
        <div className="p-3 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 flex-shrink-0">
          {/* Progress indicator for multiple agreements */}
          {agreements.length > 1 && (
            <div className="mb-2 flex items-center gap-2 text-xs text-gray-600">
              <span>Accepted:</span>
              <div className="flex gap-1">
                {agreements.map((a) => (
                  <div 
                    key={a.company_id}
                    className={`w-3 h-3 rounded-full ${acceptedAgreements[a.company_id] ? 'bg-emerald-500' : 'bg-gray-300'}`}
                    title={a.company_name}
                  />
                ))}
              </div>
              <span className="ml-auto">
                {Object.values(acceptedAgreements).filter(v => v).length} of {agreements.length}
              </span>
            </div>
          )}
          
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
            <Button
              variant="outline"
              onClick={handleDecline}
              className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700 order-2 sm:order-1 h-9 sm:h-10 text-sm"
              data-testid="decline-agreement-btn"
            >
              <LogOut className="h-3.5 w-3.5 mr-1.5" />
              Decline & Logout
            </Button>
            <Button
              onClick={handleAccept}
              disabled={!allAccepted || accepting}
              className="bg-emerald-600 hover:bg-emerald-700 text-white order-1 sm:order-2 h-10 sm:h-10 text-sm font-semibold"
              data-testid="accept-agreement-btn"
            >
              {accepting ? (
                <>
                  <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-white mr-1.5" />
                  Processing...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4 mr-1.5" />
                  I Agree to All
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default UserAgreementModal;
