import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import api from '../utils/api';
import { MessageCircle, X, Send, Sparkles, Trash2, Minimize2 } from 'lucide-react';

const SohiniAssistant = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && !isMinimized && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen, isMinimized]);

  // Add welcome message when chat opens
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: "Hi! I'm Sohini, your AI assistant for Privity. 👋\n\nI can help you with:\n• Understanding features and workflows\n• Navigating different sections\n• Explaining roles and permissions\n• Answering questions about bookings, clients, and more\n\nHow can I assist you today?"
      }]);
    }
  }, [isOpen]);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    
    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await api.post('/sohini/chat', {
        message: userMessage,
        session_id: sessionId
      });
      
      setSessionId(response.data.session_id);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.data.response 
      }]);
    } catch (error) {
      toast.error('Failed to get response');
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: "I'm sorry, I couldn't process that request. Please try again." 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = async () => {
    if (sessionId) {
      try {
        await api.delete(`/sohini/history/${sessionId}`);
      } catch (error) {
        console.error('Failed to clear history:', error);
      }
    }
    setMessages([{
      role: 'assistant',
      content: "Chat cleared! How can I help you today?"
    }]);
    setSessionId(null);
  };

  const toggleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  // Floating button when closed
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-20 right-6 z-[9999] group"
        data-testid="sohini-open-btn"
      >
        <div className="relative">
          {/* Glow effect */}
          <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full blur-lg opacity-75 group-hover:opacity-100 transition-opacity animate-pulse" />
          
          {/* Main button */}
          <div className="relative flex items-center gap-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white px-4 py-3 rounded-full shadow-xl hover:shadow-2xl transition-all transform hover:scale-105">
            {/* Avatar */}
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center overflow-hidden">
              <svg viewBox="0 0 36 36" className="w-full h-full">
                {/* Female avatar */}
                <circle cx="18" cy="18" r="18" fill="#FFD5DC"/>
                <circle cx="18" cy="14" r="8" fill="#4A3728"/>
                <path d="M10 14 Q18 8 26 14 Q26 20 18 22 Q10 20 10 14" fill="#4A3728"/>
                <circle cx="18" cy="15" r="6" fill="#FFE4C4"/>
                <circle cx="15.5" cy="14" r="1" fill="#4A3728"/>
                <circle cx="20.5" cy="14" r="1" fill="#4A3728"/>
                <path d="M16 17 Q18 18.5 20 17" stroke="#E88B8B" strokeWidth="0.8" fill="none"/>
                <ellipse cx="13" cy="15" rx="1.5" ry="0.8" fill="#FFB6C1" opacity="0.5"/>
                <ellipse cx="23" cy="15" rx="1.5" ry="0.8" fill="#FFB6C1" opacity="0.5"/>
              </svg>
            </div>
            <div className="text-left">
              <p className="font-semibold text-sm">Ask Sohini</p>
              <p className="text-xs text-white/80">AI Assistant</p>
            </div>
            <Sparkles className="w-4 h-4 text-yellow-300 animate-pulse" />
          </div>
        </div>
      </button>
    );
  }

  // Chat window
  return (
    <div 
      className={`fixed bottom-6 right-6 z-50 transition-all duration-300 ${
        isMinimized ? 'w-72' : 'w-96'
      }`}
      data-testid="sohini-chat-window"
    >
      <div className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-gray-200">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-pink-600 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Avatar */}
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center overflow-hidden ring-2 ring-white/50">
              <svg viewBox="0 0 36 36" className="w-full h-full">
                <circle cx="18" cy="18" r="18" fill="#FFD5DC"/>
                <circle cx="18" cy="14" r="8" fill="#4A3728"/>
                <path d="M10 14 Q18 8 26 14 Q26 20 18 22 Q10 20 10 14" fill="#4A3728"/>
                <circle cx="18" cy="15" r="6" fill="#FFE4C4"/>
                <circle cx="15.5" cy="14" r="1" fill="#4A3728"/>
                <circle cx="20.5" cy="14" r="1" fill="#4A3728"/>
                <path d="M16 17 Q18 18.5 20 17" stroke="#E88B8B" strokeWidth="0.8" fill="none"/>
                <ellipse cx="13" cy="15" rx="1.5" ry="0.8" fill="#FFB6C1" opacity="0.5"/>
                <ellipse cx="23" cy="15" rx="1.5" ry="0.8" fill="#FFB6C1" opacity="0.5"/>
              </svg>
            </div>
            <div className="text-white">
              <h3 className="font-semibold flex items-center gap-1">
                Sohini
                <Sparkles className="w-3 h-3 text-yellow-300" />
              </h3>
              <p className="text-xs text-white/80">AI Assistant • Online</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button 
              onClick={clearChat}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
              title="Clear chat"
            >
              <Trash2 className="w-4 h-4 text-white/80" />
            </button>
            <button 
              onClick={toggleMinimize}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
              title={isMinimized ? "Expand" : "Minimize"}
            >
              <Minimize2 className="w-4 h-4 text-white/80" />
            </button>
            <button 
              onClick={() => setIsOpen(false)}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
              title="Close"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>

        {/* Chat content - hidden when minimized */}
        {!isMinimized && (
          <>
            {/* Messages */}
            <ScrollArea className="h-80 p-4">
              <div className="space-y-4">
                {messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="w-7 h-7 rounded-full bg-gradient-to-r from-purple-100 to-pink-100 flex items-center justify-center mr-2 flex-shrink-0 mt-1">
                        <svg viewBox="0 0 36 36" className="w-5 h-5">
                          <circle cx="18" cy="18" r="18" fill="#FFD5DC"/>
                          <circle cx="18" cy="15" r="6" fill="#FFE4C4"/>
                          <circle cx="15.5" cy="14" r="1" fill="#4A3728"/>
                          <circle cx="20.5" cy="14" r="1" fill="#4A3728"/>
                          <path d="M16 17 Q18 18.5 20 17" stroke="#E88B8B" strokeWidth="0.8" fill="none"/>
                        </svg>
                      </div>
                    )}
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                        msg.role === 'user'
                          ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-br-md'
                          : 'bg-gray-100 text-gray-800 rounded-bl-md'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-r from-purple-100 to-pink-100 flex items-center justify-center mr-2">
                      <svg viewBox="0 0 36 36" className="w-5 h-5">
                        <circle cx="18" cy="18" r="18" fill="#FFD5DC"/>
                        <circle cx="18" cy="15" r="6" fill="#FFE4C4"/>
                        <circle cx="15.5" cy="14" r="1" fill="#4A3728"/>
                        <circle cx="20.5" cy="14" r="1" fill="#4A3728"/>
                      </svg>
                    </div>
                    <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Input */}
            <div className="p-4 border-t bg-gray-50">
              <div className="flex gap-2">
                <Input
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask me anything..."
                  className="flex-1 rounded-full border-gray-300 focus:border-purple-400 focus:ring-purple-400"
                  disabled={isLoading}
                />
                <Button
                  onClick={handleSend}
                  disabled={!inputValue.trim() || isLoading}
                  className="rounded-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 px-4"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
              <p className="text-xs text-gray-400 text-center mt-2">
                Powered by AI • May make mistakes
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default SohiniAssistant;
