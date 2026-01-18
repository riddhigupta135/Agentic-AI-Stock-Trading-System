"""
Risk Management Agent
Enforces position sizing and risk limits.
"""
from typing import Dict, Any, List
from openai import OpenAI
from core.base_agent import BaseAgent, AgentRole, AgentDecision
from tools.tool_registry import ToolRegistry
from config import get_settings
import json


class RiskManagementAgent(BaseAgent):
    """
    Risk Management Agent - Enforces risk limits and position sizing.
    Validates trades against risk constraints before execution.
    """
    
    def __init__(self, tool_registry: ToolRegistry, shared_memory: Dict[str, Any] = None):
        super().__init__(
            agent_id="risk_management_001",
            role=AgentRole.RISK_MANAGEMENT,
            name="Risk Manager",
            description="Enforces position sizing, risk limits, and portfolio constraints",
            shared_memory=shared_memory
        )
        self.tool_registry = tool_registry
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.model = self.settings.openai_model
    
    async def reason(self, context: Dict[str, Any]) -> AgentDecision:
        """
        Assess risk for proposed trades.
        Checks against risk limits and portfolio constraints.
        """
        # Get proposed trade from context (from other agents)
        proposed_trade = context.get("proposed_trade", {})
        symbol = proposed_trade.get("symbol") or context.get("symbols", [self.settings.default_tickers[0]])[0]
        action = proposed_trade.get("action", "hold")
        quantity = proposed_trade.get("quantity")
        price = proposed_trade.get("price")
        
        # Get current portfolio state
        portfolio_result = await self.tool_registry.call_tool("risk_portfolio.get_portfolio_value")
        portfolio_data = portfolio_result.get("result", {}) if portfolio_result.get("success") else {}
        
        # Get position info if exists
        position_result = await self.tool_registry.call_tool("risk_portfolio.get_position_info", symbol=symbol)
        position_data = position_result.get("result", {}) if position_result.get("success") else {}
        
        # Assess trade risk
        if action in ["buy", "sell"] and price:
            risk_result = await self.tool_registry.call_tool(
                "risk_portfolio.assess_trade_risk",
                symbol=symbol,
                action=action,
                quantity=quantity,
                price=price
            )
            risk_data = risk_result.get("result", {}) if risk_result.get("success") else {}
            
            # Check risk limits
            trade_value = (quantity or 0) * price
            limits_result = await self.tool_registry.call_tool(
                "risk_portfolio.check_risk_limits",
                symbol=symbol,
                trade_value=trade_value
            )
            limits_data = limits_result.get("result", {}) if limits_result.get("success") else {}
        else:
            risk_data = {"risk_score": 0.0, "risk_level": "low", "risk_factors": []}
            limits_data = {"is_valid": True, "violations": []}
        
        # Get portfolio allocation
        allocation_result = await self.tool_registry.call_tool("risk_portfolio.get_portfolio_allocation")
        allocation_data = allocation_result.get("result", {}) if allocation_result.get("success") else {}
        
        # Use LLM to synthesize risk assessment
        risk_context = {
            "symbol": symbol,
            "action": action,
            "risk_score": risk_data.get("risk_score", 0),
            "risk_level": risk_data.get("risk_level", "low"),
            "risk_factors": risk_data.get("risk_factors", []),
            "limits_valid": limits_data.get("is_valid", True),
            "violations": limits_data.get("violations", []),
            "portfolio_value": portfolio_data.get("total_value", 0),
            "current_allocation": allocation_data
        }
        
        prompt = f"""
        You are a risk management analyst. Assess the risk for this trade:
        
        {json.dumps(risk_context, indent=2)}
        
        Provide:
        1. Risk assessment (approve/caution/reject)
        2. Key risk considerations (2-3 sentences)
        3. Recommended action (buy/sell/hold/modify)
        4. Confidence level (0-1)
        
        Format as JSON: {{"assessment": "...", "considerations": "...", "recommendation": "...", "confidence": 0.0-1.0}}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a risk management analyst. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=250
            )
            
            result_text = response.choices[0].message.content
            try:
                llm_result = json.loads(result_text)
            except:
                llm_result = {
                    "assessment": "approve" if risk_data.get("risk_level") == "low" else "caution",
                    "considerations": "Risk assessment based on portfolio constraints",
                    "recommendation": action,
                    "confidence": 0.7
                }
        except Exception as e:
            llm_result = {
                "assessment": "caution",
                "considerations": f"Error in risk analysis: {str(e)}",
                "recommendation": "hold",
                "confidence": 0.0
            }
        
        # Build rationale
        recommendation = llm_result.get("recommendation", action)
        rationale = f"""
        Risk Assessment for {symbol} ({action.upper()}):
        - Risk Level: {risk_data.get('risk_level', 'unknown').upper()}
        - Risk Score: {risk_data.get('risk_score', 0):.2f}/1.0
        - Risk Factors: {', '.join(risk_data.get('risk_factors', ['None']))}
        - Limits Valid: {limits_data.get('is_valid', True)}
        - Portfolio Value: ${portfolio_data.get('total_value', 0):,.2f}
        - Assessment: {llm_result.get('assessment', 'unknown').upper()}
        - Key Considerations: {llm_result.get('considerations', 'N/A')}
        - Recommendation: {recommendation.upper()}
        """.strip()
        
        # Send risk alert if high risk
        if risk_data.get("risk_level") == "high":
            await self.tool_registry.call_tool(
                "notification.send_risk_alert",
                message=f"High risk trade detected for {symbol}: {', '.join(risk_data.get('risk_factors', []))}",
                risk_level="high"
            )
        
        # Record decision
        agent_decision = self.record_decision(
            decision=recommendation,
            rationale=rationale,
            confidence=float(llm_result.get("confidence", 0.5)),
            data={
                "symbol": symbol,
                "risk_data": risk_data,
                "limits_data": limits_data,
                "portfolio_data": portfolio_data
            }
        )
        
        # Log decision
        await self.tool_registry.call_tool(
            "logging_metrics.log_agent_decision",
            agent_id=self.agent_id,
            agent_role=self.role.value,
            decision=recommendation,
            rationale=rationale,
            confidence=float(llm_result.get("confidence", 0.5))
        )
        
        return agent_decision
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get tools available to this agent."""
        return [
            tool for tool in self.tool_registry.get_tools()
            if tool["server"] in ["risk_portfolio", "notification", "logging_metrics"]
        ]
