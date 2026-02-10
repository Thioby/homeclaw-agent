<script lang="ts">
  import { appState } from '$lib/stores/appState';

  // Suggestion chips - clicking fills the message input
  const suggestions = [
    'Turn off all lights',
    'Create a morning routine',
    'Show energy usage',
    'Set up motion sensors',
  ];

  function handleSuggestion(text: string) {
    // Dispatch a custom event that InputArea can listen to
    // For now we use a simple approach: set a global suggestion
    appState.update(s => ({ ...s, pendingSuggestion: text }));
  }
</script>

<div class="empty-state">
  <div class="empty-icon">
    {#if $appState.agentEmoji}
      <span class="emoji-icon">{$appState.agentEmoji}</span>
    {:else}
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1.07A7.001 7.001 0 0 1 7.07 19H6a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h-1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2zm-3 13a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"/>
      </svg>
    {/if}
  </div>
  <h2>Welcome to {$appState.agentName}</h2>
  <p>Your AI-powered Home Assistant companion. Ask me anything about your smart home.</p>
  <div class="suggestions">
    {#each suggestions as text}
      <button class="suggestion-chip" onclick={() => handleSuggestion(text)}>
        {text}
      </button>
    {/each}
  </div>
</div>

<style>
  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px;
    z-index: 1;
  }

  .empty-icon {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: var(--accent-light, rgba(3, 169, 244, 0.12));
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
    animation: emptyPulse 3s ease-in-out infinite;
  }

  .empty-icon svg {
    width: 48px;
    height: 48px;
    color: var(--accent, var(--primary-color));
  }

  .empty-icon .emoji-icon {
    font-size: 48px;
    line-height: 1;
  }

  @keyframes emptyPulse {
    0%, 100% {
      transform: scale(1);
      box-shadow: 0 0 0 0 var(--accent-light, rgba(3, 169, 244, 0.15));
    }
    50% {
      transform: scale(1.03);
      box-shadow: 0 0 0 16px transparent;
    }
  }

  h2 {
    font-size: 22px;
    font-weight: 600;
    color: var(--primary-text-color);
    margin-bottom: 8px;
  }

  p {
    color: var(--secondary-text-color);
    font-size: 15px;
    max-width: 360px;
    line-height: 1.5;
    margin-bottom: 0;
  }

  .suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 24px;
    justify-content: center;
    max-width: 480px;
  }

  .suggestion-chip {
    padding: 8px 16px;
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color);
    border-radius: 9999px;
    font-size: 13.5px;
    color: var(--primary-text-color);
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .suggestion-chip:hover {
    border-color: var(--accent, var(--primary-color));
    color: var(--accent, var(--primary-color));
    background: var(--accent-light, rgba(3, 169, 244, 0.08));
  }

  @media (max-width: 768px) {
    .suggestions {
      flex-direction: column;
      align-items: center;
    }

    .empty-icon {
      width: 80px;
      height: 80px;
    }

    .empty-icon svg {
      width: 40px;
      height: 40px;
    }

    h2 {
      font-size: 20px;
    }
  }
</style>
