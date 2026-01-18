"""
Market Data MCP Server
Provides market data tools using Polygon API.
Fallback to mock data if API unavailable.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests
from mcp_servers.base_server import BaseMCPServer, ToolParameter, ToolParameterType
from config import get_settings


class MarketDataServer(BaseMCPServer):
    """Market Data Server - Polygon API integration."""
    
    def __init__(self):
        super().__init__(
            server_name="market_data",
            description="Provides real-time and historical market data via Polygon API"
        )
        self.settings = get_settings()
        self.api_key = self.settings.polygon_api_key
        self.base_url = "https://api.polygon.io"
        self.cache: Dict[str, Any] = {}
    
    def _register_tools(self):
        """Register market data tools."""
        
        # Tool 1: Get latest price
        self.register_tool(
            name="get_latest_price",
            description="Get the latest price for a stock symbol",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol (e.g., AAPL)", True)
            ],
            handler=self._get_latest_price
        )
        
        # Tool 2: Get intraday candles
        self.register_tool(
            name="fetch_intraday_candles",
            description="Fetch intraday candlestick data for a symbol",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("interval", ToolParameterType.STRING, "Candle interval (1min, 5min, 15min, 1hour)", False, "15min"),
                ToolParameter("limit", ToolParameterType.INTEGER, "Number of candles to fetch", False, 100)
            ],
            handler=self._fetch_intraday_candles
        )
        
        # Tool 3: Get daily aggregates
        self.register_tool(
            name="get_daily_aggregates",
            description="Get daily aggregated price data",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("days", ToolParameterType.INTEGER, "Number of days of data", False, 30)
            ],
            handler=self._get_daily_aggregates
        )
        
        # Tool 4: Get ticker details
        self.register_tool(
            name="get_ticker_details",
            description="Get detailed information about a ticker",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True)
            ],
            handler=self._get_ticker_details
        )
        
        # Tool 5: Get market status
        self.register_tool(
            name="get_market_status",
            description="Check if market is currently open",
            parameters=[],
            handler=self._get_market_status
        )
    
    def _get_latest_price(self, symbol: str) -> Dict[str, Any]:
        """Get latest price for a symbol."""
        cache_key = f"price_{symbol}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < 60:  # 1 min cache
                return cached_data
        
        try:
            url = f"{self.base_url}/v2/last/nbbo/{symbol}"
            params = {"apikey": self.api_key}
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                price_data = {
                    "symbol": symbol,
                    "price": data.get("results", {}).get("P", 0),
                    "timestamp": datetime.now().isoformat(),
                    "source": "polygon"
                }
                self.cache[cache_key] = (datetime.now(), price_data)
                return price_data
            else:
                return self._mock_price(symbol)
        except Exception as e:
            return self._mock_price(symbol)
    
    def _fetch_intraday_candles(self, symbol: str, interval: str = "15min", limit: int = 100) -> Dict[str, Any]:
        """Fetch intraday candle data."""
        try:
            # Convert interval to Polygon format
            multiplier_map = {"1min": 1, "5min": 5, "15min": 15, "1hour": 60}
            multiplier = multiplier_map.get(interval, 15)
            timespan = "minute" if multiplier < 60 else "hour"
            
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{datetime.now().strftime('%Y-%m-%d')}/{datetime.now().strftime('%Y-%m-%d')}"
            params = {"apikey": self.api_key, "limit": limit, "adjusted": "true"}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                candles = [
                    {
                        "timestamp": datetime.fromtimestamp(r["t"] / 1000).isoformat(),
                        "open": r["o"],
                        "high": r["h"],
                        "low": r["l"],
                        "close": r["c"],
                        "volume": r["v"]
                    }
                    for r in results
                ]
                return {"symbol": symbol, "interval": interval, "candles": candles, "count": len(candles)}
            else:
                return self._mock_candles(symbol, interval, limit)
        except Exception as e:
            return self._mock_candles(symbol, interval, limit)
    
    def _get_daily_aggregates(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        """Get daily aggregates."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            params = {"apikey": self.api_key, "adjusted": "true", "sort": "asc"}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                daily_data = [
                    {
                        "date": datetime.fromtimestamp(r["t"] / 1000).strftime("%Y-%m-%d"),
                        "open": r["o"],
                        "high": r["h"],
                        "low": r["l"],
                        "close": r["c"],
                        "volume": r["v"]
                    }
                    for r in results
                ]
                return {"symbol": symbol, "days": days, "data": daily_data}
            else:
                return self._mock_daily_data(symbol, days)
        except Exception as e:
            return self._mock_daily_data(symbol, days)
    
    def _get_ticker_details(self, symbol: str) -> Dict[str, Any]:
        """Get ticker details."""
        try:
            url = f"{self.base_url}/v3/reference/tickers/{symbol}"
            params = {"apikey": self.api_key}
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("results", {})
                return {
                    "symbol": symbol,
                    "name": result.get("name", ""),
                    "description": result.get("description", ""),
                    "market": result.get("market", ""),
                    "currency": result.get("currency_name", ""),
                    "locale": result.get("locale", "")
                }
            else:
                return {"symbol": symbol, "name": f"{symbol} Inc.", "error": "API unavailable"}
        except Exception as e:
            return {"symbol": symbol, "name": f"{symbol} Inc.", "error": str(e)}
    
    def _get_market_status(self) -> Dict[str, Any]:
        """Get market status."""
        try:
            url = f"{self.base_url}/v1/marketstatus/now"
            params = {"apikey": self.api_key}
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "market": "open" if data.get("market") == "open" else "closed",
                    "exchanges": data.get("exchanges", {}),
                    "server_time": data.get("serverTime", datetime.now().isoformat())
                }
            else:
                return {"market": "unknown", "note": "API unavailable"}
        except Exception as e:
            return {"market": "unknown", "note": str(e)}
    
    # Mock data fallbacks
    def _mock_price(self, symbol: str) -> Dict[str, Any]:
        """Mock price data when API unavailable."""
        import random
        base_prices = {"AAPL": 180, "MSFT": 380, "GOOGL": 140, "AMZN": 150, "TSLA": 250}
        base = base_prices.get(symbol, 100)
        price = base * (1 + random.uniform(-0.02, 0.02))
        return {"symbol": symbol, "price": round(price, 2), "timestamp": datetime.now().isoformat(), "source": "mock"}
    
    def _mock_candles(self, symbol: str, interval: str, limit: int) -> Dict[str, Any]:
        """Mock candle data."""
        import random
        base_prices = {"AAPL": 180, "MSFT": 380, "GOOGL": 140, "AMZN": 150, "TSLA": 250}
        base = base_prices.get(symbol, 100)
        candles = []
        current_price = base
        
        for i in range(limit):
            current_price *= (1 + random.uniform(-0.01, 0.01))
            candles.append({
                "timestamp": (datetime.now() - timedelta(minutes=(limit-i)*15)).isoformat(),
                "open": round(current_price * 0.999, 2),
                "high": round(current_price * 1.002, 2),
                "low": round(current_price * 0.998, 2),
                "close": round(current_price, 2),
                "volume": random.randint(1000000, 5000000)
            })
        return {"symbol": symbol, "interval": interval, "candles": candles, "count": len(candles), "source": "mock"}
    
    def _mock_daily_data(self, symbol: str, days: int) -> Dict[str, Any]:
        """Mock daily data."""
        import random
        base_prices = {"AAPL": 180, "MSFT": 380, "GOOGL": 140, "AMZN": 150, "TSLA": 250}
        base = base_prices.get(symbol, 100)
        data = []
        current_price = base
        
        for i in range(days):
            current_price *= (1 + random.uniform(-0.03, 0.03))
            data.append({
                "date": (datetime.now() - timedelta(days=days-i)).strftime("%Y-%m-%d"),
                "open": round(current_price * 0.99, 2),
                "high": round(current_price * 1.02, 2),
                "low": round(current_price * 0.98, 2),
                "close": round(current_price, 2),
                "volume": random.randint(10000000, 50000000)
            })
        return {"symbol": symbol, "days": days, "data": data, "source": "mock"}
