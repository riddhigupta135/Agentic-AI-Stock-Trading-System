"""
Logging & Metrics MCP Server
Provides structured logging and metrics tracking.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
from pathlib import Path
from mcp_servers.base_server import BaseMCPServer, ToolParameter, ToolParameterType
from config import get_settings


class LoggingServer(BaseMCPServer):
    """Logging & Metrics Server - Structured logging and metrics."""
    
    def __init__(self):
        super().__init__(
            server_name="logging_metrics",
            description="Provides structured logging and metrics tracking"
        )
        self.settings = get_settings()
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.metrics: Dict[str, List[Dict[str, Any]]] = {}
    
    def _register_tools(self):
        """Register logging and metrics tools."""
        
        # Tool 29: Log agent decision
        self.register_tool(
            name="log_agent_decision",
            description="Log an agent's decision with rationale",
            parameters=[
                ToolParameter("agent_id", ToolParameterType.STRING, "Agent identifier", True),
                ToolParameter("agent_role", ToolParameterType.STRING, "Agent role", True),
                ToolParameter("decision", ToolParameterType.STRING, "Decision made", True),
                ToolParameter("rationale", ToolParameterType.STRING, "Decision rationale", True),
                ToolParameter("confidence", ToolParameterType.FLOAT, "Confidence score (0-1)", False, 0.5),
                ToolParameter("data", ToolParameterType.OBJECT, "Additional data", False)
            ],
            handler=self._log_agent_decision
        )
        
        # Tool 30: Log trade execution
        self.register_tool(
            name="log_trade_execution",
            description="Log a trade execution",
            parameters=[
                ToolParameter("symbol", ToolParameterType.STRING, "Stock ticker symbol", True),
                ToolParameter("action", ToolParameterType.STRING, "buy, sell, or hold", True),
                ToolParameter("quantity", ToolParameterType.INTEGER, "Number of shares", False),
                ToolParameter("price", ToolParameterType.FLOAT, "Trade price", False),
                ToolParameter("agent_id", ToolParameterType.STRING, "Agent that made decision", False),
                ToolParameter("rationale", ToolParameterType.STRING, "Trade rationale", False)
            ],
            handler=self._log_trade_execution
        )
        
        # Tool 31: Log market event
        self.register_tool(
            name="log_market_event",
            description="Log a market event or data update",
            parameters=[
                ToolParameter("event_type", ToolParameterType.STRING, "Type of event", True),
                ToolParameter("symbol", ToolParameterType.STRING, "Stock symbol (optional)", False),
                ToolParameter("data", ToolParameterType.OBJECT, "Event data", True)
            ],
            handler=self._log_market_event
        )
        
        # Tool 32: Record metric
        self.register_tool(
            name="record_metric",
            description="Record a performance metric",
            parameters=[
                ToolParameter("metric_name", ToolParameterType.STRING, "Metric name", True),
                ToolParameter("value", ToolParameterType.FLOAT, "Metric value", True),
                ToolParameter("tags", ToolParameterType.OBJECT, "Metric tags", False),
                ToolParameter("timestamp", ToolParameterType.STRING, "Timestamp (ISO format)", False)
            ],
            handler=self._record_metric
        )
        
        # Tool 33: Get metrics summary
        self.register_tool(
            name="get_metrics_summary",
            description="Get summary of recorded metrics",
            parameters=[
                ToolParameter("metric_name", ToolParameterType.STRING, "Specific metric name (optional)", False),
                ToolParameter("time_window", ToolParameterType.INTEGER, "Time window in hours", False, 24)
            ],
            handler=self._get_metrics_summary
        )
        
        # Tool 34: Export logs
        self.register_tool(
            name="export_logs",
            description="Export logs to file",
            parameters=[
                ToolParameter("log_type", ToolParameterType.STRING, "Type: decisions, trades, events, all", False, "all"),
                ToolParameter("output_file", ToolParameterType.STRING, "Output file path", False)
            ],
            handler=self._export_logs
        )
        
        # Tool 35: Log system event
        self.register_tool(
            name="log_system_event",
            description="Log a system-level event",
            parameters=[
                ToolParameter("event", ToolParameterType.STRING, "Event description", True),
                ToolParameter("level", ToolParameterType.STRING, "Log level: DEBUG, INFO, WARNING, ERROR", False, "INFO"),
                ToolParameter("details", ToolParameterType.OBJECT, "Event details", False)
            ],
            handler=self._log_system_event
        )
    
    def _log_agent_decision(
        self,
        agent_id: str,
        agent_role: str,
        decision: str,
        rationale: str,
        confidence: float = 0.5,
        data: Dict = None
    ) -> Dict[str, Any]:
        """Log agent decision."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "agent_decision",
            "agent_id": agent_id,
            "agent_role": agent_role,
            "decision": decision,
            "rationale": rationale,
            "confidence": confidence,
            "data": data or {}
        }
        
        self._write_log_entry(log_entry)
        return {"success": True, "logged": True}
    
    def _log_trade_execution(
        self,
        symbol: str,
        action: str,
        quantity: int = None,
        price: float = None,
        agent_id: str = None,
        rationale: str = None
    ) -> Dict[str, Any]:
        """Log trade execution."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "trade_execution",
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "agent_id": agent_id,
            "rationale": rationale
        }
        
        self._write_log_entry(log_entry)
        return {"success": True, "logged": True}
    
    def _log_market_event(self, event_type: str, symbol: str = None, data: Dict = None) -> Dict[str, Any]:
        """Log market event."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "market_event",
            "event_type": event_type,
            "symbol": symbol,
            "data": data or {}
        }
        
        self._write_log_entry(log_entry)
        return {"success": True, "logged": True}
    
    def _record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Dict = None,
        timestamp: str = None
    ) -> Dict[str, Any]:
        """Record a metric."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        metric_entry = {
            "timestamp": timestamp,
            "metric_name": metric_name,
            "value": value,
            "tags": tags or {}
        }
        
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(metric_entry)
        
        return {"success": True, "metric_recorded": True}
    
    def _get_metrics_summary(self, metric_name: str = None, time_window: int = 24) -> Dict[str, Any]:
        """Get metrics summary."""
        cutoff_time = datetime.now().timestamp() - (time_window * 3600)
        
        if metric_name:
            if metric_name not in self.metrics:
                return {"metric_name": metric_name, "count": 0, "summary": {}}
            
            values = [
                m["value"] for m in self.metrics[metric_name]
                if datetime.fromisoformat(m["timestamp"]).timestamp() > cutoff_time
            ]
            
            if not values:
                return {"metric_name": metric_name, "count": 0, "summary": {}}
            
            return {
                "metric_name": metric_name,
                "count": len(values),
                "summary": {
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "latest": values[-1]
                }
            }
        else:
            # All metrics
            summary = {}
            for name, entries in self.metrics.items():
                values = [
                    m["value"] for m in entries
                    if datetime.fromisoformat(m["timestamp"]).timestamp() > cutoff_time
                ]
                if values:
                    summary[name] = {
                        "count": len(values),
                        "avg": sum(values) / len(values),
                        "latest": values[-1]
                    }
            return {"metrics": summary, "time_window_hours": time_window}
    
    def _export_logs(self, log_type: str = "all", output_file: str = None) -> Dict[str, Any]:
        """Export logs to file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.log_dir / f"export_{log_type}_{timestamp}.json"
        else:
            output_file = Path(output_file)
        
        # Read all log entries (in production, would read from log files)
        # For now, return success
        return {
            "success": True,
            "output_file": str(output_file),
            "note": "Log export feature - would read from log files in production"
        }
    
    def _log_system_event(self, event: str, level: str = "INFO", details: Dict = None) -> Dict[str, Any]:
        """Log system event."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "system_event",
            "level": level,
            "event": event,
            "details": details or {}
        }
        
        self._write_log_entry(log_entry)
        return {"success": True, "logged": True}
    
    def _write_log_entry(self, log_entry: Dict[str, Any]):
        """Write log entry to file."""
        log_file = self.log_dir / "trading_floor.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
