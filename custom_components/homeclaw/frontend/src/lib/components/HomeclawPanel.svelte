<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import type { HomeAssistant } from '../types';
  import { appState } from '$lib/stores/appState';
  import { syncThemeFromPreferences, uiState } from '$lib/stores/ui';
  import { loadProviders } from '../services/provider.service';
  import { loadSessions } from '../services/session.service';
  
  // Components
  import Header from './Header.svelte';
  import Sidebar from './Sidebar/Sidebar.svelte';
  import ChatArea from './Chat/ChatArea.svelte';
  import InputArea from './Input/InputArea.svelte';
  import ThinkingPanel from './Debug/ThinkingPanel.svelte';
  import SettingsPanel from './Settings/SettingsPanel.svelte';

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
    
    // Load providers, sessions, and identity in parallel
    (async () => {
      try {
        await Promise.all([
          loadProviders(hass),
          loadSessions(hass),
          loadIdentity(hass),
          syncThemeFromPreferences(hass),
        ]);
        console.log('[HomeclawPanel] Initialization complete');
      } catch (error) {
        console.error('[HomeclawPanel] Initialization error:', error);
        appState.update(s => ({ 
          ...s, 
          error: error instanceof Error ? error.message : 'Failed to initialize' 
        }));
      }
    })();

    // Window resize handler for mobile detection
    const handleResize = () => {
      const isMobile = window.innerWidth <= 768;
      const currentUiState = get(uiState);
      if (!isMobile && currentUiState.sidebarOpen) {
        // Keep sidebar open on desktop
      }
    };
    window.addEventListener('resize', handleResize);
    handleResize(); // Initial check

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  });

  // Computed values
  const isMobile = $derived(narrow || window.innerWidth <= 768);
  const showThinkingPanel = $derived($appState.showThinking && $appState.debugInfo?.length > 0);
</script>

<div class="homeclaw-panel" class:narrow={isMobile}>
  <Header />
  
  <div class="main-container">
    <Sidebar />
    
    <div class="content-area">
      <div class="chat-container">
        <ChatArea />
        
        {#if showThinkingPanel}
          <ThinkingPanel />
        {/if}
      </div>
      
      <InputArea />
    </div>
  </div>

  <SettingsPanel />
</div>

<style>
  .homeclaw-panel {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100vh;
    overflow: hidden;
    background-color: var(--primary-background-color);
  }

  .main-container {
    display: flex;
    flex: 1;
    overflow: hidden;
    position: relative;
  }

  .content-area {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
    position: relative;
    background: var(--bg-chat, var(--primary-background-color));
    transition: background var(--transition-medium, 250ms ease-in-out);
  }

  .chat-container {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
    position: relative;
  }

  /* Mobile adjustments */
  .homeclaw-panel.narrow .content-area {
    width: 100%;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .homeclaw-panel {
      height: 100vh;
      height: 100dvh; /* Dynamic viewport height for mobile */
    }
  }

  /* Animation */
  .content-area {
    animation: fadeIn 0.3s ease-in-out;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
</style>
