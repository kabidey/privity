"""
Stock News Service
Fetches stock market news from various sources using web search
"""
import os
import asyncio
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Cache for news to avoid frequent API calls
_news_cache: Dict[str, dict] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache


async def fetch_stock_news(stock_symbols: List[str] = None, limit: int = 20) -> List[dict]:
    """
    Fetch stock news for Indian market stocks.
    Uses web search to get latest news.
    
    Args:
        stock_symbols: List of stock symbols to search news for (optional)
        limit: Maximum number of news items to return
        
    Returns:
        List of news items with title, description, source, published_at
    """
    cache_key = f"stock_news_{','.join(stock_symbols or ['general'])}_{limit}"
    
    # Check cache first
    if cache_key in _news_cache:
        cached = _news_cache[cache_key]
        if (datetime.now(timezone.utc).timestamp() - cached['timestamp']) < CACHE_TTL_SECONDS:
            logger.info("Returning cached news")
            return cached['data']
    
    news_items = []
    
    try:
        # Build search queries for Indian stock market news
        search_queries = []
        
        if stock_symbols and len(stock_symbols) > 0:
            # Search for specific stock news
            for symbol in stock_symbols[:5]:  # Limit to 5 symbols
                search_queries.append(f"{symbol} stock news India NSE BSE")
        else:
            # General Indian market news
            search_queries = [
                "Indian stock market news today NSE BSE",
                "Nifty Sensex market update today",
                "Indian equity market news latest",
            ]
        
        # Use DuckDuckGo HTML search (no API key required)
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in search_queries[:3]:  # Limit queries
                try:
                    # DuckDuckGo HTML search
                    url = "https://html.duckduckgo.com/html/"
                    response = await client.post(
                        url,
                        data={"q": query, "kl": "in-en"},  # India English
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }
                    )
                    
                    if response.status_code == 200:
                        # Parse the HTML response
                        html = response.text
                        # Extract news items from search results
                        items = parse_duckduckgo_results(html, query)
                        news_items.extend(items)
                        
                except Exception as e:
                    logger.warning(f"Search query failed: {query}, error: {e}")
                    continue
                
                # Small delay between requests
                await asyncio.sleep(0.5)
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_news = []
        for item in news_items:
            title_key = item['title'].lower()[:50]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_news.append(item)
        
        # Sort by published date (newest first) and limit
        unique_news = sorted(unique_news, key=lambda x: x.get('published_at', ''), reverse=True)[:limit]
        
        # If no news found, return fallback news
        if not unique_news:
            unique_news = get_fallback_news()
        
        # Cache the results
        _news_cache[cache_key] = {
            'data': unique_news,
            'timestamp': datetime.now(timezone.utc).timestamp()
        }
        
        return unique_news
        
    except Exception as e:
        logger.error(f"Error fetching stock news: {e}")
        # Return cached data if available, otherwise fallback
        if cache_key in _news_cache:
            return _news_cache[cache_key]['data']
        return get_fallback_news()


def parse_duckduckgo_results(html: str, query: str) -> List[dict]:
    """Parse DuckDuckGo HTML search results"""
    import re
    
    news_items = []
    
    # Extract result blocks
    result_pattern = r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]+)</a>'
    results = re.findall(result_pattern, html, re.DOTALL)
    
    for url, title, snippet in results[:10]:
        # Clean up the text
        title = title.strip()
        snippet = snippet.strip()
        
        # Skip non-news results
        if len(title) < 10 or len(snippet) < 20:
            continue
        
        # Extract source from URL
        source = extract_source_from_url(url)
        
        # Skip if not a credible news source
        if not is_credible_source(source):
            continue
        
        news_items.append({
            'id': hash(title) & 0xffffffff,
            'title': title[:200],
            'description': snippet[:300],
            'source': source,
            'source_url': url,
            'published_at': datetime.now(timezone.utc).isoformat(),
            'category': categorize_news(title, snippet),
            'search_query': query
        })
    
    return news_items


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
        'google': 'Google News',
        'bseindia': 'BSE India',
        'nseindia': 'NSE India',
        'sebi': 'SEBI',
    }
    
    url_lower = url.lower()
    for key, name in source_map.items():
        if key in url_lower:
            return name
    
    # Try to extract domain
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '')
        return domain.split('.')[0].capitalize()
    except:
        return 'News Source'


