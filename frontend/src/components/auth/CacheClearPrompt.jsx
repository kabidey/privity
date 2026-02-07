/**
 * CacheClearPrompt Component
 * Shows a prompt to users to clear their browser cache if they encounter issues
 * Also provides a button to automatically clear app cache
 */
import { useState, useEffect } from 'react';
import { AlertTriangle, RefreshCw, X, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const CacheClearPrompt = ({ theme = { primary: 'emerald' } }) => {
  const [showPrompt, setShowPrompt] = useState(false);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    // Check if user has seen the prompt recently (within 24 hours)
    const lastPromptTime = localStorage.getItem('cache_prompt_shown');
    const now = Date.now();
    const twentyFourHours = 24 * 60 * 60 * 1000;

    // Show prompt if:
    // 1. Never shown before, OR
    // 2. Last shown more than 24 hours ago, OR
    // 3. There's a version mismatch
    const appVersion = localStorage.getItem('app_version');
    const currentVersion = '6.4.0';

    if (!lastPromptTime || 
        (now - parseInt(lastPromptTime)) > twentyFourHours ||
        appVersion !== currentVersion) {
      // Small delay before showing
      const timer = setTimeout(() => {
        setShowPrompt(true);
        localStorage.setItem('app_version', currentVersion);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleDismiss = () => {
    localStorage.setItem('cache_prompt_shown', Date.now().toString());
    setShowPrompt(false);
  };

  const handleClearCache = async () => {
    setClearing(true);
    try {
      // 1. Clear all caches
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(
          cacheNames.map(cacheName => caches.delete(cacheName))
        );
        console.log('All caches cleared');
      }

      // 2. Unregister service workers
      if ('serviceWorker' in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(
          registrations.map(reg => reg.unregister())
        );
        console.log('Service workers unregistered');
      }

      // 3. Clear localStorage items (except essential ones)
      const essentialKeys = ['token', 'user'];
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!essentialKeys.includes(key)) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach(key => localStorage.removeItem(key));

      // 4. Clear sessionStorage
      sessionStorage.clear();

      toast.success('Cache cleared successfully! Refreshing page...');
      
      // Refresh the page after a short delay
      setTimeout(() => {
        window.location.reload(true);
      }, 1500);

    } catch (error) {
      console.error('Error clearing cache:', error);
      toast.error('Failed to clear cache. Please try manually.');
      setClearing(false);
    }
  };

  const handleHardRefresh = () => {
    // Mark prompt as shown
    localStorage.setItem('cache_prompt_shown', Date.now().toString());
    // Force hard refresh
    window.location.reload(true);
  };

  if (!showPrompt) return null;

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] max-w-md w-full px-4 animate-fade-in">
      <div className={`
        bg-gradient-to-r from-amber-900/95 to-orange-900/95 
        backdrop-blur-xl rounded-xl border border-amber-500/30
        shadow-2xl shadow-amber-500/20 p-4
      `}>
        <div className="flex items-start gap-3">
          <div className="p-2 bg-amber-500/20 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-white font-semibold text-sm mb-1">
              Having trouble logging in?
            </h3>
            <p className="text-amber-200/80 text-xs mb-3">
              If you're experiencing issues with login or registration, clearing your browser cache may help resolve the problem.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                onClick={handleClearCache}
                disabled={clearing}
                className="bg-amber-500 hover:bg-amber-600 text-white text-xs h-8"
              >
                {clearing ? (
                  <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <Trash2 className="w-3 h-3 mr-1" />
                )}
                Clear Cache
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleHardRefresh}
                className="border-amber-500/50 text-amber-200 hover:bg-amber-500/20 text-xs h-8"
              >
                <RefreshCw className="w-3 h-3 mr-1" />
                Refresh
              </Button>
            </div>
          </div>
          <button
            onClick={handleDismiss}
            className="text-amber-400/60 hover:text-amber-300 transition-colors p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default CacheClearPrompt;
