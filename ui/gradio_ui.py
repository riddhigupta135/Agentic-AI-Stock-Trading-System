"""
Gradio Dashboard UI
Real-time monitoring dashboard for the Trading Floor.
"""
import gradio as gr
import asyncio
import json
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from tools.tool_registry import ToolRegistry
from core.agent_manager import AgentManager
from trading_floor.trading_floor import TradingFloor

# Import initialization
from main import initialize_system


class TradingUI:
    """Gradio UI wrapper for the trading system."""
    
    def __init__(self):
        self.trading_floor: TradingFloor = None
        self.tool_registry: ToolRegistry = None
        self.agent_manager: AgentManager = None
        self.is_initialized = False
        self.latest_results: List[Dict[str, Any]] = []
    
    def initialize(self):
        """Initialize the trading system."""
        if not self.is_initialized:
            self.trading_floor, self.tool_registry, self.agent_manager = initialize_system()
            self.is_initialized = True
            return "System initialized!"
        return "System already initialized"
    
    async def execute_round_async(self, symbols_str: str):
        """Execute a trading round asynchronously."""
        if not self.is_initialized:
            self.initialize()
        
        symbols = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]
        if not symbols:
            symbols = None
        
        result = await self.trading_floor.execute_round(symbols)
        self.latest_results.insert(0, result)  # Add to front
        if len(self.latest_results) > 50:  # Keep last 50
            self.latest_results = self.latest_results[:50]
        
        return self._format_round_result(result)
    
    def execute_round(self, symbols_str: str):
        """Execute a trading round (synchronous wrapper)."""
        return asyncio.run(self.execute_round_async(symbols_str))
    
    def _format_round_result(self, result: Dict[str, Any]) -> str:
        """Format round result for display."""
        output = []
        output.append(f"## Round {result['round']} - {result['symbol']}")
        output.append(f"**Timestamp:** {result['timestamp']}\n")
        
        decisions = result['decisions']
        
        # Market Analyst
        if decisions['analyst']:
            a = decisions['analyst']
            output.append(f"### Market Analyst")
            output.append(f"- **Decision:** {a.get('decision', 'N/A').upper()}")
            output.append(f"- **Confidence:** {a.get('confidence', 0):.2%}")
            output.append(f"- **Rationale:** {a.get('rationale', 'N/A')[:200]}...\n")
        
        # News Sentiment
        if decisions['sentiment']:
            s = decisions['sentiment']
            output.append(f"### News & Sentiment")
            output.append(f"- **Decision:** {s.get('decision', 'N/A').upper()}")
            output.append(f"- **Confidence:** {s.get('confidence', 0):.2%}")
            output.append(f"- **Rationale:** {s.get('rationale', 'N/A')[:200]}...\n")
        
        # Risk Management
        if decisions['risk']:
            r = decisions['risk']
            output.append(f"### Risk Management")
            output.append(f"- **Decision:** {r.get('decision', 'N/A').upper()}")
            output.append(f"- **Confidence:** {r.get('confidence', 0):.2%}")
            output.append(f"- **Rationale:** {r.get('rationale', 'N/A')[:200]}...\n")
        
        # Execution
        if decisions['execution']:
            e = decisions['execution']
            output.append(f"### Execution")
            output.append(f"- **Final Decision:** {e.get('decision', 'N/A').upper()}")
            output.append(f"- **Confidence:** {e.get('confidence', 0):.2%}")
            output.append(f"- **Rationale:** {e.get('rationale', 'N/A')}\n")
        
        return "\n".join(output)
    
    def get_portfolio_status(self):
        """Get current portfolio status."""
        if not self.is_initialized:
            return "System not initialized. Click 'Initialize System' first."
        
        portfolio_result = asyncio.run(
            self.tool_registry.call_tool("risk_portfolio.get_portfolio_value")
        )
        
        if portfolio_result.get("success"):
            portfolio_data = portfolio_result["result"]
            return f"""## Portfolio Status

**Cash:** ${portfolio_data.get('cash', 0):,.2f}
**Positions Value:** ${portfolio_data.get('positions_value', 0):,.2f}
**Total Value:** ${portfolio_data.get('total_value', 0):,.2f}

**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        else:
            return "Error retrieving portfolio status."
    
    def get_agent_statuses(self):
        """Get status of all agents."""
        if not self.is_initialized:
            return "System not initialized. Click 'Initialize System' first."
        
        statuses = self.agent_manager.get_agent_statuses()
        
        # Also get total decisions from all agents
        total_decisions = sum(status['decisions_made'] for status in statuses)
        
        output = ["## Agent Statuses\n"]
        output.append(f"**Total Decisions Across All Agents:** {total_decisions}\n")
        
        for status in statuses:
            output.append(f"### {status['name']} ({status['role']})")
            output.append(f"- **ID:** {status['agent_id']}")
            output.append(f"- **Decisions Made:** {status['decisions_made']}")
            output.append(f"- **Pending Messages:** {status['pending_messages']}")
            output.append(f"- **Tools Available:** {status['tools_count']}\n")
        
        return "\n".join(output)
    
    def get_system_info(self):
        """Get system information."""
        if not self.is_initialized:
            return "System not initialized."
        
        floor_status = self.trading_floor.get_status()
        
        info = f"""## System Information

