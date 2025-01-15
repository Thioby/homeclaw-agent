<script lang="ts">
  import { onMount, afterUpdate } from 'svelte';
  import { appState, hasMessages } from '$lib/stores/appState';
  import { scrollToBottom } from '$lib/utils/dom';
  import MessageBubble from './MessageBubble.svelte';
  import LoadingIndicator from './LoadingIndicator.svelte';
  import EmptyState from './EmptyState.svelte';
  import ErrorMessage from './ErrorMessage.svelte';

  let messagesContainer: HTMLDivElement;

  // Auto-scroll to bottom when new messages arrive
  afterUpdate(() => {
    scrollToBottom(messagesContainer);
  });

  onMount(() => {
    scrollToBottom(messagesContainer);
  });
</script>

<div class="messages" bind:this={messagesContainer}>
  {#if !$hasMessages && !$appState.isLoading}
    <EmptyState />
  {/if}

  {#each $appState.messages as message (message.id)}
    <MessageBubble {message} />
  {/each}

  {#if $appState.isLoading}
    <LoadingIndicator />
  {/if}

  <ErrorMessage />
</div>

<style>
  .messages {
    overflow-y: auto;
    border: 1px solid var(--divider-color);
    border-radius: 12px;
    margin-bottom: 24px;
    padding: 16px;
    background: var(--primary-background-color);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    flex-grow: 1;
    width: 100%;
    display: flex;
    flex-direction: column;
  }

  /* Scrollbar styling */
  .messages::-webkit-scrollbar {
    width: 8px;
  }

  .messages::-webkit-scrollbar-track {
    background: transparent;
  }

  .messages::-webkit-scrollbar-thumb {
    background-color: var(--divider-color);
    border-radius: 4px;
  }

  .messages::-webkit-scrollbar-thumb:hover {
    background-color: var(--secondary-text-color);
  }
</style>
