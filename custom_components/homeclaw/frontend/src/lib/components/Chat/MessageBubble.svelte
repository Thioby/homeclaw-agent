<script lang="ts">
  import type { Message } from '$lib/types';
  import { get } from 'svelte/store';
  import { renderMarkdown } from '$lib/services/markdown.service';
  import { sessionState } from '$lib/stores/sessions';
  import { updateSessionRuntime } from '$lib/stores/chatRuntime';
  import { appState } from '$lib/stores/appState';
  import DashboardAction from './DashboardAction.svelte';
  import Avatar from '../Avatar.svelte';

  let { message, hass }: { message: Message; hass: any } = $props();

  const renderedContent = $derived(
    message.type === 'assistant'
      ? renderMarkdown(message.text, get(sessionState).activeSessionId || undefined)
      : message.text
  );

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

  const isUser = $derived(message.type === 'user');
  const senderName = $derived(isUser ? 'You' : ($appState.agentName || 'Homeclaw'));
  // Bot avatar uses the home icon for visual consistency; agent_emoji is
  // shown next to the name in the meta-row instead of inside the 28px box.
  const senderEmoji = $derived('');

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

  function updateToolResultStatus(toolCallId: string, newStatus: string) {
    const sessionId = get(sessionState).activeSessionId;
    if (!sessionId) return;
    updateSessionRuntime(sessionId, (r) => ({
      ...r,
      messages: r.messages.map((msg) =>
        msg.id === message.id
          ? {
              ...msg,
              toolResults: (msg.toolResults || []).map((tr) =>
                tr.toolCallId === toolCallId ? { ...tr, status: newStatus as any } : tr
              ),
            }
          : msg
      ),
    }));
  }
</script>

