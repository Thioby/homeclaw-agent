<script lang="ts">
  import { get } from 'svelte/store';
  import { providerState } from '$lib/stores/providers';
  import type { AnalysisResult, OptimizationResult, ProgressEvent, ModelOption } from './types';
  import { getHass } from './rag-helpers';

  let {
    onMessage,
  }: {
    onMessage: (text: string, type: 'success' | 'error') => void;
  } = $props();

  let analysis = $state<AnalysisResult | null>(null);
  let analysisLoading = $state(false);
  let optimizeProvider = $state<string>('');
  let optimizeModel = $state<string>('');
  let optimizeScope = $state<'all' | 'sessions' | 'memories'>('all');
  let optimizeModels = $state<ModelOption[]>([]);
  let optimizeModelsLoading = $state(false);
  let optimizing = $state(false);
  let optimizeProgress = $state<ProgressEvent[]>([]);
  let optimizeResult = $state<OptimizationResult | null>(null);
  let optimizeProgressPct = $state(0);

  // Load on mount
  $effect(() => {
    if (!analysis) loadAnalysis();
  });

  async function loadAnalysis() {
    const hass = getHass();
    if (!hass) return;
    analysisLoading = true;
    analysis = null;
    try {
      analysis = await hass.callWS({ type: 'homeclaw/rag/optimize/analyze' });
    } catch (e) {
      console.error('[RagViewer] Failed to analyze:', e);
      onMessage('Analysis failed', 'error');
    } finally {
      analysisLoading = false;
    }
  }

  async function loadModelsForProvider(provider: string) {
    const hass = getHass();
    if (!hass || !provider) {
      optimizeModels = [];
      return;
    }
    optimizeModelsLoading = true;
    try {
      const result = await hass.callWS({
        type: 'homeclaw/models/list',
        provider,
      });
      optimizeModels = result.models || [];
      // Auto-select default model
      const defaultModel = optimizeModels.find((m: ModelOption) => (m as any).default);
      if (defaultModel) {
        optimizeModel = defaultModel.id;
      } else if (optimizeModels.length > 0) {
        optimizeModel = optimizeModels[0].id;
      }
    } catch (e) {
      console.error('[RagViewer] Failed to load models:', e);
      optimizeModels = [];
    } finally {
      optimizeModelsLoading = false;
    }
  }

  function handleProviderChange() {
    optimizeModel = '';
    if (optimizeProvider) {
      loadModelsForProvider(optimizeProvider);
    } else {
      optimizeModels = [];
    }
  }

  async function runOptimization() {
    const hass = getHass();
    if (!hass || !optimizeProvider || !optimizeModel) return;

    optimizing = true;
    optimizeProgress = [];
    optimizeResult = null;
    optimizeProgressPct = 0;

    try {
      let unsub: (() => void) | undefined;
      unsub = await hass.connection.subscribeMessage(
        (event: any) => {
          const progressEvent = event as ProgressEvent;
          optimizeProgress = [...optimizeProgress, progressEvent];
          if (progressEvent.progress !== undefined) {
            optimizeProgressPct = progressEvent.progress;
          }
          if (progressEvent.type === 'result') {
            optimizeResult = (event as any).data as OptimizationResult;
            optimizing = false;
            if (
              optimizeResult &&
              optimizeResult.errors &&
              optimizeResult.errors.length > 0
            ) {
              onMessage(`Completed with ${optimizeResult.errors.length} error(s)`, 'error');
            } else {
              onMessage('Optimization complete!', 'success');
            }
            loadAnalysis();
            if (unsub) unsub();
          }
        },
        {
          type: 'homeclaw/rag/optimize/run',
          provider: optimizeProvider,
          model: optimizeModel,
          scope: optimizeScope,
        }
      );
    } catch (e: any) {
      console.error('[RagViewer] Optimization error:', e);
      onMessage(e?.message || 'Optimization failed', 'error');
      optimizing = false;
      loadAnalysis();
    }
  }

  function getAvailableProviders() {
    return get(providerState).availableProviders || [];
  }
</script>

