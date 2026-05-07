<script lang="ts">
  import { appState } from '$lib/stores/appState';
  import { activeSession } from '$lib/stores/sessions';
  import { providerState } from '$lib/stores/providers';
  import { toggleSidebar, toggleSettings, cycleTheme, uiState } from '$lib/stores/ui';
  import { countSmartEntities } from '$lib/utils/entities';
  import Icon from './Icon.svelte';

  // Count only "smart" entities — devices and sensors a user thinks about,
  // not bookkeeping (automations, scripts, groups, sun, weather, etc.).
  const entityCount = $derived.by(() => {
    const n = countSmartEntities($appState.hass?.states);
    return n > 0 ? n : null;
  });

  const themeIcon = $derived(
    $uiState.theme === 'dark' ? 'moon' : $uiState.theme === 'light' ? 'sun' : 'refresh'
  );
</script>

<div class="hc-topbar">
  <button class="hc-topbar-mobile" onclick={toggleSidebar} aria-label="Toggle sidebar" title="Sessions">
    <Icon name="menu" />
  </button>

  <div class="hc-topbar-title">
    {$activeSession?.title || $appState.agentName}
  </div>

  <div class="hc-topbar-meta">
    {#if $providerState.selectedModel}
      <b>{$providerState.selectedModel}</b>
    {/if}
    {#if $providerState.selectedModel && entityCount}<span>·</span>{/if}
    {#if entityCount}
      <span>{entityCount} entities</span>
    {/if}
  </div>

  <div class="hc-topbar-actions">
    <button onclick={cycleTheme} title="Theme: {$uiState.theme}" aria-label="Toggle theme">
      <Icon name={themeIcon} />
    </button>
    <button onclick={toggleSettings} aria-label="Settings" title="Settings">
      <Icon name="settings" />
    </button>
  </div>
</div>

<style>
  .hc-topbar {
    height: 54px;
    padding: 0 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    border-bottom: 1px solid var(--hc-line);
    background: var(--hc-bg);
    flex-shrink: 0;
  }

  .hc-topbar-mobile {
    display: none;
    width: 32px;
    height: 32px;
    background: transparent;
    border: 0;
    color: var(--hc-ink-3);
    border-radius: 8px;
    cursor: pointer;
    align-items: center;
    justify-content: center;
    padding: 0;
  }

  .hc-topbar-mobile:hover {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink);
  }

  .hc-topbar-title {
    font-family: var(--hc-font-display);
    font-size: 18px;
    font-weight: 500;
    letter-spacing: -0.01em;
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--hc-ink);
  }

  .hc-topbar-meta {
    display: flex;
    align-items: center;
    gap: 7px;
    font-family: var(--hc-font-mono);
    font-size: 11.5px;
    color: var(--hc-ink-3);
  }

  .hc-topbar-meta b {
    color: var(--hc-ink-2);
    font-weight: 500;
  }

  .hc-topbar-actions {
    display: flex;
    gap: 4px;
  }

  .hc-topbar-actions button {
    width: 32px;
    height: 32px;
    background: transparent;
    border: 0;
    color: var(--hc-ink-3);
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
  }

  .hc-topbar-actions button:hover {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink);
  }

  @media (max-width: 768px) {
    .hc-topbar {
      padding: 0 12px;
    }
    .hc-topbar-mobile {
      display: flex;
    }
    .hc-topbar-meta {
      display: none;
    }
  }
</style>
