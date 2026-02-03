import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { PublicClientApplication } from '@azure/msal-browser';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import api from '../utils/api';
import { TrendingUp, AlertCircle, Loader2, Building2, Mail, ArrowLeft, Code, Quote } from 'lucide-react';
import { getMsalConfig, getLoginRequest } from '../config/msalConfig';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getFullVersion } from '../version';

const Login = () => {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [ssoLoading, setSsoLoading] = useState(false);
  const [ssoConfig, setSsoConfig] = useState(null);
  const [msalInstance, setMsalInstance] = useState(null);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState('');
  const [loginType, setLoginType] = useState('employee'); // 'employee' or 'partner'
  const [bpOtpSent, setBpOtpSent] = useState(false);
  const [bpOtp, setBpOtp] = useState('');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    pan_number: '',
  });
  
  // CAPTCHA state
  const [captchaRequired, setCaptchaRequired] = useState(false);
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaQuestion, setCaptchaQuestion] = useState('');
  const [captchaAnswer, setCaptchaAnswer] = useState('');

  // Private Equity Quotes
  const peQuotes = [
    { quote: "Private equity is not just about buying companies, it's about building them.", author: "Henry Kravis" },
    { quote: "The best investment you can make is in yourself and the companies you believe in.", author: "Warren Buffett" },
    { quote: "In private equity, patience is not just a virtue—it's the entire strategy.", author: "David Rubenstein" },
    { quote: "Value creation is the cornerstone of successful private equity investing.", author: "Stephen Schwarzman" },
    { quote: "Private markets offer opportunities that public markets simply cannot match.", author: "Marc Andreessen" },
    { quote: "The key to private equity is finding diamonds in the rough and polishing them.", author: "Leon Black" },
    { quote: "Long-term thinking creates long-term value.", author: "Jeff Bezos" },
    { quote: "In unlisted markets, information asymmetry is your competitive advantage.", author: "Ray Dalio" },
    { quote: "Private equity transforms potential into performance.", author: "Carlyle Group" },
    { quote: "True wealth is built through strategic, patient capital deployment.", author: "Charlie Munger" },
  ];

  const [currentQuote, setCurrentQuote] = useState(() => 
    peQuotes[Math.floor(Math.random() * peQuotes.length)]
  );

  // Rotate quotes on component mount
  useEffect(() => {
    setCurrentQuote(peQuotes[Math.floor(Math.random() * peQuotes.length)]);
  }, []);

  // Fetch SSO config on mount
  useEffect(() => {
    const fetchSsoConfig = async () => {
      try {
        const response = await api.get('/auth/sso/config');
        setSsoConfig(response.data);
        
        // Initialize MSAL if SSO is enabled
        if (response.data?.enabled) {
          const msalConfig = getMsalConfig(response.data);
          if (msalConfig) {
            const instance = new PublicClientApplication(msalConfig);
            await instance.initialize();
            setMsalInstance(instance);
          }
        }
      } catch (error) {
        console.error('Failed to fetch SSO config:', error);
        setSsoConfig({ enabled: false });
      }
    };
    
    fetchSsoConfig();
  }, []);

  const handleMicrosoftLogin = async () => {
    if (!msalInstance || !ssoConfig?.enabled) {
      toast.error('Microsoft SSO is not configured');
      return;
    }

    setSsoLoading(true);
    try {
      // Trigger Microsoft login popup
      const loginRequest = getLoginRequest(ssoConfig);
      const response = await msalInstance.loginPopup(loginRequest);
      
      if (response?.accessToken) {
        // Send token to backend for validation
        const backendResponse = await api.post('/auth/sso/login', {
          token: response.accessToken
        });
        
        localStorage.setItem('token', backendResponse.data.token);
        localStorage.setItem('user', JSON.stringify(backendResponse.data.user));
        
        toast.success(`Welcome, ${backendResponse.data.user.name}!`);
        navigate('/');
      }
    } catch (error) {
      console.error('Microsoft SSO error:', error);
      if (error.errorCode === 'user_cancelled') {
        toast.info('Login cancelled');
      } else {
        toast.error(error.response?.data?.detail || 'SSO login failed. Please try again.');
      }
    } finally {
      setSsoLoading(false);
    }
  };

  const validateEmail = (email) => {
    const domain = email.split('@')[1]?.toLowerCase();
    return domain === 'smifs.com';
  };

  const validatePAN = (pan) => {
    // PAN not required for pedesk@smifs.com
    if (formData.email.toLowerCase() === 'pedesk@smifs.com') return true;
    return pan && pan.length === 10;
  };

  const isSuperAdmin = formData.email.toLowerCase() === 'pedesk@smifs.com';

  // Business Partner OTP request
  const handleBPRequestOTP = async (e) => {
    e.preventDefault();
    if (!formData.email) {
      toast.error('Please enter your email');
      return;
    }
    
    setLoading(true);
    try {
      await api.post('/business-partners/auth/request-otp', { email: formData.email });
      setBpOtpSent(true);
      toast.success('OTP sent to your email');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  // Business Partner OTP verification
  const handleBPVerifyOTP = async (e) => {
    e.preventDefault();
    if (!bpOtp || bpOtp.length !== 6) {
      toast.error('Please enter the 6-digit OTP');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.post('/business-partners/auth/verify-otp', { 
        email: formData.email,
        otp: bpOtp 
      });
      
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      
      toast.success('Logged in successfully');
      navigate('/bp-dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Check domain for registration
    if (!isLogin && !validateEmail(formData.email)) {
      toast.error('Registration is restricted to @smifs.com email addresses only');
      return;
    }
    
    // Validate PAN for registration (not required for superadmin)
    if (!isLogin && !isSuperAdmin && !validatePAN(formData.pan_number)) {
      toast.error('PAN number must be exactly 10 characters');
      return;
    }
    
    // Validate CAPTCHA if required
    if (captchaRequired && !captchaAnswer) {
      toast.error('Please solve the CAPTCHA to continue');
      return;
    }
    
    setLoading(true);

    try {
      if (isLogin) {
        // Build login URL with CAPTCHA params if required
        let loginUrl = '/auth/login';
        if (captchaRequired && captchaToken && captchaAnswer) {
          loginUrl += `?captcha_token=${encodeURIComponent(captchaToken)}&captcha_answer=${encodeURIComponent(captchaAnswer)}`;
        }
        
        const response = await api.post(loginUrl, { 
          email: formData.email, 
          password: formData.password 
        });
        
        localStorage.setItem('token', response.data.token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        
        // Clear CAPTCHA state on success
        setCaptchaRequired(false);
        setCaptchaToken('');
        setCaptchaQuestion('');
        setCaptchaAnswer('');
        
        toast.success('Logged in successfully');
        navigate('/');
      } else {
        // Registration - no password needed
        const payload = {
          email: formData.email,
          name: formData.name,
          pan_number: isSuperAdmin ? null : formData.pan_number
        };
        
        const response = await api.post('/auth/register', payload);
        
        // Show success message
        setRegistrationSuccess(true);
        setRegisteredEmail(formData.email);
        toast.success('Account created! Check your email for login credentials.');
      }
    } catch (error) {
      const errorResponse = error.response?.data;
      const errorDetail = errorResponse?.detail;
      
      // Handle CAPTCHA requirement
      // detail can be either a string or an object with captcha info
      const isCaptchaRequired = 
        error.response?.status === 428 || 
        (typeof errorDetail === 'object' && errorDetail?.captcha_required);
      
      if (isCaptchaRequired) {
        const captchaData = typeof errorDetail === 'object' ? errorDetail : {};
        setCaptchaRequired(true);
        setCaptchaToken(captchaData?.captcha_token || '');
        setCaptchaQuestion(captchaData?.captcha_question || '');
        setCaptchaAnswer('');
        
        const errorMessage = captchaData?.message || 'Please solve the CAPTCHA to continue';
        toast.error(errorMessage);
      } else {
        // Regular error handling
        const message = typeof errorDetail === 'string' 
          ? errorDetail 
          : errorDetail?.message || 'An error occurred';
        toast.error(message);
        
        // Clear CAPTCHA if error is not captcha related
        // (but don't clear if we might need it next attempt)
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Left Side - Image (hidden on mobile) */}
      <div
        className="hidden lg:block lg:w-1/2 bg-cover bg-center relative"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1769123012428-6858ea810a74?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzZ8MHwxfHNlYXJjaHwzfHxhYnN0cmFjdCUyMGZpbmFuY2lhbCUyMGdyYXBoJTIwYXJ0JTIwZGFyayUyMGdyZWVufGVufDB8fHx8MTc2OTI0OTcyN3ww&ixlib=rb-4.1.0&q=85')`,
        }}
      >
        <div className="absolute inset-0 bg-primary/80 flex flex-col">
          {/* Top Left Logo */}
          <div className="absolute top-6 left-6 bg-white/95 rounded-lg p-3 shadow-lg">
            <img 
              src="https://customer-assets.emergentagent.com/job_8c5c41a7-4474-44d9-8a72-5476f60329b4/artifacts/eineo77y_SMIFS%20%26%20PRIVITY%20Logo.png" 
              alt="SMIFS & Privity Logo" 
              className="h-10 w-auto"
              data-testid="smifs-privity-logo"
            />
          </div>
          {/* Center Content with Quote */}
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-white px-8 max-w-lg">
              {/* Quote Section */}
              <div className="mb-8 relative" data-testid="pe-quote-section">
                <Quote className="w-10 h-10 mx-auto mb-4 opacity-60" strokeWidth={1.5} />
                <blockquote className="text-xl italic font-light leading-relaxed mb-3">
                  "{currentQuote.quote}"
                </blockquote>
                <cite className="text-sm opacity-80 not-italic">— {currentQuote.author}</cite>
              </div>
              
              {/* Divider */}
              <div className="w-24 h-0.5 bg-white/30 mx-auto mb-8"></div>
              
              {/* Title Section */}
              <TrendingUp className="w-14 h-14 mx-auto mb-4" strokeWidth={1.5} />
              <h1 className="text-3xl font-bold mb-3">SMIFS Private Equity</h1>
              <p className="text-base opacity-90">Manage your client bookings and track profit & loss efficiently</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="w-full lg:w-1/2 flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8 min-h-screen lg:min-h-0">
        {/* Quote above logo - shown on both mobile and desktop */}
        <div className="mb-4 text-center max-w-sm" data-testid="pe-quote-above-logo">
          <p className="text-sm italic text-muted-foreground">
            "{currentQuote.quote}"
          </p>
          <p className="text-xs text-muted-foreground/70 mt-1">— {currentQuote.author}</p>
        </div>
        
        {/* Logo - shown on both mobile and desktop */}
        <div className="mb-6 lg:mb-8 flex justify-center">
          <img 
            src="https://customer-assets.emergentagent.com/job_8c5c41a7-4474-44d9-8a72-5476f60329b4/artifacts/vbv5ybri_privity.png" 
            alt="Privity Logo" 
            className="h-12 sm:h-14 lg:h-16 w-auto"
            data-testid="privity-logo"
          />
        </div>
        
        <Card className="w-full max-w-md border shadow-sm" data-testid="login-card">
          <CardHeader className="space-y-1 px-4 sm:px-6 pt-4 sm:pt-6">
            <CardTitle className="text-2xl sm:text-3xl font-bold text-center lg:text-left">{isLogin ? 'Welcome back' : 'Create account'}</CardTitle>
            <CardDescription className="text-sm sm:text-base text-center lg:text-left">
              {isLogin ? 'Enter your credentials to access your account' : 'Fill in the details to get started'}
            </CardDescription>
          </CardHeader>
          <CardContent className="px-4 sm:px-6 pb-4 sm:pb-6">
            {/* Registration Success Message */}
            {registrationSuccess ? (
              <div className="space-y-4">
                <div className="p-4 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-green-100 dark:bg-green-900 rounded-full">
                      <AlertCircle className="h-6 w-6 text-green-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-green-800 dark:text-green-200">Account Created Successfully!</h3>
                      <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                        Your login credentials have been sent to <strong>{registeredEmail}</strong>
                      </p>
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg">
                  <p className="text-sm text-amber-800 dark:text-amber-200">
                    <strong>Note:</strong> Please check your email for your temporary password. You will be required to change it after your first login.
                  </p>
                </div>
                <Button 
                  className="w-full" 
                  onClick={() => {
                    setRegistrationSuccess(false);
                    setIsLogin(true);
                    setFormData({ email: registeredEmail, password: '', name: '', pan_number: '' });
                  }}
                >
                  Go to Login
                </Button>
              </div>
            ) : (
            <>
            {/* Login Type Tabs for Login Only */}
            {isLogin && (
              <Tabs value={loginType} onValueChange={(v) => { setLoginType(v); setBpOtpSent(false); setBpOtp(''); }} className="mb-4">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="employee" className="data-[state=active]:bg-emerald-500 data-[state=active]:text-white">
                    <Mail className="h-4 w-4 mr-2" />
                    Employee
                  </TabsTrigger>
                  <TabsTrigger value="partner" className="data-[state=active]:bg-emerald-500 data-[state=active]:text-white">
                    <Building2 className="h-4 w-4 mr-2" />
                    Business Partner
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            )}

            {/* Business Partner OTP Login */}
            {isLogin && loginType === 'partner' ? (
              <div className="space-y-4">
                {!bpOtpSent ? (
                  <form onSubmit={handleBPRequestOTP} className="space-y-4">
                    <div className="p-3 bg-emerald-50 dark:bg-emerald-950 rounded-lg">
                      <p className="text-sm text-emerald-800 dark:text-emerald-200">
                        <Building2 className="h-4 w-4 inline mr-1" />
                        Business Partners login using OTP sent to their registered email.
                      </p>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="bp-email">Email <span className="text-red-500">*</span></Label>
                      <Input
                        id="bp-email"
                        type="email"
                        placeholder="partner@example.com"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        required
                      />
                    </div>
                    <Button type="submit" className="w-full bg-emerald-500 hover:bg-emerald-600" disabled={loading}>
                      {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Mail className="h-4 w-4 mr-2" />}
                      {loading ? 'Sending OTP...' : 'Send OTP'}
                    </Button>
                  </form>
                ) : (
                  <form onSubmit={handleBPVerifyOTP} className="space-y-4">
                    <div className="p-3 bg-green-50 dark:bg-green-950 rounded-lg">
                      <p className="text-sm text-green-800 dark:text-green-200">
                        OTP sent to <strong>{formData.email}</strong>. Valid for 10 minutes.
                      </p>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="bp-otp">Enter 6-Digit OTP <span className="text-red-500">*</span></Label>
                      <Input
                        id="bp-otp"
                        type="text"
                        placeholder="000000"
                        maxLength={6}
                        value={bpOtp}
                        onChange={(e) => setBpOtp(e.target.value.replace(/\D/g, ''))}
                        className="text-center text-2xl tracking-widest font-mono"
                        required
                      />
                    </div>
                    <Button type="submit" className="w-full bg-emerald-500 hover:bg-emerald-600" disabled={loading}>
                      {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                      {loading ? 'Verifying...' : 'Verify OTP & Login'}
                    </Button>
                    <Button 
                      type="button" 
                      variant="ghost" 
                      className="w-full" 
                      onClick={() => { setBpOtpSent(false); setBpOtp(''); }}
                    >
                      <ArrowLeft className="h-4 w-4 mr-2" />
                      Change Email
                    </Button>
                  </form>
                )}
              </div>
            ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <>
                  <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0" />
                    <p className="text-xs text-blue-800 dark:text-blue-200">
                      Registration is restricted to <strong>@smifs.com</strong> email addresses. Password will be sent to your email.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name <span className="text-red-500">*</span></Label>
                    <Input
                      id="name"
                      data-testid="name-input"
                      placeholder="John Doe"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required={!isLogin}
                    />
                  </div>
                  {!isSuperAdmin && (
                    <div className="space-y-2">
                      <Label htmlFor="pan_number">PAN Number <span className="text-red-500">*</span></Label>
                      <Input
                        id="pan_number"
                        data-testid="pan-input"
                        placeholder="ABCDE1234F"
                        maxLength={10}
                        value={formData.pan_number}
                        onChange={(e) => setFormData({ ...formData, pan_number: e.target.value.toUpperCase() })}
                        required={!isLogin && !isSuperAdmin}
                      />
                      <p className="text-xs text-muted-foreground">Required for identity verification</p>
                    </div>
                  )}
                </>
              )}
              <div className="space-y-2">
                <Label htmlFor="email">Email <span className="text-red-500">*</span></Label>
                <Input
                  id="email"
                  data-testid="email-input"
                  type="email"
                  placeholder={isLogin ? "you@example.com" : "you@smifs.com"}
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                />
              </div>
              {isLogin && (
                <div className="space-y-2">
                  <Label htmlFor="password">Password <span className="text-red-500">*</span></Label>
                  <Input
                    id="password"
                    data-testid="password-input"
                    type="password"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                  />
                </div>
              )}
              
              {/* CAPTCHA Section */}
              {isLogin && captchaRequired && (
                <div className="space-y-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-amber-600" />
                    <span className="text-sm font-medium text-amber-800 dark:text-amber-200">Security Verification Required</span>
                  </div>
                  <Label htmlFor="captcha" className="text-amber-800 dark:text-amber-200">
                    {captchaQuestion}
                  </Label>
                  <Input
                    id="captcha"
                    data-testid="captcha-input"
                    type="text"
                    placeholder="Enter your answer"
                    value={captchaAnswer}
                    onChange={(e) => setCaptchaAnswer(e.target.value)}
                    className="bg-white dark:bg-gray-800"
                    required
                  />
                  <p className="text-xs text-amber-600 dark:text-amber-400">
                    Solve the math problem to verify you're human
                  </p>
                </div>
              )}
              
              <Button
                type="submit"
                data-testid="submit-button"
                className="w-full rounded-sm"
                disabled={loading}
              >
                {loading ? 'Please wait...' : isLogin ? 'Sign In' : 'Sign Up'}
              </Button>
              {isLogin && (
                <div className="text-center">
                  <Link
                    to="/forgot-password"
                    className="text-sm text-muted-foreground hover:text-primary transition-colors"
                    data-testid="forgot-password-link"
                  >
                    Forgot your password?
                  </Link>
                </div>
              )}
              
              {/* Microsoft SSO Login */}
              {isLogin && ssoConfig?.enabled && (
                <>
                  <div className="relative my-4">
                    <div className="absolute inset-0 flex items-center">
                      <span className="w-full border-t" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                      <span className="bg-background px-2 text-muted-foreground">
                        Or continue with
                      </span>
                    </div>
                  </div>
                  
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={handleMicrosoftLogin}
                    disabled={ssoLoading}
                    data-testid="microsoft-sso-button"
                  >
                    {ssoLoading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <svg className="mr-2 h-4 w-4" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect x="1" y="1" width="9" height="9" fill="#F25022"/>
                        <rect x="11" y="1" width="9" height="9" fill="#7FBA00"/>
                        <rect x="1" y="11" width="9" height="9" fill="#00A4EF"/>
                        <rect x="11" y="11" width="9" height="9" fill="#FFB900"/>
                      </svg>
                    )}
                    {ssoLoading ? 'Signing in...' : 'Sign in with Microsoft'}
                  </Button>
                </>
              )}
            </form>
            )}
            </>
            )}

            {/* Toggle between Sign In / Sign Up - only for Employee login */}
            {!registrationSuccess && loginType === 'employee' && (
            <div className="mt-4 text-center text-sm">
              <button
                type="button"
                data-testid="toggle-auth-mode"
                onClick={() => {
                  setIsLogin(!isLogin);
                  setFormData({ email: '', password: '', name: '', pan_number: '' });
                }}
                className="text-primary hover:underline"
              >
                {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
              </button>
            </div>
            )}
          </CardContent>
        </Card>
        
        {/* Version and Credit */}
        <div className="mt-6 text-center space-y-1">
          <p className="text-sm text-muted-foreground">
            Version {getFullVersion()}
          </p>
          <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
            <Code className="h-3 w-3" />
            Vive Coding by{' '}
            <span className="text-emerald-600 font-medium">
              Somnath Dey
            </span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
