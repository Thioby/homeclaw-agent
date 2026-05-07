<script lang="ts">
  import Icon from './Icon.svelte';

  /**
   * Avatar — square 28×28 by default, sized via prop.
   * Bot: dark fill with home icon. User: sunken bg with initial.
   * `emoji` overrides the default glyph but is clipped to a single grapheme
   * and capped in font-size to never overflow the box.
   */
  export let from: 'user' | 'bot' = 'bot';
  export let name: string = '';
  export let emoji: string = '';
  export let size: number = 28;

  $: initial = (name || '?').trim().charAt(0).toUpperCase();
  // Take only the first grapheme — multi-emoji like "🤖✨" must not overflow.
  $: firstEmoji = emoji ? Array.from(emoji.trim())[0] || '' : '';
  $: emojiFontSize = Math.round(size * 0.55);
</script>

<div
  class="hc-avatar"
  class:is-user={from === 'user'}
  class:is-bot={from === 'bot'}
  style="width: {size}px; height: {size}px; min-width: {size}px; min-height: {size}px;"
  aria-hidden="true"
>
  {#if firstEmoji}
    <span class="hc-avatar-emoji" style="font-size: {emojiFontSize}px;">{firstEmoji}</span>
  {:else if from === 'bot'}
    <Icon name="home" size={Math.round(size * 0.55)} />
  {:else}
    <span class="hc-avatar-initial">{initial}</span>
  {/if}
</div>

<style>
  .hc-avatar {
    border-radius: var(--hc-radius-sm);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    font-weight: 600;
    letter-spacing: 0.02em;
    line-height: 1;
    box-sizing: border-box;
  }

  .hc-avatar.is-user {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink-2);
  }

  .hc-avatar.is-bot {
    background: var(--hc-ink);
    color: var(--hc-bg);
  }

  .hc-avatar-emoji {
    line-height: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .hc-avatar-initial {
    font-size: 11.5px;
    user-select: none;
  }
</style>
