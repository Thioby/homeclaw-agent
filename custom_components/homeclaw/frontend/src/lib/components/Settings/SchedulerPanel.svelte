<script lang="ts">
  import { getHass } from './Rag/rag-helpers';

  interface ScheduledJob {
    job_id: string;
    name: string;
    enabled: boolean;
    cron: string;
    prompt: string;
    provider: string | null;
    notify: boolean;
    one_shot: boolean;
    created_by: string;
    next_run: string | null;
    last_run: string | null;
    last_status: string;
    last_error: string;
    created_at: number;
  }

  interface SchedulerStatus {
    total_jobs: number;
    enabled_jobs: number;
    active_timers: number;
    recent_runs: number;
  }

  interface RunHistoryEntry {
    job_id: string;
    job_name: string;
    timestamp: number;
    status: string;
    response: string;
    error: string;
    duration_ms: number;
  }

  let jobs = $state<ScheduledJob[]>([]);
  let status = $state<SchedulerStatus | null>(null);
  let history = $state<RunHistoryEntry[]>([]);
  let loading = $state(false);
  let available = $state(true);
  let runningJobId = $state<string | null>(null);

  let message = $state<string | null>(null);
  let messageType = $state<'success' | 'error'>('success');

  let activeSection = $state<'jobs' | 'history'>('jobs');

  $effect(() => {
    loadJobs();
  });

  function showMessage(text: string, type: 'success' | 'error') {
    message = text;
    messageType = type;
    setTimeout(() => (message = null), 3000);
  }

  async function loadJobs() {
    const hass = getHass();
    if (!hass) return;
    loading = true;
    try {
      const result: any = await hass.callWS({ type: 'homeclaw/scheduler/list' });
      available = result.available !== false;
      jobs = result.jobs || [];
      status = result.status || null;
    } catch (e) {
      console.error('[Scheduler] Failed to load:', e);
      available = false;
    } finally {
      loading = false;
    }
  }

  async function loadHistory() {
    const hass = getHass();
    if (!hass) return;
    try {
      const result: any = await hass.callWS({
        type: 'homeclaw/scheduler/history',
        limit: 50,
      });
      history = (result.history || []).reverse();
    } catch (e) {
      console.error('[Scheduler] Failed to load history:', e);
    }
  }

  async function toggleJob(jobId: string, enabled: boolean) {
    const hass = getHass();
    if (!hass) return;
    try {
      await hass.callWS({
        type: 'homeclaw/scheduler/enable',
        job_id: jobId,
        enabled,
      });
      showMessage(enabled ? 'Job enabled' : 'Job disabled', 'success');
      await loadJobs();
    } catch (e: any) {
      showMessage(e.message || 'Failed to toggle job', 'error');
      await loadJobs();
    }
  }

  async function removeJob(jobId: string, jobName: string) {
    if (!confirm(`Remove "${jobName}"?`)) return;
    const hass = getHass();
    if (!hass) return;
    try {
      await hass.callWS({
        type: 'homeclaw/scheduler/remove',
        job_id: jobId,
      });
      showMessage('Job removed', 'success');
      await loadJobs();
    } catch (e: any) {
      showMessage(e.message || 'Failed to remove job', 'error');
    }
  }

  async function runJobNow(jobId: string) {
    const hass = getHass();
    if (!hass) return;
    runningJobId = jobId;
    try {
      const result: any = await hass.callWS({
        type: 'homeclaw/scheduler/run',
        job_id: jobId,
      });
      const run = result.run;
      if (run?.status === 'ok') {
        showMessage('Job executed successfully', 'success');
      } else {
        showMessage(run?.error || 'Job failed', 'error');
      }
      await loadJobs();
    } catch (e: any) {
      showMessage(e.message || 'Failed to run job', 'error');
    } finally {
      runningJobId = null;
    }
  }

  function handleSectionChange(section: 'jobs' | 'history') {
    activeSection = section;
    if (section === 'history') {
      loadHistory();
    }
  }

  function formatDate(isoOrTimestamp: string | number | null): string {
    if (!isoOrTimestamp) return '-';
    const d =
      typeof isoOrTimestamp === 'number'
        ? new Date(isoOrTimestamp * 1000)
        : new Date(isoOrTimestamp);
    if (isNaN(d.getTime())) return '-';
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (isToday) return time;
    const day = d.getDate();
    const month = d.toLocaleString('default', { month: 'short' });
    return `${day} ${month}, ${time}`;
  }

  function describeCron(cron: string): string {
    const parts = cron.split(' ');
    if (parts.length !== 5) return cron;
    const [min, hour, dom, mon, dow] = parts;

    // Specific date (one-shot style)
    if (dom !== '*' && mon !== '*') {
      return `${hour}:${min.padStart(2, '0')} on ${dom}/${mon}`;
    }
    // Every N minutes
    if (min.startsWith('*/')) return `Every ${min.slice(2)} min`;
    // Every N hours
    if (hour.startsWith('*/') && min === '0') return `Every ${hour.slice(2)}h`;
    // Daily at HH:MM
    if (dom === '*' && mon === '*' && dow === '*') {
      return `Daily at ${hour}:${min.padStart(2, '0')}`;
    }
    // Weekly
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    if (dow !== '*' && dom === '*') {
      const dayName = dayNames[parseInt(dow)] || dow;
      return `${dayName} at ${hour}:${min.padStart(2, '0')}`;
    }
    // Monthly
    if (dom !== '*' && mon === '*') {
      return `${dom}th of month at ${hour}:${min.padStart(2, '0')}`;
    }
    return cron;
  }
