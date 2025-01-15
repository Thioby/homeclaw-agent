<script lang="ts">
  import { uiState, closeSettings } from '$lib/stores/ui';
  import ModelsEditor from './ModelsEditor.svelte';
  import DefaultsEditor from './DefaultsEditor.svelte';
  import RagViewer from './RagViewer.svelte';

  let activeTab = $state<'defaults' | 'models' | 'rag'>('defaults');
</script>

{#if $uiState.settingsOpen}
  <!-- Backdrop -->
  <div class="settings-backdrop" onclick={closeSettings}></div>

  <!-- Panel -->
  <div class="settings-panel">
    <div class="settings-header">
      <h2>Settings</h2>
      <button class="close-btn" onclick={closeSettings} aria-label="Close settings">
        <svg viewBox="0 0 24 24" class="icon">
          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
        </svg>
      </button>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        class="tab"
        class:active={activeTab === 'defaults'}
        onclick={() => (activeTab = 'defaults')}
      >
        Defaults
      </button>
      <button
        class="tab"
        class:active={activeTab === 'models'}
        onclick={() => (activeTab = 'models')}
      >
        Models
      </button>
      <button
        class="tab"
        class:active={activeTab === 'rag'}
        onclick={() => (activeTab = 'rag')}
      >
        RAG
      </button>
    </div>

    <!-- Tab content -->
    <div class="settings-content">
      {#if activeTab === 'defaults'}
        <DefaultsEditor />
      {:else if activeTab === 'models'}
        <ModelsEditor />
      {:else if activeTab === 'rag'}
        <RagViewer />
      {/if}
    </div>
  </div>
{/if}

<style>
  .settings-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 200;
  }

  .settings-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(480px, 100vw);
    background: var(--primary-background-color);
    z-index: 201;
    display: flex;
    flex-direction: column;
    box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
    animation: slideIn 0.2s ease-out;
  }

  @keyframes slideIn {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }

  .settings-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--divider-color);
  }

  .settings-header h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--primary-text-color);
  }

  .close-btn {
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
  }

  .close-btn:hover {
    background: var(--secondary-background-color);
  }

  .icon {
    width: 20px;
    height: 20px;
    fill: var(--secondary-text-color);
  }

  .tabs {
    display: flex;
    border-bottom: 1px solid var(--divider-color);
    padding: 0 20px;
  }

  .tab {
    padding: 10px 16px;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: var(--secondary-text-color);
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
    font-family: inherit;
  }

  .tab.active {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }

  .tab:hover:not(.active) {
    color: var(--primary-text-color);
    background: var(--secondary-background-color);
  }

  .settings-content {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
  }

  @media (max-width: 768px) {
    .settings-panel {
      width: 100vw;
    }
  }
</style>
