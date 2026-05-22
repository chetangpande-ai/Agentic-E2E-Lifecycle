"""
GitHub MCP server integration for committing code and creating PRs.
Uses langchain-mcp-adapters for the GitHub MCP server.
"""

import os
from typing import List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from config.settings import get_settings
from utils.logger import logger


class GitHubMCPClient:
    """Manages the GitHub MCP server connection for code commits and PRs."""

    def __init__(self):
        self.client = None
        self._tools = None
        self.settings = get_settings()

    async def initialize(self):
        """Initialize the GitHub MCP server connection."""
        logger.info("[bold green]Initializing GitHub MCP server...[/bold green]")

        # Set GitHub token for the MCP server
        env = os.environ.copy()
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = self.settings.github_personal_access_token

        try:
            self.client = MultiServerMCPClient(
                {
                    "github": {
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-github"],
                        "env": env,
                    }
                }
            )
            self._tools = await self.client.get_tools()
            logger.info(f"GitHub MCP initialized with {len(self._tools)} tools")
            return self._tools
        except Exception as e:
            logger.error(f"Failed to initialize GitHub MCP: {e}")
            raise

    async def get_tools(self):
        """Get the GitHub MCP tools for use in LangGraph agents."""
        if self._tools is None:
            await self.initialize()
        return self._tools

    async def close(self):
        """Close the MCP client connection."""
        if self.client:
            try:
                await self.client.close()
                logger.info("GitHub MCP connection closed")
            except Exception as e:
                logger.warning(f"Error closing GitHub MCP: {e}")


# Singleton instance
_github_mcp: Optional[GitHubMCPClient] = None


async def get_github_mcp() -> GitHubMCPClient:
    """Get or create the singleton GitHub MCP client."""
    global _github_mcp
    if _github_mcp is None:
        _github_mcp = GitHubMCPClient()
    return _github_mcp
