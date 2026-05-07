<script lang="ts">
  import { providerState, hasProviders } from "$lib/stores/providers"
  import { get } from 'svelte/store';
  import { appState } from "$lib/stores/appState"
  import { sessionState } from "$lib/stores/sessions"
  import { fetchModels } from '$lib/services/provider.service';
  import { updateSessionProvider } from '$lib/services/session.service';

  let { disabled = false }: { disabled?: boolean } = $props();

  async function handleChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    const newProvider = target.value;
    const currentAppState = get(appState);
    const activeSessionId = get(sessionState).activeSessionId;

    // Persist on the active session so the backend uses the new provider
    // for the next send. Selectors are already disabled once a session has
    // messages, so updateSessionProvider should always succeed here.
    if (currentAppState.hass && activeSessionId && newProvider) {
      await updateSessionProvider(currentAppState.hass, activeSessionId, newProvider);
    } else {
      providerState.update(s => ({ ...s, selectedProvider: newProvider }));
      if (currentAppState.hass && newProvider) {
        await fetchModels(currentAppState.hass, newProvider);
      }
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
      {disabled}
      title={disabled ? 'Provider is locked for this conversation. Start a new chat to change it.' : 'Choose provider'}
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

  .provider-button:hover:not(:disabled) {
    background-color: var(--primary-background-color);
    border-color: var(--primary-color);
  }

  .provider-button:focus:not(:disabled) {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
  }

  .provider-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
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
