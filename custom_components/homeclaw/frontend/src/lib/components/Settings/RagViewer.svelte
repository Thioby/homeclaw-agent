<script lang="ts">
  import type { RagStats } from './Rag/types';
  import { getHass } from './Rag/rag-helpers';
  import RagOverview from './Rag/RagOverview.svelte';
  import RagMemories from './Rag/RagMemories.svelte';
  import RagSessions from './Rag/RagSessions.svelte';
  import RagSearch from './Rag/RagSearch.svelte';
  import RagOptimize from './Rag/RagOptimize.svelte';

  type Section = 'overview' | 'memories' | 'sessions' | 'search' | 'optimize';

  let activeSection = $state<Section>('overview');
  let loading = $state(false);
  let stats = $state<RagStats | null>(null);

  // Messages
  let message = $state<string | null>(null);
  let messageType = $state<'success' | 'error'>('success');

  // Load stats on mount
  $effect(() => {
    loadStats();
  });

  async function loadStats() {
    const hass = getHass();
    if (!hass) return;
    loading = true;
    try {
      stats = await hass.callWS({ type: 'homeclaw/rag/stats' });
    } catch (e) {
      console.error('[RagViewer] Failed to load stats:', e);
      stats = { initialized: false };
    } finally {
      loading = false;
    }
  }

  function showMessage(text: string, type: 'success' | 'error') {
    message = text;
    messageType = type;
    setTimeout(() => (message = null), 3000);
  }

  function handleSectionChange(section: Section) {
    activeSection = section;
  }
</script>

<div class="rag-viewer">
  {#if message}
    <div class="msg" class:error={messageType === 'error'}>{message}</div>
  {/if}

  <!-- Section nav -->
  <div class="section-nav">
    <button
      class="pill"
      class:active={activeSection === 'overview'}
      onclick={() => handleSectionChange('overview')}>Overview</button
    >
    <button
      class="pill"
      class:active={activeSection === 'memories'}
      onclick={() => handleSectionChange('memories')}>Memories</button
    >
    <button
      class="pill"
      class:active={activeSection === 'sessions'}
      onclick={() => handleSectionChange('sessions')}>Sessions</button
    >
    <button
      class="pill"
      class:active={activeSection === 'search'}
      onclick={() => handleSectionChange('search')}>Search</button
    >
    <button
      class="pill optimize-pill"
      class:active={activeSection === 'optimize'}
      onclick={() => handleSectionChange('optimize')}>Optimize</button
    >
  </div>

  {#if loading && !stats}
    <div class="loading">Loading RAG data...</div>
  {:else if stats && !stats.initialized}
    <div class="not-initialized">
      RAG system is not initialized. Enable it in the integration config.
    </div>
  {:else if activeSection === 'overview' && stats}
    <RagOverview {stats} onRefresh={loadStats} onMessage={showMessage} />
  {:else if activeSection === 'memories'}
    <RagMemories onMessage={showMessage} />
  {:else if activeSection === 'sessions'}
    <RagSessions />
  {:else if activeSection === 'search'}
    <RagSearch />
  {:else if activeSection === 'optimize'}
    <RagOptimize onMessage={showMessage} />
  {/if}
</div>

<style>
  .rag-viewer {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .msg {
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    background: rgba(76, 175, 80, 0.1);
    color: #4caf50;
    border: 1px solid rgba(76, 175, 80, 0.3);
  }
  .msg.error {
    background: rgba(244, 67, 54, 0.1);
    color: var(--error-color);
    border-color: rgba(244, 67, 54, 0.3);
  }
  .loading,
  .not-initialized {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
  }
  .section-nav {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .pill {
    padding: 6px 14px;
    border: 1px solid var(--divider-color);
    border-radius: 20px;
    background: var(--secondary-background-color);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
    color: var(--primary-text-color);
  }
  .pill.active {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
  }
  .pill:hover:not(.active) {
    background: var(--card-background-color);
  }
  .pill.optimize-pill {
    border-color: rgba(255, 152, 0, 0.4);
  }
  .pill.optimize-pill.active {
    background: #ff9800;
    border-color: #ff9800;
  }
</style>