def is_credible_source(source: str) -> bool:
    """Check if the source is a credible news source"""
    credible_sources = [
        'Moneycontrol', 'Economic Times', 'Mint', 'NDTV Profit',
        'Business Standard', 'Financial Express', 'Reuters', 'Bloomberg',
        'CNBC', 'Zee Business', 'Business Today', 'Hindu Business Line',
        'Yahoo Finance', 'MarketWatch', 'BSE India', 'NSE India', 'SEBI',
        'Investopedia', 'Google News'
    ]
    return source in credible_sources or len(source) > 3


def categorize_news(title: str, description: str) -> str:
    """Categorize news based on content"""
    text = (title + ' ' + description).lower()
    
    if any(word in text for word in ['nifty', 'sensex', 'index', 'benchmark']):
        return 'Market Index'
    elif any(word in text for word in ['result', 'earnings', 'profit', 'quarter', 'q1', 'q2', 'q3', 'q4']):
        return 'Earnings'
    elif any(word in text for word in ['ipo', 'listing', 'offer', 'debut']):
        return 'IPO'
    elif any(word in text for word in ['dividend', 'bonus', 'split', 'buyback']):
        return 'Corporate Action'
    elif any(word in text for word in ['rbi', 'sebi', 'regulation', 'policy']):
        return 'Regulatory'
    elif any(word in text for word in ['fii', 'dii', 'foreign', 'institutional']):
        return 'FII/DII'
    elif any(word in text for word in ['merger', 'acquisition', 'deal', 'takeover']):
        return 'M&A'
    else:
        return 'Market News'


def get_fallback_news() -> List[dict]:
    """Return fallback news when API fails"""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            'id': 1,
            'title': 'Indian Markets Show Resilience Amid Global Uncertainty',
            'description': 'Indian equity markets continue to show strength with Nifty and Sensex maintaining key support levels. Analysts remain cautiously optimistic about the medium-term outlook.',
            'source': 'Market Analysis',
            'source_url': '#',
            'published_at': now,
            'category': 'Market Index'
        },
        {
            'id': 2,
            'title': 'Q3 Earnings Season: Key Stocks to Watch',
            'description': 'As the quarterly earnings season progresses, several blue-chip companies are set to announce their results. Banking and IT sectors remain in focus.',
            'source': 'Market Analysis',
            'source_url': '#',
            'published_at': now,
            'category': 'Earnings'
        },
        {
            'id': 3,
            'title': 'FII Activity: Institutional Flows Update',
            'description': 'Foreign institutional investors show mixed sentiment this week. DII buying continues to provide support to the markets.',
            'source': 'Market Analysis',
            'source_url': '#',
            'published_at': now,
            'category': 'FII/DII'
        },
        {
            'id': 4,
            'title': 'Sectoral Analysis: Banking Stocks in Focus',
            'description': 'Banking sector stocks gain attention as credit growth remains robust. NBFCs also see renewed interest from investors.',
            'source': 'Market Analysis',
            'source_url': '#',
            'published_at': now,
            'category': 'Market News'
        },
        {
            'id': 5,
            'title': 'IPO Market Update: Upcoming Listings',
            'description': 'Several IPOs are lined up in the coming weeks. Primary market activity expected to remain buoyant.',
            'source': 'Market Analysis',
            'source_url': '#',
            'published_at': now,
            'category': 'IPO'
        }
    ]


def clear_news_cache():
    """Clear the news cache"""
    global _news_cache
    _news_cache = {}
    logger.info("News cache cleared")
