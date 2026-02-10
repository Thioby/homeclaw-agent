<script lang="ts">
  import { appState } from "$lib/stores/appState"
  import { get } from 'svelte/store';
  import { autoResize } from '$lib/utils/dom';

  let { onSend }: { onSend: () => void } = $props();
  
  let textarea: HTMLTextAreaElement;
  let value = $state('');

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

<div class="input-wrapper">
  <textarea
    bind:this={textarea}
    bind:value
    placeholder="Ask me anything about your Home Assistant..."
    disabled={$appState.isLoading}
    oninput={handleInput}
    onkeydown={handleKeyDown}
  ></textarea>
</div>

<style>
  .input-wrapper {
    flex-grow: 1;
    position: relative;
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
</style>
