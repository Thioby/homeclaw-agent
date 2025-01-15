"""WebSearch tool for performing web searches via Exa AI.

This tool performs web searches using Exa AI's MCP endpoint, exactly matching
OpenCode's websearch tool implementation. Supports various search types and
live crawling modes.

Usage:
    result = await websearch_tool.execute(
        query="latest Python news",
        num_results=8,
        type="auto"
    )
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult

_LOGGER = logging.getLogger(__name__)

# API Configuration (matching OpenCode)
API_CONFIG = {
    "BASE_URL": "https://mcp.exa.ai",
    "ENDPOINT": "/mcp",
    "DEFAULT_NUM_RESULTS": 8,
    "DEFAULT_TIMEOUT": 25,  # seconds
    "DEFAULT_CONTEXT_MAX_CHARS": 10000,
}


@ToolRegistry.register
class WebSearchTool(Tool):
    """Tool for performing web searches via Exa AI.

    Performs real-time web searches and returns relevant content.
    Uses the same Exa AI MCP endpoint as OpenCode.

    Supports:
        - Multiple search types (auto, fast, deep)
        - Live crawling modes (fallback, preferred)
        - Configurable result counts
        - Context length optimization for LLMs
    """

    id = "web_search"
    description = (
        "Search the web using Exa AI. Performs real-time web searches and returns "
        "content from relevant websites. Use for current events, recent data, and "
        "information beyond the AI's knowledge cutoff."
    )
    category = ToolCategory.WEB

    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="The search query",
            required=True,
        ),
        ToolParameter(
            name="num_results",
            type="integer",
            description="Number of search results to return (default: 8)",
            required=False,
            default=API_CONFIG["DEFAULT_NUM_RESULTS"],
        ),
        ToolParameter(
            name="type",
            type="string",
            description=(
                "Search type: 'auto' (balanced, default), 'fast' (quick results), "
                "'deep' (comprehensive search)"
            ),
            required=False,
            default="auto",
            enum=["auto", "fast", "deep"],
        ),
        ToolParameter(
            name="livecrawl",
            type="string",
            description=(
                "Live crawl mode: 'fallback' (use as backup if cached unavailable, default), "
                "'preferred' (prioritize live crawling)"
            ),
            required=False,
            default="fallback",
            enum=["fallback", "preferred"],
        ),
        ToolParameter(
            name="context_max_chars",
            type="integer",
            description="Maximum characters for context string (default: 10000)",
            required=False,
            default=API_CONFIG["DEFAULT_CONTEXT_MAX_CHARS"],
        ),
    ]

    async def execute(
        self,
        query: str,
        num_results: Optional[int] = None,
        type: Optional[str] = None,
        livecrawl: Optional[str] = None,
        context_max_chars: Optional[int] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Perform a web search using Exa AI.

        Args:
            query: The search query
            num_results: Number of results to return
            type: Search type (auto/fast/deep)
            livecrawl: Live crawl mode (fallback/preferred)
            context_max_chars: Maximum context characters

        Returns:
            ToolResult with search results
        """
        # Apply defaults
        num_results = num_results or API_CONFIG["DEFAULT_NUM_RESULTS"]
        search_type = type or "auto"
        crawl_mode = livecrawl or "fallback"
        max_chars = context_max_chars or API_CONFIG["DEFAULT_CONTEXT_MAX_CHARS"]

        # Build MCP request (matching OpenCode exactly)
        search_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "web_search_exa",
                "arguments": {
                    "query": query,
                    "type": search_type,
                    "numResults": num_results,
                    "livecrawl": crawl_mode,
                    "contextMaxCharacters": max_chars,
                },
            },
        }

        headers = {
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
        }

        url = f"{API_CONFIG['BASE_URL']}{API_CONFIG['ENDPOINT']}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=search_request,
                    timeout=aiohttp.ClientTimeout(total=API_CONFIG["DEFAULT_TIMEOUT"]),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return ToolResult(
                            output="",
                            success=False,
                            error=f"Search error ({response.status}): {error_text}",
                            title=f"Web search: {query}",
                        )

                    response_text = await response.text()

                    # Parse SSE response (matching OpenCode)
                    content = self._parse_sse_response(response_text)

                    if content:
                        return ToolResult(
                            output=content,
                            success=True,
                            title=f"Web search: {query}",
                            metadata={
                                "query": query,
                                "num_results": num_results,
                                "type": search_type,
                                "livecrawl": crawl_mode,
                            },
                        )

                    return ToolResult(
                        output="No search results found. Please try a different query.",
                        success=False,
                        title=f"Web search: {query}",
                        error="No results found",
                    )

        except asyncio.TimeoutError:
            return ToolResult(
                output="",
                success=False,
                error="Search request timed out",
                title=f"Web search: {query}",
            )
        except aiohttp.ClientError as e:
            return ToolResult(
                output="",
                success=False,
                error=f"Search request failed: {str(e)}",
                title=f"Web search: {query}",
            )
        except Exception as e:
            _LOGGER.exception(f"Unexpected error in web search: {e}")
            return ToolResult(
                output="",
                success=False,
                error=f"Unexpected error: {str(e)}",
                title=f"Web search: {query}",
            )

    def _parse_sse_response(self, response_text: str) -> Optional[str]:
        """Parse Server-Sent Events response from Exa AI.

        Matches OpenCode's SSE parsing logic.

        Args:
            response_text: Raw response text

        Returns:
            Extracted content text, or None if not found
        """
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

    def get_system_prompt(self) -> str:
        """Generate the system prompt for this tool."""
        today = datetime.now().strftime("%Y-%m-%d")
        return (
            f"- web_search(query, num_results?, type?, livecrawl?): Search the web for "
            f"current information. Returns content from relevant websites. "
            f"Today's date is {today} - use current year when searching for recent events."
        )


