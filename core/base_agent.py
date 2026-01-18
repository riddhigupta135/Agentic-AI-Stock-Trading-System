"""
Base Agent Framework for Autonomous Trading Agents.
Implements agentic AI patterns with LLM-based reasoning.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid


class AgentRole(str, Enum):
    """Agent specialization roles."""
    MARKET_ANALYST = "market_analyst"
    NEWS_SENTIMENT = "news_sentiment"
    RISK_MANAGEMENT = "risk_management"
    EXECUTION = "execution"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipient: Optional[str] = None  # None means broadcast
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    message_type: str = "information"


@dataclass
class AgentDecision:
    """Structured decision output from an agent."""
    agent_id: str
    agent_role: str
    decision: str
    rationale: str  # Chain-of-thought reasoning summary (not raw CoT)
    confidence: float  # 0.0 to 1.0
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class BaseAgent(ABC):
    """
    Base class for all trading agents.
    Each agent has reasoning capabilities and tool access.
    """
    
    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        name: str,
        description: str,
        tools: List[Any] = None,
        shared_memory: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.role = role
        self.name = name
        self.description = description
        self.tools = tools or []
        self.shared_memory = shared_memory or {}
        self.message_queue: List[AgentMessage] = []
        self.decision_history: List[AgentDecision] = []
        
    def receive_message(self, message: AgentMessage):
        """Receive a message from another agent or system."""
        if message.recipient is None or message.recipient == self.agent_id:
            self.message_queue.append(message)
    
    def broadcast_message(self, content: Dict[str, Any], message_type: str = "information"):
        """Broadcast a message to all agents."""
        message = AgentMessage(
            sender=self.agent_id,
            recipient=None,
            content=content,
            message_type=message_type
        )
        return message
    
    def send_message(self, recipient_id: str, content: Dict[str, Any], message_type: str = "information"):
        """Send a targeted message to another agent."""
        message = AgentMessage(
            sender=self.agent_id,
            recipient=recipient_id,
            content=content,
            message_type=message_type
        )
        return message
    
    def record_decision(self, decision: str, rationale: str, confidence: float, data: Dict[str, Any] = None):
        """Record a decision with rationale."""
        agent_decision = AgentDecision(
            agent_id=self.agent_id,
            agent_role=self.role.value,
            decision=decision,
            rationale=rationale,
            confidence=confidence,
            data=data or {}
        )
        self.decision_history.append(agent_decision)
        return agent_decision
    
    @abstractmethod
    async def reason(self, context: Dict[str, Any]) -> AgentDecision:
        """
        Core reasoning method - each agent implements this.
        Should use LLM for reasoning and tools for data.
        Returns a structured decision with rationale.
        """
        pass
    
    @abstractmethod
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Return list of available tools for this agent."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agent."""
        # Get tools count from get_available_tools if available
        try:
            available_tools = self.get_available_tools()
            tools_count = len(available_tools) if available_tools else len(self.tools)
        except:
            tools_count = len(self.tools)
        
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "name": self.name,
            "pending_messages": len(self.message_queue),
            "decisions_made": len(self.decision_history),
            "tools_count": tools_count
        }
