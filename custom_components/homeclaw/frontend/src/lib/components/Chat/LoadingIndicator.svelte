<script lang="ts">
  import { appState } from '$lib/stores/appState';
  import Avatar from '../Avatar.svelte';

  const senderName = $derived($appState.agentName || 'Homeclaw');
</script>

<div class="hc-msg hc-loading">
  <Avatar from="bot" name={senderName} />
  <div class="hc-msg-body">
    <div class="hc-msg-meta">
      <span class="hc-msg-name">{senderName}</span>
      <span class="hc-msg-thinking">thinking</span>
    </div>
    <div class="hc-bubble hc-bubble-loading" aria-live="polite" aria-label="Assistant is thinking">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
    </div>
  </div>
</div>

<style>
  .hc-msg {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    margin-bottom: var(--hc-msg-gap, 22px);
    animation: hcMsgAppear 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }

  .hc-msg-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
    max-width: calc(100% - 40px);
  }

  .hc-msg-meta {
    font-size: 11.5px;
    color: var(--hc-ink-3);
    display: flex;
    gap: 8px;
    align-items: baseline;
  }

  .hc-msg-name {
    font-weight: 500;
    color: var(--hc-ink-2);
  }

  .hc-msg-thinking {
    font-family: var(--hc-font-mono);
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--hc-ink-3);
  }

  .hc-bubble-loading {
    background: var(--hc-card-bg);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius);
    padding: 14px 16px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    width: fit-content;
  }

  .dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--hc-ink-3);
    animation: hcDot 1.2s infinite ease-in-out;
  }
  .dot:nth-child(2) { animation-delay: 0.18s; }
  .dot:nth-child(3) { animation-delay: 0.36s; }

  @keyframes hcDot {
    0%, 60%, 100% { opacity: 0.25; transform: translateY(0); }
    30%           { opacity: 1;    transform: translateY(-3px); }
  }

  @keyframes hcMsgAppear {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  @media (max-width: 768px) {
    .hc-msg { gap: 10px; }
    .hc-msg-body { max-width: calc(100% - 38px); }
  }
</style>
