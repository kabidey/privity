import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import api from '../utils/api';
import { FileText, Shield, LogOut, Check } from 'lucide-react';

const UserAgreementModal = ({ isOpen, onAccept, onDecline }) => {
  const [agreementText, setAgreementText] = useState('');
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [hasRead, setHasRead] = useState(false);
  const [scrolledToBottom, setScrolledToBottom] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchAgreement();
    }
  }, [isOpen]);

  const fetchAgreement = async () => {
    try {
      setLoading(true);
      const response = await api.get('/company-master/user-agreement');
      setAgreementText(response.data.user_agreement_text || 'No agreement text configured.');
    } catch (error) {
      console.error('Failed to fetch agreement:', error);
      setAgreementText('Unable to load agreement text. Please contact support.');
    } finally {
      setLoading(false);
    }
  };

  const handleScroll = (e) => {
    const target = e.target;
    const isAtBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 50;
    if (isAtBottom && !scrolledToBottom) {
      setScrolledToBottom(true);
    }
  };

  const handleAccept = async () => {
    if (!hasRead) {
      toast.error('Please confirm that you have read and understood the agreement');
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
      
      toast.success('Agreement accepted successfully');
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

  return (
    <Dialog open={isOpen} onOpenChange={() => {}}>
      <DialogContent 
        className="sm:max-w-xl w-[95vw] max-h-[85vh] h-auto p-0 overflow-hidden"
        onInteractOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
        hideCloseButton
        data-testid="user-agreement-modal"
      >
        {/* Header - Fixed at top */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 p-3 sm:p-4 text-white">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/20 rounded-xl flex-shrink-0">
              <Shield className="h-4 w-4 sm:h-5 sm:w-5" />
            </div>
            <div>
              <DialogTitle className="text-base sm:text-lg font-bold text-white">
                User Agreement
              </DialogTitle>
              <DialogDescription className="text-slate-300 text-xs">
                Please read and accept the terms to continue
              </DialogDescription>
            </div>
          </div>
        </div>

        {/* Agreement Content - Scrollable */}
        <div className="p-3 sm:p-4 overflow-y-auto" style={{ maxHeight: 'calc(85vh - 180px)' }}>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500" />
            </div>
          ) : (
            <>
              <ScrollArea 
                className="h-[200px] sm:h-[220px] border rounded-lg p-3 bg-slate-50 dark:bg-slate-900"
                onScrollCapture={handleScroll}
              >
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-xs text-gray-700 dark:text-gray-300">
                    {agreementText}
                  </pre>
                </div>
              </ScrollArea>

              {/* Confirmation Checkbox */}
              <div className="flex items-start gap-2 mt-3 p-2.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                <Checkbox 
                  id="agreement-checkbox"
                  checked={hasRead}
                  onCheckedChange={setHasRead}
                  className="mt-0.5 flex-shrink-0"
                  data-testid="agreement-checkbox"
                />
                <label 
                  htmlFor="agreement-checkbox" 
                  className="text-xs text-amber-800 dark:text-amber-200 cursor-pointer leading-tight"
                >
                  I have read, understood, and agree to be bound by the terms and conditions stated above.
                </label>
              </div>
            </>
          )}
        </div>

        {/* Footer - Always visible at bottom */}
        <div className="p-3 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
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
              disabled={!hasRead || accepting}
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
                  I Agree
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
