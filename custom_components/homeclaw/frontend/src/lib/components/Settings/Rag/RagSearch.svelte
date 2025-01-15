<script lang="ts">
  import { getHass } from './rag-helpers';

  let searchQuery = $state('');
  let searchResult = $state<string | null>(null);
  let searchLength = $state(0);
  let searching = $state(false);

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    const hass = getHass();
    if (!hass) return;
    searching = true;
    searchResult = null;
    try {
      const result = await hass.callWS({
        type: 'homeclaw/rag/search',
        query: searchQuery,
        top_k: 5,
      });
      searchResult = result.context || '(no results)';
      searchLength = result.context_length || 0;
    } catch (e: any) {
      searchResult = `Error: ${e?.message || 'search failed'}`;
      searchLength = 0;
    } finally {
      searching = false;
    }
  }
</script>

<div class="section">
  <p class="desc">Test what RAG context would be generated for a given query.</p>
  <div class="search-row">
    <input
      class="search-input"
      placeholder="Enter a query..."
      bind:value={searchQuery}
      onkeydown={(e) => e.key === 'Enter' && handleSearch()}
    />
    <button
      class="btn primary"
      onclick={handleSearch}
      disabled={searching || !searchQuery.trim()}
    >
      {searching ? '...' : 'Search'}
    </button>
  </div>

  {#if searchResult !== null}
    <div class="search-result">
      <div class="search-meta">{searchLength} chars of context</div>
      <pre class="search-text">{searchResult}</pre>
    </div>
  {/if}
</div>

<style>
  .section {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .desc {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }
  .search-row {
    display: flex;
    gap: 8px;
  }
  .search-input {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    font-size: 14px;
    color: var(--primary-text-color);
    background: var(--secondary-background-color);
    font-family: inherit;
  }
  .search-input:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
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
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .btn.primary {
    background: var(--primary-color);
    color: white;
  }
  .btn.primary:hover:not(:disabled) {
    filter: brightness(1.1);
  }
  .search-result {
    margin-top: 8px;
  }
  .search-meta {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin-bottom: 6px;
  }
  .search-text {
    font-size: 12px;
    line-height: 1.5;
    color: var(--primary-text-color);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 400px;
    overflow-y: auto;
    margin: 0;
    background: var(--secondary-background-color);
    padding: 12px;
    border-radius: 8px;
  }
</style>
