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
    --mdc-theme-primary: var(--accent, var(--primary-color));
    --mdc-theme-on-primary: var(--text-primary-color);
    width: 38px;
    height: 38px;
    min-width: 38px;
    border: none;
    border-radius: 50%;
    background: var(--accent, var(--primary-color));
    color: white;
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    flex-shrink: 0;
  }

  .icon {
    width: 20px;
    height: 20px;
    fill: white;
  }

  .send-button:hover:not(:disabled) {
    transform: scale(1.08);
    background: var(--accent-hover, var(--primary-color));
  }

  .send-button:active:not(:disabled) {
    transform: scale(0.92);
  }

  .send-button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  @media (max-width: 768px) {
    .send-button {
      width: 40px;
      height: 40px;
      min-width: 40px;
    }
  }
</style>