<div class="hc-msg" class:is-user={isUser} class:is-bot={!isUser} class:streaming={message.isStreaming}>
  <Avatar from={isUser ? 'user' : 'bot'} name={senderName} emoji={senderEmoji} />

  <div class="hc-msg-body">
    <div class="hc-msg-meta">
      <span class="hc-msg-name">{senderName}</span>
      {#if !isUser && $appState.agentEmoji}
        <span class="hc-msg-name-emoji" aria-hidden="true">{$appState.agentEmoji}</span>
      {/if}
      {#if formattedTime}
        <span class="hc-msg-time">{formattedTime}</span>
      {/if}
    </div>

    {#if hasAttachments}
      <div class="hc-attachments">
        {#if imageAttachments.length > 0}
          <div class="hc-image-attachments">
            {#each imageAttachments as att (att.file_id)}
              {#if att.data_url}
                <img src={att.data_url} alt={att.filename} class="hc-attached-image" loading="lazy" />
              {:else if att.thumbnail_b64}
                <img
                  src={`data:${att.mime_type};base64,${att.thumbnail_b64}`}
                  alt={att.filename}
                  class="hc-attached-image"
                  loading="lazy"
                />
              {:else}
                <div class="hc-image-placeholder">
                  <svg viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>
                  <span>{att.filename}</span>
                </div>
              {/if}
            {/each}
          </div>
        {/if}

        {#if fileAttachments.length > 0}
          <div class="hc-file-attachments">
            {#each fileAttachments as att (att.file_id)}
              <div class="hc-file-chip">
                <svg viewBox="0 0 24 24" class="hc-file-icon">
                  {#if att.mime_type === 'application/pdf'}
                    <path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 9.5h1v-1H9v1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm10 5.5h1v-3h-1v3z"/>
                  {:else}
                    <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                  {/if}
                </svg>
                <span class="hc-file-name" title={att.filename}>{att.filename}</span>
                <span class="hc-file-size">{formatSize(att.size)}</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    {#if message.text || message.type === 'assistant'}
      <div class="hc-bubble">
        {#if message.type === 'assistant'}
          {@html renderedContent}
          {#if message.isStreaming}
            <span class="hc-streaming-cursor">&#9611;</span>
          {/if}
        {:else if message.text}
          {message.text}
        {/if}
      </div>
    {/if}

    {#if message.toolResults?.length}
      {#each message.toolResults as tr (tr.toolCallId)}
        {#if tr.result?.ui_type === 'dashboard_action'}
          <DashboardAction
            action={tr.result.action}
            status={tr.status}
            toolResult={tr.result}
            toolCallId={tr.toolCallId}
            sessionId={get(sessionState).activeSessionId || ''}
            {hass}
            onStatusChange={(s) => updateToolResultStatus(tr.toolCallId, s)}
          />
        {/if}
      {/each}
    {/if}
  </div>
</div>

<style>
  .hc-msg {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    margin-bottom: var(--hc-msg-gap, 22px);
    animation: hcMsgAppear 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }

  .hc-msg.is-user {
    flex-direction: row-reverse;
  }

  .hc-msg-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
    max-width: calc(100% - 40px);
  }

  .hc-msg.is-user .hc-msg-body {
    align-items: flex-end;
  }

  .hc-msg-meta {
    font-size: 11.5px;
    color: var(--hc-ink-3);
    display: flex;
    gap: 8px;
    align-items: baseline;
  }

  .hc-msg-name {
    font-weight: 500;
    color: var(--hc-ink-2);
  }

  .hc-msg-name-emoji {
    font-size: 12px;
    line-height: 1;
  }

  .hc-msg-time {
    font-family: var(--hc-font-mono);
    font-size: 10.5px;
  }

  .hc-bubble {
    background: var(--hc-card-bg);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius);
    padding: 12px 14px;
    font-size: 14.5px;
    line-height: 1.55;
    color: var(--hc-ink);
    word-wrap: break-word;
    overflow-wrap: break-word;
    max-width: 100%;
  }

  .hc-msg.is-user .hc-bubble {
    background: var(--hc-ink);
    color: var(--hc-bg);
    border-color: var(--hc-ink);
  }

  /* Markdown content inside bubble */
  .hc-bubble :global(p) {
    margin: 0 0 8px 0;
  }
  .hc-bubble :global(p:last-child) {
    margin-bottom: 0;
  }
  .hc-bubble :global(strong) {
    font-weight: 600;
  }
  .hc-bubble :global(code) {
    font-family: var(--hc-font-mono);
    font-size: 12.5px;
    background: var(--hc-bg-sunken);
    padding: 1px 5px;
    border-radius: 4px;
    color: var(--hc-ink-2);
  }
  .hc-msg.is-user .hc-bubble :global(code) {
    background: rgba(255, 255, 255, 0.12);
    color: inherit;
  }
  .hc-bubble :global(pre) {
    background: var(--hc-bg-sunken);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius-sm);
    padding: 10px 12px;
    margin: 8px 0;
    overflow-x: auto;
    font-size: 12.5px;
    line-height: 1.45;
  }
  .hc-msg.is-user .hc-bubble :global(pre) {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.12);
  }
  .hc-bubble :global(pre code) {
    background: none;
    padding: 0;
    font-size: 12.5px;
  }
  .hc-bubble :global(ul),
  .hc-bubble :global(ol) {
    padding-left: 20px;
    margin: 6px 0;
  }
  .hc-bubble :global(li) {
    margin: 2px 0;
  }
  .hc-bubble :global(h1),
  .hc-bubble :global(h2),
  .hc-bubble :global(h3) {
    font-family: var(--hc-font-display);
    font-weight: 500;
    letter-spacing: -0.01em;
    margin: 12px 0 6px;
    line-height: 1.2;
  }
  .hc-bubble :global(h1) { font-size: 1.4em; }
  .hc-bubble :global(h2) { font-size: 1.2em; }
  .hc-bubble :global(h3) { font-size: 1.05em; }
  .hc-bubble :global(a) {
    color: var(--hc-cool);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .hc-msg.is-user .hc-bubble :global(a) {
    color: var(--hc-bg);
  }

  /* Attachments */
  .hc-attachments {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .hc-msg.is-user .hc-attachments {
    align-items: flex-end;
  }

  .hc-image-attachments,
  .hc-file-attachments {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .hc-attached-image {
    max-width: 280px;
    max-height: 220px;
    border-radius: var(--hc-radius-sm);
    object-fit: contain;
    display: block;
    border: 1px solid var(--hc-line);
  }

  .hc-image-placeholder {
    width: 120px;
    height: 80px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: var(--hc-bg-sunken);
    border-radius: var(--hc-radius-sm);
    gap: 4px;
  }
  .hc-image-placeholder svg {
    width: 22px;
    height: 22px;
    fill: var(--hc-ink-3);
  }
  .hc-image-placeholder span {
    font-size: 10px;
    color: var(--hc-ink-3);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100px;
  }

  .hc-file-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: var(--hc-card-bg);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius-sm);
    font-size: 12px;
    color: var(--hc-ink-2);
    max-width: 240px;
  }
  .hc-file-icon {
    width: 14px;
    height: 14px;
    fill: var(--hc-ink-3);
    flex-shrink: 0;
  }
  .hc-file-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
  }
  .hc-file-size {
    color: var(--hc-ink-3);
    white-space: nowrap;
    font-size: 11px;
  }

  .hc-streaming-cursor {
    display: inline-block;
    margin-left: 2px;
    animation: hcBlink 1s infinite;
    color: var(--hc-ink-3);
    font-weight: bold;
  }

  @keyframes hcBlink {
    0%, 50%   { opacity: 1; }
    51%, 100% { opacity: 0; }
  }

  @keyframes hcMsgAppear {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  @media (max-width: 768px) {
    .hc-msg {
      gap: 10px;
    }
    .hc-msg-body {
      max-width: calc(100% - 38px);
    }
  }
</style>
