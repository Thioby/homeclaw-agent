<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import type { HomeAssistant } from '../types';
  import { appState } from '$lib/stores/appState';
  import { syncThemeFromPreferences, uiState } from '$lib/stores/ui';
  import { loadProviders } from '../services/provider.service';
  import { loadSessions, startNewChat } from '../services/session.service';

  // Components
  import Topbar from './Topbar.svelte';
  import Sidebar from './Sidebar/Sidebar.svelte';
  import ChatArea from './Chat/ChatArea.svelte';
  import InputArea from './Input/InputArea.svelte';
  import SettingsPanel from './Settings/SettingsPanel.svelte';
  import ConfirmDialog from './ConfirmDialog.svelte';

  // Props
  let { hass, narrow = false }: { hass: HomeAssistant; narrow?: boolean; panel?: boolean } = $props();

  async function loadIdentity(ha: HomeAssistant) {
    try {
      const result = await ha.callWS({ type: 'homeclaw/rag/identity' });
      const identity = result?.identity;
      if (identity) {
        appState.update(s => ({
          ...s,
          agentName: identity.agent_name || 'Homeclaw',
          agentEmoji: identity.agent_emoji || '',
          userName: identity.user_name || '',
        }));
      }
    } catch {
      // Non-critical — keep defaults
    }
  }

  // Update appState when hass changes
  $effect(() => {
    appState.update(s => ({ ...s, hass }));
  });

  // Lifecycle - Initialize
  onMount(() => {
    console.log('[HomeclawPanel] Mounting...');

    (async () => {
      try {
        await Promise.all([
          loadProviders(hass),
          loadIdentity(hass),
          syncThemeFromPreferences(hass),
        ]);
        await loadSessions(hass);
        console.log('[HomeclawPanel] Initialization complete');
      } catch (error) {
        console.error('[HomeclawPanel] Initialization error:', error);
        appState.update(s => ({
          ...s,
          error: error instanceof Error ? error.message : 'Failed to initialize',
        }));
      }
    })();

    const handleResize = () => {
      const isMobileNow = window.innerWidth <= 768;
      const currentUiState = get(uiState);
      if (!isMobileNow && currentUiState.sidebarOpen) {
        // Keep sidebar open on desktop
      }
    };
    window.addEventListener('resize', handleResize);
    handleResize();

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  });

  const isMobile = $derived(narrow || window.innerWidth <= 768);

  function handleShortcut(e: KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 't') {
      const ha = get(appState).hass;
      if (!ha) return;
      e.preventDefault();
      startNewChat(ha);
    }
  }
</script>

<svelte:window onkeydown={handleShortcut} />

<div class="hc-app" class:narrow={isMobile}>
  <Sidebar />

  <div class="hc-main">
    <Topbar />

    <div class="hc-chat-region">
      <ChatArea {hass} />
    </div>

    <InputArea />
  </div>

  <SettingsPanel />
  <ConfirmDialog />
</div>

<style>
  .hc-app {
    display: flex;
    width: 100%;
    height: 100vh;
    min-height: 0;
    overflow: hidden;
    background: var(--hc-bg);
    color: var(--hc-ink);
    font-family: var(--hc-font-sans);
    font-size: 14px;
    line-height: 1.5;
  }

  .hc-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: var(--hc-bg);
    transition: background var(--transition-medium, 250ms ease-in-out);
  }

  .hc-chat-region {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
  }

  /* Override the legacy chat background — let the paper-tone hc-bg show through. */
  .hc-app :global(.messages) {
    background: var(--hc-bg) !important;
  }

  .hc-app :global(.messages::before) {
    /* Drop the legacy svg pattern overlay; it clashes with paper-tone bg. */
    display: none !important;
  }

  /* Widen the chat column to match the redesign target (760px). */
  .hc-app :global(.messages-inner) {
    max-width: 760px !important;
    padding: 28px 28px 16px !important;
  }

  @media (max-width: 768px) {
    .hc-app :global(.messages-inner) {
      padding: 16px 16px 12px !important;
    }
  }

  @media (max-width: 768px) {
    .hc-app {
      height: 100vh;
      height: 100dvh;
    }
  }
</style>
