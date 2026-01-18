"""
Notification MCP Server
Provides alert and notification tools using Pushover.
Fallback to console logging if API unavailable.
"""
from typing import Dict, Any
from datetime import datetime
import requests
from mcp_servers.base_server import BaseMCPServer, ToolParameter, ToolParameterType
from config import get_settings


class NotificationServer(BaseMCPServer):
    """Notification Server - Pushover API integration."""
    
    def __init__(self):
        super().__init__(
            server_name="notification",
            description="Provides alert and notification services via Pushover API"
        )
        self.settings = get_settings()
        self.user_key = self.settings.pushover_user_key
        self.api_token = self.settings.pushover_api_token
        self.pushover_url = "https://api.pushover.net/1/messages.json"
    
    def _register_tools(self):
        """Register notification tools."""
        
        # Tool 24: Send trade alert
        self.register_tool(
            name="send_trade_alert",
            description="Send a trade execution alert",
            parameters=[
                ToolParameter("message", ToolParameterType.STRING, "Alert message", True),
                ToolParameter("title", ToolParameterType.STRING, "Alert title", False, "Trading Alert"),
                ToolParameter("priority", ToolParameterType.INTEGER, "Priority (0=normal, 1=high, 2=emergency)", False, 0)
            ],
            handler=self._send_trade_alert
        )
        
        # Tool 25: Send risk alert
        self.register_tool(
            name="send_risk_alert",
            description="Send a risk management alert",
            parameters=[
                ToolParameter("message", ToolParameterType.STRING, "Alert message", True),
                ToolParameter("risk_level", ToolParameterType.STRING, "Risk level (low/medium/high)", False, "medium")
            ],
            handler=self._send_risk_alert
        )
        
        # Tool 26: Send portfolio update
        self.register_tool(
            name="send_portfolio_update",
            description="Send portfolio status update",
            parameters=[
                ToolParameter("portfolio_data", ToolParameterType.OBJECT, "Portfolio data dictionary", True)
            ],
            handler=self._send_portfolio_update
        )
        
        # Tool 27: Send market alert
        self.register_tool(
            name="send_market_alert",
            description="Send market condition alert",
            parameters=[
                ToolParameter("message", ToolParameterType.STRING, "Alert message", True),
                ToolParameter("symbol", ToolParameterType.STRING, "Stock symbol (optional)", False)
            ],
            handler=self._send_market_alert
        )
        
        # Tool 28: Send notification
        self.register_tool(
            name="send_notification",
            description="Send a generic notification",
            parameters=[
                ToolParameter("message", ToolParameterType.STRING, "Notification message", True),
                ToolParameter("title", ToolParameterType.STRING, "Notification title", False, "Trading System"),
                ToolParameter("notification_type", ToolParameterType.STRING, "Type: info, warning, error, success", False, "info")
            ],
            handler=self._send_notification
        )
    
    def _send_trade_alert(self, message: str, title: str = "Trading Alert", priority: int = 0) -> Dict[str, Any]:
        """Send trade execution alert."""
        full_message = f"{message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self._send_pushover(title, full_message, priority)
    
    def _send_risk_alert(self, message: str, risk_level: str = "medium") -> Dict[str, Any]:
        """Send risk management alert."""
        priority_map = {"low": 0, "medium": 1, "high": 2}
        priority = priority_map.get(risk_level, 1)
        title = f"Risk Alert: {risk_level.upper()}"
        full_message = f"{message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self._send_pushover(title, full_message, priority)
    
    def _send_portfolio_update(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send portfolio status update."""
        total_value = portfolio_data.get("total_value", 0)
        cash = portfolio_data.get("cash", 0)
        positions_value = portfolio_data.get("positions_value", 0)
        
        message = f"""Portfolio Update:
Total Value: ${total_value:,.2f}
Cash: ${cash:,.2f}
Positions: ${positions_value:,.2f}"""
        
        return self._send_pushover("Portfolio Update", message, 0)
    
    def _send_market_alert(self, message: str, symbol: str = None) -> Dict[str, Any]:
        """Send market condition alert."""
        title = f"Market Alert" + (f": {symbol}" if symbol else "")
        full_message = f"{message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self._send_pushover(title, full_message, 1)
    
    def _send_notification(self, message: str, title: str = "Trading System", notification_type: str = "info") -> Dict[str, Any]:
        """Send generic notification."""
        icons = {"info": "[INFO]", "warning": "[WARNING]", "error": "[ERROR]", "success": "[SUCCESS]"}
        icon = icons.get(notification_type, "[INFO]")
        full_title = f"{icon} {title}"
        return self._send_pushover(full_title, message, 0)
    
    def _send_pushover(self, title: str, message: str, priority: int = 0) -> Dict[str, Any]:
        """Send notification via Pushover API."""
        if not self.user_key or not self.api_token:
            # Fallback to console
            print(f"[PUSHOVER] {title}: {message}")
            return {
                "success": True,
                "method": "console",
                "message": "Pushover not configured, logged to console"
            }
        
        try:
            payload = {
                "token": self.api_token,
                "user": self.user_key,
                "title": title,
                "message": message,
                "priority": priority
            }
            
            response = requests.post(self.pushover_url, data=payload, timeout=5)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "method": "pushover",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                print(f"[PUSHOVER ERROR] {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "method": "pushover",
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            print(f"[PUSHOVER ERROR] {str(e)}")
            return {
                "success": False,
                "method": "pushover",
                "error": str(e)
            }
