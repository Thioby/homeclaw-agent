<script lang="ts">
  import type { SessionListItem } from '$lib/types';
  import { get } from 'svelte/store';
  import { appState } from '$lib/stores/appState';
  import { sessionState } from '$lib/stores/sessions';
  import { selectSession, deleteSession } from '$lib/services/session.service';
  import { formatSessionTime } from '$lib/utils/time';
  import Icon from '../Icon.svelte';

  let { session }: { session: SessionListItem } = $props();

  const isActive = $derived(session.session_id === $sessionState.activeSessionId);

  // Voice sessions get the mic glyph; otherwise leave room for emoji.
  const isVoice = $derived(session.title?.startsWith('Voice: ') ?? false);
  const displayTitle = $derived(isVoice ? session.title!.slice(7) : session.title);

  async function handleClick() {
    const hass = get(appState).hass;
    if (hass && !isActive) {
      await selectSession(hass, session.session_id);
    }
  }

  async function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      await handleClick();
    }
  }

  async function handleDelete(e: MouseEvent) {
    e.stopPropagation();
    const hass = get(appState).hass;
    if (!hass) return;

    if (confirm('Delete this conversation?')) {
      await deleteSession(hass, session.session_id);
    }
  }
</script>

<div
  class="hc-session"
  class:is-active={isActive}
  onclick={handleClick}
  onkeydown={handleKeydown}
  role="button"
  tabindex="0"
>
  <div class="hc-session-row">
    {#if isVoice}
      <span class="hc-session-voice" title="Voice session" aria-label="Voice session">
        <Icon name="mic" size={11} />
      </span>
    {:else if session.emoji}
      <span class="hc-session-emoji" aria-hidden="true">{session.emoji}</span>
    {/if}
    <div class="hc-session-title">{displayTitle || 'New conversation'}</div>
    <div class="hc-session-time">{formatSessionTime(session.updated_at)}</div>
    <button
      class="hc-session-del"
      onclick={handleDelete}
      aria-label="Delete session"
      title="Delete"
    >
      <Icon name="x" size={12} />
    </button>
  </div>
  {#if session.preview}
    <div class="hc-session-preview">{session.preview}</div>
  {/if}
</div>

<style>
  .hc-session {
    padding: 8px 10px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.1s;
    position: relative;
  }

  .hc-session:hover {
    background: var(--hc-bg-sunken);
  }

  .hc-session.is-active {
    background: var(--hc-card-bg);
    box-shadow: 0 0 0 1px var(--hc-line-strong);
  }

  .hc-session:focus-visible {
    outline: 2px solid var(--hc-ink);
    outline-offset: -2px;
  }

  .hc-session-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .hc-session-emoji {
    font-size: 13px;
    line-height: 1;
    flex-shrink: 0;
  }

  .hc-session-voice {
    display: inline-flex;
    align-items: center;
    color: var(--hc-cool);
    flex-shrink: 0;
  }

  .hc-session-title {
    flex: 1;
    font-size: 13.5px;
    font-weight: 500;
    color: var(--hc-ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .hc-session-time {
    font-family: var(--hc-font-mono);
    font-size: 10.5px;
    color: var(--hc-ink-3);
    flex-shrink: 0;
  }

  .hc-session.is-active .hc-session-time {
    color: var(--hc-ink-2);
  }

  .hc-session-del {
    width: 20px;
    height: 20px;
    border: 0;
    background: transparent;
    color: var(--hc-ink-3);
    border-radius: 4px;
    cursor: pointer;
    opacity: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    transition: opacity 0.12s, background 0.12s, color 0.12s;
    flex-shrink: 0;
  }

  .hc-session:hover .hc-session-del,
  .hc-session:focus-within .hc-session-del {
    opacity: 1;
  }

  .hc-session-del:hover {
    background: color-mix(in oklab, var(--hc-warn) 15%, transparent);
    color: var(--hc-warn);
  }

  .hc-session-preview {
    font-size: 12.5px;
    color: var(--hc-ink-3);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
