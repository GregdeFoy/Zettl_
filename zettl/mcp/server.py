"""
Zettl MCP Server Implementation

Implements the Model Context Protocol for Zettl note management.
Provides read-only access to notes via standardized MCP tools.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

from .tools import ZettlMCPTools
from .auth import MCPAuthenticator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ZettlMCPServer:
    """MCP Server for Zettl notes"""

    def __init__(self, jwt_secret: str):
        """
        Initialize the MCP server

        Args:
            jwt_secret: JWT secret for authentication
        """
        self.authenticator = MCPAuthenticator(jwt_secret)
        self.server = Server("zettl")
        self.tools: Optional[ZettlMCPTools] = None
        self.current_token: Optional[str] = None

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register MCP protocol handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    inputSchema=tool_def["inputSchema"]
                )
                for tool_def in ZettlMCPTools.TOOL_DEFINITIONS
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute a tool with given arguments"""
            if not self.tools:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "Not authenticated. Please provide a JWT token."})
                )]

            try:
                # Route to appropriate tool method
                if name == "search_notes":
                    result = self.tools.search_notes(arguments.get("query", ""))
                elif name == "get_note":
                    result = self.tools.get_note(arguments.get("note_id"))
                elif name == "list_recent_notes":
                    result = self.tools.list_recent_notes(
                        limit=arguments.get("limit", 10)
                    )
                elif name == "get_notes_by_tag":
                    result = self.tools.get_notes_by_tag(arguments.get("tag"))
                elif name == "get_all_tags":
                    result = self.tools.get_all_tags()
                elif name == "get_related_notes":
                    result = self.tools.get_related_notes(arguments.get("note_id"))
                elif name == "search_notes_by_date":
                    result = self.tools.search_notes_by_date(arguments.get("date"))
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]

    def authenticate(self, jwt_token: str) -> bool:
        """
        Authenticate a user with a JWT token

        Args:
            jwt_token: JWT token to validate

        Returns:
            True if authentication successful
        """
        user_id = self.authenticator.get_user_id(jwt_token)
        if user_id:
            self.current_token = jwt_token
            self.tools = ZettlMCPTools(jwt_token)
            logger.info(f"Authenticated user {user_id}")
            return True
        return False

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main(jwt_secret: str):
    """
    Main entry point for the MCP server

    Args:
        jwt_secret: JWT secret for authentication
    """
    server = ZettlMCPServer(jwt_secret)
    await server.run()


if __name__ == "__main__":
    import os
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        raise ValueError("JWT_SECRET environment variable is required")
    asyncio.run(main(jwt_secret))
