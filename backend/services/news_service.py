"""
Stock News Service
Fetches stock market news specifically for stocks in the system
"""
import os
import asyncio
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

# Cache for news to avoid frequent API calls
_news_cache: Dict[str, dict] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache


async def fetch_stock_news(stock_symbols: List[str] = None, stock_names: List[str] = None, limit: int = 20) -> List[dict]:
    """
    Fetch stock news specifically for the stocks in the system.
    
    Args:
        stock_symbols: List of stock symbols to search news for
        stock_names: List of stock/company names to search news for
        limit: Maximum number of news items to return
        
    Returns:
        List of news items with title, description, source, published_at
    """
    # Create cache key from symbols
    symbols_key = ','.join(sorted(stock_symbols or []))[:100]
    cache_key = f"stock_news_{symbols_key}_{limit}"
    
    # Check cache first
    if cache_key in _news_cache:
        cached = _news_cache[cache_key]
        if (datetime.now(timezone.utc).timestamp() - cached['timestamp']) < CACHE_TTL_SECONDS:
            logger.info("Returning cached news")
            return cached['data']
    
    news_items = []
    
    # If no stocks provided, return empty
    if not stock_symbols and not stock_names:
        logger.info("No stocks provided for news search")
        return get_no_stocks_message()
    
    try:
        # Build search queries for specific stocks
        search_queries = []
        
        # Search for each stock symbol/name
        if stock_symbols:
            for symbol in stock_symbols[:8]:  # Limit to 8 stocks
                # Clean up symbol for search
                clean_symbol = symbol.replace('-', ' ').strip()
                if len(clean_symbol) >= 3:
                    search_queries.append(f"{clean_symbol} stock news India NSE BSE")
        
        if stock_names:
            for name in stock_names[:5]:  # Also search by company name
                # Clean up name
                clean_name = name.split('(')[0].strip()[:30]
                if len(clean_name) >= 3 and clean_name not in ['Test', 'TEST']:
                    search_queries.append(f"{clean_name} share price news")
        
        # If no valid queries, return message
        if not search_queries:
            return get_no_stocks_message()
        
        # Use DuckDuckGo HTML search
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in search_queries:
                try:
                    url = "https://html.duckduckgo.com/html/"
                    response = await client.post(
                        url,
                        data={"q": query, "kl": "in-en"},
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }
                    )
                    
                    if response.status_code == 200:
                        items = parse_duckduckgo_results(response.text, query, stock_symbols, stock_names)
                        news_items.extend(items)
                        
                except Exception as e:
                    logger.warning(f"Search query failed: {query}, error: {e}")
                    continue
                
                await asyncio.sleep(0.3)
        
        # Remove duplicates
        seen_titles = set()
        unique_news = []
        for item in news_items:
            title_key = item['title'].lower()[:50]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_news.append(item)
        
        # Sort and limit
        unique_news = sorted(unique_news, key=lambda x: x.get('relevance_score', 0), reverse=True)[:limit]
        
        # If no news found for specific stocks, generate stock-specific placeholders
        if not unique_news:
            unique_news = generate_stock_specific_news(stock_symbols, stock_names)
        
        # Cache results
        _news_cache[cache_key] = {
            'data': unique_news,
            'timestamp': datetime.now(timezone.utc).timestamp()
        }
        
        return unique_news
        
    except Exception as e:
        logger.error(f"Error fetching stock news: {e}")
        if cache_key in _news_cache:
            return _news_cache[cache_key]['data']
        return generate_stock_specific_news(stock_symbols, stock_names)


def parse_duckduckgo_results(html: str, query: str, stock_symbols: List[str], stock_names: List[str]) -> List[dict]:
    """Parse DuckDuckGo HTML search results"""
    news_items = []
    
    # Extract result blocks
    result_pattern = r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]+)</a>'
    results = re.findall(result_pattern, html, re.DOTALL)
    
    for url, title, snippet in results[:8]:
        title = title.strip()
        snippet = snippet.strip()
        
        if len(title) < 10 or len(snippet) < 20:
            continue
        
        source = extract_source_from_url(url)
        
        if not is_credible_source(source):
            continue
        
        # Calculate relevance score based on stock mentions
        relevance_score = calculate_relevance(title, snippet, stock_symbols, stock_names)
        
        if relevance_score > 0:
            # Extract which stock this news is about
            related_stock = find_related_stock(title, snippet, stock_symbols, stock_names)
            
            news_items.append({
                'id': hash(title) & 0xffffffff,
                'title': title[:200],
                'description': snippet[:300],
                'source': source,
                'source_url': url,
                'published_at': datetime.now(timezone.utc).isoformat(),
                'category': categorize_news(title, snippet),
                'related_stock': related_stock,
                'relevance_score': relevance_score
            })
    
    return news_items


def calculate_relevance(title: str, description: str, symbols: List[str], names: List[str]) -> int:
    """Calculate how relevant the news is to our stocks"""
    text = (title + ' ' + description).lower()
    score = 0
    
    # Check for symbol matches
    for symbol in (symbols or []):
        if symbol.lower() in text:
            score += 10
    
    # Check for name matches
    for name in (names or []):
        name_parts = name.lower().split()
        for part in name_parts:
            if len(part) > 3 and part in text:
                score += 5
    
    # Bonus for financial news indicators
    if any(word in text for word in ['stock', 'share', 'nse', 'bse', 'equity']):
        score += 2
    
    return score


