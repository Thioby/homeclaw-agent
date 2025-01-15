/**
 * DOM manipulation utilities
 */

/**
 * Scroll element to bottom
 */
export function scrollToBottom(element: HTMLElement | null): void {
  if (element) {
    element.scrollTop = element.scrollHeight;
  }
}

/**
 * Auto-resize textarea based on content
 */
export function autoResize(textarea: HTMLTextAreaElement, maxHeight: number = 200): void {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, maxHeight) + 'px';
}

/**
 * Check if device is mobile
 */
export function isMobile(): boolean {
  return typeof window !== 'undefined' && window.innerWidth <= 768;
}

/**
 * Escape HTML to prevent XSS
 */
export function escapeHTML(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
