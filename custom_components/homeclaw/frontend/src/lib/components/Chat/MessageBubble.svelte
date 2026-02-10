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
  <div class="message-content">
    {#if message.type === 'assistant'}
      {@html renderedContent}
      {#if message.isStreaming}
        <span class="streaming-cursor">▋</span>
      {/if}
    {:else}
      {message.text}
    {/if}
  </div>

  {#if formattedTime}
    <span class="message-time">{formattedTime}</span>
  {/if}
</div>

<style>
  .message {
    padding: 12px 16px;
    border-radius: 12px;
    margin-bottom: 12px;
    max-width: 80%;
    word-wrap: break-word;
    animation: fadeIn 0.3s ease-out;
  }

  .message.user {
    background: var(--primary-color);
    color: white;
    align-self: flex-end;
    margin-left: auto;
  }

  .message.assistant {
    background: var(--card-background-color);
    color: var(--primary-text-color);
    border: 1px solid var(--divider-color);
    align-self: flex-start;
  }

  .message-content {
    line-height: 1.6;
  }

  .message-time {
    display: block;
    margin-top: 4px;
    font-size: 0.7rem;
    color: #b0b0b0;
    text-align: right;
  }

  .message.user .message-time {
    color: rgba(255, 255, 255, 0.6);
  }

  .streaming-cursor {
    display: inline-block;
    margin-left: 2px;
    animation: blink 1s infinite;
    color: var(--primary-color);
    font-weight: bold;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }

  .message.streaming {
    /* Optional: add subtle pulsing effect while streaming */
    animation: fadeIn 0.3s ease-out, pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.95; }
  }

  @media (max-width: 768px) {
    .message {
      max-width: 90%;
    }
  }
</style>
