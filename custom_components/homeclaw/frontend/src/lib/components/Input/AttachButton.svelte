<script lang="ts">
  import { appState } from '$lib/stores/appState';

  let { onFilesSelected }: { onFilesSelected: (files: FileList) => void } = $props();

  let fileInput: HTMLInputElement;

  const ACCEPT = [
    'image/png',
    'image/jpeg',
    'image/gif',
    'image/webp',
    'text/plain',
    'text/csv',
    'text/markdown',
    'text/html',
    'application/json',
    'application/xml',
    'application/pdf',
    '.txt',
    '.csv',
    '.md',
    '.json',
    '.xml',
    '.pdf',
    '.log',
    '.yaml',
    '.yml',
    '.toml',
    '.py',
    '.js',
    '.ts',
    '.sh',
    '.sql',
    '.ini',
    '.cfg',
    '.conf',
  ].join(',');

  function handleClick() {
    fileInput?.click();
  }

  function handleChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      onFilesSelected(input.files);
      // Reset so the same file can be re-selected
      input.value = '';
    }
  }
</script>

<input
  bind:this={fileInput}
  type="file"
  accept={ACCEPT}
  multiple
  class="hidden-input"
  onchange={handleChange}
/>

<button
  class="attach-button"
  onclick={handleClick}
  disabled={$appState.isLoading}
  title="Attach file"
>
  <svg viewBox="0 0 24 24" class="icon">
    <path
      d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5a2.5 2.5 0 0 1 5 0v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5a2.5 2.5 0 0 0 5 0V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"
    />
  </svg>
</button>

<style>
  .hidden-input {
    display: none;
  }

  .attach-button {
    width: 32px;
    height: 32px;
    min-width: 32px;
    border: none;
    border-radius: 50%;
    background: transparent;
    color: var(--secondary-text-color);
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
    fill: currentColor;
  }

  .attach-button:hover:not(:disabled) {
    background: var(--divider-color);
    color: var(--primary-text-color);
  }

  .attach-button:active:not(:disabled) {
    transform: scale(0.92);
  }

  .attach-button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
</style>
