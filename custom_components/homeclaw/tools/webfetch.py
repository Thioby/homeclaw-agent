"""WebFetch tool for fetching and parsing web content.

This tool fetches content from URLs and converts it to the requested format
(markdown, text, or html). Implementation matches OpenCode's webfetch tool.

Usage:
    result = await webfetch_tool.execute(
        url="https://example.com",
        format="markdown",
        timeout=30
    )
"""

import asyncio
import logging
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult

_LOGGER = logging.getLogger(__name__)

# Constants matching OpenCode implementation
MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB
DEFAULT_TIMEOUT = 30  # seconds
MAX_TIMEOUT = 120  # seconds

# User-Agent to mimic browser (matching OpenCode)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/143.0.0.0 Safari/537.36"
)


class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML, skipping script/style content."""

    def __init__(self):
        super().__init__()
        self.result: List[str] = []
        self.skip_tags = {"script", "style", "noscript", "iframe", "object", "embed"}
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag.lower() in self.skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.result.append(text)

    def get_text(self) -> str:
        return " ".join(self.result)


def extract_text_from_html(html: str) -> str:
    """Extract plain text from HTML content.

    Args:
        html: Raw HTML content

    Returns:
        Plain text with HTML tags removed
    """
    parser = HTMLTextExtractor()
    try:
        parser.feed(html)
        return parser.get_text()
    except Exception as e:
        _LOGGER.warning(f"HTML parsing failed, using regex fallback: {e}")
        # Fallback: use regex
        # Remove script and style tags
        html = re.sub(
            r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        # Remove all other tags
        text = re.sub(r"<[^>]+>", "", html)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text


def convert_html_to_markdown(html: str) -> str:
    """Convert HTML to Markdown format.

    This is a simplified implementation matching OpenCode's TurndownService.
    For production use, consider using a library like markdownify.

    Args:
        html: Raw HTML content

    Returns:
        Markdown-formatted content
    """
    # Remove script, style, meta, link tags (matching TurndownService.remove())
    html = re.sub(
        r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<meta[^>]*/?>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<link[^>]*/?>", "", html, flags=re.IGNORECASE)

    # Convert headers (h1-h6)
    for i in range(1, 7):
        pattern = rf"<h{i}[^>]*>(.*?)</h{i}>"
        replacement = "#" * i + r" \1\n\n"
        html = re.sub(pattern, replacement, html, flags=re.DOTALL | re.IGNORECASE)

    # Convert links: <a href="url">text</a> -> [text](url)
    html = re.sub(
        r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        r"[\2](\1)",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Convert images: <img src="url" alt="text"> -> ![text](url)
    html = re.sub(
        r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*/?>',
        r"![\2](\1)",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<img[^>]*alt=["\']([^"\']*)["\'][^>]*src=["\']([^"\']*)["\'][^>]*/?>',
        r"![\1](\2)",
        html,
        flags=re.IGNORECASE,
    )

    # Convert bold: <strong>text</strong> or <b>text</b> -> **text**
    html = re.sub(
        r"<(?:strong|b)[^>]*>(.*?)</(?:strong|b)>",
        r"**\1**",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Convert italic: <em>text</em> or <i>text</i> -> *text*
    html = re.sub(
        r"<(?:em|i)[^>]*>(.*?)</(?:em|i)>",
        r"*\1*",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Convert code blocks: <pre><code>text</code></pre> -> ```text```
    html = re.sub(
        r"<pre[^>]*><code[^>]*>(.*?)</code></pre>",
        r"\n```\n\1\n```\n",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Convert inline code: <code>text</code> -> `text`
    html = re.sub(
        r"<code[^>]*>(.*?)</code>", r"`\1`", html, flags=re.DOTALL | re.IGNORECASE
    )

    # Convert blockquotes: <blockquote>text</blockquote> -> > text
    html = re.sub(
        r"<blockquote[^>]*>(.*?)</blockquote>",
        lambda m: "\n"
        + "\n".join(f"> {line}" for line in m.group(1).strip().split("\n"))
        + "\n",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Convert unordered lists
    html = re.sub(
        r"<ul[^>]*>(.*?)</ul>", r"\1\n", html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(
        r"<li[^>]*>(.*?)</li>", r"- \1\n", html, flags=re.DOTALL | re.IGNORECASE
    )

    # Convert ordered lists (simplified - uses - instead of numbers)
    html = re.sub(
        r"<ol[^>]*>(.*?)</ol>", r"\1\n", html, flags=re.DOTALL | re.IGNORECASE
    )

    # Convert horizontal rules
    html = re.sub(r"<hr[^>]*/?>", "\n---\n", html, flags=re.IGNORECASE)

    # Convert line breaks
    html = re.sub(r"<br[^>]*/?>", "\n", html, flags=re.IGNORECASE)

    # Convert paragraphs
    html = re.sub(r"</p>", "\n\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<p[^>]*>", "", html, flags=re.IGNORECASE)

    # Remove remaining HTML tags
    html = re.sub(r"<[^>]+>", "", html)

    # Decode HTML entities
    html = html.replace("&nbsp;", " ")
    html = html.replace("&amp;", "&")
    html = html.replace("&lt;", "<")
    html = html.replace("&gt;", ">")
    html = html.replace("&quot;", '"')
    html = html.replace("&#39;", "'")

    # Normalize whitespace (but preserve intentional line breaks)
    lines = html.split("\n")
    normalized_lines = []
    for line in lines:
        # Collapse multiple spaces within a line
        line = re.sub(r"[ \t]+", " ", line).strip()
        normalized_lines.append(line)

    # Remove excessive blank lines (more than 2 consecutive)
    result = "\n".join(normalized_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


def get_accept_header(format: str) -> str:
    """Get the Accept header based on requested format.

    Matches OpenCode's header generation.

    Args:
        format: One of 'markdown', 'text', 'html'

    Returns:
        Accept header string with q-parameters
    """
    headers = {
        "markdown": "text/markdown;q=1.0, text/x-markdown;q=0.9, text/plain;q=0.8, text/html;q=0.7, */*;q=0.1",
        "text": "text/plain;q=1.0, text/markdown;q=0.9, text/html;q=0.8, */*;q=0.1",
        "html": "text/html;q=1.0, application/xhtml+xml;q=0.9, text/plain;q=0.8, text/markdown;q=0.7, */*;q=0.1",
    }
    return headers.get(
        format, "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    )


@ToolRegistry.register
class WebFetchTool(Tool):
    """Tool for fetching and parsing web content.

    Fetches content from a URL and converts it to the requested format.
    Supports markdown (default), plain text, or raw HTML output.

    Matches OpenCode's webfetch tool implementation.
    """

    id = "web_fetch"
    description = (
        "Fetch content from a URL. Returns content as markdown (default), "
        "text, or html. Use for retrieving and analyzing web content."
    )
    category = ToolCategory.WEB

    parameters = [
        ToolParameter(
            name="url",
            type="string",
            description="The URL to fetch content from (must start with http:// or https://)",
            required=True,
        ),
        ToolParameter(
            name="format",
            type="string",
            description="Output format: 'markdown' (default), 'text', or 'html'",
            required=False,
            default="markdown",
            enum=["markdown", "text", "html"],
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Request timeout in seconds (default: 30, max: 120)",
            required=False,
            default=DEFAULT_TIMEOUT,
        ),
    ]

    async def execute(
        self,
        url: str,
        format: str = "markdown",
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Fetch content from a URL and convert to the requested format.

        Args:
            url: The URL to fetch
            format: Output format ('markdown', 'text', or 'html')
            timeout: Request timeout in seconds

        Returns:
            ToolResult with the fetched and formatted content
        """
        # Validate URL
        if not url.startswith("http://") and not url.startswith("https://"):
            return ToolResult(
                output="",
                success=False,
                error="URL must start with http:// or https://",
                title=f"WebFetch Error: {url}",
            )

        # Normalize timeout
        effective_timeout = min(timeout or DEFAULT_TIMEOUT, MAX_TIMEOUT)

        # Build headers
        accept_header = get_accept_header(format)
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": accept_header,
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=effective_timeout),
                    allow_redirects=True,
                ) as response:
                    # Check response status
                    if response.status != 200:
                        return ToolResult(
                            output="",
                            success=False,
                            error=f"Request failed with status code: {response.status}",
                            title=f"WebFetch Error: {url}",
                        )

                    # Check content length before reading
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > MAX_RESPONSE_SIZE:
                        return ToolResult(
                            output="",
                            success=False,
                            error="Response too large (exceeds 5MB limit)",
                            title=f"WebFetch Error: {url}",
                        )

                    # Read response
                    content_bytes = await response.read()

                    # Check actual size
                    if len(content_bytes) > MAX_RESPONSE_SIZE:
                        return ToolResult(
                            output="",
                            success=False,
                            error="Response too large (exceeds 5MB limit)",
                            title=f"WebFetch Error: {url}",
                        )

                    # Decode content
                    # Try to get encoding from response, fallback to utf-8
                    encoding = response.charset or "utf-8"
                    try:
                        content = content_bytes.decode(encoding)
                    except UnicodeDecodeError:
                        content = content_bytes.decode("utf-8", errors="replace")

                    content_type = response.headers.get("content-type", "")
                    title = f"{url} ({content_type})"

                    # Process content based on format and content type
                    output = self._process_content(content, content_type, format)

                    return ToolResult(
                        output=output,
                        success=True,
                        title=title,
                        metadata={
                            "url": url,
                            "content_type": content_type,
                            "format": format,
                            "content_length": len(content),
                        },
                    )

        except asyncio.TimeoutError:
            return ToolResult(
                output="",
                success=False,
                error=f"Request timed out after {effective_timeout} seconds",
                title=f"WebFetch Timeout: {url}",
            )
        except aiohttp.ClientError as e:
            return ToolResult(
                output="",
                success=False,
                error=f"Request failed: {str(e)}",
                title=f"WebFetch Error: {url}",
            )
        except Exception as e:
            _LOGGER.exception(f"Unexpected error fetching {url}: {e}")
            return ToolResult(
                output="",
                success=False,
                error=f"Unexpected error: {str(e)}",
                title=f"WebFetch Error: {url}",
            )

    def _process_content(self, content: str, content_type: str, format: str) -> str:
        """Process content based on format and content type.

        Args:
            content: Raw content string
            content_type: HTTP Content-Type header
            format: Requested output format

        Returns:
            Processed content string
        """
        is_html = "text/html" in content_type.lower()

        if format == "html":
            return content

        if format == "text":
            if is_html:
                return extract_text_from_html(content)
            return content

        # Default: markdown
        if is_html:
            return convert_html_to_markdown(content)
        return content

    def get_system_prompt(self) -> str:
        """Generate the system prompt for this tool."""
        return (
            "- web_fetch(url, format?): Fetch content from a URL and return as "
            "markdown (default), text, or html. Use for web research and content analysis."
        )
