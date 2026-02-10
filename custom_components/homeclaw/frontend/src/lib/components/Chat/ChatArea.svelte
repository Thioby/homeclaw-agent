<script lang="ts">
  import { onMount } from 'svelte';
  import { appState, hasMessages } from '$lib/stores/appState';
  import { scrollToBottom } from '$lib/utils/dom';
  import MessageBubble from './MessageBubble.svelte';
  import LoadingIndicator from './LoadingIndicator.svelte';
  import EmptyState from './EmptyState.svelte';
  import ErrorMessage from './ErrorMessage.svelte';

  let messagesContainer: HTMLDivElement;
  let showScrollBtn = $state(false);

  // Auto-scroll to bottom when new messages arrive
  $effect(() => {
    // Track messages array to re-run on changes
    const _msgs = $appState.messages;
    const _loading = $appState.isLoading;
    if (messagesContainer) {
      scrollToBottom(messagesContainer);
    }
  });

  onMount(() => {
    scrollToBottom(messagesContainer);
  });

  function handleScroll() {
    if (!messagesContainer) return;
    const threshold = messagesContainer.scrollHeight - messagesContainer.clientHeight - 100;
    showScrollBtn = messagesContainer.scrollTop < threshold;
  }

  function scrollDown() {
    scrollToBottom(messagesContainer);
  }
</script>

<div class="chat-wrapper">
  <div class="messages" bind:this={messagesContainer} onscroll={handleScroll}>
    {#if !$hasMessages && !$appState.isLoading}
      <EmptyState />
    {/if}

    <div class="messages-inner">
      {#each $appState.messages as message (message.id)}
        <MessageBubble {message} />
      {/each}

      {#if $appState.isLoading}
        <LoadingIndicator />
      {/if}
    </div>

    <ErrorMessage />
  </div>

  {#if showScrollBtn}
    <button class="scroll-bottom-btn" onclick={scrollDown} aria-label="Scroll to bottom">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>
  {/if}
</div>

<style>
  .chat-wrapper {
    position: relative;
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .messages {
    overflow-y: auto;
    padding: 8px 0;
    background: var(--bg-chat, var(--primary-background-color));
    flex-grow: 1;
    width: 100%;
    display: flex;
    flex-direction: column;
    position: relative;
    transition: background var(--transition-medium, 250ms ease-in-out);
  }

  /* Subtle Telegram-style wallpaper pattern */
  .messages::before {
    content: '';
    position: absolute;
    inset: 0;
    opacity: 0.5;
    background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%239C92AC' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
  }

  .messages-inner {
    max-width: 720px;
    width: 100%;
    margin: 0 auto;
    padding: 0 12px;
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
  }

  /* Scrollbar styling */
  .messages::-webkit-scrollbar {
    width: 6px;
  }

  .messages::-webkit-scrollbar-track {
    background: transparent;
  }

  .messages::-webkit-scrollbar-thumb {
    background-color: var(--scrollbar-thumb, var(--divider-color));
    border-radius: 3px;
  }

  .messages::-webkit-scrollbar-thumb:hover {
    background-color: var(--secondary-text-color);
  }

  /* Scroll to bottom button */
  .scroll-bottom-btn {
    position: absolute;
    bottom: 16px;
    right: 20px;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color);
    color: var(--secondary-text-color);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 5;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transition: transform 0.15s, opacity 0.15s;
    animation: fadeIn 0.2s ease-out;
  }

  .scroll-bottom-btn:hover {
    transform: scale(1.1);
  }

  .scroll-bottom-btn svg {
    width: 20px;
    height: 20px;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @media (max-width: 768px) {
    .messages-inner {
      padding: 0 8px;
    }
  }

  @media (min-width: 1400px) {
    .messages-inner {
      max-width: 820px;
    }
  }
</style>
