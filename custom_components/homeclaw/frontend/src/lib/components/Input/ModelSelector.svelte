<script lang="ts">
  import { providerState, hasModels } from "$lib/stores/providers"

  function handleChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    providerState.update(s => ({ ...s, selectedModel: target.value }));
  }

  const isDefault = $derived(
    $providerState.defaultModel !== null &&
    $providerState.selectedModel === $providerState.defaultModel &&
    $providerState.selectedProvider === $providerState.defaultProvider
  );
</script>

{#if $hasModels}
  <div class="provider-selector">
    <span class="provider-label">Model:</span>
    {#if isDefault}
      <span class="default-star" title="Your default model">&#9733;</span>
    {/if}
    <select
      class="provider-button"
      value={$providerState.selectedModel || ''}
      onchange={handleChange}
    >
      {#each $providerState.availableModels as model}
        <option value={model.id}>
          {model.name}
        </option>
      {/each}
    </select>
  </div>
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

  .default-star {
    color: #ffc107;
    font-size: 14px;
    line-height: 1;
    flex-shrink: 0;
  }

  @media (max-width: 768px) {
    .provider-label {
      display: none;
    }
  }
</style>
