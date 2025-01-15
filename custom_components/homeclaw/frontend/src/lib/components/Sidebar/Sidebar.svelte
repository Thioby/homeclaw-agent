<script lang="ts">
  import { uiState, closeSidebar } from "$lib/stores/ui"
  import { isMobile } from '$lib/utils/dom';
  import SessionList from './SessionList.svelte';
  import NewChatButton from './NewChatButton.svelte';

  const sidebarClass = $derived(
    isMobile()
      ? ($uiState.sidebarOpen ? 'sidebar open' : 'sidebar hidden')
      : ($uiState.sidebarOpen ? 'sidebar' : 'sidebar hidden')
  );

  const showOverlay = $derived($uiState.sidebarOpen && isMobile());
</script>

<!-- Mobile overlay -->
{#if showOverlay}
  <div class="sidebar-overlay" onclick={closeSidebar}></div>
{/if}

<!-- Sidebar -->
<aside class={sidebarClass}>
  <div class="sidebar-header">
    <div class="sidebar-title">
      <svg viewBox="0 0 24 24" class="icon">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
      </svg>
      Conversations
    </div>
    <NewChatButton />
  </div>
  
  <SessionList />
</aside>

<style>
  .sidebar {
    width: 280px;
    background: var(--secondary-background-color);
    border-right: 1px solid var(--divider-color);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    transition: transform 0.3s ease, width 0.3s ease;
  }

  .sidebar.hidden {
    transform: translateX(-100%);
    width: 0;
    border: none;
  }

  .sidebar-header {
    padding: 16px;
    border-bottom: 1px solid var(--divider-color);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .sidebar-title {
    font-size: 16px;
    font-weight: 500;
    color: var(--primary-text-color);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .icon {
    width: 20px;
    height: 20px;
    fill: var(--primary-color);
  }

  .sidebar-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 99;
  }

  @media (max-width: 768px) {
    .sidebar {
      position: fixed;
      left: 0;
      top: 0;
      bottom: 0;
      z-index: 100;
      transform: translateX(-100%);
      width: 280px;
    }

    .sidebar.open {
      transform: translateX(0);
      box-shadow: 0 4px 5px 0 rgba(0, 0, 0, 0.14);
    }

    .sidebar.hidden {
      transform: translateX(-100%);
    }

    .sidebar-overlay {
      display: block;
    }
  }
</style>
