"""
Agent Manager: Orchestrates multi-agent communication and coordination.
Implements message passing and shared memory patterns.
"""
from typing import Dict, List, Optional
from core.base_agent import BaseAgent, AgentMessage, AgentDecision
from datetime import datetime
import asyncio


class AgentManager:
    """
    Manages multiple agents, their communication, and shared state.
    Implements the Trading Floor orchestrator pattern.
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.shared_memory: Dict[str, any] = {
            "portfolio": {},
            "market_data": {},
            "news_sentiment": {},
            "active_trades": [],
            "trade_history": []
        }
        self.message_bus: List[AgentMessage] = []
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the manager."""
        agent.shared_memory = self.shared_memory
        self.agents[agent.agent_id] = agent
        print(f"Registered agent: {agent.name} ({agent.agent_id})")
    
    def broadcast_message(self, message: AgentMessage):
        """Broadcast message to all relevant agents."""
        self.message_bus.append(message)
        
        # Deliver to intended recipients
        for agent_id, agent in self.agents.items():
            if message.recipient is None:  # Broadcast
                agent.receive_message(message)
            elif message.recipient == agent_id:  # Direct message
                agent.receive_message(message)
    
    async def orchestrate_round(self, context: Dict[str, any]) -> List[AgentDecision]:
        """
        Orchestrate one round of agent reasoning.
        Agents reason in sequence and later agents can access earlier decisions.
        """
        decisions = []
        
        # Clear message bus for this round
        self.message_bus.clear()
        
        # Run each agent's reasoning in sequence
        # Later agents (especially Execution) need access to earlier decisions
        for agent_id, agent in self.agents.items():
            try:
                decision = await agent.reason(context)
                decisions.append(decision)
                
                # Update context with this agent's decision for subsequent agents
                # This allows Execution agent to see decisions from other agents
                if agent.role.value == "market_analyst":
                    context["analyst_decision"] = decision.__dict__ if hasattr(decision, '__dict__') else {}
                elif agent.role.value == "news_sentiment":
                    context["sentiment_decision"] = decision.__dict__ if hasattr(decision, '__dict__') else {}
                elif agent.role.value == "risk_management":
                    context["risk_decision"] = decision.__dict__ if hasattr(decision, '__dict__') else {}
                
                # Agent may have sent messages during reasoning
                # Process any messages it wants to broadcast
                
            except Exception as e:
                print(f"Error in agent {agent.name}: {e}")
                # Record error decision
                decision = agent.record_decision(
                    decision="ERROR",
                    rationale=f"Agent encountered an error: {str(e)}",
                    confidence=0.0,
                    data={"error": str(e)}
                )
                decisions.append(decision)
        
        return decisions
    
    def get_all_decisions(self) -> List[AgentDecision]:
        """Get all decisions from all agents."""
        all_decisions = []
        for agent in self.agents.values():
            all_decisions.extend(agent.decision_history)
        return sorted(all_decisions, key=lambda d: d.timestamp)
    
    def get_agent_statuses(self) -> List[Dict[str, any]]:
        """Get status of all agents."""
        return [agent.get_status() for agent in self.agents.values()]
    
    def update_shared_memory(self, key: str, value: any):
        """Update shared memory (e.g., portfolio state)."""
        self.shared_memory[key] = value
