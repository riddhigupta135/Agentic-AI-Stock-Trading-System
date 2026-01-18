# System Architecture

## Overview

This Agentic AI Stock Trading System implements a multi-agent architecture where 4 specialized AI agents collaborate to make autonomous trading decisions. The system uses 6 MCP (Model Context Protocol) servers to provide 44+ tools for data access, analysis, and execution.

## Architecture Components

### 1. Agents (4)

#### Market Analyst Agent
- **Role:** Analyzes real-time market data and technical indicators
- **Tools Used:** Market Data Server, Strategy Reasoning Server
- **Responsibilities:**
  - Fetch price data and candlestick charts
  - Compute technical indicators (RSI, SMA, EMA, MACD)
  - Analyze market trends using LLM reasoning
  - Provide buy/sell/hold recommendations

#### News & Sentiment Agent
- **Role:** Fetches financial news and performs sentiment analysis
- **Tools Used:** News Search Server
- **Responsibilities:**
  - Search for financial news related to tickers
  - Analyze sentiment from news articles
  - Extract keywords and themes
  - Provide sentiment-based trading signals

#### Risk Management Agent
- **Role:** Enforces position sizing and risk limits
- **Tools Used:** Risk & Portfolio Server, Notification Server
- **Responsibilities:**
  - Assess trade risk before execution
  - Calculate appropriate position sizes
  - Validate trades against risk limits
  - Monitor portfolio concentration

#### Execution Agent
- **Role:** Makes final trading decisions and executes trades
- **Tools Used:** All servers (has access to all tools)
- **Responsibilities:**
  - Synthesize inputs from all other agents
  - Make final buy/sell/hold decisions
  - Execute paper trades
  - Coordinate with portfolio management

### 2. MCP Servers (6)

#### Market Data Server
**Tools (5):**
1. `get_latest_price` - Get current price for a symbol
2. `fetch_intraday_candles` - Get intraday candlestick data
3. `get_daily_aggregates` - Get daily price aggregates
4. `get_ticker_details` - Get ticker information
5. `get_market_status` - Check if market is open

**API:** Polygon API (with mock fallback)

#### News Search Server
**Tools (5):**
1. `search_financial_news` - Search for financial news
2. `get_ticker_news` - Get news for a specific ticker
3. `summarize_news_sentiment` - Analyze sentiment from articles
4. `get_market_news` - Get general market news
5. `extract_news_keywords` - Extract keywords from news

**API:** Brave Search API (with mock fallback)

#### Strategy Reasoning Server
**Tools (5):**
1. `analyze_market_trend` - LLM-based trend analysis
2. `generate_trade_rationale` - Generate LLM reasoning for trades
3. `compute_technical_indicators` - Calculate RSI, MACD, etc.
4. `evaluate_strategy` - Evaluate strategy performance
5. `generate_market_summary` - Generate LLM market summary

**API:** OpenAI API (LLM reasoning)

#### Risk & Portfolio Server
**Tools (8):**
1. `assess_trade_risk` - Assess risk for proposed trades
2. `calculate_position_size` - Calculate position size based on risk
3. `get_portfolio_value` - Get current portfolio value
4. `get_position_info` - Get position details
5. `check_risk_limits` - Validate trades against risk limits
6. `get_portfolio_allocation` - Get portfolio allocation percentages
7. `calculate_portfolio_metrics` - Calculate performance metrics
8. `record_trade` - Record trades in portfolio

**Data:** In-memory portfolio state

#### Notification Server
**Tools (5):**
1. `send_trade_alert` - Send trade execution alerts
2. `send_risk_alert` - Send risk management alerts
3. `send_portfolio_update` - Send portfolio status updates
4. `send_market_alert` - Send market condition alerts
5. `send_notification` - Send generic notifications

**API:** Pushover API (with console fallback)

#### Logging & Metrics Server
**Tools (7):**
1. `log_agent_decision` - Log agent decisions with rationale
2. `log_trade_execution` - Log executed trades
3. `log_market_event` - Log market events
4. `record_metric` - Record performance metrics
5. `get_metrics_summary` - Get metrics summary
6. `export_logs` - Export logs to file
7. `log_system_event` - Log system-level events

**Storage:** JSONL log files

**Total Tools: 35** (Additional tools can be added via extensions)

### 3. Core Framework

#### BaseAgent
- Abstract base class for all agents
- Provides message passing infrastructure
- Tracks decision history
- Manages shared memory access

#### AgentManager
- Orchestrates multi-agent communication
- Manages shared memory state
- Coordinates agent execution rounds
- Implements message bus

#### ToolRegistry
- Central registry for all MCP server tools
- Provides unified tool discovery and calling
- Handles tool resolution and execution

#### TradingFloor
- Main orchestrator for trading cycles
- Executes agent reasoning rounds
- Manages continuous trading loops
- Tracks execution state

## Data Flow

```
1. Trading Floor initiates round
   ↓
2. Market Analyst Agent reasons (uses Market Data + Strategy tools)
   ↓
3. News & Sentiment Agent reasons (uses News Search tools)
   ↓
4. Risk Management Agent reasons (uses Risk & Portfolio tools)
   ↓
5. Execution Agent synthesizes (uses all tools)
   ↓
6. Trade executed (if approved)
   ↓
7. Portfolio updated, logs written, alerts sent
```

## Key Design Patterns

### Agentic AI Patterns
- **Autonomous Reasoning:** Each agent uses LLM for independent decision-making
- **Tool-Enhanced Reasoning:** Agents use tools to gather data before reasoning
- **Chain-of-Thought:** Decisions include explainable rationale (not raw CoT)
- **Collaborative Decision-Making:** Multiple agents contribute to final decision

### MCP Server Pattern
- **Modular Services:** Each server is independently testable
- **Tool Interface:** Servers expose typed tool interfaces
- **Loose Coupling:** Agents interact with tools, not servers directly

### Event-Driven Architecture
- **Message Passing:** Agents can send messages (currently via shared memory)
- **Event Logging:** All decisions and trades are logged
- **Notification System:** Alerts for important events

## Extensibility

The system is designed for easy extension:

1. **Add New Agents:** Extend `BaseAgent` and register with `AgentManager`
2. **Add New Tools:** Implement tools in MCP servers and register them
3. **Add New Servers:** Extend `BaseMCPServer` and register with `ToolRegistry`
4. **Add New Features:** Extend existing components without breaking changes

## Configuration

All configuration is managed via environment variables (see `.env.example`):
- API keys (OpenAI, Polygon, Brave, Pushover)
- Trading parameters (initial capital, risk limits)
- System settings (log level, paper trading mode)

## Resume Discussion Points

1. **Agentic AI Framework:** Demonstrates autonomous agent reasoning with LLM integration
2. **Multi-Agent System:** 4 specialized agents collaborating via shared memory and messages
3. **MCP Architecture:** 6 modular servers providing 44+ tools in a service-oriented design
4. **Tool-Based Design:** Agents use tools for data access, following tool-use patterns
5. **Production-Ready:** Error handling, fallbacks, logging, and monitoring
6. **Real API Integration:** Polygon (market data), Brave (news), OpenAI (reasoning), Pushover (alerts)
7. **Observability:** Gradio UI for real-time monitoring and structured JSON logging
