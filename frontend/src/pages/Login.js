import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { PublicClientApplication } from '@azure/msal-browser';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import api from '../utils/api';
import { TrendingUp, AlertCircle, Loader2, Building2, Mail, ArrowLeft, Phone, Play, Sparkles, Shield, Users, BarChart3, Briefcase, Target, Rocket, Award, Globe, ChevronRight, DollarSign, PieChart, LineChart, Zap, Gem, Crown, Coins, Landmark, Scale, Timer, Eye, Lock, Key, Compass, Anchor, Flame, Star, Heart, Diamond, Layers, Box, Gift, Lightbulb, Brain, Cpu, Database, Server, Cloud, Wifi, Activity, Percent, Hash, AtSign, Command, Terminal, Code, FileText, Folder, Archive, Package, Truck, ShoppingCart, CreditCard, Wallet, PiggyBank, Banknote, Receipt, Calculator, ClipboardList, FileCheck, FilePlus, FileSearch, Search, Filter, SlidersHorizontal, Settings, Wrench, Tool, Hammer, Scissors, Paintbrush, Palette, Image, Camera, Video, Music, Headphones, Speaker, Mic, Radio, Tv, Monitor, Smartphone, Tablet, Watch, Battery, Power, Plug, Usb, HardDrive, Save, Download, Upload, Share, Send, MessageSquare, MessageCircle, Bell, BellRing, AlertTriangle, Info, HelpCircle, CheckCircle, XCircle, MinusCircle, PlusCircle, Plus, Minus, X, Check, RefreshCw, RotateCw, RotateCcw, Repeat, Shuffle, FastForward, Rewind, SkipForward, SkipBack, Pause, Square, Circle, Triangle, Pentagon, Hexagon, Octagon, ArrowUp, ArrowDown, ArrowRight, ChevronUp, ChevronDown, ChevronLeft, ChevronsUp, ChevronsDown, ChevronsLeft, ChevronsRight, MoveUp, MoveDown, MoveLeft, MoveRight, Maximize, Minimize, Expand, Shrink, ZoomIn, ZoomOut, Move, Crosshair, Navigation, Map, MapPin, Flag, Bookmark, Tag, Tags, Ticket, Calendar, Clock, Hourglass, Sun, Moon, CloudSun, CloudMoon, CloudRain, CloudSnow, CloudLightning, Wind, Droplet, Droplets, Umbrella, Thermometer, Flame as Fire, Snowflake, Leaf, Tree, Flower, Sprout, Apple, Cherry, Grape, Lemon, Banana, Carrot, Cookie, Pizza, Coffee, Wine, Beer, Utensils, ChefHat, Soup, Egg, Milk, Cake, IceCream, Candy, Popcorn } from 'lucide-react';
import { getMsalConfig, getLoginRequest } from '../config/msalConfig';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getFullVersion } from '../version';
import { useDemo } from '../contexts/DemoContext';
import useContentProtection from '../hooks/useContentProtection';

