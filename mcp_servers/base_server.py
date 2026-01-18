"""
Base MCP Server Interface.
MCP (Model Context Protocol) servers provide tools to agents.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio


class ToolParameterType(str, Enum):
    """Tool parameter types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """Tool parameter definition."""
    name: str
    type: ToolParameterType
    description: str
    required: bool = True
    default: Any = None


@dataclass
class Tool:
    """Tool definition for MCP servers."""
    name: str
    description: str
    parameters: List[ToolParameter]
    handler: Callable
    server_name: str


class BaseMCPServer(ABC):
    """
    Base class for all MCP servers.
    Servers expose tools that agents can call.
    """
    
    def __init__(self, server_name: str, description: str):
        self.server_name = server_name
        self.description = description
        self.tools: Dict[str, Tool] = {}
        self._register_tools()
    
    @abstractmethod
    def _register_tools(self):
        """Register all tools provided by this server."""
        pass
    
    def register_tool(
        self,
        name: str,
        description: str,
        parameters: List[ToolParameter],
        handler: Callable
    ):
        """Register a tool with this server."""
        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            server_name=self.server_name
        )
        self.tools[name] = tool
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a tool by name with provided arguments.
        Returns a structured result.
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found in server '{self.server_name}'"
            }
        
        tool = self.tools[tool_name]
        
        try:
            # Validate parameters
            missing_params = [
                p.name for p in tool.parameters
                if p.required and p.name not in kwargs
            ]
            if missing_params:
                return {
                    "success": False,
                    "error": f"Missing required parameters: {missing_params}"
                }
            
            # Call handler
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**kwargs)
            else:
                result = tool.handler(**kwargs)
            
            return {
                "success": True,
                "tool": tool_name,
                "server": self.server_name,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "server": self.server_name
            }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of all tools with metadata."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type.value,
                        "description": p.description,
                        "required": p.required
                    }
                    for p in tool.parameters
                ],
                "server": self.server_name
            }
            for tool in self.tools.values()
        ]
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "server_name": self.server_name,
            "description": self.description,
            "tool_count": len(self.tools),
            "tools": [tool.name for tool in self.tools.values()]
        }


# Import asyncio for async checks
import asyncio
