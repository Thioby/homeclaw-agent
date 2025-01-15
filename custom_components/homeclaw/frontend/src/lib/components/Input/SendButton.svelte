<script lang="ts">
  import { appState } from "$lib/stores/appState"
  import { hasProviders } from "$lib/stores/providers"

  let { onclick }: { onclick: () => void } = $props();

  const disabled = $derived($appState.isLoading || !$hasProviders);
</script>

<button
  class="send-button"
  {onclick}
  {disabled}
>
  <svg viewBox="0 0 24 24" class="icon">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
  </svg>
</button>

<style>
  .send-button {
    --mdc-theme-primary: var(--primary-color);
    --mdc-theme-on-primary: var(--text-primary-color);
    min-width: 80px;
    height: 36px;
    border: none;
    border-radius: 8px;
    background: var(--primary-color);
    color: white;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 16px;
    font-weight: 500;
  }

  .icon {
    width: 20px;
    height: 20px;
    fill: white;
  }

  .send-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .send-button:active:not(:disabled) {
    transform: translateY(0);
  }

  .send-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  @media (max-width: 768px) {
    .send-button {
      min-width: 44px;
      height: 44px;
    }
  }
</style>
