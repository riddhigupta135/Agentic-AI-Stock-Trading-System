"""
Execution Agent
Makes final buy/sell/hold decisions and simulates trade execution.
"""
from typing import Dict, Any, List
from openai import OpenAI
from core.base_agent import BaseAgent, AgentRole, AgentDecision
from tools.tool_registry import ToolRegistry
from config import get_settings
from datetime import datetime
import json


class ExecutionAgent(BaseAgent):
    """
    Execution Agent - Makes final trading decisions and executes trades.
    Synthesizes inputs from other agents and executes paper trades.
    """
    
    def __init__(self, tool_registry: ToolRegistry, shared_memory: Dict[str, Any] = None):
        super().__init__(
            agent_id="execution_001",
            role=AgentRole.EXECUTION,
            name="Execution Agent",
            description="Makes final trading decisions and executes trades based on agent inputs",
            shared_memory=shared_memory
        )
        self.tool_registry = tool_registry
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.model = self.settings.openai_model
    
    async def reason(self, context: Dict[str, Any]) -> AgentDecision:
        """
        Synthesize decisions from other agents and execute trades.
        This is the final decision-making agent that coordinates execution.
        """
        symbols = context.get("symbols", self.settings.default_tickers)
        symbol = symbols[0] if symbols else self.settings.default_tickers[0]
        
        # Get latest price
        price_result = await self.tool_registry.call_tool("market_data.get_latest_price", symbol=symbol)
        price_data = price_result.get("result", {}) if price_result.get("success") else {}
        current_price = price_data.get("price", 0)
        
        # Gather decisions from shared memory (set by other agents in previous round)
        # In practice, this would come from agent messages
        analyst_decision = context.get("analyst_decision", {})
        sentiment_decision = context.get("sentiment_decision", {})
        risk_decision = context.get("risk_decision", {})
        
        # Get market sentiment from shared memory
        news_sentiment = self.shared_memory.get("news_sentiment", {}).get(symbol, {})
        
        # Get portfolio state
        portfolio_result = await self.tool_registry.call_tool("risk_portfolio.get_portfolio_value")
        portfolio_data = portfolio_result.get("result", {}) if portfolio_result.get("success") else {}
        
        # Calculate position size if buying
        position_size_result = await self.tool_registry.call_tool(
            "risk_portfolio.calculate_position_size",
            symbol=symbol,
            entry_price=current_price,
            stop_loss=current_price * 0.95  # 5% stop loss
        )
        position_size_data = position_size_result.get("result", {}) if position_size_result.get("success") else {}
        recommended_quantity = position_size_data.get("recommended_quantity", 0)
        
        # Synthesize decision using LLM
        synthesis_context = {
            "symbol": symbol,
            "current_price": current_price,
            "analyst_recommendation": analyst_decision.get("decision", "hold"),
            "analyst_confidence": analyst_decision.get("confidence", 0.5),
            "sentiment_recommendation": sentiment_decision.get("decision", "hold"),
            "sentiment_confidence": sentiment_decision.get("confidence", 0.5),
            "risk_recommendation": risk_decision.get("decision", "hold"),
            "risk_confidence": risk_decision.get("confidence", 0.5),
            "news_sentiment": news_sentiment.get("sentiment", "neutral"),
            "recommended_quantity": recommended_quantity,
            "portfolio_value": portfolio_data.get("total_value", 0),
            "paper_trading": self.settings.paper_trading
        }
        
        # Extract decision values
        analyst_decision_val = analyst_decision.get('decision', 'hold').lower()
        analyst_conf = analyst_decision.get('confidence', 0.5)
        sentiment_decision_val = sentiment_decision.get('decision', 'hold').lower()
        sentiment_conf = sentiment_decision.get('confidence', 0.5)
        risk_decision_val = risk_decision.get('decision', 'hold').lower()
        risk_conf = risk_decision.get('confidence', 0.5)
        
        # Risk Manager's recommendation is often "hold" but check if it's actually rejecting
        risk_rejects = risk_decision_val == "reject" or risk_decision.get("data", {}).get("risk_data", {}).get("risk_level") == "high"
        
        prompt = f"""
        You are an active trading execution agent. Make decisive trading decisions based on market signals.
        
        Agent Inputs:
        - Market Analyst: {analyst_decision_val.upper()} (confidence: {analyst_conf:.2f}) - PRIMARY SIGNAL
        - News Sentiment: {sentiment_decision_val.upper()} (confidence: {sentiment_conf:.2f}) - SECONDARY (often neutral)
        - Risk Manager: {risk_decision_val.upper()} (confidence: {risk_conf:.2f}) - VALIDATION ONLY
        - Current Price: ${current_price:.2f}
        - Recommended Quantity: {recommended_quantity} shares
        - Portfolio Value: ${portfolio_data.get('total_value', 0):,.2f}
        
        DECISION RULES (Market Analyst is PRIMARY - trust it when confident):
        1. If Market Analyst = BUY with confidence >=0.65 AND Risk does NOT reject → BUY with quantity >=10
        2. If Market Analyst = SELL with confidence >=0.65 AND you have position → SELL with quantity >0
        3. If Market Analyst = BUY with confidence >=0.55 AND sentiment is not negative AND Risk does NOT reject → BUY with quantity >=5
        4. If Market Analyst = SELL with confidence >=0.55 AND you have position → SELL with quantity >0
        5. Only HOLD if Market Analyst confidence <0.55 OR Risk explicitly rejects OR signals strongly conflict
        
        IMPORTANT: 
        - Market Analyst is the PRIMARY signal source - trust it when confidence >0.55
        - News/Sentiment being "hold" is OK - it just means neutral, not negative
        - Risk Manager saying "hold" usually means "no objection" (not reject)
        - BE DECISIVE: If Market Analyst is confident (>0.6), make the trade even if others are neutral
        
        Quantity Rules:
        - BUY: Use {recommended_quantity} as base, minimum 5 shares, maximum 100 shares or {recommended_quantity}
        - SELL: If you have position, sell {recommended_quantity} or all if closing position
        
        Provide:
        1. Final decision: "buy", "sell", or "hold" (prefer buy/sell when analyst is confident)
        2. Quantity: positive integer if buy/sell (minimum 5 for buy), 0 if hold
        3. Rationale: brief explanation (2 sentences)
        4. Confidence: 0.0-1.0
        
        Format as JSON: {{"decision": "buy/sell/hold", "quantity": 0, "rationale": "...", "confidence": 0.0-1.0}}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an active trading execution agent. The Market Analyst is your PRIMARY signal source - trust its BUY/SELL recommendations when confidence >0.55. News and Risk being 'hold' usually means neutral/approved, not negative. Make decisive trades when Market Analyst is confident. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,  # Increased to allow more decisive action
                max_tokens=350
            )
            
            result_text = response.choices[0].message.content
            try:
                llm_result = json.loads(result_text)
            except:
                llm_result = {
                    "decision": "hold",
                    "quantity": 0,
                    "rationale": "Insufficient consensus from agents",
                    "confidence": 0.3
                }
        except Exception as e:
            llm_result = {
                "decision": "hold",
                "quantity": 0,
                "rationale": f"Error in decision synthesis: {str(e)}",
                "confidence": 0.0
            }
        
        final_decision = llm_result.get("decision", "hold").lower()
        quantity = int(llm_result.get("quantity", 0))
        
        # Execute trade if not hold and risk approved
        if final_decision in ["buy", "sell"] and quantity > 0 and risk_decision.get("decision") != "reject":
            # Record trade in portfolio
            trade_result = await self.tool_registry.call_tool(
                "risk_portfolio.record_trade",
                symbol=symbol,
                action=final_decision,
                quantity=quantity,
                price=current_price,
                timestamp=datetime.now().isoformat()
            )
            
            # Log trade execution
            await self.tool_registry.call_tool(
                "logging_metrics.log_trade_execution",
                symbol=symbol,
                action=final_decision,
                quantity=quantity,
                price=current_price,
                agent_id=self.agent_id,
                rationale=llm_result.get("rationale", "")
            )
            
            # Send trade alert
            await self.tool_registry.call_tool(
                "notification.send_trade_alert",
                message=f"Executed {final_decision.upper()} {quantity} shares of {symbol} at ${current_price:.2f}",
                title="Trade Executed"
            )
        else:
            trade_result = {"message": "No trade executed"}
        
        # Build rationale
        rationale = f"""
        Execution Decision for {symbol}:
        - Final Decision: {final_decision.upper()}
        - Quantity: {quantity} shares
        - Price: ${current_price:.2f}
        - Synthesis Rationale: {llm_result.get('rationale', 'N/A')}
        - Market Analyst: {analyst_decision.get('decision', 'N/A')} (conf: {analyst_decision.get('confidence', 0):.2f})
        - News Sentiment: {sentiment_decision.get('decision', 'N/A')} (conf: {sentiment_decision.get('confidence', 0):.2f})
        - Risk Manager: {risk_decision.get('decision', 'N/A')} (conf: {risk_decision.get('confidence', 0):.2f})
        """.strip()
        
        # Record decision
        agent_decision = self.record_decision(
            decision=final_decision,
            rationale=rationale,
            confidence=float(llm_result.get("confidence", 0.5)),
            data={
                "symbol": symbol,
                "quantity": quantity,
                "price": current_price,
                "trade_result": trade_result,
                "synthesis_context": synthesis_context
            }
        )
        
        # Log decision
        await self.tool_registry.call_tool(
            "logging_metrics.log_agent_decision",
            agent_id=self.agent_id,
            agent_role=self.role.value,
            decision=final_decision,
            rationale=rationale,
            confidence=float(llm_result.get("confidence", 0.5))
        )
        
        return agent_decision
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get tools available to this agent."""
        return self.tool_registry.get_tools()  # Execution agent has access to all tools
