import { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import api from '../utils/api';
import { MessageCircle, X, Send, Users, Minimize2, Circle, GripHorizontal } from 'lucide-react';

// Notification sound (base64 encoded short chime)
const NOTIFICATION_SOUND = 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAABhgC7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7//////////////////////////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAAAAAAAAAAAAYYNgUFIAAAAAAAAAAAAAAAAAAAA//tQZAAP8AAAaQAAAAgAAA0gAAABAAABpAAAACAAADSAAAAETEFNRTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//tQZB4P8AAAaQAAAAgAAA0gAAABAAABpAAAACAAADSAAAAEVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVQ==';

const GroupChat = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [showOnlineUsers, setShowOnlineUsers] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  
  // Dragging state
  const [position, setPosition] = useState({ x: null, y: null });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartPos = useRef({ x: 0, y: 0 });
  const dragStartOffset = useRef({ x: 0, y: 0 });
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const audioRef = useRef(null);
  const chatWindowRef = useRef(null);
  
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

  // Initialize audio for notification sound
  useEffect(() => {
    audioRef.current = new Audio(NOTIFICATION_SOUND);
    audioRef.current.volume = 0.5;
  }, []);

  // Play notification sound
  const playNotificationSound = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch(e => console.log('Audio play failed:', e));
    }
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && !isMinimized && inputRef.current) {
      inputRef.current.focus();
      setUnreadCount(0); // Clear unread when chat is open
    }
  }, [isOpen, isMinimized]);

  // Load chat history when opened
  const loadChatHistory = useCallback(async () => {
    try {
      const response = await api.get('/group-chat/messages?limit=50');
      setMessages(response.data);
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  }, []);

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = process.env.REACT_APP_BACKEND_URL?.replace(/^https?:\/\//, '') || window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/api/ws/group-chat?token=${token}`;

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('Group chat WebSocket connected');
        setIsConnected(true);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'message') {
            setMessages(prev => [...prev, data.message]);
            
            // Play sound for messages from others
            if (data.message.user_id !== currentUser.id) {
              playNotificationSound();
              
              // Increment unread count if chat is closed or minimized
              if (!isOpen || isMinimized) {
                setUnreadCount(prev => prev + 1);
              }
            }
          } else if (data.type === 'system') {
            setMessages(prev => [...prev, {
              type: 'system',
              content: data.content,
              created_at: data.timestamp
            }]);
          } else if (data.type === 'online_users') {
            setOnlineUsers(data.users);
          } else if (data.type === 'pong') {
            // Keepalive response
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      wsRef.current.onclose = () => {
        console.log('Group chat WebSocket disconnected');
        setIsConnected(false);
        // Attempt reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      };

      wsRef.current.onerror = (error) => {
        console.error('Group chat WebSocket error:', error);
        setIsConnected(false);
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
  }, [currentUser.id, isOpen, isMinimized, playNotificationSound]);

  // AUTO-LOGIN: Connect to WebSocket immediately when component mounts (user logs in)
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token && currentUser.id) {
      // Auto-connect to chat WebSocket
      loadChatHistory();
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [currentUser.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Dragging handlers
  const handleDragStart = (e) => {
    if (e.target.closest('button') || e.target.closest('input')) return;
    
    setIsDragging(true);
    const clientX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
    const clientY = e.type === 'touchstart' ? e.touches[0].clientY : e.clientY;
    
    dragStartPos.current = { x: clientX, y: clientY };
    
    if (chatWindowRef.current) {
      const rect = chatWindowRef.current.getBoundingClientRect();
      dragStartOffset.current = {
        x: position.x !== null ? position.x : rect.left,
        y: position.y !== null ? position.y : rect.top
      };
    }
    
    e.preventDefault();
  };

  const handleDragMove = useCallback((e) => {
    if (!isDragging) return;
    
    const clientX = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
    const clientY = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY;
    
    const deltaX = clientX - dragStartPos.current.x;
    const deltaY = clientY - dragStartPos.current.y;
    
    let newX = dragStartOffset.current.x + deltaX;
    let newY = dragStartOffset.current.y + deltaY;
    
    // Keep within viewport bounds
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    const chatWidth = chatWindowRef.current?.offsetWidth || 384;
    const chatHeight = chatWindowRef.current?.offsetHeight || 450;
    
    newX = Math.max(0, Math.min(newX, windowWidth - chatWidth));
    newY = Math.max(0, Math.min(newY, windowHeight - chatHeight));
    
    setPosition({ x: newX, y: newY });
  }, [isDragging]);

  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Add/remove event listeners for dragging
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleDragMove);
      window.addEventListener('mouseup', handleDragEnd);
      window.addEventListener('touchmove', handleDragMove);
      window.addEventListener('touchend', handleDragEnd);
    }
    
    return () => {
      window.removeEventListener('mousemove', handleDragMove);
      window.removeEventListener('mouseup', handleDragEnd);
      window.removeEventListener('touchmove', handleDragMove);
      window.removeEventListener('touchend', handleDragEnd);
    };
  }, [isDragging, handleDragMove, handleDragEnd]);

  const handleSend = async () => {
    if (!inputValue.trim() || isSending) return;

    const messageContent = inputValue.trim();
    setInputValue('');
    setIsSending(true);

    try {
      await api.post('/group-chat/messages', { content: messageContent });
      // Message will come back via WebSocket
    } catch (error) {
      toast.error('Failed to send message');
      setInputValue(messageContent); // Restore input on error
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleMinimize = () => {
    setIsMinimized(!isMinimized);
    if (isMinimized) {
      setUnreadCount(0); // Clear unread when expanding
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  };

  const getRoleBadgeColor = (role) => {
    const colors = {
      1: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300', // PE Desk
      2: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300', // PE Manager
      3: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300', // Finance
      4: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300', // Manager
      5: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300', // Employee
      6: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300', // Intern
      7: 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300', // RP
      8: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300', // BP
    };
    return colors[role] || colors[5];
  };

  // Reset position when closing
  const handleClose = () => {
    setIsOpen(false);
    setPosition({ x: null, y: null }); // Reset position when closed
  };

  // Floating button when closed
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-20 left-1/2 -translate-x-1/2 md:left-auto md:translate-x-0 md:right-6 md:bottom-28 z-[9999] group"
        data-testid="group-chat-open-btn"
      >
        <div className="relative">
          {/* Glow effect */}
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full blur-lg opacity-75 group-hover:opacity-100 transition-opacity" />
          
          {/* Main button */}
          <div className="relative flex items-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-4 py-3 rounded-full shadow-xl hover:shadow-2xl transition-all transform hover:scale-105">
            <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-white/20 flex items-center justify-center">
              <MessageCircle className="w-5 h-5 md:w-6 md:h-6" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-sm">Team Chat</p>
              <p className="text-xs text-white/80 hidden md:block">
                {isConnected ? `${onlineUsers.length} online` : 'Connecting...'}
              </p>
            </div>
            <div className="flex items-center gap-1">
              {isConnected && <Circle className="w-2 h-2 fill-green-400 text-green-400" />}
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold animate-pulse">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </div>
          </div>
        </div>
      </button>
    );
  }

  // Chat window - draggable
  const chatStyle = position.x !== null && position.y !== null
    ? { left: position.x, top: position.y, right: 'auto', bottom: 'auto' }
    : {};

  return (
    <div 
      ref={chatWindowRef}
      className={`fixed z-[9999] transition-all ${isDragging ? '' : 'duration-300'}
        ${position.x === null ? 'bottom-4 left-2 right-2 md:left-auto md:right-6 md:bottom-28' : ''}
        ${isMinimized ? 'md:w-72' : 'md:w-96'}
      `}
      style={chatStyle}
      data-testid="group-chat-window"
    >
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden border border-gray-200 dark:border-gray-700">
        {/* Header - Draggable area */}
        <div 
          className={`bg-gradient-to-r from-emerald-600 to-teal-600 p-4 flex items-center justify-between ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
          onMouseDown={handleDragStart}
          onTouchStart={handleDragStart}
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center ring-2 ring-white/50">
              <GripHorizontal className="w-5 h-5 text-white/70" />
            </div>
            <div className="text-white">
              <h3 className="font-semibold flex items-center gap-2">
                Team Chat
                {isConnected && <Circle className="w-2 h-2 fill-green-400 text-green-400" />}
              </h3>
              <p className="text-xs text-white/80">
                {onlineUsers.length} online • Drag to move
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button 
              onClick={() => setShowOnlineUsers(!showOnlineUsers)}
              className="p-2 hover:bg-white/20 rounded-full transition-colors relative"
              title="Online users"
            >
              <Users className="w-4 h-4 text-white/80" />
              <span className="absolute -top-1 -right-1 bg-green-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                {onlineUsers.length}
              </span>
            </button>
            <button 
              onClick={toggleMinimize}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
              title={isMinimized ? "Expand" : "Minimize"}
            >
              <Minimize2 className="w-4 h-4 text-white/80" />
            </button>
            <button 
              onClick={handleClose}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
              title="Close"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>

        {/* Online Users Panel */}
        {showOnlineUsers && !isMinimized && (
          <div className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-3 max-h-32 overflow-y-auto">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">Online Now</p>
            <div className="flex flex-wrap gap-2">
              {onlineUsers.map((user) => (
                <span 
                  key={user.id}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600"
                >
                  <Circle className="w-2 h-2 fill-green-500 text-green-500" />
                  {user.name}
                  <span className="text-gray-400">({user.role_name})</span>
                </span>
              ))}
              {onlineUsers.length === 0 && (
                <span className="text-xs text-gray-400">No users online</span>
              )}
            </div>
          </div>
        )}

        {/* Chat content - hidden when minimized */}
        {!isMinimized && (
          <>
            {/* Messages */}
            <ScrollArea className="h-80 p-4 bg-gray-50 dark:bg-gray-800">
              <div className="space-y-3">
                {messages.length === 0 && (
                  <div className="text-center text-gray-400 py-8">
                    <MessageCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No messages yet</p>
                    <p className="text-xs">Be the first to say hello!</p>
                  </div>
                )}
                {messages.map((msg, index) => (
                  <div key={msg.id || index}>
                    {msg.type === 'system' ? (
                      <div className="text-center">
                        <span className="text-xs text-gray-400 bg-gray-200 dark:bg-gray-700 px-3 py-1 rounded-full">
                          {msg.content}
                        </span>
                      </div>
                    ) : (
                      <div className={`flex ${msg.user_id === currentUser.id ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] ${msg.user_id === currentUser.id ? 'order-1' : ''}`}>
                          {/* User info - only show for others' messages */}
                          {msg.user_id !== currentUser.id && (
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                                {msg.user_name}
                              </span>
                              <span className={`text-xs px-1.5 py-0.5 rounded ${getRoleBadgeColor(msg.user_role)}`}>
                                {msg.user_role_name}
                              </span>
                            </div>
                          )}
                          <div
                            className={`rounded-2xl px-4 py-2 ${
                              msg.user_id === currentUser.id
                                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-br-md'
                                : 'bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-bl-md shadow-sm border border-gray-100 dark:border-gray-600'
                            }`}
                          >
                            <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                            <p className={`text-xs mt-1 ${
                              msg.user_id === currentUser.id ? 'text-white/70' : 'text-gray-400'
                            }`}>
                              {formatTime(msg.created_at)}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Input */}
            <div className="p-4 border-t dark:border-gray-700 bg-white dark:bg-gray-900">
              <div className="flex gap-2">
                <Input
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type a message..."
                  className="flex-1 rounded-full border-gray-300 dark:border-gray-600 focus:border-emerald-400 focus:ring-emerald-400"
                  disabled={isSending}
                  maxLength={1000}
                />
                <Button
                  onClick={handleSend}
                  disabled={!inputValue.trim() || isSending}
                  className="rounded-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 px-4"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
              {!isConnected && (
                <p className="text-xs text-orange-500 text-center mt-2">
                  Reconnecting...
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default GroupChat;
