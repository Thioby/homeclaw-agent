"""Context7 tools for fetching library documentation.

This module provides tools to query Context7's documentation database,
which provides up-to-date, version-specific documentation and code examples
for programming libraries.

Uses the public MCP endpoint at https://mcp.context7.com/mcp (no API key required).
Optional API key can be provided for higher rate limits.

Usage:
    # First resolve library name to ID
    result = await context7_resolve.execute(
        query="How to use React hooks",
        library_name="react"
    )
    # Returns library IDs like "/facebook/react"

    # Then query documentation
    result = await context7_docs.execute(
        library_id="/facebook/react",
        query="useEffect cleanup function"
    )
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult

_LOGGER = logging.getLogger(__name__)

# API Configuration for Context7 MCP endpoint
API_CONFIG = {
    "BASE_URL": "https://mcp.context7.com",
    "ENDPOINT": "/mcp",
    "DEFAULT_TIMEOUT": 30,  # seconds
}


def _parse_mcp_response(response_text: str) -> Optional[str]:
    """Parse MCP response - handles both direct JSON and SSE formats.

    Context7 returns direct JSON, while some MCP endpoints return SSE.
    This function handles both formats.

    Args:
        response_text: Raw response text (either JSON or SSE format)

    Returns:
        Extracted content text, or None if not found
    """
    # First, try to parse as direct JSON (Context7's format)
    try:
        data = json.loads(response_text)
        result = data.get("result", {})
        content = result.get("content", [])

        if content and len(content) > 0:
            return content[0].get("text", "")
    except json.JSONDecodeError:
        pass  # Not direct JSON, try SSE format

    # Fallback: try SSE format (data: {...})
    lines = response_text.split("\n")

    for line in lines:
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])  # Skip "data: " prefix

                # Extract content from MCP response
                result = data.get("result", {})
                content = result.get("content", [])

                if content and len(content) > 0:
                    # Return first content item's text
                    return content[0].get("text", "")
            except json.JSONDecodeError as e:
                _LOGGER.debug(f"Failed to parse SSE line: {e}")
                continue

    return None


async def _call_mcp_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    api_key: Optional[str] = None,
    timeout: int = API_CONFIG["DEFAULT_TIMEOUT"],
) -> ToolResult:
    """Call a tool on the Context7 MCP endpoint.

    Args:
        tool_name: Name of the MCP tool to call
        arguments: Arguments to pass to the tool
        api_key: Optional API key for higher rate limits
        timeout: Request timeout in seconds

    Returns:
        ToolResult with the response
    """
    # Build MCP JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
    }

    # Add API key if provided
    if api_key:
        headers["CONTEXT7_API_KEY"] = api_key

    url = f"{API_CONFIG['BASE_URL']}{API_CONFIG['ENDPOINT']}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=request,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return ToolResult(
                        output="",
                        success=False,
                        error=f"Context7 error ({response.status}): {error_text}",
                        title=f"Context7: {tool_name}",
                    )

                response_text = await response.text()

                # Parse MCP response (handles both JSON and SSE formats)
                content = _parse_mcp_response(response_text)

                if content:
                    return ToolResult(
                        output=content,
                        success=True,
                        title=f"Context7: {tool_name}",
                        metadata={"tool": tool_name, "arguments": arguments},
                    )

                return ToolResult(
                    output="No results found.",
                    success=False,
                    error="Empty response from Context7",
                    title=f"Context7: {tool_name}",
                )

    except asyncio.TimeoutError:
        return ToolResult(
            output="",
            success=False,
            error=f"Request timed out after {timeout} seconds",
            title=f"Context7: {tool_name}",
        )
    except aiohttp.ClientError as e:
        return ToolResult(
            output="",
            success=False,
            error=f"Request failed: {str(e)}",
            title=f"Context7: {tool_name}",
        )
    except Exception as e:
        _LOGGER.exception(f"Unexpected error calling Context7: {e}")
        return ToolResult(
            output="",
            success=False,
            error=f"Unexpected error: {str(e)}",
            title=f"Context7: {tool_name}",
        )


@ToolRegistry.register
class Context7ResolveTool(Tool):
    """Tool for resolving library names to Context7-compatible IDs.

    This tool searches Context7's library database and returns matching
    libraries with their IDs, descriptions, and metadata.

    Must be called before Context7DocsTool to get the correct library ID.
    """

    id = "context7_resolve"
    description = (
        "Resolve a library/package name to a Context7-compatible library ID. "
        "Use this FIRST before querying documentation. Returns matching libraries "
        "with IDs like '/facebook/react', '/vercel/next.js'."
    )
    category = ToolCategory.WEB

    parameters = [
        ToolParameter(
            name="library_name",
            type="string",
            description="Library name to search for (e.g., 'react', 'nextjs', 'express')",
            required=True,
        ),
        ToolParameter(
            name="query",
            type="string",
            description="Your question or task (used to rank results by relevance)",
            required=True,
        ),
    ]

    async def execute(
        self,
        library_name: str,
        query: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Resolve a library name to Context7-compatible ID.

        Args:
            library_name: Library name to search for
            query: User's question (for relevance ranking)

        Returns:
            ToolResult with matching libraries and their IDs
        """
        # Get optional API key from config
        api_key = self.config.get("context7_api_key") if self.config else None

        result = await _call_mcp_tool(
            tool_name="resolve-library-id",
            arguments={
                "libraryName": library_name,
                "query": query,
            },
            api_key=api_key,
        )

        # Update title with library name
        if result.success:
            result.title = f"Context7 resolve: {library_name}"

        return result

    def get_system_prompt(self) -> str:
        """Generate the system prompt for this tool."""
        return (
            "- context7_resolve(library_name, query): Find Context7 library ID for a package. "
            "MUST call this first before context7_docs. Returns IDs like '/facebook/react'."
        )


