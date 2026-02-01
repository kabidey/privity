import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import api from '../utils/api';

const NotificationContext = createContext();

// Audio context singleton to avoid creating multiple contexts
let globalAudioContext = null;
let audioUnlocked = false;

// Initialize or resume audio context
const initAudioContext = () => {
  if (!globalAudioContext) {
    globalAudioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (globalAudioContext.state === 'suspended') {
    globalAudioContext.resume();
  }
  return globalAudioContext;
};

// Unlock audio on user interaction
const unlockAudio = async () => {
  if (audioUnlocked) return true;
  
  try {
    const ctx = initAudioContext();
    // Create and play a silent buffer to unlock audio
    const buffer = ctx.createBuffer(1, 1, 22050);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.start(0);
    audioUnlocked = true;
    console.log('Audio context unlocked');
    return true;
  } catch (error) {
    console.error('Failed to unlock audio:', error);
    return false;
  }
};

// Request browser notification permission
const requestNotificationPermission = async () => {
  if (!('Notification' in window)) {
    console.log('Browser does not support notifications');
    return 'unsupported';
  }
  
  if (Notification.permission === 'granted') {
    return 'granted';
  }
  
  if (Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission();
    return permission;
  }
  
  return Notification.permission;
};

// Show browser notification
const showBrowserNotification = (title, options = {}) => {
  if (Notification.permission === 'granted') {
    try {
      const notification = new Notification(title, {
        icon: '/logo192.png',
        badge: '/logo192.png',
        ...options
      });
      
      notification.onclick = () => {
        window.focus();
        notification.close();
      };
      
      // Auto-close after 5 seconds
      setTimeout(() => notification.close(), 5000);
    } catch (error) {
      console.error('Failed to show browser notification:', error);
    }
  }
};

// Create a LOUD notification chime with multiple harmonics
const playNotificationSound = () => {
  try {
    const audioContext = initAudioContext();
    if (audioContext.state === 'suspended') {
      audioContext.resume();
    }
    
    const masterGain = audioContext.createGain();
    masterGain.connect(audioContext.destination);
    masterGain.gain.value = 0.8; // Louder master volume
    
    const playTone = (frequency, startTime, duration, type = 'sine', volume = 0.5) => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(masterGain);
      
      oscillator.frequency.value = frequency;
      oscillator.type = type;
      
      // Sharp attack for attention-grabbing sound
      gainNode.gain.setValueAtTime(0, startTime);
      gainNode.gain.linearRampToValueAtTime(volume, startTime + 0.01);
      gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
      
      oscillator.start(startTime);
      oscillator.stop(startTime + duration);
    };
    
    const now = audioContext.currentTime;
    
    // Create a loud, attention-grabbing notification sound
    // First chime - ascending
    playTone(523.25, now, 0.15, 'sine', 0.6);        // C5
    playTone(659.25, now + 0.05, 0.15, 'sine', 0.5); // E5
    playTone(783.99, now + 0.1, 0.2, 'sine', 0.6);   // G5
    playTone(1046.50, now + 0.15, 0.3, 'sine', 0.7); // C6
    
    // Add harmonics for richness
    playTone(1046.50 * 2, now + 0.15, 0.25, 'triangle', 0.3);
    
    // Second chime - emphasis
    playTone(1318.51, now + 0.35, 0.4, 'sine', 0.5); // E6
    playTone(1567.98, now + 0.4, 0.35, 'sine', 0.4); // G6
    
  } catch (error) {
    console.error('Failed to play notification sound:', error);
  }
};

