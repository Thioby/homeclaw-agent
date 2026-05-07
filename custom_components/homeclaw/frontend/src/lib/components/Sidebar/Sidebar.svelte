<script lang="ts">
  import { appState } from '$lib/stores/appState';
  import { uiState, closeSidebar, toggleSettings, cycleTheme } from '$lib/stores/ui';
  import { isMobile } from '$lib/utils/dom';
  import { countSmartEntities } from '$lib/utils/entities';
  import SessionList from './SessionList.svelte';
  import NewChatButton from './NewChatButton.svelte';
  import Icon from '../Icon.svelte';

  let searchQuery = $state('');

  const sidebarClass = $derived(
    isMobile()
      ? ($uiState.sidebarOpen ? 'hc-sidebar open' : 'hc-sidebar hidden')
      : ($uiState.sidebarOpen ? 'hc-sidebar' : 'hc-sidebar hidden')
  );

  const showOverlay = $derived($uiState.sidebarOpen && isMobile());

  // Smart entity count (devices/sensors only).
  const entityCount = $derived.by(() => {
    const n = countSmartEntities($appState.hass?.states);
    return n > 0 ? n : null;
  });

  const themeIcon = $derived(
    $uiState.theme === 'dark' ? 'moon' : $uiState.theme === 'light' ? 'sun' : 'refresh'
  );
</script>

<!-- Mobile overlay -->
{#if showOverlay}
  <div class="hc-sidebar-overlay" onclick={closeSidebar}></div>
{/if}

<aside class={sidebarClass}>
  <div class="hc-sidebar-head">
    <div class="hc-mark">
      <Icon name="home" size={16} />
    </div>
    <div class="hc-brand">{$appState.agentName || 'Homeclaw'}</div>
  </div>

  <NewChatButton />

  <div class="hc-search">
    <Icon name="search" size={14} />
    <input bind:value={searchQuery} placeholder="Search conversations" aria-label="Search conversations" />
  </div>

  <div class="hc-sessions">
    <SessionList {searchQuery} />
  </div>

  <div class="hc-sidebar-foot">
    <div class="hc-status-pulse"></div>
    <div class="hc-status-text">
      {$appState.hass ? 'Connected' : 'Disconnected'}
      {#if entityCount}
        <small>{entityCount} entities</small>
      {/if}
    </div>
    <button onclick={cycleTheme} title="Theme: {$uiState.theme}" aria-label="Toggle theme">
      <Icon name={themeIcon} size={15} />
    </button>
    <button onclick={toggleSettings} title="Settings" aria-label="Settings">
      <Icon name="settings" size={15} />
    </button>
  </div>
</aside>

<style>
  .hc-sidebar {
    width: 280px;
    min-width: 280px;
    height: 100%;
    flex-shrink: 0;
    background: var(--hc-bg-2);
    border-right: 1px solid var(--hc-line);
    display: flex;
    flex-direction: column;
    min-height: 0;
    transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    z-index: 10;
  }

  .hc-sidebar.hidden {
    transform: translateX(-100%);
    width: 0;
    min-width: 0;
    border: none;
    overflow: hidden;
  }

  .hc-sidebar-head {
    height: 54px;
    padding: 0 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid var(--hc-line);
    flex-shrink: 0;
  }

  .hc-mark {
    width: 26px;
    height: 26px;
    background: var(--hc-ink);
    color: var(--hc-bg);
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .hc-brand {
    font-family: var(--hc-font-display);
    font-size: 19px;
    font-weight: 500;
    letter-spacing: -0.01em;
    color: var(--hc-ink);
  }

  .hc-search {
    margin: 0 12px 12px;
    padding: 0 10px;
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--hc-card-bg);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius-sm);
  }

  .hc-search :global(svg) {
    color: var(--hc-ink-3);
    flex-shrink: 0;
  }

  .hc-search input {
    flex: 1;
    border: 0;
    background: transparent;
    padding: 8px 0;
    font: inherit;
    font-size: 13.5px;
    color: var(--hc-ink);
    outline: none;
  }

  .hc-search input::placeholder {
    color: var(--hc-ink-3);
  }

  .hc-sessions {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 0 8px 8px;
    min-height: 0;
  }

  .hc-sessions::-webkit-scrollbar {
    width: 6px;
  }
  .hc-sessions::-webkit-scrollbar-track {
    background: transparent;
  }
  .hc-sessions::-webkit-scrollbar-thumb {
    background-color: var(--hc-line-strong);
    border-radius: 3px;
  }

  .hc-sidebar-foot {
    padding: 12px 14px;
    border-top: 1px solid var(--hc-line);
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .hc-status-pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--hc-good);
    box-shadow: 0 0 0 4px color-mix(in oklab, var(--hc-good) 25%, transparent);
    flex-shrink: 0;
  }

  .hc-status-text {
    flex: 1;
    font-size: 12.5px;
    line-height: 1.3;
    color: var(--hc-ink);
    min-width: 0;
  }

  .hc-status-text small {
    display: block;
    color: var(--hc-ink-3);
    font-size: 11px;
  }

  .hc-sidebar-foot button {
    width: 28px;
    height: 28px;
    background: transparent;
    border: 0;
    color: var(--hc-ink-3);
    border-radius: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    flex-shrink: 0;
  }

  .hc-sidebar-foot button:hover {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink);
  }

  .hc-sidebar-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(20, 16, 10, 0.32);
    backdrop-filter: blur(2px);
    z-index: 99;
  }

  @media (max-width: 768px) {
    .hc-sidebar {
      position: fixed;
      left: 0;
      top: 0;
      bottom: 0;
      z-index: 100;
      transform: translateX(-100%);
      width: 85vw;
      min-width: 85vw;
      max-width: 320px;
      box-shadow: none;
    }

    .hc-sidebar.open {
      transform: translateX(0);
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.16);
    }

    .hc-sidebar.hidden {
      transform: translateX(-100%);
    }

    .hc-sidebar-overlay {
      display: block;
    }
  }
</style>