@ToolRegistry.register
class Context7DocsTool(Tool):
    """Tool for querying library documentation from Context7.

    Returns up-to-date, version-specific documentation and code examples
    for programming libraries. Use the library ID from context7_resolve.
    """

    id = "context7_docs"
    description = (
        "Get documentation and code examples for a library from Context7. "
        "Requires a Context7-compatible library ID (from context7_resolve). "
        "Returns relevant docs and code snippets for your query."
    )
    category = ToolCategory.WEB

    parameters = [
        ToolParameter(
            name="library_id",
            type="string",
            description="Context7-compatible library ID (e.g., '/facebook/react', '/vercel/next.js')",
            required=True,
        ),
        ToolParameter(
            name="query",
            type="string",
            description="What you want to know about the library",
            required=True,
        ),
        ToolParameter(
            name="topic",
            type="string",
            description="Optional topic to focus on (e.g., 'hooks', 'routing', 'authentication')",
            required=False,
            default=None,
        ),
    ]

    async def execute(
        self,
        library_id: str,
        query: str,
        topic: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Query documentation for a library.

        Args:
            library_id: Context7-compatible library ID
            query: What to search for in the documentation
            topic: Optional topic to focus on

        Returns:
            ToolResult with documentation and code examples
        """
        # Validate library_id format
        if not library_id.startswith("/"):
            return ToolResult(
                output="",
                success=False,
                error=f"Invalid library ID format: '{library_id}'. Must start with '/' (e.g., '/facebook/react')",
                title="Context7 docs error",
            )

        # Get optional API key from config
        api_key = self.config.get("context7_api_key") if self.config else None

        # Build arguments
        arguments: Dict[str, Any] = {
            "libraryId": library_id,
            "query": query,
        }

        if topic:
            arguments["topic"] = topic

        result = await _call_mcp_tool(
            tool_name="query-docs",
            arguments=arguments,
            api_key=api_key,
        )

        # Update title
        if result.success:
            result.title = f"Context7 docs: {library_id}"

        return result

    def get_system_prompt(self) -> str:
        """Generate the system prompt for this tool."""
        return (
            "- context7_docs(library_id, query, topic?): Get documentation from Context7. "
            "Requires library_id from context7_resolve (e.g., '/facebook/react')."
        )