const Login = () => {
  const navigate = useNavigate();
  const { enterDemoMode } = useDemo();
  
  // Enable content protection
  useContentProtection();
  
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
  
  // OTP Registration Flow States
  const [registrationStep, setRegistrationStep] = useState('form'); // 'form' | 'otp'
  const [registrationOtp, setRegistrationOtp] = useState('');
  const [resendingOtp, setResendingOtp] = useState(false);
  const [otpTimer, setOtpTimer] = useState(0);
  
  // Error display state
  const [formError, setFormError] = useState('');

  // All 69 SMIFS PE Quotes - Memoized to avoid re-renders
  const allQuotes = useMemo(() => [
    "Private equity is the art of patient capital.",
    "Public markets rent shares; private equity buys ownership.",
    "We don't buy tickers; we buy businesses.",
    "Liquidity is a luxury; illiquidity is a strategy.",
    "In private markets, time is a tool, not a constraint.",
    "Volatility is the price of liquidity; stability is the reward of the lock-in.",
    "True value is created in the dark, away from the daily ticker.",
    "Private equity doesn't predict the future; it engineers it.",
    "You cannot fix a company while checking its stock price every minute.",
    "Public markets react; private markets act.",
    "The illiquidity premium is the payment for patience.",
    "Alpha is found where the spotlight isn't shining.",
    "Efficient markets are for saving; inefficient markets are for earning.",
    "Wealth is built in private; it is merely revealed in public.",
    "Price is what you pay; structure is how you protect it.",
    "You make your profit on the buy, you realize it on the sell.",
    "Valuation is an opinion; cash flow is a fact.",
    "Don't catch falling knives; buy the floor.",
    "A great company at a bad price is a bad investment.",
    "Due diligence is the art of asking the question nobody wants to answer.",
    "Growth covers mistakes; leverage magnifies them.",
    "Buy the complexity, sell the simplicity.",
    "The best deals are often the hardest to close.",
    "Cynicism protects capital; optimism grows it.",
    "Entry multiple is destiny.",
    "Leverage is a good servant but a terrible master.",
    "Never fall in love with the deal; fall in love with the economics.",
    "Risk comes from not knowing what you are doing.",
    "In PE, 'cheap' is expensive if it can't be fixed.",
    "Bet on the jockey, not just the horse.",
    "Financial engineering is a tactic; operational improvement is a strategy.",
    "Alignment of interest is the most powerful force in finance.",
    "Skin in the game changes the game.",
    "A spreadsheet cannot manage a workforce.",
    "Change is hard in public; it is essential in private.",
    "Hope is not a strategy; execution is.",
    "EBITDA is an opinion; Free Cash Flow is reality.",
    "Transformation requires a runway, not a tightrope.",
    "Strong boards don't just monitor; they mentor.",
    "Cost cutting buys you time; revenue growth buys you a future.",
    "Culture eats strategy for breakfast, even in a leveraged buyout.",
    "Turnarounds don't happen in a straight line.",
    "The goal is not to be bigger; the goal is to be better.",
    "Incentives dictate behavior; get the cap table right.",
    "If you aren't growing, you're dying—slowly.",
    "Scale breaks systems; fix the system before you scale.",
    "M&A is like marriage: easy to get into, expensive to get out of.",
    "Synergies are easy to model but hard to capture.",
    "Bolt-ons are the unsung heroes of multiple expansion.",
    "Organic growth proves the concept; inorganic growth proves the platform.",
    "Focus on the core; outsource the noise.",
    "Revenue is vanity, profit is sanity, cash is king.",
    "A platform is worth more than the sum of its parts.",
    "Don't just capture market share; create market value.",
    "Every entry must have an exit strategy.",
    "You don't sell when you want to; you sell when the market wants to buy.",
    "IPOs are a branding event; strategic sales are a synergy event.",
    "Multiple expansion is luck; earnings growth is skill.",
    "The J-Curve is steep, but the view from the top is worth it.",
    "Leaving money on the table is better than holding the bag.",
    "An exit is not the end; it's the validation of the thesis.",
    "Returns are realized in cash, not in mark-to-market reports.",
    "Don't wait for the perfect exit; look for the good one.",
    "A great exit makes you forget the hard years.",
    "Capital goes where it is welcome and stays where it is well treated.",
    "Reputation takes twenty years to build and five minutes to ruin.",
    "In the long run, the fundamentals always win.",
    "Private Equity: Fueling the real economy.",
    "We don't just manage wealth; we steward potential.",
  ], []);

  // Keywords extracted from quotes for floating icons - expanded list
  const floatingKeywords = useMemo(() => [
    { word: "CAPITAL", icon: DollarSign },
    { word: "OWNERSHIP", icon: Key },
    { word: "BUSINESS", icon: Briefcase },
    { word: "STRATEGY", icon: Target },
    { word: "VALUE", icon: Gem },
    { word: "PATIENCE", icon: Timer },
    { word: "GROWTH", icon: TrendingUp },
    { word: "ALPHA", icon: Crown },
    { word: "WEALTH", icon: Coins },
    { word: "CASH FLOW", icon: Banknote },
    { word: "LEVERAGE", icon: Scale },
    { word: "RISK", icon: Shield },
    { word: "EXECUTION", icon: Rocket },
    { word: "CULTURE", icon: Users },
    { word: "SYNERGY", icon: Layers },
    { word: "PLATFORM", icon: Globe },
    { word: "EXIT", icon: Award },
    { word: "RETURNS", icon: PieChart },
    { word: "FUNDAMENTALS", icon: Landmark },
    { word: "POTENTIAL", icon: Sparkles },
    { word: "DILIGENCE", icon: Search },
    { word: "ECONOMICS", icon: BarChart3 },
    { word: "PROFIT", icon: LineChart },
    { word: "ALIGNMENT", icon: Compass },
    { word: "TRANSFORM", icon: Zap },
    { word: "MENTOR", icon: Brain },
    { word: "REVENUE", icon: Activity },
    { word: "SCALE", icon: Maximize },
    { word: "M&A", icon: Layers },
    { word: "MARKET", icon: Globe },
    // Additional keywords from quotes
    { word: "LIQUIDITY", icon: Droplet },
    { word: "STABILITY", icon: Anchor },
    { word: "VOLATILITY", icon: Activity },
    { word: "EQUITY", icon: PieChart },
    { word: "INVESTMENT", icon: Wallet },
    { word: "PORTFOLIO", icon: Folder },
    { word: "THESIS", icon: FileText },
    { word: "BUYOUT", icon: ShoppingCart },
    { word: "IPO", icon: Rocket },
    { word: "EARNINGS", icon: Calculator },
    { word: "J-CURVE", icon: LineChart },
    { word: "CAP TABLE", icon: ClipboardList },
    { word: "DUE DILIG", icon: FileSearch },
    { word: "EBITDA", icon: Hash },
    { word: "MULTIPLE", icon: Percent },
    { word: "BOLT-ON", icon: Plug },
    { word: "ORGANIC", icon: Leaf },
    { word: "INORGANIC", icon: Package },
    { word: "BOARD", icon: Users },
    { word: "STEWARD", icon: Star },
  ], []);

  // Random theme generator for surprise effect
  const themes = useMemo(() => [
    { primary: 'emerald', secondary: 'teal', accent: 'green', gradient: 'from-slate-950 via-emerald-950 to-slate-900' },
    { primary: 'cyan', secondary: 'blue', accent: 'sky', gradient: 'from-slate-950 via-cyan-950 to-slate-900' },
    { primary: 'violet', secondary: 'purple', accent: 'fuchsia', gradient: 'from-slate-950 via-violet-950 to-slate-900' },
    { primary: 'amber', secondary: 'orange', accent: 'yellow', gradient: 'from-slate-950 via-amber-950 to-slate-900' },
    { primary: 'rose', secondary: 'pink', accent: 'red', gradient: 'from-slate-950 via-rose-950 to-slate-900' },
    { primary: 'emerald', secondary: 'lime', accent: 'green', gradient: 'from-gray-950 via-emerald-950 to-gray-900' },
  ], []);

  // Select random theme on mount
  const [currentTheme] = useState(() => themes[Math.floor(Math.random() * themes.length)]);

  // Quote rotation with 15-minute no-repeat window - Sequential rolling
  const [currentQuoteIndex, setCurrentQuoteIndex] = useState(() => {
    const stored = sessionStorage.getItem('pe_quotes_shown');
    const shownQuotes = stored ? JSON.parse(stored) : { lastIndex: -1, shownIndices: [], timestamp: Date.now() };
    
    // Reset if 15 minutes passed
    if (Date.now() - shownQuotes.timestamp > 15 * 60 * 1000) {
      const startIndex = Math.floor(Math.random() * allQuotes.length); // Random starting point
      sessionStorage.setItem('pe_quotes_shown', JSON.stringify({ 
        lastIndex: startIndex, 
        shownIndices: [startIndex], 
        timestamp: Date.now() 
      }));
      return startIndex;
    }
    
    // Get next sequential quote (wrapping around)
    const nextIndex = (shownQuotes.lastIndex + 1) % allQuotes.length;
    
    // If we've shown all quotes, reset but continue from current position
    if (shownQuotes.shownIndices.length >= allQuotes.length) {
      sessionStorage.setItem('pe_quotes_shown', JSON.stringify({ 
        lastIndex: nextIndex, 
        shownIndices: [nextIndex], 
        timestamp: Date.now() 
      }));
      return nextIndex;
    }
    
    return nextIndex;
  });

  // Typewriter state
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);
  const [showCursor, setShowCursor] = useState(true);

  // Track shown quotes - Sequential update
  useEffect(() => {
    const stored = sessionStorage.getItem('pe_quotes_shown');
    const shownQuotes = stored ? JSON.parse(stored) : { lastIndex: -1, shownIndices: [], timestamp: Date.now() };
    
    shownQuotes.lastIndex = currentQuoteIndex;
    if (!shownQuotes.shownIndices.includes(currentQuoteIndex)) {
      shownQuotes.shownIndices.push(currentQuoteIndex);
    }
    sessionStorage.setItem('pe_quotes_shown', JSON.stringify(shownQuotes));
  }, [currentQuoteIndex]);

  // Typewriter effect - Sequential quote progression
  useEffect(() => {
    const quote = allQuotes[currentQuoteIndex];
    let charIndex = 0;
    let timeoutId;
    
    if (isTyping) {
      const typeChar = () => {
        if (charIndex <= quote.length) {
          setDisplayedText(quote.slice(0, charIndex));
          charIndex++;
          timeoutId = setTimeout(typeChar, 40);
        } else {
          setTimeout(() => setIsTyping(false), 4000);
        }
      };
      typeChar();
    } else {
      const eraseChar = () => {
        if (charIndex > 0) {
          charIndex--;
          setDisplayedText(quote.slice(0, charIndex));
          timeoutId = setTimeout(eraseChar, 20);
        } else {
          // Move to next sequential quote
          const stored = sessionStorage.getItem('pe_quotes_shown');
          const shownQuotes = stored ? JSON.parse(stored) : { lastIndex: currentQuoteIndex, shownIndices: [], timestamp: Date.now() };
          const nextIndex = (currentQuoteIndex + 1) % allQuotes.length;
          
          // Reset shown indices if we've completed a full cycle
          if (shownQuotes.shownIndices.length >= allQuotes.length) {
            shownQuotes.shownIndices = [nextIndex];
          }
          
          shownQuotes.lastIndex = nextIndex;
          sessionStorage.setItem('pe_quotes_shown', JSON.stringify(shownQuotes));
          setCurrentQuoteIndex(nextIndex);
          setIsTyping(true);
        }
      };
      charIndex = quote.length;
      eraseChar();
    }
    
    return () => clearTimeout(timeoutId);
  }, [currentQuoteIndex, isTyping, allQuotes]);

  // Cursor blink
  useEffect(() => {
    const interval = setInterval(() => setShowCursor(prev => !prev), 530);
    return () => clearInterval(interval);
  }, []);

  // SSO config
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

  // Random floating icon positions - generate more icons
  const floatingIcons = useMemo(() => {
    const positions = [];
    const usedPositions = new Set();
    const iconCount = 30; // Increased from 20 to 30
    
    // Generate unique positions across both sides
    while (positions.length < iconCount) {
      // Distribute icons: 40% left side, 40% right side, 20% scattered
      let top, left;
      const distribution = Math.random();
      
      if (distribution < 0.4) {
        // Left side
        top = 3 + Math.random() * 90;
        left = 1 + Math.random() * 18;
      } else if (distribution < 0.8) {
        // Right side
        top = 3 + Math.random() * 90;
        left = 81 + Math.random() * 17;
      } else {
        // Scattered middle-ish (but not center)
        top = 5 + Math.random() * 85;
        left = Math.random() < 0.5 ? (20 + Math.random() * 10) : (70 + Math.random() * 10);
      }
      
      const key = `${Math.round(top/8)}-${Math.round(left/8)}`;
      
      if (!usedPositions.has(key)) {
        usedPositions.add(key);
        const keyword = floatingKeywords[positions.length % floatingKeywords.length];
        positions.push({
          ...keyword,
          top: `${top}%`,
          left: `${left}%`,
          delay: Math.random() * 5,
          duration: 4 + Math.random() * 4,
          scale: 0.8 + Math.random() * 0.4, // Random size variation
        });
      }
    }
    return positions;
  }, [floatingKeywords]);

  // OTP Timer countdown
  useEffect(() => {
    if (otpTimer > 0) {
      const timer = setTimeout(() => setOtpTimer(otpTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [otpTimer]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setFormError(''); // Clear error when user starts typing
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
        // OTP-Based Registration Flow
        if (registrationStep === 'form') {
          // Step 1: Validate and request OTP
          const email = formData.email.toLowerCase();
          const allowedDomains = ['smifs.com', 'smifs.co.in'];
          const emailDomain = email.split('@')[1];
          
          if (!allowedDomains.includes(emailDomain)) {
            toast.error('Registration is only allowed for @smifs.com or @smifs.co.in email addresses');
            setLoading(false);
            return;
          }
          
          // Validate mobile number (required)
          const cleanMobile = formData.mobile_number?.replace(/\D/g, '') || '';
          if (cleanMobile.length !== 10) {
            toast.error('Please enter a valid 10-digit mobile number');
            setLoading(false);
            return;
          }
          
          // Validate PAN number (required, format: ABCDE1234F)
          const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
          const cleanPan = formData.pan_number?.toUpperCase().trim() || '';
          if (!cleanPan || !panRegex.test(cleanPan)) {
            toast.error('Please enter a valid PAN number (e.g., ABCDE1234F)');
            setLoading(false);
            return;
          }
          
          // Request OTP
          await api.post('/auth/register/request-otp', {
            email: formData.email,
            password: formData.password,
            name: formData.name,
            mobile_number: cleanMobile,
            pan_number: cleanPan,
          });
          
          setRegistrationStep('otp');
          setOtpTimer(600); // 10 minutes in seconds
          toast.success(`OTP sent to ${formData.email}. Please check your inbox.`);
        } else if (registrationStep === 'otp') {
          // Step 2: Verify OTP and complete registration
          if (!registrationOtp || registrationOtp.length !== 6) {
            toast.error('Please enter the 6-digit OTP');
            setLoading(false);
            return;
          }
          
          await api.post('/auth/register/verify-otp', null, {
            params: { email: formData.email, otp: registrationOtp }
          });
          
          setRegistrationSuccess(true);
          setRegisteredEmail(formData.email);
          setRegistrationStep('form');
          setRegistrationOtp('');
          toast.success('Registration successful! You can now login.');
        }
      }
    } catch (error) {
      const errorResponse = error.response?.data;
      const errorDetail = errorResponse?.detail;
      const statusCode = error.response?.status;
      
      // Handle CAPTCHA requirement
      const isCaptchaRequired = 
        statusCode === 428 || 
        (typeof errorDetail === 'object' && errorDetail?.captcha_required);
      
      if (isCaptchaRequired) {
        const captchaData = typeof errorDetail === 'object' ? errorDetail : {};
        setCaptchaRequired(true);
        setCaptchaToken(captchaData?.captcha_token || '');
        setCaptchaQuestion(captchaData?.captcha_question || '');
        
        // Show the error message from the backend (e.g., "Invalid email or password. 2 attempts remaining.")
        const captchaMessage = captchaData?.message || 'Please verify you are not a robot';
        setFormError(captchaMessage);
        toast.warning('Please answer the security question');
        return;
      }
      
      // Extract error message
      let message = 'An unexpected error occurred. Please try again.';
      
      if (typeof errorDetail === 'string') {
        message = errorDetail;
      } else if (typeof errorDetail === 'object' && errorDetail?.message) {
        message = errorDetail.message;
      } else if (error.message) {
        message = error.message;
      }
      
      // Enhance error messages based on status codes and context
      if (statusCode === 401) {
        message = 'Invalid email or password. Please check your credentials and try again.';
      } else if (statusCode === 403) {
        if (message.includes('approved')) {
          message = 'Your account is pending approval. Please contact admin.';
        } else if (message.includes('locked')) {
          message = 'Account locked due to too many failed attempts. Please try again later or reset your password.';
        } else {
          message = `Access denied: ${message}`;
        }
      } else if (statusCode === 404) {
        message = 'Account not found. Please check your email or register a new account.';
      } else if (statusCode === 400) {
        // Keep the backend message as it's usually specific
        message = message || 'Invalid request. Please check your input.';
      } else if (statusCode === 429) {
        message = 'Too many attempts. Please wait a few minutes before trying again.';
      } else if (statusCode === 500) {
        message = 'Server error. Please try again later or contact support.';
      } else if (!error.response) {
        message = 'Network error. Please check your internet connection.';
      }
      
      // Show error with longer duration for important messages
      toast.error(message, { 
        duration: statusCode === 403 || statusCode === 429 ? 6000 : 4000 
      });
      
      // Set form error for inline display
      setFormError(message);
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
    if (!msalInstance || !ssoConfig) return toast.error('SSO not configured');
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
      const response = await api.post('/auth/bp-otp/verify', { mobile: formData.mobile_number, otp: bpOtp });
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

  // Theme-based color classes
  const themeColors = {
    iconBg: `from-${currentTheme.primary}-500/20 to-${currentTheme.secondary}-500/20`,
    iconBorder: `border-${currentTheme.primary}-500/20`,
    iconText: `text-${currentTheme.primary}-400`,
    labelText: `text-${currentTheme.primary}-400/60`,
    glowOrb1: `bg-${currentTheme.primary}-500/10`,
    glowOrb2: `bg-${currentTheme.secondary}-500/10`,
    buttonGradient: `from-${currentTheme.primary}-500 to-${currentTheme.secondary}-500`,
    buttonHover: `hover:from-${currentTheme.primary}-600 hover:to-${currentTheme.secondary}-600`,
  };

  return (
    <div className={`min-h-screen relative overflow-hidden bg-gradient-to-br ${currentTheme.gradient}`}>
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Glowing orbs */}
        <div className={`absolute top-20 left-10 w-72 h-72 bg-${currentTheme.primary}-500/10 rounded-full blur-3xl animate-pulse`}></div>
        <div className={`absolute bottom-20 right-10 w-96 h-96 bg-${currentTheme.secondary}-500/10 rounded-full blur-3xl animate-pulse`} style={{animationDelay: '1s'}}></div>
        <div className={`absolute top-1/2 left-1/3 w-64 h-64 bg-${currentTheme.accent}-500/5 rounded-full blur-3xl animate-pulse`} style={{animationDelay: '2s'}}></div>
        
        {/* Grid pattern */}
        <div className={`absolute inset-0 bg-[linear-gradient(rgba(16,185,129,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.03)_1px,transparent_1px)] bg-[size:60px_60px]`}></div>
        
        {/* Floating Icons - Hidden on mobile, visible on lg+ */}
        {floatingIcons.map((item, idx) => (
          <div 
            key={idx}
            className="absolute hidden lg:block animate-float"
            style={{
              top: item.top,
              left: item.left,
              animationDelay: `${item.delay}s`,
              animationDuration: `${item.duration}s`,
              transform: `scale(${item.scale})`,
            }}
          >
            <div className={`bg-gradient-to-br from-${currentTheme.primary}-500/20 to-${currentTheme.secondary}-500/20 p-3 rounded-xl backdrop-blur-sm border border-${currentTheme.primary}-500/20 shadow-lg shadow-${currentTheme.primary}-500/10 transition-all duration-300 hover:scale-110`}>
              <item.icon className={`w-6 h-6 text-${currentTheme.primary}-400`} />
            </div>
            <p className={`text-${currentTheme.primary}-400/50 text-[10px] mt-1 text-center font-semibold tracking-wider`}>{item.word}</p>
          </div>
        ))}
      </div>

      {/* Main Content */}
      <div className="relative z-10 min-h-screen flex flex-col items-center justify-center px-4 py-8">
        
        {/* Nameplate Logo - Bolted Effect */}
        <div className="mb-6 animate-fade-in">
          <div className="relative">
            {/* Outer metal frame */}
            <div className="absolute -inset-2 bg-gradient-to-b from-gray-400 via-gray-300 to-gray-500 rounded-2xl shadow-2xl"></div>
            {/* Inner bevel */}
            <div className="absolute -inset-1 bg-gradient-to-b from-gray-600 via-gray-500 to-gray-700 rounded-xl"></div>
            {/* Main plate */}
            <div className="relative bg-gradient-to-b from-white via-gray-50 to-gray-100 rounded-lg p-4 shadow-inner border border-gray-300">
              {/* Bolts */}
              <div className="absolute top-2 left-2 w-3 h-3 rounded-full bg-gradient-to-br from-gray-400 to-gray-600 shadow-inner border border-gray-500">
                <div className="absolute inset-0.5 rounded-full bg-gradient-to-br from-gray-300 to-gray-500"></div>
                <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gray-600 transform -translate-y-1/2"></div>
              </div>
              <div className="absolute top-2 right-2 w-3 h-3 rounded-full bg-gradient-to-br from-gray-400 to-gray-600 shadow-inner border border-gray-500">
                <div className="absolute inset-0.5 rounded-full bg-gradient-to-br from-gray-300 to-gray-500"></div>
                <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gray-600 transform -translate-y-1/2 rotate-45"></div>
              </div>
              <div className="absolute bottom-2 left-2 w-3 h-3 rounded-full bg-gradient-to-br from-gray-400 to-gray-600 shadow-inner border border-gray-500">
                <div className="absolute inset-0.5 rounded-full bg-gradient-to-br from-gray-300 to-gray-500"></div>
                <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gray-600 transform -translate-y-1/2 -rotate-45"></div>
              </div>
              <div className="absolute bottom-2 right-2 w-3 h-3 rounded-full bg-gradient-to-br from-gray-400 to-gray-600 shadow-inner border border-gray-500">
                <div className="absolute inset-0.5 rounded-full bg-gradient-to-br from-gray-300 to-gray-500"></div>
                <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gray-600 transform -translate-y-1/2"></div>
              </div>
              {/* Logo */}
              <img 
                src="https://customer-assets.emergentagent.com/job_8c5c41a7-4474-44d9-8a72-5476f60329b4/artifacts/eineo77y_SMIFS%20%26%20PRIVITY%20Logo.png" 
                alt="SMIFS & Privity" 
                className="h-12 w-auto relative z-10 drop-shadow-sm"
                data-testid="logo"
              />
            </div>
            {/* Shadow underneath */}
            <div className="absolute -bottom-3 left-1/2 transform -translate-x-1/2 w-3/4 h-4 bg-black/30 blur-md rounded-full"></div>
          </div>
        </div>

        {/* Typewriter Quote */}
        <div className="mb-8 text-center max-w-2xl px-4 animate-fade-in" style={{animationDelay: '0.2s'}}>
          <div className="min-h-[80px] flex items-center justify-center">
            <blockquote className="text-lg sm:text-xl md:text-2xl font-light text-white leading-relaxed" data-testid="quote">
              &ldquo;{displayedText}
              <span className={`inline-block w-0.5 h-5 sm:h-6 bg-${currentTheme.primary}-400 ml-1 ${showCursor ? 'opacity-100' : 'opacity-0'}`}></span>&rdquo;
            </blockquote>
          </div>
          <cite className={`text-${currentTheme.primary}-400 text-sm mt-3 block font-semibold tracking-wide`}>
            — SMIFS PE
          </cite>
        </div>

        {/* Login Card */}
        <div className="w-full max-w-md animate-fade-in" style={{animationDelay: '0.4s'}}>
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
              <CardDescription className="text-center text-white">
                {isLogin ? 'Access exclusive PE opportunities' : 'Start your private equity journey'}
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {registrationSuccess ? (
                <div className="space-y-4">
                  <div className={`p-4 bg-${currentTheme.primary}-500/20 border border-${currentTheme.primary}-500/30 rounded-xl`}>
                    <div className="flex items-center gap-3">
                      <Mail className={`w-5 h-5 text-${currentTheme.primary}-400`} />
                      <div>
                        <p className="font-medium text-white">Registration Submitted!</p>
                        <p className="text-sm text-white">{registeredEmail} is pending approval.</p>
                      </div>
                    </div>
                  </div>
                  <Button onClick={() => { setRegistrationSuccess(false); setIsLogin(true); }}
                    className={`w-full bg-gradient-to-r from-${currentTheme.primary}-500 to-${currentTheme.secondary}-500`}>
                    <ArrowLeft className="w-4 h-4 mr-2" /> Back to Login
                  </Button>
                </div>
              ) : mobileRequired ? (
                <div className="space-y-4">
                  <div className="p-4 bg-amber-500/20 border border-amber-500/30 rounded-xl">
                    <div className="flex items-center gap-3">
                      <Phone className="w-5 h-5 text-amber-400" />
                      <p className="text-white text-sm">Update your mobile to continue</p>
                    </div>
                  </div>
                  <Input type="tel" placeholder="10-digit mobile" value={mobileUpdateNumber}
                    onChange={(e) => setMobileUpdateNumber(e.target.value.replace(/\D/g, '').slice(0, 10))}
                    className="bg-white/15 border-white/40 text-white" data-testid="mobile-input" />
                  <Button onClick={handleMobileUpdate} disabled={updatingMobile}
                    className={`w-full bg-gradient-to-r from-${currentTheme.primary}-500 to-${currentTheme.secondary}-500`}>
                    {updatingMobile ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null} Update & Continue
                  </Button>
                </div>
              ) : (
                <>
                  {isLogin && (
                    <Tabs value={loginType} onValueChange={setLoginType} className="mb-4">
                      <TabsList className="grid w-full grid-cols-2 bg-white/10">
                        <TabsTrigger value="employee" className={`data-[state=active]:bg-${currentTheme.primary}-500 data-[state=active]:text-white text-white/80`}>
                          <Building2 className="w-4 h-4 mr-2" /> Employee
                        </TabsTrigger>
                        <TabsTrigger value="partner" className={`data-[state=active]:bg-${currentTheme.primary}-500 data-[state=active]:text-white text-white/80`}>
                          <Users className="w-4 h-4 mr-2" /> Partner
                        </TabsTrigger>
                      </TabsList>
                    </Tabs>
                  )}

                  {loginType === 'employee' && (
                    <form onSubmit={handleSubmit} className="space-y-4">
                      <div className="space-y-2">
                        <Label className="text-white">Email</Label>
                        <Input type="email" name="email" placeholder="you@company.com" value={formData.email}
                          onChange={handleChange} required className="bg-white/10 border-white/30 text-white placeholder:text-white/60" data-testid="email" />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-white">Password</Label>
                        <Input type="password" name="password" placeholder="••••••••" value={formData.password}
                          onChange={handleChange} required className="bg-white/10 border-white/30 text-white placeholder:text-white/60" data-testid="password" />
                      </div>
                      
                      {isLogin && (
                        <div className="flex justify-end">
                          <a href="/forgot-password" className={`text-${currentTheme.primary}-400 text-sm hover:text-${currentTheme.primary}-300 hover:underline`}>
                            Forgot Password?
                          </a>
                        </div>
                      )}
                      
                      {!isLogin && (
                        <>
                          {registrationStep === 'form' ? (
                            <>
                              <div className="space-y-2">
                                <Label className="text-white">Full Name <span className="text-red-400">*</span></Label>
                                <Input type="text" name="name" placeholder="Your name" value={formData.name}
                                  onChange={handleChange} required className="bg-white/15 border-white/40 text-white" data-testid="name" />
                              </div>
                              <div className="space-y-2">
                                <Label className="text-white">Mobile Number <span className="text-red-400">*</span></Label>
                                <Input type="tel" name="mobile_number" placeholder="10-digit mobile number" value={formData.mobile_number}
                                  onChange={(e) => setFormData({...formData, mobile_number: e.target.value.replace(/\D/g, '').slice(0, 10)})}
                                  maxLength={10} required className="bg-white/15 border-white/40 text-white" data-testid="mobile" />
                                <p className="text-white/90 text-xs">Required for SMS/WhatsApp notifications</p>
                              </div>
                              <div className="space-y-2">
                                <Label className="text-white">PAN Number <span className="text-red-400">*</span></Label>
                                <Input type="text" name="pan_number" placeholder="ABCDE1234F" value={formData.pan_number}
                                  onChange={(e) => setFormData({...formData, pan_number: e.target.value.toUpperCase()})}
                                  maxLength={10} required className="bg-white/15 border-white/40 text-white font-mono" data-testid="pan" />
                                <p className="text-white/90 text-xs">Required for KYC verification</p>
                              </div>
                              
                              {/* Domain restriction warning */}
                              <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                                <p className="text-amber-300 text-xs flex items-center gap-2">
                                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                                  Registration is only available for @smifs.com and @smifs.co.in email addresses
                                </p>
                              </div>
                            </>
                          ) : (
                            <>
                              {/* OTP Verification Step */}
                              <div className="text-center mb-4">
                                <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full bg-${currentTheme.primary}-500/20 mb-3`}>
                                  <Mail className={`w-6 h-6 text-${currentTheme.primary}-400`} />
                                </div>
                                <h3 className="text-white text-lg font-semibold">Verify Your Email</h3>
                                <p className={`text-${currentTheme.primary}-300 text-sm mt-1`}>OTP sent to {formData.email}</p>
                              </div>
                              
                              <div className="space-y-2">
                                <Label className="text-white">Enter 6-digit OTP</Label>
                                <Input 
                                  type="text" 
                                  value={registrationOtp}
                                  onChange={(e) => setRegistrationOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                  placeholder="000000"
                                  maxLength={6}
                                  className="bg-white/15 border-white/40 text-white text-center text-xl tracking-widest font-mono"
                                  data-testid="registration-otp"
                                />
                                {otpTimer > 0 && (
                                  <p className="text-white/90 text-xs text-center">
                                    OTP expires in {Math.floor(otpTimer / 60)}:{String(otpTimer % 60).padStart(2, '0')}
                                  </p>
                                )}
                              </div>
                              
                              <div className="flex justify-between items-center">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setRegistrationStep('form');
                                    setRegistrationOtp('');
                                  }}
                                  className="text-white/90 text-sm hover:text-white flex items-center gap-1"
                                >
                                  <ArrowLeft className="w-4 h-4" /> Back
                                </button>
                                <button
                                  type="button"
                                  onClick={async () => {
                                    setResendingOtp(true);
                                    try {
                                      await api.post('/auth/register/resend-otp', null, {
                                        params: { email: formData.email }
                                      });
                                      setOtpTimer(600);
                                      toast.success('New OTP sent!');
                                    } catch (err) {
                                      toast.error(err.response?.data?.detail || 'Failed to resend OTP');
                                    } finally {
                                      setResendingOtp(false);
                                    }
                                  }}
                                  disabled={resendingOtp || otpTimer > 540}
                                  className={`text-${currentTheme.primary}-400 text-sm hover:text-${currentTheme.primary}-300 disabled:opacity-50 disabled:cursor-not-allowed`}
                                >
                                  {resendingOtp ? 'Sending...' : 'Resend OTP'}
                                </button>
                              </div>
                            </>
                          )}
                        </>
                      )}
                      
                      {/* Error Display */}
                      {formError && (
                        <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-xl animate-shake">
                          <p className="text-red-300 text-sm flex items-center gap-2">
                            <AlertCircle className="w-4 h-4 flex-shrink-0" />
                            {formError}
                          </p>
                        </div>
                      )}
                      
                      {captchaRequired && (
                        <div className="space-y-2 p-3 bg-amber-500/20 border border-amber-500/30 rounded-xl">
                          <Label className="text-amber-300 flex items-center gap-2">
                            <AlertCircle className="w-4 h-4" /> {captchaQuestion}
                          </Label>
                          <Input type="text" placeholder="Answer" value={captchaAnswer}
                            onChange={(e) => setCaptchaAnswer(e.target.value)} className="bg-white/15 border-white/40 text-white" />
                        </div>
                      )}
                      
                      <Button type="submit" disabled={loading}
                        className={`w-full h-12 bg-gradient-to-r from-${currentTheme.primary}-500 to-${currentTheme.secondary}-500 hover:from-${currentTheme.primary}-600 hover:to-${currentTheme.secondary}-600 text-white font-semibold shadow-lg shadow-${currentTheme.primary}-500/25 transition-all hover:scale-[1.02]`}
                        data-testid="submit">
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (
                          <>
                            {isLogin ? 'Sign In' : (registrationStep === 'otp' ? 'Verify OTP' : 'Send OTP')}
                            <ChevronRight className="w-5 h-5 ml-2" />
                          </>
                        )}
                      </Button>
                    </form>
                  )}

                  {loginType === 'partner' && isLogin && (
                    <div className="space-y-4">
                      {!bpOtpSent ? (
                        <>
                          <div className="space-y-2">
                            <Label className="text-white">Registered Mobile</Label>
                            <Input type="tel" placeholder="10-digit mobile" value={formData.mobile_number}
                              onChange={(e) => setFormData({...formData, mobile_number: e.target.value.replace(/\D/g, '').slice(0, 10)})}
                              className="bg-white/15 border-white/40 text-white" data-testid="bp-mobile" />
                          </div>
                          <Button onClick={handleBpOtpRequest} disabled={loading}
                            className={`w-full h-12 bg-gradient-to-r from-${currentTheme.primary}-500 to-${currentTheme.secondary}-500`}>
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Send OTP'}
                          </Button>
                        </>
                      ) : (
                        <>
                          <div className={`p-3 bg-${currentTheme.primary}-500/20 border border-${currentTheme.primary}-500/30 rounded-xl text-center`}>
                            <p className={`text-${currentTheme.primary}-300 text-sm`}>OTP sent to {formData.mobile_number}</p>
                          </div>
                          <Input type="text" placeholder="6-digit OTP" value={bpOtp}
                            onChange={(e) => setBpOtp(e.target.value.replace(/\D/g, '').slice(0, 6))} maxLength={6}
                            className="bg-white/15 border-white/40 text-white text-center text-xl tracking-widest font-mono" data-testid="otp" />
                          <Button onClick={handleBpOtpVerify} disabled={loading}
                            className={`w-full h-12 bg-gradient-to-r from-${currentTheme.primary}-500 to-${currentTheme.secondary}-500`}>
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Verify & Login'}
                          </Button>
                          <Button variant="ghost" onClick={() => setBpOtpSent(false)} className="w-full text-white hover:text-white hover:bg-white/10">
                            <ArrowLeft className="w-4 h-4 mr-2" /> Change Number
                          </Button>
                        </>
                      )}
                    </div>
                  )}

                  {ssoConfig?.enabled && isLogin && loginType === 'employee' && (
                    <>
                      <div className="relative my-4">
                        <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-white/30"></span></div>
                        <div className="relative flex justify-center text-xs uppercase"><span className="bg-transparent px-2 text-white/80">Or</span></div>
                      </div>
                      <Button variant="outline" onClick={handleSsoLogin} disabled={ssoLoading} className="w-full border-white/40 text-white hover:bg-white/20">
                        {ssoLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Building2 className="w-4 h-4 mr-2" />} Microsoft SSO
                      </Button>
                    </>
                  )}

                  {loginType === 'employee' && (
                    <div className="text-center pt-2">
                      <button type="button" onClick={() => setIsLogin(!isLogin)}
                        className={`text-${currentTheme.primary}-400 hover:text-${currentTheme.primary}-300 text-sm font-medium`} data-testid="toggle">
                        {isLogin ? "Don't have an account? Register" : "Already have an account? Sign in"}
                      </button>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <div className="mt-4 text-center">
            <Button variant="ghost" onClick={handleDemoMode} disabled={demoLoading} className="text-white hover:text-white hover:bg-white/20" data-testid="demo">
              {demoLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Play className="w-4 h-4 mr-2" />} Try Demo
            </Button>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center animate-fade-in" style={{animationDelay: '0.6s'}}>
          <p className="text-white/90 text-xs">© 2026 SMIFS Private Equity. All rights reserved.</p>
          <p className="text-white/80 text-xs mt-1">Powered by Privity | v{getFullVersion()}</p>
          <p className="text-emerald-400 text-xs mt-2 font-medium tracking-wide">✨ Vibe Coded by Somnath Dey</p>
        </div>
      </div>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-15px) rotate(3deg); }
        }
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-float { animation: float 6s ease-in-out infinite; }
        .animate-fade-in { animation: fade-in 0.8s ease-out forwards; }
      `}</style>
    </div>
  );
};

export default Login;
