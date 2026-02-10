<script lang="ts">
  import { appState } from "$lib/stores/appState"
  import { providerState } from "$lib/stores/providers"
  import { createSession } from '$lib/services/session.service';

  async function handleNewChat() {
    if (!$appState.hass) {
      appState.update(s => ({ ...s, error: 'Home Assistant not connected' }));
      return;
    }

    if (!$providerState.selectedProvider) {
      appState.update(s => ({ ...s, error: 'Please select a provider first' }));
      return;
    }

    await createSession($appState.hass, $providerState.selectedProvider);
  }
</script>

<button class="fab" onclick={handleNewChat} title="New chat" aria-label="New chat" disabled={!$appState.hass}>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 20h9"/>
    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
  </svg>
</button>

<style>
  .fab {
    position: absolute;
    bottom: 20px;
    right: 20px;
    width: 54px;
    height: 54px;
    border-radius: 50%;
    background: var(--accent, var(--primary-color));
    color: #fff;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: var(--fab-shadow, 0 4px 16px rgba(3, 169, 244, 0.35));
    transition: transform 0.15s, box-shadow 0.15s, background 0.15s;
    z-index: 5;
  }

  .fab:hover:not(:disabled) {
    transform: scale(1.05);
    background: var(--accent-hover, var(--primary-color));
  }

  .fab:active:not(:disabled) {
    transform: scale(0.95);
  }

  .fab:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .fab svg {
    width: 24px;
    height: 24px;
  }
</style>
