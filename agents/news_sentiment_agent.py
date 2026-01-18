"""
News & Sentiment Agent
Fetches financial news and analyzes sentiment.
"""
from typing import Dict, Any, List
from openai import OpenAI
from core.base_agent import BaseAgent, AgentRole, AgentDecision
from tools.tool_registry import ToolRegistry
from config import get_settings
import json


class NewsSentimentAgent(BaseAgent):
    """
    News & Sentiment Agent - Fetches and analyzes financial news sentiment.
    Uses news search and sentiment analysis to gauge market sentiment.
    """
    
    def __init__(self, tool_registry: ToolRegistry, shared_memory: Dict[str, Any] = None):
        super().__init__(
            agent_id="news_sentiment_001",
            role=AgentRole.NEWS_SENTIMENT,
            name="News & Sentiment Analyst",
            description="Fetches financial news and performs sentiment analysis",
            shared_memory=shared_memory
        )
        self.tool_registry = tool_registry
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.model = self.settings.openai_model
    
    async def reason(self, context: Dict[str, Any]) -> AgentDecision:
        """
        Analyze news sentiment for given symbols.
        Fetches news and performs sentiment analysis.
        """
        symbols = context.get("symbols", self.settings.default_tickers)
        symbol = symbols[0] if symbols else self.settings.default_tickers[0]
        
        # Fetch news using tools
        news_result = await self.tool_registry.call_tool("news_search.get_ticker_news", symbol=symbol, count=10)
        news_data = news_result.get("result", {}) if news_result.get("success") else {}
        articles = news_data.get("articles", [])
        
        # Analyze sentiment
        sentiment_result = await self.tool_registry.call_tool(
            "news_search.summarize_news_sentiment",
            symbol=symbol,
            news_articles=articles
        )
        sentiment_data = sentiment_result.get("result", {}) if sentiment_result.get("success") else {}
        
        # Extract keywords
        keywords_result = await self.tool_registry.call_tool(
            "news_search.extract_news_keywords",
            articles=articles[:5] if articles else []
        )
        keywords = keywords_result.get("result", {}).get("keywords", []) if keywords_result.get("success") else []
        
        # Use LLM to synthesize sentiment analysis
        articles_summary = "\n".join([
            f"- {a.get('title', '')}: {a.get('description', '')[:100]}..."
            for a in articles[:5]
        ]) if articles else "No news articles found"
        
        prompt = f"""
        You are a financial news sentiment analyst. Analyze news sentiment for {symbol}:
        
        Articles Found: {len(articles)}
        Sentiment Score: {sentiment_data.get('sentiment_score', 0)} (range: -1 to 1)
        Key Keywords: {', '.join(keywords[:5])}
        
        Recent Articles:
        {articles_summary}
        
        Provide:
        1. Overall sentiment assessment (positive/negative/neutral)
        2. Key themes from news (2-3 sentences)
        3. Impact on trading recommendation (buy/sell/hold)
        4. Confidence level (0-1)
        
        Format as JSON: {{"sentiment": "...", "themes": "...", "recommendation": "...", "confidence": 0.0-1.0}}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial news analyst. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content
            try:
                llm_result = json.loads(result_text)
            except:
                llm_result = {
                    "sentiment": "neutral",
                    "themes": "Limited news data available",
                    "recommendation": "hold",
                    "confidence": 0.3
                }
        except Exception as e:
            llm_result = {
                "sentiment": "neutral",
                "themes": f"Error in sentiment analysis: {str(e)}",
                "recommendation": "hold",
                "confidence": 0.0
            }
        
        # Build rationale
        rationale = f"""
        News Sentiment Analysis for {symbol}:
        - Articles Analyzed: {len(articles)}
        - Overall Sentiment: {llm_result.get('sentiment', 'neutral').upper()}
        - Sentiment Score: {sentiment_data.get('sentiment_score', 0):.2f}
        - Key Themes: {llm_result.get('themes', 'N/A')}
        - Recommendation: {llm_result.get('recommendation', 'hold').upper()}
        """.strip()
        
        decision = llm_result.get("recommendation", "hold").lower()
        confidence = float(llm_result.get("confidence", 0.3))
        
        # Update shared memory
        self.shared_memory["news_sentiment"][symbol] = {
            "sentiment": llm_result.get("sentiment"),
            "score": sentiment_data.get("sentiment_score", 0),
            "articles_count": len(articles),
            "timestamp": context.get("timestamp")
        }
        
        # Record decision
        agent_decision = self.record_decision(
            decision=decision,
            rationale=rationale,
            confidence=confidence,
            data={
                "symbol": symbol,
                "sentiment_data": sentiment_data,
                "articles_count": len(articles),
                "keywords": keywords
            }
        )
        
        # Log decision
        await self.tool_registry.call_tool(
            "logging_metrics.log_agent_decision",
            agent_id=self.agent_id,
            agent_role=self.role.value,
            decision=decision,
            rationale=rationale,
            confidence=confidence
        )
        
        return agent_decision
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get tools available to this agent."""
        return [
            tool for tool in self.tool_registry.get_tools()
            if tool["server"] in ["news_search", "logging_metrics"]
        ]
