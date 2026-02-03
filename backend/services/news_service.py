"""
Stock News Service - AI-Powered Real News Search
Fetches real stock market news using web search and AI summarization
"""
import os
import asyncio
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)

# Cache for news to reduce API calls
_news_cache: Dict[str, dict] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache

# Emergent LLM Key for OpenAI
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "sk-emergent-83fA4Ac5d5b70CaDf4")


async def search_web_for_stock_news(query: str) -> List[dict]:
    """
    Search the web for stock news using DuckDuckGo
    """
    results = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Use DuckDuckGo HTML search
            url = "https://html.duckduckgo.com/html/"
            response = await client.post(
                url,
                data={"q": query, "kl": "in-en"},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            
            if response.status_code == 200:
                html = response.text
                # Extract search results
                result_pattern = r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]*)</a>'
                matches = re.findall(result_pattern, html, re.DOTALL)
                
                for url, title, snippet in matches[:8]:
                    title = title.strip()
                    snippet = snippet.strip()
                    
                    if len(title) > 10 and len(snippet) > 20:
                        source = extract_source(url)
                        if is_news_source(source):
                            results.append({
                                "title": title,
                                "snippet": snippet,
                                "url": url,
                                "source": source
                            })
    except Exception as e:
        logger.error(f"Web search error: {e}")
    
    return results


def extract_source(url: str) -> str:
    """Extract source name from URL"""
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
        'yahoo': 'Yahoo Finance',
        'marketwatch': 'MarketWatch',
        'bseindia': 'BSE India',
        'nseindia': 'NSE India',
        'screener': 'Screener.in',
        'tickertape': 'Tickertape',
        'trendlyne': 'Trendlyne',
        'investing': 'Investing.com',
        'tradingview': 'TradingView',
        'groww': 'Groww',
        'upstox': 'Upstox',
        'zerodha': 'Zerodha',
        'kite': 'Kite by Zerodha',
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
        return 'News'


def is_news_source(source: str) -> bool:
    """Check if source is a credible news/finance source"""
    credible = [
        'Moneycontrol', 'Economic Times', 'Mint', 'NDTV Profit',
        'Business Standard', 'Financial Express', 'Reuters', 'Bloomberg',
        'CNBC', 'Zee Business', 'Business Today', 'Hindu Business Line',
        'Yahoo Finance', 'MarketWatch', 'BSE India', 'NSE India',
        'Screener', 'Tickertape', 'Trendlyne', 'Investing', 'TradingView',
        'Groww', 'Upstox', 'Zerodha', 'Kite by Zerodha'
    ]
    return source in credible or len(source) > 3


