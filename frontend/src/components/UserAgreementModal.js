import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
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
        className="sm:max-w-2xl max-h-[90vh] p-0 overflow-hidden"
        onInteractOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
        hideCloseButton
        data-testid="user-agreement-modal"
      >
        {/* Header */}
        <div className="relative bg-gradient-to-br from-slate-800 to-slate-900 p-6 text-white">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-white/20 rounded-xl">
              <Shield className="h-6 w-6" />
            </div>
            <div>
              <DialogTitle className="text-xl font-bold text-white">
                User Agreement
              </DialogTitle>
              <DialogDescription className="text-slate-300">
                Please read and accept the terms to continue
              </DialogDescription>
            </div>
          </div>
        </div>

        {/* Agreement Content */}
        <div className="p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500" />
            </div>
          ) : (
            <>
              <ScrollArea 
                className="h-[350px] border rounded-lg p-4 bg-slate-50 dark:bg-slate-900"
                onScrollCapture={handleScroll}
              >
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700 dark:text-gray-300">
                    {agreementText}
                  </pre>
                </div>
              </ScrollArea>

              {/* Confirmation Checkbox */}
              <div className="flex items-start gap-3 mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                <Checkbox 
                  id="agreement-checkbox"
                  checked={hasRead}
                  onCheckedChange={setHasRead}
                  className="mt-0.5"
                  data-testid="agreement-checkbox"
                />
                <label 
                  htmlFor="agreement-checkbox" 
                  className="text-sm text-amber-800 dark:text-amber-200 cursor-pointer"
                >
                  I have read, understood, and agree to be bound by the terms and conditions stated above.
                </label>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex items-center justify-between w-full">
            <Button
              variant="outline"
              onClick={handleDecline}
              className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
              data-testid="decline-agreement-btn"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Decline & Logout
            </Button>
            <Button
              onClick={handleAccept}
              disabled={!hasRead || accepting}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              data-testid="accept-agreement-btn"
            >
              {accepting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Processing...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4 mr-2" />
                  I Agree
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default UserAgreementModal;