// Play urgent alert sound for critical notifications
const playUrgentSound = () => {
  try {
    const audioContext = initAudioContext();
    if (audioContext.state === 'suspended') {
      audioContext.resume();
    }
    
    const masterGain = audioContext.createGain();
    masterGain.connect(audioContext.destination);
    masterGain.gain.value = 1.0; // Maximum volume for urgent
    
    const playTone = (frequency, startTime, duration) => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(masterGain);
      
      oscillator.frequency.value = frequency;
      oscillator.type = 'square';
      
      gainNode.gain.setValueAtTime(0, startTime);
      gainNode.gain.linearRampToValueAtTime(0.4, startTime + 0.01);
      gainNode.gain.linearRampToValueAtTime(0.4, startTime + duration - 0.01);
      gainNode.gain.linearRampToValueAtTime(0, startTime + duration);
      
      oscillator.start(startTime);
      oscillator.stop(startTime + duration);
    };
    
    const now = audioContext.currentTime;
    
    // Urgent beep pattern (like hospital alert)
    for (let i = 0; i < 3; i++) {
      playTone(880, now + i * 0.25, 0.1);
      playTone(1760, now + i * 0.25 + 0.1, 0.1);
    }
    
    // Don't close the shared audio context
  } catch (error) {
    console.error('Failed to play urgent sound:', error);
  }
};

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
};

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [hasNewNotification, setHasNewNotification] = useState(false);
  const [floatingNotifications, setFloatingNotifications] = useState([]); // For floating display
  const [showNotificationDialog, setShowNotificationDialog] = useState(false);
  const [latestNotification, setLatestNotification] = useState(null);
  const [peStatus, setPeStatus] = useState({ pe_online: false, message: 'Checking...', online_users: [] }); // PE availability status
  const [notificationPermission, setNotificationPermission] = useState('default');
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [showPermissionBanner, setShowPermissionBanner] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const peStatusCallbackRef = useRef(null); // Callback for external PE status updates

  // Check and request notification permissions on mount
  useEffect(() => {
    const checkPermissions = async () => {
      // Check if we've already asked
      const hasAsked = localStorage.getItem('privity_notification_permission_asked');
      
      if ('Notification' in window) {
        setNotificationPermission(Notification.permission);
        
        // Show banner if permission is default and we haven't asked yet
        if (Notification.permission === 'default' && !hasAsked) {
          setShowPermissionBanner(true);
        }
      }
      
      // Load sound preference
      const soundPref = localStorage.getItem('privity_sound_enabled');
      if (soundPref !== null) {
        setSoundEnabled(soundPref === 'true');
      }
    };
    
    checkPermissions();
  }, []);

  // Request permissions and unlock audio
  const requestPermissions = useCallback(async () => {
    // Unlock audio first (requires user interaction)
    await unlockAudio();
    
    // Request notification permission
    const permission = await requestNotificationPermission();
    setNotificationPermission(permission);
    
    // Mark that we've asked
    localStorage.setItem('privity_notification_permission_asked', 'true');
    setShowPermissionBanner(false);
    
    if (permission === 'granted') {
      toast.success('Notifications enabled! You will now receive alerts with sound.');
      // Play a test sound to confirm audio is working
      playNotificationSound();
    } else if (permission === 'denied') {
      toast.error('Notification permission denied. You can enable it in browser settings.');
    }
    
    return permission;
  }, []);

  // Toggle sound on/off
  const toggleSound = useCallback((enabled) => {
    setSoundEnabled(enabled);
    localStorage.setItem('privity_sound_enabled', String(enabled));
    if (enabled) {
      unlockAudio();
      playNotificationSound();
      toast.success('Sound notifications enabled');
    } else {
      toast.info('Sound notifications disabled');
    }
  }, []);

  // Dismiss permission banner
  const dismissPermissionBanner = useCallback(() => {
    setShowPermissionBanner(false);
    localStorage.setItem('privity_notification_permission_asked', 'true');
  }, []);

  // Register callback for PE status updates (used by Layout component)
  const onPeStatusChange = useCallback((callback) => {
    peStatusCallbackRef.current = callback;
  }, []);

  // Update PE status and notify callback
  const updatePeStatus = useCallback((status) => {
    setPeStatus(status);
    if (peStatusCallbackRef.current) {
      peStatusCallbackRef.current(status);
    }
  }, []);

  // Add floating notification
  const addFloatingNotification = useCallback((notification) => {
    const floatingId = `${notification.id}-${Date.now()}`;
    const floatingNotif = { ...notification, floatingId };
    
    setFloatingNotifications(prev => [...prev, floatingNotif]);
    
    // Auto-remove after 8 seconds
    setTimeout(() => {
      setFloatingNotifications(prev => prev.filter(n => n.floatingId !== floatingId));
    }, 8000);
  }, []);

  // Dismiss floating notification
  const dismissFloatingNotification = useCallback((floatingId) => {
    setFloatingNotifications(prev => prev.filter(n => n.floatingId !== floatingId));
  }, []);

  const fetchNotifications = useCallback(async () => {
    try {
      const response = await api.get('/notifications?limit=50');
      setNotifications(response.data);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    }
  }, []);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const response = await api.get('/notifications/unread-count');
      setUnreadCount(response.data.count);
    } catch (error) {
      console.error('Failed to fetch unread count:', error);
    }
  }, []);

  const markAsRead = useCallback(async (notificationId) => {
    try {
      await api.put(`/notifications/${notificationId}/read`);
      setNotifications(prev =>
        prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  }, []);

  const markAllAsRead = useCallback(async () => {
    try {
      await api.put('/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    // Get WebSocket URL from API URL
    const apiUrl = process.env.REACT_APP_BACKEND_URL || '';
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = apiUrl.replace(/^https?:\/\//, '').replace(/\/api$/, '');
    const wsUrl = `${wsProtocol}//${wsHost}/api/ws/notifications?token=${token}`;

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected');
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle PE status change event
          if (data.event === 'pe_status_change') {
            console.log('PE Status changed via WebSocket:', data.data);
            updatePeStatus(data.data);
            
            // Show toast for PE status change
            if (data.data.pe_online) {
              toast.success('PE Support is now available', {
                description: data.data.online_users?.map(u => u.name).join(', ') + ' online',
                duration: 4000
              });
            } else {
              toast.warning('PE Support is now offline', {
                duration: 4000
              });
            }
          }
          
          // Handle notification event
          else if (data.event === 'notification') {
            const notification = data.data;
            
            // Prevent duplicates
            setNotifications(prev => {
              if (prev.find(n => n.id === notification.id)) return prev;
              return [notification, ...prev];
            });
            setUnreadCount(prev => prev + 1);
            
            // Store latest notification for dialog
            setLatestNotification(notification);
            
            // Check if urgent notification type
            const urgentTypes = ['booking_rejected', 'loss_booking', 'approval_needed', 'payment_overdue'];
            const isUrgent = urgentTypes.some(t => notification.type?.includes(t));
            
            // Play sound for notifications (check localStorage directly for real-time state)
            const soundPref = localStorage.getItem('privity_sound_enabled');
            const isSoundEnabled = soundPref === null || soundPref === 'true';
            
            if (isSoundEnabled) {
              if (isUrgent) {
                playUrgentSound();
              } else {
                playNotificationSound();
              }
            }
            
            // Show browser notification if permission granted
            if (Notification.permission === 'granted') {
              showBrowserNotification(notification.title, {
                body: notification.message,
                tag: notification.id,
                requireInteraction: isUrgent
              });
            }
            
            // Trigger animation state for bell icon
            setHasNewNotification(true);
            setTimeout(() => setHasNewNotification(false), 3000);
            
            // Add floating notification for important items
            if (notification.type?.includes('loss') || notification.type?.includes('rejected') || notification.type?.includes('approved') || notification.type?.includes('pending')) {
              addFloatingNotification(notification);
            }
            
            // Show simple toast notification
            const toastType = isUrgent ? 'error' : 'info';
            toast[toastType](notification.title, {
              description: notification.message,
              duration: isUrgent ? 8000 : 4000,
            });
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected');
        // Reconnect after 5 seconds - use window.location.reload as fallback
        reconnectTimeoutRef.current = setTimeout(() => {
          const token = localStorage.getItem('token');
          if (token) {
            window.location.reload();
          }
        }, 5000);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      // Send ping every 30 seconds to keep connection alive
      const pingInterval = setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send('ping');
        }
      }, 30000);

      return () => clearInterval(pingInterval);
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }, [markAsRead, addFloatingNotification, updatePeStatus]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetchNotifications();
      fetchUnreadCount();
      connectWebSocket();
      
      // Polling fallback ONLY when WebSocket is not available
      // Poll every 60 seconds (was 10 seconds - reduced to minimize API calls)
      const pollInterval = setInterval(async () => {
        // Only poll if WebSocket is NOT connected
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          try {
            const response = await api.get('/notifications?limit=5');
            const newNotifications = response.data;
            
            // Check for new notifications by comparing with stored latest ID
            const storedLatestId = localStorage.getItem('privity_latest_notification_id');
            
            if (newNotifications.length > 0) {
              const latestFromServer = newNotifications[0];
              
              // If there's a new notification we haven't seen
              if (latestFromServer.id !== storedLatestId && !latestFromServer.read) {
                // Store the latest ID to prevent duplicate processing
                localStorage.setItem('privity_latest_notification_id', latestFromServer.id);
                
                setNotifications(prev => {
                  // Only add if not already present
                  if (!prev.find(n => n.id === latestFromServer.id)) {
                    return [latestFromServer, ...prev];
                  }
                  return prev;
                });
                setUnreadCount(prev => prev + 1);
                
                // Play sound and show floating notification
                const urgentTypes = ['booking_rejected', 'loss_booking', 'approval_needed', 'payment_overdue'];
                const isUrgent = urgentTypes.some(t => latestFromServer.type?.includes(t));
                
                if (isUrgent) {
                  playUrgentSound();
                } else {
                  playNotificationSound();
                }
                
                addFloatingNotification(latestFromServer);
                setLatestNotification(latestFromServer);
                setHasNewNotification(true);
                setTimeout(() => setHasNewNotification(false), 3000);
                
                // Show toast
                toast(latestFromServer.title, {
                  description: latestFromServer.message,
                  duration: 6000
                });
              }
            }
            
            // Update unread count
            const countResponse = await api.get('/notifications/unread-count');
            setUnreadCount(countResponse.data.count);
          } catch (error) {
            // Silent fail for polling
          }
        }
      }, 60000); // Poll every 60 seconds only as fallback
      
      return () => clearInterval(pollInterval);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [fetchNotifications, fetchUnreadCount, connectWebSocket, addFloatingNotification]);

  // Manual test notification trigger
  const triggerTestNotification = useCallback(async () => {
    try {
      // Play sound first (requires user interaction)
      playNotificationSound();
      
      const response = await api.post('/notifications/test', null, {
        params: {
          title: '🔔 Test Alert',
          message: 'This is a test notification to verify the system is working correctly.',
          notif_type: 'info'
        }
      });
      
      // The notification will come via WebSocket if connected
      // Only manually add if WebSocket is not connected
      const notification = response.data.notification;
      if (notification && (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN)) {
        setNotifications(prev => {
          // Prevent duplicates
          if (prev.find(n => n.id === notification.id)) return prev;
          return [notification, ...prev];
        });
        setUnreadCount(prev => prev + 1);
        addFloatingNotification(notification);
        setLatestNotification(notification);
        setHasNewNotification(true);
        setTimeout(() => setHasNewNotification(false), 3000);
        
        toast(notification.title, {
          description: notification.message,
          duration: 6000
        });
      }
      
      return response.data;
    } catch (error) {
      console.error('Failed to trigger test notification:', error);
      throw error;
    }
  }, [addFloatingNotification]);

  const value = {
    notifications,
    unreadCount,
    isConnected,
    hasNewNotification,
    setHasNewNotification,
    floatingNotifications,
    dismissFloatingNotification,
    showNotificationDialog,
    setShowNotificationDialog,
    latestNotification,
    peStatus,
    onPeStatusChange,
    updatePeStatus,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    connectWebSocket,
    playNotificationSound,
    playUrgentSound,
    triggerTestNotification,
    // Permission management
    notificationPermission,
    soundEnabled,
    showPermissionBanner,
    requestPermissions,
    toggleSound,
    dismissPermissionBanner
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export default NotificationContext;
