"""
Strategy Reasoning MCP Server
Provides LLM-based strategy and technical analysis tools.
"""
from typing import Dict, Any, List
from datetime import datetime
from openai import OpenAI
from mcp_servers.base_server import BaseMCPServer, ToolParameter, ToolParameterType
from config import get_settings
import json
import pandas as pd
import numpy as np


class StrategyServer(BaseMCPServer):
    """Strategy Reasoning Server - LLM orchestration for trade reasoning."""
    
    def __init__(self):
        super().__init__(
            server_name="strategy_reasoning",
            description="Provides LLM-based strategy reasoning and technical analysis"
        )
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.model = self.settings.openai_model
    
    def _register_tools(self):
        """Register strategy and reasoning tools."""
        
        # Tool 11: Analyze market trend
        self.register_tool(
            name="analyze_market_trend",
            description="Analyze market trend using price data and LLM reasoning",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("price_data", ToolParameterType.OBJECT, "Price data object with candles", False)
            ],
            handler=self._analyze_market_trend
        )
        
        # Tool 12: Generate trade rationale
        self.register_tool(
            name="generate_trade_rationale",
            description="Generate LLM-based reasoning for a trade decision",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("action", ToolParameterType.STRING, "Proposed action (buy/sell/hold)", True),
                ToolParameter("context", ToolParameterType.OBJECT, "Trading context (price, indicators, news)", True)
            ],
            handler=self._generate_trade_rationale
        )
        
        # Tool 13: Compute technical indicators
        self.register_tool(
            name="compute_technical_indicators",
            description="Calculate technical indicators (RSI, MACD, etc.) from price data",
            parameters=[
                ToolParameter("prices", ToolParameterType.ARRAY, "Array of close prices", True),
                ToolParameter("indicators", ToolParameterType.ARRAY, "List of indicators to compute", False)
            ],
            handler=self._compute_technical_indicators
        )
        
        # Tool 14: Evaluate strategy
        self.register_tool(
            name="evaluate_strategy",
            description="Evaluate trading strategy performance",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("strategy_data", ToolParameterType.OBJECT, "Strategy performance data", True)
            ],
            handler=self._evaluate_strategy
        )
        
        # Tool 15: Generate market summary
        self.register_tool(
            name="generate_market_summary",
            description="Generate LLM summary of market conditions",
            parameters=[
                ToolParameter("symbols", ToolParameterType.ARRAY, "List of symbols to analyze", True),
                ToolParameter("market_data", ToolParameterType.OBJECT, "Aggregated market data", False)
            ],
            handler=self._generate_market_summary
        )
    
    def _analyze_market_trend(self, symbol: str, price_data: Dict = None) -> Dict[str, Any]:
        """Analyze market trend using LLM."""
        if price_data is None:
            price_data = {"message": "No price data provided"}
        
        prompt = f"""
        Analyze the market trend for {symbol} based on the following data:
        {json.dumps(price_data, indent=2)}
        
        Provide:
        1. Trend direction (bullish/bearish/neutral)
        2. Key technical observations
        3. Confidence level (0-1)
        4. Brief summary
        
        Format as JSON with keys: trend, observations, confidence, summary.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a quantitative analyst. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content
            # Try to parse JSON from response
            try:
                result = json.loads(result_text)
            except:
                result = {"trend": "neutral", "summary": result_text, "confidence": 0.5}
            
            return {"symbol": symbol, **result}
        except Exception as e:
            return {"symbol": symbol, "trend": "unknown", "error": str(e)}
    
    def _generate_trade_rationale(self, symbol: str, action: str, context: Dict) -> Dict[str, Any]:
        """Generate trade rationale using LLM."""
        prompt = f"""
        Generate a concise trade rationale for {symbol}:
        - Action: {action}
        - Context: {json.dumps(context, indent=2)}
        
        Provide:
        1. Rationale (2-3 sentences explaining why)
        2. Key factors influencing the decision
        3. Risk considerations
        
        Format as JSON with keys: rationale, key_factors, risk_considerations.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a trading analyst. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=250
            )
            
            result_text = response.choices[0].message.content
            try:
                result = json.loads(result_text)
            except:
                result = {"rationale": result_text}
            
            return {"symbol": symbol, "action": action, **result}
        except Exception as e:
            return {"symbol": symbol, "action": action, "rationale": f"Error: {str(e)}"}
    
    def _compute_technical_indicators(self, prices: List[float], indicators: List[str] = None) -> Dict[str, Any]:
        """Compute technical indicators."""
        if indicators is None:
            indicators = ["rsi", "sma", "ema"]
        
        # Convert to pandas Series
        price_series = pd.Series(prices)
        result = {}
        
        # RSI
        if "rsi" in indicators:
            result["rsi"] = self._calculate_rsi(price_series, period=14)
        
        # SMA
        if "sma" in indicators:
            result["sma_20"] = float(price_series.tail(20).mean()) if len(price_series) >= 20 else None
            result["sma_50"] = float(price_series.tail(50).mean()) if len(price_series) >= 50 else None
        
        # EMA
        if "ema" in indicators:
            result["ema_12"] = float(price_series.ewm(span=12).mean().iloc[-1])
            result["ema_26"] = float(price_series.ewm(span=26).mean().iloc[-1])
        
        # MACD
        if "macd" in indicators:
            ema12 = price_series.ewm(span=12).mean()
            ema26 = price_series.ewm(span=26).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9).mean()
            result["macd"] = float(macd_line.iloc[-1])
            result["macd_signal"] = float(signal_line.iloc[-1])
        
        return {"indicators": result, "periods": len(prices)}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty else 50.0
    
    def _evaluate_strategy(self, symbol: str, strategy_data: Dict) -> Dict[str, Any]:
        """Evaluate strategy performance."""
        # Simplified evaluation
        return {
            "symbol": symbol,
            "evaluation": "Strategy evaluation based on performance metrics",
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_market_summary(self, symbols: List[str], market_data: Dict = None) -> Dict[str, Any]:
        """Generate market summary using LLM."""
        prompt = f"""
        Provide a brief market summary for these symbols: {', '.join(symbols)}.
        {f'Market data: {json.dumps(market_data, indent=2)}' if market_data else ''}
        
        Format as JSON with: summary, key_insights, overall_sentiment.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a market analyst. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content
            try:
                result = json.loads(result_text)
            except:
                result = {"summary": result_text}
            
            return {"symbols": symbols, **result}
        except Exception as e:
            return {"symbols": symbols, "summary": f"Error: {str(e)}"}
