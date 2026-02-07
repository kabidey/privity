/**
 * RegistrationForm Component
 * Handles OTP-based user registration
 */
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Loader2, AlertCircle, ChevronRight } from 'lucide-react';
import OtpInput from './OtpInput';

const RegistrationForm = ({
  formData,
  onChange,
  onSubmit,
  loading,
  error,
  theme,
  step,
  otp,
  onOtpChange,
  otpTimer,
  onResendOtp,
  resendingOtp,
  onBack
}) => {
  if (step === 'otp') {
    return (
      <OtpInput
        value={otp}
        onChange={onOtpChange}
        timer={otpTimer}
        onResend={onResendOtp}
        resending={resendingOtp}
        onBack={onBack}
        email={formData.email}
        theme={theme}
        loading={loading}
        onSubmit={onSubmit}
        submitText="Complete Registration"
      />
    );
  }

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
      </div>

      <div className="space-y-2">
        <Label className="text-white font-medium">Full Name <span className="text-red-400">*</span></Label>
        <Input
          type="text"
          name="name"
          placeholder="Your name"
          value={formData.name}
          onChange={onChange}
          required
          className="bg-white/15 border-white/50 text-white placeholder:text-gray-400"
          data-testid="name"
        />
      </div>

      <div className="space-y-2">
        <Label className="text-white font-medium">Mobile Number <span className="text-red-400">*</span></Label>
        <Input
          type="tel"
          name="mobile_number"
          placeholder="10-digit mobile number"
          value={formData.mobile_number}
          onChange={(e) => onChange({
            target: {
              name: 'mobile_number',
              value: e.target.value.replace(/\D/g, '').slice(0, 10)
            }
          })}
          maxLength={10}
          required
          className="bg-white/15 border-white/50 text-white placeholder:text-gray-400"
          data-testid="mobile"
        />
        <p className="text-gray-300 text-xs font-medium">Required for SMS/WhatsApp notifications</p>
      </div>

      <div className="space-y-2">
        <Label className="text-white font-medium">PAN Number <span className="text-red-400">*</span></Label>
        <Input
          type="text"
          name="pan_number"
          placeholder="ABCDE1234F"
          value={formData.pan_number}
          onChange={(e) => onChange({
            target: {
              name: 'pan_number',
              value: e.target.value.toUpperCase()
            }
          })}
          maxLength={10}
          required
          className="bg-white/15 border-white/50 text-white font-mono placeholder:text-gray-400"
          data-testid="pan"
        />
        <p className="text-gray-300 text-xs font-medium">Required for KYC verification</p>
      </div>

      {/* Domain restriction warning */}
      <div className="p-3 bg-amber-500/15 border border-amber-400/30 rounded-lg">
        <p className="text-amber-200 text-xs flex items-center gap-2 font-medium">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          Registration is only available for @smifs.com and @smifs.co.in email addresses
        </p>
      </div>

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
          <>Send OTP <ChevronRight className="w-5 h-5 ml-2" /></>
        )}
      </Button>
    </form>
  );
};

export default RegistrationForm;
