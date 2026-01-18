"""
Main Entry Point for Agentic AI Stock Trading System
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from tools.tool_registry import ToolRegistry
from core.agent_manager import AgentManager
from trading_floor.trading_floor import TradingFloor

# Import MCP Servers
from mcp_servers.market_data_server import MarketDataServer
from mcp_servers.news_server import NewsServer
from mcp_servers.strategy_server import StrategyServer
from mcp_servers.risk_server import RiskServer
from mcp_servers.notification_server import NotificationServer
from mcp_servers.logging_server import LoggingServer

# Import Agents
from agents.market_analyst_agent import MarketAnalystAgent
from agents.news_sentiment_agent import NewsSentimentAgent
from agents.risk_management_agent import RiskManagementAgent
from agents.execution_agent import ExecutionAgent


def initialize_system():
    """Initialize the trading system: servers, tools, agents."""
    print("=" * 60)
    print("Initializing Agentic AI Stock Trading System")
    print("=" * 60)
    
    # Initialize tool registry
    tool_registry = ToolRegistry()
    
    # Initialize MCP Servers
    print("\nInitializing MCP Servers...")
    servers = [
        MarketDataServer(),
        NewsServer(),
        StrategyServer(),
        RiskServer(),
        NotificationServer(),
        LoggingServer()
    ]
    
    for server in servers:
        tool_registry.register_server(server)
    
    print(f"\nRegistered {tool_registry.get_server_count()} servers with {tool_registry.get_tool_count()} tools")
    
    # Initialize Agent Manager
    agent_manager = AgentManager()
    
    # Initialize Agents
    print("\nInitializing Agents...")
    agents = [
        MarketAnalystAgent(tool_registry, agent_manager.shared_memory),
        NewsSentimentAgent(tool_registry, agent_manager.shared_memory),
        RiskManagementAgent(tool_registry, agent_manager.shared_memory),
        ExecutionAgent(tool_registry, agent_manager.shared_memory)
    ]
    
    for agent in agents:
        agent_manager.register_agent(agent)
    
    print(f"Registered {len(agents)} agents")
    
    # Initialize Trading Floor
    trading_floor = TradingFloor(tool_registry, agent_manager)
    
    print("\n" + "=" * 60)
    print("System initialized successfully!")
    print("=" * 60)
    print(f"Agents: {len(agents)}")
    print(f"Tools: {tool_registry.get_tool_count()}")
    print(f"Servers: {tool_registry.get_server_count()}")
    print("=" * 60 + "\n")
    
    return trading_floor, tool_registry, agent_manager


async def run_single_round():
    """Run a single round of trading."""
    trading_floor, _, _ = initialize_system()
    
    print("Executing single trading round...\n")
    result = await trading_floor.execute_round()
    
    print("\n📋 Round Results:")
    print(f"  Symbol: {result['symbol']}")
    print(f"  Round: {result['round']}")
    
    if result['decisions']['execution']:
        exec_decision = result['decisions']['execution']
        print(f"  Final Decision: {exec_decision.get('decision', 'N/A').upper()}")
        print(f"  Confidence: {exec_decision.get('confidence', 0):.2%}")
        print(f"  Rationale: {exec_decision.get('rationale', 'N/A')[:100]}...")
    
    return result


async def run_continuous():
    """Run continuous trading rounds."""
    trading_floor, _, _ = initialize_system()
    
    settings = get_settings()
    interval = 300  # 5 minutes
    
    try:
        await trading_floor.run_continuous(interval_seconds=interval)
    except KeyboardInterrupt:
        print("\nStopping trading floor...")
        trading_floor.stop()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic AI Stock Trading System")
    parser.add_argument(
        "--mode",
        choices=["single", "continuous", "ui"],
        default="ui",
        help="Run mode: single round, continuous, or UI (default: ui)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "single":
        asyncio.run(run_single_round())
    elif args.mode == "continuous":
        asyncio.run(run_continuous())
    else:  # UI mode
        # Import and run UI
        from ui.gradio_ui import launch_ui
        print("Launching Gradio UI...")
        launch_ui()


if __name__ == "__main__":
    main()