</script>

<div class="scheduler-panel">
  {#if message}
    <div class="msg" class:error={messageType === 'error'}>{message}</div>
  {/if}

  <div class="section-nav">
    <button
      class="pill"
      class:active={activeSection === 'jobs'}
      onclick={() => handleSectionChange('jobs')}>Jobs</button
    >
    <button
      class="pill"
      class:active={activeSection === 'history'}
      onclick={() => handleSectionChange('history')}>History</button
    >
    <button class="pill refresh-pill" onclick={loadJobs} title="Refresh">Refresh</button>
  </div>

  {#if loading && !jobs.length}
    <div class="loading">Loading scheduler...</div>
  {:else if !available}
    <div class="not-available">
      Scheduler is not initialized. It starts automatically with the integration.
    </div>
  {:else if activeSection === 'jobs'}
    {#if status}
      <div class="status-bar">
        <span>{status.total_jobs} jobs</span>
        <span class="dot">&#183;</span>
        <span>{status.enabled_jobs} enabled</span>
        <span class="dot">&#183;</span>
        <span>{status.active_timers} timers</span>
      </div>
    {/if}

    {#if jobs.length === 0}
      <div class="empty">
        No scheduled jobs yet. Ask the assistant to create one, e.g.
        <em>"Remind me to check energy at 8pm every day"</em>
      </div>
    {:else}
      <div class="jobs-list">
        {#each jobs as job (job.job_id)}
          <div class="job-card" class:disabled={!job.enabled}>
            <div class="job-header">
              <div class="job-title-row">
                <span class="job-name">{job.name}</span>
                {#if job.one_shot}
                  <span class="badge one-shot">once</span>
                {/if}
                <span class="badge" class:agent={job.created_by === 'agent'}>
                  {job.created_by}
                </span>
              </div>
              <label class="toggle">
                <input
                  type="checkbox"
                  checked={job.enabled}
                  onchange={() => toggleJob(job.job_id, !job.enabled)}
                />
                <span class="slider"></span>
              </label>
            </div>

            <div class="job-meta">
              <span class="cron" title={job.cron}>{describeCron(job.cron)}</span>
              {#if job.next_run && job.enabled}
                <span class="next-run">Next: {formatDate(job.next_run)}</span>
              {/if}
            </div>

            <div class="job-prompt">{job.prompt}</div>

            {#if job.last_run}
              <div class="job-last-run">
                <span
                  class="status-dot"
                  class:ok={job.last_status === 'ok'}
                  class:error={job.last_status === 'error'}
                ></span>
                Last: {formatDate(job.last_run)}
                {#if job.last_error}
                  <span class="last-error" title={job.last_error}>failed</span>
                {/if}
              </div>
            {/if}

            <div class="job-actions">
              <button
                class="action-btn run"
                onclick={() => runJobNow(job.job_id)}
                disabled={runningJobId === job.job_id}
              >
                {runningJobId === job.job_id ? 'Running...' : 'Run now'}
              </button>
              <button class="action-btn delete" onclick={() => removeJob(job.job_id, job.name)}>
                Remove
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {:else if activeSection === 'history'}
    {#if history.length === 0}
      <div class="empty">No run history yet.</div>
    {:else}
      <div class="history-list">
        {#each history as run}
          <div class="history-item" class:error={run.status === 'error'}>
            <div class="history-header">
              <span class="history-name">{run.job_name}</span>
              <span class="history-time">{formatDate(run.timestamp)}</span>
            </div>
            <div class="history-detail">
              <span
                class="status-dot"
                class:ok={run.status === 'ok'}
                class:error={run.status === 'error'}
              ></span>
              <span class="history-status">{run.status}</span>
              {#if run.duration_ms}
                <span class="history-duration">{(run.duration_ms / 1000).toFixed(1)}s</span>
              {/if}
            </div>
            {#if run.error}
              <div class="history-error">{run.error}</div>
            {/if}
            {#if run.response}
              <div class="history-response">{run.response.slice(0, 200)}</div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  .scheduler-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .msg {
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    background: rgba(76, 175, 80, 0.1);
    color: #4caf50;
    border: 1px solid rgba(76, 175, 80, 0.3);
  }
  .msg.error {
    background: rgba(244, 67, 54, 0.1);
    color: var(--error-color);
    border-color: rgba(244, 67, 54, 0.3);
  }

  .section-nav {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .pill {
    padding: 6px 14px;
    border: 1px solid var(--divider-color);
    border-radius: 20px;
    background: var(--secondary-background-color);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
    color: var(--primary-text-color);
  }
  .pill.active {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
  }
  .pill:hover:not(.active) {
    background: var(--card-background-color);
  }
  .pill.refresh-pill {
    margin-left: auto;
    border-color: rgba(33, 150, 243, 0.4);
  }

  .loading,
  .not-available,
  .empty {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
    line-height: 1.5;
  }
  .empty em {
    display: block;
    margin-top: 8px;
    opacity: 0.7;
    font-size: 13px;
  }

  .status-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--secondary-text-color);
    padding: 4px 0;
  }
  .dot {
    font-size: 16px;
  }

  .jobs-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .job-card {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 10px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: opacity 0.2s;
  }
  .job-card.disabled {
    opacity: 0.55;
  }

  .job-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
  }
  .job-title-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .job-name {
    font-weight: 600;
    font-size: 14px;
    color: var(--primary-text-color);
  }

  .badge {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 10px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .badge.agent {
    background: rgba(33, 150, 243, 0.15);
    color: #2196f3;
  }
  .badge.one-shot {
    background: rgba(255, 152, 0, 0.15);
    color: #ff9800;
  }

  .job-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
    color: var(--secondary-text-color);
  }
  .cron {
    font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
    background: var(--secondary-background-color);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 11px;
  }
  .next-run {
    color: var(--primary-color);
  }

  .job-prompt {
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .job-last-run {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--secondary-text-color);
  }
  .last-error {
    color: var(--error-color);
    font-weight: 500;
  }

  .status-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--secondary-text-color);
    flex-shrink: 0;
  }
  .status-dot.ok {
    background: #4caf50;
  }
  .status-dot.error {
    background: #f44336;
  }

  .job-actions {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }
  .action-btn {
    padding: 5px 12px;
    border: 1px solid var(--divider-color);
    border-radius: 6px;
    background: var(--secondary-background-color);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
    color: var(--primary-text-color);
  }
  .action-btn:hover {
    background: var(--card-background-color);
  }
  .action-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .action-btn.run {
    border-color: rgba(33, 150, 243, 0.4);
    color: #2196f3;
  }
  .action-btn.run:hover {
    background: rgba(33, 150, 243, 0.1);
  }
  .action-btn.delete {
    border-color: rgba(244, 67, 54, 0.3);
    color: #f44336;
  }
  .action-btn.delete:hover {
    background: rgba(244, 67, 54, 0.1);
  }

  /* Toggle switch */
  .toggle {
    position: relative;
    display: inline-block;
    width: 36px;
    height: 20px;
    flex-shrink: 0;
  }
  .toggle input {
    opacity: 0;
    width: 0;
    height: 0;
  }
  .slider {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background: var(--divider-color);
    border-radius: 20px;
    transition: 0.2s;
  }
  .slider::before {
    content: '';
    position: absolute;
    height: 14px;
    width: 14px;
    left: 3px;
    bottom: 3px;
    background: white;
    border-radius: 50%;
    transition: 0.2s;
  }
  .toggle input:checked + .slider {
    background: var(--primary-color);
  }
  .toggle input:checked + .slider::before {
    transform: translateX(16px);
  }

  /* History */
  .history-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .history-item {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .history-item.error {
    border-color: rgba(244, 67, 54, 0.3);
  }
  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .history-name {
    font-weight: 600;
    font-size: 13px;
    color: var(--primary-text-color);
  }
  .history-time {
    font-size: 11px;
    color: var(--secondary-text-color);
  }
  .history-detail {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--secondary-text-color);
  }
  .history-status {
    text-transform: uppercase;
    font-weight: 500;
    font-size: 11px;
  }
  .history-duration {
    opacity: 0.7;
  }
  .history-error {
    font-size: 12px;
    color: var(--error-color);
    margin-top: 2px;
  }
  .history-response {
    font-size: 12px;
    color: var(--secondary-text-color);
    line-height: 1.4;
    opacity: 0.8;
    margin-top: 2px;
  }
</style>
