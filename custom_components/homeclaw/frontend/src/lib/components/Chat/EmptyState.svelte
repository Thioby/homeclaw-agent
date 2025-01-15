<div class="empty-chat">
  <svg viewBox="0 0 24 24" class="icon">
    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
  </svg>
  <h3>Start a conversation</h3>
  <p>Ask your AI assistant about your Home Assistant setup, automations, or devices.</p>
</div>

<style>
  .empty-chat {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 32px;
    color: var(--secondary-text-color);
  }

  .icon {
    width: 64px;
    height: 64px;
    fill: var(--disabled-text-color);
    margin-bottom: 16px;
  }

  h3 {
    font-size: 18px;
    font-weight: 500;
    color: var(--primary-text-color);
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    margin-bottom: 24px;
    max-width: 300px;
  }
</style>
