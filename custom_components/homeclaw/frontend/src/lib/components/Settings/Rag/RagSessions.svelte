<script lang="ts">
  import type { SessionChunk } from './types';
  import { getHass } from './rag-helpers';

  let chunks = $state<SessionChunk[]>([]);
  let chunksLoaded = $state(false);
  let loading = $state(false);

  // Load on mount
  $effect(() => {
    if (!chunksLoaded) loadChunks();
  });

  async function loadChunks() {
    const hass = getHass();
    if (!hass) return;
    loading = true;
    try {
      const result = await hass.callWS({
        type: 'homeclaw/rag/sessions',
        limit: 100,
      });
      chunks = result.chunks || [];
      chunksLoaded = true;
    } catch (e) {
      console.error('[RagViewer] Failed to load chunks:', e);
    } finally {
      loading = false;
    }
  }
</script>

<div class="section">
  <div class="toolbar">
    <span class="count">{chunks.length} chunks</span>
    <button class="btn text" onclick={loadChunks}>Refresh</button>
  </div>

  {#if loading && !chunksLoaded}
    <div class="empty">Loading session chunks...</div>
  {:else if chunks.length === 0}
    <div class="empty">No session chunks indexed.</div>
  {:else}
    {#each chunks as chunk (chunk.id)}
      <div class="chunk-card">
        <div class="chunk-header">
          <span class="badge">session: {chunk.session_id.substring(0, 8)}...</span>
          <span class="chunk-range">msgs {chunk.start_msg}-{chunk.end_msg}</span>
          <span class="chunk-len">{chunk.text_length} chars</span>
        </div>
        <pre class="chunk-text">{chunk.text}</pre>
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
  .btn {
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }
  .btn.text {
    background: none;
    color: var(--primary-color);
    padding: 6px 8px;
  }
  .btn.text:hover {
    background: rgba(3, 169, 244, 0.08);
  }
  .chunk-card {
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 10px 14px;
  }
  .chunk-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 12px;
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
  .chunk-range {
    color: var(--secondary-text-color);
  }
  .chunk-len {
    color: var(--secondary-text-color);
    margin-left: auto;
  }
  .chunk-text {
    font-size: 12px;
    line-height: 1.5;
    color: var(--primary-text-color);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
    margin: 0;
    background: var(--primary-background-color);
    padding: 8px;
    border-radius: 6px;
  }
</style>
