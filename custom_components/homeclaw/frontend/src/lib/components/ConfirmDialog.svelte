<script lang="ts">
  import { confirmDialogRequest, resolveConfirmDialog } from '$lib/stores/dialog';
  import Icon from './Icon.svelte';

  function onCancel() {
    resolveConfirmDialog(false);
  }

  function onConfirm() {
    resolveConfirmDialog(true);
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      onConfirm();
    }
  }

  function focusConfirm(node: HTMLButtonElement) {
    queueMicrotask(() => node.focus());
  }
</script>

<svelte:window onkeydown={$confirmDialogRequest ? onKeydown : null} />

{#if $confirmDialogRequest}
  {@const req = $confirmDialogRequest}
  <div class="hc-confirm-scrim" onclick={onCancel} role="presentation"></div>

  <div
    class="hc-confirm"
    role="alertdialog"
    aria-modal="true"
    aria-labelledby="hc-confirm-title"
    aria-describedby="hc-confirm-msg"
  >
    <div class="hc-confirm-head">
      <div
        class="hc-confirm-icon"
        class:is-danger={req.destructive}
        aria-hidden="true"
      >
        {#if req.destructive}
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 9v4M12 17h.01"/>
            <path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          </svg>
        {:else}
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 16v-4M12 8h.01"/>
          </svg>
        {/if}
      </div>
      <div class="hc-confirm-text">
        <h3 id="hc-confirm-title" class="hc-confirm-title">
          {req.title ?? 'Are you sure?'}
        </h3>
        <p id="hc-confirm-msg" class="hc-confirm-message">{req.message}</p>
      </div>
      <button
        class="hc-confirm-x"
        onclick={onCancel}
        aria-label="Close"
        type="button"
      >
        <Icon name="x" size={14} />
      </button>
    </div>

    <div class="hc-confirm-actions">
      <button class="hc-confirm-btn hc-confirm-cancel" onclick={onCancel} type="button">
        {req.cancelText ?? 'Cancel'}
      </button>
      <button
        class="hc-confirm-btn hc-confirm-ok"
        class:is-danger={req.destructive}
        onclick={onConfirm}
        use:focusConfirm
        type="button"
      >
        {req.confirmText ?? 'Confirm'}
      </button>
    </div>
  </div>
{/if}

<style>
  .hc-confirm-scrim {
    position: fixed;
    inset: 0;
    background: rgba(20, 16, 10, 0.42);
    backdrop-filter: blur(3px);
    -webkit-backdrop-filter: blur(3px);
    z-index: 1000;
    animation: hc-confirm-fade 0.16s ease-out;
  }

  :global(:host([data-theme="dark"])) .hc-confirm-scrim,
  :global(:host([data-aesthetic="ambient"])) .hc-confirm-scrim {
    background: rgba(0, 0, 0, 0.58);
  }

  .hc-confirm {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 1001;
    width: min(420px, calc(100vw - 32px));
    background: var(--hc-card-bg);
    color: var(--hc-ink);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius, 14px);
    box-shadow:
      0 1px 3px rgba(0, 0, 0, 0.04),
      0 12px 32px rgba(20, 16, 10, 0.18),
      0 24px 60px rgba(20, 16, 10, 0.12);
    animation: hc-confirm-pop 0.2s cubic-bezier(0.34, 1.2, 0.64, 1);
    overflow: hidden;
  }

  :global(:host([data-theme="dark"])) .hc-confirm,
  :global(:host([data-aesthetic="ambient"])) .hc-confirm {
    box-shadow:
      0 1px 3px rgba(0, 0, 0, 0.4),
      0 12px 32px rgba(0, 0, 0, 0.5),
      0 24px 60px rgba(0, 0, 0, 0.4);
  }

  @keyframes hc-confirm-fade {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes hc-confirm-pop {
    from {
      opacity: 0;
      transform: translate(-50%, -48%) scale(0.96);
    }
    to {
      opacity: 1;
      transform: translate(-50%, -50%) scale(1);
    }
  }

  .hc-confirm-head {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 20px 20px 4px 20px;
    position: relative;
  }

  .hc-confirm-icon {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    background: color-mix(in oklab, var(--hc-cool) 14%, transparent);
    color: var(--hc-cool);
  }

  .hc-confirm-icon.is-danger {
    background: color-mix(in oklab, var(--hc-warn) 16%, transparent);
    color: var(--hc-warn);
  }

  .hc-confirm-text {
    flex: 1;
    min-width: 0;
    padding-top: 2px;
  }

  .hc-confirm-title {
    font-family: var(--hc-font-display);
    font-size: 17px;
    font-weight: 600;
    letter-spacing: -0.01em;
    margin: 0 0 4px 0;
    color: var(--hc-ink);
    line-height: 1.3;
  }

  .hc-confirm-message {
    font-size: 13.5px;
    line-height: 1.5;
    color: var(--hc-ink-2);
    margin: 0;
    word-wrap: break-word;
  }

  .hc-confirm-x {
    position: absolute;
    top: 12px;
    right: 12px;
    width: 26px;
    height: 26px;
    border: 0;
    background: transparent;
    color: var(--hc-ink-3);
    border-radius: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    transition: background 0.12s, color 0.12s;
  }

  .hc-confirm-x:hover {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink);
  }

  .hc-confirm-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 16px 20px 20px 20px;
  }

  .hc-confirm-btn {
    appearance: none;
    border: 1px solid transparent;
    border-radius: var(--hc-radius-sm, 10px);
    padding: 9px 16px;
    font-family: inherit;
    font-size: 13.5px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.12s, color 0.12s, border-color 0.12s, transform 0.06s;
    min-width: 88px;
  }

  .hc-confirm-btn:active {
    transform: translateY(1px);
  }

  .hc-confirm-btn:focus-visible {
    outline: 2px solid var(--hc-ink);
    outline-offset: 2px;
  }

  .hc-confirm-cancel {
    background: transparent;
    color: var(--hc-ink-2);
    border-color: var(--hc-line-strong);
  }

  .hc-confirm-cancel:hover {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink);
  }

  .hc-confirm-ok {
    background: var(--hc-ink);
    color: var(--hc-bg);
    border-color: var(--hc-ink);
  }

  .hc-confirm-ok:hover {
    background: var(--hc-ink-2);
    border-color: var(--hc-ink-2);
  }

  .hc-confirm-ok.is-danger {
    background: var(--hc-warn);
    color: #fff;
    border-color: var(--hc-warn);
  }

  .hc-confirm-ok.is-danger:hover {
    background: color-mix(in oklab, var(--hc-warn) 88%, black);
    border-color: color-mix(in oklab, var(--hc-warn) 88%, black);
  }

  .hc-confirm-ok.is-danger:focus-visible {
    outline-color: var(--hc-warn);
  }

  @media (max-width: 480px) {
    .hc-confirm {
      width: calc(100vw - 24px);
    }
    .hc-confirm-head {
      padding: 16px 16px 4px 16px;
      gap: 12px;
    }
    .hc-confirm-actions {
      padding: 12px 16px 16px 16px;
    }
    .hc-confirm-btn {
      flex: 1;
      min-width: 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .hc-confirm-scrim,
    .hc-confirm {
      animation: none;
    }
  }
</style>
