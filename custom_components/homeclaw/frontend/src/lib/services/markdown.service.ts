import { marked } from 'marked';
import { markedHighlight } from 'marked-highlight';
import hljs from '@highlightjs/cdn-assets/es/highlight.min.js';
import yaml from '@highlightjs/cdn-assets/es/languages/yaml.min.js';
import DOMPurify from 'dompurify';

// Register YAML language for syntax highlighting
hljs.registerLanguage('yaml', yaml);

// Configure marked with syntax highlighting
marked.use(
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return hljs.highlightAuto(code).value;
    },
  })
);

// Configure marked for GitHub Flavored Markdown
marked.use({
  gfm: true,
  breaks: true,
});

/**
 * Markdown cache - keyed by session ID to prevent content leaks between sessions
 */
const markdownCache = new Map<string, Map<string, string>>();

/**
 * Render markdown with syntax highlighting and sanitization
 * Cache is per-session to prevent content leaks
 */
export function renderMarkdown(text: string, sessionId?: string): string {
  if (!text) return '';

  const cacheKey = sessionId || 'default';

  // Get or create session cache
  if (!markdownCache.has(cacheKey)) {
    markdownCache.set(cacheKey, new Map());
  }

  const sessionCache = markdownCache.get(cacheKey)!;

  // Check cache
  if (sessionCache.has(text)) {
    return sessionCache.get(text)!;
  }

  try {
    // Parse markdown
    const rawHtml = marked.parse(text) as string;

    // Sanitize to prevent XSS
    const sanitized = DOMPurify.sanitize(rawHtml, {
      ALLOWED_TAGS: [
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'p',
        'br',
        'ul',
        'ol',
        'li',
        'strong',
        'em',
        'code',
        'pre',
        'blockquote',
        'a',
        'span',
        'hr',
      ],
      ALLOWED_ATTR: ['href', 'target', 'rel', 'class'],
    });

    // Cache the result (limit cache size per session)
    if (sessionCache.size > 100) {
      const firstKey = sessionCache.keys().next().value;
      if (firstKey) {
        sessionCache.delete(firstKey);
      }
    }

    sessionCache.set(text, sanitized);
    return sanitized;
  } catch (e) {
    console.error('Markdown rendering error:', e);
    return text;
  }
}

/**
 * Clear markdown cache for a specific session
 */
export function clearSessionCache(sessionId: string): void {
  markdownCache.delete(sessionId);
}

/**
 * Clear all markdown caches
 */
export function clearAllCaches(): void {
  markdownCache.clear();
}
