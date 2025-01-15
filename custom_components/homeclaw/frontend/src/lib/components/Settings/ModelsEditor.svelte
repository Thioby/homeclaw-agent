<script lang="ts">
  import { get } from 'svelte/store';
  import { appState } from '$lib/stores/appState';
  import { getModelsConfig, updateProviderModels } from '$lib/services/config.service';
  import { invalidateProvidersCache } from '$lib/services/provider.service';
  import type { Model, ProvidersConfig } from '$lib/types';

  let config = $state<ProvidersConfig>({});
  let expandedProvider = $state<string | null>(null);
  let loading = $state(true);
  let saving = $state<string | null>(null);
  let message = $state<string | null>(null);
  let messageType = $state<'success' | 'error'>('success');

  // Editing state per provider
  let editingModels = $state<Record<string, Model[]>>({});

  // Load config on mount
  $effect(() => {
    loadConfig();
  });

  async function loadConfig() {
    const hass = get(appState).hass;
    if (!hass) return;

    loading = true;
    try {
      config = await getModelsConfig(hass, true);
    } catch (e) {
      console.error('[ModelsEditor] Failed to load config:', e);
    } finally {
      loading = false;
    }
  }

  function toggleProvider(provider: string) {
    if (expandedProvider === provider) {
      expandedProvider = null;
    } else {
      expandedProvider = provider;
      // Initialize editing state with current models
      if (!editingModels[provider]) {
        editingModels[provider] = JSON.parse(
          JSON.stringify(config[provider]?.models || []),
        );
      }
    }
  }

  function addModel(provider: string) {
    if (!editingModels[provider]) {
      editingModels[provider] = [];
    }
    editingModels[provider] = [
      ...editingModels[provider],
      { id: '', name: '', description: '' },
    ];
  }

  function removeModel(provider: string, index: number) {
    editingModels[provider] = editingModels[provider].filter((_, i) => i !== index);
  }

  function setDefault(provider: string, index: number) {
    editingModels[provider] = editingModels[provider].map((m, i) => ({
      ...m,
      default: i === index ? true : undefined,
    }));
  }

  function updateModelField(
    provider: string,
    index: number,
    field: keyof Model,
    value: string,
  ) {
    editingModels[provider] = editingModels[provider].map((m, i) =>
      i === index ? { ...m, [field]: value } : m,
    );
  }

  async function handleSave(provider: string) {
    const hass = get(appState).hass;
    if (!hass) return;

    const models = editingModels[provider];
    if (!models) return;

    // Validate
    for (const m of models) {
      if (!m.id || !m.name) {
        showMessage('Each model must have an ID and Name', 'error');
        return;
      }
    }

    saving = provider;
    try {
      const result = await updateProviderModels(hass, provider, { models });
      config[provider] = { ...config[provider], ...result };
      editingModels[provider] = JSON.parse(JSON.stringify(result.models || []));
      invalidateProvidersCache();
      showMessage(`${provider} models saved`, 'success');
    } catch (e: any) {
      showMessage(e?.message || 'Failed to save', 'error');
    } finally {
      saving = null;
    }
  }

  function handleRevert(provider: string) {
    editingModels[provider] = JSON.parse(
      JSON.stringify(config[provider]?.models || []),
    );
    showMessage('Changes reverted', 'success');
  }

  function showMessage(text: string, type: 'success' | 'error') {
    message = text;
    messageType = type;
    setTimeout(() => (message = null), 3000);
  }

  const providerKeys = $derived(Object.keys(config));
</script>

