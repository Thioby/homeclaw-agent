<script lang="ts">
  import { appState } from '$lib/stores/appState';
  import { get } from 'svelte/store';
  import { autoResize } from '$lib/utils/dom';

  let {
    onSend,
    onFilesDropped,
  }: {
    onSend: () => void;
    onFilesDropped?: (files: File[]) => void;
  } = $props();

  let textarea: HTMLTextAreaElement;
  let value = $state('');
  let isDragOver = $state(false);

  function handleInput(e: Event) {
    const target = e.target as HTMLTextAreaElement;
    value = target.value;
    autoResize(target);
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey && !get(appState).isLoading) {
      e.preventDefault();
      onSend();
    }
  }

  function handlePaste(e: ClipboardEvent) {
    if (!onFilesDropped) return;

    const items = e.clipboardData?.items;
    if (!items) return;

    const files: File[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }

    if (files.length > 0) {
      e.preventDefault();
      onFilesDropped(files);
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
    isDragOver = true;
  }

  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    isDragOver = false;
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    isDragOver = false;

    if (!onFilesDropped) return;

    const files: File[] = [];
    if (e.dataTransfer?.files) {
      for (let i = 0; i < e.dataTransfer.files.length; i++) {
        files.push(e.dataTransfer.files[i]);
      }
    }

    if (files.length > 0) {
      onFilesDropped(files);
    }
  }

  // Export getValue for parent component
  export function getValue(): string {
    return value;
  }

  export function clear(): void {
    value = '';
    if (textarea) {
      textarea.style.height = 'auto';
    }
  }
</script>

<div
  class="input-wrapper"
  class:drag-over={isDragOver}
  ondragover={handleDragOver}
  ondragleave={handleDragLeave}
  ondrop={handleDrop}
  role="textbox"
  tabindex="-1"
>
  <textarea
    bind:this={textarea}
    bind:value
    placeholder="Ask me anything about your Home Assistant..."
    disabled={$appState.isLoading}
    oninput={handleInput}
    onkeydown={handleKeyDown}
    onpaste={handlePaste}
  ></textarea>
  {#if isDragOver}
    <div class="drop-overlay">
      <span class="drop-label">Drop files here</span>
    </div>
  {/if}
</div>

<style>
  .input-wrapper {
    flex-grow: 1;
    position: relative;
    transition: background 0.15s ease;
    border-radius: 8px;
  }

  .input-wrapper.drag-over {
    background: var(--accent-light, rgba(3, 169, 244, 0.08));
  }

  textarea {
    width: 100%;
    min-height: 24px;
    max-height: 160px;
    padding: 8px 12px;
    border: none;
    outline: none;
    resize: none;
    font-size: 14px;
    line-height: 1.45;
    background: transparent;
    color: var(--primary-text-color);
    font-family: inherit;
  }

  textarea::placeholder {
    color: var(--search-text, var(--secondary-text-color));
  }

  textarea:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .drop-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--accent-light, rgba(3, 169, 244, 0.12));
    border-radius: 8px;
    border: 2px dashed var(--accent, var(--primary-color));
    pointer-events: none;
  }

  .drop-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--accent, var(--primary-color));
  }
</style>
