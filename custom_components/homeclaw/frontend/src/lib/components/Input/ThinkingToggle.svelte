<script lang="ts">
  import { appState } from '$lib/stores/appState';

  function toggle() {
    appState.update(s => ({ ...s, showThinking: !s.showThinking }));
  }
</script>

<label class="thinking-toggle">
  <input
    type="checkbox"
    checked={$appState.showThinking}
    onchange={toggle}
  />
  <span class="label">Debug Mode</span>
</label>

<style>
  .thinking-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
    font-size: 14px;
  }

  input[type="checkbox"] {
    cursor: pointer;
    width: 18px;
    height: 18px;
  }

  .label {
    color: var(--secondary-text-color);
    font-weight: 500;
  }

  @media (max-width: 768px) {
    .label {
      display: none;
    }
  }
</style>
