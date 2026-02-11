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

  // Check if message has attachments
  const hasAttachments = $derived(
    message.attachments && message.attachments.length > 0
  );

  const imageAttachments = $derived(
    (message.attachments || []).filter((a) => a.is_image)
  );

  const fileAttachments = $derived(
    (message.attachments || []).filter((a) => !a.is_image)
  );

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
</script>

<div
  class="message"
  class:user={message.type === 'user'}
  class:assistant={message.type === 'assistant'}
  class:streaming={message.isStreaming}
>
  <div class="bubble">
    {#if hasAttachments}
      <div class="attachments">
        {#if imageAttachments.length > 0}
          <div class="image-attachments">
            {#each imageAttachments as att (att.file_id)}
              {#if att.data_url}
                <img
                  src={att.data_url}
                  alt={att.filename}
                  class="attached-image"
                  loading="lazy"
                />
              {:else if att.thumbnail_b64}
                <img
                  src={`data:${att.mime_type};base64,${att.thumbnail_b64}`}
                  alt={att.filename}
                  class="attached-image"
                  loading="lazy"
                />
              {:else}
                <div class="image-placeholder">
                  <svg viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>
                  <span>{att.filename}</span>
                </div>
              {/if}
            {/each}
          </div>
        {/if}

        {#if fileAttachments.length > 0}
          <div class="file-attachments">
            {#each fileAttachments as att (att.file_id)}
              <div class="file-chip">
                <svg viewBox="0 0 24 24" class="file-icon">
                  {#if att.mime_type === 'application/pdf'}
                    <path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 9.5h1v-1H9v1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm10 5.5h1v-3h-1v3z"/>
                  {:else}
                    <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                  {/if}
                </svg>
                <span class="file-name" title={att.filename}>{att.filename}</span>
                <span class="file-size">{formatSize(att.size)}</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    {#if message.type === 'assistant'}
      {@html renderedContent}
      {#if message.isStreaming}
        <span class="streaming-cursor">&#9611;</span>
      {/if}
    {:else if message.text}
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
    overflow: hidden;
  }

  /* User bubble -- right side, Telegram-style */
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

  /* Assistant bubble -- left side */
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

  /* Timestamp INSIDE bubble -- Telegram style */
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

  /* --- Attachments --- */
  .attachments {
    margin-bottom: 6px;
  }

  .image-attachments {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 4px;
  }

  .attached-image {
    max-width: 260px;
    max-height: 200px;
    border-radius: 8px;
    object-fit: contain;
    cursor: pointer;
    display: block;
  }

  .image-placeholder {
    width: 120px;
    height: 80px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.06);
    border-radius: 8px;
    gap: 4px;
  }

  .image-placeholder svg {
    width: 24px;
    height: 24px;
    fill: var(--secondary-text-color);
  }

  .image-placeholder span {
    font-size: 10px;
    color: var(--secondary-text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100px;
  }

  .file-attachments {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 4px;
  }

  .file-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: rgba(0, 0, 0, 0.06);
    border-radius: 8px;
    font-size: 12px;
    max-width: 200px;
  }

  .message.user .file-chip {
    background: rgba(255, 255, 255, 0.15);
  }

  .file-icon {
    width: 16px;
    height: 16px;
    min-width: 16px;
    fill: currentColor;
    opacity: 0.7;
  }

  .file-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
  }

  .file-size {
    opacity: 0.6;
    white-space: nowrap;
    font-size: 11px;
  }

  /* Bubble content formatting (from markdown) */
  .bubble :global(p) {
    margin-bottom: 6px;
  }
  .bubble :global(p:last-of-type) {
    margin-bottom: 0;
  }
  .bubble :global(strong) {
    font-weight: 600;
  }
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
  .bubble :global(ul),
  .bubble :global(ol) {
    padding-left: 18px;
    margin: 4px 0;
  }
  .bubble :global(li) {
    margin: 2px 0;
  }

  /* Streaming cursor */
  .streaming-cursor {
    display: inline-block;
    margin-left: 2px;
    animation: blink 1s infinite;
    color: var(--accent, var(--primary-color));
    font-weight: bold;
  }

  @keyframes blink {
    0%,
    50% {
      opacity: 1;
    }
    51%,
    100% {
      opacity: 0;
    }
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