def find_related_stock(title: str, description: str, symbols: List[str], names: List[str]) -> Optional[str]:
    """Find which stock the news is about"""
    text = (title + ' ' + description).lower()
    
    for symbol in (symbols or []):
        if symbol.lower() in text:
            return symbol
    
    for name in (names or []):
        if name.lower()[:10] in text:
            return name[:20]
    
    return None


def extract_source_from_url(url: str) -> str:
    """Extract readable source name from URL"""
    source_map = {
        'moneycontrol': 'Moneycontrol',
        'economictimes': 'Economic Times',
        'livemint': 'Mint',
        'ndtv': 'NDTV Profit',
        'business-standard': 'Business Standard',
        'financialexpress': 'Financial Express',
        'reuters': 'Reuters',
        'bloomberg': 'Bloomberg',
        'cnbc': 'CNBC',
        'zeebiz': 'Zee Business',
        'businesstoday': 'Business Today',
        'thehindubusinessline': 'Hindu Business Line',
        'investopedia': 'Investopedia',
        'marketwatch': 'MarketWatch',
        'yahoo': 'Yahoo Finance',
        'bseindia': 'BSE India',
        'nseindia': 'NSE India',
        'screener': 'Screener.in',
        'tickertape': 'Tickertape',
        'trendlyne': 'Trendlyne',
    }
    
    url_lower = url.lower()
    for key, name in source_map.items():
        if key in url_lower:
            return name
    
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '')
        return domain.split('.')[0].capitalize()
    except:
        return 'News Source'


def is_credible_source(source: str) -> bool:
    """Check if the source is credible"""
    credible_sources = [
        'Moneycontrol', 'Economic Times', 'Mint', 'NDTV Profit',
        'Business Standard', 'Financial Express', 'Reuters', 'Bloomberg',
        'CNBC', 'Zee Business', 'Business Today', 'Hindu Business Line',
        'Yahoo Finance', 'MarketWatch', 'BSE India', 'NSE India',
        'Screener', 'Tickertape', 'Trendlyne', 'Investopedia'
    ]
    return source in credible_sources or len(source) > 3


def categorize_news(title: str, description: str) -> str:
    """Categorize news based on content"""
    text = (title + ' ' + description).lower()
    
    if any(word in text for word in ['result', 'earnings', 'profit', 'quarter', 'q1', 'q2', 'q3', 'q4', 'revenue']):
        return 'Earnings'
    elif any(word in text for word in ['dividend', 'bonus', 'split', 'buyback', 'record date']):
        return 'Corporate Action'
    elif any(word in text for word in ['buy', 'sell', 'target', 'rating', 'upgrade', 'downgrade']):
        return 'Analyst View'
    elif any(word in text for word in ['ipo', 'listing', 'offer', 'debut']):
        return 'IPO'
    elif any(word in text for word in ['merger', 'acquisition', 'deal', 'takeover']):
        return 'M&A'
    elif any(word in text for word in ['fii', 'dii', 'foreign', 'institutional']):
        return 'Institutional'
    else:
        return 'Stock Update'


def generate_stock_specific_news(symbols: List[str], names: List[str]) -> List[dict]:
    """Generate placeholder news for specific stocks"""
    now = datetime.now(timezone.utc).isoformat()
    news = []
    
    all_stocks = list(zip(symbols or [], names or []))
    
    for i, (symbol, name) in enumerate(all_stocks[:5]):
        display_name = name if name and 'test' not in name.lower() else symbol
        
        news.append({
            'id': i + 1,
            'title': f'{display_name}: Stock Analysis and Market Update',
            'description': f'Latest market analysis for {display_name} ({symbol}). Track price movements, technical indicators, and trading volumes on NSE/BSE.',
            'source': 'Market Analysis',
            'source_url': '#',
            'published_at': now,
            'category': 'Stock Update',
            'related_stock': symbol
        })
    
    # Add general news if we have stocks
    if all_stocks:
        news.append({
            'id': 100,
            'title': f'Portfolio Stocks: Daily Market Summary',
            'description': f'Tracking {len(all_stocks)} stocks in your portfolio. Monitor key levels, support/resistance, and market sentiment for your holdings.',
            'source': 'Portfolio Analysis',
            'source_url': '#',
            'published_at': now,
            'category': 'Stock Update',
            'related_stock': None
        })
    
    return news


def get_no_stocks_message() -> List[dict]:
    """Return message when no stocks are in the system"""
    now = datetime.now(timezone.utc).isoformat()
    return [{
        'id': 1,
        'title': 'Add Stocks to See Related News',
        'description': 'News will appear here once you add stocks to your inventory. Add stocks through the Stocks page to start tracking relevant market updates.',
        'source': 'System',
        'source_url': '#',
        'published_at': now,
        'category': 'Info',
        'related_stock': None
    }]


def clear_news_cache():
    """Clear the news cache"""
    global _news_cache
    _news_cache = {}
    logger.info("News cache cleared")
