<script lang="ts">
  import type { SessionListItem } from '$lib/types';
  import { get } from 'svelte/store';
  import { appState } from "$lib/stores/appState"
  import { sessionState } from "$lib/stores/sessions"
  import { selectSession, deleteSession } from '$lib/services/session.service';
  import { formatSessionTime } from '$lib/utils/time';

  let { session }: { session: SessionListItem } = $props();

  const isActive = $derived(session.session_id === $sessionState.activeSessionId);

  // Generate avatar color from session title hash
  const avatarColor = $derived.by(() => {
    const title = session.title || 'New';
    let hash = 0;
    for (let i = 0; i < title.length; i++) {
      hash = title.charCodeAt(i) + ((hash << 5) - hash);
    }
    const colors = ['#2AABEE', '#F5A623', '#E74C3C', '#27AE60', '#9B59B6', '#1ABC9C', '#E67E22', '#3498DB'];
    return colors[Math.abs(hash) % colors.length];
  });

  // Detect voice sessions by title prefix
  const isVoice = $derived(session.title?.startsWith('Voice: ') ?? false);
  const displayTitle = $derived(isVoice ? session.title!.slice(7) : session.title);

  // Avatar displays emoji if available, otherwise first letter
  const avatarText = $derived(session.emoji || (displayTitle || 'N')[0].toUpperCase());

  async function handleClick() {
    const hass = get(appState).hass;
    if (hass && !isActive) {
      await selectSession(hass, session.session_id);
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
  class="session-item"
  class:active={isActive}
  onclick={handleClick}
  role="button"
  tabindex="0"
>
  <div class="session-avatar" style="background: {avatarColor}">
    <span>{avatarText}</span>
    {#if isVoice}
      <div class="voice-badge" title="Voice session" role="img" aria-label="Voice session">
        <svg viewBox="0 0 24 24" fill="currentColor" width="10" height="10">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
      </div>
    {/if}
  </div>
  <div class="session-content">
    <div class="session-top-row">
      <span class="session-name">{displayTitle || 'New Conversation'}</span>
      <span class="session-time">{formatSessionTime(session.updated_at)}</span>
    </div>
    <div class="session-bottom-row">
      <span class="session-preview">{session.preview || 'Start typing...'}</span>
    </div>
  </div>
  
  <button
    class="session-delete"
    onclick={handleDelete}
    aria-label="Delete session"
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
    </svg>
  </button>
</div>

<style>
  .session-item {
    display: flex;
    align-items: center;
    padding: 9px 12px;
    gap: 12px;
    cursor: pointer;
    transition: background 0.15s;
    position: relative;
  }

  .session-item:hover {
    background: var(--bg-hover, rgba(0, 0, 0, 0.04));
  }

  .session-item.active {
    background: var(--bg-active, rgba(42, 171, 238, 0.12));
  }

  .session-avatar {
    width: 50px;
    height: 50px;
    min-width: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #fff;
    flex-shrink: 0;
    position: relative;
  }

  .voice-badge {
    position: absolute;
    bottom: -1px;
    right: -1px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--primary-color, #03a9f4);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    border: 2px solid var(--card-background-color, #fff);
  }

  .voice-badge svg {
    width: 10px;
    height: 10px;
  }

  .session-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .session-top-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
  }

  .session-name {
    font-size: 15px;
    font-weight: 500;
    color: var(--primary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .session-time {
    font-size: 12px;
    color: var(--disabled-text-color);
    flex-shrink: 0;
  }

  .session-item.active .session-time {
    color: var(--accent, var(--primary-color));
  }

  .session-bottom-row {
    display: flex;
    align-items: center;
  }

  .session-preview {
    font-size: 13.5px;
    color: var(--secondary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .session-delete {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 30px;
    height: 30px;
    border: none;
    background: transparent;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.15s, background 0.15s;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    color: var(--secondary-text-color);
  }

  .session-item:hover .session-delete {
    opacity: 1;
  }

  .session-delete:hover {
    background: rgba(219, 68, 55, 0.12);
    color: var(--error-color, #db4437);
  }

  .session-delete svg {
    width: 16px;
    height: 16px;
  }
</style>
