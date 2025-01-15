<script lang="ts">
  import { appState } from '$lib/stores/appState';

  function dismissError() {
    appState.update(s => ({ ...s, error: null }));
  }
</script>

{#if $appState.error}
  <div class="error">
    <svg viewBox="0 0 24 24" class="icon">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
    </svg>
    <span class="error-message">{$appState.error}</span>
    <button class="error-dismiss" onclick={dismissError} aria-label="Dismiss error">
      <svg viewBox="0 0 24 24" class="close-icon">
        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
      </svg>
    </button>
  </div>
{/if}

<style>
  .error {
    color: var(--error-color);
    padding: 12px 16px;
    margin: 8px 16px;
    border-radius: 8px;
    background: rgba(219, 68, 55, 0.1);
    border: 1px solid var(--error-color);
    animation: fadeIn 0.3s ease-out;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
  }

  .icon {
    width: 20px;
    height: 20px;
    fill: var(--error-color);
    flex-shrink: 0;
  }

  .error-message {
    flex: 1;
  }

  .error-dismiss {
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .error-dismiss:hover {
    background: rgba(219, 68, 55, 0.2);
  }

  .close-icon {
    width: 18px;
    height: 18px;
    fill: var(--error-color);
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
