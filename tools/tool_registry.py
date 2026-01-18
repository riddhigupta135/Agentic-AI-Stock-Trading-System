"""
Tool Registry: Central registry for all tools from MCP servers.
Provides unified tool access interface for agents.
"""
from typing import Dict, Any, List, Optional
from mcp_servers.base_server import BaseMCPServer
import asyncio


class ToolRegistry:
    """
    Central registry that aggregates tools from all MCP servers.
    Agents use this to discover and call tools.
    """
    
    def __init__(self):
        self.servers: Dict[str, BaseMCPServer] = {}
        self.all_tools: Dict[str, Dict[str, Any]] = {}
    
    def register_server(self, server: BaseMCPServer):
        """Register an MCP server and its tools."""
        self.servers[server.server_name] = server
        tools = server.get_tools()
        
        for tool in tools:
            tool_key = f"{server.server_name}.{tool['name']}"
            self.all_tools[tool_key] = {
                **tool,
                "server_instance": server,
                "full_name": tool_key
            }
        
        print(f"Registered server '{server.server_name}' with {len(tools)} tools")
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a tool by its full name (server.tool_name) or short name.
        Returns structured result.
        """
        # Try full name first
        if tool_name in self.all_tools:
            tool_info = self.all_tools[tool_name]
            server = tool_info["server_instance"]
            actual_tool_name = tool_info["name"]
            return await server.call_tool(actual_tool_name, **kwargs)
        
        # Try short name (search across servers)
        for full_name, tool_info in self.all_tools.items():
            if tool_info["name"] == tool_name:
                server = tool_info["server_instance"]
                return await server.call_tool(tool_name, **kwargs)
        
        return {
            "success": False,
            "error": f"Tool '{tool_name}' not found"
        }
    
    def get_tools(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tools, optionally filtered by server."""
        if server_name:
            return [
                tool for tool in self.all_tools.values()
                if tool["server"] == server_name
            ]
        return list(self.all_tools.values())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool."""
        return self.all_tools.get(tool_name)
    
    def get_tool_count(self) -> int:
        """Get total number of registered tools."""
        return len(self.all_tools)
    
    def get_server_count(self) -> int:
        """Get number of registered servers."""
        return len(self.servers)