async def summarize_news_with_ai(stock_name: str, stock_symbol: str, raw_news: List[dict]) -> List[dict]:
    """
    Use OpenAI GPT to summarize and extract news gist for stocks
    """
    if not raw_news:
        return []
    
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=EMERGENT_LLM_KEY)
        
        # Prepare news content for AI
        news_text = ""
        for i, item in enumerate(raw_news[:6], 1):
            news_text += f"\n{i}. Title: {item['title']}\n   Snippet: {item['snippet']}\n   Source: {item['source']}\n"
        
        prompt = f"""You are a financial news analyst. Analyze the following news search results for {stock_name} ({stock_symbol}) stock.

For each relevant news item, provide:
1. A clear, concise gist (1-2 sentences summarizing the key point)
2. The sentiment (Bullish/Bearish/Neutral)
3. The category (Earnings, Price Movement, Corporate Action, Analyst View, Market Update, Regulatory, IPO, M&A)

Raw search results:
{news_text}

Return ONLY a valid JSON array with this exact format (no markdown, no code blocks):
[
  {{
    "title": "Original or slightly improved title",
    "gist": "Clear 1-2 sentence summary of what the news means for investors",
    "sentiment": "Bullish/Bearish/Neutral",
    "category": "Category name",
    "source": "Source name"
  }}
]

Only include news items that are actually relevant to {stock_symbol} stock. If a result is not about this specific stock, skip it.
Return at least 3 items if possible, maximum 6 items."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial news analyst. Return only valid JSON arrays, no markdown formatting."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = re.sub(r'^```json?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        # Parse JSON
        summarized = json.loads(response_text)
        
        # Add metadata
        now = datetime.now(timezone.utc).isoformat()
        result = []
        for i, item in enumerate(summarized):
            # Find matching source URL
            source_url = "#"
            for raw in raw_news:
                if raw['source'].lower() in item.get('source', '').lower() or item.get('source', '').lower() in raw['source'].lower():
                    source_url = raw['url']
                    break
            
            result.append({
                'id': hash(item.get('title', '')) & 0xffffffff,
                'title': item.get('title', 'Stock Update'),
                'description': item.get('gist', ''),
                'source': item.get('source', 'Market News'),
                'source_url': source_url,
                'published_at': now,
                'category': item.get('category', 'Market Update'),
                'sentiment': item.get('sentiment', 'Neutral'),
                'related_stock': stock_symbol
            })
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}, response: {response_text[:200]}")
        # Return raw news as fallback
        return format_raw_news(raw_news, stock_symbol)
    except Exception as e:
        logger.error(f"AI summarization error: {e}")
        return format_raw_news(raw_news, stock_symbol)


def format_raw_news(raw_news: List[dict], stock_symbol: str) -> List[dict]:
    """Format raw search results as news items"""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            'id': hash(item['title']) & 0xffffffff,
            'title': item['title'],
            'description': item['snippet'],
            'source': item['source'],
            'source_url': item.get('url', '#'),
            'published_at': now,
            'category': 'Market News',
            'sentiment': 'Neutral',
            'related_stock': stock_symbol
        }
        for item in raw_news[:5]
    ]


async def fetch_stock_news(stock_symbols: List[str] = None, stock_names: List[str] = None, limit: int = 20) -> List[dict]:
    """
    Fetch real stock news using web search and AI summarization.
    
    Args:
        stock_symbols: List of stock symbols (e.g., ['RELIANCE', 'TCS'])
        stock_names: List of company names (e.g., ['Reliance Industries', 'Tata Consultancy'])
        limit: Maximum number of news items to return
        
    Returns:
        List of news items with AI-generated gist
    """
    # Create cache key
    symbols_key = ','.join(sorted(stock_symbols or []))[:100]
    cache_key = f"ai_news_{symbols_key}_{limit}"
    
    # Check cache
    if cache_key in _news_cache:
        cached = _news_cache[cache_key]
        if (datetime.now(timezone.utc).timestamp() - cached['timestamp']) < CACHE_TTL_SECONDS:
            logger.info("Returning cached AI news")
            return cached['data']
    
    # If no stocks, return message
    if not stock_symbols and not stock_names:
        return get_no_stocks_message()
    
    all_news = []
    
    # Create stock pairs for searching
    stock_pairs = list(zip(
        stock_symbols or [''] * len(stock_names or []),
        stock_names or [''] * len(stock_symbols or [])
    ))
    
    # Search and summarize for each stock
    for symbol, name in stock_pairs[:5]:  # Limit to 5 stocks
        if not symbol and not name:
            continue
            
        # Skip test stocks
        if 'test' in (symbol or '').lower() or 'test' in (name or '').lower():
            continue
        
        # Build search query
        search_name = name.split('(')[0].strip() if name else symbol
        query = f"{search_name} {symbol} stock news India NSE BSE latest"
        
        logger.info(f"Searching news for: {query}")
        
        # Search web
        raw_results = await search_web_for_stock_news(query)
        
        if raw_results:
            # Summarize with AI
            summarized = await summarize_news_with_ai(
                stock_name=search_name,
                stock_symbol=symbol,
                raw_news=raw_results
            )
            all_news.extend(summarized)
        
        # Small delay between searches
        await asyncio.sleep(0.5)
    
    # Remove duplicates and limit
    seen = set()
    unique_news = []
    for item in all_news:
        key = item['title'].lower()[:40]
        if key not in seen:
            seen.add(key)
            unique_news.append(item)
    
    # Sort by recency and limit
    unique_news = unique_news[:limit]
    
    # If no news found, return message
    if not unique_news:
        unique_news = get_no_real_news_message(stock_symbols)
    
    # Cache results
    _news_cache[cache_key] = {
        'data': unique_news,
        'timestamp': datetime.now(timezone.utc).timestamp()
    }
    
    return unique_news


def get_no_stocks_message() -> List[dict]:
    """Message when no stocks in system"""
    now = datetime.now(timezone.utc).isoformat()
    return [{
        'id': 1,
        'title': 'Add Stocks to See Related News',
        'description': 'News will appear here once you add stocks to your inventory. Add stocks through the Stocks page to start tracking relevant market updates.',
        'source': 'System',
        'source_url': '#',
        'published_at': now,
        'category': 'Info',
        'sentiment': 'Neutral',
        'related_stock': None
    }]


def get_no_real_news_message(symbols: List[str]) -> List[dict]:
    """Message when no real news found"""
    now = datetime.now(timezone.utc).isoformat()
    stocks_str = ', '.join(symbols[:3]) if symbols else 'your stocks'
    return [{
        'id': 1,
        'title': f'No Recent News Found for {stocks_str}',
        'description': f'Unable to find recent news articles for {stocks_str}. This could be due to limited coverage or the stocks being less actively traded. Try adding more popular stocks.',
        'source': 'System',
        'source_url': '#',
        'published_at': now,
        'category': 'Info',
        'sentiment': 'Neutral',
        'related_stock': None
    }]


def clear_news_cache():
    """Clear the news cache"""
    global _news_cache
    _news_cache = {}
    logger.info("News cache cleared")
