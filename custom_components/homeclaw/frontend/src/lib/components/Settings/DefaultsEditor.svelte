<script lang="ts">
  import { get } from 'svelte/store';
  import { appState } from '$lib/stores/appState';
  import { providerState } from '$lib/stores/providers';
  import { savePreferences } from '$lib/services/provider.service';
  import type { Model } from '$lib/types';

  let selectedProvider = $state<string | null>(null);
  let selectedModel = $state<string | null>(null);
  let models = $state<Model[]>([]);
  let loading = $state(false);
  let saving = $state(false);
  let message = $state<string | null>(null);
  let messageType = $state<'success' | 'error'>('success');

  // Initialize from current store state
  $effect(() => {
    const ps = $providerState;
    if (selectedProvider === null) {
      selectedProvider = ps.defaultProvider;
    }
    if (selectedModel === null) {
      selectedModel = ps.defaultModel;
    }
  });

  // Fetch models when provider changes
  $effect(() => {
    if (selectedProvider) {
      loadModelsForProvider(selectedProvider);
    } else {
      models = [];
    }
  });

  async function loadModelsForProvider(provider: string) {
    const hass = get(appState).hass;
    if (!hass) return;

    loading = true;
    try {
      const result = await hass.callWS({
        type: 'homeclaw/models/list',
        provider,
      });
      models = result.models || [];
    } catch (e) {
      console.warn('[DefaultsEditor] Failed to load models:', e);
      models = [];
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    const hass = get(appState).hass;
    if (!hass) return;

    saving = true;
    message = null;

    try {
      await savePreferences(hass, {
        default_provider: selectedProvider,
        default_model: selectedModel,
      });
      message = 'Defaults saved successfully';
      messageType = 'success';
    } catch (e: any) {
      console.error('[DefaultsEditor] Failed to save:', e);
      message = e?.message || 'Failed to save defaults';
      messageType = 'error';
    } finally {
      saving = false;
      setTimeout(() => (message = null), 3000);
    }
  }

  async function handleClear() {
    const hass = get(appState).hass;
    if (!hass) return;

    saving = true;
    message = null;

    try {
      await savePreferences(hass, {
        default_provider: null,
        default_model: null,
      });
      selectedProvider = null;
      selectedModel = null;
      message = 'Defaults cleared';
      messageType = 'success';
    } catch (e: any) {
      message = e?.message || 'Failed to clear defaults';
      messageType = 'error';
    } finally {
      saving = false;
      setTimeout(() => (message = null), 3000);
    }
  }

  function handleProviderChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    selectedProvider = target.value || null;
    selectedModel = null;
  }

  function handleModelChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    selectedModel = target.value || null;
  }

  const hasDefaults = $derived(
    $providerState.defaultProvider !== null || $providerState.defaultModel !== null,
  );
</script>

<div class="defaults-editor">
  <p class="description">
    Set a default provider and model that will be automatically selected when you open the chat.
  </p>

  <!-- Provider selector -->
  <div class="field">
    <label for="default-provider">Default Provider</label>
    <select
      id="default-provider"
      class="select"
      value={selectedProvider || ''}
      onchange={handleProviderChange}
    >
      <option value="">-- None (auto-select first) --</option>
      {#each $providerState.availableProviders as provider}
        <option value={provider.value}>{provider.label}</option>
      {/each}
    </select>
  </div>

  <!-- Model selector -->
  <div class="field">
    <label for="default-model">Default Model</label>
    {#if loading}
      <div class="loading-text">Loading models...</div>
    {:else}
      <select
        id="default-model"
        class="select"
        value={selectedModel || ''}
        onchange={handleModelChange}
        disabled={!selectedProvider || models.length === 0}
      >
        <option value="">-- Provider default --</option>
        {#each models as model}
          <option value={model.id}>
            {model.name}{model.default ? ' (provider default)' : ''}
          </option>
        {/each}
      </select>
    {/if}
  </div>

  <!-- Current defaults info -->
  {#if hasDefaults}
    <div class="current-defaults">
      <strong>Current defaults:</strong>
      {#if $providerState.defaultProvider}
        <span class="badge">
          {$providerState.availableProviders.find((p) => p.value === $providerState.defaultProvider)
            ?.label || $providerState.defaultProvider}
        </span>
      {/if}
      {#if $providerState.defaultModel}
        <span class="badge model">{$providerState.defaultModel}</span>
      {/if}
    </div>
  {/if}

  <!-- Message -->
  {#if message}
    <div class="message" class:error={messageType === 'error'}>
      {message}
    </div>
  {/if}

  <!-- Actions -->
  <div class="actions">
    <button class="btn primary" onclick={handleSave} disabled={saving}>
      {saving ? 'Saving...' : 'Save Defaults'}
    </button>
    {#if hasDefaults}
      <button class="btn secondary" onclick={handleClear} disabled={saving}>
        Clear Defaults
      </button>
    {/if}
  </div>
</div>

<style>
  .defaults-editor {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .description {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .field label {
    font-size: 13px;
    font-weight: 500;
    color: var(--primary-text-color);
  }

  .select {
    padding: 8px 12px;
    background: var(--secondary-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    font-size: 14px;
    color: var(--primary-text-color);
    cursor: pointer;
    font-family: inherit;
    appearance: none;
    background-image: url('data:image/svg+xml;charset=US-ASCII,<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7 10l5 5 5-5H7z" fill="currentColor"/></svg>');
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 30px;
  }

  .select:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .select:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
  }

  .loading-text {
    font-size: 13px;
    color: var(--secondary-text-color);
    padding: 8px 0;
  }

  .current-defaults {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    padding: 10px 12px;
    background: var(--secondary-background-color);
    border-radius: 8px;
    font-size: 13px;
    color: var(--secondary-text-color);
  }

  .badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    background: var(--primary-color);
    color: white;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
  }

  .badge.model {
    background: var(--accent-color, #4caf50);
  }

  .message {
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    background: rgba(76, 175, 80, 0.1);
    color: #4caf50;
    border: 1px solid rgba(76, 175, 80, 0.3);
  }

  .message.error {
    background: rgba(244, 67, 54, 0.1);
    color: var(--error-color);
    border-color: rgba(244, 67, 54, 0.3);
  }

  .actions {
    display: flex;
    gap: 8px;
    padding-top: 8px;
  }

  .btn {
    padding: 8px 20px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
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

  .btn.secondary {
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    border: 1px solid var(--divider-color);
  }

  .btn.secondary:hover:not(:disabled) {
    background: var(--card-background-color);
  }
</style>
