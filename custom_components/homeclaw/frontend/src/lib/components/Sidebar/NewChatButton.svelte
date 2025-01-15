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

<button class="new-chat-btn" onclick={handleNewChat}>
  <svg viewBox="0 0 24 24" class="icon">
    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
  </svg>
  <span>New Chat</span>
</button>

<style>
  .new-chat-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 14px 16px;
    min-height: 48px;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s, transform 0.1s;
    font-family: inherit;
    width: 100%;
  }

  .icon {
    width: 20px;
    height: 20px;
    fill: currentColor;
  }

  .new-chat-btn:hover {
    filter: brightness(1.1);
  }

  .new-chat-btn:active {
    transform: scale(0.98);
  }

  @media (max-width: 768px) {
    .new-chat-btn {
      width: 44px;
      height: 44px;
      min-width: 44px;
      min-height: 44px;
      padding: 0;
      font-size: 0;
      gap: 0;
    }

    .new-chat-btn span {
      display: none;
    }

    .icon {
      width: 24px;
      height: 24px;
    }
  }
</style>
