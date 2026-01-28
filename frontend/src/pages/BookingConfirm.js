import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { CheckCircle, XCircle, Loader2, AlertTriangle } from 'lucide-react';
import api from '../utils/api';

const BookingConfirm = () => {
  const { bookingId, token, action } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showDenyForm, setShowDenyForm] = useState(false);
  const [denyReason, setDenyReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (action === 'accept') {
      confirmBooking();
    } else if (action === 'deny') {
      setShowDenyForm(true);
      setLoading(false);
    } else {
      setError('Invalid action');
      setLoading(false);
    }
  }, [bookingId, token, action]);

  const confirmBooking = async (reason = null) => {
    setSubmitting(true);
    try {
      let response;
      if (action === 'accept') {
        // Use GET for accept (no body needed)
        response = await api.get(`/booking-confirm/${bookingId}/${token}/${action}`);
      } else {
        // Use POST for deny (to send reason)
        response = await api.post(`/booking-confirm/${bookingId}/${token}/${action}`, {
          reason: reason
        });
      }
      setResult(response.data);
    } catch (err) {
      const errorDetail = err.response?.data?.detail || 'Failed to process confirmation';
      console.error('Booking confirmation error:', err.response?.data);
      setError(errorDetail);
    } finally {
      setLoading(false);
      setSubmitting(false);
    }
  };

  const handleDenySubmit = () => {
    confirmBooking(denyReason);
    setShowDenyForm(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="text-lg">Processing your confirmation...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (showDenyForm) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center mb-4">
              <XCircle className="h-10 w-10 text-red-600 dark:text-red-400" />
            </div>
            <CardTitle className="text-2xl">Deny Booking</CardTitle>
            <CardDescription>
              Please provide a reason for denying this booking (optional)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Reason for Denial</Label>
              <Textarea
                placeholder="Enter your reason for denying this booking..."
                value={denyReason}
                onChange={(e) => setDenyReason(e.target.value)}
                rows={4}
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => navigate('/')}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                className="flex-1"
                onClick={handleDenySubmit}
                disabled={submitting}
              >
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <XCircle className="h-4 w-4 mr-2" />
                )}
                Confirm Denial
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 bg-yellow-100 dark:bg-yellow-900 rounded-full flex items-center justify-center mb-4">
              <AlertTriangle className="h-10 w-10 text-yellow-600 dark:text-yellow-400" />
            </div>
            <CardTitle className="text-2xl">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent className="text-center">
            <Button onClick={() => navigate('/')}>Go to Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Handle pending approval states
  if (result?.status === 'pending_approval' || result?.status === 'pending_loss_approval') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 bg-yellow-100 dark:bg-yellow-900 rounded-full flex items-center justify-center mb-4">
              <AlertTriangle className="h-10 w-10 text-yellow-600 dark:text-yellow-400" />
            </div>
            <CardTitle className="text-2xl text-yellow-600">Booking Pending Approval</CardTitle>
            <CardDescription className="text-base mt-2">
              {result?.message}
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            {result?.booking_number && (
              <div className="bg-muted p-4 rounded-lg">
                <p className="text-sm text-muted-foreground">Booking Reference</p>
                <p className="text-xl font-mono font-bold">{result.booking_number}</p>
              </div>
            )}
            <p className="text-sm text-muted-foreground">
              {result?.status === 'pending_loss_approval' 
                ? 'This booking requires additional loss approval before you can confirm it. Please wait for the approval email.'
                : 'This booking is still pending internal approval. Please wait for the approval email before confirming.'}
            </p>
            <Button variant="outline" onClick={() => window.close()}>
              Close Window
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          {result?.status === 'accepted' ? (
            <>
              <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mb-4">
                <CheckCircle className="h-10 w-10 text-green-600 dark:text-green-400" />
              </div>
              <CardTitle className="text-2xl text-green-600">Booking Accepted!</CardTitle>
            </>
          ) : (
            <>
              <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center mb-4">
                <XCircle className="h-10 w-10 text-red-600 dark:text-red-400" />
              </div>
              <CardTitle className="text-2xl text-red-600">Booking Denied</CardTitle>
            </>
          )}
          <CardDescription className="text-base mt-2">
            {result?.message}
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          {result?.booking_number && (
            <div className="bg-muted p-4 rounded-lg">
              <p className="text-sm text-muted-foreground">Booking Reference</p>
              <p className="text-xl font-mono font-bold">{result.booking_number}</p>
            </div>
          )}
          <p className="text-sm text-muted-foreground">
            {result?.status === 'accepted' 
              ? 'Your booking has been confirmed! Payment process can now be initiated.'
              : 'The booking has been cancelled. The booking creator has been notified.'}
          </p>
          <Button variant="outline" onClick={() => window.close()}>
            Close Window
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default BookingConfirm;
