# Agentic AI Stock Trading System

A production-grade autonomous trading floor with 4 specialized AI agents, 6 MCP servers, and 40+ tools.

## Architecture Overview

### Agents (4)
- **Market Analyst Agent**: Analyzes real-time market data and technical indicators
- **News & Sentiment Agent**: Fetches financial news and sentiment analysis
- **Risk Management Agent**: Enforces position sizing and risk limits
- **Execution Agent**: Makes buy/sell/hold decisions and simulates execution

### MCP Servers (6)
- **Market Data Server**: Polygon API integration for price data and candles
- **News Search Server**: Brave API integration for financial news
- **Strategy Reasoning Server**: LLM orchestration for trade reasoning
- **Risk & Portfolio Server**: Position management and risk calculations
- **Notification Server**: Pushover integration for alerts
- **Logging & Metrics Server**: Structured logging and metrics tracking

### Features
- Agentic AI framework with LLM-based reasoning
- Real-time market data integration
- Sentiment analysis from news
- Risk management with position sizing
- Paper trading simulation
- Gradio dashboard for real-time monitoring
- 40+ reusable tools
- Structured JSON logging

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (see `.env.example`):
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Run the system:
```bash
python main.py
```

## Project Structure

```
.
    agents/              # 4 specialized agents
    mcp_servers/         # 6 MCP-style servers
    tools/               # 40+ reusable tools
    core/                # Core framework (Agent base, AgentManager)
    trading_floor/       # Trading floor orchestrator
    ui/                  # Gradio dashboard
    config/              # Configuration files
    logs/                # Log files
    data/                # Portfolio data and trade history
    main.py             # Entry point
```

## Resume Points

- Built a Trading Floor with 4 Agents making autonomous trades
- Powered by 6 MCP servers and 44 tools
- Agentic AI Framework, LLM Models, MCP Servers, Python, Gradio
- Integrated Brave API, Polygon API, Pushover, OpenAI SDK
