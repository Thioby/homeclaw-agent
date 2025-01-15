<script lang="ts">
  import { appState } from "$lib/stores/appState"

  function toggleExpanded() {
    appState.update(s => ({ ...s, thinkingExpanded: !s.thinkingExpanded }));
  }

  const subtitle = $derived(() => {
    if (!$appState.debugInfo) return '';
    
    const parts: string[] = [];
    if ($appState.debugInfo.provider) parts.push($appState.debugInfo.provider);
    if ($appState.debugInfo.model) parts.push($appState.debugInfo.model);
    if ($appState.debugInfo.endpoint_type) parts.push($appState.debugInfo.endpoint_type);
    
    return parts.join(' · ');
  });

  const conversation = $derived($appState.debugInfo?.conversation || []);
</script>

{#if $appState.showThinking && $appState.debugInfo}
  <div class="thinking-panel">
    <div class="thinking-header" onclick={toggleExpanded} role="button" tabindex="0">
      <div>
        <span class="thinking-title">Thinking trace</span>
        {#if subtitle()}
          <span class="thinking-subtitle">{subtitle()}</span>
        {/if}
      </div>
      <svg viewBox="0 0 24 24" class="icon">
        {#if $appState.thinkingExpanded}
          <path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"/>
        {:else}
          <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
        {/if}
      </svg>
    </div>
    
    {#if $appState.thinkingExpanded}
      <div class="thinking-body">
        {#if conversation.length === 0}
          <div class="thinking-empty">No trace captured.</div>
        {:else}
          {#each conversation as entry}
            <div class="thinking-entry">
              <div class="badge">{entry.role || 'unknown'}</div>
              <pre>{entry.content || ''}</pre>
            </div>
          {/each}
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .thinking-panel {
    border: 1px dashed var(--divider-color);
    border-radius: 10px;
    padding: 10px 12px;
    margin: 12px 0;
    background: var(--secondary-background-color);
  }

  .thinking-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    gap: 10px;
  }

  .thinking-title {
    font-weight: 600;
    color: var(--primary-text-color);
    font-size: 14px;
  }

  .thinking-subtitle {
    display: block;
    font-size: 12px;
    color: var(--secondary-text-color);
    margin-top: 2px;
    font-weight: normal;
  }

  .icon {
    width: 20px;
    height: 20px;
    fill: var(--secondary-text-color);
    flex-shrink: 0;
  }

  .thinking-body {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-height: 240px;
    overflow-y: auto;
  }

  .thinking-body::-webkit-scrollbar {
    width: 6px;
  }

  .thinking-body::-webkit-scrollbar-track {
    background: transparent;
  }

  .thinking-body::-webkit-scrollbar-thumb {
    background-color: var(--divider-color);
    border-radius: 3px;
  }

  .thinking-entry {
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 8px;
    background: var(--primary-background-color);
  }

  .badge {
    display: inline-block;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 6px;
    margin-bottom: 6px;
    font-weight: 500;
    text-transform: uppercase;
  }

  .thinking-entry pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 12px;
    font-family: 'SF Mono', Monaco, Consolas, monospace;
    color: var(--primary-text-color);
  }

  .thinking-empty {
    color: var(--secondary-text-color);
    font-size: 12px;
    text-align: center;
    padding: 16px;
  }
</style>
