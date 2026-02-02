import { useState } from 'react';
import { AlertTriangle, User, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * ProxyBanner - Shows when PE Desk is viewing app as another user
 * Displays at the top of the screen with option to return to original account
 */
const ProxyBanner = ({ proxySession, onEndProxy }) => {
  const [loading, setLoading] = useState(false);

  if (!proxySession?.is_proxy) return null;

  const handleEndProxy = async () => {
    setLoading(true);
    try {
      const response = await api.post('/auth/proxy-logout');
      
      // Store new token and user
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      
      // Clear proxy session and original user
      localStorage.removeItem('proxy_session');
      localStorage.removeItem('original_user');
      
      toast.success('Returned to your account');
      
      // Callback to parent
      if (onEndProxy) {
        onEndProxy(response.data);
      }
      
      // Force full page reload to clear all cached state
      window.location.replace('/');
    } catch (error) {
      console.error('Proxy logout error:', error);
      toast.error('Failed to end proxy session. Try refreshing the page.');
      
      // Fallback: Clear local storage and redirect anyway
      localStorage.removeItem('proxy_session');
      localStorage.removeItem('original_user');
      window.location.replace('/login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="fixed top-0 left-0 right-0 z-[9999] bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-lg"
      data-testid="proxy-banner"
    >
      <div className="max-w-screen-2xl mx-auto px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white/20 rounded-full px-3 py-1">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-semibold">PROXY MODE</span>
          </div>
          <div className="flex items-center gap-2">
            <User className="h-4 w-4" />
            <span className="text-sm">
              Viewing as <strong>{proxySession.viewing_as?.name}</strong>
              <span className="opacity-75 ml-1">
                ({proxySession.viewing_as?.role_name})
              </span>
            </span>
          </div>
        </div>
        
        <Button
          onClick={handleEndProxy}
          disabled={loading}
          size="sm"
          className="bg-white/20 hover:bg-white/30 text-white border-0"
          data-testid="end-proxy-btn"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          {loading ? 'Returning...' : `Return to ${proxySession.original_user?.name || 'PE Desk'}`}
        </Button>
      </div>
    </div>
  );
};

export default ProxyBanner;
