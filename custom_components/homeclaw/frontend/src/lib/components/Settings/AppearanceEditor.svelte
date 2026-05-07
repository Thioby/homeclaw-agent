<script lang="ts">
  import { uiState, setTheme, setAesthetic } from '$lib/stores/ui';
  import type { Aesthetic } from '$lib/stores/ui';

  type Theme = 'light' | 'dark' | 'system';

  function onThemeChange(e: Event) {
    const value = (e.target as HTMLSelectElement).value as Theme;
    setTheme(value);
  }

  function onAestheticPick(value: Aesthetic) {
    setAesthetic(value);
  }

  const aesthetics: Array<{ id: Aesthetic; name: string; sub: string }> = [
    { id: 'warm', name: 'Warm', sub: 'Paper-tone, editorial serif.' },
    { id: 'tech', name: 'Tech', sub: 'High-contrast, dense, monospaced.' },
    { id: 'ambient', name: 'Ambient', sub: 'Always dark, gold accent glow.' },
  ];
</script>

<div class="hc-section-block">
  <div class="hc-set-eyebrow">Theme</div>
  <div class="hc-set-row">
    <div class="hc-set-row-text">
      <div class="hc-set-row-title">Color mode</div>
      <div class="hc-set-row-sub">Light, dark, or follow system preference.</div>
    </div>
    <select class="hc-pill-select" value={$uiState.theme} onchange={onThemeChange}>
      <option value="light">Light</option>
      <option value="dark">Dark</option>
      <option value="system">System</option>
    </select>
  </div>
</div>

<div class="hc-section-block">
  <div class="hc-set-eyebrow">Aesthetic</div>
  <div class="hc-aesthetic-grid">
    {#each aesthetics as a}
      <button
        class="hc-aesthetic"
        class:selected={$uiState.aesthetic === a.id}
        onclick={() => onAestheticPick(a.id)}
        type="button"
      >
        <div class="hc-aesthetic-swatch" data-id={a.id}>
          <span class="sw-bg"></span>
          <span class="sw-card"></span>
          <span class="sw-ink"></span>
        </div>
        <div class="hc-aesthetic-text">
          <div class="hc-aesthetic-name">{a.name}</div>
          <div class="hc-aesthetic-sub">{a.sub}</div>
        </div>
      </button>
    {/each}
  </div>
</div>

<style>
  .hc-section-block {
    margin-bottom: 28px;
  }
  .hc-section-block:last-child {
    margin-bottom: 0;
  }

  .hc-set-eyebrow {
    font-family: var(--hc-font-mono);
    font-size: 10.5px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--hc-ink-3);
    margin-bottom: 12px;
  }

  .hc-set-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 0;
    border-bottom: 1px solid var(--hc-line);
  }

  .hc-set-row:last-child {
    border-bottom: 0;
  }

  .hc-set-row-text {
    flex: 1;
    min-width: 0;
  }

  .hc-set-row-title {
    font-size: 13.5px;
    font-weight: 500;
    color: var(--hc-ink);
  }

  .hc-set-row-sub {
    font-size: 12px;
    color: var(--hc-ink-3);
    margin-top: 2px;
    line-height: 1.4;
  }

  .hc-pill-select {
    font: inherit;
    font-size: 13px;
    background: var(--hc-card-bg);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius-sm);
    padding: 6px 10px;
    color: var(--hc-ink);
    flex-shrink: 0;
    cursor: pointer;
  }

  .hc-aesthetic-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .hc-aesthetic {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    background: var(--hc-card-bg);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius-sm);
    cursor: pointer;
    font: inherit;
    text-align: left;
    transition: border-color 0.12s, background 0.12s;
  }

  .hc-aesthetic:hover {
    border-color: var(--hc-line-strong);
  }

  .hc-aesthetic.selected {
    border-color: var(--hc-ink);
    background: var(--hc-bg-2);
  }

  .hc-aesthetic-swatch {
    width: 44px;
    height: 28px;
    border-radius: 6px;
    overflow: hidden;
    flex-shrink: 0;
    display: flex;
    border: 1px solid var(--hc-line);
  }

  .hc-aesthetic-swatch .sw-bg,
  .hc-aesthetic-swatch .sw-card,
  .hc-aesthetic-swatch .sw-ink {
    flex: 1;
    height: 100%;
  }

  /* warm preview */
  .hc-aesthetic-swatch[data-id='warm'] .sw-bg   { background: #FBF8F2; }
  .hc-aesthetic-swatch[data-id='warm'] .sw-card { background: #FFFEFB; }
  .hc-aesthetic-swatch[data-id='warm'] .sw-ink  { background: #1F1A14; }

  /* tech preview */
  .hc-aesthetic-swatch[data-id='tech'] .sw-bg   { background: #FFFFFF; }
  .hc-aesthetic-swatch[data-id='tech'] .sw-card { background: #F5F5F4; }
  .hc-aesthetic-swatch[data-id='tech'] .sw-ink  { background: #0A0A0A; }

  /* ambient preview */
  .hc-aesthetic-swatch[data-id='ambient'] .sw-bg   { background: #0F0D0A; }
  .hc-aesthetic-swatch[data-id='ambient'] .sw-card { background: #1A1612; }
  .hc-aesthetic-swatch[data-id='ambient'] .sw-ink  { background: #E8C46A; }

  .hc-aesthetic-text {
    flex: 1;
    min-width: 0;
  }

  .hc-aesthetic-name {
    font-size: 13.5px;
    font-weight: 500;
    color: var(--hc-ink);
  }

  .hc-aesthetic-sub {
    font-size: 12px;
    color: var(--hc-ink-3);
    margin-top: 2px;
    line-height: 1.35;
  }
</style>
