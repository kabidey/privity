import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Download, X, Smartphone } from 'lucide-react';

const InstallPWA = () => {
  const [installPrompt, setInstallPrompt] = useState(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstalled(true);
      return;
    }

    // Listen for install prompt
    const handleBeforeInstall = (e) => {
      e.preventDefault();
      setInstallPrompt(e);
      // Show banner after a short delay
      setTimeout(() => setShowBanner(true), 2000);
    };

    const handleAppInstalled = () => {
      setInstallPrompt(null);
      setIsInstalled(true);
      setShowBanner(false);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  const handleInstall = async () => {
    if (!installPrompt) return;

    installPrompt.prompt();
    const { outcome } = await installPrompt.userChoice;
    
    if (outcome === 'accepted') {
      setInstallPrompt(null);
      setShowBanner(false);
    }
  };

  const dismissBanner = () => {
    setShowBanner(false);
    // Don't show again for this session
    sessionStorage.setItem('pwa-banner-dismissed', 'true');
  };

  // Check if banner was dismissed this session
  useEffect(() => {
    if (sessionStorage.getItem('pwa-banner-dismissed')) {
      setShowBanner(false);
    }
  }, []);

  // Don't render if already installed or no prompt available
  if (isInstalled || !showBanner || !installPrompt) {
    return null;
  }

  return (
    <div 
      className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 z-[9998] animate-in slide-in-from-bottom-4 duration-300"
      data-testid="pwa-install-banner"
    >
      <div className="bg-gradient-to-r from-emerald-800 to-teal-800 text-white rounded-xl shadow-2xl p-4 border border-emerald-700">
        <div className="flex items-start gap-3">
          <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
            <Smartphone className="w-6 h-6" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-base">Install PRIVITY</h3>
            <p className="text-sm text-white/80 mt-0.5">
              Add to your home screen for quick access & offline use
            </p>
            <div className="flex gap-2 mt-3">
              <Button
                onClick={handleInstall}
                size="sm"
                className="bg-white text-emerald-800 hover:bg-white/90 font-medium"
              >
                <Download className="w-4 h-4 mr-1" />
                Install App
              </Button>
              <Button
                onClick={dismissBanner}
                size="sm"
                variant="ghost"
                className="text-white/80 hover:text-white hover:bg-white/10"
              >
                Not now
              </Button>
            </div>
          </div>
          <button
            onClick={dismissBanner}
            className="p-1 hover:bg-white/10 rounded-full transition-colors"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4 text-white/60" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default InstallPWA;
