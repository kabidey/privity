import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import api from '../utils/api';
import { TrendingUp, AlertCircle } from 'lucide-react';

const Login = () => {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
  });

  const validateEmail = (email) => {
    const domain = email.split('@')[1]?.toLowerCase();
    return domain === 'smifs.com';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Check domain for registration
    if (!isLogin && !validateEmail(formData.email)) {
      toast.error('Registration is restricted to @smifs.com email addresses only');
      return;
    }
    
    setLoading(true);

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin
        ? { email: formData.email, password: formData.password }
        : formData;

      const response = await api.post(endpoint, payload);
      
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      
      toast.success(isLogin ? 'Logged in successfully' : 'Account created as Employee');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Side - Image */}
      <div
        className="hidden lg:block lg:w-1/2 bg-cover bg-center relative"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1769123012428-6858ea810a74?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzZ8MHwxfHNlYXJjaHwzfHxhYnN0cmFjdCUyMGZpbmFuY2lhbCUyMGdyYXBoJTIwYXJ0JTIwZGFyayUyMGdyZWVufGVufDB8fHx8MTc2OTI0OTcyN3ww&ixlib=rb-4.1.0&q=85')`,
        }}
      >
        <div className="absolute inset-0 bg-primary/80 flex items-center justify-center">
          <div className="text-center text-white px-8">
            <TrendingUp className="w-16 h-16 mx-auto mb-4" strokeWidth={1.5} />
            <h1 className="text-4xl font-bold mb-4">SMIFS Share Booking</h1>
            <p className="text-lg opacity-90">Manage your client bookings and track profit & loss efficiently</p>
          </div>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <Card className="w-full max-w-md border shadow-sm" data-testid="login-card">
          <CardHeader className="space-y-1">
            <CardTitle className="text-3xl font-bold">{isLogin ? 'Welcome back' : 'Create account'}</CardTitle>
            <CardDescription className="text-base">
              {isLogin ? 'Enter your credentials to access your account' : 'Fill in the details to get started'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <>
                  <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0" />
                    <p className="text-xs text-blue-800 dark:text-blue-200">
                      Registration is restricted to <strong>@smifs.com</strong> email addresses only. You will be registered as an Employee.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name</Label>
                    <Input
                      id="name"
                      data-testid="name-input"
                      placeholder="John Doe"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required={!isLogin}
                    />
                  </div>
                </>
              )}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
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
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
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
            </form>
            <div className="mt-4 text-center text-sm">
              <button
                type="button"
                data-testid="toggle-auth-mode"
                onClick={() => setIsLogin(!isLogin)}
                className="text-primary hover:underline"
              >
                {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Login;
