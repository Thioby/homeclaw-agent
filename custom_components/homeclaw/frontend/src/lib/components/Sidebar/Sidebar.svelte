<script lang="ts">
  import { uiState, closeSidebar } from "$lib/stores/ui"
  import { isMobile } from '$lib/utils/dom';
  import SessionList from './SessionList.svelte';
  import NewChatButton from './NewChatButton.svelte';

  let searchQuery = $state('');

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
  <div class="search-container">
    <div class="search-bar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <input type="text" placeholder="Search conversations..." aria-label="Search conversations" bind:value={searchQuery}>
    </div>
  </div>
  
  <SessionList {searchQuery} />
  
  <NewChatButton />
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width, 320px);
    min-width: var(--sidebar-width, 320px);
    height: 100%;
    background: var(--bg-sidebar, var(--secondary-background-color));
    border-right: 1px solid var(--divider-color);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), background 0.25s ease;
    position: relative;
    z-index: 10;
  }

  .sidebar.hidden {
    transform: translateX(-100%);
    width: 0;
    min-width: 0;
    border: none;
    overflow: hidden;
  }

  .search-container {
    padding: 10px 12px;
  }

  .search-bar {
    display: flex;
    align-items: center;
    background: var(--search-bg, var(--secondary-background-color));
    border-radius: 24px;
    padding: 8px 14px;
    gap: 10px;
    transition: background 0.2s, box-shadow 0.15s;
    cursor: text;
  }

  .search-bar:focus-within {
    box-shadow: 0 0 0 2px var(--accent, var(--primary-color));
    background: var(--card-background-color, #fff);
  }

  .search-bar svg {
    width: 18px;
    height: 18px;
    color: var(--search-text, var(--secondary-text-color));
    flex-shrink: 0;
  }

  .search-bar input {
    border: none;
    outline: none;
    background: transparent;
    font-size: 14px;
    color: var(--primary-text-color);
    width: 100%;
    font-family: inherit;
  }

  .search-bar input::placeholder {
    color: var(--search-text, var(--secondary-text-color));
  }

  .sidebar-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--bg-overlay, rgba(0, 0, 0, 0.4));
    z-index: 99;
    opacity: 0;
    transition: opacity 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  }

  @media (max-width: 768px) {
    .sidebar {
      position: fixed;
      left: 0;
      top: 0;
      bottom: 0;
      z-index: 100;
      transform: translateX(-100%);
      width: 85vw;
      min-width: 85vw;
      max-width: 360px;
      box-shadow: none;
    }

    .sidebar.open {
      transform: translateX(0);
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.16);
    }

    .sidebar.hidden {
      transform: translateX(-100%);
    }

    .sidebar-overlay {
      display: block;
      opacity: 1;
    }
  }

  @media (max-width: 1024px) and (min-width: 769px) {
    .sidebar {
      width: 260px;
      min-width: 260px;
    }
  }
</style>
