"""
Stock News Service - AI-Powered Real News Search
Fetches real stock market news using Google News RSS and AI summarization
"""
import os
import asyncio
import httpx
from datetime import datetime, timezone
from typing import List, Dict
import logging
import json
import re
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# Cache for news
_news_cache: Dict[str, dict] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour

# Emergent LLM Key
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "sk-emergent-83fA4Ac5d5b70CaDf4")


async def search_google_news_rss(query: str) -> List[dict]:
    """Search Google News RSS for stock news"""
    results = []
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            encoded_query = quote_plus(query)
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
            
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            if response.status_code == 200:
                items = re.findall(
                    r'<item>.*?<title>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</title>.*?<link>(.+?)</link>.*?<pubDate>(.+?)</pubDate>.*?<source[^>]*>(.+?)</source>.*?</item>',
                    response.text, re.DOTALL
                )
                
                for title, link, pub_date, source in items[:10]:
                    title = re.sub(r'<!\[CDATA\[|\]\]>', '', title).strip()
                    source = re.sub(r'<!\[CDATA\[|\]\]>', '', source).strip()
                    
                    if len(title) >= 20 and not title.startswith('Google'):
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
    """Use Emergent LLM to summarize news"""
    if not raw_news:
        return []
    
    try:
        from emergentintegrations.llm.openai import LlmChat, UserMessage
        
        # Prepare headlines
        headlines = "\n".join([f"{i+1}. {item['title']} ({item['source']})" 
                              for i, item in enumerate(raw_news[:8])])
        
        prompt = f"""Analyze these {stock_name} ({stock_symbol}) stock news headlines.

Headlines:
{headlines}

For each headline, provide:
- title: Short headline (max 80 chars)
- gist: What this means for investors (1-2 sentences)
- sentiment: Bullish, Bearish, or Neutral
- category: Earnings, Price Movement, Corporate Action, Analyst View, Market Update, or Sector News
- source: Source name

Return ONLY a JSON array, no markdown:
[{{"title":"...", "gist":"...", "sentiment":"...", "category":"...", "source":"..."}}]

Include 4-6 most relevant items."""

        # Initialize chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"news_{stock_symbol}_{datetime.now().timestamp()}",
            system_message="You are a financial analyst. Return only valid JSON arrays."
        )
        chat = chat.with_model("openai", "gpt-4o-mini")
        chat = chat.with_params(temperature=0.3, max_tokens=1500)
        
        # Send message
        user_msg = UserMessage(text=prompt)
        response_text = await chat.send_message(user_msg)
        
        # Clean response
        response_text = response_text.strip()
        response_text = re.sub(r'^```json?\n?', '', response_text)
        response_text = re.sub(r'\n?```$', '', response_text)
        
        summarized = json.loads(response_text)
        
        now = datetime.now(timezone.utc).isoformat()
        result = []
        
        for i, item in enumerate(summarized):
            # Find URL
            source_url = "#"
            for raw in raw_news:
                if item.get('source', '').lower() in raw['source'].lower():
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
        
        logger.info(f"AI summarized {len(result)} news items for {stock_symbol}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return format_raw_news(raw_news, stock_symbol)
    except Exception as e:
        logger.error(f"AI summarization error: {e}")
        return format_raw_news(raw_news, stock_symbol)


def format_raw_news(raw_news: List[dict], stock_symbol: str) -> List[dict]:
    """Fallback: format raw news"""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            'id': hash(item['title']) & 0xffffffff,
            'title': item['title'][:100],
            'description': f"Latest {item['source']} update on {stock_symbol} stock.",
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
    """Fetch real stock news with AI summaries"""
    symbols_key = ','.join(sorted(stock_symbols or []))[:100]
    cache_key = f"gnews_v3_{symbols_key}_{limit}"
    
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
        
        logger.info(f"Searching news for: {query}")
        
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
        'title': 'Add Stocks to See News',
        'description': 'Add stock symbols like RELIANCE, TCS, INFY to see AI-summarized news.',
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
    return [{
        'id': 1,
        'title': f'No Recent News for {", ".join(valid[:3]) or "stocks"}',
        'description': 'Try adding popular stocks like RELIANCE, TCS, HDFC for better news coverage.',
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