# Alternative implementation that doesn't require Exa API
# Can be used as fallback if Exa is unavailable
class SimpleWebSearchTool(Tool):
    """Simplified web search using DuckDuckGo HTML (no API key required).

    This is a fallback implementation that doesn't require any API keys.
    It performs basic searches by scraping DuckDuckGo's HTML results.

    Note: This is not registered by default. Register manually if needed:
        ToolRegistry.register(SimpleWebSearchTool)
    """

    id = "web_search_simple"
    description = (
        "Basic web search using DuckDuckGo. No API key required. "
        "Use when Exa API is unavailable."
    )
    category = ToolCategory.WEB
    enabled = False  # Disabled by default

    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="The search query",
            required=True,
        ),
        ToolParameter(
            name="num_results",
            type="integer",
            description="Number of results (approximate, default: 5)",
            required=False,
            default=5,
        ),
    ]

    async def execute(
        self,
        query: str,
        num_results: int = 5,
        **kwargs: Any,
    ) -> ToolResult:
        """Perform a basic web search using DuckDuckGo HTML.

        Args:
            query: The search query
            num_results: Approximate number of results

        Returns:
            ToolResult with search results
        """
        import re
        from urllib.parse import quote_plus

        # DuckDuckGo HTML search
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/143.0.0.0 Safari/537.36"
            ),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status != 200:
                        return ToolResult(
                            output="",
                            success=False,
                            error=f"Search failed with status: {response.status}",
                            title=f"Web search: {query}",
                        )

                    html = await response.text()

                    # Extract results (basic parsing)
                    results = []

                    # Find result links
                    link_pattern = (
                        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
                    )
                    matches = re.findall(link_pattern, html, re.IGNORECASE)

                    for url, title in matches[:num_results]:
                        if url and title:
                            results.append(f"- [{title.strip()}]({url})")

                    if results:
                        output = f"Search results for '{query}':\n\n" + "\n".join(
                            results
                        )
                        return ToolResult(
                            output=output,
                            success=True,
                            title=f"Web search: {query}",
                            metadata={"query": query, "num_results": len(results)},
                        )

                    return ToolResult(
                        output="No results found.",
                        success=False,
                        error="No results",
                        title=f"Web search: {query}",
                    )

        except Exception as e:
            return ToolResult(
                output="",
                success=False,
                error=f"Search failed: {str(e)}",
                title=f"Web search: {query}",
            )
