<script lang="ts">
  import type { MemoryItem } from './types';
  import { getHass, formatTimestamp, formatExpiresAt } from './rag-helpers';

  let {
    onMessage,
  }: {
    onMessage: (text: string, type: 'success' | 'error') => void;
  } = $props();

  let memories = $state<MemoryItem[]>([]);
  let memoriesLoaded = $state(false);
  let loading = $state(false);
  let categoryFilter = $state<string>('');
  let sourceFilter = $state<string>('');
  let filteredMemories = $derived(
    sourceFilter ? memories.filter((m) => m.source === sourceFilter) : memories
  );

  // Load on mount
  $effect(() => {
    if (!memoriesLoaded) loadMemories();
  });

  async function loadMemories() {
    const hass = getHass();
    if (!hass) return;
    loading = true;
    try {
      const result = await hass.callWS({
        type: 'homeclaw/rag/memories',
        limit: 100,
        ...(categoryFilter ? { category: categoryFilter } : {}),
      });
      memories = result.memories || [];
      memoriesLoaded = true;
    } catch (e) {
      console.error('[RagViewer] Failed to load memories:', e);
    } finally {
      loading = false;
    }
  }

  async function deleteMemory(id: string) {
    const hass = getHass();
    if (!hass) return;
    try {
      await hass.callWS({ type: 'homeclaw/rag/memory/delete', memory_id: id });
      memories = memories.filter((m) => m.id !== id);
      onMessage('Memory deleted', 'success');
    } catch (e: any) {
      onMessage(e?.message || 'Failed to delete', 'error');
    }
  }
</script>

<div class="section">
  <div class="toolbar">
    <select class="filter-select" bind:value={categoryFilter} onchange={loadMemories}>
      <option value="">All categories</option>
      <option value="fact">fact</option>
      <option value="preference">preference</option>
      <option value="decision">decision</option>
      <option value="entity">entity</option>
      <option value="observation">observation</option>
      <option value="other">other</option>
    </select>
    <select class="filter-select" bind:value={sourceFilter}>
      <option value="">All sources</option>
      <option value="agent">agent (proactive)</option>
      <option value="auto">auto-captured</option>
      <option value="user">user/tool</option>
    </select>
    <span class="count">{filteredMemories.length} memories</span>
  </div>

  {#if loading && !memoriesLoaded}
    <div class="empty">Loading memories...</div>
  {:else if filteredMemories.length === 0}
    <div class="empty">No memories found.</div>
  {:else}
    {#each filteredMemories as mem (mem.id)}
      <div
        class="memory-card"
        class:expiring={mem.expires_at && mem.expires_at - Date.now() / 1000 < 86400}
      >
        <div class="memory-header">
          <span class="badge cat-{mem.category}">{mem.category}</span>
          {#if mem.expires_at}
            <span class="badge ttl-badge">{formatExpiresAt(mem.expires_at)}</span>
          {/if}
          <span class="importance" title="Importance">{mem.importance}</span>
          <span class="source">{mem.source}</span>
          <button class="del-btn" onclick={() => deleteMemory(mem.id)} title="Delete memory"
            >x</button
          >
        </div>
        <div class="memory-text">{mem.text}</div>
        <div class="memory-meta">
          {formatTimestamp(mem.created_at)}
        </div>
      </div>
    {/each}
  {/if}
</div>

<style>
  .section {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .filter-select {
    padding: 6px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 6px;
    font-size: 13px;
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    font-family: inherit;
  }
  .count {
    font-size: 12px;
    color: var(--secondary-text-color);
  }
  .empty {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
  }
  .memory-card {
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 10px 14px;
  }
  .memory-card.expiring {
    opacity: 0.7;
    border-left: 3px solid #ff9800;
  }
  .memory-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .badge {
    display: inline-flex;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 500;
    background: var(--divider-color);
    color: var(--primary-text-color);
  }
  .badge.cat-fact {
    background: rgba(33, 150, 243, 0.15);
    color: #2196f3;
  }
  .badge.cat-preference {
    background: rgba(156, 39, 176, 0.15);
    color: #9c27b0;
  }
  .badge.cat-decision {
    background: rgba(255, 152, 0, 0.15);
    color: #ff9800;
  }
  .badge.cat-entity {
    background: rgba(0, 150, 136, 0.15);
    color: #009688;
  }
  .badge.cat-observation {
    background: rgba(121, 85, 72, 0.15);
    color: #795548;
  }
  .badge.ttl-badge {
    background: rgba(255, 152, 0, 0.12);
    color: #ff9800;
    font-size: 10px;
  }
  .importance {
    font-size: 11px;
    color: var(--secondary-text-color);
  }
  .source {
    font-size: 11px;
    color: var(--secondary-text-color);
    margin-left: auto;
  }
  .del-btn {
    width: 22px;
    height: 22px;
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 14px;
    color: var(--secondary-text-color);
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .del-btn:hover {
    background: rgba(244, 67, 54, 0.1);
    color: var(--error-color);
  }
  .memory-text {
    font-size: 13px;
    color: var(--primary-text-color);
    line-height: 1.5;
    word-break: break-word;
  }
  .memory-meta {
    font-size: 11px;
    color: var(--secondary-text-color);
    margin-top: 4px;
  }
</style>
