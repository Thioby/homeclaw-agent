<script lang="ts">
  import { appState } from '$lib/stores/appState';
  import Icon from '../Icon.svelte';

  type Tone = 'good' | 'warn' | 'cool' | 'ink';
  interface Chip {
    tone: Tone;
    label: string;
  }

  function greeting(): string {
    const h = new Date().getHours();
    if (h < 5) return 'Up late';
    if (h < 12) return 'Good morning';
    if (h < 18) return 'Good afternoon';
    return 'Good evening';
  }

  // Build a "right now" status rail from hass.states. Best-effort: returns
  // 0–4 chips depending on what entities exist. Never throws.
  const statusChips = $derived.by<Chip[]>(() => {
    const states = $appState.hass?.states;
    if (!states) return [];
    const ids = Object.keys(states);
    const chips: Chip[] = [];

    // Lights on
    const lightsOn = ids.filter(
      id => id.startsWith('light.') && states[id]?.state === 'on'
    ).length;
    if (lightsOn > 0) {
      chips.push({ tone: 'good', label: `${lightsOn} light${lightsOn === 1 ? '' : 's'} on` });
    }

    // Climate (first entity with target/current temp)
    for (const id of ids) {
      if (!id.startsWith('climate.')) continue;
      const s = states[id];
      const mode = s?.state;
      const current = s?.attributes?.current_temperature;
      if (current == null || mode === 'off') continue;
      const unit = $appState.hass?.config?.unit_system?.temperature || '°';
      const verb = mode === 'cool' ? 'Cooling' : mode === 'heat' ? 'Heating' : 'Climate';
      const tone: Tone = mode === 'cool' ? 'cool' : mode === 'heat' ? 'warn' : 'ink';
      chips.push({ tone, label: `${verb} · ${Math.round(current)}${unit}` });
      break;
    }

    // Locks
    const lockIds = ids.filter(id => id.startsWith('lock.'));
    if (lockIds.length > 0) {
      const unlocked = lockIds.filter(id => states[id]?.state === 'unlocked').length;
      if (unlocked === 0) {
        chips.push({ tone: 'good', label: 'Doors locked' });
      } else {
        chips.push({ tone: 'warn', label: `${unlocked} unlocked` });
      }
    }

    // Garage / open covers
    const openCovers = ids.filter(
      id => id.startsWith('cover.') && states[id]?.state === 'open'
    );
    if (openCovers.length > 0) {
      const first = openCovers[0];
      const friendly = states[first]?.attributes?.friendly_name || first.split('.')[1];
      chips.push({
        tone: 'warn',
        label: openCovers.length === 1 ? `${friendly} open` : `${openCovers.length} covers open`,
      });
    }

    return chips.slice(0, 4);
  });

  const userName = $derived(($appState.userName || '').trim());

  type Suggestion = { icon: 'sparkle' | 'chart' | 'leaf' | 'home'; title: string; sub: string };
  const suggestions: Suggestion[] = [
    {
      icon: 'sparkle',
      title: 'Set up a sunset routine',
      sub: 'Lights, blinds, and music when the sun goes down.',
    },
    {
      icon: 'chart',
      title: 'Why did energy spike yesterday?',
      sub: 'Compare to last week and find the culprit.',
    },
    {
      icon: 'leaf',
      title: 'Make the house more efficient',
      sub: 'Audit always-on devices and propose changes.',
    },
    {
      icon: 'home',
      title: "Build a 'leaving home' scene",
      sub: 'Locks, thermostat, lights — one tap on the way out.',
    },
  ];

  function toneVar(t: Tone): string {
    switch (t) {
      case 'good': return 'var(--hc-good)';
      case 'warn': return 'var(--hc-warn)';
      case 'cool': return 'var(--hc-cool)';
      default:     return 'var(--hc-ink-3)';
    }
  }

  function handleSuggestion(text: string) {
    window.dispatchEvent(new CustomEvent('homeclaw-suggest', { detail: text }));
  }
</script>

<div class="hc-empty">
  {#if statusChips.length > 0}
    <div class="hc-empty-rail">
      <span class="hc-rail-label">RIGHT NOW</span>
      {#each statusChips as s}
        <div class="hc-rail-chip">
          <span class="dot" style="background: {toneVar(s.tone)};"></span>
          {s.label}
        </div>
      {/each}
    </div>
  {/if}

  <h1 class="hc-empty-greet">
    {greeting()}{userName ? `, ${userName}` : ''}.
    <em>What should the house do?</em>
  </h1>

  <p class="hc-empty-sub">
    Ask in plain language. I can read sensors, control devices, and propose
    automations — you approve before anything is saved.
  </p>

  <div class="hc-empty-grid">
    {#each suggestions as s}
      <button class="hc-suggest" onclick={() => handleSuggestion(s.title)}>
        <div class="hc-suggest-icon"><Icon name={s.icon} size={14} /></div>
        <div class="hc-suggest-title">{s.title}</div>
        <div class="hc-suggest-sub">{s.sub}</div>
      </button>
    {/each}
  </div>
</div>

<style>
  .hc-empty {
    max-width: 760px;
    width: 100%;
    margin: 0 auto;
    padding: 60px 28px 28px;
    display: flex;
    flex-direction: column;
    gap: 24px;
    z-index: 1;
    position: relative;
  }

  .hc-empty-rail {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .hc-rail-label {
    font-family: var(--hc-font-mono);
    font-size: 10.5px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--hc-ink-3);
    margin-right: 4px;
  }

  .hc-rail-chip {
    font-size: 12.5px;
    background: var(--hc-card-bg);
    border: 1px solid var(--hc-line);
    border-radius: 999px;
    padding: 5px 12px;
    color: var(--hc-ink-2);
    display: inline-flex;
    align-items: center;
    gap: 7px;
  }

  .hc-rail-chip .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .hc-empty-greet {
    font-family: var(--hc-font-display);
    font-weight: 400;
    font-size: 38px;
    letter-spacing: -0.025em;
    line-height: 1.1;
    margin: 8px 0 0;
    text-wrap: balance;
    color: var(--hc-ink);
  }

  .hc-empty-greet em {
    color: var(--hc-ink-3);
    font-style: italic;
  }

  .hc-empty-sub {
    max-width: 560px;
    font-size: 15px;
    color: var(--hc-ink-2);
    line-height: 1.55;
    margin: 0;
  }

  .hc-empty-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-top: 8px;
  }

  .hc-suggest {
    text-align: left;
    background: var(--hc-card-bg);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius);
    padding: 14px;
    cursor: pointer;
    font: inherit;
    color: var(--hc-ink);
    display: flex;
    flex-direction: column;
    gap: 6px;
    transition: border-color 0.12s, transform 0.12s;
  }

  .hc-suggest:hover {
    border-color: var(--hc-line-strong);
    transform: translateY(-1px);
  }

  .hc-suggest-icon {
    width: 26px;
    height: 26px;
    background: var(--hc-bg-sunken);
    color: var(--hc-ink-2);
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 2px;
  }

  .hc-suggest-title {
    font-size: 14px;
    font-weight: 500;
  }

  .hc-suggest-sub {
    font-size: 12.5px;
    color: var(--hc-ink-3);
    line-height: 1.45;
  }

  @media (max-width: 768px) {
    .hc-empty {
      padding: 40px 16px 16px;
    }
    .hc-empty-greet {
      font-size: 30px;
    }
    .hc-empty-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