<div class="models-editor">
  <p class="description">
    Edit model definitions for each provider. Changes are saved to the server and take
    effect immediately.
  </p>

  {#if message}
    <div class="message" class:error={messageType === 'error'}>
      {message}
    </div>
  {/if}

  {#if loading}
    <div class="loading">Loading configuration...</div>
  {:else}
    <div class="provider-list">
      {#each providerKeys as provider (provider)}
        {@const pc = config[provider]}
        {@const isExpanded = expandedProvider === provider}
        {@const models = editingModels[provider] || pc.models || []}

        <div class="provider-card" class:expanded={isExpanded}>
          <!-- Provider header -->
          <button
            class="provider-header"
            onclick={() => toggleProvider(provider)}
          >
            <div class="provider-info">
              <span class="provider-name">{pc.display_name || provider}</span>
              <span class="model-count">{(pc.models || []).length} models</span>
            </div>
            <svg
              class="chevron"
              class:rotated={isExpanded}
              viewBox="0 0 24 24"
            >
              <path d="M7 10l5 5 5-5H7z" />
            </svg>
          </button>

          <!-- Expanded content -->
          {#if isExpanded}
            <div class="provider-body">
              <!-- Models list -->
              {#each models as model, index (index)}
                <div class="model-row">
                  <div class="model-fields">
                    <input
                      class="input small"
                      placeholder="ID (e.g. gpt-4o)"
                      value={model.id}
                      oninput={(e) =>
                        updateModelField(
                          provider,
                          index,
                          'id',
                          (e.target as HTMLInputElement).value,
                        )}
                    />
                    <input
                      class="input"
                      placeholder="Display Name"
                      value={model.name}
                      oninput={(e) =>
                        updateModelField(
                          provider,
                          index,
                          'name',
                          (e.target as HTMLInputElement).value,
                        )}
                    />
                    <input
                      class="input wide"
                      placeholder="Description (optional)"
                      value={model.description || ''}
                      oninput={(e) =>
                        updateModelField(
                          provider,
                          index,
                          'description',
                          (e.target as HTMLInputElement).value,
                        )}
                    />
                  </div>
                  <div class="model-actions">
                    <button
                      class="icon-btn"
                      class:active={model.default}
                      title={model.default ? 'Default model' : 'Set as default'}
                      onclick={() => setDefault(provider, index)}
                    >
                      <svg viewBox="0 0 24 24" class="star-icon">
                        {#if model.default}
                          <path
                            d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
                          />
                        {:else}
                          <path
                            d="M22 9.24l-7.19-.62L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.63-7.03L22 9.24zM12 15.4l-3.76 2.27 1-4.28-3.32-2.88 4.38-.38L12 6.1l1.71 4.04 4.38.38-3.32 2.88 1 4.28L12 15.4z"
                          />
                        {/if}
                      </svg>
                    </button>
                    <button
                      class="icon-btn danger"
                      title="Remove model"
                      onclick={() => removeModel(provider, index)}
                    >
                      <svg viewBox="0 0 24 24">
                        <path
                          d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              {/each}

              {#if models.length === 0}
                <div class="empty-models">
                  No models defined. Add one below.
                </div>
              {/if}

              <!-- Actions -->
              <div class="provider-actions">
                <button class="btn text" onclick={() => addModel(provider)}>
                  + Add Model
                </button>
                <div class="action-group">
                  <button
                    class="btn secondary"
                    onclick={() => handleRevert(provider)}
                  >
                    Revert
                  </button>
                  <button
                    class="btn primary"
                    onclick={() => handleSave(provider)}
                    disabled={saving === provider}
                  >
                    {saving === provider ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .models-editor {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .description {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }

  .loading {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
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

  .provider-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .provider-card {
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    overflow: hidden;
    transition: border-color 0.2s;
  }

  .provider-card.expanded {
    border-color: var(--primary-color);
  }

  .provider-header {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border: none;
    background: var(--secondary-background-color);
    cursor: pointer;
    font-family: inherit;
    transition: background 0.2s;
  }

  .provider-header:hover {
    background: var(--card-background-color);
  }

  .provider-info {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .provider-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--primary-text-color);
  }

  .model-count {
    font-size: 12px;
    color: var(--secondary-text-color);
    background: var(--divider-color);
    padding: 2px 8px;
    border-radius: 10px;
  }

  .chevron {
    width: 20px;
    height: 20px;
    fill: var(--secondary-text-color);
    transition: transform 0.2s;
  }

  .chevron.rotated {
    transform: rotate(180deg);
  }

  .provider-body {
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    border-top: 1px solid var(--divider-color);
  }

  .model-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
  }

  .model-fields {
    display: flex;
    flex: 1;
    gap: 6px;
    flex-wrap: wrap;
  }

  .input {
    padding: 6px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 6px;
    font-size: 13px;
    color: var(--primary-text-color);
    background: var(--primary-background-color);
    font-family: inherit;
    min-width: 0;
    flex: 1;
  }

  .input.small {
    flex: 0.8;
  }

  .input.wide {
    flex: 1.5;
  }

  .input:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.15);
  }

  .model-actions {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  .icon-btn {
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    cursor: pointer;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
  }

  .icon-btn:hover {
    background: var(--secondary-background-color);
  }

  .icon-btn svg {
    width: 18px;
    height: 18px;
    fill: var(--secondary-text-color);
  }

  .icon-btn.active svg,
  .icon-btn.active .star-icon {
    fill: #ffc107;
  }

  .star-icon {
    fill: var(--secondary-text-color);
  }

  .icon-btn.danger:hover {
    background: rgba(244, 67, 54, 0.1);
  }

  .icon-btn.danger:hover svg {
    fill: var(--error-color);
  }

  .empty-models {
    text-align: center;
    padding: 16px;
    color: var(--secondary-text-color);
    font-size: 13px;
    font-style: italic;
  }

  .provider-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 8px;
    border-top: 1px solid var(--divider-color);
  }

  .action-group {
    display: flex;
    gap: 6px;
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

  .btn.secondary {
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    border: 1px solid var(--divider-color);
  }

  .btn.secondary:hover:not(:disabled) {
    background: var(--card-background-color);
  }

  .btn.text {
    background: none;
    color: var(--primary-color);
    padding: 6px 8px;
  }

  .btn.text:hover {
    background: rgba(3, 169, 244, 0.08);
  }

  @media (max-width: 480px) {
    .model-fields {
      flex-direction: column;
    }

    .input.small,
    .input.wide {
      flex: 1;
    }
  }
</style>