<div class="section">
  <p class="desc">
    Condense RAG data using an AI model. This reduces session chunks and merges duplicate memories
    while preserving important information.
  </p>

  <!-- Analysis -->
  {#if analysisLoading}
    <div class="loading">Analyzing RAG database...</div>
  {:else if analysis && analysis.initialized}
    <div class="card">
      <h3>Current Size</h3>
      <div class="kv-grid">
        <span class="k">Session chunks</span><span class="v"
          >{analysis.total_session_chunks}</span
        >
        <span class="k">Sessions</span><span class="v">{analysis.total_sessions}</span>
        <span class="k">Optimizable sessions</span><span class="v highlight"
          >{analysis.optimizable_sessions}</span
        >
        <span class="k">Storage</span><span class="v">{analysis.total_size_mb} MB</span>
        <span class="k">Memories</span><span class="v">{analysis.total_memories}</span>
      </div>
    </div>

    {#if analysis.potential_chunk_savings > 0 || analysis.potential_memory_savings > 0}
      <div class="card savings-card">
        <h3>Estimated Savings</h3>
        <div class="kv-grid">
          {#if analysis.potential_chunk_savings > 0}
            <span class="k">Chunks reducible</span>
            <span class="v savings"
              >~{analysis.potential_chunk_savings} chunks ({Math.round(
                (analysis.potential_chunk_savings / analysis.total_session_chunks) * 100
              )}%)</span
            >
          {/if}
          {#if analysis.potential_memory_savings > 0}
            <span class="k">Memories reducible</span>
            <span class="v savings"
              >~{analysis.potential_memory_savings} memories ({Math.round(
                (analysis.potential_memory_savings / analysis.total_memories) * 100
              )}%)</span
            >
          {/if}
        </div>
      </div>

      <!-- Provider/Model Selection -->
      <div class="card">
        <h3>Optimization Settings</h3>
        <div class="opt-form">
          <div class="form-row">
            <label for="opt-provider">Provider</label>
            <select
              id="opt-provider"
              class="filter-select"
              bind:value={optimizeProvider}
              onchange={handleProviderChange}
            >
              <option value="">Select provider...</option>
              {#each getAvailableProviders() as provider}
                <option value={provider.value}>{provider.label}</option>
              {/each}
            </select>
          </div>

          <div class="form-row">
            <label for="opt-model">Model</label>
            <select
              id="opt-model"
              class="filter-select"
              bind:value={optimizeModel}
              disabled={!optimizeProvider || optimizeModelsLoading}
            >
              {#if optimizeModelsLoading}
                <option value="">Loading models...</option>
              {:else if optimizeModels.length === 0}
                <option value="">Select provider first</option>
              {:else}
                {#each optimizeModels as model}
                  <option value={model.id}>{model.name}</option>
                {/each}
              {/if}
            </select>
          </div>

          <div class="form-row">
            <label for="opt-scope">Scope</label>
            <select id="opt-scope" class="filter-select" bind:value={optimizeScope}>
              <option value="all">All (sessions + memories)</option>
              <option value="sessions">Sessions only</option>
              <option value="memories">Memories only</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Run Button -->
      <button
        class="btn primary optimize-btn"
        onclick={runOptimization}
        disabled={optimizing || !optimizeProvider || !optimizeModel}
      >
        {#if optimizing}
          Optimizing...
        {:else}
          Run Optimization
        {/if}
      </button>
    {:else}
      <div class="card">
        <p class="no-savings">RAG database is already compact. No optimization needed.</p>
      </div>
    {/if}

    <!-- Progress -->
    {#if optimizing || optimizeProgress.length > 0}
      <div class="card progress-card">
        <h3>Progress</h3>
        {#if optimizing}
          <div class="progress-bar-container">
            <div class="progress-bar" style="width: {optimizeProgressPct}%"></div>
          </div>
        {/if}
        <div class="progress-log">
          {#each optimizeProgress as event}
            <div
              class="progress-line"
              class:phase={event.type === 'phase'}
              class:done={event.type === 'session_done' || event.type === 'category_done'}
              class:error-line={event.type === 'session_error' ||
                event.type === 'category_error'}
              class:complete={event.type === 'complete'}
            >
              {event.message}
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Result -->
    {#if optimizeResult}
      <div class="card result-card" class:has-errors={optimizeResult.errors.length > 0}>
        <h3>Optimization Result</h3>
        <div class="kv-grid">
          {#if optimizeResult.chunks_before > 0}
            <span class="k">Session chunks</span>
            <span class="v"
              >{optimizeResult.chunks_before} -> {optimizeResult.chunks_after}
              <span class="savings">(-{optimizeResult.chunks_saved})</span></span
            >
          {/if}
          {#if optimizeResult.memories_before > 0}
            <span class="k">Memories</span>
            <span class="v"
              >{optimizeResult.memories_before} -> {optimizeResult.memories_after}
              <span class="savings">(-{optimizeResult.memories_saved})</span></span
            >
          {/if}
          <span class="k">Duration</span><span class="v"
            >{optimizeResult.duration_seconds}s</span
          >
          <span class="k">Sessions processed</span><span class="v"
            >{optimizeResult.sessions_processed}</span
          >
        </div>
        {#if optimizeResult.errors.length > 0}
          <div class="error-list">
            <strong>Errors:</strong>
            {#each optimizeResult.errors as err}
              <div class="error-line">{err}</div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    <button class="btn text" onclick={loadAnalysis}>Refresh Analysis</button>
  {:else if analysis && !analysis.initialized}
    <div class="not-initialized">RAG system is not initialized.</div>
  {/if}
</div>

<style>
  .section {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .loading,
  .not-initialized {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
  }
  .desc {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }
  .card {
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 12px 16px;
  }
  .card h3 {
    margin: 0 0 8px 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--primary-text-color);
  }
  .kv-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 12px;
    font-size: 13px;
  }
  .k {
    color: var(--secondary-text-color);
  }
  .v {
    color: var(--primary-text-color);
    font-weight: 500;
  }
  .v.highlight {
    color: #ff9800;
    font-weight: 600;
  }
  .v.savings,
  .savings {
    color: #4caf50;
    font-weight: 600;
  }
  .savings-card {
    border: 1px solid rgba(76, 175, 80, 0.3);
  }
  .no-savings {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    text-align: center;
    padding: 8px 0;
  }
  .filter-select {
    padding: 6px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 6px;
    font-size: 13px;
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    font-family: inherit;
  }
  .opt-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .form-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .form-row label {
    min-width: 70px;
    font-size: 13px;
    color: var(--secondary-text-color);
    font-weight: 500;
  }
  .form-row .filter-select {
    flex: 1;
  }
  .btn {
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .btn.primary {
    background: var(--primary-color);
    color: white;
  }
  .btn.primary:hover:not(:disabled) {
    filter: brightness(1.1);
  }
  .btn.text {
    background: none;
    color: var(--primary-color);
    padding: 6px 8px;
  }
  .btn.text:hover {
    background: rgba(3, 169, 244, 0.08);
  }
  .optimize-btn {
    align-self: flex-start;
    padding: 10px 24px;
    font-size: 14px;
    background: #ff9800;
    border-color: #ff9800;
  }
  .optimize-btn:hover:not(:disabled) {
    background: #f57c00;
  }
  .progress-card {
    border: 1px solid rgba(3, 169, 244, 0.3);
  }
  .progress-bar-container {
    width: 100%;
    height: 6px;
    background: var(--divider-color);
    border-radius: 3px;
    margin-bottom: 8px;
    overflow: hidden;
  }
  .progress-bar {
    height: 100%;
    background: var(--primary-color);
    border-radius: 3px;
    transition: width 0.3s ease;
  }
  .progress-log {
    max-height: 150px;
    overflow-y: auto;
    font-size: 12px;
    color: var(--secondary-text-color);
    line-height: 1.6;
  }
  .progress-line {
    padding: 1px 0;
  }
  .progress-line.phase {
    color: var(--primary-color);
    font-weight: 600;
    margin-top: 4px;
  }
  .progress-line.done {
    color: #4caf50;
  }
  .progress-line.error-line {
    color: var(--error-color, #f44336);
  }
  .progress-line.complete {
    color: #4caf50;
    font-weight: 600;
    margin-top: 4px;
  }
  .result-card {
    border: 1px solid rgba(76, 175, 80, 0.3);
  }
  .result-card.has-errors {
    border-color: rgba(255, 152, 0, 0.3);
  }
  .error-list {
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid var(--divider-color);
    font-size: 12px;
  }
  .error-line {
    color: var(--error-color);
    padding: 2px 0;
  }
</style>
