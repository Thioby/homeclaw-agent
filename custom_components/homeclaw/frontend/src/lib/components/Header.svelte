<script lang="ts">
  import { get } from 'svelte/store';
  import { appState } from '$lib/stores/appState';
  import { sessionState, activeSession } from '$lib/stores/sessions';
  import { toggleSidebar, toggleSettings, cycleTheme, uiState } from '$lib/stores/ui';
  import { deleteSession } from '$lib/services/session.service';
  import { clearAllCaches } from '$lib/services/markdown.service';

  async function clearChat() {
    const currentAppState = get(appState);
    const currentSessionState = get(sessionState);
    
    if (!currentAppState.hass) return;
    if (!currentSessionState.activeSessionId) return;

    if (confirm('Clear this conversation?')) {
      await deleteSession(currentAppState.hass, currentSessionState.activeSessionId);
      clearAllCaches();
    }
  }
</script>

<div class="header">
  <button class="header-btn back-btn" onclick={toggleSidebar} aria-label="Toggle sidebar">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="3" y1="6" x2="21" y2="6"/>
      <line x1="3" y1="12" x2="21" y2="12"/>
      <line x1="3" y1="18" x2="21" y2="18"/>
    </svg>
  </button>

  <div class="header-avatar">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1.07A7.001 7.001 0 0 1 7.07 19H6a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h-1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2zm-3 13a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"/>
    </svg>
  </div>

  <div class="header-info">
    <div class="header-title">{$activeSession?.title || $appState.agentName}</div>
    <div class="header-subtitle">online</div>
  </div>

  <div class="header-actions">
    <button class="header-btn" onclick={cycleTheme} title="Toggle theme ({$uiState.theme})" aria-label="Toggle theme">
      {#if $uiState.theme === 'light'}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
      {:else if $uiState.theme === 'dark'}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      {:else}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
      {/if}
    </button>

    <button class="header-btn" onclick={toggleSettings} aria-label="Settings" title="Settings">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/>
      </svg>
    </button>

    <button
      class="header-btn delete-btn"
      onclick={clearChat}
      disabled={$appState.isLoading}
      title="Clear chat"
      aria-label="Clear chat"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
      </svg>
    </button>
  </div>
</div>

<style>
  .header {
    height: 54px;
    min-height: 54px;
    background: var(--bg-sidebar, var(--secondary-background-color));
    color: var(--primary-text-color);
    border-bottom: 1px solid var(--divider-color);
    display: flex;
    align-items: center;
    padding: 0 8px;
    gap: 8px;
    position: relative;
    z-index: 100;
    transition: background var(--transition-medium, 250ms), border-color var(--transition-medium, 250ms);
  }

  .header-btn {
    width: 40px;
    height: 40px;
    border: none;
    background: transparent;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--secondary-text-color);
    transition: background 0.15s, color 0.15s;
    flex-shrink: 0;
    padding: 0;
  }

  .header-btn:hover {
    background: var(--bg-hover, rgba(0, 0, 0, 0.04));
    color: var(--primary-text-color);
  }

  .header-btn svg {
    width: 22px;
    height: 22px;
  }

  /* Back/hamburger button - hidden on desktop */
  .back-btn {
    display: none;
  }

  .header-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--accent, #2AABEE), var(--accent-hover, #229ED9));
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    flex-shrink: 0;
  }

  .header-avatar svg {
    width: 22px;
    height: 22px;
  }

  .header-info {
    flex: 1;
    min-width: 0;
  }

  .header-title {
    font-size: 15px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.2;
  }

  .header-subtitle {
    font-size: 12.5px;
    color: var(--accent, var(--primary-color));
    line-height: 1.2;
  }

  .header-actions {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }

  .delete-btn:hover {
    color: var(--error-color, #db4437);
  }

  .delete-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  @media (max-width: 768px) {
    .back-btn {
      display: flex;
    }

    .header-avatar {
      width: 36px;
      height: 36px;
    }

    .header-avatar svg {
      width: 18px;
      height: 18px;
    }

    .header-title {
      font-size: 14px;
    }
  }
</style>
