import { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Newspaper, ExternalLink, RefreshCw, TrendingUp, Building2, FileText, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '../utils/api';

const POLL_INTERVAL = 60 * 60 * 1000; // 1 hour in milliseconds
const SCROLL_SPEED = 30; // pixels per second

const categoryIcons = {
  'Market Index': TrendingUp,
  'Earnings': FileText,
  'IPO': Building2,
  'Corporate Action': Building2,
  'Regulatory': AlertCircle,
  'FII/DII': TrendingUp,
  'M&A': Building2,
  'Market News': Newspaper,
};

const categoryColors = {
  'Market Index': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  'Earnings': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  'IPO': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  'Corporate Action': 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  'Regulatory': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  'FII/DII': 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400',
  'M&A': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
  'Market News': 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
};

const StockNewsSection = () => {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isPaused, setIsPaused] = useState(false);
  const scrollContainerRef = useRef(null);
  const scrollAnimationRef = useRef(null);
  const scrollPositionRef = useRef(0);

  const fetchNews = async () => {
    try {
      const response = await api.get('/dashboard/stock-news?limit=20');
      setNews(response.data.news || []);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error('Failed to fetch news:', err);
      setError('Failed to load news');
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and polling
  useEffect(() => {
    fetchNews();
    
    // Poll every hour
    const pollInterval = setInterval(fetchNews, POLL_INTERVAL);
    
    return () => clearInterval(pollInterval);
  }, []);

  // Auto-scroll animation
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container || news.length === 0) return;

    let lastTime = performance.now();
    
    const animate = (currentTime) => {
      if (!isPaused) {
        const deltaTime = (currentTime - lastTime) / 1000; // Convert to seconds
        scrollPositionRef.current += SCROLL_SPEED * deltaTime;
        
        // Reset scroll position when reaching the end (seamless loop)
        const scrollHeight = container.scrollHeight / 2; // Because we duplicate content
        if (scrollPositionRef.current >= scrollHeight) {
          scrollPositionRef.current = 0;
        }
        
        container.scrollTop = scrollPositionRef.current;
      }
      lastTime = currentTime;
      scrollAnimationRef.current = requestAnimationFrame(animate);
    };
    
    scrollAnimationRef.current = requestAnimationFrame(animate);
    
    return () => {
      if (scrollAnimationRef.current) {
        cancelAnimationFrame(scrollAnimationRef.current);
      }
    };
  }, [news, isPaused]);

  const formatTime = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  };

  const handleManualRefresh = async () => {
    setLoading(true);
    await fetchNews();
  };

  // Duplicate news for seamless scrolling
  const duplicatedNews = [...news, ...news];

  if (loading && news.length === 0) {
    return (
      <Card className="border shadow-sm h-[500px]" data-testid="stock-news-section">
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <Newspaper className="h-6 w-6 text-emerald-600" />
            Stock Market News
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 flex items-center justify-center h-[420px]">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground mx-auto mb-2" />
            <p className="text-muted-foreground">Loading latest news...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card 
      className="border shadow-sm h-[500px] overflow-hidden" 
      data-testid="stock-news-section"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <CardHeader className="pb-3 border-b bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <div className="p-2 bg-emerald-100 dark:bg-emerald-900/50 rounded-lg">
              <Newspaper className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <span className="text-foreground">Stock Market News</span>
              <p className="text-xs font-normal text-muted-foreground mt-0.5">
                Auto-updates every hour • Hover to pause
              </p>
            </div>
          </CardTitle>
          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-xs text-muted-foreground hidden sm:block">
                Updated: {lastUpdated.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleManualRefresh}
              disabled={loading}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-0 h-[420px] overflow-hidden relative">
        {error ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
              <p className="text-muted-foreground">{error}</p>
              <Button variant="outline" size="sm" onClick={handleManualRefresh} className="mt-2">
                Try Again
              </Button>
            </div>
          </div>
        ) : (
          <>
            {/* Gradient overlays for smooth scroll effect */}
            <div className="absolute top-0 left-0 right-0 h-8 bg-gradient-to-b from-background to-transparent z-10 pointer-events-none" />
            <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-background to-transparent z-10 pointer-events-none" />
            
            {/* Scrolling news container */}
            <div 
              ref={scrollContainerRef}
              className="h-full overflow-hidden"
              style={{ scrollBehavior: 'auto' }}
            >
              <div className="divide-y divide-border/50">
                {duplicatedNews.map((item, index) => {
                  const CategoryIcon = categoryIcons[item.category] || Newspaper;
                  const categoryColor = categoryColors[item.category] || categoryColors['Market News'];
                  
                  return (
                    <div 
                      key={`${item.id}-${index}`}
                      className="p-4 hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex gap-3">
                        {/* Category Icon */}
                        <div className={`flex-shrink-0 p-2 rounded-lg ${categoryColor.split(' ').slice(0, 2).join(' ')}`}>
                          <CategoryIcon className={`h-4 w-4 ${categoryColor.split(' ').slice(2).join(' ')}`} />
                        </div>
                        
                        {/* News Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <h4 className="font-semibold text-sm leading-tight line-clamp-2">
                              {item.title}
                            </h4>
                          </div>
                          
                          <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                            {item.description}
                          </p>
                          
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 ${categoryColor}`}>
                              {item.category}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                              <ExternalLink className="h-3 w-3" />
                              {item.source}
                            </span>
                            {item.published_at && (
                              <span className="text-[10px] text-muted-foreground">
                                • {formatTime(item.published_at)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
        
        {/* Pause indicator */}
        {isPaused && (
          <div className="absolute bottom-4 right-4 bg-black/70 text-white text-xs px-2 py-1 rounded-full">
            Paused
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default StockNewsSection;
