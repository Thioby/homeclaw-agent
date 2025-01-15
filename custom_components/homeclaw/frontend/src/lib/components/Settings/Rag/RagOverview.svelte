<script lang="ts">
  import type { RagStats, IdentityForm } from './types';
  import { getHass } from './rag-helpers';

  let {
    stats,
    onRefresh,
    onMessage,
  }: {
    stats: RagStats;
    onRefresh: () => void;
    onMessage: (text: string, type: 'success' | 'error') => void;
  } = $props();

  // Identity editing
  let identityEditing = $state(false);
  let identityForm = $state<IdentityForm>({
    agent_name: '',
    agent_personality: '',
    agent_emoji: '',
    user_name: '',
    user_info: '',
    language: 'auto',
  });
  let identitySaving = $state(false);

  function startEditingIdentity() {
    if (stats?.identity) {
      identityForm = {
        agent_name: stats.identity.agent_name || '',
        agent_personality: stats.identity.agent_personality || '',
        agent_emoji: stats.identity.agent_emoji || '',
        user_name: stats.identity.user_name || '',
        user_info: stats.identity.user_info || '',
        language: stats.identity.language || 'auto',
      };
    }
    identityEditing = true;
  }

  function cancelEditingIdentity() {
    identityEditing = false;
  }

  async function saveIdentity() {
    const hass = getHass();
    if (!hass) return;
    identitySaving = true;
    try {
      await hass.callWS({
        type: 'homeclaw/rag/identity/update',
        ...identityForm,
      });
      identityEditing = false;
      onMessage('Identity saved', 'success');
      onRefresh();
    } catch (e: any) {
      onMessage(e?.message || 'Failed to save identity', 'error');
    } finally {
      identitySaving = false;
    }
  }
</script>

