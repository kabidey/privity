/**
 * Login Page
 * Main authentication page with login, registration, and partner login
 * Refactored into smaller components for better maintainability
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { PublicClientApplication } from '@azure/msal-browser';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '../utils/api';
import { 
  Sparkles, Loader2, Building2, Mail, ArrowLeft, Phone, Play, Users 
} from 'lucide-react';
import { getMsalConfig, getLoginRequest } from '../config/msalConfig';
import { getFullVersion } from '../version';
import { useDemo } from '../contexts/DemoContext';
import useContentProtection from '../hooks/useContentProtection';

// Import auth components
import {
  FloatingIcons,
  TypewriterQuote,
  LoginForm,
  RegistrationForm,
  PartnerLogin,
  CacheClearPrompt,
  LOGIN_THEMES,
  LOGO_URL
} from '../components/auth';

const Login = () => {
  const navigate = useNavigate();
  const { enterDemoMode } = useDemo();
  
  // Enable content protection
  useContentProtection();
  
  // Form state
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [ssoLoading, setSsoLoading] = useState(false);
  const [ssoConfig, setSsoConfig] = useState(null);
  const [msalInstance, setMsalInstance] = useState(null);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState('');
  const [loginType, setLoginType] = useState('employee');
  const [bpOtpSent, setBpOtpSent] = useState(false);
  const [bpOtp, setBpOtp] = useState('');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    pan_number: '',
    mobile_number: '',
  });
  
  // Mobile update state
  const [mobileRequired, setMobileRequired] = useState(false);
  const [mobileUpdateNumber, setMobileUpdateNumber] = useState('');
  const [updatingMobile, setUpdatingMobile] = useState(false);
  
  // Captcha state
  const [captchaRequired, setCaptchaRequired] = useState(false);
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaQuestion, setCaptchaQuestion] = useState('');
  const [captchaAnswer, setCaptchaAnswer] = useState('');
  
  // OTP Registration state
  const [registrationStep, setRegistrationStep] = useState('form');
  const [registrationOtp, setRegistrationOtp] = useState('');
  const [resendingOtp, setResendingOtp] = useState(false);
  const [otpTimer, setOtpTimer] = useState(0);
  
  // Error state
  const [formError, setFormError] = useState('');

  // Theme
  const [currentTheme] = useState(() => LOGIN_THEMES[Math.floor(Math.random() * LOGIN_THEMES.length)]);

  // OTP Timer
  useEffect(() => {
    if (otpTimer > 0) {
      const timer = setTimeout(() => setOtpTimer(otpTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [otpTimer]);

  // Fetch SSO config
  useEffect(() => {
    const fetchSsoConfig = async () => {
      try {
        const response = await api.get('/auth/sso/config');
        if (response.data.enabled) {
          setSsoConfig(response.data);
          const msalConfig = getMsalConfig(response.data);
          const instance = new PublicClientApplication(msalConfig);
          await instance.initialize();
          setMsalInstance(instance);
        }
      } catch (error) {
        console.log('SSO not configured');
      }
    };
    fetchSsoConfig();
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setFormError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setFormError('');
    
    try {
      if (isLogin) {
        const loginData = { email: formData.email, password: formData.password };
        if (captchaRequired && captchaAnswer) {
          loginData.captcha_answer = captchaAnswer;
          loginData.captcha_token = captchaToken;
        }
        
        const response = await api.post('/auth/login', loginData);
        const { token, user, mobile_required } = response.data;
        
        if (mobile_required) {
          setMobileRequired(true);
          localStorage.setItem('token', token);
          toast.info('Please update your mobile number to continue');
          return;
        }
        
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
        toast.success('Login successful!');
        navigate('/');
      } else {
        // OTP-Based Registration
        if (registrationStep === 'form') {
          const email = formData.email.toLowerCase();
          const allowedDomains = ['smifs.com', 'smifs.co.in'];
          const emailDomain = email.split('@')[1];
          
          if (!allowedDomains.includes(emailDomain)) {
            setFormError('Registration is only allowed for @smifs.com or @smifs.co.in email addresses');
            setLoading(false);
            return;
          }
          
          const cleanMobile = formData.mobile_number?.replace(/\D/g, '') || '';
          if (cleanMobile.length !== 10) {
            setFormError('Please enter a valid 10-digit mobile number');
            setLoading(false);
            return;
          }
          
          const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
          const cleanPan = formData.pan_number?.toUpperCase().trim() || '';
          if (!cleanPan || !panRegex.test(cleanPan)) {
            setFormError('Please enter a valid PAN number (e.g., ABCDE1234F)');
            setLoading(false);
            return;
          }
          
          await api.post('/auth/register/request-otp', {
            email: formData.email,
            password: formData.password,
            name: formData.name,
            mobile_number: cleanMobile,
            pan_number: cleanPan,
          });
          
          setRegistrationStep('otp');
          setOtpTimer(600);
          toast.success(`OTP sent to ${formData.email}. Please check your inbox.`);
        } else if (registrationStep === 'otp') {
          if (!registrationOtp || registrationOtp.length !== 6) {
            setFormError('Please enter the 6-digit OTP');
            setLoading(false);
            return;
          }
          
          await api.post('/auth/register/verify-otp', {
            email: formData.email,
            otp: registrationOtp,
          });
          
          setRegisteredEmail(formData.email);
          setRegistrationSuccess(true);
          setRegistrationStep('form');
          setRegistrationOtp('');
          toast.success('Registration submitted! Awaiting admin approval.');
        }
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'An error occurred';
      
      if (error.response?.data?.captcha_required) {
        setCaptchaRequired(true);
        setCaptchaToken(error.response.data.captcha_token);
        setCaptchaQuestion(error.response.data.captcha_question);
        setFormError('Too many attempts. Please answer the security question.');
      } else if (errorMsg.includes('Invalid credentials') || errorMsg.includes('not found')) {
        setFormError('Invalid email or password. Please check your credentials and try again.');
      } else if (errorMsg.includes('not approved')) {
        setFormError('Your account is pending approval. Please contact the administrator.');
      } else if (errorMsg.includes('locked') || errorMsg.includes('suspended')) {
        setFormError('Your account has been locked. Please contact support.');
      } else {
        setFormError(errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setResendingOtp(true);
    try {
      await api.post('/auth/register/request-otp', {
        email: formData.email,
        password: formData.password,
        name: formData.name,
        mobile_number: formData.mobile_number,
        pan_number: formData.pan_number,
      });
      setOtpTimer(600);
      toast.success('New OTP sent!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to resend OTP');
    } finally {
      setResendingOtp(false);
    }
  };

  const handleBpOtpRequest = async () => {
    if (!formData.mobile_number || formData.mobile_number.length !== 10) {
      toast.error('Please enter a valid 10-digit mobile number');
      return;
    }
    setLoading(true);
    try {
      await api.post('/auth/bp/request-otp', { mobile_number: formData.mobile_number });
      setBpOtpSent(true);
      toast.success('OTP sent to your registered mobile');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleBpOtpVerify = async () => {
    if (!bpOtp || bpOtp.length !== 6) {
      toast.error('Please enter the 6-digit OTP');
      return;
    }
    setLoading(true);
    try {
      const response = await api.post('/auth/bp/verify-otp', {
        mobile_number: formData.mobile_number,
        otp: bpOtp,
      });
      const { token, user } = response.data;
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      toast.success('Login successful!');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleMobileUpdate = async () => {
    if (!mobileUpdateNumber || mobileUpdateNumber.length !== 10) {
      toast.error('Please enter a valid 10-digit mobile number');
      return;
    }
    setUpdatingMobile(true);
    try {
      await api.put('/auth/update-mobile', { mobile_number: mobileUpdateNumber });
      toast.success('Mobile updated successfully!');
      setMobileRequired(false);
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update mobile');
    } finally {
      setUpdatingMobile(false);
    }
  };

  const handleSsoLogin = async () => {
    if (!msalInstance) return;
    setSsoLoading(true);
    try {
      const loginRequest = getLoginRequest(ssoConfig);
      const response = await msalInstance.loginPopup(loginRequest);
      const ssoResponse = await api.post('/auth/sso/callback', {
        token: response.idToken,
        account: response.account,
      });
      const { token, user } = ssoResponse.data;
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      toast.success('SSO Login successful!');
      navigate('/');
    } catch (error) {
      if (error.errorCode !== 'user_cancelled') {
        toast.error('SSO login failed');
      }
    } finally {
      setSsoLoading(false);
    }
  };

  const handleDemoMode = async () => {
    setDemoLoading(true);
    try {
      enterDemoMode('employee');
      navigate('/demo');
    } catch (error) {
      toast.error('Failed to start demo mode');
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className={`min-h-screen flex flex-col items-center justify-center bg-gradient-to-br ${currentTheme.gradient} p-4 relative overflow-hidden`}>
      {/* Cache Clear Prompt */}
      <CacheClearPrompt theme={currentTheme} />
      
      {/* Floating Icons */}
      <FloatingIcons theme={currentTheme} />
      
      {/* Decorative elements */}
      <div className={`absolute top-0 left-0 w-96 h-96 bg-${currentTheme.primary}-500/10 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2`}></div>
      <div className={`absolute bottom-0 right-0 w-96 h-96 bg-${currentTheme.secondary}-500/10 rounded-full blur-3xl translate-x-1/2 translate-y-1/2`}></div>
      
      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center w-full max-w-md">
        {/* Logo */}
        <div className="mb-6 animate-fade-in relative">
          <div className="relative">
            <div className={`absolute inset-0 bg-gradient-to-r from-${currentTheme.primary}-400/20 to-${currentTheme.secondary}-400/20 blur-xl rounded-full`}></div>
            <div className="bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-xl relative">
              <img 
                src={LOGO_URL}
                alt="SMIFS & Privity" 
                className="h-12 w-auto relative z-10 drop-shadow-sm"
                data-testid="logo"
              />
            </div>
          </div>
        </div>

        {/* Quote */}
        <TypewriterQuote theme={currentTheme} />

        {/* Login Card */}
        <div className="w-full animate-fade-in" style={{animationDelay: '0.4s'}}>
          <Card className={`bg-white/10 backdrop-blur-xl border-white/20 shadow-2xl shadow-${currentTheme.primary}-500/10`} data-testid="login-card">
            <CardHeader className="space-y-1 pb-4">
              <div className="flex items-center justify-center gap-2 mb-2">
                <div className={`h-1 w-12 bg-gradient-to-r from-transparent to-${currentTheme.primary}-500 rounded-full`}></div>
                <Sparkles className={`w-5 h-5 text-${currentTheme.primary}-400`} />
                <div className={`h-1 w-12 bg-gradient-to-l from-transparent to-${currentTheme.primary}-500 rounded-full`}></div>
              </div>
              <CardTitle className="text-2xl font-bold text-center text-white">
                {isLogin ? 'Welcome Back' : 'Join Privity'}
              </CardTitle>
              <CardDescription className="text-center text-gray-200 font-medium">
                {isLogin ? 'Access exclusive PE opportunities' : 'Start your private equity journey'}
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {registrationSuccess ? (
                <div className="space-y-4">
                  <div className={`p-4 bg-${currentTheme.primary}-500/20 border border-${currentTheme.primary}-400/30 rounded-xl`}>
                    <div className="flex items-center gap-3">
                      <Mail className={`w-5 h-5 text-${currentTheme.primary}-400`} />
                      <div>
                        <p className="font-semibold text-white">Registration Submitted!</p>
                        <p className="text-sm text-gray-200">{registeredEmail} is pending approval.</p>
                      </div>
                    </div>
                  </div>
                  <Button 
                    onClick={() => { setRegistrationSuccess(false); setIsLogin(true); }}
                    className={`w-full bg-gradient-to-r from-${currentTheme.primary}-500 to-${currentTheme.secondary}-500`}
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" /> Back to Login
                  </Button>
                </div>
              ) : mobileRequired ? (
                <div className="space-y-4">
                  <div className="p-4 bg-amber-500/15 border border-amber-400/30 rounded-xl">
                    <div className="flex items-center gap-3">
                      <Phone className="w-5 h-5 text-amber-300" />
                      <p className="text-gray-100 text-sm font-medium">Update your mobile to continue</p>
                    </div>
                  </div>
                  <Input 
                    type="tel" 
                    placeholder="10-digit mobile" 
                    value={mobileUpdateNumber}
                    onChange={(e) => setMobileUpdateNumber(e.target.value.replace(/\D/g, '').slice(0, 10))}
                    className="bg-white/15 border-white/50 text-white placeholder:text-gray-400" 
                    data-testid="mobile-input" 
                  />
                  <Button 
                    onClick={handleMobileUpdate} 
                    disabled={updatingMobile}
                    className={`w-full bg-gradient-to-r from-${currentTheme.primary}-500 to-${currentTheme.secondary}-500`}
                  >
                    {updatingMobile && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                    Update & Continue
                  </Button>
                </div>
              ) : (
                <>
                  {isLogin && (
                    <Tabs value={loginType} onValueChange={setLoginType} className="mb-4">
                      <TabsList className="grid w-full grid-cols-2 bg-white/10">
                        <TabsTrigger 
                          value="employee" 
                          className={`data-[state=active]:bg-${currentTheme.primary}-500 data-[state=active]:text-white text-gray-200 font-medium`}
                        >
                          <Building2 className="w-4 h-4 mr-2" /> Employee
                        </TabsTrigger>
                        <TabsTrigger 
                          value="partner" 
                          className={`data-[state=active]:bg-${currentTheme.primary}-500 data-[state=active]:text-white text-gray-200 font-medium`}
                        >
                          <Users className="w-4 h-4 mr-2" /> Partner
                        </TabsTrigger>
                      </TabsList>
                    </Tabs>
                  )}

                  {loginType === 'partner' && isLogin ? (
                    <PartnerLogin
                      mobile={formData.mobile_number}
                      onMobileChange={(val) => setFormData({...formData, mobile_number: val})}
                      otp={bpOtp}
                      onOtpChange={setBpOtp}
                      otpSent={bpOtpSent}
                      onRequestOtp={handleBpOtpRequest}
                      onVerifyOtp={handleBpOtpVerify}
                      onBack={() => setBpOtpSent(false)}
                      loading={loading}
                      theme={currentTheme}
                    />
                  ) : isLogin ? (
                    <LoginForm
                      formData={formData}
                      onChange={handleChange}
                      onSubmit={handleSubmit}
                      loading={loading}
                      error={formError}
                      theme={currentTheme}
                      captchaRequired={captchaRequired}
                      captchaQuestion={captchaQuestion}
                      captchaAnswer={captchaAnswer}
                      onCaptchaChange={setCaptchaAnswer}
                      ssoConfig={ssoConfig}
                      ssoLoading={ssoLoading}
                      onSsoLogin={handleSsoLogin}
                    />
                  ) : (
                    <RegistrationForm
                      formData={formData}
                      onChange={handleChange}
                      onSubmit={handleSubmit}
                      loading={loading}
                      error={formError}
                      theme={currentTheme}
                      step={registrationStep}
                      otp={registrationOtp}
                      onOtpChange={setRegistrationOtp}
                      otpTimer={otpTimer}
                      onResendOtp={handleResendOtp}
                      resendingOtp={resendingOtp}
                      onBack={() => { setRegistrationStep('form'); setRegistrationOtp(''); }}
                    />
                  )}
                  
                  <div className="text-center pt-2">
                    <button
                      type="button"
                      onClick={() => { setIsLogin(!isLogin); setFormError(''); setRegistrationStep('form'); }}
                      className={`text-${currentTheme.primary}-400 hover:text-${currentTheme.primary}-300 text-sm transition-colors`}
                      data-testid="toggle"
                    >
                      {isLogin ? "Don't have an account? Register" : 'Already have an account? Sign in'}
                    </button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Demo Button */}
        <div className="mt-4 text-center">
          <Button 
            variant="ghost" 
            onClick={handleDemoMode} 
            disabled={demoLoading} 
            className="text-gray-200 font-medium hover:text-white hover:bg-white/20" 
            data-testid="demo"
          >
            {demoLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Play className="w-4 h-4 mr-2" />}
            Try Demo
          </Button>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center animate-fade-in" style={{animationDelay: '0.6s'}}>
          <p className="text-gray-200 text-xs font-medium">© 2026 SMIFS Private Equity. All rights reserved.</p>
          <p className="text-gray-300 text-xs mt-1 font-medium">Powered by Privity | v{getFullVersion()}</p>
          <p className="text-emerald-300 text-xs mt-2 font-semibold tracking-wide drop-shadow-sm">✨ Vibe Coded by Somnath Dey</p>
        </div>
      </div>
    </div>
  );
};

export default Login;
