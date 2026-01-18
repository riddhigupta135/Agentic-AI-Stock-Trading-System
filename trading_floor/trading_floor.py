"""
Trading Floor Orchestrator
Coordinates the multi-agent trading system.
"""
from typing import Dict, Any, List
from datetime import datetime
import asyncio
from core.agent_manager import AgentManager
from core.base_agent import AgentDecision
from tools.tool_registry import ToolRegistry
from config import get_settings


class TradingFloor:
    """
    Trading Floor - Main orchestrator for the agentic trading system.
    Coordinates agent communication and execution cycles.
    """
    
    def __init__(self, tool_registry: ToolRegistry, agent_manager: AgentManager):
        self.tool_registry = tool_registry
        self.agent_manager = agent_manager
        self.settings = get_settings()
        self.is_running = False
        self.execution_rounds = 0
    
    async def execute_round(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Execute one round of agent reasoning and trading.
        Returns summary of decisions and actions.
        """
        if symbols is None:
            symbols = self.settings.default_tickers
        
        symbol = symbols[0]  # Focus on first symbol for this round
        
        # Prepare context
        context = {
            "symbols": symbols,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "round": self.execution_rounds
        }
        
        # Execute agent reasoning round
        # Agents are run in order: Market Analyst -> News Sentiment -> Risk Management -> Execution
        decisions = await self.agent_manager.orchestrate_round(context)
        
        # Extract decisions by agent role
        analyst_decision = next((d for d in decisions if d.agent_role == "market_analyst"), None)
        sentiment_decision = next((d for d in decisions if d.agent_role == "news_sentiment"), None)
        risk_decision = next((d for d in decisions if d.agent_role == "risk_management"), None)
        execution_decision = next((d for d in decisions if d.agent_role == "execution"), None)
        
        # Update context for execution agent (in a real system, this would be via messages)
        if execution_decision:
            # Re-run execution with context from other agents
            execution_context = {
                **context,
                "analyst_decision": analyst_decision.__dict__ if analyst_decision else {},
                "sentiment_decision": sentiment_decision.__dict__ if sentiment_decision else {},
                "risk_decision": risk_decision.__dict__ if risk_decision else {}
            }
            # Note: In a full implementation, execution agent would have access to these via messages
            # For simplicity, we pass via context
        
        # Update portfolio prices (for positions)
        portfolio = self.agent_manager.shared_memory.get("portfolio", {})
        if "positions" in portfolio:
            from mcp_servers.risk_server import RiskServer
            risk_server = next(
                (s for s in self.tool_registry.servers.values() if isinstance(s, RiskServer)),
                None
            )
            if risk_server:
                for symbol_pos in symbols:
                    price_result = await self.tool_registry.call_tool(
                        "market_data.get_latest_price",
                        symbol=symbol_pos
                    )
                    if price_result.get("success"):
                        price = price_result.get("result", {}).get("price")
                        if price:
                            risk_server.update_position_price(symbol_pos, price)
        
        self.execution_rounds += 1
        
        return {
            "round": self.execution_rounds,
            "timestamp": context["timestamp"],
            "symbol": symbol,
            "decisions": {
                "analyst": analyst_decision.__dict__ if analyst_decision else None,
                "sentiment": sentiment_decision.__dict__ if sentiment_decision else None,
                "risk": risk_decision.__dict__ if risk_decision else None,
                "execution": execution_decision.__dict__ if execution_decision else None
            },
            "portfolio": self.agent_manager.shared_memory.get("portfolio", {})
        }
    
    async def run_continuous(self, interval_seconds: int = 300, symbols: List[str] = None):
        """
        Run continuous trading rounds at specified interval.
        """
        self.is_running = True
        print(f"Trading Floor started - Executing rounds every {interval_seconds} seconds")
        
        while self.is_running:
            try:
                round_result = await self.execute_round(symbols)
                print(f"Round {round_result['round']} completed for {round_result['symbol']}")
                await asyncio.sleep(interval_seconds)
            except KeyboardInterrupt:
                print("\nTrading Floor stopped by user")
                self.is_running = False
                break
            except Exception as e:
                print(f"Error in trading round: {e}")
                await asyncio.sleep(interval_seconds)
    
    def stop(self):
        """Stop the trading floor."""
        self.is_running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current trading floor status."""
        portfolio = self.agent_manager.shared_memory.get("portfolio", {})
        
        return {
            "is_running": self.is_running,
            "execution_rounds": self.execution_rounds,
            "agents": self.agent_manager.get_agent_statuses(),
            "tools_count": self.tool_registry.get_tool_count(),
            "servers_count": self.tool_registry.get_server_count(),
            "portfolio_value": portfolio.get("total_value", 0) if isinstance(portfolio, dict) else 0
        }