<div class="section">
  <!-- Identity -->
  {#if stats.identity}
    <div class="card">
      <div class="card-header">
        <h3>Agent Identity</h3>
        {#if !identityEditing}
          <button class="btn text btn-sm" onclick={startEditingIdentity}>Edit</button>
        {/if}
      </div>

      {#if identityEditing}
        <div class="identity-form">
          <div class="form-group">
            <label for="id-agent-name">Agent Name</label>
            <input
              id="id-agent-name"
              type="text"
              bind:value={identityForm.agent_name}
              placeholder="e.g. Jarvis"
            />
          </div>
          <div class="form-group">
            <label for="id-agent-personality">Personality</label>
            <textarea
              id="id-agent-personality"
              bind:value={identityForm.agent_personality}
              placeholder="e.g. Friendly, witty, concise"
              rows="2"
            ></textarea>
          </div>
          <div class="form-group">
            <label for="id-agent-emoji">Emoji</label>
            <input
              id="id-agent-emoji"
              type="text"
              bind:value={identityForm.agent_emoji}
              placeholder="e.g. 🤖"
              maxlength="4"
              class="emoji-input"
            />
          </div>
          <div class="form-group">
            <label for="id-user-name">Your Name</label>
            <input
              id="id-user-name"
              type="text"
              bind:value={identityForm.user_name}
              placeholder="e.g. Adam"
            />
          </div>
          <div class="form-group">
            <label for="id-user-info">About You</label>
            <textarea
              id="id-user-info"
              bind:value={identityForm.user_info}
              placeholder="e.g. Lives in Warsaw, works from home, has 2 cats"
              rows="3"
            ></textarea>
          </div>
          <div class="form-group">
            <label for="id-language">Language</label>
            <select id="id-language" bind:value={identityForm.language}>
              <option value="auto">Auto-detect</option>
              <option value="pl">Polski</option>
              <option value="en">English</option>
              <option value="de">Deutsch</option>
              <option value="fr">Français</option>
              <option value="es">Español</option>
              <option value="it">Italiano</option>
              <option value="nl">Nederlands</option>
              <option value="uk">Українська</option>
            </select>
          </div>
          <div class="form-actions">
            <button class="btn primary" onclick={saveIdentity} disabled={identitySaving}>
              {identitySaving ? 'Saving...' : 'Save'}
            </button>
            <button class="btn text" onclick={cancelEditingIdentity}>Cancel</button>
          </div>
        </div>
      {:else}
        <div class="kv-grid">
          <span class="k">Name</span><span class="v"
            >{stats.identity.agent_name || '-'} {stats.identity.agent_emoji || ''}</span
          >
          <span class="k">Personality</span><span class="v"
            >{stats.identity.agent_personality || '-'}</span
          >
          <span class="k">User</span><span class="v">{stats.identity.user_name || '-'}</span>
          <span class="k">Language</span><span class="v"
            >{stats.identity.language || 'auto'}</span
          >
          <span class="k">Onboarded</span><span class="v"
            >{stats.identity.onboarding_completed ? 'Yes' : 'No'}</span
          >
        </div>
      {/if}
    </div>
  {:else}
    <div class="card">
      <div class="card-header">
        <h3>Agent Identity</h3>
        <button class="btn text btn-sm" onclick={startEditingIdentity}>Set up</button>
      </div>
      <p class="desc">
        No identity configured yet. Click "Set up" to create one, or start a conversation to go
        through the onboarding flow.
      </p>
    </div>
  {/if}

  <!-- Entity stats -->
  {#if stats.stats}
    <div class="card">
      <h3>Entity Index</h3>
      <div class="kv-grid">
        <span class="k">Indexed entities</span><span class="v"
          >{stats.stats.indexed_entities ?? stats.stats.total_documents ?? '-'}</span
        >
        <span class="k">Embedding provider</span><span class="v"
          >{stats.stats.embedding_provider || '-'}</span
        >
        <span class="k">Dimensions</span><span class="v"
          >{stats.stats.embedding_dimensions || '-'}</span
        >
      </div>
    </div>

    <!-- Session stats -->
    {#if stats.stats.session_chunks}
      <div class="card">
        <h3>Session Index</h3>
        <div class="kv-grid">
          <span class="k">Total chunks</span><span class="v"
            >{stats.stats.session_chunks.total_chunks}</span
          >
          <span class="k">Indexed sessions</span><span class="v"
            >{stats.stats.session_chunks.indexed_sessions}</span
          >
          <span class="k">Storage</span><span class="v"
            >{stats.stats.session_chunks.total_mb} MB</span
          >
        </div>
      </div>
    {/if}
  {/if}

  <!-- Memory stats -->
  {#if stats.memory_stats}
    <div class="card">
      <h3>Memories</h3>
      <div class="kv-grid">
        <span class="k">Total</span><span class="v">{stats.memory_stats.total || 0}</span>
        {#if stats.memory_stats.categories}
          {#each Object.entries(stats.memory_stats.categories) as [cat, count]}
            <span class="k cat">{cat}</span><span class="v">{count}</span>
          {/each}
        {/if}
      </div>
    </div>

    <!-- Smart Memory / Source breakdown -->
    {#if stats.memory_stats.sources || stats.memory_stats.expiring_soon !== undefined}
      <div class="card smart-memory-card">
        <h3>Smart Memory</h3>
        <div class="kv-grid">
          {#if stats.memory_stats.sources}
            {#each Object.entries(stats.memory_stats.sources) as [src, count]}
              <span class="k source-label"
                >{src === 'agent'
                  ? 'Agent (proactive)'
                  : src === 'auto'
                    ? 'Auto-captured'
                    : src === 'user'
                      ? 'User/tool'
                      : src}</span
              >
              <span class="v" class:highlight={src === 'agent'}>{count}</span>
            {/each}
          {/if}
          {#if stats.memory_stats.total_with_ttl}
            <span class="k">With TTL (ephemeral)</span>
            <span class="v">{stats.memory_stats.total_with_ttl}</span>
          {/if}
          {#if stats.memory_stats.expiring_soon}
            <span class="k">Expiring within 3 days</span>
            <span class="v expiring-count">{stats.memory_stats.expiring_soon}</span>
          {/if}
        </div>
      </div>
    {/if}
  {/if}

  <button class="btn text" onclick={onRefresh}>Refresh</button>
</div>

<style>
  .section {
    display: flex;
    flex-direction: column;
    gap: 10px;
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
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  .card-header h3 {
    margin: 0;
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
  .k.cat {
    text-transform: capitalize;
    padding-left: 12px;
  }
  .v {
    color: var(--primary-text-color);
    font-weight: 500;
  }
  .v.highlight {
    color: #ff9800;
    font-weight: 600;
  }
  .desc {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.5;
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
  .btn-sm {
    font-size: 12px;
    padding: 3px 8px;
  }

  /* Identity form */
  .identity-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .form-group label {
    font-size: 12px;
    color: var(--secondary-text-color);
    font-weight: 500;
  }
  .form-group input,
  .form-group textarea,
  .form-group select {
    padding: 7px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 6px;
    font-size: 13px;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: inherit;
    resize: vertical;
  }
  .form-group input:focus,
  .form-group textarea:focus,
  .form-group select:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.15);
  }
  .emoji-input {
    width: 60px;
    text-align: center;
    font-size: 18px;
  }
  .form-actions {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }

  /* Smart Memory card */
  .smart-memory-card {
    border: 1px solid rgba(103, 58, 183, 0.25);
  }
  .source-label {
    text-transform: capitalize;
  }
  .v.expiring-count {
    color: #ff9800;
    font-weight: 600;
  }
</style>
