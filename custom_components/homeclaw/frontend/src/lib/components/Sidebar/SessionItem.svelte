<script lang="ts">
  import type { SessionListItem } from '$lib/types';
  import { get } from 'svelte/store';
  import { appState } from "$lib/stores/appState"
  import { sessionState } from "$lib/stores/sessions"
  import { selectSession, deleteSession } from '$lib/services/session.service';
  import { formatSessionTime } from '$lib/utils/time';

  let { session }: { session: SessionListItem } = $props();

  const isActive = $derived(session.session_id === $sessionState.activeSessionId);

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
  <span class="session-title">{session.title || 'New Conversation'}</span>
  <span class="session-preview">{session.preview || 'Start typing...'}</span>
  <span class="session-time">{formatSessionTime(session.updated_at)}</span>
  
  <button
    class="session-delete"
    onclick={handleDelete}
    aria-label="Delete session"
  >
    <svg viewBox="0 0 24 24" class="icon">
      <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
    </svg>
  </button>
</div>

<style>
  .session-item {
    display: flex;
    flex-direction: column;
    padding: 12px;
    margin-bottom: 4px;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.2s, transform 0.2s;
    position: relative;
    animation: slideIn 0.2s ease-out;
  }

  .session-item:active {
    transform: scale(0.98);
  }

  .session-item:hover {
    background: var(--card-background-color);
  }

  .session-item.active {
    background: rgba(3, 169, 244, 0.15);
    border-left: 3px solid var(--primary-color);
  }

  .session-title {
    font-size: 14px;
    font-weight: 500;
    color: var(--primary-text-color);
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-right: 24px;
  }

  .session-preview {
    font-size: 12px;
    color: var(--secondary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .session-time {
    font-size: 11px;
    color: var(--disabled-text-color);
    margin-top: 4px;
  }

  .session-delete {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 32px;
    height: 32px;
    min-width: 44px;
    min-height: 44px;
    border: none;
    background: transparent;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
  }

  .session-item:hover .session-delete {
    opacity: 1;
  }

  .session-delete:hover {
    background: rgba(219, 68, 55, 0.2);
  }

  .icon {
    width: 16px;
    height: 16px;
    fill: var(--secondary-text-color);
  }

  .session-delete:hover .icon {
    fill: var(--error-color);
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateX(-10px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }
</style>
