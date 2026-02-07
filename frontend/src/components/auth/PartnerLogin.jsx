/**
 * PartnerLogin Component
 * Handles business partner OTP-based login
 */
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Loader2, ArrowLeft } from 'lucide-react';

const PartnerLogin = ({
  mobile,
  onMobileChange,
  otp,
  onOtpChange,
  otpSent,
  onRequestOtp,
  onVerifyOtp,
  onBack,
  loading,
  theme
}) => {
  if (!otpSent) {
    return (
      <div className="space-y-4">
        <div className="space-y-2">
          <Label className="text-white font-medium">Registered Mobile</Label>
          <Input
            type="tel"
            placeholder="10-digit mobile"
            value={mobile}
            onChange={(e) => onMobileChange(e.target.value.replace(/\D/g, '').slice(0, 10))}
            className="bg-white/15 border-white/50 text-white placeholder:text-gray-400"
            data-testid="bp-mobile"
          />
        </div>
        <Button
          onClick={onRequestOtp}
          disabled={loading || mobile.length !== 10}
          className={`w-full h-12 bg-gradient-to-r from-${theme.primary}-500 to-${theme.secondary}-500`}
        >
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Send OTP'}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className={`p-3 bg-${theme.primary}-500/20 border border-${theme.primary}-400/30 rounded-xl text-center`}>
        <p className={`text-${theme.primary}-200 text-sm font-medium`}>OTP sent to {mobile}</p>
      </div>
      <Input
        type="text"
        placeholder="6-digit OTP"
        value={otp}
        onChange={(e) => onOtpChange(e.target.value.replace(/\D/g, '').slice(0, 6))}
        maxLength={6}
        className="bg-white/15 border-white/50 text-white text-center text-xl tracking-widest font-mono placeholder:text-gray-400"
        data-testid="otp"
      />
      <Button
        onClick={onVerifyOtp}
        disabled={loading || otp.length !== 6}
        className={`w-full h-12 bg-gradient-to-r from-${theme.primary}-500 to-${theme.secondary}-500`}
      >
        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Verify & Login'}
      </Button>
      <Button
        variant="ghost"
        onClick={onBack}
        className="w-full text-gray-200 font-medium hover:text-white hover:bg-white/10"
      >
        <ArrowLeft className="w-4 h-4 mr-2" /> Change Number
      </Button>
    </div>
  );
};

export default PartnerLogin;
