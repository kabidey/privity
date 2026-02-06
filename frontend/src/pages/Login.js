import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { PublicClientApplication } from '@azure/msal-browser';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import api from '../utils/api';
import { TrendingUp, AlertCircle, Loader2, Building2, Mail, ArrowLeft, Code, Quote, Phone, Play, Sparkles, Shield, Users, BarChart3, Briefcase, Target, Rocket, Award, Globe, Lock, ChevronRight, DollarSign, PieChart, LineChart, Zap } from 'lucide-react';
import { getMsalConfig, getLoginRequest } from '../config/msalConfig';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getFullVersion } from '../version';
import { useDemo } from '../contexts/DemoContext';

const Login = () => {
  const navigate = useNavigate();
  const { enterDemoMode } = useDemo();
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
  
  const [mobileRequired, setMobileRequired] = useState(false);
  const [mobileUpdateNumber, setMobileUpdateNumber] = useState('');
  const [updatingMobile, setUpdatingMobile] = useState(false);
  
  const [captchaRequired, setCaptchaRequired] = useState(false);
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaQuestion, setCaptchaQuestion] = useState('');
  const [captchaAnswer, setCaptchaAnswer] = useState('');

  // Extended Private Equity Quotes - SMIFS PE Mantras
  const peQuotes = [
    { quote: "Private equity is the art of patient capital.", author: "SMIFS PE", icon: Target },
    { quote: "Public markets rent shares; private equity buys ownership.", author: "SMIFS PE", icon: Building2 },
    { quote: "We don't buy tickers; we buy businesses.", author: "SMIFS PE", icon: Briefcase },
    { quote: "Liquidity is a luxury; illiquidity is a strategy.", author: "SMIFS PE", icon: Shield },
    { quote: "In private markets, time is a tool, not a constraint.", author: "SMIFS PE", icon: TrendingUp },
    { quote: "Volatility is the price of liquidity; stability is the reward of the lock-in.", author: "SMIFS PE", icon: LineChart },
    { quote: "True value is created in the dark, away from the daily ticker.", author: "SMIFS PE", icon: Sparkles },
    { quote: "Private equity doesn't predict the future; it engineers it.", author: "SMIFS PE", icon: Rocket },
    { quote: "You cannot fix a company while checking its stock price every minute.", author: "SMIFS PE", icon: Target },
    { quote: "Public markets react; private markets act.", author: "SMIFS PE", icon: Zap },
    { quote: "The illiquidity premium is the payment for patience.", author: "SMIFS PE", icon: DollarSign },
    { quote: "Alpha is found where the spotlight isn't shining.", author: "SMIFS PE", icon: Award },
    { quote: "Efficient markets are for saving; inefficient markets are for earning.", author: "SMIFS PE", icon: PieChart },
    { quote: "Wealth is built in private; it is merely revealed in public.", author: "SMIFS PE", icon: Globe },
    { quote: "Price is what you pay; structure is how you protect it.", author: "SMIFS PE", icon: Shield },
    { quote: "You make your profit on the buy, you realize it on the sell.", author: "SMIFS PE", icon: TrendingUp },
    { quote: "Valuation is an opinion; cash flow is a fact.", author: "SMIFS PE", icon: BarChart3 },
    { quote: "Don't catch falling knives; buy the floor.", author: "SMIFS PE", icon: Target },
    { quote: "A great company at a bad price is a bad investment.", author: "SMIFS PE", icon: DollarSign },
    { quote: "Due diligence is the art of asking the question nobody wants to answer.", author: "SMIFS PE", icon: Shield },
    { quote: "Growth covers mistakes; leverage magnifies them.", author: "SMIFS PE", icon: LineChart },
    { quote: "Buy the complexity, sell the simplicity.", author: "SMIFS PE", icon: Sparkles },
    { quote: "The best deals are often the hardest to close.", author: "SMIFS PE", icon: Award },
    { quote: "Cynicism protects capital; optimism grows it.", author: "SMIFS PE", icon: Shield },
    { quote: "Entry multiple is destiny.", author: "SMIFS PE", icon: Target },
    { quote: "Leverage is a good servant but a terrible master.", author: "SMIFS PE", icon: BarChart3 },
    { quote: "Never fall in love with the deal; fall in love with the economics.", author: "SMIFS PE", icon: DollarSign },
    { quote: "Risk comes from not knowing what you are doing.", author: "SMIFS PE", icon: Shield },
    { quote: "In PE, 'cheap' is expensive if it can't be fixed.", author: "SMIFS PE", icon: Briefcase },
    { quote: "Bet on the jockey, not just the horse.", author: "SMIFS PE", icon: Rocket },
    { quote: "Financial engineering is a tactic; operational improvement is a strategy.", author: "SMIFS PE", icon: Target },
    { quote: "Alignment of interest is the most powerful force in finance.", author: "SMIFS PE", icon: Users },
    { quote: "Skin in the game changes the game.", author: "SMIFS PE", icon: Zap },
    { quote: "A spreadsheet cannot manage a workforce.", author: "SMIFS PE", icon: Users },
    { quote: "Change is hard in public; it is essential in private.", author: "SMIFS PE", icon: Rocket },
    { quote: "Hope is not a strategy; execution is.", author: "SMIFS PE", icon: Target },
    { quote: "EBITDA is an opinion; Free Cash Flow is reality.", author: "SMIFS PE", icon: DollarSign },
    { quote: "Transformation requires a runway, not a tightrope.", author: "SMIFS PE", icon: Rocket },
    { quote: "Strong boards don't just monitor; they mentor.", author: "SMIFS PE", icon: Users },
    { quote: "Cost cutting buys you time; revenue growth buys you a future.", author: "SMIFS PE", icon: TrendingUp },
    { quote: "Culture eats strategy for breakfast, even in a leveraged buyout.", author: "SMIFS PE", icon: Award },
    { quote: "Turnarounds don't happen in a straight line.", author: "SMIFS PE", icon: LineChart },
    { quote: "The goal is not to be bigger; the goal is to be better.", author: "SMIFS PE", icon: Target },
    { quote: "Incentives dictate behavior; get the cap table right.", author: "SMIFS PE", icon: PieChart },
    { quote: "If you aren't growing, you're dying—slowly.", author: "SMIFS PE", icon: TrendingUp },
    { quote: "Scale breaks systems; fix the system before you scale.", author: "SMIFS PE", icon: Shield },
    { quote: "M&A is like marriage: easy to get into, expensive to get out of.", author: "SMIFS PE", icon: Briefcase },
    { quote: "Synergies are easy to model but hard to capture.", author: "SMIFS PE", icon: BarChart3 },
    { quote: "Bolt-ons are the unsung heroes of multiple expansion.", author: "SMIFS PE", icon: Rocket },
    { quote: "Organic growth proves the concept; inorganic growth proves the platform.", author: "SMIFS PE", icon: TrendingUp },
    { quote: "Focus on the core; outsource the noise.", author: "SMIFS PE", icon: Target },
    { quote: "Revenue is vanity, profit is sanity, cash is king.", author: "SMIFS PE", icon: DollarSign },
    { quote: "A platform is worth more than the sum of its parts.", author: "SMIFS PE", icon: Globe },
    { quote: "Don't just capture market share; create market value.", author: "SMIFS PE", icon: TrendingUp },
    { quote: "Every entry must have an exit strategy.", author: "SMIFS PE", icon: Target },
    { quote: "You don't sell when you want to; you sell when the market wants to buy.", author: "SMIFS PE", icon: BarChart3 },
    { quote: "IPOs are a branding event; strategic sales are a synergy event.", author: "SMIFS PE", icon: Award },
    { quote: "Multiple expansion is luck; earnings growth is skill.", author: "SMIFS PE", icon: LineChart },
    { quote: "The J-Curve is steep, but the view from the top is worth it.", author: "SMIFS PE", icon: TrendingUp },
    { quote: "Leaving money on the table is better than holding the bag.", author: "SMIFS PE", icon: DollarSign },
    { quote: "An exit is not the end; it's the validation of the thesis.", author: "SMIFS PE", icon: Award },
    { quote: "Returns are realized in cash, not in mark-to-market reports.", author: "SMIFS PE", icon: DollarSign },
    { quote: "Don't wait for the perfect exit; look for the good one.", author: "SMIFS PE", icon: Target },
    { quote: "A great exit makes you forget the hard years.", author: "SMIFS PE", icon: Sparkles },
    { quote: "Capital goes where it is welcome and stays where it is well treated.", author: "SMIFS PE", icon: Globe },
    { quote: "Reputation takes twenty years to build and five minutes to ruin.", author: "SMIFS PE", icon: Shield },
    { quote: "In the long run, the fundamentals always win.", author: "SMIFS PE", icon: TrendingUp },
    { quote: "Private Equity: Fueling the real economy.", author: "SMIFS PE", icon: Rocket },
    { quote: "We don't just manage wealth; we steward potential.", author: "SMIFS PE", icon: Sparkles },
  ];

  // Typewriter animation state
  const [displayedText, setDisplayedText] = useState('');
  const [currentQuoteIndex, setCurrentQuoteIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(true);
  const [showCursor, setShowCursor] = useState(true);

  // Typewriter effect
  useEffect(() => {
    const quote = peQuotes[currentQuoteIndex].quote;
    let charIndex = 0;
    let timeoutId;
    
    if (isTyping) {
      const typeChar = () => {
        if (charIndex <= quote.length) {
          setDisplayedText(quote.slice(0, charIndex));
          charIndex++;
          timeoutId = setTimeout(typeChar, 50);
        } else {
          setTimeout(() => {
            setIsTyping(false);
          }, 3000);
        }
      };
      typeChar();
    } else {
      const eraseChar = () => {
        if (charIndex > 0) {
          charIndex--;
          setDisplayedText(quote.slice(0, charIndex));
          timeoutId = setTimeout(eraseChar, 30);
        } else {
          setCurrentQuoteIndex((prev) => (prev + 1) % peQuotes.length);
          setIsTyping(true);
        }
      };
      charIndex = quote.length;
      eraseChar();
    }
    
    return () => clearTimeout(timeoutId);
  }, [currentQuoteIndex, isTyping]);

  // Cursor blink effect
  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 530);
    return () => clearInterval(cursorInterval);
  }, []);

  // Fetch SSO config on mount
  useEffect(() => {
    const fetchSsoConfig = async () => {
      try {
        const response = await api.get('/auth/sso/config');
        setSsoConfig(response.data);
        
        if (response.data?.enabled) {
          const msalConfig = getMsalConfig(response.data);
          const msal = new PublicClientApplication(msalConfig);
          await msal.initialize();
          setMsalInstance(msal);
        }
      } catch (error) {
        console.log('SSO not configured');
      }
    };
    fetchSsoConfig();
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
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
        await api.post('/auth/register', {
          email: formData.email,
          password: formData.password,
          name: formData.name,
          pan_number: formData.pan_number,
        });
        setRegistrationSuccess(true);
        setRegisteredEmail(formData.email);
        toast.success('Registration submitted! Awaiting approval.');
      }
    } catch (error) {
      console.error('Login error:', error);
      const errorResponse = error.response?.data;
      const errorDetail = errorResponse?.detail;
      
      const isCaptchaRequired = 
        error.response?.status === 428 || 
        (typeof errorDetail === 'object' && errorDetail?.captcha_required);
      
      if (isCaptchaRequired) {
        const captchaData = typeof errorDetail === 'object' ? errorDetail : {};
        setCaptchaRequired(true);
        setCaptchaToken(captchaData?.captcha_token || '');
        setCaptchaQuestion(captchaData?.captcha_question || '');
        toast.warning('Please answer the security question');
      } else {
        let message = 'An error occurred';
        if (typeof errorDetail === 'string') {
          message = errorDetail;
        } else if (errorDetail?.message) {
          message = errorDetail.message;
        } else if (error.response?.status === 0 || error.code === 'ERR_NETWORK') {
          message = 'Network error. Please check your connection.';
        } else if (error.response?.status === 500) {
          message = 'Server error. Please try again later.';
        }
        toast.error(message);
      }
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
      await api.put('/auth/update-mobile', { mobile: mobileUpdateNumber });
      toast.success('Mobile number updated successfully!');
      setMobileRequired(false);
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update mobile number');
    } finally {
      setUpdatingMobile(false);
    }
  };

  const handleSsoLogin = async () => {
    if (!msalInstance || !ssoConfig) {
      toast.error('SSO is not configured');
      return;
    }
    
    setSsoLoading(true);
    try {
      const loginRequest = getLoginRequest(ssoConfig);
      const response = await msalInstance.loginPopup(loginRequest);
      
      const ssoResponse = await api.post('/auth/sso/callback', {
        access_token: response.accessToken,
        id_token: response.idToken,
      });
      
      const { token, user } = ssoResponse.data;
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      toast.success('SSO Login successful!');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'SSO login failed');
    } finally {
      setSsoLoading(false);
    }
  };

  const handleBpOtpRequest = async () => {
    if (!formData.mobile_number || formData.mobile_number.length !== 10) {
      toast.error('Please enter a valid 10-digit mobile number');
      return;
    }
    
    setLoading(true);
    try {
      await api.post('/auth/bp-otp/request', { mobile: formData.mobile_number });
      setBpOtpSent(true);
      toast.success('OTP sent to your mobile number');
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
      const response = await api.post('/auth/bp-otp/verify', {
        mobile: formData.mobile_number,
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

  const handleDemoMode = async () => {
    setDemoLoading(true);
    try {
      await enterDemoMode();
      toast.success('Demo mode activated!');
      navigate('/');
    } catch (error) {
      toast.error('Failed to enter demo mode');
    } finally {
      setDemoLoading(false);
    }
  };

  const CurrentIcon = peQuotes[currentQuoteIndex].icon;

  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-slate-950 via-emerald-950 to-slate-900">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Floating orbs */}
        <div className="absolute top-20 left-10 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-pulse" style={{animationDelay: '1s'}}></div>
        <div className="absolute top-1/2 left-1/3 w-64 h-64 bg-green-500/5 rounded-full blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
        
        {/* Grid pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(16,185,129,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.03)_1px,transparent_1px)] bg-[size:60px_60px]"></div>
        
        {/* Floating icons - Private Equity mantras */}
        <div className="absolute top-[15%] left-[8%] animate-float" style={{animationDelay: '0s'}}>
          <div className="bg-gradient-to-br from-emerald-500/20 to-teal-500/20 p-4 rounded-2xl backdrop-blur-sm border border-emerald-500/20">
            <TrendingUp className="w-8 h-8 text-emerald-400" />
          </div>
          <p className="text-emerald-400/60 text-xs mt-2 text-center font-medium">GROWTH</p>
        </div>
        
        <div className="absolute top-[25%] right-[12%] animate-float" style={{animationDelay: '0.5s'}}>
          <div className="bg-gradient-to-br from-teal-500/20 to-cyan-500/20 p-4 rounded-2xl backdrop-blur-sm border border-teal-500/20">
            <Shield className="w-8 h-8 text-teal-400" />
          </div>
          <p className="text-teal-400/60 text-xs mt-2 text-center font-medium">TRUST</p>
        </div>
        
        <div className="absolute top-[45%] left-[5%] animate-float" style={{animationDelay: '1s'}}>
          <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 p-4 rounded-2xl backdrop-blur-sm border border-green-500/20">
            <Target className="w-8 h-8 text-green-400" />
          </div>
          <p className="text-green-400/60 text-xs mt-2 text-center font-medium">PRECISION</p>
        </div>
        
        <div className="absolute top-[55%] right-[8%] animate-float" style={{animationDelay: '1.5s'}}>
          <div className="bg-gradient-to-br from-emerald-500/20 to-green-500/20 p-4 rounded-2xl backdrop-blur-sm border border-emerald-500/20">
            <Rocket className="w-8 h-8 text-emerald-400" />
          </div>
          <p className="text-emerald-400/60 text-xs mt-2 text-center font-medium">MOMENTUM</p>
        </div>
        
        <div className="absolute bottom-[25%] left-[10%] animate-float" style={{animationDelay: '2s'}}>
          <div className="bg-gradient-to-br from-cyan-500/20 to-teal-500/20 p-4 rounded-2xl backdrop-blur-sm border border-cyan-500/20">
            <Award className="w-8 h-8 text-cyan-400" />
          </div>
          <p className="text-cyan-400/60 text-xs mt-2 text-center font-medium">EXCELLENCE</p>
        </div>
        
        <div className="absolute bottom-[30%] right-[15%] animate-float" style={{animationDelay: '2.5s'}}>
          <div className="bg-gradient-to-br from-teal-500/20 to-emerald-500/20 p-4 rounded-2xl backdrop-blur-sm border border-teal-500/20">
            <Globe className="w-8 h-8 text-teal-400" />
          </div>
          <p className="text-teal-400/60 text-xs mt-2 text-center font-medium">GLOBAL</p>
        </div>
        
        <div className="absolute top-[70%] left-[20%] animate-float" style={{animationDelay: '3s'}}>
          <div className="bg-gradient-to-br from-green-500/20 to-cyan-500/20 p-4 rounded-2xl backdrop-blur-sm border border-green-500/20">
            <BarChart3 className="w-8 h-8 text-green-400" />
          </div>
          <p className="text-green-400/60 text-xs mt-2 text-center font-medium">ANALYTICS</p>
        </div>
        
        <div className="absolute top-[10%] left-[40%] animate-float" style={{animationDelay: '1.2s'}}>
          <div className="bg-gradient-to-br from-emerald-500/20 to-teal-500/20 p-4 rounded-2xl backdrop-blur-sm border border-emerald-500/20">
            <DollarSign className="w-8 h-8 text-emerald-400" />
          </div>
          <p className="text-emerald-400/60 text-xs mt-2 text-center font-medium">WEALTH</p>
        </div>
        
        <div className="absolute bottom-[15%] right-[35%] animate-float" style={{animationDelay: '0.8s'}}>
          <div className="bg-gradient-to-br from-teal-500/20 to-green-500/20 p-4 rounded-2xl backdrop-blur-sm border border-teal-500/20">
            <Briefcase className="w-8 h-8 text-teal-400" />
          </div>
          <p className="text-teal-400/60 text-xs mt-2 text-center font-medium">EXPERTISE</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 min-h-screen flex flex-col items-center justify-center px-4 py-8">
        {/* Top Logo */}
        <div className="mb-6 animate-fade-in">
          <div className="bg-white/95 rounded-2xl p-4 shadow-2xl shadow-emerald-500/20 backdrop-blur-sm">
            <img 
              src="https://customer-assets.emergentagent.com/job_8c5c41a7-4474-44d9-8a72-5476f60329b4/artifacts/eineo77y_SMIFS%20%26%20PRIVITY%20Logo.png" 
              alt="SMIFS & Privity Logo" 
              className="h-12 w-auto"
              data-testid="smifs-privity-logo"
            />
          </div>
        </div>

        {/* Typewriter Quote Section */}
        <div className="mb-8 text-center max-w-2xl animate-fade-in" style={{animationDelay: '0.2s'}}>
          <div className="flex justify-center mb-4">
            <div className="p-3 rounded-full bg-gradient-to-br from-emerald-500/30 to-teal-500/30 backdrop-blur-sm border border-emerald-500/30">
              <CurrentIcon className="w-6 h-6 text-emerald-400" />
            </div>
          </div>
          <div className="min-h-[80px] flex items-center justify-center">
            <blockquote className="text-xl md:text-2xl font-light text-white/90 leading-relaxed" data-testid="typewriter-quote">
              &ldquo;{displayedText}
              <span className={`inline-block w-0.5 h-6 bg-emerald-400 ml-1 ${showCursor ? 'opacity-100' : 'opacity-0'}`}></span>&rdquo;
            </blockquote>
          </div>
          <cite className="text-emerald-400/80 text-sm mt-3 block font-medium">
            — {peQuotes[currentQuoteIndex].author}
          </cite>
        </div>

        {/* Login Card */}
        <div className="w-full max-w-md animate-fade-in" style={{animationDelay: '0.4s'}}>
          <Card className="bg-white/10 backdrop-blur-xl border-white/20 shadow-2xl shadow-black/20" data-testid="login-card">
            <CardHeader className="space-y-1 pb-4">
              <div className="flex items-center justify-center gap-2 mb-2">
                <div className="h-1 w-12 bg-gradient-to-r from-transparent to-emerald-500 rounded-full"></div>
                <Sparkles className="w-5 h-5 text-emerald-400" />
                <div className="h-1 w-12 bg-gradient-to-l from-transparent to-emerald-500 rounded-full"></div>
              </div>
              <CardTitle className="text-2xl font-bold text-center text-white">
                {isLogin ? 'Welcome Back' : 'Join Privity'}
              </CardTitle>
              <CardDescription className="text-center text-white/60">
                {isLogin ? 'Enter your credentials to access PE opportunities' : 'Start your private equity journey today'}
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {/* Registration Success */}
              {registrationSuccess ? (
                <div className="space-y-4">
                  <div className="p-4 bg-emerald-500/20 border border-emerald-500/30 rounded-xl">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-emerald-500/30 rounded-full">
                        <Mail className="w-5 h-5 text-emerald-400" />
                      </div>
                      <div>
                        <p className="font-medium text-white">Registration Submitted!</p>
                        <p className="text-sm text-white/60">Your request for {registeredEmail} is pending approval.</p>
                      </div>
                    </div>
                  </div>
                  <Button 
                    onClick={() => { setRegistrationSuccess(false); setIsLogin(true); }}
                    className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white"
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" /> Back to Login
                  </Button>
                </div>
              ) : mobileRequired ? (
                <div className="space-y-4">
                  <div className="p-4 bg-amber-500/20 border border-amber-500/30 rounded-xl">
                    <div className="flex items-center gap-3">
                      <Phone className="w-5 h-5 text-amber-400" />
                      <p className="text-white/80 text-sm">Please update your mobile number to continue</p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-white/80">Mobile Number</Label>
                    <Input
                      type="tel"
                      placeholder="Enter 10-digit mobile number"
                      value={mobileUpdateNumber}
                      onChange={(e) => setMobileUpdateNumber(e.target.value.replace(/\D/g, '').slice(0, 10))}
                      className="bg-white/10 border-white/20 text-white placeholder:text-white/40"
                      data-testid="mobile-update-input"
                    />
                  </div>
                  <Button 
                    onClick={handleMobileUpdate} 
                    disabled={updatingMobile}
                    className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600"
                  >
                    {updatingMobile ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                    Update & Continue
                  </Button>
                </div>
              ) : (
                <>
                  {/* Login Type Tabs */}
                  {isLogin && (
                    <Tabs value={loginType} onValueChange={setLoginType} className="mb-4">
                      <TabsList className="grid w-full grid-cols-2 bg-white/10">
                        <TabsTrigger value="employee" className="data-[state=active]:bg-emerald-500 data-[state=active]:text-white text-white/60">
                          <Building2 className="w-4 h-4 mr-2" /> Employee
                        </TabsTrigger>
                        <TabsTrigger value="partner" className="data-[state=active]:bg-emerald-500 data-[state=active]:text-white text-white/60">
                          <Users className="w-4 h-4 mr-2" /> Partner
                        </TabsTrigger>
                      </TabsList>
                    </Tabs>
                  )}

                  {/* Employee Login Form */}
                  {loginType === 'employee' && (
                    <form onSubmit={handleSubmit} className="space-y-4">
                      <div className="space-y-2">
                        <Label className="text-white/80">Email</Label>
                        <Input
                          type="email"
                          name="email"
                          placeholder="you@company.com"
                          value={formData.email}
                          onChange={handleChange}
                          required
                          className="bg-white/10 border-white/20 text-white placeholder:text-white/40 focus:border-emerald-500 focus:ring-emerald-500/20"
                          data-testid="email-input"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label className="text-white/80">Password</Label>
                        <Input
                          type="password"
                          name="password"
                          placeholder="••••••••"
                          value={formData.password}
                          onChange={handleChange}
                          required
                          className="bg-white/10 border-white/20 text-white placeholder:text-white/40 focus:border-emerald-500 focus:ring-emerald-500/20"
                          data-testid="password-input"
                        />
                      </div>
                      
                      {!isLogin && (
                        <>
                          <div className="space-y-2">
                            <Label className="text-white/80">Full Name</Label>
                            <Input
                              type="text"
                              name="name"
                              placeholder="Your full name"
                              value={formData.name}
                              onChange={handleChange}
                              required
                              className="bg-white/10 border-white/20 text-white placeholder:text-white/40"
                              data-testid="name-input"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-white/80">PAN Number</Label>
                            <Input
                              type="text"
                              name="pan_number"
                              placeholder="ABCDE1234F"
                              value={formData.pan_number}
                              onChange={(e) => setFormData({...formData, pan_number: e.target.value.toUpperCase()})}
                              maxLength={10}
                              className="bg-white/10 border-white/20 text-white placeholder:text-white/40 font-mono"
                              data-testid="pan-input"
                            />
                          </div>
                        </>
                      )}
                      
                      {/* CAPTCHA */}
                      {captchaRequired && (
                        <div className="space-y-2 p-3 bg-amber-500/20 border border-amber-500/30 rounded-xl">
                          <Label className="text-amber-300 flex items-center gap-2">
                            <AlertCircle className="w-4 h-4" /> Security Question
                          </Label>
                          <p className="text-white/80 text-sm">{captchaQuestion}</p>
                          <Input
                            type="text"
                            placeholder="Your answer"
                            value={captchaAnswer}
                            onChange={(e) => setCaptchaAnswer(e.target.value)}
                            className="bg-white/10 border-white/20 text-white"
                            data-testid="captcha-answer"
                          />
                        </div>
                      )}
                      
                      <Button 
                        type="submit" 
                        disabled={loading}
                        className="w-full h-12 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-semibold text-base shadow-lg shadow-emerald-500/25 transition-all duration-300 hover:shadow-emerald-500/40 hover:scale-[1.02]"
                        data-testid="submit-btn"
                      >
                        {loading ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <>
                            {isLogin ? 'Sign In' : 'Create Account'}
                            <ChevronRight className="w-5 h-5 ml-2" />
                          </>
                        )}
                      </Button>
                    </form>
                  )}

                  {/* Partner OTP Login */}
                  {loginType === 'partner' && isLogin && (
                    <div className="space-y-4">
                      {!bpOtpSent ? (
                        <>
                          <div className="space-y-2">
                            <Label className="text-white/80">Registered Mobile Number</Label>
                            <Input
                              type="tel"
                              placeholder="10-digit mobile number"
                              value={formData.mobile_number}
                              onChange={(e) => setFormData({...formData, mobile_number: e.target.value.replace(/\D/g, '').slice(0, 10)})}
                              className="bg-white/10 border-white/20 text-white placeholder:text-white/40"
                              data-testid="bp-mobile-input"
                            />
                          </div>
                          <Button 
                            onClick={handleBpOtpRequest}
                            disabled={loading}
                            className="w-full h-12 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600"
                          >
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Send OTP'}
                          </Button>
                        </>
                      ) : (
                        <>
                          <div className="p-3 bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-center">
                            <p className="text-emerald-300 text-sm">OTP sent to {formData.mobile_number}</p>
                          </div>
                          <div className="space-y-2">
                            <Label className="text-white/80">Enter OTP</Label>
                            <Input
                              type="text"
                              placeholder="6-digit OTP"
                              value={bpOtp}
                              onChange={(e) => setBpOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                              maxLength={6}
                              className="bg-white/10 border-white/20 text-white placeholder:text-white/40 text-center text-xl tracking-widest font-mono"
                              data-testid="bp-otp-input"
                            />
                          </div>
                          <Button 
                            onClick={handleBpOtpVerify}
                            disabled={loading}
                            className="w-full h-12 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600"
                          >
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Verify & Login'}
                          </Button>
                          <Button 
                            variant="ghost" 
                            onClick={() => setBpOtpSent(false)}
                            className="w-full text-white/60 hover:text-white hover:bg-white/10"
                          >
                            <ArrowLeft className="w-4 h-4 mr-2" /> Change Number
                          </Button>
                        </>
                      )}
                    </div>
                  )}

                  {/* SSO Login */}
                  {ssoConfig?.enabled && isLogin && loginType === 'employee' && (
                    <>
                      <div className="relative my-4">
                        <div className="absolute inset-0 flex items-center">
                          <span className="w-full border-t border-white/20"></span>
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                          <span className="bg-transparent px-2 text-white/40">Or continue with</span>
                        </div>
                      </div>
                      <Button 
                        type="button" 
                        variant="outline" 
                        onClick={handleSsoLogin}
                        disabled={ssoLoading}
                        className="w-full border-white/20 text-white hover:bg-white/10"
                      >
                        {ssoLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Building2 className="w-4 h-4 mr-2" />}
                        Microsoft SSO
                      </Button>
                    </>
                  )}

                  {/* Toggle Login/Register */}
                  {loginType === 'employee' && (
                    <div className="text-center pt-2">
                      <button 
                        type="button"
                        onClick={() => setIsLogin(!isLogin)}
                        className="text-emerald-400 hover:text-emerald-300 text-sm font-medium transition-colors"
                        data-testid="toggle-auth"
                      >
                        {isLogin ? "Don't have an account? Register" : "Already have an account? Sign in"}
                      </button>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Demo Mode Button */}
          <div className="mt-4 text-center">
            <Button
              variant="ghost"
              onClick={handleDemoMode}
              disabled={demoLoading}
              className="text-white/50 hover:text-white hover:bg-white/10"
              data-testid="demo-mode-btn"
            >
              {demoLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Play className="w-4 h-4 mr-2" />}
              Try Demo Mode
            </Button>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center animate-fade-in" style={{animationDelay: '0.6s'}}>
          <p className="text-white/40 text-xs">
            © 2026 SMIFS Private Equity. All rights reserved.
          </p>
          <p className="text-white/30 text-xs mt-1">
            Powered by Privity | v{getFullVersion()}
          </p>
        </div>
      </div>

      {/* Custom CSS for animations */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-20px) rotate(5deg); }
        }
        
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        .animate-float {
          animation: float 6s ease-in-out infinite;
        }
        
        .animate-fade-in {
          animation: fade-in 0.8s ease-out forwards;
        }
      `}</style>
    </div>
  );
};

export default Login;
