<script lang="ts">
  import { sessionState, hasSessions } from "$lib/stores/sessions"
  import SessionItem from './SessionItem.svelte';

  // Loading skeleton count
  const skeletonCount = 3;
</script>

<div class="session-list">
  {#if $sessionState.sessionsLoading}
    <!-- Loading skeletons -->
    {#each Array(skeletonCount) as _}
      <div class="session-skeleton">
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
        <div class="skeleton-line tiny"></div>
      </div>
    {/each}
  {:else if !$hasSessions}
    <!-- Empty state -->
    <div class="empty-sessions">
      <svg viewBox="0 0 24 24" class="icon">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
      </svg>
      <p>No conversations yet</p>
    </div>
  {:else}
    <!-- Session list -->
    {#each $sessionState.sessions as session (session.session_id)}
      <SessionItem {session} />
    {/each}
  {/if}
</div>

<style>
  .session-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  /* Scrollbar styling */
  .session-list::-webkit-scrollbar {
    width: 6px;
  }

  .session-list::-webkit-scrollbar-track {
    background: transparent;
  }

  .session-list::-webkit-scrollbar-thumb {
    background-color: var(--divider-color);
    border-radius: 3px;
  }

  .session-list::-webkit-scrollbar-thumb:hover {
    background-color: var(--secondary-text-color);
  }

  /* Empty state */
  .empty-sessions {
    text-align: center;
    padding: 32px 16px;
    color: var(--secondary-text-color);
  }

  .empty-sessions .icon {
    width: 48px;
    height: 48px;
    fill: var(--disabled-text-color);
    margin-bottom: 12px;
  }

  .empty-sessions p {
    margin: 0;
    font-size: 14px;
  }

  /* Loading skeleton */
  .session-skeleton {
    padding: 12px;
    margin-bottom: 4px;
  }

  .skeleton-line {
    height: 14px;
    background: linear-gradient(
      90deg,
      var(--divider-color) 25%,
      var(--card-background-color) 50%,
      var(--divider-color) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-shimmer 1.5s infinite;
    border-radius: 4px;
    margin-bottom: 8px;
  }

  .skeleton-line.short {
    width: 60%;
    height: 12px;
  }

  .skeleton-line.tiny {
    width: 40%;
    height: 10px;
  }

  @keyframes skeleton-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }
</style>
