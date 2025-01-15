<script lang="ts">
  import { get } from 'svelte/store';
  import { appState } from '$lib/stores/appState';
  import { sessionState } from '$lib/stores/sessions';
  import { toggleSidebar, toggleSettings } from '$lib/stores/ui';
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
  <button class="menu-toggle" onclick={toggleSidebar} aria-label="Toggle sidebar">
    <svg viewBox="0 0 24 24" class="icon">
      <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
    </svg>
  </button>
  
  <svg viewBox="0 0 24 24" class="robot-icon">
    <path d="M12 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm6 16.5V22h-3v-3.5h3zM5.5 22h3v-3.5h-3V22zM19 9h-1.5V7.5c0-1.93-1.57-3.5-3.5-3.5S10.5 5.57 10.5 7.5V9H9c-.55 0-1 .45-1 1v9c0 .55.45 1 1 1h10c.55 0 1-.45 1-1v-9c0-.55-.45-1-1-1zm-7.5-1.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5V9h-3V7.5z"/>
  </svg>
  
  <span class="title">Homeclaw</span>

  <button
    class="settings-button"
    onclick={toggleSettings}
    aria-label="Settings"
    title="Settings"
  >
    <svg viewBox="0 0 24 24" class="icon">
      <path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
    </svg>
  </button>

  <button
    class="clear-button"
    onclick={clearChat}
    disabled={$appState.isLoading}
  >
    <svg viewBox="0 0 24 24" class="icon">
      <path d="M15 16h4v2h-4zm0-8h7v2h-7zm0 4h6v2h-6zM3 18c0 1.1.9 2 2 2h6c1.1 0 2-.9 2-2V8H3v10zM14 5h-3l-1-1H6L5 5H2v2h12z"/>
    </svg>
    <span>Clear Chat</span>
  </button>
</div>

<style>
  .header {
    background: var(--app-header-background-color, var(--secondary-background-color));
    color: var(--app-header-text-color, var(--primary-text-color));
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 20px;
    font-weight: 500;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    position: relative;
    z-index: 100;
  }

  .menu-toggle {
    display: none;
    width: 44px;
    height: 44px;
    min-width: 44px;
    min-height: 44px;
    border: none;
    background: transparent;
    cursor: pointer;
    border-radius: 50%;
    align-items: center;
    justify-content: center;
    margin-right: 8px;
    padding: 0;
  }

  .menu-toggle:hover {
    background: var(--card-background-color);
  }

  .icon {
    width: 24px;
    height: 24px;
    fill: currentColor;
  }

  .robot-icon {
    width: 24px;
    height: 24px;
    fill: var(--primary-color);
  }

  .title {
    flex: 1;
  }

  .settings-button {
    width: 36px;
    height: 36px;
    border: none;
    background: transparent;
    cursor: pointer;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
    flex-shrink: 0;
    margin-left: auto;
  }

  .settings-button:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  .settings-button .icon {
    width: 20px;
    height: 20px;
    fill: currentColor;
    opacity: 0.8;
  }

  .settings-button:hover .icon {
    opacity: 1;
  }

  .clear-button {
    border: none;
    border-radius: 16px;
    background: var(--error-color);
    color: #fff;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
    min-width: unset;
    width: auto;
    height: 36px;
    flex-shrink: 0;
    font-family: inherit;
  }

  .clear-button .icon {
    width: 16px;
    height: 16px;
    margin-right: 2px;
    fill: white;
  }

  .clear-button span {
    color: #fff;
    font-weight: 500;
  }

  .clear-button:hover:not(:disabled) {
    opacity: 0.92;
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.13);
  }

  .clear-button:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
  }

  .clear-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  @media (max-width: 768px) {
    .menu-toggle {
      display: flex;
    }

    .robot-icon {
      display: none;
    }
  }
</style>
