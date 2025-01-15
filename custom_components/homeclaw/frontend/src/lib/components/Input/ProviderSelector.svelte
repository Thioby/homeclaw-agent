<script lang="ts">
  import { providerState, hasProviders } from "$lib/stores/providers"
  import { get } from 'svelte/store';
  import { appState } from "$lib/stores/appState"
  import { fetchModels } from '$lib/services/provider.service';

  async function handleChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    providerState.update(s => ({ ...s, selectedProvider: target.value }));
    
    // Fetch models for new provider
    const currentAppState = get(appState);
    if (currentAppState.hass && target.value) {
      await fetchModels(currentAppState.hass, target.value);
    }
  }
</script>

{#if $hasProviders}
  <div class="provider-selector">
    <span class="provider-label">Provider:</span>
    <select
      class="provider-button"
      value={$providerState.selectedProvider || ''}
      onchange={handleChange}
    >
      {#each $providerState.availableProviders as provider}
        <option value={provider.value}>
          {provider.label}
        </option>
      {/each}
    </select>
  </div>
{:else}
  <div class="no-providers">No providers configured</div>
{/if}

<style>
  .provider-selector {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .provider-label {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin-right: 8px;
  }

  .provider-button {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: var(--secondary-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: var(--primary-text-color);
    transition: all 0.2s ease;
    min-width: 150px;
    appearance: none;
    background-image: url('data:image/svg+xml;charset=US-ASCII,<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7 10l5 5 5-5H7z" fill="currentColor"/></svg>');
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 30px;
  }

  .provider-button:hover {
    background-color: var(--primary-background-color);
    border-color: var(--primary-color);
  }

  .provider-button:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
  }

  .no-providers {
    color: var(--error-color);
    font-size: 14px;
    padding: 8px;
  }

  @media (max-width: 768px) {
    .provider-label {
      display: none;
    }

    .provider-button {
      width: 44px;
      min-width: 44px;
      height: 44px;
      padding: 4px;
      font-size: 0;
      border-radius: 50%;
    }
  }
</style>
