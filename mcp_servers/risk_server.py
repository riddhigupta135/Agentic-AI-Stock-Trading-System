"""
Risk & Portfolio MCP Server
Provides risk management and portfolio tracking tools.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from mcp_servers.base_server import BaseMCPServer, ToolParameter, ToolParameterType
from config import get_settings


class RiskServer(BaseMCPServer):
    """Risk & Portfolio Server - Risk management and position tracking."""
    
    def __init__(self):
        super().__init__(
            server_name="risk_portfolio",
            description="Provides risk management, position sizing, and portfolio tracking"
        )
        self.settings = get_settings()
        self.portfolio = {
            "cash": self.settings.initial_capital,
            "positions": {},  # {symbol: {"quantity": int, "avg_price": float, "current_price": float}}
            "trade_history": []
        }
    
    def _register_tools(self):
        """Register risk and portfolio tools."""
        
        # Tool 16: Assess trade risk
        self.register_tool(
            name="assess_trade_risk",
            description="Assess risk for a proposed trade",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("action", ToolParameterType.STRING, "Action: buy, sell, hold", True),
                ToolParameter("quantity", ToolParameterType.INTEGER, "Number of shares", False),
                ToolParameter("price", ToolParameterType.FLOAT, "Trade price", True)
            ],
            handler=self._assess_trade_risk
        )
        
        # Tool 17: Calculate position size
        self.register_tool(
            name="calculate_position_size",
            description="Calculate appropriate position size based on risk limits",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("entry_price", ToolParameterType.FLOAT, "Entry price", True),
                ToolParameter("stop_loss", ToolParameterType.FLOAT, "Stop loss price", False),
                ToolParameter("risk_amount", ToolParameterType.FLOAT, "Amount to risk (dollars)", False)
            ],
            handler=self._calculate_position_size
        )
        
        # Tool 18: Get portfolio value
        self.register_tool(
            name="get_portfolio_value",
            description="Get current portfolio total value",
            parameters=[],
            handler=self._get_portfolio_value
        )
        
        # Tool 19: Get position info
        self.register_tool(
            name="get_position_info",
            description="Get information about a specific position",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True)
            ],
            handler=self._get_position_info
        )
        
        # Tool 20: Check risk limits
        self.register_tool(
            name="check_risk_limits",
            description="Check if a trade violates risk limits",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("trade_value", ToolParameterType.FLOAT, "Total trade value", True)
            ],
            handler=self._check_risk_limits
        )
        
        # Tool 21: Get portfolio allocation
        self.register_tool(
            name="get_portfolio_allocation",
            description="Get portfolio allocation percentages",
            parameters=[],
            handler=self._get_portfolio_allocation
        )
        
        # Tool 22: Calculate portfolio metrics
        self.register_tool(
            name="calculate_portfolio_metrics",
            description="Calculate portfolio performance metrics",
            parameters=[],
            handler=self._calculate_portfolio_metrics
        )
        
        # Tool 23: Record trade
        self.register_tool(
            name="record_trade",
            description="Record a trade in portfolio",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("action", ToolParameterType.STRING, "buy or sell", True),
                ToolParameter("quantity", ToolParameterType.INTEGER, "Number of shares", True),
                ToolParameter("price", ToolParameterType.FLOAT, "Trade price", True),
                ToolParameter("timestamp", ToolParameterType.STRING, "Trade timestamp", False)
            ],
            handler=self._record_trade
        )
    
    def _assess_trade_risk(self, symbol: str, action: str, quantity: int = None, price: float = 0) -> Dict[str, Any]:
        """Assess risk for a trade."""
        portfolio_value = self._get_portfolio_value()["total_value"]
        
        if action == "buy" and quantity and price:
            trade_value = quantity * price
            position_pct = (trade_value / portfolio_value) if portfolio_value > 0 else 0
            
            risk_score = 0.0
            risk_factors = []
            
            # Check position size limit
            if position_pct > self.settings.max_position_size:
                risk_score += 0.5
                risk_factors.append(f"Exceeds max position size ({position_pct:.2%} > {self.settings.max_position_size:.2%})")
            
            # Check available cash
            if trade_value > self.portfolio["cash"]:
                risk_score = 1.0
                risk_factors.append("Insufficient cash")
            
            # Check concentration risk
            current_positions_value = sum(
                pos["quantity"] * pos.get("current_price", pos["avg_price"])
                for pos in self.portfolio["positions"].values()
            )
            if (current_positions_value + trade_value) / portfolio_value > 0.8:
                risk_score += 0.2
                risk_factors.append("High portfolio concentration")
            
            return {
                "symbol": symbol,
                "action": action,
                "risk_score": min(risk_score, 1.0),  # 0-1 scale
                "risk_level": "low" if risk_score < 0.3 else "medium" if risk_score < 0.7 else "high",
                "risk_factors": risk_factors,
                "recommendation": "proceed" if risk_score < 0.5 else "caution" if risk_score < 0.8 else "reject"
            }
        else:
            return {"symbol": symbol, "action": action, "risk_score": 0.0, "risk_level": "low"}
    
    def _calculate_position_size(self, symbol: str, entry_price: float, stop_loss: float = None, risk_amount: float = None) -> Dict[str, Any]:
        """Calculate position size based on risk."""
        portfolio_value = self._get_portfolio_value()["total_value"]
        
        if risk_amount is None:
            risk_amount = portfolio_value * self.settings.risk_per_trade
        
        if stop_loss is None:
            stop_loss = entry_price * 0.95  # Default 5% stop loss
        
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share == 0:
            risk_per_share = entry_price * 0.05
        
        position_size = int(risk_amount / risk_per_share)
        trade_value = position_size * entry_price
        
        # Apply max position size limit
        max_trade_value = portfolio_value * self.settings.max_position_size
        if trade_value > max_trade_value:
            position_size = int(max_trade_value / entry_price)
            trade_value = position_size * entry_price
        
        # Check cash constraint
        if trade_value > self.portfolio["cash"]:
            position_size = int(self.portfolio["cash"] / entry_price)
            trade_value = position_size * entry_price
        
        return {
            "symbol": symbol,
            "recommended_quantity": max(0, position_size),
            "trade_value": round(trade_value, 2),
            "risk_per_share": round(risk_per_share, 2),
            "total_risk": round(position_size * risk_per_share, 2),
            "risk_percentage": round((position_size * risk_per_share / portfolio_value) * 100, 2)
        }
    
    def _get_portfolio_value(self) -> Dict[str, Any]:
        """Get portfolio total value."""
        positions_value = sum(
            pos["quantity"] * pos.get("current_price", pos["avg_price"])
            for pos in self.portfolio["positions"].values()
        )
        total_value = self.portfolio["cash"] + positions_value
        
        return {
            "cash": round(self.portfolio["cash"], 2),
            "positions_value": round(positions_value, 2),
            "total_value": round(total_value, 2),
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_position_info(self, symbol: str) -> Dict[str, Any]:
        """Get position information."""
        position = self.portfolio["positions"].get(symbol)
        if not position:
            return {"symbol": symbol, "position": None, "message": "No position found"}
        
        current_value = position["quantity"] * position.get("current_price", position["avg_price"])
        cost_basis = position["quantity"] * position["avg_price"]
        unrealized_pnl = current_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
        
        return {
            "symbol": symbol,
            "quantity": position["quantity"],
            "avg_price": position["avg_price"],
            "current_price": position.get("current_price", position["avg_price"]),
            "cost_basis": round(cost_basis, 2),
            "current_value": round(current_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2)
        }
    
    def _check_risk_limits(self, symbol: str, trade_value: float) -> Dict[str, Any]:
        """Check if trade violates risk limits."""
        portfolio_value = self._get_portfolio_value()["total_value"]
        position_pct = (trade_value / portfolio_value) if portfolio_value > 0 else 0
        
        violations = []
        is_valid = True
        
        if position_pct > self.settings.max_position_size:
            violations.append(f"Exceeds max position size: {position_pct:.2%} > {self.settings.max_position_size:.2%}")
            is_valid = False
        
        if trade_value > self.portfolio["cash"]:
            violations.append(f"Insufficient cash: ${trade_value:.2f} > ${self.portfolio['cash']:.2f}")
            is_valid = False
        
        return {
            "symbol": symbol,
            "trade_value": trade_value,
            "is_valid": is_valid,
            "violations": violations,
            "position_percentage": round(position_pct * 100, 2)
        }
    
    def _get_portfolio_allocation(self) -> Dict[str, Any]:
        """Get portfolio allocation."""
        portfolio_value = self._get_portfolio_value()
        total_value = portfolio_value["total_value"]
        
        if total_value == 0:
            return {"cash_pct": 100, "positions": {}}
        
        allocations = {}
        for symbol, position in self.portfolio["positions"].items():
            position_value = position["quantity"] * position.get("current_price", position["avg_price"])
            allocations[symbol] = round((position_value / total_value) * 100, 2)
        
        cash_pct = round((self.portfolio["cash"] / total_value) * 100, 2)
        
        return {
            "cash_pct": cash_pct,
            "positions": allocations,
            "total_value": total_value
        }
    
    def _calculate_portfolio_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio metrics."""
        initial_capital = self.settings.initial_capital
        current_value = self._get_portfolio_value()["total_value"]
        
        total_return = current_value - initial_capital
        total_return_pct = (total_return / initial_capital * 100) if initial_capital > 0 else 0
        
        # Count trades
        num_trades = len(self.portfolio["trade_history"])
        
        # Calculate unrealized P&L
        unrealized_pnl = sum(
            (pos["quantity"] * pos.get("current_price", pos["avg_price"])) - (pos["quantity"] * pos["avg_price"])
            for pos in self.portfolio["positions"].values()
        )
        
        return {
            "initial_capital": initial_capital,
            "current_value": round(current_value, 2),
            "total_return": round(total_return, 2),
            "total_return_pct": round(total_return_pct, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "num_trades": num_trades,
            "num_positions": len(self.portfolio["positions"])
        }
    
    def _record_trade(self, symbol: str, action: str, quantity: int, price: float, timestamp: str = None) -> Dict[str, Any]:
        """Record a trade in portfolio."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        trade_value = quantity * price
        
        if action == "buy":
            if trade_value > self.portfolio["cash"]:
                return {"success": False, "error": "Insufficient cash"}
            
            self.portfolio["cash"] -= trade_value
            
            if symbol in self.portfolio["positions"]:
                # Update existing position
                pos = self.portfolio["positions"][symbol]
                total_cost = (pos["quantity"] * pos["avg_price"]) + trade_value
                total_quantity = pos["quantity"] + quantity
                pos["avg_price"] = total_cost / total_quantity
                pos["quantity"] = total_quantity
            else:
                # New position
                self.portfolio["positions"][symbol] = {
                    "quantity": quantity,
                    "avg_price": price,
                    "current_price": price
                }
        
        elif action == "sell":
            if symbol not in self.portfolio["positions"]:
                return {"success": False, "error": "No position to sell"}
            
            pos = self.portfolio["positions"][symbol]
            if quantity > pos["quantity"]:
                return {"success": False, "error": "Insufficient shares"}
            
            self.portfolio["cash"] += trade_value
            pos["quantity"] -= quantity
            
            if pos["quantity"] == 0:
                del self.portfolio["positions"][symbol]
        
        # Record in trade history
        trade_record = {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "value": trade_value,
            "timestamp": timestamp
        }
        self.portfolio["trade_history"].append(trade_record)
        
        return {"success": True, "trade": trade_record, "portfolio": self._get_portfolio_value()}
    
    def update_position_price(self, symbol: str, current_price: float):
        """Update current price for a position (called externally)."""
        if symbol in self.portfolio["positions"]:
            self.portfolio["positions"][symbol]["current_price"] = current_price
