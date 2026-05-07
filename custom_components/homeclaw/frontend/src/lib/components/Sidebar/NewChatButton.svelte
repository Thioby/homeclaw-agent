<script lang="ts">
  import { appState } from '$lib/stores/appState';
  import { providerState } from '$lib/stores/providers';
  import { createSession } from '$lib/services/session.service';
  import { fetchModels } from '$lib/services/provider.service';
  import Icon from '../Icon.svelte';

  async function handleNewChat() {
    if (!$appState.hass) {
      appState.update(s => ({ ...s, error: 'Home Assistant not connected' }));
      return;
    }

    // New chats always start from the user's preferred default, even if the
    // selector currently mirrors some other session's locked provider.
    const startProvider =
      $providerState.defaultProvider || $providerState.selectedProvider;

    if (!startProvider) {
      appState.update(s => ({ ...s, error: 'Please select a provider first' }));
      return;
    }

    if ($providerState.selectedProvider !== startProvider) {
      providerState.update(s => ({
        ...s,
        selectedProvider: startProvider,
        selectedModel: $providerState.defaultModel || null,
      }));
      await fetchModels($appState.hass, startProvider);
    }

    await createSession($appState.hass, startProvider);
  }
</script>

<button class="hc-newchat" onclick={handleNewChat} disabled={!$appState.hass}>
  <Icon name="plus" />
  <span>New conversation</span>
</button>

<style>
  .hc-newchat {
    margin: 12px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--hc-card-bg);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius-sm);
    cursor: pointer;
    font: inherit;
    color: var(--hc-ink);
    transition: border-color 0.12s, background 0.12s;
    text-align: left;
  }

  .hc-newchat:hover:not(:disabled) {
    border-color: var(--hc-line-strong);
  }

  .hc-newchat:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .hc-newchat :global(svg) {
    width: 14px;
    height: 14px;
    color: var(--hc-ink-2);
  }

  .hc-newchat span {
    flex: 1;
    font-weight: 500;
    font-size: 13.5px;
  }
</style>
