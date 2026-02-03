"""
Stock News Service - AI-Powered Real News Search
Fetches real stock market news using Google News RSS and AI summarization
Uses Emergent LLM integration for OpenAI access
"""
import os
import asyncio
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging
import json
import re
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# Cache for news to reduce API calls
_news_cache: Dict[str, dict] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache


async def search_google_news_rss(query: str) -> List[dict]:
    """
    Search Google News RSS for stock news
    """
    results = []
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            encoded_query = quote_plus(query)
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
            
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            if response.status_code == 200:
                content = response.text
                
                # Parse RSS items
                items = re.findall(
                    r'<item>.*?<title>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</title>.*?<link>(.+?)</link>.*?<pubDate>(.+?)</pubDate>.*?<source[^>]*>(.+?)</source>.*?</item>',
                    content, re.DOTALL
                )
                
                for title, link, pub_date, source in items[:10]:
                    title = re.sub(r'<!\[CDATA\[|\]\]>', '', title).strip()
                    source = re.sub(r'<!\[CDATA\[|\]\]>', '', source).strip()
                    
                    if len(title) < 20 or title.startswith('Google'):
                        continue
                    
                    results.append({
                        'title': title,
                        'url': link,
                        'source': source,
                        'pub_date': pub_date
                    })
                    
    except Exception as e:
        logger.error(f"Google News RSS error: {e}")
    
    return results


async def summarize_news_with_ai(stock_name: str, stock_symbol: str, raw_news: List[dict]) -> List[dict]:
    """
    Use OpenAI GPT via Emergent integration to summarize news
    """
    if not raw_news:
        return []
    
    try:
        from emergentintegrations.llm.openai import chat_completion
        
        # Prepare news content for AI
        news_text = ""
        for i, item in enumerate(raw_news[:8], 1):
            news_text += f"\n{i}. {item['title']} (Source: {item['source']})"
        
        prompt = f"""Analyze these news headlines about {stock_name} ({stock_symbol}) stock.

For each relevant headline, provide:
1. A clear gist (1-2 sentences explaining what this means for investors)
2. Sentiment: Bullish, Bearish, or Neutral
3. Category: Earnings, Price Movement, Corporate Action, Analyst View, Market Update, or Sector News

Headlines:{news_text}

Return ONLY a JSON array (no markdown, no explanation):
[{{"title": "Short title", "gist": "What this means for investors", "sentiment": "Bullish/Bearish/Neutral", "category": "Category", "source": "Source"}}]

Include only the 4-6 most relevant items about {stock_symbol}."""

        # Use Emergent integration
        response = await chat_completion(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial analyst. Return only valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        response_text = response.strip()
        
        # Clean markdown
        response_text = re.sub(r'^```json?\n?', '', response_text)
        response_text = re.sub(r'\n?```$', '', response_text)
        
        summarized = json.loads(response_text)
        
        now = datetime.now(timezone.utc).isoformat()
        result = []
        
        for i, item in enumerate(summarized):
            # Find URL from raw news
            source_url = "#"
            source_name = item.get('source', 'News')
            for raw in raw_news:
                if source_name.lower() in raw['source'].lower():
                    source_url = raw['url']
                    break
            if source_url == "#" and raw_news:
                source_url = raw_news[min(i, len(raw_news)-1)]['url']
            
            result.append({
                'id': hash(item.get('title', '')) & 0xffffffff,
                'title': item.get('title', 'Stock Update')[:100],
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
        logger.error(f"JSON parse error: {e}")
        return format_raw_news(raw_news, stock_symbol)
    except Exception as e:
        logger.error(f"AI summarization error: {e}")
        return format_raw_news(raw_news, stock_symbol)


def format_raw_news(raw_news: List[dict], stock_symbol: str) -> List[dict]:
    """Format raw news as fallback"""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            'id': hash(item['title']) & 0xffffffff,
            'title': item['title'][:100],
            'description': f"Latest update from {item['source']} regarding {stock_symbol} stock.",
            'source': item['source'],
            'source_url': item.get('url', '#'),
            'published_at': now,
            'category': 'Market News',
            'sentiment': 'Neutral',
            'related_stock': stock_symbol
        }
        for item in raw_news[:6]
    ]


async def fetch_stock_news(stock_symbols: List[str] = None, stock_names: List[str] = None, limit: int = 20) -> List[dict]:
    """
    Fetch real stock news using Google News RSS and AI summarization.
    """
    symbols_key = ','.join(sorted(stock_symbols or []))[:100]
    cache_key = f"gnews_v2_{symbols_key}_{limit}"
    
    # Check cache
    if cache_key in _news_cache:
        cached = _news_cache[cache_key]
        if (datetime.now(timezone.utc).timestamp() - cached['timestamp']) < CACHE_TTL_SECONDS:
            logger.info("Returning cached news")
            return cached['data']
    
    if not stock_symbols and not stock_names:
        return get_no_stocks_message()
    
    all_news = []
    
    stock_pairs = list(zip(
        stock_symbols or [''] * len(stock_names or []),
        stock_names or [''] * len(stock_symbols or [])
    ))
    
    for symbol, name in stock_pairs[:5]:
        if not symbol and not name:
            continue
        if 'test' in (symbol or '').lower() or 'test' in (name or '').lower():
            continue
        
        search_name = name.split('(')[0].strip() if name else symbol
        query = f"{search_name} {symbol} stock"
        
        logger.info(f"Searching Google News for: {query}")
        
        raw_results = await search_google_news_rss(query)
        logger.info(f"Found {len(raw_results)} results for {symbol}")
        
        if raw_results:
            summarized = await summarize_news_with_ai(search_name, symbol, raw_results)
            all_news.extend(summarized)
        
        await asyncio.sleep(0.3)
    
    # Deduplicate
    seen = set()
    unique_news = []
    for item in all_news:
        key = item['title'].lower()[:40]
        if key not in seen:
            seen.add(key)
            unique_news.append(item)
    
    unique_news = unique_news[:limit]
    
    if not unique_news:
        unique_news = get_no_real_news_message(stock_symbols)
    
    _news_cache[cache_key] = {
        'data': unique_news,
        'timestamp': datetime.now(timezone.utc).timestamp()
    }
    
    return unique_news


def get_no_stocks_message() -> List[dict]:
    now = datetime.now(timezone.utc).isoformat()
    return [{
        'id': 1,
        'title': 'Add Stocks to See Related News',
        'description': 'Add real stock symbols like RELIANCE, TCS, INFY to see AI-summarized news.',
        'source': 'System',
        'source_url': '#',
        'published_at': now,
        'category': 'Info',
        'sentiment': 'Neutral',
        'related_stock': None
    }]


def get_no_real_news_message(symbols: List[str]) -> List[dict]:
    now = datetime.now(timezone.utc).isoformat()
    valid = [s for s in (symbols or []) if s and 'test' not in s.lower()]
    stocks_str = ', '.join(valid[:3]) if valid else 'your stocks'
    return [{
        'id': 1,
        'title': f'No Recent News for {stocks_str}',
        'description': f'Try adding popular stocks like RELIANCE, TCS, HDFC, INFY for better coverage.',
        'source': 'System',
        'source_url': '#',
        'published_at': now,
        'category': 'Info',
        'sentiment': 'Neutral',
        'related_stock': None
    }]


def clear_news_cache():
    global _news_cache
    _news_cache = {}
