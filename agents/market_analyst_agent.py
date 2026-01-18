"""
Market Analyst Agent
Analyzes real-time market data and technical indicators.
"""
from typing import Dict, Any, List
from openai import OpenAI
from core.base_agent import BaseAgent, AgentRole, AgentDecision
from tools.tool_registry import ToolRegistry
from config import get_settings
import json


class MarketAnalystAgent(BaseAgent):
    """
    Market Analyst Agent - Analyzes market data and trends.
    Uses technical indicators and price action to assess market conditions.
    """
    
    def __init__(self, tool_registry: ToolRegistry, shared_memory: Dict[str, Any] = None):
        super().__init__(
            agent_id="market_analyst_001",
            role=AgentRole.MARKET_ANALYST,
            name="Market Analyst",
            description="Analyzes real-time market data, technical indicators, and price trends",
            shared_memory=shared_memory
        )
        self.tool_registry = tool_registry
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.model = self.settings.openai_model
    
    async def reason(self, context: Dict[str, Any]) -> AgentDecision:
        """
        Analyze market conditions for given symbols.
        Uses market data and technical analysis tools.
        """
        symbols = context.get("symbols", self.settings.default_tickers)
        symbol = symbols[0] if symbols else self.settings.default_tickers[0]
        
        # Gather market data using tools
        price_result = await self.tool_registry.call_tool("market_data.get_latest_price", symbol=symbol)
        candles_result = await self.tool_registry.call_tool("market_data.fetch_intraday_candles", symbol=symbol, interval="15min", limit=100)
        
        price_data = price_result.get("result", {}) if price_result.get("success") else {}
        candles_data = candles_result.get("result", {}) if candles_result.get("success") else {}
        
        # Compute technical indicators
        candles = candles_data.get("candles", [])
        if candles:
            closes = [c["close"] for c in candles]
            indicators_result = await self.tool_registry.call_tool(
                "strategy_reasoning.compute_technical_indicators",
                prices=closes,
                indicators=["rsi", "sma", "ema", "macd"]
            )
            indicators = indicators_result.get("result", {}).get("indicators", {}) if indicators_result.get("success") else {}
        else:
            indicators = {}
        
        # Analyze trend using LLM
        analysis_data = {
            "symbol": symbol,
            "current_price": price_data.get("price"),
            "indicators": indicators,
            "recent_candles": candles[-5:] if candles else []
        }
        
        trend_result = await self.tool_registry.call_tool(
            "strategy_reasoning.analyze_market_trend",
            symbol=symbol,
            price_data=analysis_data
        )
        trend_analysis = trend_result.get("result", {}) if trend_result.get("success") else {}
        
        # Use LLM to synthesize analysis
        prompt = f"""
        You are a market analyst. Analyze the following market data for {symbol}:
        
        Current Price: ${price_data.get('price', 'N/A')}
        Technical Indicators:
        {json.dumps(indicators, indent=2)}
        
        Trend Analysis: {trend_analysis.get('trend', 'neutral')}
        
        Provide:
        1. Market assessment (bullish/bearish/neutral)
        2. Key technical signals (2-3 sentences)
        3. Confidence level (0-1)
        4. Recommendation (buy/sell/hold signal)
        
        Format as JSON: {{"assessment": "...", "signals": "...", "confidence": 0.0-1.0, "recommendation": "..."}}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a quantitative market analyst. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content
            try:
                llm_result = json.loads(result_text)
            except:
                llm_result = {
                    "assessment": "neutral",
                    "signals": "Insufficient data for analysis",
                    "confidence": 0.5,
                    "recommendation": "hold"
                }
        except Exception as e:
            llm_result = {
                "assessment": "unknown",
                "signals": f"Error in analysis: {str(e)}",
                "confidence": 0.0,
                "recommendation": "hold"
            }
        
        # Build rationale
        rationale = f"""
        Market Analysis for {symbol}:
        - Current Price: ${price_data.get('price', 'N/A')}
        - Technical Assessment: {llm_result.get('assessment', 'neutral')}
        - Key Signals: {llm_result.get('signals', 'N/A')}
        - RSI: {indicators.get('rsi', 'N/A'):.2f} (if available)
        - Recommendation: {llm_result.get('recommendation', 'hold').upper()}
        """.strip()
        
        decision = llm_result.get("recommendation", "hold").lower()
        confidence = float(llm_result.get("confidence", 0.5))
        
        # Record decision
        agent_decision = self.record_decision(
            decision=decision,
            rationale=rationale,
            confidence=confidence,
            data={
                "symbol": symbol,
                "price": price_data.get("price"),
                "indicators": indicators,
                "trend_analysis": trend_analysis
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
            if tool["server"] in ["market_data", "strategy_reasoning", "logging_metrics"]
        ]
