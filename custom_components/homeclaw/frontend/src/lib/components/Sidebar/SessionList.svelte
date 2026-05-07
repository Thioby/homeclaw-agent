<script lang="ts">
  import type { SessionListItem } from '$lib/types';
  import { sessionState, hasSessions } from '$lib/stores/sessions';
  import SessionItem from './SessionItem.svelte';

  let { searchQuery = '' }: { searchQuery?: string } = $props();

  type Group = 'Today' | 'Yesterday' | 'Earlier';
  const GROUP_ORDER: Group[] = ['Today', 'Yesterday', 'Earlier'];

  function classify(timestamp?: string): Group {
    if (!timestamp) return 'Earlier';
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return 'Earlier';
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date >= today) return 'Today';
    if (date >= yesterday) return 'Yesterday';
    return 'Earlier';
  }

  const filteredSessions = $derived.by(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return $sessionState.sessions;
    return $sessionState.sessions.filter(s =>
      s.title.toLowerCase().includes(q) || s.preview.toLowerCase().includes(q)
    );
  });

  const grouped = $derived.by(() => {
    const buckets: Record<Group, SessionListItem[]> = {
      Today: [],
      Yesterday: [],
      Earlier: [],
    };
    for (const s of filteredSessions) {
      buckets[classify(s.updated_at)].push(s);
    }
    return GROUP_ORDER
      .map(name => ({ name, items: buckets[name] }))
      .filter(g => g.items.length > 0);
  });

  const skeletonCount = 3;
</script>

{#if $sessionState.sessionsLoading}
  {#each Array(skeletonCount) as _}
    <div class="hc-session-skeleton">
      <div class="line"></div>
      <div class="line short"></div>
    </div>
  {/each}
{:else if !$hasSessions}
  <div class="hc-empty-sessions">No conversations yet</div>
{:else if filteredSessions.length === 0}
  <div class="hc-empty-sessions">No results for &ldquo;{searchQuery}&rdquo;</div>
{:else}
  {#each grouped as g (g.name)}
    <div class="hc-section">{g.name}</div>
    {#each g.items as session (session.session_id)}
      <SessionItem {session} />
    {/each}
  {/each}
{/if}

<style>
  .hc-section {
    font-family: var(--hc-font-mono);
    font-size: 10.5px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--hc-ink-3);
    padding: 14px 8px 6px;
  }

  .hc-empty-sessions {
    text-align: center;
    padding: 32px 16px;
    color: var(--hc-ink-3);
    font-size: 13px;
  }

  .hc-session-skeleton {
    padding: 8px 10px;
  }

  .hc-session-skeleton .line {
    height: 12px;
    background: linear-gradient(
      90deg,
      var(--hc-line) 25%,
      var(--hc-bg-sunken) 50%,
      var(--hc-line) 75%
    );
    background-size: 200% 100%;
    animation: hc-shimmer 1.5s infinite;
    border-radius: 4px;
    margin-bottom: 6px;
  }

  .hc-session-skeleton .line.short {
    width: 60%;
    height: 10px;
  }

  @keyframes hc-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }
</style>
