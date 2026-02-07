/**
 * OtpInput Component
 * Reusable OTP input with timer and resend functionality
 */
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Loader2, ArrowLeft } from 'lucide-react';

const OtpInput = ({
  value,
  onChange,
  timer,
  onResend,
  resending,
  onBack,
  email,
  theme,
  loading,
  onSubmit,
  submitText = 'Verify OTP'
}) => {
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className="space-y-4">
      <div className={`p-4 bg-${theme.primary}-500/20 border border-${theme.primary}-400/30 rounded-xl text-center`}>
        <h3 className="text-white text-lg font-bold">Verify Your Email</h3>
        <p className={`text-${theme.primary}-200 text-sm mt-1 font-medium`}>OTP sent to {email}</p>
      </div>
      
      <div className="space-y-2">
        <Label className="text-white font-medium">Enter 6-digit OTP</Label>
        <Input 
          type="text" 
          value={value}
          onChange={(e) => onChange(e.target.value.replace(/\D/g, '').slice(0, 6))}
          placeholder="000000"
          maxLength={6}
          className="bg-white/15 border-white/50 text-white text-center text-xl tracking-widest font-mono placeholder:text-gray-400"
          data-testid="otp-input"
        />
      </div>
      
      {timer > 0 && (
        <p className="text-gray-300 text-xs text-center font-medium">
          OTP expires in {formatTime(timer)}
        </p>
      )}
      
      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={onResend}
          disabled={resending || timer > 540}
          className="flex-1 border-white/40 text-white hover:bg-white/10"
        >
          {resending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
          Resend OTP
        </Button>
        <Button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            onSubmit(e);
          }}
          disabled={loading || value.length !== 6}
          className={`flex-1 bg-gradient-to-r from-${theme.primary}-500 to-${theme.secondary}-500`}
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
          {submitText}
        </Button>
      </div>
      
      <button
        type="button"
        onClick={onBack}
        className="text-gray-200 text-sm hover:text-white flex items-center gap-1 font-medium"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>
    </div>
  );
};

export default OtpInput;
