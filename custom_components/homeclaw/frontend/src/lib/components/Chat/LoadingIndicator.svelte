<!-- Telegram-style typing indicator bubble -->
<div class="typing-indicator">
  <div class="typing-bubble">
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
  </div>
</div>

<style>
  .typing-indicator {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 3px;
    animation: messageAppear 0.3s ease-out;
  }

  .typing-bubble {
    background: var(--bubble-assistant, var(--card-background-color));
    padding: 12px 16px;
    border-radius: 12px 12px 12px 4px;
    display: flex;
    align-items: center;
    gap: 4px;
    position: relative;
  }

  /* Tail on left side, matching assistant bubble */
  .typing-bubble::after {
    content: '';
    position: absolute;
    left: -8px;
    bottom: 0;
    width: 0;
    height: 0;
    border: 8px solid transparent;
    border-right-color: var(--bubble-assistant-tail, var(--card-background-color));
    border-bottom-color: var(--bubble-assistant-tail, var(--card-background-color));
    border-left: 0;
    border-bottom-left-radius: 4px;
  }

  .typing-dot {
    width: 7px;
    height: 7px;
    background: var(--secondary-text-color);
    border-radius: 50%;
    animation: typingBounce 1.4s infinite ease-in-out;
  }

  .typing-dot:nth-child(2) {
    animation-delay: 0.2s;
  }

  .typing-dot:nth-child(3) {
    animation-delay: 0.4s;
  }

  @keyframes typingBounce {
    0%, 60%, 100% {
      transform: translateY(0);
      opacity: 0.4;
    }
    30% {
      transform: translateY(-5px);
      opacity: 1;
    }
  }

  @keyframes messageAppear {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
