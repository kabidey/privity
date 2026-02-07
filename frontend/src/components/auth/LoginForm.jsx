/**
 * LoginForm Component
 * Handles employee login with email/password and SSO
 */
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Loader2, Building2, AlertCircle, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const LoginForm = ({
  formData,
  onChange,
  onSubmit,
  loading,
  error,
  theme,
  captchaRequired,
  captchaQuestion,
  captchaAnswer,
  onCaptchaChange,
  ssoConfig,
  ssoLoading,
  onSsoLogin
}) => {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label className="text-white font-medium">Email</Label>
        <Input
          type="email"
          name="email"
          placeholder="you@company.com"
          value={formData.email}
          onChange={onChange}
          required
          className="bg-white/10 border-white/40 text-white placeholder:text-gray-400"
          data-testid="email"
        />
      </div>
      
      <div className="space-y-2">
        <Label className="text-white font-medium">Password</Label>
        <Input
          type="password"
          name="password"
          placeholder="••••••••"
          value={formData.password}
          onChange={onChange}
          required
          className="bg-white/10 border-white/40 text-white placeholder:text-gray-400"
          data-testid="password"
        />
        <div className="flex justify-end">
          <Link 
            to="/forgot-password" 
            className={`text-${theme.primary}-400 text-sm hover:text-${theme.primary}-300 transition-colors`}
          >
            Forgot Password?
          </Link>
        </div>
      </div>

      {captchaRequired && (
        <div className="space-y-2 p-3 bg-amber-500/15 border border-amber-400/30 rounded-xl">
          <Label className="text-amber-200 flex items-center gap-2 font-medium">
            <AlertCircle className="w-4 h-4" /> {captchaQuestion}
          </Label>
          <Input
            type="text"
            placeholder="Answer"
            value={captchaAnswer}
            onChange={(e) => onCaptchaChange(e.target.value)}
            className="bg-white/15 border-white/50 text-white placeholder:text-gray-400"
          />
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-xl">
          <p className="text-red-300 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </p>
        </div>
      )}

      <Button
        type="submit"
        disabled={loading}
        className={`w-full h-12 bg-gradient-to-r from-${theme.primary}-500 to-${theme.secondary}-500 hover:from-${theme.primary}-600 hover:to-${theme.secondary}-600 text-white font-semibold text-lg shadow-lg shadow-${theme.primary}-500/25 transition-all duration-300`}
        data-testid="submit"
      >
        {loading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <>Sign In <ChevronRight className="w-5 h-5 ml-2" /></>
        )}
      </Button>

      {ssoConfig?.enabled && (
        <>
          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-white/40"></span>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-transparent px-2 text-gray-200 font-medium">Or</span>
            </div>
          </div>
          <Button
            variant="outline"
            onClick={onSsoLogin}
            disabled={ssoLoading}
            className="w-full border-white/50 text-white font-medium hover:bg-white/20"
          >
            {ssoLoading ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Building2 className="w-4 h-4 mr-2" />
            )}
            Microsoft SSO
          </Button>
        </>
      )}
    </form>
  );
};

export default LoginForm;
