"""
Playwright MCP server integration for web crawling.
Uses langchain-mcp-adapters to expose Playwright tools to LangGraph agents.
"""

import asyncio
from typing import List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from utils.logger import logger


class PlaywrightMCPClient:
    """Manages the Playwright MCP server connection for web crawling."""

    def __init__(self):
        self.client = None
        self._tools = None

    async def initialize(self):
        """Initialize the Playwright MCP server connection."""
        logger.info("[bold cyan]Initializing Playwright MCP server...[/bold cyan]")
        try:
            self.client = MultiServerMCPClient(
                {
                    "browser": {
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["-y", "@playwright/mcp@latest"],
                    }
                }
            )
            self._tools = await self.client.get_tools()
            logger.info(f"Playwright MCP initialized with {len(self._tools)} tools")
            return self._tools
        except Exception as e:
            logger.error(f"Failed to initialize Playwright MCP: {e}")
            raise

    async def get_tools(self):
        """Get the Playwright MCP tools for use in LangGraph agents."""
        if self._tools is None:
            await self.initialize()
        return self._tools

    async def close(self):
        """Close the MCP client connection."""
        if self.client:
            try:
                await self.client.close()
                logger.info("Playwright MCP connection closed")
            except Exception as e:
                logger.warning(f"Error closing Playwright MCP: {e}")


# Singleton instance
_playwright_mcp: Optional[PlaywrightMCPClient] = None


async def get_playwright_mcp() -> PlaywrightMCPClient:
    """Get or create the singleton Playwright MCP client."""
    global _playwright_mcp
    if _playwright_mcp is None:
        _playwright_mcp = PlaywrightMCPClient()
    return _playwright_mcp
