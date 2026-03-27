<script lang="ts">
  import { confirmDashboardAction } from '$lib/services/websocket.service';

  let {
    action,
    status = 'preview',
    toolResult,
    toolCallId,
    sessionId,
    hass,
    onStatusChange,
  }: {
    action: 'create' | 'update' | 'delete';
    status: 'preview' | 'confirmed' | 'success' | 'error' | 'rejected';
    toolResult: any;
    toolCallId: string;
    sessionId: string;
    hass: any;
    onStatusChange: (newStatus: string) => void;
  } = $props();

  const title = $derived(toolResult?.title || toolResult?.dashboard_url || 'Dashboard');
  const viewCount = $derived(
    toolResult?.preview
      ? (toolResult.preview.match(/^  - title:/gm) || []).length
      : toolResult?.views?.length || 0
  );

  const actionLabels: Record<string, string> = {
    create: 'Create Dashboard',
    update: 'Update Dashboard',
    delete: 'Delete Dashboard',
  };

  const actionIcons: Record<string, string> = {
    create: '+',
    update: '✎',
    delete: '✕',
  };

  const statusMessages: Record<string, string> = {
    confirmed: 'Confirming...',
    success: action === 'delete' ? 'Deleted' : action === 'update' ? 'Updated' : 'Created',
    error: 'Error',
    rejected: 'Cancelled',
  };

  async function handleConfirm() {
    onStatusChange('confirmed');
    try {
      const res = await confirmDashboardAction(hass, toolCallId, sessionId, true);
      onStatusChange(res.status === 'success' ? 'success' : 'error');
    } catch (e) {
      console.error('Dashboard confirm failed:', e);
      onStatusChange('error');
    }
  }

  function handleReject() {
    confirmDashboardAction(hass, toolCallId, sessionId, false).catch(() => {});
    onStatusChange('rejected');
  }
</script>

<div
  class="dashboard-action"
  class:delete={action === 'delete'}
  class:collapsed={status !== 'preview'}
>
  <div class="da-header">
    <span class="da-icon">{actionIcons[action]}</span>
    <span class="da-title">{actionLabels[action]}: "{title}"</span>
    {#if status !== 'preview'}
      <span
        class="da-status"
        class:success={status === 'success'}
        class:error={status === 'error'}
      >
        {statusMessages[status] || status}
        {#if status === 'success'}✓{/if}
        {#if status === 'confirmed'}<span class="da-spinner"></span>{/if}
      </span>
    {/if}
  </div>

  {#if status === 'preview'}
    {#if viewCount > 0}
      <div class="da-stats">Views: {viewCount}</div>
    {/if}

    {#if toolResult?.preview || toolResult?.new_config}
      <details open>
        <summary>Show YAML preview</summary>
        <div class="da-yaml">
          {#if action === 'update' && toolResult?.current_config}
            <div class="da-yaml-label">Current:</div>
            <pre><code>{toolResult.current_config}</code></pre>
            <div class="da-yaml-label">New:</div>
          {/if}
          <pre><code>{toolResult.preview || toolResult.new_config}</code></pre>
        </div>
      </details>
    {/if}

    <div class="da-buttons">
      <button
        class="da-btn da-btn-confirm"
        class:da-btn-danger={action === 'delete'}
        onclick={handleConfirm}
      >
        Zatwierdź
      </button>
      <button class="da-btn da-btn-reject" onclick={handleReject}>Odrzuć</button>
    </div>
  {/if}
</div>

<style>
  .dashboard-action {
    margin-top: 8px;
    border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    border-radius: 8px;
    padding: 10px 12px;
    background: var(--bubble-code-bg, rgba(0, 0, 0, 0.04));
    font-size: 13px;
  }
  .dashboard-action.delete {
    border-color: rgba(244, 67, 54, 0.4);
  }
  .dashboard-action.collapsed {
    padding: 8px 12px;
  }
  .da-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 500;
  }
  .da-icon {
    font-size: 14px;
    opacity: 0.7;
  }
  .da-title {
    flex: 1;
  }
  .da-status {
    font-size: 12px;
    opacity: 0.8;
  }
  .da-status.success {
    color: #4caf50;
  }
  .da-status.error {
    color: #f44336;
  }
  .da-stats {
    margin-top: 4px;
    font-size: 12px;
    opacity: 0.7;
  }
  details {
    margin-top: 8px;
  }
  summary {
    cursor: pointer;
    font-size: 12px;
    opacity: 0.7;
    user-select: none;
  }
  .da-yaml {
    margin-top: 6px;
    max-height: 300px;
    overflow-y: auto;
  }
  .da-yaml pre {
    margin: 0;
    padding: 8px;
    background: var(--bubble-code-bg, rgba(0, 0, 0, 0.06));
    border-radius: 4px;
    font-size: 12px;
    line-height: 1.4;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .da-yaml-label {
    font-size: 11px;
    font-weight: 600;
    margin-top: 6px;
    margin-bottom: 2px;
    opacity: 0.6;
  }
  .da-buttons {
    display: flex;
    gap: 8px;
    margin-top: 10px;
  }
  .da-btn {
    padding: 6px 16px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    font-weight: 500;
  }
  .da-btn-confirm {
    background: #4caf50;
    color: white;
  }
  .da-btn-confirm:hover {
    background: #43a047;
  }
  .da-btn-danger {
    background: #f44336;
  }
  .da-btn-danger:hover {
    background: #e53935;
  }
  .da-btn-reject {
    background: var(--divider-color, rgba(0, 0, 0, 0.08));
    color: var(--primary-text-color, #333);
  }
  .da-btn-reject:hover {
    background: rgba(0, 0, 0, 0.15);
  }
  .da-spinner {
    display: inline-block;
    width: 12px;
    height: 12px;
    border: 2px solid rgba(0, 0, 0, 0.1);
    border-top-color: currentColor;
    border-radius: 50%;
    animation: da-spin 0.6s linear infinite;
    vertical-align: middle;
    margin-left: 4px;
  }
  @keyframes da-spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
