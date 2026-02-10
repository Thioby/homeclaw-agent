<script lang="ts">
  import type { Message } from '$lib/types';
  import { get } from 'svelte/store';
  import { renderMarkdown } from '$lib/services/markdown.service';
  import { sessionState } from '$lib/stores/sessions';

  // Props
  let { message }: { message: Message } = $props();

  // Render markdown for assistant messages
  const renderedContent = $derived(
    message.type === 'assistant' 
      ? renderMarkdown(message.text, get(sessionState).activeSessionId || undefined)
      : message.text
  );

  // Format timestamp for display
  const formattedTime = $derived.by(() => {
    if (!message.timestamp) return '';
    try {
      const d = new Date(message.timestamp);
      if (isNaN(d.getTime())) return '';
      const now = new Date();
      const isToday =
        d.getDate() === now.getDate() &&
        d.getMonth() === now.getMonth() &&
        d.getFullYear() === now.getFullYear();
      const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      if (isToday) return time;
      const date = d.toLocaleDateString([], { day: 'numeric', month: 'short' });
      return `${date}, ${time}`;
    } catch {
      return '';
    }
  });
</script>

<div class="message" class:user={message.type === 'user'} class:assistant={message.type === 'assistant'} class:streaming={message.isStreaming}>
  <div class="bubble">
    {#if message.type === 'assistant'}
      {@html renderedContent}
      {#if message.isStreaming}
        <span class="streaming-cursor">▋</span>
      {/if}
    {:else}
      {message.text}
    {/if}
    {#if formattedTime}
      <span class="bubble-time">{formattedTime}</span>
    {/if}
  </div>
</div>

<style>
  .message {
    display: flex;
    margin-bottom: 3px;
    animation: messageAppear 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }

  /* Group spacing: different sender = more space */
  :global(.message.user + .message.assistant),
  :global(.message.assistant + .message.user) {
    margin-top: 10px;
  }

  .message.user {
    justify-content: flex-end;
  }

  .message.assistant {
    justify-content: flex-start;
  }

  .bubble {
    max-width: min(80%, 500px);
    padding: 7px 11px;
    position: relative;
    line-height: 1.45;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }

  /* User bubble — right side, Telegram-style */
  .message.user .bubble {
    background: var(--bubble-user);
    color: var(--text-bubble-user);
    border-radius: 12px 12px 4px 12px;
  }

  /* User bubble tail (CSS triangle) */
  .message.user .bubble::after {
    content: '';
    position: absolute;
    right: -8px;
    bottom: 0;
    width: 0;
    height: 0;
    border: 8px solid transparent;
    border-left-color: var(--bubble-user-tail);
    border-bottom-color: var(--bubble-user-tail);
    border-right: 0;
    border-bottom-right-radius: 4px;
  }

  /* Hide tail on consecutive same-type messages */
  :global(.message.user + .message.user .bubble)::after {
    display: none;
  }

  /* Assistant bubble — left side */
  .message.assistant .bubble {
    background: var(--bubble-assistant);
    color: var(--text-bubble-assistant);
    border-radius: 12px 12px 12px 4px;
  }

  /* Assistant bubble tail */
  .message.assistant .bubble::after {
    content: '';
    position: absolute;
    left: -8px;
    bottom: 0;
    width: 0;
    height: 0;
    border: 8px solid transparent;
    border-right-color: var(--bubble-assistant-tail);
    border-bottom-color: var(--bubble-assistant-tail);
    border-left: 0;
    border-bottom-left-radius: 4px;
  }

  :global(.message.assistant + .message.assistant .bubble)::after {
    display: none;
  }

  /* Timestamp INSIDE bubble — Telegram style */
  .bubble-time {
    float: right;
    font-size: 11px;
    margin: 4px -4px -2px 12px;
    color: var(--text-bubble-time);
    white-space: nowrap;
  }

  .message.user .bubble-time {
    color: var(--text-bubble-time-user);
  }

  /* Bubble content formatting (from markdown) */
  .bubble :global(p) { margin-bottom: 6px; }
  .bubble :global(p:last-of-type) { margin-bottom: 0; }
  .bubble :global(strong) { font-weight: 600; }
  .bubble :global(code) {
    background: var(--bubble-code-bg);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 13px;
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  }
  .bubble :global(pre) {
    background: var(--bubble-code-bg);
    border-radius: 8px;
    padding: 10px 12px;
    margin: 6px 0;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.4;
  }
  .bubble :global(pre code) {
    background: none;
    padding: 0;
    font-size: 13px;
  }
  .bubble :global(ul), .bubble :global(ol) {
    padding-left: 18px;
    margin: 4px 0;
  }
  .bubble :global(li) { margin: 2px 0; }

  /* Streaming cursor */
  .streaming-cursor {
    display: inline-block;
    margin-left: 2px;
    animation: blink 1s infinite;
    color: var(--accent, var(--primary-color));
    font-weight: bold;
  }

  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }

  .message.streaming {
    animation: messageAppear 0.3s ease-out;
  }

  @media (max-width: 768px) {
    .bubble {
      max-width: min(88%, 500px);
    }
  }

  @media (max-width: 400px) {
    .bubble {
      max-width: 92%;
      font-size: 13.5px;
    }
  }
</style>