### Trading Floor
- **Status:** {'Running' if floor_status['is_running'] else 'Stopped'}
- **Execution Rounds:** {floor_status['execution_rounds']}
- **Tools Count:** {floor_status['tools_count']}
- **Servers Count:** {floor_status['servers_count']}

### Configuration
- **Paper Trading:** {get_settings().paper_trading}
- **Initial Capital:** ${get_settings().initial_capital:,.2f}
- **Max Position Size:** {get_settings().max_position_size:.1%}
- **Risk Per Trade:** {get_settings().risk_per_trade:.1%}
"""
        return info


def create_ui():
    """Create and launch the Gradio UI."""
    ui = TradingUI()
    
    with gr.Blocks(title="Agentic AI Trading Floor") as demo:
        gr.Markdown("# Agentic AI Stock Trading System")
        gr.Markdown("### Trading Floor with 4 Agents, 6 MCP Servers, and 44 Tools")
        
        with gr.Tab("Control Panel"):
            with gr.Row():
                init_btn = gr.Button("Initialize System", variant="primary", size="lg")
                init_status = gr.Textbox(label="Initialization Status", interactive=False)
            
            init_btn.click(
                fn=ui.initialize,
                outputs=init_status
            )
            
            with gr.Row():
                symbols_input = gr.Textbox(
                    label="Symbols (comma-separated, e.g., AAPL,MSFT)",
                    value="AAPL",
                    placeholder="AAPL,MSFT,GOOGL"
                )
                execute_btn = gr.Button("Execute Trading Round", variant="primary")
            
            round_output = gr.Markdown(label="Round Results")
            
            execute_btn.click(
                fn=ui.execute_round,
                inputs=symbols_input,
                outputs=round_output
            )
        
        with gr.Tab("Portfolio"):
            portfolio_status = gr.Markdown()
            portfolio_btn = gr.Button("Refresh Portfolio Status")
            
            portfolio_btn.click(
                fn=ui.get_portfolio_status,
                outputs=portfolio_status
            )
        
        with gr.Tab("Agents"):
            agent_statuses = gr.Markdown()
            agent_btn = gr.Button("Refresh Agent Statuses")
            
            agent_btn.click(
                fn=ui.get_agent_statuses,
                outputs=agent_statuses
            )
        
        with gr.Tab("System Info"):
            system_info = gr.Markdown()
            info_btn = gr.Button("Refresh System Info")
            
            info_btn.click(
                fn=ui.get_system_info,
                outputs=system_info
            )
        
        gr.Markdown("---")
        gr.Markdown("""
        ### System Architecture
        - **4 Agents:** Market Analyst, News & Sentiment, Risk Management, Execution
        - **6 MCP Servers:** Market Data, News Search, Strategy Reasoning, Risk & Portfolio, Notification, Logging
        - **44 Tools:** Distributed across servers for data, analysis, and execution
        - **Paper Trading:** All trades are simulated
        """)
    
    return demo


def launch_ui():
    """Launch the Gradio UI."""
    import os
    demo = create_ui()
    # Check for environment variable, otherwise try 7860, fallback to 7861
    port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    
    # Try the requested port, fallback to next available
    for attempt_port in [port, 7861, 7862, 7863]:
        try:
            print(f"Attempting to launch on port {attempt_port}...")
            demo.launch(server_name="127.0.0.1", server_port=attempt_port, share=False, theme=gr.themes.Soft())
            break
        except OSError as e:
            if attempt_port == 7863:  # Last attempt
                raise e
            print(f"Port {attempt_port} in use, trying next port...")


if __name__ == "__main__":
    launch_ui()
