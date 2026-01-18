"""
News & Search MCP Server
Provides financial news and sentiment tools using Brave API.
Fallback to mock data if API unavailable.
"""
from typing import Dict, Any, List
from datetime import datetime
import requests
from mcp_servers.base_server import BaseMCPServer, ToolParameter, ToolParameterType
from config import get_settings


class NewsServer(BaseMCPServer):
    """News Server - Brave Search API integration."""
    
    def __init__(self):
        super().__init__(
            server_name="news_search",
            description="Provides financial news search and sentiment analysis via Brave API"
        )
        self.settings = get_settings()
        self.api_key = self.settings.brave_api_key
        self.base_url = "https://api.search.brave.com/res/v1"
    
    def _register_tools(self):
        """Register news and sentiment tools."""
        
        # Tool 6: Search financial news
        self.register_tool(
            name="search_financial_news",
            description="Search for financial news about a ticker or topic",
            parameters=[
                ToolParameter("query", ToolParameterType.STRING, "Search query (ticker symbol or topic)", True),
                ToolParameter("count", ToolParameterType.INTEGER, "Number of articles to return", False, 10)
            ],
            handler=self._search_financial_news
        )
        
        # Tool 7: Get ticker news
        self.register_tool(
            name="get_ticker_news",
            description="Get recent news for a specific ticker",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("count", ToolParameterType.INTEGER, "Number of articles", False, 10)
            ],
            handler=self._get_ticker_news
        )
        
        # Tool 8: Summarize news sentiment
        self.register_tool(
            name="summarize_news_sentiment",
            description="Analyze and summarize sentiment from news articles",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("news_articles", ToolParameterType.ARRAY, "Array of news article objects", False)
            ],
            handler=self._summarize_news_sentiment
        )
        
        # Tool 9: Get market news
        self.register_tool(
            name="get_market_news",
            description="Get general market news",
            parameters=[
                ToolParameter("count", ToolParameterType.INTEGER, "Number of articles", False, 10)
            ],
            handler=self._get_market_news
        )
        
        # Tool 10: Extract news keywords
        self.register_tool(
            name="extract_news_keywords",
            description="Extract key terms and keywords from news",
            parameters=[
                ToolParameter("articles", ToolParameterType.ARRAY, "Array of news articles", True)
            ],
            handler=self._extract_news_keywords
        )
    
    def _search_financial_news(self, query: str, count: int = 10) -> Dict[str, Any]:
        """Search for financial news."""
        try:
            url = f"{self.base_url}/news/search"
            headers = {"X-Subscription-Token": self.api_key}
            params = {
                "q": f"{query} stock financial news",
                "count": min(count, 20),
                "freshness": "pw"  # Past week
            }
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("web", {}).get("results", [])
                articles = [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "description": r.get("description", ""),
                        "published_time": r.get("age", ""),
                        "source": r.get("meta_url", {}).get("hostname", "")
                    }
                    for r in results[:count]
                ]
                return {"query": query, "articles": articles, "count": len(articles)}
            else:
                return self._mock_news(query, count)
        except Exception as e:
            return self._mock_news(query, count)
    
    def _get_ticker_news(self, symbol: str, count: int = 10) -> Dict[str, Any]:
        """Get news for a specific ticker."""
        return self._search_financial_news(f"{symbol} stock", count)
    
    def _summarize_news_sentiment(self, symbol: str, news_articles: List[Dict] = None) -> Dict[str, Any]:
        """Summarize sentiment from news (simplified - would use LLM in production)."""
        if news_articles is None:
            news_result = self._get_ticker_news(symbol, 10)
            news_articles = news_result.get("articles", [])
        
        # Simple keyword-based sentiment (in production, use LLM)
        positive_keywords = ["surge", "gain", "growth", "beat", "strong", "up", "rally", "profit"]
        negative_keywords = ["fall", "drop", "decline", "miss", "weak", "down", "loss", "risk"]
        
        sentiment_scores = []
        for article in news_articles:
            text = (article.get("title", "") + " " + article.get("description", "")).lower()
            pos_count = sum(1 for kw in positive_keywords if kw in text)
            neg_count = sum(1 for kw in negative_keywords if kw in text)
            
            if pos_count > neg_count:
                sentiment_scores.append(1)
            elif neg_count > pos_count:
                sentiment_scores.append(-1)
            else:
                sentiment_scores.append(0)
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        return {
            "symbol": symbol,
            "sentiment_score": round(avg_sentiment, 2),  # -1 to 1
            "sentiment_label": "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral",
            "articles_analyzed": len(news_articles),
            "method": "keyword_based"
        }
    
    def _get_market_news(self, count: int = 10) -> Dict[str, Any]:
        """Get general market news."""
        return self._search_financial_news("stock market financial news", count)
    
    def _extract_news_keywords(self, articles: List[Dict]) -> Dict[str, Any]:
        """Extract keywords from news articles."""
        from collections import Counter
        import re
        
        all_text = " ".join([
            article.get("title", "") + " " + article.get("description", "")
            for article in articles
        ]).lower()
        
        # Extract words (simplified)
        words = re.findall(r'\b[a-z]{4,}\b', all_text)
        financial_terms = [
            "stock", "market", "trading", "price", "earnings", "revenue", "profit",
            "growth", "investor", "share", "dividend", "analyst", "forecast"
        ]
        
        word_counts = Counter(words)
        keywords = [word for word, count in word_counts.most_common(20) if word not in financial_terms]
        
        return {"keywords": keywords[:10], "articles_processed": len(articles)}
    
    def _mock_news(self, query: str, count: int) -> Dict[str, Any]:
        """Mock news data."""
        articles = []
        for i in range(count):
            articles.append({
                "title": f"Financial News: {query} shows {['strong', 'mixed', 'volatile'][i % 3]} performance",
                "url": f"https://example.com/news/{i}",
                "description": f"Recent developments in {query} indicate market interest.",
                "published_time": f"{(count-i)} hours ago",
                "source": "example.com"
            })
        return {"query": query, "articles": articles, "count": len(articles), "source": "mock"}
