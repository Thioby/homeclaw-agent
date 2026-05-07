<script lang="ts">
  import { uiState, closeSettings } from '$lib/stores/ui';
  import Icon from '../Icon.svelte';
  import AppearanceEditor from './AppearanceEditor.svelte';
  import ModelsEditor from './ModelsEditor.svelte';
  import DefaultsEditor from './DefaultsEditor.svelte';
  import RagViewer from './RagViewer.svelte';
  import SchedulerPanel from './SchedulerPanel.svelte';

  type Tab = 'appearance' | 'defaults' | 'models' | 'rag' | 'scheduler';
  let activeTab = $state<Tab>('appearance');

  const tabs: Array<{ id: Tab; label: string }> = [
    { id: 'appearance', label: 'Appearance' },
    { id: 'defaults', label: 'Defaults' },
    { id: 'models', label: 'Models' },
    { id: 'rag', label: 'RAG' },
    { id: 'scheduler', label: 'Scheduler' },
  ];
</script>

{#if $uiState.settingsOpen}
  <div class="hc-drawer-scrim" onclick={closeSettings} role="presentation"></div>

  <div class="hc-drawer">
    <div class="hc-drawer-head">
      <h2>Settings</h2>
      <button class="hc-drawer-close" onclick={closeSettings} aria-label="Close settings">
        <Icon name="x" size={16} />
      </button>
    </div>

    <div class="hc-drawer-tabs">
      {#each tabs as t}
        <button
          class="hc-drawer-tab"
          class:active={activeTab === t.id}
          onclick={() => (activeTab = t.id)}
        >
          {t.label}
        </button>
      {/each}
    </div>

    <div class="hc-drawer-body">
      {#if activeTab === 'appearance'}
        <AppearanceEditor />
      {:else if activeTab === 'defaults'}
        <DefaultsEditor />
      {:else if activeTab === 'models'}
        <ModelsEditor />
      {:else if activeTab === 'rag'}
        <RagViewer />
      {:else if activeTab === 'scheduler'}
        <SchedulerPanel />
      {/if}
    </div>
  </div>
{/if}

<style>
  .hc-drawer-scrim {
    position: fixed;
    inset: 0;
    background: rgba(20, 16, 10, 0.32);
    backdrop-filter: blur(2px);
    z-index: 50;
    animation: scrimFadeIn 0.18s ease-out;
  }

  @keyframes scrimFadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  .hc-drawer {
    position: fixed;
    right: 0;
    top: 0;
    bottom: 0;
    width: min(520px, 100vw);
    background: var(--hc-bg);
    border-left: 1px solid var(--hc-line);
    z-index: 51;
    display: flex;
    flex-direction: column;
    color: var(--hc-ink);
    animation: drawerSlideIn 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  }

  @keyframes drawerSlideIn {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
  }

  .hc-drawer-head {
    height: 60px;
    padding: 0 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--hc-line);
    flex-shrink: 0;
  }

  .hc-drawer-head h2 {
    font-family: var(--hc-font-display);
    font-size: 22px;
    font-weight: 500;
    margin: 0;
    letter-spacing: -0.01em;
    color: var(--hc-ink);
  }

  .hc-drawer-close {
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

  .hc-drawer-close:hover {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink);
  }

  .hc-drawer-tabs {
    display: flex;
    border-bottom: 1px solid var(--hc-line);
    padding: 0 16px;
    overflow-x: auto;
    flex-shrink: 0;
  }

  .hc-drawer-tabs::-webkit-scrollbar {
    height: 0;
  }

  .hc-drawer-tab {
    padding: 12px 14px;
    border: 0;
    background: transparent;
    cursor: pointer;
    font: inherit;
    font-size: 13px;
    font-weight: 500;
    color: var(--hc-ink-3);
    border-bottom: 2px solid transparent;
    transition: color 0.12s, border-color 0.12s;
    white-space: nowrap;
  }

  .hc-drawer-tab:hover {
    color: var(--hc-ink);
  }

  .hc-drawer-tab.active {
    color: var(--hc-ink);
    border-bottom-color: var(--hc-ink);
  }

  .hc-drawer-body {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }

  /* Override legacy backgrounds inside settings sub-panels so they pick up
     paper-tone hc tokens. Sub-panel internals stay as-is. */
  .hc-drawer-body :global(.tab-content),
  .hc-drawer-body :global(.editor-section),
  .hc-drawer-body :global(.section) {
    background: transparent !important;
  }

  @media (max-width: 768px) {
    .hc-drawer {
      width: 100vw;
    }
    .hc-drawer-head {
      padding: 0 16px;
    }
    .hc-drawer-body {
      padding: 16px;
    }
  }
</style>
