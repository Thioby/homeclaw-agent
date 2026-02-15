const appCss = `/* Global styles for Homeclaw Panel */

:host {
  /* Home Assistant Theme Variables */
  --primary-color: var(--ha-primary-color, #03a9f4);
  --accent-color: var(--ha-accent-color, #ff9800);
  --primary-background-color: var(--ha-primary-background-color, #fafafa);
  --secondary-background-color: var(--ha-secondary-background-color, #e5e5e5);
  --divider-color: var(--ha-divider-color, rgba(0, 0, 0, 0.12));
  --primary-text-color: var(--ha-primary-text-color, #212121);
  --secondary-text-color: var(--ha-secondary-text-color, #727272);
  --disabled-text-color: var(--ha-disabled-text-color, #bdbdbd);
  --sidebar-background-color: var(--ha-sidebar-background-color, #fafafa);
  --sidebar-text-color: var(--ha-sidebar-text-color, #212121);
  --card-background-color: var(--ha-card-background-color, #fff);
  --mdc-theme-primary: var(--primary-color);
  --mdc-theme-on-primary: white;
  --error-color: #db4437;
  --success-color: #0f9d58;
  --warning-color: #f4b400;

  /* Telegram-inspired Chat Variables (defaults for system/HA theme) */
  --accent: var(--primary-color);
  --accent-hover: color-mix(in srgb, var(--primary-color) 85%, black);
  --accent-light: color-mix(in srgb, var(--primary-color) 12%, transparent);

  --bg-chat: var(--primary-background-color);
  --bg-chat-pattern: rgba(0, 0, 0, 0.02);
  --bg-sidebar: var(--secondary-background-color);
  --bg-input: var(--card-background-color);
  --bg-hover: rgba(0, 0, 0, 0.04);
  --bg-active: color-mix(in srgb, var(--primary-color) 12%, transparent);
  --bg-overlay: rgba(0, 0, 0, 0.4);

  --bubble-user: color-mix(in srgb, var(--primary-color) 15%, var(--card-background-color));
  --bubble-user-tail: var(--bubble-user);
  --bubble-assistant: var(--card-background-color);
  --bubble-assistant-tail: var(--bubble-assistant);
  --bubble-code-bg: var(--secondary-background-color);

  --text-bubble-user: var(--primary-text-color);
  --text-bubble-assistant: var(--primary-text-color);
  --text-bubble-time: rgba(0, 0, 0, 0.35);
  --text-bubble-time-user: rgba(0, 0, 0, 0.4);

  --search-bg: var(--secondary-background-color);
  --search-text: var(--secondary-text-color);

  --scrollbar-thumb: rgba(0, 0, 0, 0.15);
  --scrollbar-track: transparent;

  --fab-shadow: 0 4px 16px color-mix(in srgb, var(--primary-color) 35%, transparent);

  /* Sidebar width */
  --sidebar-width: 320px;

  /* Spacing */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;

  /* Border Radius */
  --border-radius-sm: 4px;
  --border-radius-md: 8px;
  --border-radius-lg: 12px;
  --border-radius-xl: 16px;

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
  --shadow-md: 0 3px 6px rgba(0, 0, 0, 0.16), 0 3px 6px rgba(0, 0, 0, 0.23);
  --shadow-lg: 0 10px 20px rgba(0, 0, 0, 0.19), 0 6px 6px rgba(0, 0, 0, 0.23);

  /* Transitions */
  --transition-fast: 150ms ease-in-out;
  --transition-medium: 250ms ease-in-out;
  --transition-slow: 350ms ease-in-out;

  /* Z-index layers */
  --z-sidebar: 100;
  --z-dropdown: 200;
  --z-modal: 300;
  --z-overlay: 400;
  --z-toast: 500;
}

/* Reset & Base Styles */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:host {
  display: block;
  width: 100%;
  height: 100%;
  font-family: var(--ha-font-family, Roboto, sans-serif);
  font-size: 14px;
  line-height: 1.5;
  color: var(--primary-text-color);
  background-color: var(--primary-background-color);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* =======================================================================
   TELEGRAM-INSPIRED LIGHT THEME (forced override)
   Applied when data-theme="light" is set on :host
   ======================================================================= */
:host([data-theme="light"]) {
  --primary-background-color: #FFFFFF;
  --secondary-background-color: #F4F4F5;
  --card-background-color: #FFFFFF;
  --divider-color: #E0E0E0;
  --primary-text-color: #000000;
  --secondary-text-color: #707579;
  --disabled-text-color: #9E9E9E;

  --accent: #2AABEE;
  --accent-hover: #229ED9;
  --accent-light: rgba(42, 171, 238, 0.12);

  --bg-chat: #E6EBEE;
  --bg-chat-pattern: rgba(0, 0, 0, 0.02);
  --bg-sidebar: #FFFFFF;
  --bg-input: #FFFFFF;
  --bg-hover: rgba(0, 0, 0, 0.04);
  --bg-active: rgba(42, 171, 238, 0.12);
  --bg-overlay: rgba(0, 0, 0, 0.4);

  --bubble-user: #EFFDDE;
  --bubble-user-tail: #EFFDDE;
  --bubble-assistant: #FFFFFF;
  --bubble-assistant-tail: #FFFFFF;
  --bubble-code-bg: #F0F2F5;

  --text-bubble-user: #000000;
  --text-bubble-assistant: #000000;
  --text-bubble-time: rgba(0, 0, 0, 0.35);
  --text-bubble-time-user: rgba(0, 100, 0, 0.45);

  --search-bg: #F0F2F5;
  --search-text: #707579;
  --scrollbar-thumb: rgba(0, 0, 0, 0.15);
  --fab-shadow: 0 4px 16px rgba(42, 171, 238, 0.35);
}

/* =======================================================================
   TELEGRAM-INSPIRED DARK THEME (forced override)
   Applied when data-theme="dark" is set on :host
   ======================================================================= */
:host([data-theme="dark"]) {
  --primary-background-color: #0E1621;
  --secondary-background-color: #17212B;
  --card-background-color: #17212B;
  --divider-color: #1F2F3F;
  --primary-text-color: #F5F5F5;
  --secondary-text-color: #8696A8;
  --disabled-text-color: #5B6F82;

  --accent: #2AABEE;
  --accent-hover: #229ED9;
  --accent-light: rgba(42, 171, 238, 0.15);

  --bg-chat: #0E1621;
  --bg-chat-pattern: rgba(255, 255, 255, 0.01);
  --bg-sidebar: #17212B;
  --bg-input: #17212B;
  --bg-hover: rgba(255, 255, 255, 0.05);
  --bg-active: rgba(42, 171, 238, 0.15);
  --bg-overlay: rgba(0, 0, 0, 0.6);

  --bubble-user: #2B5278;
  --bubble-user-tail: #2B5278;
  --bubble-assistant: #182533;
  --bubble-assistant-tail: #182533;
  --bubble-code-bg: #0E1621;

  --text-bubble-user: #F5F5F5;
  --text-bubble-assistant: #F5F5F5;
  --text-bubble-time: rgba(255, 255, 255, 0.4);
  --text-bubble-time-user: rgba(255, 255, 255, 0.45);

  --search-bg: #242F3D;
  --search-text: #8696A8;
  --scrollbar-thumb: rgba(255, 255, 255, 0.12);
  --fab-shadow: 0 4px 16px rgba(42, 171, 238, 0.25);
}

/* Scrollbar Styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--scrollbar-track);
  border-radius: var(--border-radius-sm);
}

::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: var(--border-radius-sm);
  transition: background var(--transition-fast);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--secondary-text-color);
}

/* Focus Styles */
:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

button:focus-visible,
a:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* Animations */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideInUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes slideInLeft {
  from {
    transform: translateX(-20px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideInRight {
  from {
    transform: translateX(20px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes bounce {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes shimmer {
  0% {
    background-position: -468px 0;
  }
  100% {
    background-position: 468px 0;
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

@keyframes emptyPulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 var(--accent-light);
  }
  50% {
    transform: scale(1.03);
    box-shadow: 0 0 0 16px transparent;
  }
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

/* Theme transition smoothing */
:host(.theme-transitioning),
:host(.theme-transitioning) * {
  transition-duration: 0.3s !important;
}

/* Utility Classes */
.fade-in {
  animation: fadeIn var(--transition-medium);
}

.slide-in-up {
  animation: slideInUp var(--transition-medium);
}

.slide-in-left {
  animation: slideInLeft var(--transition-medium);
}

.slide-in-right {
  animation: slideInRight var(--transition-medium);
}

/* Markdown Content Styling */
.markdown-content {
  line-height: 1.6;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
  margin-top: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
  font-weight: 600;
  color: var(--primary-text-color);
}

.markdown-content h1 {
  font-size: 1.5em;
}
.markdown-content h2 {
  font-size: 1.3em;
}
.markdown-content h3 {
  font-size: 1.1em;
}

.markdown-content p {
  margin-bottom: var(--spacing-sm);
}

.markdown-content ul,
.markdown-content ol {
  margin-left: var(--spacing-lg);
  margin-bottom: var(--spacing-sm);
}

.markdown-content li {
  margin-bottom: var(--spacing-xs);
}

.markdown-content code {
  background: var(--secondary-background-color);
  padding: 2px 6px;
  border-radius: var(--border-radius-sm);
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9em;
}

.markdown-content pre {
  background: var(--secondary-background-color);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  overflow-x: auto;
  margin-bottom: var(--spacing-sm);
}

.markdown-content pre code {
  background: none;
  padding: 0;
}

.markdown-content blockquote {
  border-left: 4px solid var(--primary-color);
  padding-left: var(--spacing-md);
  margin-left: 0;
  margin-bottom: var(--spacing-sm);
  color: var(--secondary-text-color);
  font-style: italic;
}

.markdown-content a {
  color: var(--primary-color);
  text-decoration: none;
  transition: opacity var(--transition-fast);
}

.markdown-content a:hover {
  opacity: 0.8;
  text-decoration: underline;
}

.markdown-content table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: var(--spacing-sm);
}

.markdown-content th,
.markdown-content td {
  border: 1px solid var(--divider-color);
  padding: var(--spacing-sm);
  text-align: left;
}

.markdown-content th {
  background: var(--secondary-background-color);
  font-weight: 600;
}

.markdown-content img {
  max-width: 100%;
  height: auto;
  border-radius: var(--border-radius-sm);
  margin-bottom: var(--spacing-sm);
}

/* Responsive Breakpoints */
@media (max-width: 768px) {
  :host {
    font-size: 13px;
  }
}

@media (prefers-color-scheme: dark) {
  /* Dark mode adjustments are handled by HA theme variables */
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Selection */
::selection {
  background-color: var(--primary-color);
  color: white;
}
`;
const componentCss = `
  .header.svelte-1elxaub {
    height: 54px;
    min-height: 54px;
    background: var(--bg-sidebar, var(--secondary-background-color));
    color: var(--primary-text-color);
    border-bottom: 1px solid var(--divider-color);
    display: flex;
    align-items: center;
    padding: 0 8px;
    gap: 8px;
    position: relative;
    z-index: 100;
    transition: background var(--transition-medium, 250ms), border-color var(--transition-medium, 250ms);
  }

  .header-btn.svelte-1elxaub {
    width: 40px;
    height: 40px;
    border: none;
    background: transparent;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--secondary-text-color);
    transition: background 0.15s, color 0.15s;
    flex-shrink: 0;
    padding: 0;
  }

  .header-btn.svelte-1elxaub:hover {
    background: var(--bg-hover, rgba(0, 0, 0, 0.04));
    color: var(--primary-text-color);
  }

  .header-btn.svelte-1elxaub svg:where(.svelte-1elxaub) {
    width: 22px;
    height: 22px;
  }

  /* Back/hamburger button - hidden on desktop */
  .back-btn.svelte-1elxaub {
    display: none;
  }

  .header-avatar.svelte-1elxaub {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--accent, #2AABEE), var(--accent-hover, #229ED9));
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    flex-shrink: 0;
  }

  .header-avatar.svelte-1elxaub svg:where(.svelte-1elxaub) {
    width: 22px;
    height: 22px;
  }

  .header-info.svelte-1elxaub {
    flex: 1;
    min-width: 0;
  }

  .header-title.svelte-1elxaub {
    font-size: 15px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.2;
  }

  .header-subtitle.svelte-1elxaub {
    font-size: 12.5px;
    color: var(--accent, var(--primary-color));
    line-height: 1.2;
  }

  .header-actions.svelte-1elxaub {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }

  .delete-btn.svelte-1elxaub:hover {
    color: var(--error-color, #db4437);
  }

  .delete-btn.svelte-1elxaub:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  @media (max-width: 768px) {
    .back-btn.svelte-1elxaub {
      display: flex;
    }

    .header-avatar.svelte-1elxaub {
      width: 36px;
      height: 36px;
    }

    .header-avatar.svelte-1elxaub svg:where(.svelte-1elxaub) {
      width: 18px;
      height: 18px;
    }

    .header-title.svelte-1elxaub {
      font-size: 14px;
    }
  }

  .session-item.svelte-114uzds {
    display: flex;
    align-items: center;
    padding: 9px 12px;
    gap: 12px;
    cursor: pointer;
    transition: background 0.15s;
    position: relative;
  }

  .session-item.svelte-114uzds:hover {
    background: var(--bg-hover, rgba(0, 0, 0, 0.04));
  }

  .session-item.active.svelte-114uzds {
    background: var(--bg-active, rgba(42, 171, 238, 0.12));
  }

  .session-avatar.svelte-114uzds {
    width: 50px;
    height: 50px;
    min-width: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #fff;
    flex-shrink: 0;
    position: relative;
  }

  .voice-badge.svelte-114uzds {
    position: absolute;
    bottom: -1px;
    right: -1px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--primary-color, #03a9f4);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    border: 2px solid var(--card-background-color, #fff);
  }

  .voice-badge.svelte-114uzds svg:where(.svelte-114uzds) {
    width: 10px;
    height: 10px;
  }

  .session-content.svelte-114uzds {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .session-top-row.svelte-114uzds {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
  }

  .session-name.svelte-114uzds {
    font-size: 15px;
    font-weight: 500;
    color: var(--primary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .session-time.svelte-114uzds {
    font-size: 12px;
    color: var(--disabled-text-color);
    flex-shrink: 0;
  }

  .session-item.active.svelte-114uzds .session-time:where(.svelte-114uzds) {
    color: var(--accent, var(--primary-color));
  }

  .session-bottom-row.svelte-114uzds {
    display: flex;
    align-items: center;
  }

  .session-preview.svelte-114uzds {
    font-size: 13.5px;
    color: var(--secondary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .session-delete.svelte-114uzds {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 30px;
    height: 30px;
    border: none;
    background: transparent;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.15s, background 0.15s;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    color: var(--secondary-text-color);
  }

  .session-item.svelte-114uzds:hover .session-delete:where(.svelte-114uzds) {
    opacity: 1;
  }

  .session-delete.svelte-114uzds:hover {
    background: rgba(219, 68, 55, 0.12);
    color: var(--error-color, #db4437);
  }

  .session-delete.svelte-114uzds svg:where(.svelte-114uzds) {
    width: 16px;
    height: 16px;
  }

  .session-list.svelte-1j5qstn {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 0;
  }

  /* Scrollbar styling */
  .session-list.svelte-1j5qstn::-webkit-scrollbar {
    width: 6px;
  }

  .session-list.svelte-1j5qstn::-webkit-scrollbar-track {
    background: transparent;
  }

  .session-list.svelte-1j5qstn::-webkit-scrollbar-thumb {
    background-color: var(--scrollbar-thumb, var(--divider-color));
    border-radius: 3px;
  }

  .session-list.svelte-1j5qstn::-webkit-scrollbar-thumb:hover {
    background-color: var(--secondary-text-color);
  }

  /* Empty state */
  .empty-sessions.svelte-1j5qstn {
    text-align: center;
    padding: 32px 16px;
    color: var(--secondary-text-color);
  }

  .empty-sessions.svelte-1j5qstn .icon:where(.svelte-1j5qstn) {
    width: 48px;
    height: 48px;
    fill: var(--disabled-text-color);
    margin-bottom: 12px;
  }

  .empty-sessions.svelte-1j5qstn p:where(.svelte-1j5qstn) {
    margin: 0;
    font-size: 14px;
  }

  /* Loading skeleton */
  .session-skeleton.svelte-1j5qstn {
    padding: 9px 12px;
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .session-skeleton.svelte-1j5qstn::before {
    content: '';
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: linear-gradient(
      90deg,
      var(--divider-color) 25%,
      var(--card-background-color, #fff) 50%,
      var(--divider-color) 75%
    );
    background-size: 200% 100%;
    animation: svelte-1j5qstn-skeleton-shimmer 1.5s infinite;
    flex-shrink: 0;
  }

  .skeleton-line.svelte-1j5qstn {
    height: 14px;
    background: linear-gradient(
      90deg,
      var(--divider-color) 25%,
      var(--card-background-color, #fff) 50%,
      var(--divider-color) 75%
    );
    background-size: 200% 100%;
    animation: svelte-1j5qstn-skeleton-shimmer 1.5s infinite;
    border-radius: 4px;
    margin-bottom: 6px;
  }

  .skeleton-line.short.svelte-1j5qstn {
    width: 60%;
    height: 12px;
  }

  .skeleton-line.tiny.svelte-1j5qstn {
    width: 40%;
    height: 10px;
  }

  @keyframes svelte-1j5qstn-skeleton-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  .fab.svelte-19p7jpv {
    position: absolute;
    bottom: 20px;
    right: 20px;
    width: 54px;
    height: 54px;
    border-radius: 50%;
    background: var(--accent, var(--primary-color));
    color: #fff;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: var(--fab-shadow, 0 4px 16px rgba(3, 169, 244, 0.35));
    transition: transform 0.15s, box-shadow 0.15s, background 0.15s;
    z-index: 5;
  }

  .fab.svelte-19p7jpv:hover:not(:disabled) {
    transform: scale(1.05);
    background: var(--accent-hover, var(--primary-color));
  }

  .fab.svelte-19p7jpv:active:not(:disabled) {
    transform: scale(0.95);
  }

  .fab.svelte-19p7jpv:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .fab.svelte-19p7jpv svg:where(.svelte-19p7jpv) {
    width: 24px;
    height: 24px;
  }

  .sidebar.svelte-ou1367 {
    width: var(--sidebar-width, 320px);
    min-width: var(--sidebar-width, 320px);
    height: 100%;
    background: var(--bg-sidebar, var(--secondary-background-color));
    border-right: 1px solid var(--divider-color);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), background 0.25s ease;
    position: relative;
    z-index: 10;
  }

  .sidebar.hidden.svelte-ou1367 {
    transform: translateX(-100%);
    width: 0;
    min-width: 0;
    border: none;
    overflow: hidden;
  }

  .search-container.svelte-ou1367 {
    padding: 10px 12px;
  }

  .search-bar.svelte-ou1367 {
    display: flex;
    align-items: center;
    background: var(--search-bg, var(--secondary-background-color));
    border-radius: 24px;
    padding: 8px 14px;
    gap: 10px;
    transition: background 0.2s, box-shadow 0.15s;
    cursor: text;
  }

  .search-bar.svelte-ou1367:focus-within {
    box-shadow: 0 0 0 2px var(--accent, var(--primary-color));
    background: var(--card-background-color, #fff);
  }

  .search-bar.svelte-ou1367 svg:where(.svelte-ou1367) {
    width: 18px;
    height: 18px;
    color: var(--search-text, var(--secondary-text-color));
    flex-shrink: 0;
  }

  .search-bar.svelte-ou1367 input:where(.svelte-ou1367) {
    border: none;
    outline: none;
    background: transparent;
    font-size: 14px;
    color: var(--primary-text-color);
    width: 100%;
    font-family: inherit;
  }

  .search-bar.svelte-ou1367 input:where(.svelte-ou1367)::placeholder {
    color: var(--search-text, var(--secondary-text-color));
  }

  .sidebar-overlay.svelte-ou1367 {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--bg-overlay, rgba(0, 0, 0, 0.4));
    z-index: 99;
    opacity: 0;
    transition: opacity 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  }

  @media (max-width: 768px) {
    .sidebar.svelte-ou1367 {
      position: fixed;
      left: 0;
      top: 0;
      bottom: 0;
      z-index: 100;
      transform: translateX(-100%);
      width: 85vw;
      min-width: 85vw;
      max-width: 360px;
      box-shadow: none;
    }

    .sidebar.open.svelte-ou1367 {
      transform: translateX(0);
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.16);
    }

    .sidebar.hidden.svelte-ou1367 {
      transform: translateX(-100%);
    }

    .sidebar-overlay.svelte-ou1367 {
      display: block;
      opacity: 1;
    }
  }

  @media (max-width: 1024px) and (min-width: 769px) {
    .sidebar.svelte-ou1367 {
      width: 260px;
      min-width: 260px;
    }
  }

  .message.svelte-cu3vo4 {
    display: flex;
    margin-bottom: 3px;
    animation: messageAppear 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }

  /* Group spacing: different sender = more space */
  .message.user + .message.assistant,
  .message.assistant + .message.user {
    margin-top: 10px;
  }

  .message.user.svelte-cu3vo4 {
    justify-content: flex-end;
  }

  .message.assistant.svelte-cu3vo4 {
    justify-content: flex-start;
  }

  .bubble.svelte-cu3vo4 {
    max-width: min(80%, 500px);
    padding: 7px 11px;
    position: relative;
    line-height: 1.45;
    word-wrap: break-word;
    overflow-wrap: break-word;
    overflow: hidden;
  }

  /* User bubble -- right side, Telegram-style */
  .message.user.svelte-cu3vo4 .bubble:where(.svelte-cu3vo4) {
    background: var(--bubble-user);
    color: var(--text-bubble-user);
    border-radius: 12px 12px 4px 12px;
  }

  /* User bubble tail (CSS triangle) */
  .message.user.svelte-cu3vo4 .bubble:where(.svelte-cu3vo4)::after {
    content: '';
    position: absolute;
    right: -8px;
    bottom: 0;
    width: 0;
    height: 0;
    border: 8px solid transparent;
    border-left-color: var(--bubble-user-tail);
    border-bottom-color: var(--bubble-user-tail);
    border-right: 0;
    border-bottom-right-radius: 4px;
  }

  /* Hide tail on consecutive same-type messages */
  .message.user + .message.user .bubble::after {
    display: none;
  }

  /* Assistant bubble -- left side */
  .message.assistant.svelte-cu3vo4 .bubble:where(.svelte-cu3vo4) {
    background: var(--bubble-assistant);
    color: var(--text-bubble-assistant);
    border-radius: 12px 12px 12px 4px;
  }

  /* Assistant bubble tail */
  .message.assistant.svelte-cu3vo4 .bubble:where(.svelte-cu3vo4)::after {
    content: '';
    position: absolute;
    left: -8px;
    bottom: 0;
    width: 0;
    height: 0;
    border: 8px solid transparent;
    border-right-color: var(--bubble-assistant-tail);
    border-bottom-color: var(--bubble-assistant-tail);
    border-left: 0;
    border-bottom-left-radius: 4px;
  }

  .message.assistant + .message.assistant .bubble::after {
    display: none;
  }

  /* Timestamp INSIDE bubble -- Telegram style */
  .bubble-time.svelte-cu3vo4 {
    float: right;
    font-size: 11px;
    margin: 4px -4px -2px 12px;
    color: var(--text-bubble-time);
    white-space: nowrap;
  }

  .message.user.svelte-cu3vo4 .bubble-time:where(.svelte-cu3vo4) {
    color: var(--text-bubble-time-user);
  }

  /* --- Attachments --- */
  .attachments.svelte-cu3vo4 {
    margin-bottom: 6px;
  }

  .image-attachments.svelte-cu3vo4 {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 4px;
  }

  .attached-image.svelte-cu3vo4 {
    max-width: 260px;
    max-height: 200px;
    border-radius: 8px;
    object-fit: contain;
    cursor: pointer;
    display: block;
  }

  .image-placeholder.svelte-cu3vo4 {
    width: 120px;
    height: 80px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.06);
    border-radius: 8px;
    gap: 4px;
  }

  .image-placeholder.svelte-cu3vo4 svg:where(.svelte-cu3vo4) {
    width: 24px;
    height: 24px;
    fill: var(--secondary-text-color);
  }

  .image-placeholder.svelte-cu3vo4 span:where(.svelte-cu3vo4) {
    font-size: 10px;
    color: var(--secondary-text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100px;
  }

  .file-attachments.svelte-cu3vo4 {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 4px;
  }

  .file-chip.svelte-cu3vo4 {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: rgba(0, 0, 0, 0.06);
    border-radius: 8px;
    font-size: 12px;
    max-width: 200px;
  }

  .message.user.svelte-cu3vo4 .file-chip:where(.svelte-cu3vo4) {
    background: rgba(255, 255, 255, 0.15);
  }

  .file-icon.svelte-cu3vo4 {
    width: 16px;
    height: 16px;
    min-width: 16px;
    fill: currentColor;
    opacity: 0.7;
  }

  .file-name.svelte-cu3vo4 {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
  }

  .file-size.svelte-cu3vo4 {
    opacity: 0.6;
    white-space: nowrap;
    font-size: 11px;
  }

  /* Bubble content formatting (from markdown) */
  .bubble.svelte-cu3vo4 p {
    margin-bottom: 6px;
  }
  .bubble.svelte-cu3vo4 p:last-of-type {
    margin-bottom: 0;
  }
  .bubble.svelte-cu3vo4 strong {
    font-weight: 600;
  }
  .bubble.svelte-cu3vo4 code {
    background: var(--bubble-code-bg);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 13px;
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  }
  .bubble.svelte-cu3vo4 pre {
    background: var(--bubble-code-bg);
    border-radius: 8px;
    padding: 10px 12px;
    margin: 6px 0;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.4;
  }
  .bubble.svelte-cu3vo4 pre code {
    background: none;
    padding: 0;
    font-size: 13px;
  }
  .bubble.svelte-cu3vo4 ul,
  .bubble.svelte-cu3vo4 ol {
    padding-left: 18px;
    margin: 4px 0;
  }
  .bubble.svelte-cu3vo4 li {
    margin: 2px 0;
  }

  /* Streaming cursor */
  .streaming-cursor.svelte-cu3vo4 {
    display: inline-block;
    margin-left: 2px;
    animation: svelte-cu3vo4-blink 1s infinite;
    color: var(--accent, var(--primary-color));
    font-weight: bold;
  }

  @keyframes svelte-cu3vo4-blink {
    0%,
    50% {
      opacity: 1;
    }
    51%,
    100% {
      opacity: 0;
    }
  }

  .message.streaming.svelte-cu3vo4 {
    animation: messageAppear 0.3s ease-out;
  }

  @media (max-width: 768px) {
    .bubble.svelte-cu3vo4 {
      max-width: min(88%, 500px);
    }
  }

  @media (max-width: 400px) {
    .bubble.svelte-cu3vo4 {
      max-width: 92%;
      font-size: 13.5px;
    }
  }

  .typing-indicator.svelte-174ds4q {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 3px;
    animation: svelte-174ds4q-messageAppear 0.3s ease-out;
  }

  .typing-bubble.svelte-174ds4q {
    background: var(--bubble-assistant, var(--card-background-color));
    padding: 12px 16px;
    border-radius: 12px 12px 12px 4px;
    display: flex;
    align-items: center;
    gap: 4px;
    position: relative;
  }

  /* Tail on left side, matching assistant bubble */
  .typing-bubble.svelte-174ds4q::after {
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

  .typing-dot.svelte-174ds4q {
    width: 7px;
    height: 7px;
    background: var(--secondary-text-color);
    border-radius: 50%;
    animation: svelte-174ds4q-typingBounce 1.4s infinite ease-in-out;
  }

  .typing-dot.svelte-174ds4q:nth-child(2) {
    animation-delay: 0.2s;
  }

  .typing-dot.svelte-174ds4q:nth-child(3) {
    animation-delay: 0.4s;
  }

  @keyframes svelte-174ds4q-typingBounce {
    0%, 60%, 100% {
      transform: translateY(0);
      opacity: 0.4;
    }
    30% {
      transform: translateY(-5px);
      opacity: 1;
    }
  }

  @keyframes svelte-174ds4q-messageAppear {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .empty-state.svelte-euh035 {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px;
    z-index: 1;
  }

  .empty-icon.svelte-euh035 {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: var(--accent-light, rgba(3, 169, 244, 0.12));
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
    animation: svelte-euh035-emptyPulse 3s ease-in-out infinite;
  }

  .empty-icon.svelte-euh035 svg:where(.svelte-euh035) {
    width: 48px;
    height: 48px;
    color: var(--accent, var(--primary-color));
  }

  .empty-icon.svelte-euh035 .emoji-icon:where(.svelte-euh035) {
    font-size: 48px;
    line-height: 1;
  }

  @keyframes svelte-euh035-emptyPulse {
    0%, 100% {
      transform: scale(1);
      box-shadow: 0 0 0 0 var(--accent-light, rgba(3, 169, 244, 0.15));
    }
    50% {
      transform: scale(1.03);
      box-shadow: 0 0 0 16px transparent;
    }
  }

  h2.svelte-euh035 {
    font-size: 22px;
    font-weight: 600;
    color: var(--primary-text-color);
    margin-bottom: 8px;
  }

  p.svelte-euh035 {
    color: var(--secondary-text-color);
    font-size: 15px;
    max-width: 360px;
    line-height: 1.5;
    margin-bottom: 0;
  }

  .suggestions.svelte-euh035 {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 24px;
    justify-content: center;
    max-width: 480px;
  }

  .suggestion-chip.svelte-euh035 {
    padding: 8px 16px;
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color);
    border-radius: 9999px;
    font-size: 13.5px;
    color: var(--primary-text-color);
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .suggestion-chip.svelte-euh035:hover {
    border-color: var(--accent, var(--primary-color));
    color: var(--accent, var(--primary-color));
    background: var(--accent-light, rgba(3, 169, 244, 0.08));
  }

  @media (max-width: 768px) {
    .suggestions.svelte-euh035 {
      flex-direction: column;
      align-items: center;
    }

    .empty-icon.svelte-euh035 {
      width: 80px;
      height: 80px;
    }

    .empty-icon.svelte-euh035 svg:where(.svelte-euh035) {
      width: 40px;
      height: 40px;
    }

    h2.svelte-euh035 {
      font-size: 20px;
    }
  }

  .error.svelte-sualbq {
    color: var(--error-color);
    padding: 12px 16px;
    margin: 8px 16px;
    border-radius: 8px;
    background: rgba(219, 68, 55, 0.1);
    border: 1px solid var(--error-color);
    animation: svelte-sualbq-fadeIn 0.3s ease-out;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
  }

  .icon.svelte-sualbq {
    width: 20px;
    height: 20px;
    fill: var(--error-color);
    flex-shrink: 0;
  }

  .error-message.svelte-sualbq {
    flex: 1;
  }

  .error-dismiss.svelte-sualbq {
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .error-dismiss.svelte-sualbq:hover {
    background: rgba(219, 68, 55, 0.2);
  }

  .close-icon.svelte-sualbq {
    width: 18px;
    height: 18px;
    fill: var(--error-color);
  }

  @keyframes svelte-sualbq-fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .chat-wrapper.svelte-hiq0w4 {
    position: relative;
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .messages.svelte-hiq0w4 {
    overflow-y: auto;
    padding: 8px 0;
    background: var(--bg-chat, var(--primary-background-color));
    flex-grow: 1;
    width: 100%;
    display: flex;
    flex-direction: column;
    position: relative;
    transition: background var(--transition-medium, 250ms ease-in-out);
  }

  /* Subtle Telegram-style wallpaper pattern */
  .messages.svelte-hiq0w4::before {
    content: '';
    position: absolute;
    inset: 0;
    opacity: 0.5;
    background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%239C92AC' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
  }

  .messages-inner.svelte-hiq0w4 {
    max-width: 720px;
    width: 100%;
    margin: 0 auto;
    padding: 0 12px;
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
  }

  /* Scrollbar styling */
  .messages.svelte-hiq0w4::-webkit-scrollbar {
    width: 6px;
  }

  .messages.svelte-hiq0w4::-webkit-scrollbar-track {
    background: transparent;
  }

  .messages.svelte-hiq0w4::-webkit-scrollbar-thumb {
    background-color: var(--scrollbar-thumb, var(--divider-color));
    border-radius: 3px;
  }

  .messages.svelte-hiq0w4::-webkit-scrollbar-thumb:hover {
    background-color: var(--secondary-text-color);
  }

  /* Scroll to bottom button */
  .scroll-bottom-btn.svelte-hiq0w4 {
    position: absolute;
    bottom: 16px;
    right: 20px;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color);
    color: var(--secondary-text-color);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 5;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transition: transform 0.15s, opacity 0.15s;
    animation: svelte-hiq0w4-fadeIn 0.2s ease-out;
  }

  .scroll-bottom-btn.svelte-hiq0w4:hover {
    transform: scale(1.1);
  }

  .scroll-bottom-btn.svelte-hiq0w4 svg:where(.svelte-hiq0w4) {
    width: 20px;
    height: 20px;
  }

  @keyframes svelte-hiq0w4-fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @media (max-width: 768px) {
    .messages-inner.svelte-hiq0w4 {
      padding: 0 8px;
    }
  }

  @media (min-width: 1400px) {
    .messages-inner.svelte-hiq0w4 {
      max-width: 820px;
    }
  }

  .input-wrapper.svelte-5grvz8 {
    flex-grow: 1;
    position: relative;
    transition: background 0.15s ease;
    border-radius: 8px;
  }

  .input-wrapper.drag-over.svelte-5grvz8 {
    background: var(--accent-light, rgba(3, 169, 244, 0.08));
  }

  textarea.svelte-5grvz8 {
    width: 100%;
    min-height: 24px;
    max-height: 160px;
    padding: 8px 12px;
    border: none;
    outline: none;
    resize: none;
    font-size: 14px;
    line-height: 1.45;
    background: transparent;
    color: var(--primary-text-color);
    font-family: inherit;
  }

  textarea.svelte-5grvz8::placeholder {
    color: var(--search-text, var(--secondary-text-color));
  }

  textarea.svelte-5grvz8:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .drop-overlay.svelte-5grvz8 {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--accent-light, rgba(3, 169, 244, 0.12));
    border-radius: 8px;
    border: 2px dashed var(--accent, var(--primary-color));
    pointer-events: none;
  }

  .drop-label.svelte-5grvz8 {
    font-size: 13px;
    font-weight: 500;
    color: var(--accent, var(--primary-color));
  }

  .provider-selector.svelte-6zrmqv {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .provider-label.svelte-6zrmqv {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin-right: 8px;
  }

  .provider-button.svelte-6zrmqv {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: var(--secondary-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: var(--primary-text-color);
    transition: all 0.2s ease;
    min-width: 150px;
    appearance: none;
    background-image: url('data:image/svg+xml;charset=US-ASCII,<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7 10l5 5 5-5H7z" fill="currentColor"/></svg>');
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 30px;
  }

  .provider-button.svelte-6zrmqv:hover {
    background-color: var(--primary-background-color);
    border-color: var(--primary-color);
  }

  .provider-button.svelte-6zrmqv:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
  }

  .no-providers.svelte-6zrmqv {
    color: var(--error-color);
    font-size: 14px;
    padding: 8px;
  }

  @media (max-width: 768px) {
    .provider-label.svelte-6zrmqv {
      display: none;
    }

    .provider-button.svelte-6zrmqv {
      width: 44px;
      min-width: 44px;
      height: 44px;
      padding: 4px;
      font-size: 0;
      border-radius: 50%;
    }
  }

  .provider-selector.svelte-1whqbkb {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .provider-label.svelte-1whqbkb {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin-right: 8px;
  }

  .provider-button.svelte-1whqbkb {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: var(--secondary-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: var(--primary-text-color);
    transition: all 0.2s ease;
    min-width: 150px;
    appearance: none;
    background-image: url('data:image/svg+xml;charset=US-ASCII,<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7 10l5 5 5-5H7z" fill="currentColor"/></svg>');
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 30px;
  }

  .provider-button.svelte-1whqbkb:hover {
    background-color: var(--primary-background-color);
    border-color: var(--primary-color);
  }

  .provider-button.svelte-1whqbkb:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
  }

  .default-star.svelte-1whqbkb {
    color: #ffc107;
    font-size: 14px;
    line-height: 1;
    flex-shrink: 0;
  }

  @media (max-width: 768px) {
    .provider-label.svelte-1whqbkb {
      display: none;
    }
  }

  .send-button.svelte-1lpj1oh {
    --mdc-theme-primary: var(--accent, var(--primary-color));
    --mdc-theme-on-primary: var(--text-primary-color);
    width: 38px;
    height: 38px;
    min-width: 38px;
    border: none;
    border-radius: 50%;
    background: var(--accent, var(--primary-color));
    color: white;
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    flex-shrink: 0;
  }

  .icon.svelte-1lpj1oh {
    width: 20px;
    height: 20px;
    fill: white;
  }

  .send-button.svelte-1lpj1oh:hover:not(:disabled) {
    transform: scale(1.08);
    background: var(--accent-hover, var(--primary-color));
  }

  .send-button.svelte-1lpj1oh:active:not(:disabled) {
    transform: scale(0.92);
  }

  .send-button.svelte-1lpj1oh:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  @media (max-width: 768px) {
    .send-button.svelte-1lpj1oh {
      width: 40px;
      height: 40px;
      min-width: 40px;
    }
  }

  .thinking-toggle.svelte-1ahnk03 {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
    font-size: 14px;
  }

  input[type="checkbox"].svelte-1ahnk03 {
    cursor: pointer;
    width: 18px;
    height: 18px;
  }

  .label.svelte-1ahnk03 {
    color: var(--secondary-text-color);
    font-weight: 500;
  }

  @media (max-width: 768px) {
    .label.svelte-1ahnk03 {
      display: none;
    }
  }

  .hidden-input.svelte-nfbktg {
    display: none;
  }

  .attach-button.svelte-nfbktg {
    width: 32px;
    height: 32px;
    min-width: 32px;
    border: none;
    border-radius: 50%;
    background: transparent;
    color: var(--secondary-text-color);
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    flex-shrink: 0;
  }

  .icon.svelte-nfbktg {
    width: 20px;
    height: 20px;
    fill: currentColor;
  }

  .attach-button.svelte-nfbktg:hover:not(:disabled) {
    background: var(--divider-color);
    color: var(--primary-text-color);
  }

  .attach-button.svelte-nfbktg:active:not(:disabled) {
    transform: scale(0.92);
  }

  .attach-button.svelte-nfbktg:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .attachment-preview.svelte-fchx1w {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 12px 4px;
  }

  .attachment-item.svelte-fchx1w {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
    border-radius: 10px;
    border: 1px solid var(--divider-color);
    max-width: 200px;
    min-width: 0;
    overflow: hidden;
    transition: border-color 0.15s ease;
  }

  .attachment-item.is-image.svelte-fchx1w {
    padding: 4px;
    max-width: 120px;
    flex-direction: column;
  }

  .attachment-item.is-error.svelte-fchx1w {
    border-color: var(--error-color, #f44336);
    background: rgba(244, 67, 54, 0.08);
  }

  .thumbnail.svelte-fchx1w {
    width: 100%;
    max-height: 80px;
    object-fit: cover;
    border-radius: 6px;
  }

  .file-icon.svelte-fchx1w {
    width: 28px;
    height: 28px;
    min-width: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--divider-color);
    border-radius: 6px;
    padding: 4px;
  }

  .file-icon.pdf.svelte-fchx1w {
    background: rgba(244, 67, 54, 0.12);
    color: #f44336;
  }

  .file-icon.svelte-fchx1w svg:where(.svelte-fchx1w) {
    width: 20px;
    height: 20px;
    fill: currentColor;
  }

  .attachment-info.svelte-fchx1w {
    display: flex;
    flex-direction: column;
    min-width: 0;
    flex: 1;
  }

  .filename.svelte-fchx1w {
    font-size: 12px;
    font-weight: 500;
    color: var(--primary-text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .is-image.svelte-fchx1w .filename:where(.svelte-fchx1w) {
    font-size: 11px;
    text-align: center;
  }

  .filesize.svelte-fchx1w {
    font-size: 11px;
    color: var(--secondary-text-color);
  }

  .is-image.svelte-fchx1w .filesize:where(.svelte-fchx1w) {
    display: none;
  }

  .remove-btn.svelte-fchx1w {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 20px;
    height: 20px;
    border: none;
    border-radius: 50%;
    background: var(--secondary-text-color);
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    transition: background 0.15s ease;
    z-index: 1;
  }

  .remove-btn.svelte-fchx1w:hover {
    background: var(--error-color, #f44336);
  }

  .remove-btn.svelte-fchx1w svg:where(.svelte-fchx1w) {
    width: 14px;
    height: 14px;
    fill: currentColor;
  }

  .status-overlay.svelte-fchx1w {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.7);
    border-radius: 10px;
  }

  .spinner.svelte-fchx1w {
    width: 20px;
    height: 20px;
    border: 2px solid var(--divider-color);
    border-top-color: var(--accent, var(--primary-color));
    border-radius: 50%;
    animation: svelte-fchx1w-spin 0.8s linear infinite;
  }

  @keyframes svelte-fchx1w-spin {
    to {
      transform: rotate(360deg);
    }
  }

  .input-container.svelte-f7ebxa {
    position: relative;
    width: 100%;
    background: var(--bg-input, var(--card-background-color));
    border: 1px solid var(--divider-color);
    border-radius: 24px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
    margin: 0 auto 12px;
    max-width: 720px;
    overflow: hidden;
    transition:
      border-color var(--transition-fast, 150ms ease-in-out),
      box-shadow var(--transition-fast, 150ms ease-in-out);
  }

  .input-container.svelte-f7ebxa:focus-within {
    border-color: var(--accent, var(--primary-color));
    box-shadow: 0 0 0 2px var(--accent-light, rgba(3, 169, 244, 0.1));
  }

  .input-main.svelte-f7ebxa {
    display: flex;
    align-items: flex-end;
    padding: 8px 12px;
    gap: 8px;
  }

  .input-footer.svelte-f7ebxa {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 14px 10px;
    border-top: 1px solid var(--divider-color);
    gap: 8px;
  }

  @media (max-width: 768px) {
    .input-container.svelte-f7ebxa {
      border-radius: 20px;
      margin-bottom: 8px;
      margin-left: 6px;
      margin-right: 6px;
    }

    .input-footer.svelte-f7ebxa {
      gap: 6px;
      padding: 4px 10px 8px;
    }
  }

  @media (min-width: 1400px) {
    .input-container.svelte-f7ebxa {
      max-width: 820px;
    }
  }

  .thinking-panel.svelte-wqn4rm {
    border: 1px dashed var(--divider-color);
    border-radius: 10px;
    padding: 10px 12px;
    margin: 12px 0;
    background: var(--secondary-background-color);
  }

  .thinking-header.svelte-wqn4rm {
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    gap: 10px;
  }

  .thinking-title.svelte-wqn4rm {
    font-weight: 600;
    color: var(--primary-text-color);
    font-size: 14px;
  }

  .thinking-subtitle.svelte-wqn4rm {
    display: block;
    font-size: 12px;
    color: var(--secondary-text-color);
    margin-top: 2px;
    font-weight: normal;
  }

  .icon.svelte-wqn4rm {
    width: 20px;
    height: 20px;
    fill: var(--secondary-text-color);
    flex-shrink: 0;
  }

  .thinking-body.svelte-wqn4rm {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-height: 240px;
    overflow-y: auto;
  }

  .thinking-body.svelte-wqn4rm::-webkit-scrollbar {
    width: 6px;
  }

  .thinking-body.svelte-wqn4rm::-webkit-scrollbar-track {
    background: transparent;
  }

  .thinking-body.svelte-wqn4rm::-webkit-scrollbar-thumb {
    background-color: var(--divider-color);
    border-radius: 3px;
  }

  .thinking-entry.svelte-wqn4rm {
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 8px;
    background: var(--primary-background-color);
  }

  .badge.svelte-wqn4rm {
    display: inline-block;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 6px;
    margin-bottom: 6px;
    font-weight: 500;
    text-transform: uppercase;
  }

  .thinking-entry.svelte-wqn4rm pre:where(.svelte-wqn4rm) {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 12px;
    font-family: 'SF Mono', Monaco, Consolas, monospace;
    color: var(--primary-text-color);
  }

  .thinking-empty.svelte-wqn4rm {
    color: var(--secondary-text-color);
    font-size: 12px;
    text-align: center;
    padding: 16px;
  }

  .models-editor.svelte-fraw8h {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .description.svelte-fraw8h {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }

  .loading.svelte-fraw8h {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
  }

  .message.svelte-fraw8h {
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    background: rgba(76, 175, 80, 0.1);
    color: #4caf50;
    border: 1px solid rgba(76, 175, 80, 0.3);
  }

  .message.error.svelte-fraw8h {
    background: rgba(244, 67, 54, 0.1);
    color: var(--error-color);
    border-color: rgba(244, 67, 54, 0.3);
  }

  .provider-list.svelte-fraw8h {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .provider-card.svelte-fraw8h {
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    overflow: hidden;
    transition: border-color 0.2s;
  }

  .provider-card.expanded.svelte-fraw8h {
    border-color: var(--primary-color);
  }

  .provider-header.svelte-fraw8h {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border: none;
    background: var(--secondary-background-color);
    cursor: pointer;
    font-family: inherit;
    transition: background 0.2s;
  }

  .provider-header.svelte-fraw8h:hover {
    background: var(--card-background-color);
  }

  .provider-info.svelte-fraw8h {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .provider-name.svelte-fraw8h {
    font-size: 14px;
    font-weight: 600;
    color: var(--primary-text-color);
  }

  .model-count.svelte-fraw8h {
    font-size: 12px;
    color: var(--secondary-text-color);
    background: var(--divider-color);
    padding: 2px 8px;
    border-radius: 10px;
  }

  .chevron.svelte-fraw8h {
    width: 20px;
    height: 20px;
    fill: var(--secondary-text-color);
    transition: transform 0.2s;
  }

  .chevron.rotated.svelte-fraw8h {
    transform: rotate(180deg);
  }

  .provider-body.svelte-fraw8h {
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    border-top: 1px solid var(--divider-color);
  }

  .model-row.svelte-fraw8h {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
  }

  .model-fields.svelte-fraw8h {
    display: flex;
    flex: 1;
    gap: 6px;
    flex-wrap: wrap;
  }

  .input.svelte-fraw8h {
    padding: 6px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 6px;
    font-size: 13px;
    color: var(--primary-text-color);
    background: var(--primary-background-color);
    font-family: inherit;
    min-width: 0;
    flex: 1;
  }

  .input.small.svelte-fraw8h {
    flex: 0.8;
  }

  .input.wide.svelte-fraw8h {
    flex: 1.5;
  }

  .input.svelte-fraw8h:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.15);
  }

  .model-actions.svelte-fraw8h {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  .icon-btn.svelte-fraw8h {
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    cursor: pointer;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
  }

  .icon-btn.svelte-fraw8h:hover {
    background: var(--secondary-background-color);
  }

  .icon-btn.svelte-fraw8h svg:where(.svelte-fraw8h) {
    width: 18px;
    height: 18px;
    fill: var(--secondary-text-color);
  }

  .icon-btn.active.svelte-fraw8h svg:where(.svelte-fraw8h),
  .icon-btn.active.svelte-fraw8h .star-icon:where(.svelte-fraw8h) {
    fill: #ffc107;
  }

  .star-icon.svelte-fraw8h {
    fill: var(--secondary-text-color);
  }

  .icon-btn.danger.svelte-fraw8h:hover {
    background: rgba(244, 67, 54, 0.1);
  }

  .icon-btn.danger.svelte-fraw8h:hover svg:where(.svelte-fraw8h) {
    fill: var(--error-color);
  }

  .empty-models.svelte-fraw8h {
    text-align: center;
    padding: 16px;
    color: var(--secondary-text-color);
    font-size: 13px;
    font-style: italic;
  }

  .provider-actions.svelte-fraw8h {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 8px;
    border-top: 1px solid var(--divider-color);
  }

  .action-group.svelte-fraw8h {
    display: flex;
    gap: 6px;
  }

  .btn.svelte-fraw8h {
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }

  .btn.svelte-fraw8h:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn.primary.svelte-fraw8h {
    background: var(--primary-color);
    color: white;
  }

  .btn.primary.svelte-fraw8h:hover:not(:disabled) {
    filter: brightness(1.1);
  }

  .btn.secondary.svelte-fraw8h {
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    border: 1px solid var(--divider-color);
  }

  .btn.secondary.svelte-fraw8h:hover:not(:disabled) {
    background: var(--card-background-color);
  }

  .btn.text.svelte-fraw8h {
    background: none;
    color: var(--primary-color);
    padding: 6px 8px;
  }

  .btn.text.svelte-fraw8h:hover {
    background: rgba(3, 169, 244, 0.08);
  }

  @media (max-width: 480px) {
    .model-fields.svelte-fraw8h {
      flex-direction: column;
    }

    .input.small.svelte-fraw8h,
    .input.wide.svelte-fraw8h {
      flex: 1;
    }
  }

  .defaults-editor.svelte-1udswlp {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .description.svelte-1udswlp {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }

  .field.svelte-1udswlp {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .field.svelte-1udswlp label:where(.svelte-1udswlp) {
    font-size: 13px;
    font-weight: 500;
    color: var(--primary-text-color);
  }

  .select.svelte-1udswlp {
    padding: 8px 12px;
    background: var(--secondary-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    font-size: 14px;
    color: var(--primary-text-color);
    cursor: pointer;
    font-family: inherit;
    appearance: none;
    background-image: url('data:image/svg+xml;charset=US-ASCII,<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7 10l5 5 5-5H7z" fill="currentColor"/></svg>');
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 30px;
  }

  .select.svelte-1udswlp:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .select.svelte-1udswlp:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
  }

  .loading-text.svelte-1udswlp {
    font-size: 13px;
    color: var(--secondary-text-color);
    padding: 8px 0;
  }

  .current-defaults.svelte-1udswlp {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    padding: 10px 12px;
    background: var(--secondary-background-color);
    border-radius: 8px;
    font-size: 13px;
    color: var(--secondary-text-color);
  }

  .badge.svelte-1udswlp {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    background: var(--primary-color);
    color: white;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
  }

  .badge.model.svelte-1udswlp {
    background: var(--accent-color, #4caf50);
  }

  .message.svelte-1udswlp {
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    background: rgba(76, 175, 80, 0.1);
    color: #4caf50;
    border: 1px solid rgba(76, 175, 80, 0.3);
  }

  .message.error.svelte-1udswlp {
    background: rgba(244, 67, 54, 0.1);
    color: var(--error-color);
    border-color: rgba(244, 67, 54, 0.3);
  }

  .actions.svelte-1udswlp {
    display: flex;
    gap: 8px;
    padding-top: 8px;
  }

  .btn.svelte-1udswlp {
    padding: 8px 20px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }

  .btn.svelte-1udswlp:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn.primary.svelte-1udswlp {
    background: var(--primary-color);
    color: white;
  }

  .btn.primary.svelte-1udswlp:hover:not(:disabled) {
    filter: brightness(1.1);
  }

  .btn.secondary.svelte-1udswlp {
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    border: 1px solid var(--divider-color);
  }

  .btn.secondary.svelte-1udswlp:hover:not(:disabled) {
    background: var(--card-background-color);
  }

  .section.svelte-1lsjbvq {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .card.svelte-1lsjbvq {
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 12px 16px;
  }
  .card.svelte-1lsjbvq h3:where(.svelte-1lsjbvq) {
    margin: 0 0 8px 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--primary-text-color);
  }
  .card-header.svelte-1lsjbvq {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  .card-header.svelte-1lsjbvq h3:where(.svelte-1lsjbvq) {
    margin: 0;
  }
  .kv-grid.svelte-1lsjbvq {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 12px;
    font-size: 13px;
  }
  .k.svelte-1lsjbvq {
    color: var(--secondary-text-color);
  }
  .k.cat.svelte-1lsjbvq {
    text-transform: capitalize;
    padding-left: 12px;
  }
  .v.svelte-1lsjbvq {
    color: var(--primary-text-color);
    font-weight: 500;
  }
  .v.highlight.svelte-1lsjbvq {
    color: #ff9800;
    font-weight: 600;
  }
  .desc.svelte-1lsjbvq {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }
  .btn.svelte-1lsjbvq {
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }
  .btn.svelte-1lsjbvq:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .btn.primary.svelte-1lsjbvq {
    background: var(--primary-color);
    color: white;
  }
  .btn.primary.svelte-1lsjbvq:hover:not(:disabled) {
    filter: brightness(1.1);
  }
  .btn.text.svelte-1lsjbvq {
    background: none;
    color: var(--primary-color);
    padding: 6px 8px;
  }
  .btn.text.svelte-1lsjbvq:hover {
    background: rgba(3, 169, 244, 0.08);
  }
  .btn-sm.svelte-1lsjbvq {
    font-size: 12px;
    padding: 3px 8px;
  }

  /* Identity form */
  .identity-form.svelte-1lsjbvq {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .form-group.svelte-1lsjbvq {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .form-group.svelte-1lsjbvq label:where(.svelte-1lsjbvq) {
    font-size: 12px;
    color: var(--secondary-text-color);
    font-weight: 500;
  }
  .form-group.svelte-1lsjbvq input:where(.svelte-1lsjbvq),
  .form-group.svelte-1lsjbvq textarea:where(.svelte-1lsjbvq),
  .form-group.svelte-1lsjbvq select:where(.svelte-1lsjbvq) {
    padding: 7px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 6px;
    font-size: 13px;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: inherit;
    resize: vertical;
  }
  .form-group.svelte-1lsjbvq input:where(.svelte-1lsjbvq):focus,
  .form-group.svelte-1lsjbvq textarea:where(.svelte-1lsjbvq):focus,
  .form-group.svelte-1lsjbvq select:where(.svelte-1lsjbvq):focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.15);
  }
  .emoji-input.svelte-1lsjbvq {
    width: 60px;
    text-align: center;
    font-size: 18px;
  }
  .form-actions.svelte-1lsjbvq {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }

  /* Smart Memory card */
  .smart-memory-card.svelte-1lsjbvq {
    border: 1px solid rgba(103, 58, 183, 0.25);
  }
  .source-label.svelte-1lsjbvq {
    text-transform: capitalize;
  }
  .v.expiring-count.svelte-1lsjbvq {
    color: #ff9800;
    font-weight: 600;
  }

  .section.svelte-maj3ai {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .toolbar.svelte-maj3ai {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .filter-select.svelte-maj3ai {
    padding: 6px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 6px;
    font-size: 13px;
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    font-family: inherit;
  }
  .count.svelte-maj3ai {
    font-size: 12px;
    color: var(--secondary-text-color);
  }
  .empty.svelte-maj3ai {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
  }
  .memory-card.svelte-maj3ai {
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 10px 14px;
  }
  .memory-card.expiring.svelte-maj3ai {
    opacity: 0.7;
    border-left: 3px solid #ff9800;
  }
  .memory-header.svelte-maj3ai {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .badge.svelte-maj3ai {
    display: inline-flex;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 500;
    background: var(--divider-color);
    color: var(--primary-text-color);
  }
  .badge.cat-fact.svelte-maj3ai {
    background: rgba(33, 150, 243, 0.15);
    color: #2196f3;
  }
  .badge.cat-preference.svelte-maj3ai {
    background: rgba(156, 39, 176, 0.15);
    color: #9c27b0;
  }
  .badge.cat-decision.svelte-maj3ai {
    background: rgba(255, 152, 0, 0.15);
    color: #ff9800;
  }
  .badge.cat-entity.svelte-maj3ai {
    background: rgba(0, 150, 136, 0.15);
    color: #009688;
  }
  .badge.cat-observation.svelte-maj3ai {
    background: rgba(121, 85, 72, 0.15);
    color: #795548;
  }
  .badge.ttl-badge.svelte-maj3ai {
    background: rgba(255, 152, 0, 0.12);
    color: #ff9800;
    font-size: 10px;
  }
  .importance.svelte-maj3ai {
    font-size: 11px;
    color: var(--secondary-text-color);
  }
  .source.svelte-maj3ai {
    font-size: 11px;
    color: var(--secondary-text-color);
    margin-left: auto;
  }
  .del-btn.svelte-maj3ai {
    width: 22px;
    height: 22px;
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 14px;
    color: var(--secondary-text-color);
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .del-btn.svelte-maj3ai:hover {
    background: rgba(244, 67, 54, 0.1);
    color: var(--error-color);
  }
  .memory-text.svelte-maj3ai {
    font-size: 13px;
    color: var(--primary-text-color);
    line-height: 1.5;
    word-break: break-word;
  }
  .memory-meta.svelte-maj3ai {
    font-size: 11px;
    color: var(--secondary-text-color);
    margin-top: 4px;
  }

  .section.svelte-1gytc9k {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .toolbar.svelte-1gytc9k {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .count.svelte-1gytc9k {
    font-size: 12px;
    color: var(--secondary-text-color);
  }
  .empty.svelte-1gytc9k {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
  }
  .btn.svelte-1gytc9k {
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }
  .btn.text.svelte-1gytc9k {
    background: none;
    color: var(--primary-color);
    padding: 6px 8px;
  }
  .btn.text.svelte-1gytc9k:hover {
    background: rgba(3, 169, 244, 0.08);
  }
  .chunk-card.svelte-1gytc9k {
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 10px 14px;
  }
  .chunk-header.svelte-1gytc9k {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 12px;
  }
  .badge.svelte-1gytc9k {
    display: inline-flex;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 500;
    background: var(--divider-color);
    color: var(--primary-text-color);
  }
  .chunk-range.svelte-1gytc9k {
    color: var(--secondary-text-color);
  }
  .chunk-len.svelte-1gytc9k {
    color: var(--secondary-text-color);
    margin-left: auto;
  }
  .chunk-text.svelte-1gytc9k {
    font-size: 12px;
    line-height: 1.5;
    color: var(--primary-text-color);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
    margin: 0;
    background: var(--primary-background-color);
    padding: 8px;
    border-radius: 6px;
  }

  .section.svelte-xtoz3f {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .desc.svelte-xtoz3f {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }
  .search-row.svelte-xtoz3f {
    display: flex;
    gap: 8px;
  }
  .search-input.svelte-xtoz3f {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    font-size: 14px;
    color: var(--primary-text-color);
    background: var(--secondary-background-color);
    font-family: inherit;
  }
  .search-input.svelte-xtoz3f:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
  }
  .btn.svelte-xtoz3f {
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }
  .btn.svelte-xtoz3f:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .btn.primary.svelte-xtoz3f {
    background: var(--primary-color);
    color: white;
  }
  .btn.primary.svelte-xtoz3f:hover:not(:disabled) {
    filter: brightness(1.1);
  }
  .search-result.svelte-xtoz3f {
    margin-top: 8px;
  }
  .search-meta.svelte-xtoz3f {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin-bottom: 6px;
  }
  .search-text.svelte-xtoz3f {
    font-size: 12px;
    line-height: 1.5;
    color: var(--primary-text-color);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 400px;
    overflow-y: auto;
    margin: 0;
    background: var(--secondary-background-color);
    padding: 12px;
    border-radius: 8px;
  }

  .section.svelte-10ewjma {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .loading.svelte-10ewjma,
  .not-initialized.svelte-10ewjma {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
  }
  .desc.svelte-10ewjma {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }
  .card.svelte-10ewjma {
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 12px 16px;
  }
  .card.svelte-10ewjma h3:where(.svelte-10ewjma) {
    margin: 0 0 8px 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--primary-text-color);
  }
  .kv-grid.svelte-10ewjma {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 12px;
    font-size: 13px;
  }
  .k.svelte-10ewjma {
    color: var(--secondary-text-color);
  }
  .v.svelte-10ewjma {
    color: var(--primary-text-color);
    font-weight: 500;
  }
  .v.highlight.svelte-10ewjma {
    color: #ff9800;
    font-weight: 600;
  }
  .v.savings.svelte-10ewjma,
  .savings.svelte-10ewjma {
    color: #4caf50;
    font-weight: 600;
  }
  .savings-card.svelte-10ewjma {
    border: 1px solid rgba(76, 175, 80, 0.3);
  }
  .no-savings.svelte-10ewjma {
    margin: 0;
    font-size: 13px;
    color: var(--secondary-text-color);
    text-align: center;
    padding: 8px 0;
  }
  .filter-select.svelte-10ewjma {
    padding: 6px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 6px;
    font-size: 13px;
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    font-family: inherit;
  }
  .opt-form.svelte-10ewjma {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .form-row.svelte-10ewjma {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .form-row.svelte-10ewjma label:where(.svelte-10ewjma) {
    min-width: 70px;
    font-size: 13px;
    color: var(--secondary-text-color);
    font-weight: 500;
  }
  .form-row.svelte-10ewjma .filter-select:where(.svelte-10ewjma) {
    flex: 1;
  }
  .btn.svelte-10ewjma {
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }
  .btn.svelte-10ewjma:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .btn.primary.svelte-10ewjma {
    background: var(--primary-color);
    color: white;
  }
  .btn.primary.svelte-10ewjma:hover:not(:disabled) {
    filter: brightness(1.1);
  }
  .btn.text.svelte-10ewjma {
    background: none;
    color: var(--primary-color);
    padding: 6px 8px;
  }
  .btn.text.svelte-10ewjma:hover {
    background: rgba(3, 169, 244, 0.08);
  }
  .optimize-btn.svelte-10ewjma {
    align-self: flex-start;
    padding: 10px 24px;
    font-size: 14px;
    background: #ff9800;
    border-color: #ff9800;
  }
  .optimize-btn.svelte-10ewjma:hover:not(:disabled) {
    background: #f57c00;
  }
  .progress-card.svelte-10ewjma {
    border: 1px solid rgba(3, 169, 244, 0.3);
  }
  .progress-bar-container.svelte-10ewjma {
    width: 100%;
    height: 6px;
    background: var(--divider-color);
    border-radius: 3px;
    margin-bottom: 8px;
    overflow: hidden;
  }
  .progress-bar.svelte-10ewjma {
    height: 100%;
    background: var(--primary-color);
    border-radius: 3px;
    transition: width 0.3s ease;
  }
  .progress-log.svelte-10ewjma {
    max-height: 150px;
    overflow-y: auto;
    font-size: 12px;
    color: var(--secondary-text-color);
    line-height: 1.6;
  }
  .progress-line.svelte-10ewjma {
    padding: 1px 0;
  }
  .progress-line.phase.svelte-10ewjma {
    color: var(--primary-color);
    font-weight: 600;
    margin-top: 4px;
  }
  .progress-line.done.svelte-10ewjma {
    color: #4caf50;
  }
  .progress-line.error-line.svelte-10ewjma {
    color: var(--error-color, #f44336);
  }
  .progress-line.complete.svelte-10ewjma {
    color: #4caf50;
    font-weight: 600;
    margin-top: 4px;
  }
  .result-card.svelte-10ewjma {
    border: 1px solid rgba(76, 175, 80, 0.3);
  }
  .result-card.has-errors.svelte-10ewjma {
    border-color: rgba(255, 152, 0, 0.3);
  }
  .error-list.svelte-10ewjma {
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid var(--divider-color);
    font-size: 12px;
  }
  .error-line.svelte-10ewjma {
    color: var(--error-color);
    padding: 2px 0;
  }

  .rag-viewer.svelte-1djclk2 {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .msg.svelte-1djclk2 {
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    background: rgba(76, 175, 80, 0.1);
    color: #4caf50;
    border: 1px solid rgba(76, 175, 80, 0.3);
  }
  .msg.error.svelte-1djclk2 {
    background: rgba(244, 67, 54, 0.1);
    color: var(--error-color);
    border-color: rgba(244, 67, 54, 0.3);
  }
  .loading.svelte-1djclk2,
  .not-initialized.svelte-1djclk2 {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
  }
  .section-nav.svelte-1djclk2 {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .pill.svelte-1djclk2 {
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
  .pill.active.svelte-1djclk2 {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
  }
  .pill.svelte-1djclk2:hover:not(.active) {
    background: var(--card-background-color);
  }
  .pill.optimize-pill.svelte-1djclk2 {
    border-color: rgba(255, 152, 0, 0.4);
  }
  .pill.optimize-pill.active.svelte-1djclk2 {
    background: #ff9800;
    border-color: #ff9800;
  }

  .scheduler-panel.svelte-7zsr1v {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .msg.svelte-7zsr1v {
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    background: rgba(76, 175, 80, 0.1);
    color: #4caf50;
    border: 1px solid rgba(76, 175, 80, 0.3);
  }
  .msg.error.svelte-7zsr1v {
    background: rgba(244, 67, 54, 0.1);
    color: var(--error-color);
    border-color: rgba(244, 67, 54, 0.3);
  }

  .section-nav.svelte-7zsr1v {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .pill.svelte-7zsr1v {
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
  .pill.active.svelte-7zsr1v {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
  }
  .pill.svelte-7zsr1v:hover:not(.active) {
    background: var(--card-background-color);
  }
  .pill.refresh-pill.svelte-7zsr1v {
    margin-left: auto;
    border-color: rgba(33, 150, 243, 0.4);
  }

  .loading.svelte-7zsr1v,
  .not-available.svelte-7zsr1v,
  .empty.svelte-7zsr1v {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
    font-size: 14px;
    line-height: 1.5;
  }
  .empty.svelte-7zsr1v em:where(.svelte-7zsr1v) {
    display: block;
    margin-top: 8px;
    opacity: 0.7;
    font-size: 13px;
  }

  .status-bar.svelte-7zsr1v {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--secondary-text-color);
    padding: 4px 0;
  }
  .dot.svelte-7zsr1v {
    font-size: 16px;
  }

  .jobs-list.svelte-7zsr1v {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .job-card.svelte-7zsr1v {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 10px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: opacity 0.2s;
  }
  .job-card.disabled.svelte-7zsr1v {
    opacity: 0.55;
  }

  .job-header.svelte-7zsr1v {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
  }
  .job-title-row.svelte-7zsr1v {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .job-name.svelte-7zsr1v {
    font-weight: 600;
    font-size: 14px;
    color: var(--primary-text-color);
  }

  .badge.svelte-7zsr1v {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 10px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .badge.agent.svelte-7zsr1v {
    background: rgba(33, 150, 243, 0.15);
    color: #2196f3;
  }
  .badge.one-shot.svelte-7zsr1v {
    background: rgba(255, 152, 0, 0.15);
    color: #ff9800;
  }

  .job-meta.svelte-7zsr1v {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
    color: var(--secondary-text-color);
  }
  .cron.svelte-7zsr1v {
    font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
    background: var(--secondary-background-color);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 11px;
  }
  .next-run.svelte-7zsr1v {
    color: var(--primary-color);
  }

  .job-prompt.svelte-7zsr1v {
    font-size: 13px;
    color: var(--secondary-text-color);
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .job-last-run.svelte-7zsr1v {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--secondary-text-color);
  }
  .last-error.svelte-7zsr1v {
    color: var(--error-color);
    font-weight: 500;
  }

  .status-dot.svelte-7zsr1v {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--secondary-text-color);
    flex-shrink: 0;
  }
  .status-dot.ok.svelte-7zsr1v {
    background: #4caf50;
  }
  .status-dot.error.svelte-7zsr1v {
    background: #f44336;
  }

  .job-actions.svelte-7zsr1v {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }
  .action-btn.svelte-7zsr1v {
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
  .action-btn.svelte-7zsr1v:hover {
    background: var(--card-background-color);
  }
  .action-btn.svelte-7zsr1v:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .action-btn.run.svelte-7zsr1v {
    border-color: rgba(33, 150, 243, 0.4);
    color: #2196f3;
  }
  .action-btn.run.svelte-7zsr1v:hover {
    background: rgba(33, 150, 243, 0.1);
  }
  .action-btn.delete.svelte-7zsr1v {
    border-color: rgba(244, 67, 54, 0.3);
    color: #f44336;
  }
  .action-btn.delete.svelte-7zsr1v:hover {
    background: rgba(244, 67, 54, 0.1);
  }

  /* Toggle switch */
  .toggle.svelte-7zsr1v {
    position: relative;
    display: inline-block;
    width: 36px;
    height: 20px;
    flex-shrink: 0;
  }
  .toggle.svelte-7zsr1v input:where(.svelte-7zsr1v) {
    opacity: 0;
    width: 0;
    height: 0;
  }
  .slider.svelte-7zsr1v {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background: var(--divider-color);
    border-radius: 20px;
    transition: 0.2s;
  }
  .slider.svelte-7zsr1v::before {
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
  .toggle.svelte-7zsr1v input:where(.svelte-7zsr1v):checked + .slider:where(.svelte-7zsr1v) {
    background: var(--primary-color);
  }
  .toggle.svelte-7zsr1v input:where(.svelte-7zsr1v):checked + .slider:where(.svelte-7zsr1v)::before {
    transform: translateX(16px);
  }

  /* History */
  .history-list.svelte-7zsr1v {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .history-item.svelte-7zsr1v {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .history-item.error.svelte-7zsr1v {
    border-color: rgba(244, 67, 54, 0.3);
  }
  .history-header.svelte-7zsr1v {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .history-name.svelte-7zsr1v {
    font-weight: 600;
    font-size: 13px;
    color: var(--primary-text-color);
  }
  .history-time.svelte-7zsr1v {
    font-size: 11px;
    color: var(--secondary-text-color);
  }
  .history-detail.svelte-7zsr1v {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--secondary-text-color);
  }
  .history-status.svelte-7zsr1v {
    text-transform: uppercase;
    font-weight: 500;
    font-size: 11px;
  }
  .history-duration.svelte-7zsr1v {
    opacity: 0.7;
  }
  .history-error.svelte-7zsr1v {
    font-size: 12px;
    color: var(--error-color);
    margin-top: 2px;
  }
  .history-response.svelte-7zsr1v {
    font-size: 12px;
    color: var(--secondary-text-color);
    line-height: 1.4;
    opacity: 0.8;
    margin-top: 2px;
  }

  .settings-backdrop.svelte-nsapwt {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 200;
  }

  .settings-panel.svelte-nsapwt {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(480px, 100vw);
    background: var(--primary-background-color);
    z-index: 201;
    display: flex;
    flex-direction: column;
    box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
    animation: svelte-nsapwt-slideIn 0.2s ease-out;
  }

  @keyframes svelte-nsapwt-slideIn {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }

  .settings-header.svelte-nsapwt {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--divider-color);
  }

  .settings-header.svelte-nsapwt h2:where(.svelte-nsapwt) {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--primary-text-color);
  }

  .close-btn.svelte-nsapwt {
    width: 36px;
    height: 36px;
    border: none;
    background: transparent;
    cursor: pointer;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
  }

  .close-btn.svelte-nsapwt:hover {
    background: var(--secondary-background-color);
  }

  .icon.svelte-nsapwt {
    width: 20px;
    height: 20px;
    fill: var(--secondary-text-color);
  }

  .tabs.svelte-nsapwt {
    display: flex;
    border-bottom: 1px solid var(--divider-color);
    padding: 0 20px;
  }

  .tab.svelte-nsapwt {
    padding: 10px 16px;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: var(--secondary-text-color);
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
    font-family: inherit;
  }

  .tab.active.svelte-nsapwt {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }

  .tab.svelte-nsapwt:hover:not(.active) {
    color: var(--primary-text-color);
    background: var(--secondary-background-color);
  }

  .settings-content.svelte-nsapwt {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
  }

  @media (max-width: 768px) {
    .settings-panel.svelte-nsapwt {
      width: 100vw;
    }
  }

  .homeclaw-panel.svelte-j6syiu {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100vh;
    overflow: hidden;
    background-color: var(--primary-background-color);
  }

  .main-container.svelte-j6syiu {
    display: flex;
    flex: 1;
    overflow: hidden;
    position: relative;
  }

  .content-area.svelte-j6syiu {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
    position: relative;
    background: var(--bg-chat, var(--primary-background-color));
    transition: background var(--transition-medium, 250ms ease-in-out);
  }

  .chat-container.svelte-j6syiu {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
    position: relative;
  }

  /* Mobile adjustments */
  .homeclaw-panel.narrow.svelte-j6syiu .content-area:where(.svelte-j6syiu) {
    width: 100%;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .homeclaw-panel.svelte-j6syiu {
      height: 100vh;
      height: 100dvh; /* Dynamic viewport height for mobile */
    }
  }

  /* Animation */
  .content-area.svelte-j6syiu {
    animation: svelte-j6syiu-fadeIn 0.3s ease-in-out;
  }

  @keyframes svelte-j6syiu-fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
`;
const PUBLIC_VERSION = "5";
if (typeof window !== "undefined") {
  ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add(PUBLIC_VERSION);
}
const EACH_ITEM_REACTIVE = 1;
const EACH_INDEX_REACTIVE = 1 << 1;
const EACH_IS_CONTROLLED = 1 << 2;
const EACH_IS_ANIMATED = 1 << 3;
const EACH_ITEM_IMMUTABLE = 1 << 4;
const TEMPLATE_FRAGMENT = 1;
const TEMPLATE_USE_IMPORT_NODE = 1 << 1;
const UNINITIALIZED = /* @__PURE__ */ Symbol();
const NAMESPACE_HTML = "http://www.w3.org/1999/xhtml";
const DEV = false;
var is_array = Array.isArray;
var index_of = Array.prototype.indexOf;
var includes = Array.prototype.includes;
var array_from = Array.from;
var define_property = Object.defineProperty;
var get_descriptor = Object.getOwnPropertyDescriptor;
var get_descriptors = Object.getOwnPropertyDescriptors;
var object_prototype = Object.prototype;
var array_prototype = Array.prototype;
var get_prototype_of = Object.getPrototypeOf;
var is_extensible = Object.isExtensible;
const noop = () => {
};
function run(fn) {
  return fn();
}
function run_all(arr) {
  for (var i2 = 0; i2 < arr.length; i2++) {
    arr[i2]();
  }
}
function deferred() {
  var resolve;
  var reject;
  var promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
function to_array(value, n2) {
  if (Array.isArray(value)) {
    return value;
  }
  if (!(Symbol.iterator in value)) {
    return Array.from(value);
  }
  const array = [];
  for (const element of value) {
    array.push(element);
    if (array.length === n2) break;
  }
  return array;
}
const DERIVED = 1 << 1;
const EFFECT = 1 << 2;
const RENDER_EFFECT = 1 << 3;
const MANAGED_EFFECT = 1 << 24;
const BLOCK_EFFECT = 1 << 4;
const BRANCH_EFFECT = 1 << 5;
const ROOT_EFFECT = 1 << 6;
const BOUNDARY_EFFECT = 1 << 7;
const CONNECTED = 1 << 9;
const CLEAN = 1 << 10;
const DIRTY = 1 << 11;
const MAYBE_DIRTY = 1 << 12;
const INERT = 1 << 13;
const DESTROYED = 1 << 14;
const EFFECT_RAN = 1 << 15;
const EFFECT_TRANSPARENT = 1 << 16;
const EAGER_EFFECT = 1 << 17;
const HEAD_EFFECT = 1 << 18;
const EFFECT_PRESERVED = 1 << 19;
const USER_EFFECT = 1 << 20;
const EFFECT_OFFSCREEN = 1 << 25;
const WAS_MARKED = 1 << 15;
const REACTION_IS_UPDATING = 1 << 21;
const ASYNC = 1 << 22;
const ERROR_VALUE = 1 << 23;
const STATE_SYMBOL = /* @__PURE__ */ Symbol("$state");
const LOADING_ATTR_SYMBOL = /* @__PURE__ */ Symbol("");
const STALE_REACTION = new class StaleReactionError extends Error {
  name = "StaleReactionError";
  message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}();
function lifecycle_outside_component(name) {
  {
    throw new Error(`https://svelte.dev/e/lifecycle_outside_component`);
  }
}
function async_derived_orphan() {
  {
    throw new Error(`https://svelte.dev/e/async_derived_orphan`);
  }
}
function effect_in_teardown(rune) {
  {
    throw new Error(`https://svelte.dev/e/effect_in_teardown`);
  }
}
function effect_in_unowned_derived() {
  {
    throw new Error(`https://svelte.dev/e/effect_in_unowned_derived`);
  }
}
function effect_orphan(rune) {
  {
    throw new Error(`https://svelte.dev/e/effect_orphan`);
  }
}
function effect_update_depth_exceeded() {
  {
    throw new Error(`https://svelte.dev/e/effect_update_depth_exceeded`);
  }
}
function state_descriptors_fixed() {
  {
    throw new Error(`https://svelte.dev/e/state_descriptors_fixed`);
  }
}
function state_prototype_fixed() {
  {
    throw new Error(`https://svelte.dev/e/state_prototype_fixed`);
  }
}
function state_unsafe_mutation() {
  {
    throw new Error(`https://svelte.dev/e/state_unsafe_mutation`);
  }
}
function svelte_boundary_reset_onerror() {
  {
    throw new Error(`https://svelte.dev/e/svelte_boundary_reset_onerror`);
  }
}
function select_multiple_invalid_value() {
  {
    console.warn(`https://svelte.dev/e/select_multiple_invalid_value`);
  }
}
function svelte_boundary_reset_noop() {
  {
    console.warn(`https://svelte.dev/e/svelte_boundary_reset_noop`);
  }
}
function equals(value) {
  return value === this.v;
}
function safe_not_equal(a2, b2) {
  return a2 != a2 ? b2 == b2 : a2 !== b2 || a2 !== null && typeof a2 === "object" || typeof a2 === "function";
}
function safe_equals(value) {
  return !safe_not_equal(value, this.v);
}
let legacy_mode_flag = false;
let tracing_mode_flag = false;
function enable_legacy_mode_flag() {
  legacy_mode_flag = true;
}
let component_context = null;
function set_component_context(context) {
  component_context = context;
}
function push(props, runes = false, fn) {
  component_context = {
    p: component_context,
    i: false,
    c: null,
    e: null,
    s: props,
    x: null,
    l: legacy_mode_flag && !runes ? { s: null, u: null, $: [] } : null
  };
}
function pop(component) {
  var context = (
    /** @type {ComponentContext} */
    component_context
  );
  var effects = context.e;
  if (effects !== null) {
    context.e = null;
    for (var fn of effects) {
      create_user_effect(fn);
    }
  }
  if (component !== void 0) {
    context.x = component;
  }
  context.i = true;
  component_context = context.p;
  return component ?? /** @type {T} */
  {};
}
function is_runes() {
  return !legacy_mode_flag || component_context !== null && component_context.l === null;
}
let micro_tasks = [];
function run_micro_tasks() {
  var tasks = micro_tasks;
  micro_tasks = [];
  run_all(tasks);
}
function queue_micro_task(fn) {
  if (micro_tasks.length === 0 && !is_flushing_sync) {
    var tasks = micro_tasks;
    queueMicrotask(() => {
      if (tasks === micro_tasks) run_micro_tasks();
    });
  }
  micro_tasks.push(fn);
}
function flush_tasks() {
  while (micro_tasks.length > 0) {
    run_micro_tasks();
  }
}
function handle_error(error) {
  var effect2 = active_effect;
  if (effect2 === null) {
    active_reaction.f |= ERROR_VALUE;
    return error;
  }
  if ((effect2.f & EFFECT_RAN) === 0) {
    if ((effect2.f & BOUNDARY_EFFECT) === 0) {
      throw error;
    }
    effect2.b.error(error);
  } else {
    invoke_error_boundary(error, effect2);
  }
}
function invoke_error_boundary(error, effect2) {
  while (effect2 !== null) {
    if ((effect2.f & BOUNDARY_EFFECT) !== 0) {
      try {
        effect2.b.error(error);
        return;
      } catch (e2) {
        error = e2;
      }
    }
    effect2 = effect2.parent;
  }
  throw error;
}
const STATUS_MASK = -7169;
function set_signal_status(signal, status) {
  signal.f = signal.f & STATUS_MASK | status;
}
function update_derived_status(derived2) {
  if ((derived2.f & CONNECTED) !== 0 || derived2.deps === null) {
    set_signal_status(derived2, CLEAN);
  } else {
    set_signal_status(derived2, MAYBE_DIRTY);
  }
}
function clear_marked(deps) {
  if (deps === null) return;
  for (const dep of deps) {
    if ((dep.f & DERIVED) === 0 || (dep.f & WAS_MARKED) === 0) {
      continue;
    }
    dep.f ^= WAS_MARKED;
    clear_marked(
      /** @type {Derived} */
      dep.deps
    );
  }
}
function defer_effect(effect2, dirty_effects, maybe_dirty_effects) {
  if ((effect2.f & DIRTY) !== 0) {
    dirty_effects.add(effect2);
  } else if ((effect2.f & MAYBE_DIRTY) !== 0) {
    maybe_dirty_effects.add(effect2);
  }
  clear_marked(effect2.deps);
  set_signal_status(effect2, CLEAN);
}
const batches = /* @__PURE__ */ new Set();
let current_batch = null;
let previous_batch = null;
let batch_values = null;
let queued_root_effects = [];
let last_scheduled_effect = null;
let is_flushing = false;
let is_flushing_sync = false;
class Batch {
  committed = false;
  /**
   * The current values of any sources that are updated in this batch
   * They keys of this map are identical to `this.#previous`
   * @type {Map<Source, any>}
   */
  current = /* @__PURE__ */ new Map();
  /**
   * The values of any sources that are updated in this batch _before_ those updates took place.
   * They keys of this map are identical to `this.#current`
   * @type {Map<Source, any>}
   */
  previous = /* @__PURE__ */ new Map();
  /**
   * When the batch is committed (and the DOM is updated), we need to remove old branches
   * and append new ones by calling the functions added inside (if/each/key/etc) blocks
   * @type {Set<() => void>}
   */
  #commit_callbacks = /* @__PURE__ */ new Set();
  /**
   * If a fork is discarded, we need to destroy any effects that are no longer needed
   * @type {Set<(batch: Batch) => void>}
   */
  #discard_callbacks = /* @__PURE__ */ new Set();
  /**
   * The number of async effects that are currently in flight
   */
  #pending = 0;
  /**
   * The number of async effects that are currently in flight, _not_ inside a pending boundary
   */
  #blocking_pending = 0;
  /**
   * A deferred that resolves when the batch is committed, used with `settled()`
   * TODO replace with Promise.withResolvers once supported widely enough
   * @type {{ promise: Promise<void>, resolve: (value?: any) => void, reject: (reason: unknown) => void } | null}
   */
  #deferred = null;
  /**
   * Deferred effects (which run after async work has completed) that are DIRTY
   * @type {Set<Effect>}
   */
  #dirty_effects = /* @__PURE__ */ new Set();
  /**
   * Deferred effects that are MAYBE_DIRTY
   * @type {Set<Effect>}
   */
  #maybe_dirty_effects = /* @__PURE__ */ new Set();
  /**
   * A set of branches that still exist, but will be destroyed when this batch
   * is committed — we skip over these during `process`
   * @type {Set<Effect>}
   */
  skipped_effects = /* @__PURE__ */ new Set();
  is_fork = false;
  #decrement_queued = false;
  is_deferred() {
    return this.is_fork || this.#blocking_pending > 0;
  }
  /**
   *
   * @param {Effect[]} root_effects
   */
  process(root_effects) {
    queued_root_effects = [];
    this.apply();
    var effects = [];
    var render_effects = [];
    for (const root2 of root_effects) {
      this.#traverse_effect_tree(root2, effects, render_effects);
    }
    if (this.is_deferred()) {
      this.#defer_effects(render_effects);
      this.#defer_effects(effects);
      for (const e2 of this.skipped_effects) {
        reset_branch(e2);
      }
    } else {
      for (const fn of this.#commit_callbacks) fn();
      this.#commit_callbacks.clear();
      if (this.#pending === 0) {
        this.#commit();
      }
      previous_batch = this;
      current_batch = null;
      flush_queued_effects(render_effects);
      flush_queued_effects(effects);
      previous_batch = null;
      this.#deferred?.resolve();
    }
    batch_values = null;
  }
  /**
   * Traverse the effect tree, executing effects or stashing
   * them for later execution as appropriate
   * @param {Effect} root
   * @param {Effect[]} effects
   * @param {Effect[]} render_effects
   */
  #traverse_effect_tree(root2, effects, render_effects) {
    root2.f ^= CLEAN;
    var effect2 = root2.first;
    var pending_boundary = null;
    while (effect2 !== null) {
      var flags2 = effect2.f;
      var is_branch = (flags2 & (BRANCH_EFFECT | ROOT_EFFECT)) !== 0;
      var is_skippable_branch = is_branch && (flags2 & CLEAN) !== 0;
      var skip = is_skippable_branch || (flags2 & INERT) !== 0 || this.skipped_effects.has(effect2);
      if (!skip && effect2.fn !== null) {
        if (is_branch) {
          effect2.f ^= CLEAN;
        } else if (pending_boundary !== null && (flags2 & (EFFECT | RENDER_EFFECT | MANAGED_EFFECT)) !== 0) {
          pending_boundary.b.defer_effect(effect2);
        } else if ((flags2 & EFFECT) !== 0) {
          effects.push(effect2);
        } else if (is_dirty(effect2)) {
          if ((flags2 & BLOCK_EFFECT) !== 0) this.#maybe_dirty_effects.add(effect2);
          update_effect(effect2);
        }
        var child2 = effect2.first;
        if (child2 !== null) {
          effect2 = child2;
          continue;
        }
      }
      var parent = effect2.parent;
      effect2 = effect2.next;
      while (effect2 === null && parent !== null) {
        if (parent === pending_boundary) {
          pending_boundary = null;
        }
        effect2 = parent.next;
        parent = parent.parent;
      }
    }
  }
  /**
   * @param {Effect[]} effects
   */
  #defer_effects(effects) {
    for (var i2 = 0; i2 < effects.length; i2 += 1) {
      defer_effect(effects[i2], this.#dirty_effects, this.#maybe_dirty_effects);
    }
  }
  /**
   * Associate a change to a given source with the current
   * batch, noting its previous and current values
   * @param {Source} source
   * @param {any} value
   */
  capture(source2, value) {
    if (value !== UNINITIALIZED && !this.previous.has(source2)) {
      this.previous.set(source2, value);
    }
    if ((source2.f & ERROR_VALUE) === 0) {
      this.current.set(source2, source2.v);
      batch_values?.set(source2, source2.v);
    }
  }
  activate() {
    current_batch = this;
    this.apply();
  }
  deactivate() {
    if (current_batch !== this) return;
    current_batch = null;
    batch_values = null;
  }
  flush() {
    this.activate();
    if (queued_root_effects.length > 0) {
      flush_effects();
      if (current_batch !== null && current_batch !== this) {
        return;
      }
    } else if (this.#pending === 0) {
      this.process([]);
    }
    this.deactivate();
  }
  discard() {
    for (const fn of this.#discard_callbacks) fn(this);
    this.#discard_callbacks.clear();
  }
  #commit() {
    if (batches.size > 1) {
      this.previous.clear();
      var previous_batch_values = batch_values;
      var is_earlier = true;
      for (const batch of batches) {
        if (batch === this) {
          is_earlier = false;
          continue;
        }
        const sources = [];
        for (const [source2, value] of this.current) {
          if (batch.current.has(source2)) {
            if (is_earlier && value !== batch.current.get(source2)) {
              batch.current.set(source2, value);
            } else {
              continue;
            }
          }
          sources.push(source2);
        }
        if (sources.length === 0) {
          continue;
        }
        const others = [...batch.current.keys()].filter((s2) => !this.current.has(s2));
        if (others.length > 0) {
          var prev_queued_root_effects = queued_root_effects;
          queued_root_effects = [];
          const marked = /* @__PURE__ */ new Set();
          const checked = /* @__PURE__ */ new Map();
          for (const source2 of sources) {
            mark_effects(source2, others, marked, checked);
          }
          if (queued_root_effects.length > 0) {
            current_batch = batch;
            batch.apply();
            for (const root2 of queued_root_effects) {
              batch.#traverse_effect_tree(root2, [], []);
            }
            batch.deactivate();
          }
          queued_root_effects = prev_queued_root_effects;
        }
      }
      current_batch = null;
      batch_values = previous_batch_values;
    }
    this.committed = true;
    batches.delete(this);
  }
  /**
   *
   * @param {boolean} blocking
   */
  increment(blocking) {
    this.#pending += 1;
    if (blocking) this.#blocking_pending += 1;
  }
  /**
   *
   * @param {boolean} blocking
   */
  decrement(blocking) {
    this.#pending -= 1;
    if (blocking) this.#blocking_pending -= 1;
    if (this.#decrement_queued) return;
    this.#decrement_queued = true;
    queue_micro_task(() => {
      this.#decrement_queued = false;
      if (!this.is_deferred()) {
        this.revive();
      } else if (queued_root_effects.length > 0) {
        this.flush();
      }
    });
  }
  revive() {
    for (const e2 of this.#dirty_effects) {
      this.#maybe_dirty_effects.delete(e2);
      set_signal_status(e2, DIRTY);
      schedule_effect(e2);
    }
    for (const e2 of this.#maybe_dirty_effects) {
      set_signal_status(e2, MAYBE_DIRTY);
      schedule_effect(e2);
    }
    this.flush();
  }
  /** @param {() => void} fn */
  oncommit(fn) {
    this.#commit_callbacks.add(fn);
  }
  /** @param {(batch: Batch) => void} fn */
  ondiscard(fn) {
    this.#discard_callbacks.add(fn);
  }
  settled() {
    return (this.#deferred ??= deferred()).promise;
  }
  static ensure() {
    if (current_batch === null) {
      const batch = current_batch = new Batch();
      batches.add(current_batch);
      if (!is_flushing_sync) {
        queue_micro_task(() => {
          if (current_batch !== batch) {
            return;
          }
          batch.flush();
        });
      }
    }
    return current_batch;
  }
  apply() {
    return;
  }
}
function flushSync(fn) {
  var was_flushing_sync = is_flushing_sync;
  is_flushing_sync = true;
  try {
    var result;
    if (fn) ;
    while (true) {
      flush_tasks();
      if (queued_root_effects.length === 0) {
        current_batch?.flush();
        if (queued_root_effects.length === 0) {
          last_scheduled_effect = null;
          return (
            /** @type {T} */
            result
          );
        }
      }
      flush_effects();
    }
  } finally {
    is_flushing_sync = was_flushing_sync;
  }
}
function flush_effects() {
  is_flushing = true;
  var source_stacks = null;
  try {
    var flush_count = 0;
    while (queued_root_effects.length > 0) {
      var batch = Batch.ensure();
      if (flush_count++ > 1e3) {
        var updates, entry;
        if (DEV) ;
        infinite_loop_guard();
      }
      batch.process(queued_root_effects);
      old_values.clear();
      if (DEV) ;
    }
  } finally {
    is_flushing = false;
    last_scheduled_effect = null;
  }
}
function infinite_loop_guard() {
  try {
    effect_update_depth_exceeded();
  } catch (error) {
    invoke_error_boundary(error, last_scheduled_effect);
  }
}
let eager_block_effects = null;
function flush_queued_effects(effects) {
  var length = effects.length;
  if (length === 0) return;
  var i2 = 0;
  while (i2 < length) {
    var effect2 = effects[i2++];
    if ((effect2.f & (DESTROYED | INERT)) === 0 && is_dirty(effect2)) {
      eager_block_effects = /* @__PURE__ */ new Set();
      update_effect(effect2);
      if (effect2.deps === null && effect2.first === null && effect2.nodes === null) {
        if (effect2.teardown === null && effect2.ac === null) {
          unlink_effect(effect2);
        } else {
          effect2.fn = null;
        }
      }
      if (eager_block_effects?.size > 0) {
        old_values.clear();
        for (const e2 of eager_block_effects) {
          if ((e2.f & (DESTROYED | INERT)) !== 0) continue;
          const ordered_effects = [e2];
          let ancestor = e2.parent;
          while (ancestor !== null) {
            if (eager_block_effects.has(ancestor)) {
              eager_block_effects.delete(ancestor);
              ordered_effects.push(ancestor);
            }
            ancestor = ancestor.parent;
          }
          for (let j2 = ordered_effects.length - 1; j2 >= 0; j2--) {
            const e3 = ordered_effects[j2];
            if ((e3.f & (DESTROYED | INERT)) !== 0) continue;
            update_effect(e3);
          }
        }
        eager_block_effects.clear();
      }
    }
  }
  eager_block_effects = null;
}
function mark_effects(value, sources, marked, checked) {
  if (marked.has(value)) return;
  marked.add(value);
  if (value.reactions !== null) {
    for (const reaction of value.reactions) {
      const flags2 = reaction.f;
      if ((flags2 & DERIVED) !== 0) {
        mark_effects(
          /** @type {Derived} */
          reaction,
          sources,
          marked,
          checked
        );
      } else if ((flags2 & (ASYNC | BLOCK_EFFECT)) !== 0 && (flags2 & DIRTY) === 0 && depends_on(reaction, sources, checked)) {
        set_signal_status(reaction, DIRTY);
        schedule_effect(
          /** @type {Effect} */
          reaction
        );
      }
    }
  }
}
function depends_on(reaction, sources, checked) {
  const depends = checked.get(reaction);
  if (depends !== void 0) return depends;
  if (reaction.deps !== null) {
    for (const dep of reaction.deps) {
      if (includes.call(sources, dep)) {
        return true;
      }
      if ((dep.f & DERIVED) !== 0 && depends_on(
        /** @type {Derived} */
        dep,
        sources,
        checked
      )) {
        checked.set(
          /** @type {Derived} */
          dep,
          true
        );
        return true;
      }
    }
  }
  checked.set(reaction, false);
  return false;
}
function schedule_effect(signal) {
  var effect2 = last_scheduled_effect = signal;
  while (effect2.parent !== null) {
    effect2 = effect2.parent;
    var flags2 = effect2.f;
    if (is_flushing && effect2 === active_effect && (flags2 & BLOCK_EFFECT) !== 0 && (flags2 & HEAD_EFFECT) === 0) {
      return;
    }
    if ((flags2 & (ROOT_EFFECT | BRANCH_EFFECT)) !== 0) {
      if ((flags2 & CLEAN) === 0) return;
      effect2.f ^= CLEAN;
    }
  }
  queued_root_effects.push(effect2);
}
function reset_branch(effect2) {
  if ((effect2.f & BRANCH_EFFECT) !== 0 && (effect2.f & CLEAN) !== 0) {
    return;
  }
  set_signal_status(effect2, CLEAN);
  var e2 = effect2.first;
  while (e2 !== null) {
    reset_branch(e2);
    e2 = e2.next;
  }
}
function createSubscriber(start) {
  let subscribers = 0;
  let version = source(0);
  let stop;
  return () => {
    if (effect_tracking()) {
      get$1(version);
      render_effect(() => {
        if (subscribers === 0) {
          stop = untrack(() => start(() => increment(version)));
        }
        subscribers += 1;
        return () => {
          queue_micro_task(() => {
            subscribers -= 1;
            if (subscribers === 0) {
              stop?.();
              stop = void 0;
              increment(version);
            }
          });
        };
      });
    }
  };
}
var flags = EFFECT_TRANSPARENT | EFFECT_PRESERVED | BOUNDARY_EFFECT;
function boundary(node, props, children) {
  new Boundary(node, props, children);
}
class Boundary {
  /** @type {Boundary | null} */
  parent;
  is_pending = false;
  /** @type {TemplateNode} */
  #anchor;
  /** @type {TemplateNode | null} */
  #hydrate_open = null;
  /** @type {BoundaryProps} */
  #props;
  /** @type {((anchor: Node) => void)} */
  #children;
  /** @type {Effect} */
  #effect;
  /** @type {Effect | null} */
  #main_effect = null;
  /** @type {Effect | null} */
  #pending_effect = null;
  /** @type {Effect | null} */
  #failed_effect = null;
  /** @type {DocumentFragment | null} */
  #offscreen_fragment = null;
  /** @type {TemplateNode | null} */
  #pending_anchor = null;
  #local_pending_count = 0;
  #pending_count = 0;
  #pending_count_update_queued = false;
  #is_creating_fallback = false;
  /** @type {Set<Effect>} */
  #dirty_effects = /* @__PURE__ */ new Set();
  /** @type {Set<Effect>} */
  #maybe_dirty_effects = /* @__PURE__ */ new Set();
  /**
   * A source containing the number of pending async deriveds/expressions.
   * Only created if `$effect.pending()` is used inside the boundary,
   * otherwise updating the source results in needless `Batch.ensure()`
   * calls followed by no-op flushes
   * @type {Source<number> | null}
   */
  #effect_pending = null;
  #effect_pending_subscriber = createSubscriber(() => {
    this.#effect_pending = source(this.#local_pending_count);
    return () => {
      this.#effect_pending = null;
    };
  });
  /**
   * @param {TemplateNode} node
   * @param {BoundaryProps} props
   * @param {((anchor: Node) => void)} children
   */
  constructor(node, props, children) {
    this.#anchor = node;
    this.#props = props;
    this.#children = children;
    this.parent = /** @type {Effect} */
    active_effect.b;
    this.is_pending = !!this.#props.pending;
    this.#effect = block(() => {
      active_effect.b = this;
      {
        var anchor = this.#get_anchor();
        try {
          this.#main_effect = branch(() => children(anchor));
        } catch (error) {
          this.error(error);
        }
        if (this.#pending_count > 0) {
          this.#show_pending_snippet();
        } else {
          this.is_pending = false;
        }
      }
      return () => {
        this.#pending_anchor?.remove();
      };
    }, flags);
  }
  #hydrate_resolved_content() {
    try {
      this.#main_effect = branch(() => this.#children(this.#anchor));
    } catch (error) {
      this.error(error);
    }
  }
  #hydrate_pending_content() {
    const pending = this.#props.pending;
    if (!pending) return;
    this.#pending_effect = branch(() => pending(this.#anchor));
    queue_micro_task(() => {
      var anchor = this.#get_anchor();
      this.#main_effect = this.#run(() => {
        Batch.ensure();
        return branch(() => this.#children(anchor));
      });
      if (this.#pending_count > 0) {
        this.#show_pending_snippet();
      } else {
        pause_effect(
          /** @type {Effect} */
          this.#pending_effect,
          () => {
            this.#pending_effect = null;
          }
        );
        this.is_pending = false;
      }
    });
  }
  #get_anchor() {
    var anchor = this.#anchor;
    if (this.is_pending) {
      this.#pending_anchor = create_text();
      this.#anchor.before(this.#pending_anchor);
      anchor = this.#pending_anchor;
    }
    return anchor;
  }
  /**
   * Defer an effect inside a pending boundary until the boundary resolves
   * @param {Effect} effect
   */
  defer_effect(effect2) {
    defer_effect(effect2, this.#dirty_effects, this.#maybe_dirty_effects);
  }
  /**
   * Returns `false` if the effect exists inside a boundary whose pending snippet is shown
   * @returns {boolean}
   */
  is_rendered() {
    return !this.is_pending && (!this.parent || this.parent.is_rendered());
  }
  has_pending_snippet() {
    return !!this.#props.pending;
  }
  /**
   * @param {() => Effect | null} fn
   */
  #run(fn) {
    var previous_effect = active_effect;
    var previous_reaction = active_reaction;
    var previous_ctx = component_context;
    set_active_effect(this.#effect);
    set_active_reaction(this.#effect);
    set_component_context(this.#effect.ctx);
    try {
      return fn();
    } catch (e2) {
      handle_error(e2);
      return null;
    } finally {
      set_active_effect(previous_effect);
      set_active_reaction(previous_reaction);
      set_component_context(previous_ctx);
    }
  }
  #show_pending_snippet() {
    const pending = (
      /** @type {(anchor: Node) => void} */
      this.#props.pending
    );
    if (this.#main_effect !== null) {
      this.#offscreen_fragment = document.createDocumentFragment();
      this.#offscreen_fragment.append(
        /** @type {TemplateNode} */
        this.#pending_anchor
      );
      move_effect(this.#main_effect, this.#offscreen_fragment);
    }
    if (this.#pending_effect === null) {
      this.#pending_effect = branch(() => pending(this.#anchor));
    }
  }
  /**
   * Updates the pending count associated with the currently visible pending snippet,
   * if any, such that we can replace the snippet with content once work is done
   * @param {1 | -1} d
   */
  #update_pending_count(d2) {
    if (!this.has_pending_snippet()) {
      if (this.parent) {
        this.parent.#update_pending_count(d2);
      }
      return;
    }
    this.#pending_count += d2;
    if (this.#pending_count === 0) {
      this.is_pending = false;
      for (const e2 of this.#dirty_effects) {
        set_signal_status(e2, DIRTY);
        schedule_effect(e2);
      }
      for (const e2 of this.#maybe_dirty_effects) {
        set_signal_status(e2, MAYBE_DIRTY);
        schedule_effect(e2);
      }
      this.#dirty_effects.clear();
      this.#maybe_dirty_effects.clear();
      if (this.#pending_effect) {
        pause_effect(this.#pending_effect, () => {
          this.#pending_effect = null;
        });
      }
      if (this.#offscreen_fragment) {
        this.#anchor.before(this.#offscreen_fragment);
        this.#offscreen_fragment = null;
      }
    }
  }
  /**
   * Update the source that powers `$effect.pending()` inside this boundary,
   * and controls when the current `pending` snippet (if any) is removed.
   * Do not call from inside the class
   * @param {1 | -1} d
   */
  update_pending_count(d2) {
    this.#update_pending_count(d2);
    this.#local_pending_count += d2;
    if (!this.#effect_pending || this.#pending_count_update_queued) return;
    this.#pending_count_update_queued = true;
    queue_micro_task(() => {
      this.#pending_count_update_queued = false;
      if (this.#effect_pending) {
        internal_set(this.#effect_pending, this.#local_pending_count);
      }
    });
  }
  get_effect_pending() {
    this.#effect_pending_subscriber();
    return get$1(
      /** @type {Source<number>} */
      this.#effect_pending
    );
  }
  /** @param {unknown} error */
  error(error) {
    var onerror = this.#props.onerror;
    let failed = this.#props.failed;
    if (this.#is_creating_fallback || !onerror && !failed) {
      throw error;
    }
    if (this.#main_effect) {
      destroy_effect(this.#main_effect);
      this.#main_effect = null;
    }
    if (this.#pending_effect) {
      destroy_effect(this.#pending_effect);
      this.#pending_effect = null;
    }
    if (this.#failed_effect) {
      destroy_effect(this.#failed_effect);
      this.#failed_effect = null;
    }
    var did_reset = false;
    var calling_on_error = false;
    const reset = () => {
      if (did_reset) {
        svelte_boundary_reset_noop();
        return;
      }
      did_reset = true;
      if (calling_on_error) {
        svelte_boundary_reset_onerror();
      }
      Batch.ensure();
      this.#local_pending_count = 0;
      if (this.#failed_effect !== null) {
        pause_effect(this.#failed_effect, () => {
          this.#failed_effect = null;
        });
      }
      this.is_pending = this.has_pending_snippet();
      this.#main_effect = this.#run(() => {
        this.#is_creating_fallback = false;
        return branch(() => this.#children(this.#anchor));
      });
      if (this.#pending_count > 0) {
        this.#show_pending_snippet();
      } else {
        this.is_pending = false;
      }
    };
    queue_micro_task(() => {
      try {
        calling_on_error = true;
        onerror?.(error, reset);
        calling_on_error = false;
      } catch (error2) {
        invoke_error_boundary(error2, this.#effect && this.#effect.parent);
      }
      if (failed) {
        this.#failed_effect = this.#run(() => {
          Batch.ensure();
          this.#is_creating_fallback = true;
          try {
            return branch(() => {
              failed(
                this.#anchor,
                () => error,
                () => reset
              );
            });
          } catch (error2) {
            invoke_error_boundary(
              error2,
              /** @type {Effect} */
              this.#effect.parent
            );
            return null;
          } finally {
            this.#is_creating_fallback = false;
          }
        });
      }
    });
  }
}
function flatten(blockers, sync, async, fn) {
  const d2 = is_runes() ? derived$1 : derived_safe_equal;
  var pending = blockers.filter((b2) => !b2.settled);
  if (async.length === 0 && pending.length === 0) {
    fn(sync.map(d2));
    return;
  }
  var batch = current_batch;
  var parent = (
    /** @type {Effect} */
    active_effect
  );
  var restore = capture();
  var blocker_promise = pending.length === 1 ? pending[0].promise : pending.length > 1 ? Promise.all(pending.map((b2) => b2.promise)) : null;
  function finish(values) {
    restore();
    try {
      fn(values);
    } catch (error) {
      if ((parent.f & DESTROYED) === 0) {
        invoke_error_boundary(error, parent);
      }
    }
    batch?.deactivate();
    unset_context();
  }
  if (async.length === 0) {
    blocker_promise.then(() => finish(sync.map(d2)));
    return;
  }
  function run2() {
    restore();
    Promise.all(async.map((expression) => /* @__PURE__ */ async_derived(expression))).then((result) => finish([...sync.map(d2), ...result])).catch((error) => invoke_error_boundary(error, parent));
  }
  if (blocker_promise) {
    blocker_promise.then(run2);
  } else {
    run2();
  }
}
function capture() {
  var previous_effect = active_effect;
  var previous_reaction = active_reaction;
  var previous_component_context = component_context;
  var previous_batch2 = current_batch;
  return function restore(activate_batch = true) {
    set_active_effect(previous_effect);
    set_active_reaction(previous_reaction);
    set_component_context(previous_component_context);
    if (activate_batch) previous_batch2?.activate();
  };
}
function unset_context() {
  set_active_effect(null);
  set_active_reaction(null);
  set_component_context(null);
}
// @__NO_SIDE_EFFECTS__
function derived$1(fn) {
  var flags2 = DERIVED | DIRTY;
  var parent_derived = active_reaction !== null && (active_reaction.f & DERIVED) !== 0 ? (
    /** @type {Derived} */
    active_reaction
  ) : null;
  if (active_effect !== null) {
    active_effect.f |= EFFECT_PRESERVED;
  }
  const signal = {
    ctx: component_context,
    deps: null,
    effects: null,
    equals,
    f: flags2,
    fn,
    reactions: null,
    rv: 0,
    v: (
      /** @type {V} */
      UNINITIALIZED
    ),
    wv: 0,
    parent: parent_derived ?? active_effect,
    ac: null
  };
  return signal;
}
// @__NO_SIDE_EFFECTS__
function async_derived(fn, label, location) {
  let parent = (
    /** @type {Effect | null} */
    active_effect
  );
  if (parent === null) {
    async_derived_orphan();
  }
  var boundary2 = (
    /** @type {Boundary} */
    parent.b
  );
  var promise = (
    /** @type {Promise<V>} */
    /** @type {unknown} */
    void 0
  );
  var signal = source(
    /** @type {V} */
    UNINITIALIZED
  );
  var should_suspend = !active_reaction;
  var deferreds = /* @__PURE__ */ new Map();
  async_effect(() => {
    var d2 = deferred();
    promise = d2.promise;
    try {
      Promise.resolve(fn()).then(d2.resolve, d2.reject).then(() => {
        if (batch === current_batch && batch.committed) {
          batch.deactivate();
        }
        unset_context();
      });
    } catch (error) {
      d2.reject(error);
      unset_context();
    }
    var batch = (
      /** @type {Batch} */
      current_batch
    );
    if (should_suspend) {
      var blocking = boundary2.is_rendered();
      boundary2.update_pending_count(1);
      batch.increment(blocking);
      deferreds.get(batch)?.reject(STALE_REACTION);
      deferreds.delete(batch);
      deferreds.set(batch, d2);
    }
    const handler = (value, error = void 0) => {
      batch.activate();
      if (error) {
        if (error !== STALE_REACTION) {
          signal.f |= ERROR_VALUE;
          internal_set(signal, error);
        }
      } else {
        if ((signal.f & ERROR_VALUE) !== 0) {
          signal.f ^= ERROR_VALUE;
        }
        internal_set(signal, value);
        for (const [b2, d3] of deferreds) {
          deferreds.delete(b2);
          if (b2 === batch) break;
          d3.reject(STALE_REACTION);
        }
      }
      if (should_suspend) {
        boundary2.update_pending_count(-1);
        batch.decrement(blocking);
      }
    };
    d2.promise.then(handler, (e2) => handler(null, e2 || "unknown"));
  });
  teardown(() => {
    for (const d2 of deferreds.values()) {
      d2.reject(STALE_REACTION);
    }
  });
  return new Promise((fulfil) => {
    function next(p2) {
      function go() {
        if (p2 === promise) {
          fulfil(signal);
        } else {
          next(promise);
        }
      }
      p2.then(go, go);
    }
    next(promise);
  });
}
// @__NO_SIDE_EFFECTS__
function user_derived(fn) {
  const d2 = /* @__PURE__ */ derived$1(fn);
  push_reaction_value(d2);
  return d2;
}
// @__NO_SIDE_EFFECTS__
function derived_safe_equal(fn) {
  const signal = /* @__PURE__ */ derived$1(fn);
  signal.equals = safe_equals;
  return signal;
}
function destroy_derived_effects(derived2) {
  var effects = derived2.effects;
  if (effects !== null) {
    derived2.effects = null;
    for (var i2 = 0; i2 < effects.length; i2 += 1) {
      destroy_effect(
        /** @type {Effect} */
        effects[i2]
      );
    }
  }
}
function get_derived_parent_effect(derived2) {
  var parent = derived2.parent;
  while (parent !== null) {
    if ((parent.f & DERIVED) === 0) {
      return (parent.f & DESTROYED) === 0 ? (
        /** @type {Effect} */
        parent
      ) : null;
    }
    parent = parent.parent;
  }
  return null;
}
function execute_derived(derived2) {
  var value;
  var prev_active_effect = active_effect;
  set_active_effect(get_derived_parent_effect(derived2));
  {
    try {
      derived2.f &= ~WAS_MARKED;
      destroy_derived_effects(derived2);
      value = update_reaction(derived2);
    } finally {
      set_active_effect(prev_active_effect);
    }
  }
  return value;
}
function update_derived(derived2) {
  var value = execute_derived(derived2);
  if (!derived2.equals(value)) {
    derived2.wv = increment_write_version();
    if (!current_batch?.is_fork || derived2.deps === null) {
      derived2.v = value;
      if (derived2.deps === null) {
        set_signal_status(derived2, CLEAN);
        return;
      }
    }
  }
  if (is_destroying_effect) {
    return;
  }
  if (batch_values !== null) {
    if (effect_tracking() || current_batch?.is_fork) {
      batch_values.set(derived2, value);
    }
  } else {
    update_derived_status(derived2);
  }
}
let eager_effects = /* @__PURE__ */ new Set();
const old_values = /* @__PURE__ */ new Map();
let eager_effects_deferred = false;
function source(v2, stack) {
  var signal = {
    f: 0,
    // TODO ideally we could skip this altogether, but it causes type errors
    v: v2,
    reactions: null,
    equals,
    rv: 0,
    wv: 0
  };
  return signal;
}
// @__NO_SIDE_EFFECTS__
function state(v2, stack) {
  const s2 = source(v2);
  push_reaction_value(s2);
  return s2;
}
// @__NO_SIDE_EFFECTS__
function mutable_source(initial_value, immutable = false, trackable = true) {
  const s2 = source(initial_value);
  if (!immutable) {
    s2.equals = safe_equals;
  }
  if (legacy_mode_flag && trackable && component_context !== null && component_context.l !== null) {
    (component_context.l.s ??= []).push(s2);
  }
  return s2;
}
function set(source2, value, should_proxy = false) {
  if (active_reaction !== null && // since we are untracking the function inside `$inspect.with` we need to add this check
  // to ensure we error if state is set inside an inspect effect
  (!untracking || (active_reaction.f & EAGER_EFFECT) !== 0) && is_runes() && (active_reaction.f & (DERIVED | BLOCK_EFFECT | ASYNC | EAGER_EFFECT)) !== 0 && (current_sources === null || !includes.call(current_sources, source2))) {
    state_unsafe_mutation();
  }
  let new_value = should_proxy ? proxy(value) : value;
  return internal_set(source2, new_value);
}
function internal_set(source2, value) {
  if (!source2.equals(value)) {
    var old_value = source2.v;
    if (is_destroying_effect) {
      old_values.set(source2, value);
    } else {
      old_values.set(source2, old_value);
    }
    source2.v = value;
    var batch = Batch.ensure();
    batch.capture(source2, old_value);
    if ((source2.f & DERIVED) !== 0) {
      const derived2 = (
        /** @type {Derived} */
        source2
      );
      if ((source2.f & DIRTY) !== 0) {
        execute_derived(derived2);
      }
      update_derived_status(derived2);
    }
    source2.wv = increment_write_version();
    mark_reactions(source2, DIRTY);
    if (is_runes() && active_effect !== null && (active_effect.f & CLEAN) !== 0 && (active_effect.f & (BRANCH_EFFECT | ROOT_EFFECT)) === 0) {
      if (untracked_writes === null) {
        set_untracked_writes([source2]);
      } else {
        untracked_writes.push(source2);
      }
    }
    if (!batch.is_fork && eager_effects.size > 0 && !eager_effects_deferred) {
      flush_eager_effects();
    }
  }
  return value;
}
function flush_eager_effects() {
  eager_effects_deferred = false;
  for (const effect2 of eager_effects) {
    if ((effect2.f & CLEAN) !== 0) {
      set_signal_status(effect2, MAYBE_DIRTY);
    }
    if (is_dirty(effect2)) {
      update_effect(effect2);
    }
  }
  eager_effects.clear();
}
function increment(source2) {
  set(source2, source2.v + 1);
}
function mark_reactions(signal, status) {
  var reactions = signal.reactions;
  if (reactions === null) return;
  var runes = is_runes();
  var length = reactions.length;
  for (var i2 = 0; i2 < length; i2++) {
    var reaction = reactions[i2];
    var flags2 = reaction.f;
    if (!runes && reaction === active_effect) continue;
    var not_dirty = (flags2 & DIRTY) === 0;
    if (not_dirty) {
      set_signal_status(reaction, status);
    }
    if ((flags2 & DERIVED) !== 0) {
      var derived2 = (
        /** @type {Derived} */
        reaction
      );
      batch_values?.delete(derived2);
      if ((flags2 & WAS_MARKED) === 0) {
        if (flags2 & CONNECTED) {
          reaction.f |= WAS_MARKED;
        }
        mark_reactions(derived2, MAYBE_DIRTY);
      }
    } else if (not_dirty) {
      if ((flags2 & BLOCK_EFFECT) !== 0 && eager_block_effects !== null) {
        eager_block_effects.add(
          /** @type {Effect} */
          reaction
        );
      }
      schedule_effect(
        /** @type {Effect} */
        reaction
      );
    }
  }
}
function proxy(value) {
  if (typeof value !== "object" || value === null || STATE_SYMBOL in value) {
    return value;
  }
  const prototype = get_prototype_of(value);
  if (prototype !== object_prototype && prototype !== array_prototype) {
    return value;
  }
  var sources = /* @__PURE__ */ new Map();
  var is_proxied_array = is_array(value);
  var version = /* @__PURE__ */ state(0);
  var parent_version = update_version;
  var with_parent = (fn) => {
    if (update_version === parent_version) {
      return fn();
    }
    var reaction = active_reaction;
    var version2 = update_version;
    set_active_reaction(null);
    set_update_version(parent_version);
    var result = fn();
    set_active_reaction(reaction);
    set_update_version(version2);
    return result;
  };
  if (is_proxied_array) {
    sources.set("length", /* @__PURE__ */ state(
      /** @type {any[]} */
      value.length
    ));
  }
  return new Proxy(
    /** @type {any} */
    value,
    {
      defineProperty(_2, prop2, descriptor) {
        if (!("value" in descriptor) || descriptor.configurable === false || descriptor.enumerable === false || descriptor.writable === false) {
          state_descriptors_fixed();
        }
        var s2 = sources.get(prop2);
        if (s2 === void 0) {
          s2 = with_parent(() => {
            var s3 = /* @__PURE__ */ state(descriptor.value);
            sources.set(prop2, s3);
            return s3;
          });
        } else {
          set(s2, descriptor.value, true);
        }
        return true;
      },
      deleteProperty(target, prop2) {
        var s2 = sources.get(prop2);
        if (s2 === void 0) {
          if (prop2 in target) {
            const s3 = with_parent(() => /* @__PURE__ */ state(UNINITIALIZED));
            sources.set(prop2, s3);
            increment(version);
          }
        } else {
          set(s2, UNINITIALIZED);
          increment(version);
        }
        return true;
      },
      get(target, prop2, receiver) {
        if (prop2 === STATE_SYMBOL) {
          return value;
        }
        var s2 = sources.get(prop2);
        var exists = prop2 in target;
        if (s2 === void 0 && (!exists || get_descriptor(target, prop2)?.writable)) {
          s2 = with_parent(() => {
            var p2 = proxy(exists ? target[prop2] : UNINITIALIZED);
            var s3 = /* @__PURE__ */ state(p2);
            return s3;
          });
          sources.set(prop2, s2);
        }
        if (s2 !== void 0) {
          var v2 = get$1(s2);
          return v2 === UNINITIALIZED ? void 0 : v2;
        }
        return Reflect.get(target, prop2, receiver);
      },
      getOwnPropertyDescriptor(target, prop2) {
        var descriptor = Reflect.getOwnPropertyDescriptor(target, prop2);
        if (descriptor && "value" in descriptor) {
          var s2 = sources.get(prop2);
          if (s2) descriptor.value = get$1(s2);
        } else if (descriptor === void 0) {
          var source2 = sources.get(prop2);
          var value2 = source2?.v;
          if (source2 !== void 0 && value2 !== UNINITIALIZED) {
            return {
              enumerable: true,
              configurable: true,
              value: value2,
              writable: true
            };
          }
        }
        return descriptor;
      },
      has(target, prop2) {
        if (prop2 === STATE_SYMBOL) {
          return true;
        }
        var s2 = sources.get(prop2);
        var has = s2 !== void 0 && s2.v !== UNINITIALIZED || Reflect.has(target, prop2);
        if (s2 !== void 0 || active_effect !== null && (!has || get_descriptor(target, prop2)?.writable)) {
          if (s2 === void 0) {
            s2 = with_parent(() => {
              var p2 = has ? proxy(target[prop2]) : UNINITIALIZED;
              var s3 = /* @__PURE__ */ state(p2);
              return s3;
            });
            sources.set(prop2, s2);
          }
          var value2 = get$1(s2);
          if (value2 === UNINITIALIZED) {
            return false;
          }
        }
        return has;
      },
      set(target, prop2, value2, receiver) {
        var s2 = sources.get(prop2);
        var has = prop2 in target;
        if (is_proxied_array && prop2 === "length") {
          for (var i2 = value2; i2 < /** @type {Source<number>} */
          s2.v; i2 += 1) {
            var other_s = sources.get(i2 + "");
            if (other_s !== void 0) {
              set(other_s, UNINITIALIZED);
            } else if (i2 in target) {
              other_s = with_parent(() => /* @__PURE__ */ state(UNINITIALIZED));
              sources.set(i2 + "", other_s);
            }
          }
        }
        if (s2 === void 0) {
          if (!has || get_descriptor(target, prop2)?.writable) {
            s2 = with_parent(() => /* @__PURE__ */ state(void 0));
            set(s2, proxy(value2));
            sources.set(prop2, s2);
          }
        } else {
          has = s2.v !== UNINITIALIZED;
          var p2 = with_parent(() => proxy(value2));
          set(s2, p2);
        }
        var descriptor = Reflect.getOwnPropertyDescriptor(target, prop2);
        if (descriptor?.set) {
          descriptor.set.call(receiver, value2);
        }
        if (!has) {
          if (is_proxied_array && typeof prop2 === "string") {
            var ls = (
              /** @type {Source<number>} */
              sources.get("length")
            );
            var n2 = Number(prop2);
            if (Number.isInteger(n2) && n2 >= ls.v) {
              set(ls, n2 + 1);
            }
          }
          increment(version);
        }
        return true;
      },
      ownKeys(target) {
        get$1(version);
        var own_keys = Reflect.ownKeys(target).filter((key2) => {
          var source3 = sources.get(key2);
          return source3 === void 0 || source3.v !== UNINITIALIZED;
        });
        for (var [key, source2] of sources) {
          if (source2.v !== UNINITIALIZED && !(key in target)) {
            own_keys.push(key);
          }
        }
        return own_keys;
      },
      setPrototypeOf() {
        state_prototype_fixed();
      }
    }
  );
}
function get_proxied_value(value) {
  try {
    if (value !== null && typeof value === "object" && STATE_SYMBOL in value) {
      return value[STATE_SYMBOL];
    }
  } catch {
  }
  return value;
}
function is(a2, b2) {
  return Object.is(get_proxied_value(a2), get_proxied_value(b2));
}
var $window;
var is_firefox;
var first_child_getter;
var next_sibling_getter;
function init_operations() {
  if ($window !== void 0) {
    return;
  }
  $window = window;
  is_firefox = /Firefox/.test(navigator.userAgent);
  var element_prototype = Element.prototype;
  var node_prototype = Node.prototype;
  var text_prototype = Text.prototype;
  first_child_getter = get_descriptor(node_prototype, "firstChild").get;
  next_sibling_getter = get_descriptor(node_prototype, "nextSibling").get;
  if (is_extensible(element_prototype)) {
    element_prototype.__click = void 0;
    element_prototype.__className = void 0;
    element_prototype.__attributes = null;
    element_prototype.__style = void 0;
    element_prototype.__e = void 0;
  }
  if (is_extensible(text_prototype)) {
    text_prototype.__t = void 0;
  }
}
function create_text(value = "") {
  return document.createTextNode(value);
}
// @__NO_SIDE_EFFECTS__
function get_first_child(node) {
  return (
    /** @type {TemplateNode | null} */
    first_child_getter.call(node)
  );
}
// @__NO_SIDE_EFFECTS__
function get_next_sibling(node) {
  return (
    /** @type {TemplateNode | null} */
    next_sibling_getter.call(node)
  );
}
function child(node, is_text) {
  {
    return /* @__PURE__ */ get_first_child(node);
  }
}
function first_child(node, is_text = false) {
  {
    var first = /* @__PURE__ */ get_first_child(node);
    if (first instanceof Comment && first.data === "") return /* @__PURE__ */ get_next_sibling(first);
    return first;
  }
}
function sibling(node, count = 1, is_text = false) {
  let next_sibling = node;
  while (count--) {
    next_sibling = /** @type {TemplateNode} */
    /* @__PURE__ */ get_next_sibling(next_sibling);
  }
  {
    return next_sibling;
  }
}
function clear_text_content(node) {
  node.textContent = "";
}
function should_defer_append() {
  return false;
}
let listening_to_form_reset = false;
function add_form_reset_listener() {
  if (!listening_to_form_reset) {
    listening_to_form_reset = true;
    document.addEventListener(
      "reset",
      (evt) => {
        Promise.resolve().then(() => {
          if (!evt.defaultPrevented) {
            for (
              const e2 of
              /**@type {HTMLFormElement} */
              evt.target.elements
            ) {
              e2.__on_r?.();
            }
          }
        });
      },
      // In the capture phase to guarantee we get noticed of it (no possibility of stopPropagation)
      { capture: true }
    );
  }
}
function without_reactive_context(fn) {
  var previous_reaction = active_reaction;
  var previous_effect = active_effect;
  set_active_reaction(null);
  set_active_effect(null);
  try {
    return fn();
  } finally {
    set_active_reaction(previous_reaction);
    set_active_effect(previous_effect);
  }
}
function listen_to_event_and_reset_event(element, event2, handler, on_reset = handler) {
  element.addEventListener(event2, () => without_reactive_context(handler));
  const prev = element.__on_r;
  if (prev) {
    element.__on_r = () => {
      prev();
      on_reset(true);
    };
  } else {
    element.__on_r = () => on_reset(true);
  }
  add_form_reset_listener();
}
function validate_effect(rune) {
  if (active_effect === null) {
    if (active_reaction === null) {
      effect_orphan();
    }
    effect_in_unowned_derived();
  }
  if (is_destroying_effect) {
    effect_in_teardown();
  }
}
function push_effect(effect2, parent_effect) {
  var parent_last = parent_effect.last;
  if (parent_last === null) {
    parent_effect.last = parent_effect.first = effect2;
  } else {
    parent_last.next = effect2;
    effect2.prev = parent_last;
    parent_effect.last = effect2;
  }
}
function create_effect(type, fn, sync) {
  var parent = active_effect;
  if (parent !== null && (parent.f & INERT) !== 0) {
    type |= INERT;
  }
  var effect2 = {
    ctx: component_context,
    deps: null,
    nodes: null,
    f: type | DIRTY | CONNECTED,
    first: null,
    fn,
    last: null,
    next: null,
    parent,
    b: parent && parent.b,
    prev: null,
    teardown: null,
    wv: 0,
    ac: null
  };
  if (sync) {
    try {
      update_effect(effect2);
      effect2.f |= EFFECT_RAN;
    } catch (e3) {
      destroy_effect(effect2);
      throw e3;
    }
  } else if (fn !== null) {
    schedule_effect(effect2);
  }
  var e2 = effect2;
  if (sync && e2.deps === null && e2.teardown === null && e2.nodes === null && e2.first === e2.last && // either `null`, or a singular child
  (e2.f & EFFECT_PRESERVED) === 0) {
    e2 = e2.first;
    if ((type & BLOCK_EFFECT) !== 0 && (type & EFFECT_TRANSPARENT) !== 0 && e2 !== null) {
      e2.f |= EFFECT_TRANSPARENT;
    }
  }
  if (e2 !== null) {
    e2.parent = parent;
    if (parent !== null) {
      push_effect(e2, parent);
    }
    if (active_reaction !== null && (active_reaction.f & DERIVED) !== 0 && (type & ROOT_EFFECT) === 0) {
      var derived2 = (
        /** @type {Derived} */
        active_reaction
      );
      (derived2.effects ??= []).push(e2);
    }
  }
  return effect2;
}
function effect_tracking() {
  return active_reaction !== null && !untracking;
}
function teardown(fn) {
  const effect2 = create_effect(RENDER_EFFECT, null, false);
  set_signal_status(effect2, CLEAN);
  effect2.teardown = fn;
  return effect2;
}
function user_effect(fn) {
  validate_effect();
  var flags2 = (
    /** @type {Effect} */
    active_effect.f
  );
  var defer = !active_reaction && (flags2 & BRANCH_EFFECT) !== 0 && (flags2 & EFFECT_RAN) === 0;
  if (defer) {
    var context = (
      /** @type {ComponentContext} */
      component_context
    );
    (context.e ??= []).push(fn);
  } else {
    return create_user_effect(fn);
  }
}
function create_user_effect(fn) {
  return create_effect(EFFECT | USER_EFFECT, fn, false);
}
function user_pre_effect(fn) {
  validate_effect();
  return create_effect(RENDER_EFFECT | USER_EFFECT, fn, true);
}
function component_root(fn) {
  Batch.ensure();
  const effect2 = create_effect(ROOT_EFFECT | EFFECT_PRESERVED, fn, true);
  return (options = {}) => {
    return new Promise((fulfil) => {
      if (options.outro) {
        pause_effect(effect2, () => {
          destroy_effect(effect2);
          fulfil(void 0);
        });
      } else {
        destroy_effect(effect2);
        fulfil(void 0);
      }
    });
  };
}
function effect(fn) {
  return create_effect(EFFECT, fn, false);
}
function async_effect(fn) {
  return create_effect(ASYNC | EFFECT_PRESERVED, fn, true);
}
function render_effect(fn, flags2 = 0) {
  return create_effect(RENDER_EFFECT | flags2, fn, true);
}
function template_effect(fn, sync = [], async = [], blockers = []) {
  flatten(blockers, sync, async, (values) => {
    create_effect(RENDER_EFFECT, () => fn(...values.map(get$1)), true);
  });
}
function block(fn, flags2 = 0) {
  var effect2 = create_effect(BLOCK_EFFECT | flags2, fn, true);
  return effect2;
}
function branch(fn) {
  return create_effect(BRANCH_EFFECT | EFFECT_PRESERVED, fn, true);
}
function execute_effect_teardown(effect2) {
  var teardown2 = effect2.teardown;
  if (teardown2 !== null) {
    const previously_destroying_effect = is_destroying_effect;
    const previous_reaction = active_reaction;
    set_is_destroying_effect(true);
    set_active_reaction(null);
    try {
      teardown2.call(null);
    } finally {
      set_is_destroying_effect(previously_destroying_effect);
      set_active_reaction(previous_reaction);
    }
  }
}
function destroy_effect_children(signal, remove_dom = false) {
  var effect2 = signal.first;
  signal.first = signal.last = null;
  while (effect2 !== null) {
    const controller = effect2.ac;
    if (controller !== null) {
      without_reactive_context(() => {
        controller.abort(STALE_REACTION);
      });
    }
    var next = effect2.next;
    if ((effect2.f & ROOT_EFFECT) !== 0) {
      effect2.parent = null;
    } else {
      destroy_effect(effect2, remove_dom);
    }
    effect2 = next;
  }
}
function destroy_block_effect_children(signal) {
  var effect2 = signal.first;
  while (effect2 !== null) {
    var next = effect2.next;
    if ((effect2.f & BRANCH_EFFECT) === 0) {
      destroy_effect(effect2);
    }
    effect2 = next;
  }
}
function destroy_effect(effect2, remove_dom = true) {
  var removed = false;
  if ((remove_dom || (effect2.f & HEAD_EFFECT) !== 0) && effect2.nodes !== null && effect2.nodes.end !== null) {
    remove_effect_dom(
      effect2.nodes.start,
      /** @type {TemplateNode} */
      effect2.nodes.end
    );
    removed = true;
  }
  destroy_effect_children(effect2, remove_dom && !removed);
  remove_reactions(effect2, 0);
  set_signal_status(effect2, DESTROYED);
  var transitions = effect2.nodes && effect2.nodes.t;
  if (transitions !== null) {
    for (const transition of transitions) {
      transition.stop();
    }
  }
  execute_effect_teardown(effect2);
  var parent = effect2.parent;
  if (parent !== null && parent.first !== null) {
    unlink_effect(effect2);
  }
  effect2.next = effect2.prev = effect2.teardown = effect2.ctx = effect2.deps = effect2.fn = effect2.nodes = effect2.ac = null;
}
function remove_effect_dom(node, end) {
  while (node !== null) {
    var next = node === end ? null : /* @__PURE__ */ get_next_sibling(node);
    node.remove();
    node = next;
  }
}
function unlink_effect(effect2) {
  var parent = effect2.parent;
  var prev = effect2.prev;
  var next = effect2.next;
  if (prev !== null) prev.next = next;
  if (next !== null) next.prev = prev;
  if (parent !== null) {
    if (parent.first === effect2) parent.first = next;
    if (parent.last === effect2) parent.last = prev;
  }
}
function pause_effect(effect2, callback, destroy = true) {
  var transitions = [];
  pause_children(effect2, transitions, true);
  var fn = () => {
    if (destroy) destroy_effect(effect2);
    if (callback) callback();
  };
  var remaining = transitions.length;
  if (remaining > 0) {
    var check = () => --remaining || fn();
    for (var transition of transitions) {
      transition.out(check);
    }
  } else {
    fn();
  }
}
function pause_children(effect2, transitions, local) {
  if ((effect2.f & INERT) !== 0) return;
  effect2.f ^= INERT;
  var t2 = effect2.nodes && effect2.nodes.t;
  if (t2 !== null) {
    for (const transition of t2) {
      if (transition.is_global || local) {
        transitions.push(transition);
      }
    }
  }
  var child2 = effect2.first;
  while (child2 !== null) {
    var sibling2 = child2.next;
    var transparent = (child2.f & EFFECT_TRANSPARENT) !== 0 || // If this is a branch effect without a block effect parent,
    // it means the parent block effect was pruned. In that case,
    // transparency information was transferred to the branch effect.
    (child2.f & BRANCH_EFFECT) !== 0 && (effect2.f & BLOCK_EFFECT) !== 0;
    pause_children(child2, transitions, transparent ? local : false);
    child2 = sibling2;
  }
}
function resume_effect(effect2) {
  resume_children(effect2, true);
}
function resume_children(effect2, local) {
  if ((effect2.f & INERT) === 0) return;
  effect2.f ^= INERT;
  if ((effect2.f & CLEAN) === 0) {
    set_signal_status(effect2, DIRTY);
    schedule_effect(effect2);
  }
  var child2 = effect2.first;
  while (child2 !== null) {
    var sibling2 = child2.next;
    var transparent = (child2.f & EFFECT_TRANSPARENT) !== 0 || (child2.f & BRANCH_EFFECT) !== 0;
    resume_children(child2, transparent ? local : false);
    child2 = sibling2;
  }
  var t2 = effect2.nodes && effect2.nodes.t;
  if (t2 !== null) {
    for (const transition of t2) {
      if (transition.is_global || local) {
        transition.in();
      }
    }
  }
}
function move_effect(effect2, fragment) {
  if (!effect2.nodes) return;
  var node = effect2.nodes.start;
  var end = effect2.nodes.end;
  while (node !== null) {
    var next = node === end ? null : /* @__PURE__ */ get_next_sibling(node);
    fragment.append(node);
    node = next;
  }
}
let is_updating_effect = false;
let is_destroying_effect = false;
function set_is_destroying_effect(value) {
  is_destroying_effect = value;
}
let active_reaction = null;
let untracking = false;
function set_active_reaction(reaction) {
  active_reaction = reaction;
}
let active_effect = null;
function set_active_effect(effect2) {
  active_effect = effect2;
}
let current_sources = null;
function push_reaction_value(value) {
  if (active_reaction !== null && true) {
    if (current_sources === null) {
      current_sources = [value];
    } else {
      current_sources.push(value);
    }
  }
}
let new_deps = null;
let skipped_deps = 0;
let untracked_writes = null;
function set_untracked_writes(value) {
  untracked_writes = value;
}
let write_version = 1;
let read_version = 0;
let update_version = read_version;
function set_update_version(value) {
  update_version = value;
}
function increment_write_version() {
  return ++write_version;
}
function is_dirty(reaction) {
  var flags2 = reaction.f;
  if ((flags2 & DIRTY) !== 0) {
    return true;
  }
  if (flags2 & DERIVED) {
    reaction.f &= ~WAS_MARKED;
  }
  if ((flags2 & MAYBE_DIRTY) !== 0) {
    var dependencies = (
      /** @type {Value[]} */
      reaction.deps
    );
    var length = dependencies.length;
    for (var i2 = 0; i2 < length; i2++) {
      var dependency = dependencies[i2];
      if (is_dirty(
        /** @type {Derived} */
        dependency
      )) {
        update_derived(
          /** @type {Derived} */
          dependency
        );
      }
      if (dependency.wv > reaction.wv) {
        return true;
      }
    }
    if ((flags2 & CONNECTED) !== 0 && // During time traveling we don't want to reset the status so that
    // traversal of the graph in the other batches still happens
    batch_values === null) {
      set_signal_status(reaction, CLEAN);
    }
  }
  return false;
}
function schedule_possible_effect_self_invalidation(signal, effect2, root2 = true) {
  var reactions = signal.reactions;
  if (reactions === null) return;
  if (current_sources !== null && includes.call(current_sources, signal)) {
    return;
  }
  for (var i2 = 0; i2 < reactions.length; i2++) {
    var reaction = reactions[i2];
    if ((reaction.f & DERIVED) !== 0) {
      schedule_possible_effect_self_invalidation(
        /** @type {Derived} */
        reaction,
        effect2,
        false
      );
    } else if (effect2 === reaction) {
      if (root2) {
        set_signal_status(reaction, DIRTY);
      } else if ((reaction.f & CLEAN) !== 0) {
        set_signal_status(reaction, MAYBE_DIRTY);
      }
      schedule_effect(
        /** @type {Effect} */
        reaction
      );
    }
  }
}
function update_reaction(reaction) {
  var previous_deps = new_deps;
  var previous_skipped_deps = skipped_deps;
  var previous_untracked_writes = untracked_writes;
  var previous_reaction = active_reaction;
  var previous_sources = current_sources;
  var previous_component_context = component_context;
  var previous_untracking = untracking;
  var previous_update_version = update_version;
  var flags2 = reaction.f;
  new_deps = /** @type {null | Value[]} */
  null;
  skipped_deps = 0;
  untracked_writes = null;
  active_reaction = (flags2 & (BRANCH_EFFECT | ROOT_EFFECT)) === 0 ? reaction : null;
  current_sources = null;
  set_component_context(reaction.ctx);
  untracking = false;
  update_version = ++read_version;
  if (reaction.ac !== null) {
    without_reactive_context(() => {
      reaction.ac.abort(STALE_REACTION);
    });
    reaction.ac = null;
  }
  try {
    reaction.f |= REACTION_IS_UPDATING;
    var fn = (
      /** @type {Function} */
      reaction.fn
    );
    var result = fn();
    var deps = reaction.deps;
    var is_fork = current_batch?.is_fork;
    if (new_deps !== null) {
      var i2;
      if (!is_fork) {
        remove_reactions(reaction, skipped_deps);
      }
      if (deps !== null && skipped_deps > 0) {
        deps.length = skipped_deps + new_deps.length;
        for (i2 = 0; i2 < new_deps.length; i2++) {
          deps[skipped_deps + i2] = new_deps[i2];
        }
      } else {
        reaction.deps = deps = new_deps;
      }
      if (effect_tracking() && (reaction.f & CONNECTED) !== 0) {
        for (i2 = skipped_deps; i2 < deps.length; i2++) {
          (deps[i2].reactions ??= []).push(reaction);
        }
      }
    } else if (!is_fork && deps !== null && skipped_deps < deps.length) {
      remove_reactions(reaction, skipped_deps);
      deps.length = skipped_deps;
    }
    if (is_runes() && untracked_writes !== null && !untracking && deps !== null && (reaction.f & (DERIVED | MAYBE_DIRTY | DIRTY)) === 0) {
      for (i2 = 0; i2 < /** @type {Source[]} */
      untracked_writes.length; i2++) {
        schedule_possible_effect_self_invalidation(
          untracked_writes[i2],
          /** @type {Effect} */
          reaction
        );
      }
    }
    if (previous_reaction !== null && previous_reaction !== reaction) {
      read_version++;
      if (previous_reaction.deps !== null) {
        for (let i3 = 0; i3 < previous_skipped_deps; i3 += 1) {
          previous_reaction.deps[i3].rv = read_version;
        }
      }
      if (previous_deps !== null) {
        for (const dep of previous_deps) {
          dep.rv = read_version;
        }
      }
      if (untracked_writes !== null) {
        if (previous_untracked_writes === null) {
          previous_untracked_writes = untracked_writes;
        } else {
          previous_untracked_writes.push(.../** @type {Source[]} */
          untracked_writes);
        }
      }
    }
    if ((reaction.f & ERROR_VALUE) !== 0) {
      reaction.f ^= ERROR_VALUE;
    }
    return result;
  } catch (error) {
    return handle_error(error);
  } finally {
    reaction.f ^= REACTION_IS_UPDATING;
    new_deps = previous_deps;
    skipped_deps = previous_skipped_deps;
    untracked_writes = previous_untracked_writes;
    active_reaction = previous_reaction;
    current_sources = previous_sources;
    set_component_context(previous_component_context);
    untracking = previous_untracking;
    update_version = previous_update_version;
  }
}
function remove_reaction(signal, dependency) {
  let reactions = dependency.reactions;
  if (reactions !== null) {
    var index2 = index_of.call(reactions, signal);
    if (index2 !== -1) {
      var new_length = reactions.length - 1;
      if (new_length === 0) {
        reactions = dependency.reactions = null;
      } else {
        reactions[index2] = reactions[new_length];
        reactions.pop();
      }
    }
  }
  if (reactions === null && (dependency.f & DERIVED) !== 0 && // Destroying a child effect while updating a parent effect can cause a dependency to appear
  // to be unused, when in fact it is used by the currently-updating parent. Checking `new_deps`
  // allows us to skip the expensive work of disconnecting and immediately reconnecting it
  (new_deps === null || !includes.call(new_deps, dependency))) {
    var derived2 = (
      /** @type {Derived} */
      dependency
    );
    if ((derived2.f & CONNECTED) !== 0) {
      derived2.f ^= CONNECTED;
      derived2.f &= ~WAS_MARKED;
    }
    update_derived_status(derived2);
    destroy_derived_effects(derived2);
    remove_reactions(derived2, 0);
  }
}
function remove_reactions(signal, start_index) {
  var dependencies = signal.deps;
  if (dependencies === null) return;
  for (var i2 = start_index; i2 < dependencies.length; i2++) {
    remove_reaction(signal, dependencies[i2]);
  }
}
function update_effect(effect2) {
  var flags2 = effect2.f;
  if ((flags2 & DESTROYED) !== 0) {
    return;
  }
  set_signal_status(effect2, CLEAN);
  var previous_effect = active_effect;
  var was_updating_effect = is_updating_effect;
  active_effect = effect2;
  is_updating_effect = true;
  try {
    if ((flags2 & (BLOCK_EFFECT | MANAGED_EFFECT)) !== 0) {
      destroy_block_effect_children(effect2);
    } else {
      destroy_effect_children(effect2);
    }
    execute_effect_teardown(effect2);
    var teardown2 = update_reaction(effect2);
    effect2.teardown = typeof teardown2 === "function" ? teardown2 : null;
    effect2.wv = write_version;
    var dep;
    if (DEV && tracing_mode_flag && (effect2.f & DIRTY) !== 0 && effect2.deps !== null) ;
  } finally {
    is_updating_effect = was_updating_effect;
    active_effect = previous_effect;
  }
}
async function tick() {
  await Promise.resolve();
  flushSync();
}
function get$1(signal) {
  var flags2 = signal.f;
  var is_derived = (flags2 & DERIVED) !== 0;
  if (active_reaction !== null && !untracking) {
    var destroyed = active_effect !== null && (active_effect.f & DESTROYED) !== 0;
    if (!destroyed && (current_sources === null || !includes.call(current_sources, signal))) {
      var deps = active_reaction.deps;
      if ((active_reaction.f & REACTION_IS_UPDATING) !== 0) {
        if (signal.rv < read_version) {
          signal.rv = read_version;
          if (new_deps === null && deps !== null && deps[skipped_deps] === signal) {
            skipped_deps++;
          } else if (new_deps === null) {
            new_deps = [signal];
          } else {
            new_deps.push(signal);
          }
        }
      } else {
        (active_reaction.deps ??= []).push(signal);
        var reactions = signal.reactions;
        if (reactions === null) {
          signal.reactions = [active_reaction];
        } else if (!includes.call(reactions, active_reaction)) {
          reactions.push(active_reaction);
        }
      }
    }
  }
  if (is_destroying_effect && old_values.has(signal)) {
    return old_values.get(signal);
  }
  if (is_derived) {
    var derived2 = (
      /** @type {Derived} */
      signal
    );
    if (is_destroying_effect) {
      var value = derived2.v;
      if ((derived2.f & CLEAN) === 0 && derived2.reactions !== null || depends_on_old_values(derived2)) {
        value = execute_derived(derived2);
      }
      old_values.set(derived2, value);
      return value;
    }
    var should_connect = (derived2.f & CONNECTED) === 0 && !untracking && active_reaction !== null && (is_updating_effect || (active_reaction.f & CONNECTED) !== 0);
    var is_new = derived2.deps === null;
    if (is_dirty(derived2)) {
      if (should_connect) {
        derived2.f |= CONNECTED;
      }
      update_derived(derived2);
    }
    if (should_connect && !is_new) {
      reconnect(derived2);
    }
  }
  if (batch_values?.has(signal)) {
    return batch_values.get(signal);
  }
  if ((signal.f & ERROR_VALUE) !== 0) {
    throw signal.v;
  }
  return signal.v;
}
function reconnect(derived2) {
  if (derived2.deps === null) return;
  derived2.f |= CONNECTED;
  for (const dep of derived2.deps) {
    (dep.reactions ??= []).push(derived2);
    if ((dep.f & DERIVED) !== 0 && (dep.f & CONNECTED) === 0) {
      reconnect(
        /** @type {Derived} */
        dep
      );
    }
  }
}
function depends_on_old_values(derived2) {
  if (derived2.v === UNINITIALIZED) return true;
  if (derived2.deps === null) return false;
  for (const dep of derived2.deps) {
    if (old_values.has(dep)) {
      return true;
    }
    if ((dep.f & DERIVED) !== 0 && depends_on_old_values(
      /** @type {Derived} */
      dep
    )) {
      return true;
    }
  }
  return false;
}
function untrack(fn) {
  var previous_untracking = untracking;
  try {
    untracking = true;
    return fn();
  } finally {
    untracking = previous_untracking;
  }
}
function deep_read_state(value) {
  if (typeof value !== "object" || !value || value instanceof EventTarget) {
    return;
  }
  if (STATE_SYMBOL in value) {
    deep_read(value);
  } else if (!Array.isArray(value)) {
    for (let key in value) {
      const prop2 = value[key];
      if (typeof prop2 === "object" && prop2 && STATE_SYMBOL in prop2) {
        deep_read(prop2);
      }
    }
  }
}
function deep_read(value, visited = /* @__PURE__ */ new Set()) {
  if (typeof value === "object" && value !== null && // We don't want to traverse DOM elements
  !(value instanceof EventTarget) && !visited.has(value)) {
    visited.add(value);
    if (value instanceof Date) {
      value.getTime();
    }
    for (let key in value) {
      try {
        deep_read(value[key], visited);
      } catch (e2) {
      }
    }
    const proto = get_prototype_of(value);
    if (proto !== Object.prototype && proto !== Array.prototype && proto !== Map.prototype && proto !== Set.prototype && proto !== Date.prototype) {
      const descriptors = get_descriptors(proto);
      for (let key in descriptors) {
        const get2 = descriptors[key].get;
        if (get2) {
          try {
            get2.call(value);
          } catch (e2) {
          }
        }
      }
    }
  }
}
const all_registered_events = /* @__PURE__ */ new Set();
const root_event_handles = /* @__PURE__ */ new Set();
function create_event(event_name, dom, handler, options = {}) {
  function target_handler(event2) {
    if (!options.capture) {
      handle_event_propagation.call(dom, event2);
    }
    if (!event2.cancelBubble) {
      return without_reactive_context(() => {
        return handler?.call(this, event2);
      });
    }
  }
  if (event_name.startsWith("pointer") || event_name.startsWith("touch") || event_name === "wheel") {
    queue_micro_task(() => {
      dom.addEventListener(event_name, target_handler, options);
    });
  } else {
    dom.addEventListener(event_name, target_handler, options);
  }
  return target_handler;
}
function event(event_name, dom, handler, capture2, passive) {
  var options = { capture: capture2, passive };
  var target_handler = create_event(event_name, dom, handler, options);
  if (dom === document.body || // @ts-ignore
  dom === window || // @ts-ignore
  dom === document || // Firefox has quirky behavior, it can happen that we still get "canplay" events when the element is already removed
  dom instanceof HTMLMediaElement) {
    teardown(() => {
      dom.removeEventListener(event_name, target_handler, options);
    });
  }
}
function delegate(events) {
  for (var i2 = 0; i2 < events.length; i2++) {
    all_registered_events.add(events[i2]);
  }
  for (var fn of root_event_handles) {
    fn(events);
  }
}
let last_propagated_event = null;
function handle_event_propagation(event2) {
  var handler_element = this;
  var owner_document = (
    /** @type {Node} */
    handler_element.ownerDocument
  );
  var event_name = event2.type;
  var path = event2.composedPath?.() || [];
  var current_target = (
    /** @type {null | Element} */
    path[0] || event2.target
  );
  last_propagated_event = event2;
  var path_idx = 0;
  var handled_at = last_propagated_event === event2 && event2.__root;
  if (handled_at) {
    var at_idx = path.indexOf(handled_at);
    if (at_idx !== -1 && (handler_element === document || handler_element === /** @type {any} */
    window)) {
      event2.__root = handler_element;
      return;
    }
    var handler_idx = path.indexOf(handler_element);
    if (handler_idx === -1) {
      return;
    }
    if (at_idx <= handler_idx) {
      path_idx = at_idx;
    }
  }
  current_target = /** @type {Element} */
  path[path_idx] || event2.target;
  if (current_target === handler_element) return;
  define_property(event2, "currentTarget", {
    configurable: true,
    get() {
      return current_target || owner_document;
    }
  });
  var previous_reaction = active_reaction;
  var previous_effect = active_effect;
  set_active_reaction(null);
  set_active_effect(null);
  try {
    var throw_error;
    var other_errors = [];
    while (current_target !== null) {
      var parent_element = current_target.assignedSlot || current_target.parentNode || /** @type {any} */
      current_target.host || null;
      try {
        var delegated = current_target["__" + event_name];
        if (delegated != null && (!/** @type {any} */
        current_target.disabled || // DOM could've been updated already by the time this is reached, so we check this as well
        // -> the target could not have been disabled because it emits the event in the first place
        event2.target === current_target)) {
          delegated.call(current_target, event2);
        }
      } catch (error) {
        if (throw_error) {
          other_errors.push(error);
        } else {
          throw_error = error;
        }
      }
      if (event2.cancelBubble || parent_element === handler_element || parent_element === null) {
        break;
      }
      current_target = parent_element;
    }
    if (throw_error) {
      for (let error of other_errors) {
        queueMicrotask(() => {
          throw error;
        });
      }
      throw throw_error;
    }
  } finally {
    event2.__root = handler_element;
    delete event2.currentTarget;
    set_active_reaction(previous_reaction);
    set_active_effect(previous_effect);
  }
}
function create_fragment_from_html(html2) {
  var elem = document.createElement("template");
  elem.innerHTML = html2.replaceAll("<!>", "<!---->");
  return elem.content;
}
function assign_nodes(start, end) {
  var effect2 = (
    /** @type {Effect} */
    active_effect
  );
  if (effect2.nodes === null) {
    effect2.nodes = { start, end, a: null, t: null };
  }
}
// @__NO_SIDE_EFFECTS__
function from_html(content, flags2) {
  var is_fragment = (flags2 & TEMPLATE_FRAGMENT) !== 0;
  var use_import_node = (flags2 & TEMPLATE_USE_IMPORT_NODE) !== 0;
  var node;
  var has_start = !content.startsWith("<!>");
  return () => {
    if (node === void 0) {
      node = create_fragment_from_html(has_start ? content : "<!>" + content);
      if (!is_fragment) node = /** @type {TemplateNode} */
      /* @__PURE__ */ get_first_child(node);
    }
    var clone2 = (
      /** @type {TemplateNode} */
      use_import_node || is_firefox ? document.importNode(node, true) : node.cloneNode(true)
    );
    if (is_fragment) {
      var start = (
        /** @type {TemplateNode} */
        /* @__PURE__ */ get_first_child(clone2)
      );
      var end = (
        /** @type {TemplateNode} */
        clone2.lastChild
      );
      assign_nodes(start, end);
    } else {
      assign_nodes(clone2, clone2);
    }
    return clone2;
  };
}
// @__NO_SIDE_EFFECTS__
function from_namespace(content, flags2, ns = "svg") {
  var has_start = !content.startsWith("<!>");
  var wrapped = `<${ns}>${has_start ? content : "<!>" + content}</${ns}>`;
  var node;
  return () => {
    if (!node) {
      var fragment = (
        /** @type {DocumentFragment} */
        create_fragment_from_html(wrapped)
      );
      var root2 = (
        /** @type {Element} */
        /* @__PURE__ */ get_first_child(fragment)
      );
      {
        node = /** @type {Element} */
        /* @__PURE__ */ get_first_child(root2);
      }
    }
    var clone2 = (
      /** @type {TemplateNode} */
      node.cloneNode(true)
    );
    {
      assign_nodes(clone2, clone2);
    }
    return clone2;
  };
}
// @__NO_SIDE_EFFECTS__
function from_svg(content, flags2) {
  return /* @__PURE__ */ from_namespace(content, flags2, "svg");
}
function text$1(value = "") {
  {
    var t2 = create_text(value + "");
    assign_nodes(t2, t2);
    return t2;
  }
}
function comment() {
  var frag = document.createDocumentFragment();
  var start = document.createComment("");
  var anchor = create_text();
  frag.append(start, anchor);
  assign_nodes(start, anchor);
  return frag;
}
function append(anchor, dom) {
  if (anchor === null) {
    return;
  }
  anchor.before(
    /** @type {Node} */
    dom
  );
}
const PASSIVE_EVENTS = ["touchstart", "touchmove"];
function is_passive_event(name) {
  return PASSIVE_EVENTS.includes(name);
}
function set_text(text2, value) {
  var str = value == null ? "" : typeof value === "object" ? value + "" : value;
  if (str !== (text2.__t ??= text2.nodeValue)) {
    text2.__t = str;
    text2.nodeValue = str + "";
  }
}
function mount(component, options) {
  return _mount(component, options);
}
const document_listeners = /* @__PURE__ */ new Map();
function _mount(Component, { target, anchor, props = {}, events, context, intro = true }) {
  init_operations();
  var registered_events = /* @__PURE__ */ new Set();
  var event_handle = (events2) => {
    for (var i2 = 0; i2 < events2.length; i2++) {
      var event_name = events2[i2];
      if (registered_events.has(event_name)) continue;
      registered_events.add(event_name);
      var passive = is_passive_event(event_name);
      target.addEventListener(event_name, handle_event_propagation, { passive });
      var n2 = document_listeners.get(event_name);
      if (n2 === void 0) {
        document.addEventListener(event_name, handle_event_propagation, { passive });
        document_listeners.set(event_name, 1);
      } else {
        document_listeners.set(event_name, n2 + 1);
      }
    }
  };
  event_handle(array_from(all_registered_events));
  root_event_handles.add(event_handle);
  var component = void 0;
  var unmount2 = component_root(() => {
    var anchor_node = anchor ?? target.appendChild(create_text());
    boundary(
      /** @type {TemplateNode} */
      anchor_node,
      {
        pending: () => {
        }
      },
      (anchor_node2) => {
        if (context) {
          push({});
          var ctx = (
            /** @type {ComponentContext} */
            component_context
          );
          ctx.c = context;
        }
        if (events) {
          props.$$events = events;
        }
        component = Component(anchor_node2, props) || {};
        if (context) {
          pop();
        }
      }
    );
    return () => {
      for (var event_name of registered_events) {
        target.removeEventListener(event_name, handle_event_propagation);
        var n2 = (
          /** @type {number} */
          document_listeners.get(event_name)
        );
        if (--n2 === 0) {
          document.removeEventListener(event_name, handle_event_propagation);
          document_listeners.delete(event_name);
        } else {
          document_listeners.set(event_name, n2);
        }
      }
      root_event_handles.delete(event_handle);
      if (anchor_node !== anchor) {
        anchor_node.parentNode?.removeChild(anchor_node);
      }
    };
  });
  mounted_components.set(component, unmount2);
  return component;
}
let mounted_components = /* @__PURE__ */ new WeakMap();
function unmount(component, options) {
  const fn = mounted_components.get(component);
  if (fn) {
    mounted_components.delete(component);
    return fn(options);
  }
  return Promise.resolve();
}
class BranchManager {
  /** @type {TemplateNode} */
  anchor;
  /** @type {Map<Batch, Key>} */
  #batches = /* @__PURE__ */ new Map();
  /**
   * Map of keys to effects that are currently rendered in the DOM.
   * These effects are visible and actively part of the document tree.
   * Example:
   * ```
   * {#if condition}
   * 	foo
   * {:else}
   * 	bar
   * {/if}
   * ```
   * Can result in the entries `true->Effect` and `false->Effect`
   * @type {Map<Key, Effect>}
   */
  #onscreen = /* @__PURE__ */ new Map();
  /**
   * Similar to #onscreen with respect to the keys, but contains branches that are not yet
   * in the DOM, because their insertion is deferred.
   * @type {Map<Key, Branch>}
   */
  #offscreen = /* @__PURE__ */ new Map();
  /**
   * Keys of effects that are currently outroing
   * @type {Set<Key>}
   */
  #outroing = /* @__PURE__ */ new Set();
  /**
   * Whether to pause (i.e. outro) on change, or destroy immediately.
   * This is necessary for `<svelte:element>`
   */
  #transition = true;
  /**
   * @param {TemplateNode} anchor
   * @param {boolean} transition
   */
  constructor(anchor, transition = true) {
    this.anchor = anchor;
    this.#transition = transition;
  }
  #commit = () => {
    var batch = (
      /** @type {Batch} */
      current_batch
    );
    if (!this.#batches.has(batch)) return;
    var key = (
      /** @type {Key} */
      this.#batches.get(batch)
    );
    var onscreen = this.#onscreen.get(key);
    if (onscreen) {
      resume_effect(onscreen);
      this.#outroing.delete(key);
    } else {
      var offscreen = this.#offscreen.get(key);
      if (offscreen) {
        this.#onscreen.set(key, offscreen.effect);
        this.#offscreen.delete(key);
        offscreen.fragment.lastChild.remove();
        this.anchor.before(offscreen.fragment);
        onscreen = offscreen.effect;
      }
    }
    for (const [b2, k2] of this.#batches) {
      this.#batches.delete(b2);
      if (b2 === batch) {
        break;
      }
      const offscreen2 = this.#offscreen.get(k2);
      if (offscreen2) {
        destroy_effect(offscreen2.effect);
        this.#offscreen.delete(k2);
      }
    }
    for (const [k2, effect2] of this.#onscreen) {
      if (k2 === key || this.#outroing.has(k2)) continue;
      const on_destroy = () => {
        const keys = Array.from(this.#batches.values());
        if (keys.includes(k2)) {
          var fragment = document.createDocumentFragment();
          move_effect(effect2, fragment);
          fragment.append(create_text());
          this.#offscreen.set(k2, { effect: effect2, fragment });
        } else {
          destroy_effect(effect2);
        }
        this.#outroing.delete(k2);
        this.#onscreen.delete(k2);
      };
      if (this.#transition || !onscreen) {
        this.#outroing.add(k2);
        pause_effect(effect2, on_destroy, false);
      } else {
        on_destroy();
      }
    }
  };
  /**
   * @param {Batch} batch
   */
  #discard = (batch) => {
    this.#batches.delete(batch);
    const keys = Array.from(this.#batches.values());
    for (const [k2, branch2] of this.#offscreen) {
      if (!keys.includes(k2)) {
        destroy_effect(branch2.effect);
        this.#offscreen.delete(k2);
      }
    }
  };
  /**
   *
   * @param {any} key
   * @param {null | ((target: TemplateNode) => void)} fn
   */
  ensure(key, fn) {
    var batch = (
      /** @type {Batch} */
      current_batch
    );
    var defer = should_defer_append();
    if (fn && !this.#onscreen.has(key) && !this.#offscreen.has(key)) {
      if (defer) {
        var fragment = document.createDocumentFragment();
        var target = create_text();
        fragment.append(target);
        this.#offscreen.set(key, {
          effect: branch(() => fn(target)),
          fragment
        });
      } else {
        this.#onscreen.set(
          key,
          branch(() => fn(this.anchor))
        );
      }
    }
    this.#batches.set(batch, key);
    if (defer) {
      for (const [k2, effect2] of this.#onscreen) {
        if (k2 === key) {
          batch.skipped_effects.delete(effect2);
        } else {
          batch.skipped_effects.add(effect2);
        }
      }
      for (const [k2, branch2] of this.#offscreen) {
        if (k2 === key) {
          batch.skipped_effects.delete(branch2.effect);
        } else {
          batch.skipped_effects.add(branch2.effect);
        }
      }
      batch.oncommit(this.#commit);
      batch.ondiscard(this.#discard);
    } else {
      this.#commit();
    }
  }
}
function onMount(fn) {
  if (component_context === null) {
    lifecycle_outside_component();
  }
  if (legacy_mode_flag && component_context.l !== null) {
    init_update_callbacks(component_context).m.push(fn);
  } else {
    user_effect(() => {
      const cleanup = untrack(fn);
      if (typeof cleanup === "function") return (
        /** @type {() => void} */
        cleanup
      );
    });
  }
}
function init_update_callbacks(context) {
  var l2 = (
    /** @type {ComponentContextLegacy} */
    context.l
  );
  return l2.u ??= { a: [], b: [], m: [] };
}
function if_block(node, fn, elseif = false) {
  var branches = new BranchManager(node);
  var flags2 = elseif ? EFFECT_TRANSPARENT : 0;
  function update_branch(condition, fn2) {
    branches.ensure(condition, fn2);
  }
  block(() => {
    var has_branch = false;
    fn((fn2, flag = true) => {
      has_branch = true;
      update_branch(flag, fn2);
    });
    if (!has_branch) {
      update_branch(false, null);
    }
  }, flags2);
}
function index(_2, i2) {
  return i2;
}
function pause_effects(state2, to_destroy, controlled_anchor) {
  var transitions = [];
  var length = to_destroy.length;
  var group;
  var remaining = to_destroy.length;
  for (var i2 = 0; i2 < length; i2++) {
    let effect2 = to_destroy[i2];
    pause_effect(
      effect2,
      () => {
        if (group) {
          group.pending.delete(effect2);
          group.done.add(effect2);
          if (group.pending.size === 0) {
            var groups = (
              /** @type {Set<EachOutroGroup>} */
              state2.outrogroups
            );
            destroy_effects(array_from(group.done));
            groups.delete(group);
            if (groups.size === 0) {
              state2.outrogroups = null;
            }
          }
        } else {
          remaining -= 1;
        }
      },
      false
    );
  }
  if (remaining === 0) {
    var fast_path = transitions.length === 0 && controlled_anchor !== null;
    if (fast_path) {
      var anchor = (
        /** @type {Element} */
        controlled_anchor
      );
      var parent_node = (
        /** @type {Element} */
        anchor.parentNode
      );
      clear_text_content(parent_node);
      parent_node.append(anchor);
      state2.items.clear();
    }
    destroy_effects(to_destroy, !fast_path);
  } else {
    group = {
      pending: new Set(to_destroy),
      done: /* @__PURE__ */ new Set()
    };
    (state2.outrogroups ??= /* @__PURE__ */ new Set()).add(group);
  }
}
function destroy_effects(to_destroy, remove_dom = true) {
  for (var i2 = 0; i2 < to_destroy.length; i2++) {
    destroy_effect(to_destroy[i2], remove_dom);
  }
}
var offscreen_anchor;
function each(node, flags2, get_collection, get_key, render_fn, fallback_fn = null) {
  var anchor = node;
  var items = /* @__PURE__ */ new Map();
  var is_controlled = (flags2 & EACH_IS_CONTROLLED) !== 0;
  if (is_controlled) {
    var parent_node = (
      /** @type {Element} */
      node
    );
    anchor = parent_node.appendChild(create_text());
  }
  var fallback = null;
  var each_array = /* @__PURE__ */ derived_safe_equal(() => {
    var collection = get_collection();
    return is_array(collection) ? collection : collection == null ? [] : array_from(collection);
  });
  var array;
  var first_run = true;
  function commit() {
    state2.fallback = fallback;
    reconcile(state2, array, anchor, flags2, get_key);
    if (fallback !== null) {
      if (array.length === 0) {
        if ((fallback.f & EFFECT_OFFSCREEN) === 0) {
          resume_effect(fallback);
        } else {
          fallback.f ^= EFFECT_OFFSCREEN;
          move(fallback, null, anchor);
        }
      } else {
        pause_effect(fallback, () => {
          fallback = null;
        });
      }
    }
  }
  var effect2 = block(() => {
    array = /** @type {V[]} */
    get$1(each_array);
    var length = array.length;
    var keys = /* @__PURE__ */ new Set();
    var batch = (
      /** @type {Batch} */
      current_batch
    );
    var defer = should_defer_append();
    for (var index2 = 0; index2 < length; index2 += 1) {
      var value = array[index2];
      var key = get_key(value, index2);
      var item = first_run ? null : items.get(key);
      if (item) {
        if (item.v) internal_set(item.v, value);
        if (item.i) internal_set(item.i, index2);
        if (defer) {
          batch.skipped_effects.delete(item.e);
        }
      } else {
        item = create_item(
          items,
          first_run ? anchor : offscreen_anchor ??= create_text(),
          value,
          key,
          index2,
          render_fn,
          flags2,
          get_collection
        );
        if (!first_run) {
          item.e.f |= EFFECT_OFFSCREEN;
        }
        items.set(key, item);
      }
      keys.add(key);
    }
    if (length === 0 && fallback_fn && !fallback) {
      if (first_run) {
        fallback = branch(() => fallback_fn(anchor));
      } else {
        fallback = branch(() => fallback_fn(offscreen_anchor ??= create_text()));
        fallback.f |= EFFECT_OFFSCREEN;
      }
    }
    if (!first_run) {
      if (defer) {
        for (const [key2, item2] of items) {
          if (!keys.has(key2)) {
            batch.skipped_effects.add(item2.e);
          }
        }
        batch.oncommit(commit);
        batch.ondiscard(() => {
        });
      } else {
        commit();
      }
    }
    get$1(each_array);
  });
  var state2 = { effect: effect2, items, outrogroups: null, fallback };
  first_run = false;
}
function skip_to_branch(effect2) {
  while (effect2 !== null && (effect2.f & BRANCH_EFFECT) === 0) {
    effect2 = effect2.next;
  }
  return effect2;
}
function reconcile(state2, array, anchor, flags2, get_key) {
  var is_animated = (flags2 & EACH_IS_ANIMATED) !== 0;
  var length = array.length;
  var items = state2.items;
  var current = skip_to_branch(state2.effect.first);
  var seen;
  var prev = null;
  var to_animate;
  var matched = [];
  var stashed = [];
  var value;
  var key;
  var effect2;
  var i2;
  if (is_animated) {
    for (i2 = 0; i2 < length; i2 += 1) {
      value = array[i2];
      key = get_key(value, i2);
      effect2 = /** @type {EachItem} */
      items.get(key).e;
      if ((effect2.f & EFFECT_OFFSCREEN) === 0) {
        effect2.nodes?.a?.measure();
        (to_animate ??= /* @__PURE__ */ new Set()).add(effect2);
      }
    }
  }
  for (i2 = 0; i2 < length; i2 += 1) {
    value = array[i2];
    key = get_key(value, i2);
    effect2 = /** @type {EachItem} */
    items.get(key).e;
    if (state2.outrogroups !== null) {
      for (const group of state2.outrogroups) {
        group.pending.delete(effect2);
        group.done.delete(effect2);
      }
    }
    if ((effect2.f & EFFECT_OFFSCREEN) !== 0) {
      effect2.f ^= EFFECT_OFFSCREEN;
      if (effect2 === current) {
        move(effect2, null, anchor);
      } else {
        var next = prev ? prev.next : current;
        if (effect2 === state2.effect.last) {
          state2.effect.last = effect2.prev;
        }
        if (effect2.prev) effect2.prev.next = effect2.next;
        if (effect2.next) effect2.next.prev = effect2.prev;
        link(state2, prev, effect2);
        link(state2, effect2, next);
        move(effect2, next, anchor);
        prev = effect2;
        matched = [];
        stashed = [];
        current = skip_to_branch(prev.next);
        continue;
      }
    }
    if ((effect2.f & INERT) !== 0) {
      resume_effect(effect2);
      if (is_animated) {
        effect2.nodes?.a?.unfix();
        (to_animate ??= /* @__PURE__ */ new Set()).delete(effect2);
      }
    }
    if (effect2 !== current) {
      if (seen !== void 0 && seen.has(effect2)) {
        if (matched.length < stashed.length) {
          var start = stashed[0];
          var j2;
          prev = start.prev;
          var a2 = matched[0];
          var b2 = matched[matched.length - 1];
          for (j2 = 0; j2 < matched.length; j2 += 1) {
            move(matched[j2], start, anchor);
          }
          for (j2 = 0; j2 < stashed.length; j2 += 1) {
            seen.delete(stashed[j2]);
          }
          link(state2, a2.prev, b2.next);
          link(state2, prev, a2);
          link(state2, b2, start);
          current = start;
          prev = b2;
          i2 -= 1;
          matched = [];
          stashed = [];
        } else {
          seen.delete(effect2);
          move(effect2, current, anchor);
          link(state2, effect2.prev, effect2.next);
          link(state2, effect2, prev === null ? state2.effect.first : prev.next);
          link(state2, prev, effect2);
          prev = effect2;
        }
        continue;
      }
      matched = [];
      stashed = [];
      while (current !== null && current !== effect2) {
        (seen ??= /* @__PURE__ */ new Set()).add(current);
        stashed.push(current);
        current = skip_to_branch(current.next);
      }
      if (current === null) {
        continue;
      }
    }
    if ((effect2.f & EFFECT_OFFSCREEN) === 0) {
      matched.push(effect2);
    }
    prev = effect2;
    current = skip_to_branch(effect2.next);
  }
  if (state2.outrogroups !== null) {
    for (const group of state2.outrogroups) {
      if (group.pending.size === 0) {
        destroy_effects(array_from(group.done));
        state2.outrogroups?.delete(group);
      }
    }
    if (state2.outrogroups.size === 0) {
      state2.outrogroups = null;
    }
  }
  if (current !== null || seen !== void 0) {
    var to_destroy = [];
    if (seen !== void 0) {
      for (effect2 of seen) {
        if ((effect2.f & INERT) === 0) {
          to_destroy.push(effect2);
        }
      }
    }
    while (current !== null) {
      if ((current.f & INERT) === 0 && current !== state2.fallback) {
        to_destroy.push(current);
      }
      current = skip_to_branch(current.next);
    }
    var destroy_length = to_destroy.length;
    if (destroy_length > 0) {
      var controlled_anchor = (flags2 & EACH_IS_CONTROLLED) !== 0 && length === 0 ? anchor : null;
      if (is_animated) {
        for (i2 = 0; i2 < destroy_length; i2 += 1) {
          to_destroy[i2].nodes?.a?.measure();
        }
        for (i2 = 0; i2 < destroy_length; i2 += 1) {
          to_destroy[i2].nodes?.a?.fix();
        }
      }
      pause_effects(state2, to_destroy, controlled_anchor);
    }
  }
  if (is_animated) {
    queue_micro_task(() => {
      if (to_animate === void 0) return;
      for (effect2 of to_animate) {
        effect2.nodes?.a?.apply();
      }
    });
  }
}
function create_item(items, anchor, value, key, index2, render_fn, flags2, get_collection) {
  var v2 = (flags2 & EACH_ITEM_REACTIVE) !== 0 ? (flags2 & EACH_ITEM_IMMUTABLE) === 0 ? /* @__PURE__ */ mutable_source(value, false, false) : source(value) : null;
  var i2 = (flags2 & EACH_INDEX_REACTIVE) !== 0 ? source(index2) : null;
  return {
    v: v2,
    i: i2,
    e: branch(() => {
      render_fn(anchor, v2 ?? value, i2 ?? index2, get_collection);
      return () => {
        items.delete(key);
      };
    })
  };
}
function move(effect2, next, anchor) {
  if (!effect2.nodes) return;
  var node = effect2.nodes.start;
  var end = effect2.nodes.end;
  var dest = next && (next.f & EFFECT_OFFSCREEN) === 0 ? (
    /** @type {EffectNodes} */
    next.nodes.start
  ) : anchor;
  while (node !== null) {
    var next_node = (
      /** @type {TemplateNode} */
      /* @__PURE__ */ get_next_sibling(node)
    );
    dest.before(node);
    if (node === end) {
      return;
    }
    node = next_node;
  }
}
function link(state2, prev, next) {
  if (prev === null) {
    state2.effect.first = next;
  } else {
    prev.next = next;
  }
  if (next === null) {
    state2.effect.last = prev;
  } else {
    next.prev = prev;
  }
}
function html$2(node, get_value, svg2 = false, mathml = false, skip_warning = false) {
  var anchor = node;
  var value = "";
  template_effect(() => {
    var effect2 = (
      /** @type {Effect} */
      active_effect
    );
    if (value === (value = get_value() ?? "")) {
      return;
    }
    if (effect2.nodes !== null) {
      remove_effect_dom(
        effect2.nodes.start,
        /** @type {TemplateNode} */
        effect2.nodes.end
      );
      effect2.nodes = null;
    }
    if (value === "") return;
    var html2 = value + "";
    if (svg2) html2 = `<svg>${html2}</svg>`;
    else if (mathml) html2 = `<math>${html2}</math>`;
    var node2 = create_fragment_from_html(html2);
    if (svg2 || mathml) {
      node2 = /** @type {Element} */
      /* @__PURE__ */ get_first_child(node2);
    }
    assign_nodes(
      /** @type {TemplateNode} */
      /* @__PURE__ */ get_first_child(node2),
      /** @type {TemplateNode} */
      node2.lastChild
    );
    if (svg2 || mathml) {
      while (/* @__PURE__ */ get_first_child(node2)) {
        anchor.before(
          /** @type {TemplateNode} */
          /* @__PURE__ */ get_first_child(node2)
        );
      }
    } else {
      anchor.before(node2);
    }
  });
}
function r$1(e2) {
  var t2, f2, n2 = "";
  if ("string" == typeof e2 || "number" == typeof e2) n2 += e2;
  else if ("object" == typeof e2) if (Array.isArray(e2)) {
    var o2 = e2.length;
    for (t2 = 0; t2 < o2; t2++) e2[t2] && (f2 = r$1(e2[t2])) && (n2 && (n2 += " "), n2 += f2);
  } else for (f2 in e2) e2[f2] && (n2 && (n2 += " "), n2 += f2);
  return n2;
}
function clsx$1() {
  for (var e2, t2, f2 = 0, n2 = "", o2 = arguments.length; f2 < o2; f2++) (e2 = arguments[f2]) && (t2 = r$1(e2)) && (n2 && (n2 += " "), n2 += t2);
  return n2;
}
function clsx(value) {
  if (typeof value === "object") {
    return clsx$1(value);
  } else {
    return value ?? "";
  }
}
const whitespace = [..." 	\n\r\f \v\uFEFF"];
function to_class(value, hash, directives) {
  var classname = value == null ? "" : "" + value;
  if (hash) {
    classname = classname ? classname + " " + hash : hash;
  }
  if (directives) {
    for (var key in directives) {
      if (directives[key]) {
        classname = classname ? classname + " " + key : key;
      } else if (classname.length) {
        var len = key.length;
        var a2 = 0;
        while ((a2 = classname.indexOf(key, a2)) >= 0) {
          var b2 = a2 + len;
          if ((a2 === 0 || whitespace.includes(classname[a2 - 1])) && (b2 === classname.length || whitespace.includes(classname[b2]))) {
            classname = (a2 === 0 ? "" : classname.substring(0, a2)) + classname.substring(b2 + 1);
          } else {
            a2 = b2;
          }
        }
      }
    }
  }
  return classname === "" ? null : classname;
}
function to_style(value, styles) {
  return value == null ? null : String(value);
}
function set_class(dom, is_html, value, hash, prev_classes, next_classes) {
  var prev = dom.__className;
  if (prev !== value || prev === void 0) {
    var next_class_name = to_class(value, hash, next_classes);
    {
      if (next_class_name == null) {
        dom.removeAttribute("class");
      } else if (is_html) {
        dom.className = next_class_name;
      } else {
        dom.setAttribute("class", next_class_name);
      }
    }
    dom.__className = value;
  } else if (next_classes && prev_classes !== next_classes) {
    for (var key in next_classes) {
      var is_present = !!next_classes[key];
      if (prev_classes == null || is_present !== !!prev_classes[key]) {
        dom.classList.toggle(key, is_present);
      }
    }
  }
  return next_classes;
}
function set_style(dom, value, prev_styles, next_styles) {
  var prev = dom.__style;
  if (prev !== value) {
    var next_style_attr = to_style(value);
    {
      if (next_style_attr == null) {
        dom.removeAttribute("style");
      } else {
        dom.style.cssText = next_style_attr;
      }
    }
    dom.__style = value;
  }
  return next_styles;
}
function select_option(select, value, mounting = false) {
  if (select.multiple) {
    if (value == void 0) {
      return;
    }
    if (!is_array(value)) {
      return select_multiple_invalid_value();
    }
    for (var option of select.options) {
      option.selected = value.includes(get_option_value(option));
    }
    return;
  }
  for (option of select.options) {
    var option_value = get_option_value(option);
    if (is(option_value, value)) {
      option.selected = true;
      return;
    }
  }
  if (!mounting || value !== void 0) {
    select.selectedIndex = -1;
  }
}
function init_select(select) {
  var observer = new MutationObserver(() => {
    select_option(select, select.__value);
  });
  observer.observe(select, {
    // Listen to option element changes
    childList: true,
    subtree: true,
    // because of <optgroup>
    // Listen to option element value attribute changes
    // (doesn't get notified of select value changes,
    // because that property is not reflected as an attribute)
    attributes: true,
    attributeFilter: ["value"]
  });
  teardown(() => {
    observer.disconnect();
  });
}
function bind_select_value(select, get2, set2 = get2) {
  var batches2 = /* @__PURE__ */ new WeakSet();
  var mounting = true;
  listen_to_event_and_reset_event(select, "change", (is_reset) => {
    var query = is_reset ? "[selected]" : ":checked";
    var value;
    if (select.multiple) {
      value = [].map.call(select.querySelectorAll(query), get_option_value);
    } else {
      var selected_option = select.querySelector(query) ?? // will fall back to first non-disabled option if no option is selected
      select.querySelector("option:not([disabled])");
      value = selected_option && get_option_value(selected_option);
    }
    set2(value);
    if (current_batch !== null) {
      batches2.add(current_batch);
    }
  });
  effect(() => {
    var value = get2();
    if (select === document.activeElement) {
      var batch = (
        /** @type {Batch} */
        previous_batch ?? current_batch
      );
      if (batches2.has(batch)) {
        return;
      }
    }
    select_option(select, value, mounting);
    if (mounting && value === void 0) {
      var selected_option = select.querySelector(":checked");
      if (selected_option !== null) {
        value = get_option_value(selected_option);
        set2(value);
      }
    }
    select.__value = value;
    mounting = false;
  });
  init_select(select);
}
function get_option_value(option) {
  if ("__value" in option) {
    return option.__value;
  } else {
    return option.value;
  }
}
const IS_CUSTOM_ELEMENT = /* @__PURE__ */ Symbol("is custom element");
const IS_HTML = /* @__PURE__ */ Symbol("is html");
function set_value(element, value) {
  var attributes = get_attributes(element);
  if (attributes.value === (attributes.value = // treat null and undefined the same for the initial value
  value ?? void 0) || // @ts-expect-error
  // `progress` elements always need their value set when it's `0`
  element.value === value && (value !== 0 || element.nodeName !== "PROGRESS")) {
    return;
  }
  element.value = value ?? "";
}
function set_checked(element, checked) {
  var attributes = get_attributes(element);
  if (attributes.checked === (attributes.checked = // treat null and undefined the same for the initial value
  checked ?? void 0)) {
    return;
  }
  element.checked = checked;
}
function set_attribute(element, attribute, value, skip_warning) {
  var attributes = get_attributes(element);
  if (attributes[attribute] === (attributes[attribute] = value)) return;
  if (attribute === "loading") {
    element[LOADING_ATTR_SYMBOL] = value;
  }
  if (value == null) {
    element.removeAttribute(attribute);
  } else if (typeof value !== "string" && get_setters(element).includes(attribute)) {
    element[attribute] = value;
  } else {
    element.setAttribute(attribute, value);
  }
}
function get_attributes(element) {
  return (
    /** @type {Record<string | symbol, unknown>} **/
    // @ts-expect-error
    element.__attributes ??= {
      [IS_CUSTOM_ELEMENT]: element.nodeName.includes("-"),
      [IS_HTML]: element.namespaceURI === NAMESPACE_HTML
    }
  );
}
var setters_cache = /* @__PURE__ */ new Map();
function get_setters(element) {
  var cache_key = element.getAttribute("is") || element.nodeName;
  var setters = setters_cache.get(cache_key);
  if (setters) return setters;
  setters_cache.set(cache_key, setters = []);
  var descriptors;
  var proto = element;
  var element_proto = Element.prototype;
  while (element_proto !== proto) {
    descriptors = get_descriptors(proto);
    for (var key in descriptors) {
      if (descriptors[key].set) {
        setters.push(key);
      }
    }
    proto = get_prototype_of(proto);
  }
  return setters;
}
function bind_value(input, get2, set2 = get2) {
  var batches2 = /* @__PURE__ */ new WeakSet();
  listen_to_event_and_reset_event(input, "input", async (is_reset) => {
    var value = is_reset ? input.defaultValue : input.value;
    value = is_numberlike_input(input) ? to_number(value) : value;
    set2(value);
    if (current_batch !== null) {
      batches2.add(current_batch);
    }
    await tick();
    if (value !== (value = get2())) {
      var start = input.selectionStart;
      var end = input.selectionEnd;
      var length = input.value.length;
      input.value = value ?? "";
      if (end !== null) {
        var new_length = input.value.length;
        if (start === end && end === length && new_length > length) {
          input.selectionStart = new_length;
          input.selectionEnd = new_length;
        } else {
          input.selectionStart = start;
          input.selectionEnd = Math.min(end, new_length);
        }
      }
    }
  });
  if (
    // If we are hydrating and the value has since changed,
    // then use the updated value from the input instead.
    // If defaultValue is set, then value == defaultValue
    // TODO Svelte 6: remove input.value check and set to empty string?
    untrack(get2) == null && input.value
  ) {
    set2(is_numberlike_input(input) ? to_number(input.value) : input.value);
    if (current_batch !== null) {
      batches2.add(current_batch);
    }
  }
  render_effect(() => {
    var value = get2();
    if (input === document.activeElement) {
      var batch = (
        /** @type {Batch} */
        previous_batch ?? current_batch
      );
      if (batches2.has(batch)) {
        return;
      }
    }
    if (is_numberlike_input(input) && value === to_number(input.value)) {
      return;
    }
    if (input.type === "date" && !value && !input.value) {
      return;
    }
    if (value !== input.value) {
      input.value = value ?? "";
    }
  });
}
function bind_checked(input, get2, set2 = get2) {
  listen_to_event_and_reset_event(input, "change", (is_reset) => {
    var value = is_reset ? input.defaultChecked : input.checked;
    set2(value);
  });
  if (
    // If we are hydrating and the value has since changed,
    // then use the update value from the input instead.
    // If defaultChecked is set, then checked == defaultChecked
    untrack(get2) == null
  ) {
    set2(input.checked);
  }
  render_effect(() => {
    var value = get2();
    input.checked = Boolean(value);
  });
}
function is_numberlike_input(input) {
  var type = input.type;
  return type === "number" || type === "range";
}
function to_number(value) {
  return value === "" ? null : +value;
}
function is_bound_this(bound_value, element_or_component) {
  return bound_value === element_or_component || bound_value?.[STATE_SYMBOL] === element_or_component;
}
function bind_this(element_or_component = {}, update, get_value, get_parts) {
  effect(() => {
    var old_parts;
    var parts;
    render_effect(() => {
      old_parts = parts;
      parts = [];
      untrack(() => {
        if (element_or_component !== get_value(...parts)) {
          update(element_or_component, ...parts);
          if (old_parts && is_bound_this(get_value(...old_parts), element_or_component)) {
            update(null, ...old_parts);
          }
        }
      });
    });
    return () => {
      queue_micro_task(() => {
        if (parts && is_bound_this(get_value(...parts), element_or_component)) {
          update(null, ...parts);
        }
      });
    };
  });
  return element_or_component;
}
function init(immutable = false) {
  const context = (
    /** @type {ComponentContextLegacy} */
    component_context
  );
  const callbacks = context.l.u;
  if (!callbacks) return;
  let props = () => deep_read_state(context.s);
  if (immutable) {
    let version = 0;
    let prev = (
      /** @type {Record<string, any>} */
      {}
    );
    const d2 = /* @__PURE__ */ derived$1(() => {
      let changed = false;
      const props2 = context.s;
      for (const key in props2) {
        if (props2[key] !== prev[key]) {
          prev[key] = props2[key];
          changed = true;
        }
      }
      if (changed) version++;
      return version;
    });
    props = () => get$1(d2);
  }
  if (callbacks.b.length) {
    user_pre_effect(() => {
      observe_all(context, props);
      run_all(callbacks.b);
    });
  }
  user_effect(() => {
    const fns = untrack(() => callbacks.m.map(run));
    return () => {
      for (const fn of fns) {
        if (typeof fn === "function") {
          fn();
        }
      }
    };
  });
  if (callbacks.a.length) {
    user_effect(() => {
      observe_all(context, props);
      run_all(callbacks.a);
    });
  }
}
function observe_all(context, props) {
  if (context.l.s) {
    for (const signal of context.l.s) get$1(signal);
  }
  props();
}
function subscribe_to_store(store, run2, invalidate) {
  if (store == null) {
    run2(void 0);
    if (invalidate) invalidate(void 0);
    return noop;
  }
  const unsub = untrack(
    () => store.subscribe(
      run2,
      // @ts-expect-error
      invalidate
    )
  );
  return unsub.unsubscribe ? () => unsub.unsubscribe() : unsub;
}
const subscriber_queue = [];
function readable(value, start) {
  return {
    subscribe: writable(value, start).subscribe
  };
}
function writable(value, start = noop) {
  let stop = null;
  const subscribers = /* @__PURE__ */ new Set();
  function set2(new_value) {
    if (safe_not_equal(value, new_value)) {
      value = new_value;
      if (stop) {
        const run_queue = !subscriber_queue.length;
        for (const subscriber of subscribers) {
          subscriber[1]();
          subscriber_queue.push(subscriber, value);
        }
        if (run_queue) {
          for (let i2 = 0; i2 < subscriber_queue.length; i2 += 2) {
            subscriber_queue[i2][0](subscriber_queue[i2 + 1]);
          }
          subscriber_queue.length = 0;
        }
      }
    }
  }
  function update(fn) {
    set2(fn(
      /** @type {T} */
      value
    ));
  }
  function subscribe(run2, invalidate = noop) {
    const subscriber = [run2, invalidate];
    subscribers.add(subscriber);
    if (subscribers.size === 1) {
      stop = start(set2, update) || noop;
    }
    run2(
      /** @type {T} */
      value
    );
    return () => {
      subscribers.delete(subscriber);
      if (subscribers.size === 0 && stop) {
        stop();
        stop = null;
      }
    };
  }
  return { set: set2, update, subscribe };
}
function derived(stores, fn, initial_value) {
  const single = !Array.isArray(stores);
  const stores_array = single ? [stores] : stores;
  if (!stores_array.every(Boolean)) {
    throw new Error("derived() expects stores as input, got a falsy value");
  }
  const auto = fn.length < 2;
  return readable(initial_value, (set2, update) => {
    let started = false;
    const values = [];
    let pending = 0;
    let cleanup = noop;
    const sync = () => {
      if (pending) {
        return;
      }
      cleanup();
      const result = fn(single ? values[0] : values, set2, update);
      if (auto) {
        set2(result);
      } else {
        cleanup = typeof result === "function" ? result : noop;
      }
    };
    const unsubscribers = stores_array.map(
      (store, i2) => subscribe_to_store(
        store,
        (value) => {
          values[i2] = value;
          pending &= ~(1 << i2);
          if (started) {
            sync();
          }
        },
        () => {
          pending |= 1 << i2;
        }
      )
    );
    started = true;
    sync();
    return function stop() {
      run_all(unsubscribers);
      cleanup();
      started = false;
    };
  });
}
function get(store) {
  let value;
  subscribe_to_store(store, (_2) => value = _2)();
  return value;
}
let IS_UNMOUNTED = /* @__PURE__ */ Symbol();
function store_get(store, store_name, stores) {
  const entry = stores[store_name] ??= {
    store: null,
    source: /* @__PURE__ */ mutable_source(void 0),
    unsubscribe: noop
  };
  if (entry.store !== store && !(IS_UNMOUNTED in stores)) {
    entry.unsubscribe();
    entry.store = store ?? null;
    if (store == null) {
      entry.source.v = void 0;
      entry.unsubscribe = noop;
    } else {
      var is_synchronous_callback = true;
      entry.unsubscribe = subscribe_to_store(store, (v2) => {
        if (is_synchronous_callback) {
          entry.source.v = v2;
        } else {
          set(entry.source, v2);
        }
      });
      is_synchronous_callback = false;
    }
  }
  if (store && IS_UNMOUNTED in stores) {
    return get(store);
  }
  return get$1(entry.source);
}
function setup_stores() {
  const stores = {};
  function cleanup() {
    teardown(() => {
      for (var store_name in stores) {
        const ref = stores[store_name];
        ref.unsubscribe();
      }
      define_property(stores, IS_UNMOUNTED, {
        enumerable: false,
        value: true
      });
    });
  }
  return [stores, cleanup];
}
function prop(props, key, flags2, fallback) {
  var fallback_value = (
    /** @type {V} */
    fallback
  );
  var fallback_dirty = true;
  var get_fallback = () => {
    if (fallback_dirty) {
      fallback_dirty = false;
      fallback_value = /** @type {V} */
      fallback;
    }
    return fallback_value;
  };
  var initial_value;
  {
    initial_value = /** @type {V} */
    props[key];
  }
  if (initial_value === void 0 && fallback !== void 0) {
    initial_value = get_fallback();
  }
  var getter;
  {
    getter = () => {
      var value = (
        /** @type {V} */
        props[key]
      );
      if (value === void 0) return get_fallback();
      fallback_dirty = true;
      return value;
    };
  }
  {
    return getter;
  }
}
const initialState$3 = {
  hass: null,
  messages: [],
  isLoading: false,
  error: null,
  debugInfo: null,
  showThinking: false,
  thinkingExpanded: false,
  agentName: "Homeclaw",
  agentEmoji: ""
};
const appState = writable(initialState$3);
const hasMessages = derived(appState, ($state) => $state.messages.length > 0);
derived(appState, ($state) => $state.error !== null);
let _hostElement = null;
function setHostElement(el) {
  _hostElement = el;
}
const initialState$2 = {
  sidebarOpen: typeof window !== "undefined" ? window.innerWidth > 768 : false,
  showProviderDropdown: false,
  settingsOpen: false,
  theme: "system"
};
const uiState = writable(initialState$2);
function isValidTheme(theme) {
  return theme === "light" || theme === "dark" || theme === "system";
}
function toggleSidebar() {
  uiState.update((state2) => ({ ...state2, sidebarOpen: !state2.sidebarOpen }));
}
function closeSidebar() {
  uiState.update((state2) => ({ ...state2, sidebarOpen: false }));
}
function openSidebar() {
  uiState.update((state2) => ({ ...state2, sidebarOpen: true }));
}
function closeDropdowns() {
  uiState.update((state2) => ({ ...state2, showProviderDropdown: false }));
}
function openSettings() {
  uiState.update((state2) => ({ ...state2, settingsOpen: true }));
}
function closeSettings() {
  uiState.update((state2) => ({ ...state2, settingsOpen: false }));
}
function toggleSettings() {
  uiState.update((state2) => ({ ...state2, settingsOpen: !state2.settingsOpen }));
}
function setTheme(theme) {
  uiState.update((s2) => ({ ...s2, theme }));
  applyThemeToHost(theme);
  try {
    localStorage.setItem("homeclaw-theme", theme);
  } catch {
  }
  void persistThemePreference(theme);
}
function cycleTheme() {
  const current = get(uiState).theme;
  const next = current === "system" ? "light" : current === "light" ? "dark" : "system";
  setTheme(next);
}
function applyThemeToHost(theme) {
  const host = _hostElement || document.querySelector("homeclaw-panel");
  if (!host) {
    console.warn("[Theme] Could not find homeclaw-panel host element");
    return;
  }
  if (theme === "system") {
    host.removeAttribute("data-theme");
  } else {
    host.setAttribute("data-theme", theme);
  }
  host.classList.add("theme-transitioning");
  setTimeout(() => host.classList.remove("theme-transitioning"), 350);
}
async function persistThemePreference(theme) {
  const hass = get(appState).hass;
  if (!hass) return;
  try {
    await hass.callWS({
      type: "homeclaw/preferences/set",
      theme
    });
  } catch (error) {
    console.warn("[Theme] Could not persist theme preference:", error);
  }
}
async function syncThemeFromPreferences(hass) {
  const ha = hass ?? get(appState).hass;
  if (!ha) return;
  try {
    const result = await ha.callWS({ type: "homeclaw/preferences/get" });
    const theme = result?.preferences?.theme;
    if (!isValidTheme(theme)) return;
    uiState.update((s2) => ({ ...s2, theme }));
    applyThemeToHost(theme);
    try {
      localStorage.setItem("homeclaw-theme", theme);
    } catch {
    }
  } catch (error) {
    console.warn("[Theme] Could not load theme preference:", error);
  }
}
function initTheme() {
  try {
    const saved = localStorage.getItem("homeclaw-theme");
    if (isValidTheme(saved)) {
      uiState.update((s2) => ({ ...s2, theme: saved }));
      setTimeout(() => applyThemeToHost(saved), 0);
    }
  } catch {
  }
}
initTheme();
const ui = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  closeDropdowns,
  closeSettings,
  closeSidebar,
  cycleTheme,
  openSettings,
  openSidebar,
  setHostElement,
  setTheme,
  syncThemeFromPreferences,
  toggleSettings,
  toggleSidebar,
  uiState
}, Symbol.toStringTag, { value: "Module" }));
const initialState$1 = {
  availableProviders: [],
  selectedProvider: null,
  availableModels: [],
  selectedModel: null,
  providersLoaded: false,
  defaultProvider: null,
  defaultModel: null
};
const providerState = writable(initialState$1);
const hasProviders = derived(providerState, ($state) => $state.availableProviders.length > 0);
const hasModels = derived(providerState, ($state) => $state.availableModels.length > 0);
derived(
  providerState,
  ($state) => $state.availableProviders.find((p2) => p2.value === $state.selectedProvider) || null
);
derived(
  providerState,
  ($state) => $state.selectedProvider === $state.defaultProvider && $state.selectedModel === $state.defaultModel && $state.defaultProvider !== null
);
const PROVIDERS = {
  openai: "OpenAI",
  llama: "Llama",
  gemini: "Google Gemini",
  gemini_oauth: "Gemini (OAuth)",
  openrouter: "OpenRouter",
  anthropic: "Anthropic",
  anthropic_oauth: "Claude Pro/Max",
  groq: "Groq",
  alter: "Alter",
  zai: "z.ai",
  local: "Local Model"
};
let _providersConfig = null;
async function fetchProvidersConfig(hass) {
  if (_providersConfig) return _providersConfig;
  try {
    const result = await hass.callWS({
      type: "homeclaw/providers/config"
    });
    _providersConfig = result.providers || {};
    return _providersConfig;
  } catch (e2) {
    console.warn("[Provider] Could not fetch providers config, using fallback:", e2);
    return {};
  }
}
function getProviderLabel(provider, config) {
  return config[provider]?.display_name || PROVIDERS[provider] || provider;
}
function isValidProvider(provider, config) {
  return !!(config[provider] || PROVIDERS[provider]);
}
async function fetchPreferences(hass) {
  try {
    const result = await hass.callWS({ type: "homeclaw/preferences/get" });
    return result.preferences || {};
  } catch (e2) {
    console.warn("[Provider] Could not fetch user preferences:", e2);
    return {};
  }
}
async function savePreferences(hass, prefs) {
  const result = await hass.callWS({
    type: "homeclaw/preferences/set",
    ...prefs
  });
  const updated = result.preferences || {};
  providerState.update((s2) => ({
    ...s2,
    defaultProvider: updated.default_provider ?? null,
    defaultModel: updated.default_model ?? null
  }));
  return updated;
}
function invalidateProvidersCache() {
  _providersConfig = null;
  providerState.update((s2) => ({ ...s2, providersLoaded: false }));
}
async function loadProviders(hass) {
  console.log("[Provider] Loading providers...");
  const state2 = get(providerState);
  if (state2.providersLoaded) {
    console.log("[Provider] Already loaded, skipping");
    return;
  }
  try {
    const [config, prefs] = await Promise.all([
      fetchProvidersConfig(hass),
      fetchPreferences(hass)
    ]);
    console.log("[Provider] User preferences:", prefs);
    providerState.update((s2) => ({
      ...s2,
      defaultProvider: prefs.default_provider ?? null,
      defaultModel: prefs.default_model ?? null
    }));
    const allEntries = await hass.callWS({ type: "config_entries/get" });
    console.log("[Provider] All config entries:", allEntries.length);
    const homeclawEntries = allEntries.filter((entry) => entry.domain === "homeclaw");
    console.log("[Provider] Homeclaw entries:", homeclawEntries.length, homeclawEntries);
    if (homeclawEntries.length > 0) {
      const providers = homeclawEntries.map((entry) => {
        const provider = resolveProviderFromEntry(entry, config);
        console.log("[Provider] Resolved entry:", entry.title, "->", provider);
        if (!provider) return null;
        return {
          value: provider,
          label: getProviderLabel(provider, config)
        };
      }).filter(Boolean);
      console.log("[Provider] Final providers list:", providers);
      providerState.update((s2) => ({ ...s2, availableProviders: providers }));
      const currentState = get(providerState);
      const preferredProvider = prefs.default_provider;
      const hasPreferred = preferredProvider && providers.find((p2) => p2.value === preferredProvider);
      if ((!currentState.selectedProvider || !providers.find((p2) => p2.value === currentState.selectedProvider)) && providers.length > 0) {
        const autoSelect = hasPreferred ? preferredProvider : providers[0].value;
        providerState.update((s2) => ({ ...s2, selectedProvider: autoSelect }));
      }
      const updatedState = get(providerState);
      if (updatedState.selectedProvider) {
        await fetchModels(hass, updatedState.selectedProvider, prefs.default_model ?? null);
      }
      providerState.update((s2) => ({ ...s2, providersLoaded: true }));
    } else {
      providerState.update((s2) => ({ ...s2, availableProviders: [] }));
    }
  } catch (error) {
    console.error("Error fetching config entries:", error);
    appState.update((s2) => ({
      ...s2,
      error: "Failed to load AI provider configurations."
    }));
    providerState.update((s2) => ({ ...s2, availableProviders: [] }));
  }
}
async function fetchModels(hass, provider, preferredModel = null) {
  console.log("[Provider] Fetching models for provider:", provider);
  try {
    const result = await hass.callWS({
      type: "homeclaw/models/list",
      provider
    });
    const models = [...result.models || []];
    console.log("[Provider] Models received:", models);
    providerState.update((s2) => ({ ...s2, availableModels: models }));
    const hasPreferred = preferredModel && models.find((m2) => m2.id === preferredModel);
    let selectedModel;
    if (hasPreferred) {
      selectedModel = preferredModel;
      console.log("[Provider] Using preferred model:", preferredModel);
    } else {
      const defaultModel = models.find((m2) => m2.default);
      selectedModel = defaultModel ? defaultModel.id : models[0]?.id || null;
    }
    providerState.update((s2) => ({ ...s2, selectedModel }));
  } catch (e2) {
    console.warn("Could not fetch available models:", e2);
    providerState.update((s2) => ({
      ...s2,
      availableModels: [],
      selectedModel: null
    }));
  }
}
function resolveProviderFromEntry(entry, config = {}) {
  if (!entry) return null;
  const providerFromData = entry.data?.ai_provider || entry.options?.ai_provider;
  if (providerFromData && isValidProvider(providerFromData, config)) {
    return providerFromData;
  }
  const uniqueId = entry.unique_id || entry.uniqueId;
  if (uniqueId && uniqueId.startsWith("homeclaw_")) {
    const fromUniqueId = uniqueId.replace("homeclaw_", "");
    if (isValidProvider(fromUniqueId, config)) {
      return fromUniqueId;
    }
  }
  const titleMap = {
    "homeclaw (openrouter)": "openrouter",
    "homeclaw (google gemini)": "gemini",
    "homeclaw (openai)": "openai",
    "homeclaw (llama)": "llama",
    "homeclaw (anthropic (claude))": "anthropic",
    "homeclaw (alter)": "alter",
    "homeclaw (z.ai)": "zai",
    "homeclaw (local model)": "local",
    "homeclaw (groq)": "groq"
  };
  if (entry.title) {
    const lowerTitle = entry.title.toLowerCase();
    if (titleMap[lowerTitle]) {
      return titleMap[lowerTitle];
    }
    const allProviderKeys = /* @__PURE__ */ new Set([
      ...Object.keys(PROVIDERS),
      ...Object.keys(config)
    ]);
    const match = entry.title.match(/\(([^)]+)\)/);
    if (match && match[1]) {
      const normalized = match[1].toLowerCase().replace(/[^a-z0-9]/g, "");
      const providerKey = [...allProviderKeys].find(
        (key) => key.replace(/[^a-z0-9]/g, "") === normalized
      );
      if (providerKey) {
        return providerKey;
      }
    }
  }
  return null;
}
const initialState = {
  sessions: [],
  activeSessionId: null,
  sessionsLoading: true
};
const sessionState = writable(initialState);
const hasSessions = derived(sessionState, ($state) => $state.sessions.length > 0);
const activeSession = derived(
  sessionState,
  ($state) => $state.sessions.find((s2) => s2.session_id === $state.activeSessionId) || null
);
function L$1() {
  return { async: false, breaks: false, extensions: null, gfm: true, hooks: null, pedantic: false, renderer: null, silent: false, tokenizer: null, walkTokens: null };
}
var T$1 = L$1();
function Z$1(u4) {
  T$1 = u4;
}
var C$1 = { exec: () => null };
function k$1(u4, e2 = "") {
  let t2 = typeof u4 == "string" ? u4 : u4.source, n2 = { replace: (r2, i2) => {
    let s2 = typeof i2 == "string" ? i2 : i2.source;
    return s2 = s2.replace(m$1.caret, "$1"), t2 = t2.replace(r2, s2), n2;
  }, getRegex: () => new RegExp(t2, e2) };
  return n2;
}
var me$1 = (() => {
  try {
    return !!new RegExp("(?<=1)(?<!1)");
  } catch {
    return false;
  }
})(), m$1 = { codeRemoveIndent: /^(?: {1,4}| {0,3}\t)/gm, outputLinkReplace: /\\([\[\]])/g, indentCodeCompensation: /^(\s+)(?:```)/, beginningSpace: /^\s+/, endingHash: /#$/, startingSpaceChar: /^ /, endingSpaceChar: / $/, nonSpaceChar: /[^ ]/, newLineCharGlobal: /\n/g, tabCharGlobal: /\t/g, multipleSpaceGlobal: /\s+/g, blankLine: /^[ \t]*$/, doubleBlankLine: /\n[ \t]*\n[ \t]*$/, blockquoteStart: /^ {0,3}>/, blockquoteSetextReplace: /\n {0,3}((?:=+|-+) *)(?=\n|$)/g, blockquoteSetextReplace2: /^ {0,3}>[ \t]?/gm, listReplaceTabs: /^\t+/, listReplaceNesting: /^ {1,4}(?=( {4})*[^ ])/g, listIsTask: /^\[[ xX]\] +\S/, listReplaceTask: /^\[[ xX]\] +/, listTaskCheckbox: /\[[ xX]\]/, anyLine: /\n.*\n/, hrefBrackets: /^<(.*)>$/, tableDelimiter: /[:|]/, tableAlignChars: /^\||\| *$/g, tableRowBlankLine: /\n[ \t]*$/, tableAlignRight: /^ *-+: *$/, tableAlignCenter: /^ *:-+: *$/, tableAlignLeft: /^ *:-+ *$/, startATag: /^<a /i, endATag: /^<\/a>/i, startPreScriptTag: /^<(pre|code|kbd|script)(\s|>)/i, endPreScriptTag: /^<\/(pre|code|kbd|script)(\s|>)/i, startAngleBracket: /^</, endAngleBracket: />$/, pedanticHrefTitle: /^([^'"]*[^\s])\s+(['"])(.*)\2/, unicodeAlphaNumeric: /[\p{L}\p{N}]/u, escapeTest: /[&<>"']/, escapeReplace: /[&<>"']/g, escapeTestNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/, escapeReplaceNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g, unescapeTest: /&(#(?:\d+)|(?:#x[0-9A-Fa-f]+)|(?:\w+));?/ig, caret: /(^|[^\[])\^/g, percentDecode: /%25/g, findPipe: /\|/g, splitPipe: / \|/, slashPipe: /\\\|/g, carriageReturn: /\r\n|\r/g, spaceLine: /^ +$/gm, notSpaceStart: /^\S*/, endingNewline: /\n$/, listItemRegex: (u4) => new RegExp(`^( {0,3}${u4})((?:[	 ][^\\n]*)?(?:\\n|$))`), nextBulletRegex: (u4) => new RegExp(`^ {0,${Math.min(3, u4 - 1)}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`), hrRegex: (u4) => new RegExp(`^ {0,${Math.min(3, u4 - 1)}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`), fencesBeginRegex: (u4) => new RegExp(`^ {0,${Math.min(3, u4 - 1)}}(?:\`\`\`|~~~)`), headingBeginRegex: (u4) => new RegExp(`^ {0,${Math.min(3, u4 - 1)}}#`), htmlBeginRegex: (u4) => new RegExp(`^ {0,${Math.min(3, u4 - 1)}}<(?:[a-z].*>|!--)`, "i") }, xe$1 = /^(?:[ \t]*(?:\n|$))+/, be$1 = /^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/, Re$1 = /^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/, I$1 = /^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/, Te$1 = /^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/, N$1 = /(?:[*+-]|\d{1,9}[.)])/, re$1 = /^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/, se$1 = k$1(re$1).replace(/bull/g, N$1).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/\|table/g, "").getRegex(), Oe$1 = k$1(re$1).replace(/bull/g, N$1).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/table/g, / {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(), Q$1 = /^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table| +\n)[^\n]+)*)/, we$1 = /^[^\n]+/, F$1 = /(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/, ye$1 = k$1(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label", F$1).replace("title", /(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(), Pe$1 = k$1(/^( {0,3}bull)([ \t][^\n]+?)?(?:\n|$)/).replace(/bull/g, N$1).getRegex(), v$1 = "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul", j$1 = /<!--(?:-?>|[\s\S]*?(?:-->|$))/, Se$1 = k$1("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n+|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>\\n*|$)|<![A-Z][\\s\\S]*?(?:>\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))", "i").replace("comment", j$1).replace("tag", v$1).replace("attribute", / +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(), ie$1 = k$1(Q$1).replace("hr", I$1).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("|table", "").replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)]) ").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", v$1).getRegex(), $e$1 = k$1(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph", ie$1).getRegex(), U$1 = { blockquote: $e$1, code: be$1, def: ye$1, fences: Re$1, heading: Te$1, hr: I$1, html: Se$1, lheading: se$1, list: Pe$1, newline: xe$1, paragraph: ie$1, table: C$1, text: we$1 }, te$1 = k$1("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr", I$1).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("blockquote", " {0,3}>").replace("code", "(?: {4}| {0,3}	)[^\\n]").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)]) ").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", v$1).getRegex(), _e$1 = { ...U$1, lheading: Oe$1, table: te$1, paragraph: k$1(Q$1).replace("hr", I$1).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("table", te$1).replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)]) ").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", v$1).getRegex() }, Le$1 = { ...U$1, html: k$1(`^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:"[^"]*"|'[^']*'|\\s[^'"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))`).replace("comment", j$1).replace(/tag/g, "(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(), def: /^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/, heading: /^(#{1,6})(.*)(?:\n+|$)/, fences: C$1, lheading: /^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/, paragraph: k$1(Q$1).replace("hr", I$1).replace("heading", ` *#{1,6} *[^
]`).replace("lheading", se$1).replace("|table", "").replace("blockquote", " {0,3}>").replace("|fences", "").replace("|list", "").replace("|html", "").replace("|tag", "").getRegex() }, Me$1 = /^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/, ze$1 = /^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/, oe$1 = /^( {2,}|\\)\n(?!\s*$)/, Ae$1 = /^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/, D$1 = /[\p{P}\p{S}]/u, K$1 = /[\s\p{P}\p{S}]/u, ae$1 = /[^\s\p{P}\p{S}]/u, Ce$1 = k$1(/^((?![*_])punctSpace)/, "u").replace(/punctSpace/g, K$1).getRegex(), le$1 = /(?!~)[\p{P}\p{S}]/u, Ie$1 = /(?!~)[\s\p{P}\p{S}]/u, Ee$1 = /(?:[^\s\p{P}\p{S}]|~)/u, Be$1 = k$1(/link|precode-code|html/, "g").replace("link", /\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-", me$1 ? "(?<!`)()" : "(^^|[^`])").replace("code", /(?<b>`+)[^`]+\k<b>(?!`)/).replace("html", /<(?! )[^<>]*?>/).getRegex(), ue$1 = /^(?:\*+(?:((?!\*)punct)|[^\s*]))|^_+(?:((?!_)punct)|([^\s_]))/, qe = k$1(ue$1, "u").replace(/punct/g, D$1).getRegex(), ve$1 = k$1(ue$1, "u").replace(/punct/g, le$1).getRegex(), pe$1 = "^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)", De$1 = k$1(pe$1, "gu").replace(/notPunctSpace/g, ae$1).replace(/punctSpace/g, K$1).replace(/punct/g, D$1).getRegex(), He = k$1(pe$1, "gu").replace(/notPunctSpace/g, Ee$1).replace(/punctSpace/g, Ie$1).replace(/punct/g, le$1).getRegex(), Ze = k$1("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)", "gu").replace(/notPunctSpace/g, ae$1).replace(/punctSpace/g, K$1).replace(/punct/g, D$1).getRegex(), Ge = k$1(/\\(punct)/, "gu").replace(/punct/g, D$1).getRegex(), Ne$1 = k$1(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme", /[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email", /[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(), Qe = k$1(j$1).replace("(?:-->|$)", "-->").getRegex(), Fe$1 = k$1("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment", Qe).replace("attribute", /\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(), q$1 = /(?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+[^`]*?`+(?!`)|[^\[\]\\`])*?/, je$1 = k$1(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]*(?:\n[ \t]*)?)(title))?\s*\)/).replace("label", q$1).replace("href", /<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]*/).replace("title", /"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(), ce$1 = k$1(/^!?\[(label)\]\[(ref)\]/).replace("label", q$1).replace("ref", F$1).getRegex(), he$1 = k$1(/^!?\[(ref)\](?:\[\])?/).replace("ref", F$1).getRegex(), Ue$1 = k$1("reflink|nolink(?!\\()", "g").replace("reflink", ce$1).replace("nolink", he$1).getRegex(), ne$1 = /[hH][tT][tT][pP][sS]?|[fF][tT][pP]/, W$1 = { _backpedal: C$1, anyPunctuation: Ge, autolink: Ne$1, blockSkip: Be$1, br: oe$1, code: ze$1, del: C$1, emStrongLDelim: qe, emStrongRDelimAst: De$1, emStrongRDelimUnd: Ze, escape: Me$1, link: je$1, nolink: he$1, punctuation: Ce$1, reflink: ce$1, reflinkSearch: Ue$1, tag: Fe$1, text: Ae$1, url: C$1 }, Ke = { ...W$1, link: k$1(/^!?\[(label)\]\((.*?)\)/).replace("label", q$1).getRegex(), reflink: k$1(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label", q$1).getRegex() }, G$1 = { ...W$1, emStrongRDelimAst: He, emStrongLDelim: ve$1, url: k$1(/^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("protocol", ne$1).replace("email", /[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(), _backpedal: /(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/, del: /^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/, text: k$1(/^([`~]+|[^`~])(?:(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/).replace("protocol", ne$1).getRegex() }, We = { ...G$1, br: k$1(oe$1).replace("{2,}", "*").getRegex(), text: k$1(G$1.text).replace("\\b_", "\\b_| {2,}\\n").replace(/\{2,\}/g, "*").getRegex() }, E$1 = { normal: U$1, gfm: _e$1, pedantic: Le$1 }, M$1 = { normal: W$1, gfm: G$1, breaks: We, pedantic: Ke };
var Xe = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }, ke$1 = (u4) => Xe[u4];
function w$1(u4, e2) {
  if (e2) {
    if (m$1.escapeTest.test(u4)) return u4.replace(m$1.escapeReplace, ke$1);
  } else if (m$1.escapeTestNoEncode.test(u4)) return u4.replace(m$1.escapeReplaceNoEncode, ke$1);
  return u4;
}
function X$1(u4) {
  try {
    u4 = encodeURI(u4).replace(m$1.percentDecode, "%");
  } catch {
    return null;
  }
  return u4;
}
function J$1(u4, e2) {
  let t2 = u4.replace(m$1.findPipe, (i2, s2, a2) => {
    let o2 = false, l2 = s2;
    for (; --l2 >= 0 && a2[l2] === "\\"; ) o2 = !o2;
    return o2 ? "|" : " |";
  }), n2 = t2.split(m$1.splitPipe), r2 = 0;
  if (n2[0].trim() || n2.shift(), n2.length > 0 && !n2.at(-1)?.trim() && n2.pop(), e2) if (n2.length > e2) n2.splice(e2);
  else for (; n2.length < e2; ) n2.push("");
  for (; r2 < n2.length; r2++) n2[r2] = n2[r2].trim().replace(m$1.slashPipe, "|");
  return n2;
}
function z$1(u4, e2, t2) {
  let n2 = u4.length;
  if (n2 === 0) return "";
  let r2 = 0;
  for (; r2 < n2; ) {
    let i2 = u4.charAt(n2 - r2 - 1);
    if (i2 === e2 && true) r2++;
    else break;
  }
  return u4.slice(0, n2 - r2);
}
function de$1(u4, e2) {
  if (u4.indexOf(e2[1]) === -1) return -1;
  let t2 = 0;
  for (let n2 = 0; n2 < u4.length; n2++) if (u4[n2] === "\\") n2++;
  else if (u4[n2] === e2[0]) t2++;
  else if (u4[n2] === e2[1] && (t2--, t2 < 0)) return n2;
  return t2 > 0 ? -2 : -1;
}
function ge$1(u4, e2, t2, n2, r2) {
  let i2 = e2.href, s2 = e2.title || null, a2 = u4[1].replace(r2.other.outputLinkReplace, "$1");
  n2.state.inLink = true;
  let o2 = { type: u4[0].charAt(0) === "!" ? "image" : "link", raw: t2, href: i2, title: s2, text: a2, tokens: n2.inlineTokens(a2) };
  return n2.state.inLink = false, o2;
}
function Je(u4, e2, t2) {
  let n2 = u4.match(t2.other.indentCodeCompensation);
  if (n2 === null) return e2;
  let r2 = n2[1];
  return e2.split(`
`).map((i2) => {
    let s2 = i2.match(t2.other.beginningSpace);
    if (s2 === null) return i2;
    let [a2] = s2;
    return a2.length >= r2.length ? i2.slice(r2.length) : i2;
  }).join(`
`);
}
var y$1 = class y {
  options;
  rules;
  lexer;
  constructor(e2) {
    this.options = e2 || T$1;
  }
  space(e2) {
    let t2 = this.rules.block.newline.exec(e2);
    if (t2 && t2[0].length > 0) return { type: "space", raw: t2[0] };
  }
  code(e2) {
    let t2 = this.rules.block.code.exec(e2);
    if (t2) {
      let n2 = t2[0].replace(this.rules.other.codeRemoveIndent, "");
      return { type: "code", raw: t2[0], codeBlockStyle: "indented", text: this.options.pedantic ? n2 : z$1(n2, `
`) };
    }
  }
  fences(e2) {
    let t2 = this.rules.block.fences.exec(e2);
    if (t2) {
      let n2 = t2[0], r2 = Je(n2, t2[3] || "", this.rules);
      return { type: "code", raw: n2, lang: t2[2] ? t2[2].trim().replace(this.rules.inline.anyPunctuation, "$1") : t2[2], text: r2 };
    }
  }
  heading(e2) {
    let t2 = this.rules.block.heading.exec(e2);
    if (t2) {
      let n2 = t2[2].trim();
      if (this.rules.other.endingHash.test(n2)) {
        let r2 = z$1(n2, "#");
        (this.options.pedantic || !r2 || this.rules.other.endingSpaceChar.test(r2)) && (n2 = r2.trim());
      }
      return { type: "heading", raw: t2[0], depth: t2[1].length, text: n2, tokens: this.lexer.inline(n2) };
    }
  }
  hr(e2) {
    let t2 = this.rules.block.hr.exec(e2);
    if (t2) return { type: "hr", raw: z$1(t2[0], `
`) };
  }
  blockquote(e2) {
    let t2 = this.rules.block.blockquote.exec(e2);
    if (t2) {
      let n2 = z$1(t2[0], `
`).split(`
`), r2 = "", i2 = "", s2 = [];
      for (; n2.length > 0; ) {
        let a2 = false, o2 = [], l2;
        for (l2 = 0; l2 < n2.length; l2++) if (this.rules.other.blockquoteStart.test(n2[l2])) o2.push(n2[l2]), a2 = true;
        else if (!a2) o2.push(n2[l2]);
        else break;
        n2 = n2.slice(l2);
        let p2 = o2.join(`
`), c2 = p2.replace(this.rules.other.blockquoteSetextReplace, `
    $1`).replace(this.rules.other.blockquoteSetextReplace2, "");
        r2 = r2 ? `${r2}
${p2}` : p2, i2 = i2 ? `${i2}
${c2}` : c2;
        let g2 = this.lexer.state.top;
        if (this.lexer.state.top = true, this.lexer.blockTokens(c2, s2, true), this.lexer.state.top = g2, n2.length === 0) break;
        let h2 = s2.at(-1);
        if (h2?.type === "code") break;
        if (h2?.type === "blockquote") {
          let R2 = h2, f2 = R2.raw + `
` + n2.join(`
`), O2 = this.blockquote(f2);
          s2[s2.length - 1] = O2, r2 = r2.substring(0, r2.length - R2.raw.length) + O2.raw, i2 = i2.substring(0, i2.length - R2.text.length) + O2.text;
          break;
        } else if (h2?.type === "list") {
          let R2 = h2, f2 = R2.raw + `
` + n2.join(`
`), O2 = this.list(f2);
          s2[s2.length - 1] = O2, r2 = r2.substring(0, r2.length - h2.raw.length) + O2.raw, i2 = i2.substring(0, i2.length - R2.raw.length) + O2.raw, n2 = f2.substring(s2.at(-1).raw.length).split(`
`);
          continue;
        }
      }
      return { type: "blockquote", raw: r2, tokens: s2, text: i2 };
    }
  }
  list(e2) {
    let t2 = this.rules.block.list.exec(e2);
    if (t2) {
      let n2 = t2[1].trim(), r2 = n2.length > 1, i2 = { type: "list", raw: "", ordered: r2, start: r2 ? +n2.slice(0, -1) : "", loose: false, items: [] };
      n2 = r2 ? `\\d{1,9}\\${n2.slice(-1)}` : `\\${n2}`, this.options.pedantic && (n2 = r2 ? n2 : "[*+-]");
      let s2 = this.rules.other.listItemRegex(n2), a2 = false;
      for (; e2; ) {
        let l2 = false, p2 = "", c2 = "";
        if (!(t2 = s2.exec(e2)) || this.rules.block.hr.test(e2)) break;
        p2 = t2[0], e2 = e2.substring(p2.length);
        let g2 = t2[2].split(`
`, 1)[0].replace(this.rules.other.listReplaceTabs, (O2) => " ".repeat(3 * O2.length)), h2 = e2.split(`
`, 1)[0], R2 = !g2.trim(), f2 = 0;
        if (this.options.pedantic ? (f2 = 2, c2 = g2.trimStart()) : R2 ? f2 = t2[1].length + 1 : (f2 = t2[2].search(this.rules.other.nonSpaceChar), f2 = f2 > 4 ? 1 : f2, c2 = g2.slice(f2), f2 += t2[1].length), R2 && this.rules.other.blankLine.test(h2) && (p2 += h2 + `
`, e2 = e2.substring(h2.length + 1), l2 = true), !l2) {
          let O2 = this.rules.other.nextBulletRegex(f2), V2 = this.rules.other.hrRegex(f2), Y2 = this.rules.other.fencesBeginRegex(f2), ee2 = this.rules.other.headingBeginRegex(f2), fe2 = this.rules.other.htmlBeginRegex(f2);
          for (; e2; ) {
            let H2 = e2.split(`
`, 1)[0], A2;
            if (h2 = H2, this.options.pedantic ? (h2 = h2.replace(this.rules.other.listReplaceNesting, "  "), A2 = h2) : A2 = h2.replace(this.rules.other.tabCharGlobal, "    "), Y2.test(h2) || ee2.test(h2) || fe2.test(h2) || O2.test(h2) || V2.test(h2)) break;
            if (A2.search(this.rules.other.nonSpaceChar) >= f2 || !h2.trim()) c2 += `
` + A2.slice(f2);
            else {
              if (R2 || g2.replace(this.rules.other.tabCharGlobal, "    ").search(this.rules.other.nonSpaceChar) >= 4 || Y2.test(g2) || ee2.test(g2) || V2.test(g2)) break;
              c2 += `
` + h2;
            }
            !R2 && !h2.trim() && (R2 = true), p2 += H2 + `
`, e2 = e2.substring(H2.length + 1), g2 = A2.slice(f2);
          }
        }
        i2.loose || (a2 ? i2.loose = true : this.rules.other.doubleBlankLine.test(p2) && (a2 = true)), i2.items.push({ type: "list_item", raw: p2, task: !!this.options.gfm && this.rules.other.listIsTask.test(c2), loose: false, text: c2, tokens: [] }), i2.raw += p2;
      }
      let o2 = i2.items.at(-1);
      if (o2) o2.raw = o2.raw.trimEnd(), o2.text = o2.text.trimEnd();
      else return;
      i2.raw = i2.raw.trimEnd();
      for (let l2 of i2.items) {
        if (this.lexer.state.top = false, l2.tokens = this.lexer.blockTokens(l2.text, []), l2.task) {
          if (l2.text = l2.text.replace(this.rules.other.listReplaceTask, ""), l2.tokens[0]?.type === "text" || l2.tokens[0]?.type === "paragraph") {
            l2.tokens[0].raw = l2.tokens[0].raw.replace(this.rules.other.listReplaceTask, ""), l2.tokens[0].text = l2.tokens[0].text.replace(this.rules.other.listReplaceTask, "");
            for (let c2 = this.lexer.inlineQueue.length - 1; c2 >= 0; c2--) if (this.rules.other.listIsTask.test(this.lexer.inlineQueue[c2].src)) {
              this.lexer.inlineQueue[c2].src = this.lexer.inlineQueue[c2].src.replace(this.rules.other.listReplaceTask, "");
              break;
            }
          }
          let p2 = this.rules.other.listTaskCheckbox.exec(l2.raw);
          if (p2) {
            let c2 = { type: "checkbox", raw: p2[0] + " ", checked: p2[0] !== "[ ]" };
            l2.checked = c2.checked, i2.loose ? l2.tokens[0] && ["paragraph", "text"].includes(l2.tokens[0].type) && "tokens" in l2.tokens[0] && l2.tokens[0].tokens ? (l2.tokens[0].raw = c2.raw + l2.tokens[0].raw, l2.tokens[0].text = c2.raw + l2.tokens[0].text, l2.tokens[0].tokens.unshift(c2)) : l2.tokens.unshift({ type: "paragraph", raw: c2.raw, text: c2.raw, tokens: [c2] }) : l2.tokens.unshift(c2);
          }
        }
        if (!i2.loose) {
          let p2 = l2.tokens.filter((g2) => g2.type === "space"), c2 = p2.length > 0 && p2.some((g2) => this.rules.other.anyLine.test(g2.raw));
          i2.loose = c2;
        }
      }
      if (i2.loose) for (let l2 of i2.items) {
        l2.loose = true;
        for (let p2 of l2.tokens) p2.type === "text" && (p2.type = "paragraph");
      }
      return i2;
    }
  }
  html(e2) {
    let t2 = this.rules.block.html.exec(e2);
    if (t2) return { type: "html", block: true, raw: t2[0], pre: t2[1] === "pre" || t2[1] === "script" || t2[1] === "style", text: t2[0] };
  }
  def(e2) {
    let t2 = this.rules.block.def.exec(e2);
    if (t2) {
      let n2 = t2[1].toLowerCase().replace(this.rules.other.multipleSpaceGlobal, " "), r2 = t2[2] ? t2[2].replace(this.rules.other.hrefBrackets, "$1").replace(this.rules.inline.anyPunctuation, "$1") : "", i2 = t2[3] ? t2[3].substring(1, t2[3].length - 1).replace(this.rules.inline.anyPunctuation, "$1") : t2[3];
      return { type: "def", tag: n2, raw: t2[0], href: r2, title: i2 };
    }
  }
  table(e2) {
    let t2 = this.rules.block.table.exec(e2);
    if (!t2 || !this.rules.other.tableDelimiter.test(t2[2])) return;
    let n2 = J$1(t2[1]), r2 = t2[2].replace(this.rules.other.tableAlignChars, "").split("|"), i2 = t2[3]?.trim() ? t2[3].replace(this.rules.other.tableRowBlankLine, "").split(`
`) : [], s2 = { type: "table", raw: t2[0], header: [], align: [], rows: [] };
    if (n2.length === r2.length) {
      for (let a2 of r2) this.rules.other.tableAlignRight.test(a2) ? s2.align.push("right") : this.rules.other.tableAlignCenter.test(a2) ? s2.align.push("center") : this.rules.other.tableAlignLeft.test(a2) ? s2.align.push("left") : s2.align.push(null);
      for (let a2 = 0; a2 < n2.length; a2++) s2.header.push({ text: n2[a2], tokens: this.lexer.inline(n2[a2]), header: true, align: s2.align[a2] });
      for (let a2 of i2) s2.rows.push(J$1(a2, s2.header.length).map((o2, l2) => ({ text: o2, tokens: this.lexer.inline(o2), header: false, align: s2.align[l2] })));
      return s2;
    }
  }
  lheading(e2) {
    let t2 = this.rules.block.lheading.exec(e2);
    if (t2) return { type: "heading", raw: t2[0], depth: t2[2].charAt(0) === "=" ? 1 : 2, text: t2[1], tokens: this.lexer.inline(t2[1]) };
  }
  paragraph(e2) {
    let t2 = this.rules.block.paragraph.exec(e2);
    if (t2) {
      let n2 = t2[1].charAt(t2[1].length - 1) === `
` ? t2[1].slice(0, -1) : t2[1];
      return { type: "paragraph", raw: t2[0], text: n2, tokens: this.lexer.inline(n2) };
    }
  }
  text(e2) {
    let t2 = this.rules.block.text.exec(e2);
    if (t2) return { type: "text", raw: t2[0], text: t2[0], tokens: this.lexer.inline(t2[0]) };
  }
  escape(e2) {
    let t2 = this.rules.inline.escape.exec(e2);
    if (t2) return { type: "escape", raw: t2[0], text: t2[1] };
  }
  tag(e2) {
    let t2 = this.rules.inline.tag.exec(e2);
    if (t2) return !this.lexer.state.inLink && this.rules.other.startATag.test(t2[0]) ? this.lexer.state.inLink = true : this.lexer.state.inLink && this.rules.other.endATag.test(t2[0]) && (this.lexer.state.inLink = false), !this.lexer.state.inRawBlock && this.rules.other.startPreScriptTag.test(t2[0]) ? this.lexer.state.inRawBlock = true : this.lexer.state.inRawBlock && this.rules.other.endPreScriptTag.test(t2[0]) && (this.lexer.state.inRawBlock = false), { type: "html", raw: t2[0], inLink: this.lexer.state.inLink, inRawBlock: this.lexer.state.inRawBlock, block: false, text: t2[0] };
  }
  link(e2) {
    let t2 = this.rules.inline.link.exec(e2);
    if (t2) {
      let n2 = t2[2].trim();
      if (!this.options.pedantic && this.rules.other.startAngleBracket.test(n2)) {
        if (!this.rules.other.endAngleBracket.test(n2)) return;
        let s2 = z$1(n2.slice(0, -1), "\\");
        if ((n2.length - s2.length) % 2 === 0) return;
      } else {
        let s2 = de$1(t2[2], "()");
        if (s2 === -2) return;
        if (s2 > -1) {
          let o2 = (t2[0].indexOf("!") === 0 ? 5 : 4) + t2[1].length + s2;
          t2[2] = t2[2].substring(0, s2), t2[0] = t2[0].substring(0, o2).trim(), t2[3] = "";
        }
      }
      let r2 = t2[2], i2 = "";
      if (this.options.pedantic) {
        let s2 = this.rules.other.pedanticHrefTitle.exec(r2);
        s2 && (r2 = s2[1], i2 = s2[3]);
      } else i2 = t2[3] ? t2[3].slice(1, -1) : "";
      return r2 = r2.trim(), this.rules.other.startAngleBracket.test(r2) && (this.options.pedantic && !this.rules.other.endAngleBracket.test(n2) ? r2 = r2.slice(1) : r2 = r2.slice(1, -1)), ge$1(t2, { href: r2 && r2.replace(this.rules.inline.anyPunctuation, "$1"), title: i2 && i2.replace(this.rules.inline.anyPunctuation, "$1") }, t2[0], this.lexer, this.rules);
    }
  }
  reflink(e2, t2) {
    let n2;
    if ((n2 = this.rules.inline.reflink.exec(e2)) || (n2 = this.rules.inline.nolink.exec(e2))) {
      let r2 = (n2[2] || n2[1]).replace(this.rules.other.multipleSpaceGlobal, " "), i2 = t2[r2.toLowerCase()];
      if (!i2) {
        let s2 = n2[0].charAt(0);
        return { type: "text", raw: s2, text: s2 };
      }
      return ge$1(n2, i2, n2[0], this.lexer, this.rules);
    }
  }
  emStrong(e2, t2, n2 = "") {
    let r2 = this.rules.inline.emStrongLDelim.exec(e2);
    if (!r2 || r2[3] && n2.match(this.rules.other.unicodeAlphaNumeric)) return;
    if (!(r2[1] || r2[2] || "") || !n2 || this.rules.inline.punctuation.exec(n2)) {
      let s2 = [...r2[0]].length - 1, a2, o2, l2 = s2, p2 = 0, c2 = r2[0][0] === "*" ? this.rules.inline.emStrongRDelimAst : this.rules.inline.emStrongRDelimUnd;
      for (c2.lastIndex = 0, t2 = t2.slice(-1 * e2.length + s2); (r2 = c2.exec(t2)) != null; ) {
        if (a2 = r2[1] || r2[2] || r2[3] || r2[4] || r2[5] || r2[6], !a2) continue;
        if (o2 = [...a2].length, r2[3] || r2[4]) {
          l2 += o2;
          continue;
        } else if ((r2[5] || r2[6]) && s2 % 3 && !((s2 + o2) % 3)) {
          p2 += o2;
          continue;
        }
        if (l2 -= o2, l2 > 0) continue;
        o2 = Math.min(o2, o2 + l2 + p2);
        let g2 = [...r2[0]][0].length, h2 = e2.slice(0, s2 + r2.index + g2 + o2);
        if (Math.min(s2, o2) % 2) {
          let f2 = h2.slice(1, -1);
          return { type: "em", raw: h2, text: f2, tokens: this.lexer.inlineTokens(f2) };
        }
        let R2 = h2.slice(2, -2);
        return { type: "strong", raw: h2, text: R2, tokens: this.lexer.inlineTokens(R2) };
      }
    }
  }
  codespan(e2) {
    let t2 = this.rules.inline.code.exec(e2);
    if (t2) {
      let n2 = t2[2].replace(this.rules.other.newLineCharGlobal, " "), r2 = this.rules.other.nonSpaceChar.test(n2), i2 = this.rules.other.startingSpaceChar.test(n2) && this.rules.other.endingSpaceChar.test(n2);
      return r2 && i2 && (n2 = n2.substring(1, n2.length - 1)), { type: "codespan", raw: t2[0], text: n2 };
    }
  }
  br(e2) {
    let t2 = this.rules.inline.br.exec(e2);
    if (t2) return { type: "br", raw: t2[0] };
  }
  del(e2) {
    let t2 = this.rules.inline.del.exec(e2);
    if (t2) return { type: "del", raw: t2[0], text: t2[2], tokens: this.lexer.inlineTokens(t2[2]) };
  }
  autolink(e2) {
    let t2 = this.rules.inline.autolink.exec(e2);
    if (t2) {
      let n2, r2;
      return t2[2] === "@" ? (n2 = t2[1], r2 = "mailto:" + n2) : (n2 = t2[1], r2 = n2), { type: "link", raw: t2[0], text: n2, href: r2, tokens: [{ type: "text", raw: n2, text: n2 }] };
    }
  }
  url(e2) {
    let t2;
    if (t2 = this.rules.inline.url.exec(e2)) {
      let n2, r2;
      if (t2[2] === "@") n2 = t2[0], r2 = "mailto:" + n2;
      else {
        let i2;
        do
          i2 = t2[0], t2[0] = this.rules.inline._backpedal.exec(t2[0])?.[0] ?? "";
        while (i2 !== t2[0]);
        n2 = t2[0], t2[1] === "www." ? r2 = "http://" + t2[0] : r2 = t2[0];
      }
      return { type: "link", raw: t2[0], text: n2, href: r2, tokens: [{ type: "text", raw: n2, text: n2 }] };
    }
  }
  inlineText(e2) {
    let t2 = this.rules.inline.text.exec(e2);
    if (t2) {
      let n2 = this.lexer.state.inRawBlock;
      return { type: "text", raw: t2[0], text: t2[0], escaped: n2 };
    }
  }
};
var x$1 = class u {
  tokens;
  options;
  state;
  inlineQueue;
  tokenizer;
  constructor(e2) {
    this.tokens = [], this.tokens.links = /* @__PURE__ */ Object.create(null), this.options = e2 || T$1, this.options.tokenizer = this.options.tokenizer || new y$1(), this.tokenizer = this.options.tokenizer, this.tokenizer.options = this.options, this.tokenizer.lexer = this, this.inlineQueue = [], this.state = { inLink: false, inRawBlock: false, top: true };
    let t2 = { other: m$1, block: E$1.normal, inline: M$1.normal };
    this.options.pedantic ? (t2.block = E$1.pedantic, t2.inline = M$1.pedantic) : this.options.gfm && (t2.block = E$1.gfm, this.options.breaks ? t2.inline = M$1.breaks : t2.inline = M$1.gfm), this.tokenizer.rules = t2;
  }
  static get rules() {
    return { block: E$1, inline: M$1 };
  }
  static lex(e2, t2) {
    return new u(t2).lex(e2);
  }
  static lexInline(e2, t2) {
    return new u(t2).inlineTokens(e2);
  }
  lex(e2) {
    e2 = e2.replace(m$1.carriageReturn, `
`), this.blockTokens(e2, this.tokens);
    for (let t2 = 0; t2 < this.inlineQueue.length; t2++) {
      let n2 = this.inlineQueue[t2];
      this.inlineTokens(n2.src, n2.tokens);
    }
    return this.inlineQueue = [], this.tokens;
  }
  blockTokens(e2, t2 = [], n2 = false) {
    for (this.options.pedantic && (e2 = e2.replace(m$1.tabCharGlobal, "    ").replace(m$1.spaceLine, "")); e2; ) {
      let r2;
      if (this.options.extensions?.block?.some((s2) => (r2 = s2.call({ lexer: this }, e2, t2)) ? (e2 = e2.substring(r2.raw.length), t2.push(r2), true) : false)) continue;
      if (r2 = this.tokenizer.space(e2)) {
        e2 = e2.substring(r2.raw.length);
        let s2 = t2.at(-1);
        r2.raw.length === 1 && s2 !== void 0 ? s2.raw += `
` : t2.push(r2);
        continue;
      }
      if (r2 = this.tokenizer.code(e2)) {
        e2 = e2.substring(r2.raw.length);
        let s2 = t2.at(-1);
        s2?.type === "paragraph" || s2?.type === "text" ? (s2.raw += (s2.raw.endsWith(`
`) ? "" : `
`) + r2.raw, s2.text += `
` + r2.text, this.inlineQueue.at(-1).src = s2.text) : t2.push(r2);
        continue;
      }
      if (r2 = this.tokenizer.fences(e2)) {
        e2 = e2.substring(r2.raw.length), t2.push(r2);
        continue;
      }
      if (r2 = this.tokenizer.heading(e2)) {
        e2 = e2.substring(r2.raw.length), t2.push(r2);
        continue;
      }
      if (r2 = this.tokenizer.hr(e2)) {
        e2 = e2.substring(r2.raw.length), t2.push(r2);
        continue;
      }
      if (r2 = this.tokenizer.blockquote(e2)) {
        e2 = e2.substring(r2.raw.length), t2.push(r2);
        continue;
      }
      if (r2 = this.tokenizer.list(e2)) {
        e2 = e2.substring(r2.raw.length), t2.push(r2);
        continue;
      }
      if (r2 = this.tokenizer.html(e2)) {
        e2 = e2.substring(r2.raw.length), t2.push(r2);
        continue;
      }
      if (r2 = this.tokenizer.def(e2)) {
        e2 = e2.substring(r2.raw.length);
        let s2 = t2.at(-1);
        s2?.type === "paragraph" || s2?.type === "text" ? (s2.raw += (s2.raw.endsWith(`
`) ? "" : `
`) + r2.raw, s2.text += `
` + r2.raw, this.inlineQueue.at(-1).src = s2.text) : this.tokens.links[r2.tag] || (this.tokens.links[r2.tag] = { href: r2.href, title: r2.title }, t2.push(r2));
        continue;
      }
      if (r2 = this.tokenizer.table(e2)) {
        e2 = e2.substring(r2.raw.length), t2.push(r2);
        continue;
      }
      if (r2 = this.tokenizer.lheading(e2)) {
        e2 = e2.substring(r2.raw.length), t2.push(r2);
        continue;
      }
      let i2 = e2;
      if (this.options.extensions?.startBlock) {
        let s2 = 1 / 0, a2 = e2.slice(1), o2;
        this.options.extensions.startBlock.forEach((l2) => {
          o2 = l2.call({ lexer: this }, a2), typeof o2 == "number" && o2 >= 0 && (s2 = Math.min(s2, o2));
        }), s2 < 1 / 0 && s2 >= 0 && (i2 = e2.substring(0, s2 + 1));
      }
      if (this.state.top && (r2 = this.tokenizer.paragraph(i2))) {
        let s2 = t2.at(-1);
        n2 && s2?.type === "paragraph" ? (s2.raw += (s2.raw.endsWith(`
`) ? "" : `
`) + r2.raw, s2.text += `
` + r2.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = s2.text) : t2.push(r2), n2 = i2.length !== e2.length, e2 = e2.substring(r2.raw.length);
        continue;
      }
      if (r2 = this.tokenizer.text(e2)) {
        e2 = e2.substring(r2.raw.length);
        let s2 = t2.at(-1);
        s2?.type === "text" ? (s2.raw += (s2.raw.endsWith(`
`) ? "" : `
`) + r2.raw, s2.text += `
` + r2.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = s2.text) : t2.push(r2);
        continue;
      }
      if (e2) {
        let s2 = "Infinite loop on byte: " + e2.charCodeAt(0);
        if (this.options.silent) {
          console.error(s2);
          break;
        } else throw new Error(s2);
      }
    }
    return this.state.top = true, t2;
  }
  inline(e2, t2 = []) {
    return this.inlineQueue.push({ src: e2, tokens: t2 }), t2;
  }
  inlineTokens(e2, t2 = []) {
    let n2 = e2, r2 = null;
    if (this.tokens.links) {
      let o2 = Object.keys(this.tokens.links);
      if (o2.length > 0) for (; (r2 = this.tokenizer.rules.inline.reflinkSearch.exec(n2)) != null; ) o2.includes(r2[0].slice(r2[0].lastIndexOf("[") + 1, -1)) && (n2 = n2.slice(0, r2.index) + "[" + "a".repeat(r2[0].length - 2) + "]" + n2.slice(this.tokenizer.rules.inline.reflinkSearch.lastIndex));
    }
    for (; (r2 = this.tokenizer.rules.inline.anyPunctuation.exec(n2)) != null; ) n2 = n2.slice(0, r2.index) + "++" + n2.slice(this.tokenizer.rules.inline.anyPunctuation.lastIndex);
    let i2;
    for (; (r2 = this.tokenizer.rules.inline.blockSkip.exec(n2)) != null; ) i2 = r2[2] ? r2[2].length : 0, n2 = n2.slice(0, r2.index + i2) + "[" + "a".repeat(r2[0].length - i2 - 2) + "]" + n2.slice(this.tokenizer.rules.inline.blockSkip.lastIndex);
    n2 = this.options.hooks?.emStrongMask?.call({ lexer: this }, n2) ?? n2;
    let s2 = false, a2 = "";
    for (; e2; ) {
      s2 || (a2 = ""), s2 = false;
      let o2;
      if (this.options.extensions?.inline?.some((p2) => (o2 = p2.call({ lexer: this }, e2, t2)) ? (e2 = e2.substring(o2.raw.length), t2.push(o2), true) : false)) continue;
      if (o2 = this.tokenizer.escape(e2)) {
        e2 = e2.substring(o2.raw.length), t2.push(o2);
        continue;
      }
      if (o2 = this.tokenizer.tag(e2)) {
        e2 = e2.substring(o2.raw.length), t2.push(o2);
        continue;
      }
      if (o2 = this.tokenizer.link(e2)) {
        e2 = e2.substring(o2.raw.length), t2.push(o2);
        continue;
      }
      if (o2 = this.tokenizer.reflink(e2, this.tokens.links)) {
        e2 = e2.substring(o2.raw.length);
        let p2 = t2.at(-1);
        o2.type === "text" && p2?.type === "text" ? (p2.raw += o2.raw, p2.text += o2.text) : t2.push(o2);
        continue;
      }
      if (o2 = this.tokenizer.emStrong(e2, n2, a2)) {
        e2 = e2.substring(o2.raw.length), t2.push(o2);
        continue;
      }
      if (o2 = this.tokenizer.codespan(e2)) {
        e2 = e2.substring(o2.raw.length), t2.push(o2);
        continue;
      }
      if (o2 = this.tokenizer.br(e2)) {
        e2 = e2.substring(o2.raw.length), t2.push(o2);
        continue;
      }
      if (o2 = this.tokenizer.del(e2)) {
        e2 = e2.substring(o2.raw.length), t2.push(o2);
        continue;
      }
      if (o2 = this.tokenizer.autolink(e2)) {
        e2 = e2.substring(o2.raw.length), t2.push(o2);
        continue;
      }
      if (!this.state.inLink && (o2 = this.tokenizer.url(e2))) {
        e2 = e2.substring(o2.raw.length), t2.push(o2);
        continue;
      }
      let l2 = e2;
      if (this.options.extensions?.startInline) {
        let p2 = 1 / 0, c2 = e2.slice(1), g2;
        this.options.extensions.startInline.forEach((h2) => {
          g2 = h2.call({ lexer: this }, c2), typeof g2 == "number" && g2 >= 0 && (p2 = Math.min(p2, g2));
        }), p2 < 1 / 0 && p2 >= 0 && (l2 = e2.substring(0, p2 + 1));
      }
      if (o2 = this.tokenizer.inlineText(l2)) {
        e2 = e2.substring(o2.raw.length), o2.raw.slice(-1) !== "_" && (a2 = o2.raw.slice(-1)), s2 = true;
        let p2 = t2.at(-1);
        p2?.type === "text" ? (p2.raw += o2.raw, p2.text += o2.text) : t2.push(o2);
        continue;
      }
      if (e2) {
        let p2 = "Infinite loop on byte: " + e2.charCodeAt(0);
        if (this.options.silent) {
          console.error(p2);
          break;
        } else throw new Error(p2);
      }
    }
    return t2;
  }
};
var P$1 = class P {
  options;
  parser;
  constructor(e2) {
    this.options = e2 || T$1;
  }
  space(e2) {
    return "";
  }
  code({ text: e2, lang: t2, escaped: n2 }) {
    let r2 = (t2 || "").match(m$1.notSpaceStart)?.[0], i2 = e2.replace(m$1.endingNewline, "") + `
`;
    return r2 ? '<pre><code class="language-' + w$1(r2) + '">' + (n2 ? i2 : w$1(i2, true)) + `</code></pre>
` : "<pre><code>" + (n2 ? i2 : w$1(i2, true)) + `</code></pre>
`;
  }
  blockquote({ tokens: e2 }) {
    return `<blockquote>
${this.parser.parse(e2)}</blockquote>
`;
  }
  html({ text: e2 }) {
    return e2;
  }
  def(e2) {
    return "";
  }
  heading({ tokens: e2, depth: t2 }) {
    return `<h${t2}>${this.parser.parseInline(e2)}</h${t2}>
`;
  }
  hr(e2) {
    return `<hr>
`;
  }
  list(e2) {
    let t2 = e2.ordered, n2 = e2.start, r2 = "";
    for (let a2 = 0; a2 < e2.items.length; a2++) {
      let o2 = e2.items[a2];
      r2 += this.listitem(o2);
    }
    let i2 = t2 ? "ol" : "ul", s2 = t2 && n2 !== 1 ? ' start="' + n2 + '"' : "";
    return "<" + i2 + s2 + `>
` + r2 + "</" + i2 + `>
`;
  }
  listitem(e2) {
    return `<li>${this.parser.parse(e2.tokens)}</li>
`;
  }
  checkbox({ checked: e2 }) {
    return "<input " + (e2 ? 'checked="" ' : "") + 'disabled="" type="checkbox"> ';
  }
  paragraph({ tokens: e2 }) {
    return `<p>${this.parser.parseInline(e2)}</p>
`;
  }
  table(e2) {
    let t2 = "", n2 = "";
    for (let i2 = 0; i2 < e2.header.length; i2++) n2 += this.tablecell(e2.header[i2]);
    t2 += this.tablerow({ text: n2 });
    let r2 = "";
    for (let i2 = 0; i2 < e2.rows.length; i2++) {
      let s2 = e2.rows[i2];
      n2 = "";
      for (let a2 = 0; a2 < s2.length; a2++) n2 += this.tablecell(s2[a2]);
      r2 += this.tablerow({ text: n2 });
    }
    return r2 && (r2 = `<tbody>${r2}</tbody>`), `<table>
<thead>
` + t2 + `</thead>
` + r2 + `</table>
`;
  }
  tablerow({ text: e2 }) {
    return `<tr>
${e2}</tr>
`;
  }
  tablecell(e2) {
    let t2 = this.parser.parseInline(e2.tokens), n2 = e2.header ? "th" : "td";
    return (e2.align ? `<${n2} align="${e2.align}">` : `<${n2}>`) + t2 + `</${n2}>
`;
  }
  strong({ tokens: e2 }) {
    return `<strong>${this.parser.parseInline(e2)}</strong>`;
  }
  em({ tokens: e2 }) {
    return `<em>${this.parser.parseInline(e2)}</em>`;
  }
  codespan({ text: e2 }) {
    return `<code>${w$1(e2, true)}</code>`;
  }
  br(e2) {
    return "<br>";
  }
  del({ tokens: e2 }) {
    return `<del>${this.parser.parseInline(e2)}</del>`;
  }
  link({ href: e2, title: t2, tokens: n2 }) {
    let r2 = this.parser.parseInline(n2), i2 = X$1(e2);
    if (i2 === null) return r2;
    e2 = i2;
    let s2 = '<a href="' + e2 + '"';
    return t2 && (s2 += ' title="' + w$1(t2) + '"'), s2 += ">" + r2 + "</a>", s2;
  }
  image({ href: e2, title: t2, text: n2, tokens: r2 }) {
    r2 && (n2 = this.parser.parseInline(r2, this.parser.textRenderer));
    let i2 = X$1(e2);
    if (i2 === null) return w$1(n2);
    e2 = i2;
    let s2 = `<img src="${e2}" alt="${n2}"`;
    return t2 && (s2 += ` title="${w$1(t2)}"`), s2 += ">", s2;
  }
  text(e2) {
    return "tokens" in e2 && e2.tokens ? this.parser.parseInline(e2.tokens) : "escaped" in e2 && e2.escaped ? e2.text : w$1(e2.text);
  }
};
var $$1 = class $ {
  strong({ text: e2 }) {
    return e2;
  }
  em({ text: e2 }) {
    return e2;
  }
  codespan({ text: e2 }) {
    return e2;
  }
  del({ text: e2 }) {
    return e2;
  }
  html({ text: e2 }) {
    return e2;
  }
  text({ text: e2 }) {
    return e2;
  }
  link({ text: e2 }) {
    return "" + e2;
  }
  image({ text: e2 }) {
    return "" + e2;
  }
  br() {
    return "";
  }
  checkbox({ raw: e2 }) {
    return e2;
  }
};
var b$1 = class u2 {
  options;
  renderer;
  textRenderer;
  constructor(e2) {
    this.options = e2 || T$1, this.options.renderer = this.options.renderer || new P$1(), this.renderer = this.options.renderer, this.renderer.options = this.options, this.renderer.parser = this, this.textRenderer = new $$1();
  }
  static parse(e2, t2) {
    return new u2(t2).parse(e2);
  }
  static parseInline(e2, t2) {
    return new u2(t2).parseInline(e2);
  }
  parse(e2) {
    let t2 = "";
    for (let n2 = 0; n2 < e2.length; n2++) {
      let r2 = e2[n2];
      if (this.options.extensions?.renderers?.[r2.type]) {
        let s2 = r2, a2 = this.options.extensions.renderers[s2.type].call({ parser: this }, s2);
        if (a2 !== false || !["space", "hr", "heading", "code", "table", "blockquote", "list", "html", "def", "paragraph", "text"].includes(s2.type)) {
          t2 += a2 || "";
          continue;
        }
      }
      let i2 = r2;
      switch (i2.type) {
        case "space": {
          t2 += this.renderer.space(i2);
          break;
        }
        case "hr": {
          t2 += this.renderer.hr(i2);
          break;
        }
        case "heading": {
          t2 += this.renderer.heading(i2);
          break;
        }
        case "code": {
          t2 += this.renderer.code(i2);
          break;
        }
        case "table": {
          t2 += this.renderer.table(i2);
          break;
        }
        case "blockquote": {
          t2 += this.renderer.blockquote(i2);
          break;
        }
        case "list": {
          t2 += this.renderer.list(i2);
          break;
        }
        case "checkbox": {
          t2 += this.renderer.checkbox(i2);
          break;
        }
        case "html": {
          t2 += this.renderer.html(i2);
          break;
        }
        case "def": {
          t2 += this.renderer.def(i2);
          break;
        }
        case "paragraph": {
          t2 += this.renderer.paragraph(i2);
          break;
        }
        case "text": {
          t2 += this.renderer.text(i2);
          break;
        }
        default: {
          let s2 = 'Token with "' + i2.type + '" type was not found.';
          if (this.options.silent) return console.error(s2), "";
          throw new Error(s2);
        }
      }
    }
    return t2;
  }
  parseInline(e2, t2 = this.renderer) {
    let n2 = "";
    for (let r2 = 0; r2 < e2.length; r2++) {
      let i2 = e2[r2];
      if (this.options.extensions?.renderers?.[i2.type]) {
        let a2 = this.options.extensions.renderers[i2.type].call({ parser: this }, i2);
        if (a2 !== false || !["escape", "html", "link", "image", "strong", "em", "codespan", "br", "del", "text"].includes(i2.type)) {
          n2 += a2 || "";
          continue;
        }
      }
      let s2 = i2;
      switch (s2.type) {
        case "escape": {
          n2 += t2.text(s2);
          break;
        }
        case "html": {
          n2 += t2.html(s2);
          break;
        }
        case "link": {
          n2 += t2.link(s2);
          break;
        }
        case "image": {
          n2 += t2.image(s2);
          break;
        }
        case "checkbox": {
          n2 += t2.checkbox(s2);
          break;
        }
        case "strong": {
          n2 += t2.strong(s2);
          break;
        }
        case "em": {
          n2 += t2.em(s2);
          break;
        }
        case "codespan": {
          n2 += t2.codespan(s2);
          break;
        }
        case "br": {
          n2 += t2.br(s2);
          break;
        }
        case "del": {
          n2 += t2.del(s2);
          break;
        }
        case "text": {
          n2 += t2.text(s2);
          break;
        }
        default: {
          let a2 = 'Token with "' + s2.type + '" type was not found.';
          if (this.options.silent) return console.error(a2), "";
          throw new Error(a2);
        }
      }
    }
    return n2;
  }
};
var S$1 = class S {
  options;
  block;
  constructor(e2) {
    this.options = e2 || T$1;
  }
  static passThroughHooks = /* @__PURE__ */ new Set(["preprocess", "postprocess", "processAllTokens", "emStrongMask"]);
  static passThroughHooksRespectAsync = /* @__PURE__ */ new Set(["preprocess", "postprocess", "processAllTokens"]);
  preprocess(e2) {
    return e2;
  }
  postprocess(e2) {
    return e2;
  }
  processAllTokens(e2) {
    return e2;
  }
  emStrongMask(e2) {
    return e2;
  }
  provideLexer() {
    return this.block ? x$1.lex : x$1.lexInline;
  }
  provideParser() {
    return this.block ? b$1.parse : b$1.parseInline;
  }
};
var B$1 = class B {
  defaults = L$1();
  options = this.setOptions;
  parse = this.parseMarkdown(true);
  parseInline = this.parseMarkdown(false);
  Parser = b$1;
  Renderer = P$1;
  TextRenderer = $$1;
  Lexer = x$1;
  Tokenizer = y$1;
  Hooks = S$1;
  constructor(...e2) {
    this.use(...e2);
  }
  walkTokens(e2, t2) {
    let n2 = [];
    for (let r2 of e2) switch (n2 = n2.concat(t2.call(this, r2)), r2.type) {
      case "table": {
        let i2 = r2;
        for (let s2 of i2.header) n2 = n2.concat(this.walkTokens(s2.tokens, t2));
        for (let s2 of i2.rows) for (let a2 of s2) n2 = n2.concat(this.walkTokens(a2.tokens, t2));
        break;
      }
      case "list": {
        let i2 = r2;
        n2 = n2.concat(this.walkTokens(i2.items, t2));
        break;
      }
      default: {
        let i2 = r2;
        this.defaults.extensions?.childTokens?.[i2.type] ? this.defaults.extensions.childTokens[i2.type].forEach((s2) => {
          let a2 = i2[s2].flat(1 / 0);
          n2 = n2.concat(this.walkTokens(a2, t2));
        }) : i2.tokens && (n2 = n2.concat(this.walkTokens(i2.tokens, t2)));
      }
    }
    return n2;
  }
  use(...e2) {
    let t2 = this.defaults.extensions || { renderers: {}, childTokens: {} };
    return e2.forEach((n2) => {
      let r2 = { ...n2 };
      if (r2.async = this.defaults.async || r2.async || false, n2.extensions && (n2.extensions.forEach((i2) => {
        if (!i2.name) throw new Error("extension name required");
        if ("renderer" in i2) {
          let s2 = t2.renderers[i2.name];
          s2 ? t2.renderers[i2.name] = function(...a2) {
            let o2 = i2.renderer.apply(this, a2);
            return o2 === false && (o2 = s2.apply(this, a2)), o2;
          } : t2.renderers[i2.name] = i2.renderer;
        }
        if ("tokenizer" in i2) {
          if (!i2.level || i2.level !== "block" && i2.level !== "inline") throw new Error("extension level must be 'block' or 'inline'");
          let s2 = t2[i2.level];
          s2 ? s2.unshift(i2.tokenizer) : t2[i2.level] = [i2.tokenizer], i2.start && (i2.level === "block" ? t2.startBlock ? t2.startBlock.push(i2.start) : t2.startBlock = [i2.start] : i2.level === "inline" && (t2.startInline ? t2.startInline.push(i2.start) : t2.startInline = [i2.start]));
        }
        "childTokens" in i2 && i2.childTokens && (t2.childTokens[i2.name] = i2.childTokens);
      }), r2.extensions = t2), n2.renderer) {
        let i2 = this.defaults.renderer || new P$1(this.defaults);
        for (let s2 in n2.renderer) {
          if (!(s2 in i2)) throw new Error(`renderer '${s2}' does not exist`);
          if (["options", "parser"].includes(s2)) continue;
          let a2 = s2, o2 = n2.renderer[a2], l2 = i2[a2];
          i2[a2] = (...p2) => {
            let c2 = o2.apply(i2, p2);
            return c2 === false && (c2 = l2.apply(i2, p2)), c2 || "";
          };
        }
        r2.renderer = i2;
      }
      if (n2.tokenizer) {
        let i2 = this.defaults.tokenizer || new y$1(this.defaults);
        for (let s2 in n2.tokenizer) {
          if (!(s2 in i2)) throw new Error(`tokenizer '${s2}' does not exist`);
          if (["options", "rules", "lexer"].includes(s2)) continue;
          let a2 = s2, o2 = n2.tokenizer[a2], l2 = i2[a2];
          i2[a2] = (...p2) => {
            let c2 = o2.apply(i2, p2);
            return c2 === false && (c2 = l2.apply(i2, p2)), c2;
          };
        }
        r2.tokenizer = i2;
      }
      if (n2.hooks) {
        let i2 = this.defaults.hooks || new S$1();
        for (let s2 in n2.hooks) {
          if (!(s2 in i2)) throw new Error(`hook '${s2}' does not exist`);
          if (["options", "block"].includes(s2)) continue;
          let a2 = s2, o2 = n2.hooks[a2], l2 = i2[a2];
          S$1.passThroughHooks.has(s2) ? i2[a2] = (p2) => {
            if (this.defaults.async && S$1.passThroughHooksRespectAsync.has(s2)) return (async () => {
              let g2 = await o2.call(i2, p2);
              return l2.call(i2, g2);
            })();
            let c2 = o2.call(i2, p2);
            return l2.call(i2, c2);
          } : i2[a2] = (...p2) => {
            if (this.defaults.async) return (async () => {
              let g2 = await o2.apply(i2, p2);
              return g2 === false && (g2 = await l2.apply(i2, p2)), g2;
            })();
            let c2 = o2.apply(i2, p2);
            return c2 === false && (c2 = l2.apply(i2, p2)), c2;
          };
        }
        r2.hooks = i2;
      }
      if (n2.walkTokens) {
        let i2 = this.defaults.walkTokens, s2 = n2.walkTokens;
        r2.walkTokens = function(a2) {
          let o2 = [];
          return o2.push(s2.call(this, a2)), i2 && (o2 = o2.concat(i2.call(this, a2))), o2;
        };
      }
      this.defaults = { ...this.defaults, ...r2 };
    }), this;
  }
  setOptions(e2) {
    return this.defaults = { ...this.defaults, ...e2 }, this;
  }
  lexer(e2, t2) {
    return x$1.lex(e2, t2 ?? this.defaults);
  }
  parser(e2, t2) {
    return b$1.parse(e2, t2 ?? this.defaults);
  }
  parseMarkdown(e2) {
    return (n2, r2) => {
      let i2 = { ...r2 }, s2 = { ...this.defaults, ...i2 }, a2 = this.onError(!!s2.silent, !!s2.async);
      if (this.defaults.async === true && i2.async === false) return a2(new Error("marked(): The async option was set to true by an extension. Remove async: false from the parse options object to return a Promise."));
      if (typeof n2 > "u" || n2 === null) return a2(new Error("marked(): input parameter is undefined or null"));
      if (typeof n2 != "string") return a2(new Error("marked(): input parameter is of type " + Object.prototype.toString.call(n2) + ", string expected"));
      if (s2.hooks && (s2.hooks.options = s2, s2.hooks.block = e2), s2.async) return (async () => {
        let o2 = s2.hooks ? await s2.hooks.preprocess(n2) : n2, p2 = await (s2.hooks ? await s2.hooks.provideLexer() : e2 ? x$1.lex : x$1.lexInline)(o2, s2), c2 = s2.hooks ? await s2.hooks.processAllTokens(p2) : p2;
        s2.walkTokens && await Promise.all(this.walkTokens(c2, s2.walkTokens));
        let h2 = await (s2.hooks ? await s2.hooks.provideParser() : e2 ? b$1.parse : b$1.parseInline)(c2, s2);
        return s2.hooks ? await s2.hooks.postprocess(h2) : h2;
      })().catch(a2);
      try {
        s2.hooks && (n2 = s2.hooks.preprocess(n2));
        let l2 = (s2.hooks ? s2.hooks.provideLexer() : e2 ? x$1.lex : x$1.lexInline)(n2, s2);
        s2.hooks && (l2 = s2.hooks.processAllTokens(l2)), s2.walkTokens && this.walkTokens(l2, s2.walkTokens);
        let c2 = (s2.hooks ? s2.hooks.provideParser() : e2 ? b$1.parse : b$1.parseInline)(l2, s2);
        return s2.hooks && (c2 = s2.hooks.postprocess(c2)), c2;
      } catch (o2) {
        return a2(o2);
      }
    };
  }
  onError(e2, t2) {
    return (n2) => {
      if (n2.message += `
Please report this to https://github.com/markedjs/marked.`, e2) {
        let r2 = "<p>An error occurred:</p><pre>" + w$1(n2.message + "", true) + "</pre>";
        return t2 ? Promise.resolve(r2) : r2;
      }
      if (t2) return Promise.reject(n2);
      throw n2;
    };
  }
};
var _$1 = new B$1();
function d$1(u4, e2) {
  return _$1.parse(u4, e2);
}
d$1.options = d$1.setOptions = function(u4) {
  return _$1.setOptions(u4), d$1.defaults = _$1.defaults, Z$1(d$1.defaults), d$1;
};
d$1.getDefaults = L$1;
d$1.defaults = T$1;
d$1.use = function(...u4) {
  return _$1.use(...u4), d$1.defaults = _$1.defaults, Z$1(d$1.defaults), d$1;
};
d$1.walkTokens = function(u4, e2) {
  return _$1.walkTokens(u4, e2);
};
d$1.parseInline = _$1.parseInline;
d$1.Parser = b$1;
d$1.parser = b$1.parse;
d$1.Renderer = P$1;
d$1.TextRenderer = $$1;
d$1.Lexer = x$1;
d$1.lexer = x$1.lex;
d$1.Tokenizer = y$1;
d$1.Hooks = S$1;
d$1.parse = d$1;
d$1.options;
d$1.setOptions;
d$1.use;
d$1.walkTokens;
d$1.parseInline;
b$1.parse;
x$1.lex;
function markedHighlight(options) {
  if (typeof options === "function") {
    options = {
      highlight: options
    };
  }
  if (!options || typeof options.highlight !== "function") {
    throw new Error("Must provide highlight function");
  }
  if (typeof options.langPrefix !== "string") {
    options.langPrefix = "language-";
  }
  if (typeof options.emptyLangClass !== "string") {
    options.emptyLangClass = "";
  }
  return {
    async: !!options.async,
    walkTokens(token) {
      if (token.type !== "code") {
        return;
      }
      const lang = getLang(token.lang);
      if (options.async) {
        return Promise.resolve(options.highlight(token.text, lang, token.lang || "")).then(updateToken(token));
      }
      const code = options.highlight(token.text, lang, token.lang || "");
      if (code instanceof Promise) {
        throw new Error("markedHighlight is not set to async but the highlight function is async. Set the async option to true on markedHighlight to await the async highlight function.");
      }
      updateToken(token)(code);
    },
    useNewRenderer: true,
    renderer: {
      code(code, infoString, escaped) {
        if (typeof code === "object") {
          escaped = code.escaped;
          infoString = code.lang;
          code = code.text;
        }
        const lang = getLang(infoString);
        const classValue = lang ? options.langPrefix + escape(lang) : options.emptyLangClass;
        const classAttr = classValue ? ` class="${classValue}"` : "";
        code = code.replace(/\n$/, "");
        return `<pre><code${classAttr}>${escaped ? code : escape(code, true)}
</code></pre>`;
      }
    }
  };
}
function getLang(lang) {
  return (lang || "").match(/\S*/)[0];
}
function updateToken(token) {
  return (code) => {
    if (typeof code === "string" && code !== token.text) {
      token.escaped = true;
      token.text = code;
    }
  };
}
const escapeTest = /[&<>"']/;
const escapeReplace = new RegExp(escapeTest.source, "g");
const escapeTestNoEncode = /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/;
const escapeReplaceNoEncode = new RegExp(escapeTestNoEncode.source, "g");
const escapeReplacements = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;"
};
const getEscapeReplacement = (ch) => escapeReplacements[ch];
function escape(html2, encode) {
  if (encode) {
    if (escapeTest.test(html2)) {
      return html2.replace(escapeReplace, getEscapeReplacement);
    }
  } else {
    if (escapeTestNoEncode.test(html2)) {
      return html2.replace(escapeReplaceNoEncode, getEscapeReplacement);
    }
  }
  return html2;
}
function e(n2) {
  return n2 instanceof Map ? n2.clear = n2.delete = n2.set = () => {
    throw Error("map is read-only");
  } : n2 instanceof Set && (n2.add = n2.clear = n2.delete = () => {
    throw Error("set is read-only");
  }), Object.freeze(n2), Object.getOwnPropertyNames(n2).forEach(((t2) => {
    const a2 = n2[t2], i2 = typeof a2;
    "object" !== i2 && "function" !== i2 || Object.isFrozen(a2) || e(a2);
  })), n2;
}
class n {
  constructor(e2) {
    void 0 === e2.data && (e2.data = {}), this.data = e2.data, this.isMatchIgnored = false;
  }
  ignoreMatch() {
    this.isMatchIgnored = true;
  }
}
function t(e2) {
  return e2.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
}
function a(e2, ...n2) {
  const t2 = /* @__PURE__ */ Object.create(null);
  for (const n3 in e2) t2[n3] = e2[n3];
  return n2.forEach(((e3) => {
    for (const n3 in e3) t2[n3] = e3[n3];
  })), t2;
}
const i = (e2) => !!e2.scope;
class r {
  constructor(e2, n2) {
    this.buffer = "", this.classPrefix = n2.classPrefix, e2.walk(this);
  }
  addText(e2) {
    this.buffer += t(e2);
  }
  openNode(e2) {
    if (!i(e2)) return;
    const n2 = ((e3, { prefix: n3 }) => {
      if (e3.startsWith("language:")) return e3.replace("language:", "language-");
      if (e3.includes(".")) {
        const t2 = e3.split(".");
        return [`${n3}${t2.shift()}`, ...t2.map(((e4, n4) => `${e4}${"_".repeat(n4 + 1)}`))].join(" ");
      }
      return `${n3}${e3}`;
    })(e2.scope, { prefix: this.classPrefix });
    this.span(n2);
  }
  closeNode(e2) {
    i(e2) && (this.buffer += "</span>");
  }
  value() {
    return this.buffer;
  }
  span(e2) {
    this.buffer += `<span class="${e2}">`;
  }
}
const s = (e2 = {}) => {
  const n2 = { children: [] };
  return Object.assign(n2, e2), n2;
};
class o {
  constructor() {
    this.rootNode = s(), this.stack = [this.rootNode];
  }
  get top() {
    return this.stack[this.stack.length - 1];
  }
  get root() {
    return this.rootNode;
  }
  add(e2) {
    this.top.children.push(e2);
  }
  openNode(e2) {
    const n2 = s({ scope: e2 });
    this.add(n2), this.stack.push(n2);
  }
  closeNode() {
    if (this.stack.length > 1) return this.stack.pop();
  }
  closeAllNodes() {
    for (; this.closeNode(); ) ;
  }
  toJSON() {
    return JSON.stringify(this.rootNode, null, 4);
  }
  walk(e2) {
    return this.constructor._walk(e2, this.rootNode);
  }
  static _walk(e2, n2) {
    return "string" == typeof n2 ? e2.addText(n2) : n2.children && (e2.openNode(n2), n2.children.forEach(((n3) => this._walk(e2, n3))), e2.closeNode(n2)), e2;
  }
  static _collapse(e2) {
    "string" != typeof e2 && e2.children && (e2.children.every(((e3) => "string" == typeof e3)) ? e2.children = [e2.children.join("")] : e2.children.forEach(((e3) => {
      o._collapse(e3);
    })));
  }
}
class l extends o {
  constructor(e2) {
    super(), this.options = e2;
  }
  addText(e2) {
    "" !== e2 && this.add(e2);
  }
  startScope(e2) {
    this.openNode(e2);
  }
  endScope() {
    this.closeNode();
  }
  __addSublanguage(e2, n2) {
    const t2 = e2.root;
    n2 && (t2.scope = "language:" + n2), this.add(t2);
  }
  toHTML() {
    return new r(this, this.options).value();
  }
  finalize() {
    return this.closeAllNodes(), true;
  }
}
function c(e2) {
  return e2 ? "string" == typeof e2 ? e2 : e2.source : null;
}
function d(e2) {
  return b("(?=", e2, ")");
}
function g(e2) {
  return b("(?:", e2, ")*");
}
function u3(e2) {
  return b("(?:", e2, ")?");
}
function b(...e2) {
  return e2.map(((e3) => c(e3))).join("");
}
function m(...e2) {
  const n2 = ((e3) => {
    const n3 = e3[e3.length - 1];
    return "object" == typeof n3 && n3.constructor === Object ? (e3.splice(e3.length - 1, 1), n3) : {};
  })(e2);
  return "(" + (n2.capture ? "" : "?:") + e2.map(((e3) => c(e3))).join("|") + ")";
}
function p(e2) {
  return RegExp(e2.toString() + "|").exec("").length - 1;
}
const _ = /\[(?:[^\\\]]|\\.)*\]|\(\??|\\([1-9][0-9]*)|\\./;
function h(e2, { joinWith: n2 }) {
  let t2 = 0;
  return e2.map(((e3) => {
    t2 += 1;
    const n3 = t2;
    let a2 = c(e3), i2 = "";
    for (; a2.length > 0; ) {
      const e4 = _.exec(a2);
      if (!e4) {
        i2 += a2;
        break;
      }
      i2 += a2.substring(0, e4.index), a2 = a2.substring(e4.index + e4[0].length), "\\" === e4[0][0] && e4[1] ? i2 += "\\" + (Number(e4[1]) + n3) : (i2 += e4[0], "(" === e4[0] && t2++);
    }
    return i2;
  })).map(((e3) => `(${e3})`)).join(n2);
}
const f = "[a-zA-Z]\\w*", E = "[a-zA-Z_]\\w*", y2 = "\\b\\d+(\\.\\d+)?", w = "(-?)(\\b0[xX][a-fA-F0-9]+|(\\b\\d+(\\.\\d*)?|\\.\\d+)([eE][-+]?\\d+)?)", v = "\\b(0b[01]+)", N = {
  begin: "\\\\[\\s\\S]",
  relevance: 0
}, k = {
  scope: "string",
  begin: "'",
  end: "'",
  illegal: "\\n",
  contains: [N]
}, x = {
  scope: "string",
  begin: '"',
  end: '"',
  illegal: "\\n",
  contains: [N]
}, O = (e2, n2, t2 = {}) => {
  const i2 = a({
    scope: "comment",
    begin: e2,
    end: n2,
    contains: []
  }, t2);
  i2.contains.push({
    scope: "doctag",
    begin: "[ ]*(?=(TODO|FIXME|NOTE|BUG|OPTIMIZE|HACK|XXX):)",
    end: /(TODO|FIXME|NOTE|BUG|OPTIMIZE|HACK|XXX):/,
    excludeBegin: true,
    relevance: 0
  });
  const r2 = m("I", "a", "is", "so", "us", "to", "at", "if", "in", "it", "on", /[A-Za-z]+['](d|ve|re|ll|t|s|n)/, /[A-Za-z]+[-][a-z]+/, /[A-Za-z][a-z]{2,}/);
  return i2.contains.push({ begin: b(/[ ]+/, "(", r2, /[.]?[:]?([.][ ]|[ ])/, "){3}") }), i2;
}, M = O("//", "$"), A = O("/\\*", "\\*/"), S2 = O("#", "$");
var C = Object.freeze({
  __proto__: null,
  APOS_STRING_MODE: k,
  BACKSLASH_ESCAPE: N,
  BINARY_NUMBER_MODE: {
    scope: "number",
    begin: v,
    relevance: 0
  },
  BINARY_NUMBER_RE: v,
  COMMENT: O,
  C_BLOCK_COMMENT_MODE: A,
  C_LINE_COMMENT_MODE: M,
  C_NUMBER_MODE: {
    scope: "number",
    begin: w,
    relevance: 0
  },
  C_NUMBER_RE: w,
  END_SAME_AS_BEGIN: (e2) => Object.assign(e2, {
    "on:begin": (e3, n2) => {
      n2.data._beginMatch = e3[1];
    },
    "on:end": (e3, n2) => {
      n2.data._beginMatch !== e3[1] && n2.ignoreMatch();
    }
  }),
  HASH_COMMENT_MODE: S2,
  IDENT_RE: f,
  MATCH_NOTHING_RE: /\b\B/,
  METHOD_GUARD: { begin: "\\.\\s*" + E, relevance: 0 },
  NUMBER_MODE: { scope: "number", begin: y2, relevance: 0 },
  NUMBER_RE: y2,
  PHRASAL_WORDS_MODE: {
    begin: /\b(a|an|the|are|I'm|isn't|don't|doesn't|won't|but|just|should|pretty|simply|enough|gonna|going|wtf|so|such|will|you|your|they|like|more)\b/
  },
  QUOTE_STRING_MODE: x,
  REGEXP_MODE: {
    scope: "regexp",
    begin: /\/(?=[^/\n]*\/)/,
    end: /\/[gimuy]*/,
    contains: [N, { begin: /\[/, end: /\]/, relevance: 0, contains: [N] }]
  },
  RE_STARTERS_RE: "!|!=|!==|%|%=|&|&&|&=|\\*|\\*=|\\+|\\+=|,|-|-=|/=|/|:|;|<<|<<=|<=|<|===|==|=|>>>=|>>=|>=|>>>|>>|>|\\?|\\[|\\{|\\(|\\^|\\^=|\\||\\|=|\\|\\||~",
  SHEBANG: (e2 = {}) => {
    const n2 = /^#![ ]*\//;
    return e2.binary && (e2.begin = b(n2, /.*\b/, e2.binary, /\b.*/)), a({
      scope: "meta",
      begin: n2,
      end: /$/,
      relevance: 0,
      "on:begin": (e3, n3) => {
        0 !== e3.index && n3.ignoreMatch();
      }
    }, e2);
  },
  TITLE_MODE: { scope: "title", begin: f, relevance: 0 },
  UNDERSCORE_IDENT_RE: E,
  UNDERSCORE_TITLE_MODE: { scope: "title", begin: E, relevance: 0 }
});
function T(e2, n2) {
  "." === e2.input[e2.index - 1] && n2.ignoreMatch();
}
function R(e2, n2) {
  void 0 !== e2.className && (e2.scope = e2.className, delete e2.className);
}
function D(e2, n2) {
  n2 && e2.beginKeywords && (e2.begin = "\\b(" + e2.beginKeywords.split(" ").join("|") + ")(?!\\.)(?=\\b|\\s)", e2.__beforeBegin = T, e2.keywords = e2.keywords || e2.beginKeywords, delete e2.beginKeywords, void 0 === e2.relevance && (e2.relevance = 0));
}
function I(e2, n2) {
  Array.isArray(e2.illegal) && (e2.illegal = m(...e2.illegal));
}
function L(e2, n2) {
  if (e2.match) {
    if (e2.begin || e2.end) throw Error("begin & end are not supported with match");
    e2.begin = e2.match, delete e2.match;
  }
}
function B2(e2, n2) {
  void 0 === e2.relevance && (e2.relevance = 1);
}
const $2 = (e2, n2) => {
  if (!e2.beforeMatch) return;
  if (e2.starts) throw Error("beforeMatch cannot be used with starts");
  const t2 = Object.assign({}, e2);
  Object.keys(e2).forEach(((n3) => {
    delete e2[n3];
  })), e2.keywords = t2.keywords, e2.begin = b(t2.beforeMatch, d(t2.begin)), e2.starts = {
    relevance: 0,
    contains: [Object.assign(t2, { endsParent: true })]
  }, e2.relevance = 0, delete t2.beforeMatch;
}, F = ["of", "and", "for", "in", "not", "or", "if", "then", "parent", "list", "value"];
function z(e2, n2, t2 = "keyword") {
  const a2 = /* @__PURE__ */ Object.create(null);
  return "string" == typeof e2 ? i2(t2, e2.split(" ")) : Array.isArray(e2) ? i2(t2, e2) : Object.keys(e2).forEach(((t3) => {
    Object.assign(a2, z(e2[t3], n2, t3));
  })), a2;
  function i2(e3, t3) {
    n2 && (t3 = t3.map(((e4) => e4.toLowerCase()))), t3.forEach(((n3) => {
      const t4 = n3.split("|");
      a2[t4[0]] = [e3, j(t4[0], t4[1])];
    }));
  }
}
function j(e2, n2) {
  return n2 ? Number(n2) : ((e3) => F.includes(e3.toLowerCase()))(e2) ? 0 : 1;
}
const U = {}, P2 = (e2) => {
  console.error(e2);
}, K = (e2, ...n2) => {
  console.log("WARN: " + e2, ...n2);
}, q = (e2, n2) => {
  U[`${e2}/${n2}`] || (console.log(`Deprecated as of ${e2}. ${n2}`), U[`${e2}/${n2}`] = true);
}, H = Error();
function G(e2, n2, { key: t2 }) {
  let a2 = 0;
  const i2 = e2[t2], r2 = {}, s2 = {};
  for (let e3 = 1; e3 <= n2.length; e3++) s2[e3 + a2] = i2[e3], r2[e3 + a2] = true, a2 += p(n2[e3 - 1]);
  e2[t2] = s2, e2[t2]._emit = r2, e2[t2]._multi = true;
}
function Z(e2) {
  ((e3) => {
    e3.scope && "object" == typeof e3.scope && null !== e3.scope && (e3.beginScope = e3.scope, delete e3.scope);
  })(e2), "string" == typeof e2.beginScope && (e2.beginScope = {
    _wrap: e2.beginScope
  }), "string" == typeof e2.endScope && (e2.endScope = {
    _wrap: e2.endScope
  }), ((e3) => {
    if (Array.isArray(e3.begin)) {
      if (e3.skip || e3.excludeBegin || e3.returnBegin) throw P2("skip, excludeBegin, returnBegin not compatible with beginScope: {}"), H;
      if ("object" != typeof e3.beginScope || null === e3.beginScope) throw P2("beginScope must be object"), H;
      G(e3, e3.begin, { key: "beginScope" }), e3.begin = h(e3.begin, { joinWith: "" });
    }
  })(e2), ((e3) => {
    if (Array.isArray(e3.end)) {
      if (e3.skip || e3.excludeEnd || e3.returnEnd) throw P2("skip, excludeEnd, returnEnd not compatible with endScope: {}"), H;
      if ("object" != typeof e3.endScope || null === e3.endScope) throw P2("endScope must be object"), H;
      G(e3, e3.end, { key: "endScope" }), e3.end = h(e3.end, { joinWith: "" });
    }
  })(e2);
}
function W(e2) {
  function n2(n3, t3) {
    return RegExp(c(n3), "m" + (e2.case_insensitive ? "i" : "") + (e2.unicodeRegex ? "u" : "") + (t3 ? "g" : ""));
  }
  class t2 {
    constructor() {
      this.matchIndexes = {}, this.regexes = [], this.matchAt = 1, this.position = 0;
    }
    addRule(e3, n3) {
      n3.position = this.position++, this.matchIndexes[this.matchAt] = n3, this.regexes.push([n3, e3]), this.matchAt += p(e3) + 1;
    }
    compile() {
      0 === this.regexes.length && (this.exec = () => null);
      const e3 = this.regexes.map(((e4) => e4[1]));
      this.matcherRe = n2(h(e3, {
        joinWith: "|"
      }), true), this.lastIndex = 0;
    }
    exec(e3) {
      this.matcherRe.lastIndex = this.lastIndex;
      const n3 = this.matcherRe.exec(e3);
      if (!n3) return null;
      const t3 = n3.findIndex(((e4, n4) => n4 > 0 && void 0 !== e4)), a2 = this.matchIndexes[t3];
      return n3.splice(0, t3), Object.assign(n3, a2);
    }
  }
  class i2 {
    constructor() {
      this.rules = [], this.multiRegexes = [], this.count = 0, this.lastIndex = 0, this.regexIndex = 0;
    }
    getMatcher(e3) {
      if (this.multiRegexes[e3]) return this.multiRegexes[e3];
      const n3 = new t2();
      return this.rules.slice(e3).forEach((([e4, t3]) => n3.addRule(e4, t3))), n3.compile(), this.multiRegexes[e3] = n3, n3;
    }
    resumingScanAtSamePosition() {
      return 0 !== this.regexIndex;
    }
    considerAll() {
      this.regexIndex = 0;
    }
    addRule(e3, n3) {
      this.rules.push([e3, n3]), "begin" === n3.type && this.count++;
    }
    exec(e3) {
      const n3 = this.getMatcher(this.regexIndex);
      n3.lastIndex = this.lastIndex;
      let t3 = n3.exec(e3);
      if (this.resumingScanAtSamePosition()) if (t3 && t3.index === this.lastIndex) ;
      else {
        const n4 = this.getMatcher(0);
        n4.lastIndex = this.lastIndex + 1, t3 = n4.exec(e3);
      }
      return t3 && (this.regexIndex += t3.position + 1, this.regexIndex === this.count && this.considerAll()), t3;
    }
  }
  if (e2.compilerExtensions || (e2.compilerExtensions = []), e2.contains && e2.contains.includes("self")) throw Error("ERR: contains `self` is not supported at the top-level of a language.  See documentation.");
  return e2.classNameAliases = a(e2.classNameAliases || {}), (function t3(r2, s2) {
    const o2 = r2;
    if (r2.isCompiled) return o2;
    [R, L, Z, $2].forEach(((e3) => e3(r2, s2))), e2.compilerExtensions.forEach(((e3) => e3(r2, s2))), r2.__beforeBegin = null, [D, I, B2].forEach(((e3) => e3(r2, s2))), r2.isCompiled = true;
    let l2 = null;
    return "object" == typeof r2.keywords && r2.keywords.$pattern && (r2.keywords = Object.assign({}, r2.keywords), l2 = r2.keywords.$pattern, delete r2.keywords.$pattern), l2 = l2 || /\w+/, r2.keywords && (r2.keywords = z(r2.keywords, e2.case_insensitive)), o2.keywordPatternRe = n2(l2, true), s2 && (r2.begin || (r2.begin = /\B|\b/), o2.beginRe = n2(o2.begin), r2.end || r2.endsWithParent || (r2.end = /\B|\b/), r2.end && (o2.endRe = n2(o2.end)), o2.terminatorEnd = c(o2.end) || "", r2.endsWithParent && s2.terminatorEnd && (o2.terminatorEnd += (r2.end ? "|" : "") + s2.terminatorEnd)), r2.illegal && (o2.illegalRe = n2(r2.illegal)), r2.contains || (r2.contains = []), r2.contains = [].concat(...r2.contains.map(((e3) => ((e4) => (e4.variants && !e4.cachedVariants && (e4.cachedVariants = e4.variants.map(((n3) => a(e4, {
      variants: null
    }, n3)))), e4.cachedVariants ? e4.cachedVariants : Q(e4) ? a(e4, {
      starts: e4.starts ? a(e4.starts) : null
    }) : Object.isFrozen(e4) ? a(e4) : e4))("self" === e3 ? r2 : e3)))), r2.contains.forEach(((e3) => {
      t3(e3, o2);
    })), r2.starts && t3(r2.starts, s2), o2.matcher = ((e3) => {
      const n3 = new i2();
      return e3.contains.forEach(((e4) => n3.addRule(e4.begin, {
        rule: e4,
        type: "begin"
      }))), e3.terminatorEnd && n3.addRule(e3.terminatorEnd, {
        type: "end"
      }), e3.illegal && n3.addRule(e3.illegal, { type: "illegal" }), n3;
    })(o2), o2;
  })(e2);
}
function Q(e2) {
  return !!e2 && (e2.endsWithParent || Q(e2.starts));
}
class X extends Error {
  constructor(e2, n2) {
    super(e2), this.name = "HTMLInjectionError", this.html = n2;
  }
}
const V = t, J = a, Y = /* @__PURE__ */ Symbol("nomatch"), ee = (t2) => {
  const a2 = /* @__PURE__ */ Object.create(null), i2 = /* @__PURE__ */ Object.create(null), r2 = [];
  let s2 = true;
  const o2 = "Could not find the language '{}', did you forget to load/include a language module?", c2 = {
    disableAutodetect: true,
    name: "Plain text",
    contains: []
  };
  let p2 = {
    ignoreUnescapedHTML: false,
    throwUnescapedHTML: false,
    noHighlightRe: /^(no-?highlight)$/i,
    languageDetectRe: /\blang(?:uage)?-([\w-]+)\b/i,
    classPrefix: "hljs-",
    cssSelector: "pre code",
    languages: null,
    __emitter: l
  };
  function _2(e2) {
    return p2.noHighlightRe.test(e2);
  }
  function h2(e2, n2, t3) {
    let a3 = "", i3 = "";
    "object" == typeof n2 ? (a3 = e2, t3 = n2.ignoreIllegals, i3 = n2.language) : (q("10.7.0", "highlight(lang, code, ...args) has been deprecated."), q("10.7.0", "Please use highlight(code, options) instead.\nhttps://github.com/highlightjs/highlight.js/issues/2277"), i3 = e2, a3 = n2), void 0 === t3 && (t3 = true);
    const r3 = { code: a3, language: i3 };
    O2("before:highlight", r3);
    const s3 = r3.result ? r3.result : f2(r3.language, r3.code, t3);
    return s3.code = r3.code, O2("after:highlight", s3), s3;
  }
  function f2(e2, t3, i3, r3) {
    const l2 = /* @__PURE__ */ Object.create(null);
    function c3() {
      if (!O3.keywords) return void A2.addText(S3);
      let e3 = 0;
      O3.keywordPatternRe.lastIndex = 0;
      let n2 = O3.keywordPatternRe.exec(S3), t4 = "";
      for (; n2; ) {
        t4 += S3.substring(e3, n2.index);
        const i4 = v3.case_insensitive ? n2[0].toLowerCase() : n2[0], r4 = (a3 = i4, O3.keywords[a3]);
        if (r4) {
          const [e4, a4] = r4;
          if (A2.addText(t4), t4 = "", l2[i4] = (l2[i4] || 0) + 1, l2[i4] <= 7 && (C2 += a4), e4.startsWith("_")) t4 += n2[0];
          else {
            const t5 = v3.classNameAliases[e4] || e4;
            g2(n2[0], t5);
          }
        } else t4 += n2[0];
        e3 = O3.keywordPatternRe.lastIndex, n2 = O3.keywordPatternRe.exec(S3);
      }
      var a3;
      t4 += S3.substring(e3), A2.addText(t4);
    }
    function d2() {
      null != O3.subLanguage ? (() => {
        if ("" === S3) return;
        let e3 = null;
        if ("string" == typeof O3.subLanguage) {
          if (!a2[O3.subLanguage]) return void A2.addText(S3);
          e3 = f2(O3.subLanguage, S3, true, M2[O3.subLanguage]), M2[O3.subLanguage] = e3._top;
        } else e3 = E2(S3, O3.subLanguage.length ? O3.subLanguage : null);
        O3.relevance > 0 && (C2 += e3.relevance), A2.__addSublanguage(e3._emitter, e3.language);
      })() : c3(), S3 = "";
    }
    function g2(e3, n2) {
      "" !== e3 && (A2.startScope(n2), A2.addText(e3), A2.endScope());
    }
    function u4(e3, n2) {
      let t4 = 1;
      const a3 = n2.length - 1;
      for (; t4 <= a3; ) {
        if (!e3._emit[t4]) {
          t4++;
          continue;
        }
        const a4 = v3.classNameAliases[e3[t4]] || e3[t4], i4 = n2[t4];
        a4 ? g2(i4, a4) : (S3 = i4, c3(), S3 = ""), t4++;
      }
    }
    function b2(e3, n2) {
      return e3.scope && "string" == typeof e3.scope && A2.openNode(v3.classNameAliases[e3.scope] || e3.scope), e3.beginScope && (e3.beginScope._wrap ? (g2(S3, v3.classNameAliases[e3.beginScope._wrap] || e3.beginScope._wrap), S3 = "") : e3.beginScope._multi && (u4(e3.beginScope, n2), S3 = "")), O3 = Object.create(e3, { parent: {
        value: O3
      } }), O3;
    }
    function m2(e3, t4, a3) {
      let i4 = ((e4, n2) => {
        const t5 = e4 && e4.exec(n2);
        return t5 && 0 === t5.index;
      })(e3.endRe, a3);
      if (i4) {
        if (e3["on:end"]) {
          const a4 = new n(e3);
          e3["on:end"](t4, a4), a4.isMatchIgnored && (i4 = false);
        }
        if (i4) {
          for (; e3.endsParent && e3.parent; ) e3 = e3.parent;
          return e3;
        }
      }
      if (e3.endsWithParent) return m2(e3.parent, t4, a3);
    }
    function _3(e3) {
      return 0 === O3.matcher.regexIndex ? (S3 += e3[0], 1) : (D2 = true, 0);
    }
    function h3(e3) {
      const n2 = e3[0], a3 = t3.substring(e3.index), i4 = m2(O3, e3, a3);
      if (!i4) return Y;
      const r4 = O3;
      O3.endScope && O3.endScope._wrap ? (d2(), g2(n2, O3.endScope._wrap)) : O3.endScope && O3.endScope._multi ? (d2(), u4(O3.endScope, e3)) : r4.skip ? S3 += n2 : (r4.returnEnd || r4.excludeEnd || (S3 += n2), d2(), r4.excludeEnd && (S3 = n2));
      do {
        O3.scope && A2.closeNode(), O3.skip || O3.subLanguage || (C2 += O3.relevance), O3 = O3.parent;
      } while (O3 !== i4.parent);
      return i4.starts && b2(i4.starts, e3), r4.returnEnd ? 0 : n2.length;
    }
    let y4 = {};
    function w3(a3, r4) {
      const o3 = r4 && r4[0];
      if (S3 += a3, null == o3) return d2(), 0;
      if ("begin" === y4.type && "end" === r4.type && y4.index === r4.index && "" === o3) {
        if (S3 += t3.slice(r4.index, r4.index + 1), !s2) {
          const n2 = Error(`0 width match regex (${e2})`);
          throw n2.languageName = e2, n2.badRule = y4.rule, n2;
        }
        return 1;
      }
      if (y4 = r4, "begin" === r4.type) return ((e3) => {
        const t4 = e3[0], a4 = e3.rule, i4 = new n(a4), r5 = [a4.__beforeBegin, a4["on:begin"]];
        for (const n2 of r5) if (n2 && (n2(e3, i4), i4.isMatchIgnored)) return _3(t4);
        return a4.skip ? S3 += t4 : (a4.excludeBegin && (S3 += t4), d2(), a4.returnBegin || a4.excludeBegin || (S3 = t4)), b2(a4, e3), a4.returnBegin ? 0 : t4.length;
      })(r4);
      if ("illegal" === r4.type && !i3) {
        const e3 = Error('Illegal lexeme "' + o3 + '" for mode "' + (O3.scope || "<unnamed>") + '"');
        throw e3.mode = O3, e3;
      }
      if ("end" === r4.type) {
        const e3 = h3(r4);
        if (e3 !== Y) return e3;
      }
      if ("illegal" === r4.type && "" === o3) return S3 += "\n", 1;
      if (R2 > 1e5 && R2 > 3 * r4.index) throw Error("potential infinite loop, way more iterations than matches");
      return S3 += o3, o3.length;
    }
    const v3 = N2(e2);
    if (!v3) throw P2(o2.replace("{}", e2)), Error('Unknown language: "' + e2 + '"');
    const k3 = W(v3);
    let x3 = "", O3 = r3 || k3;
    const M2 = {}, A2 = new p2.__emitter(p2);
    (() => {
      const e3 = [];
      for (let n2 = O3; n2 !== v3; n2 = n2.parent) n2.scope && e3.unshift(n2.scope);
      e3.forEach(((e4) => A2.openNode(e4)));
    })();
    let S3 = "", C2 = 0, T2 = 0, R2 = 0, D2 = false;
    try {
      if (v3.__emitTokens) v3.__emitTokens(t3, A2);
      else {
        for (O3.matcher.considerAll(); ; ) {
          R2++, D2 ? D2 = false : O3.matcher.considerAll(), O3.matcher.lastIndex = T2;
          const e3 = O3.matcher.exec(t3);
          if (!e3) break;
          const n2 = w3(t3.substring(T2, e3.index), e3);
          T2 = e3.index + n2;
        }
        w3(t3.substring(T2));
      }
      return A2.finalize(), x3 = A2.toHTML(), {
        language: e2,
        value: x3,
        relevance: C2,
        illegal: false,
        _emitter: A2,
        _top: O3
      };
    } catch (n2) {
      if (n2.message && n2.message.includes("Illegal")) return {
        language: e2,
        value: V(t3),
        illegal: true,
        relevance: 0,
        _illegalBy: {
          message: n2.message,
          index: T2,
          context: t3.slice(T2 - 100, T2 + 100),
          mode: n2.mode,
          resultSoFar: x3
        },
        _emitter: A2
      };
      if (s2) return {
        language: e2,
        value: V(t3),
        illegal: false,
        relevance: 0,
        errorRaised: n2,
        _emitter: A2,
        _top: O3
      };
      throw n2;
    }
  }
  function E2(e2, n2) {
    n2 = n2 || p2.languages || Object.keys(a2);
    const t3 = ((e3) => {
      const n3 = { value: V(e3), illegal: false, relevance: 0, _top: c2, _emitter: new p2.__emitter(p2) };
      return n3._emitter.addText(e3), n3;
    })(e2), i3 = n2.filter(N2).filter(x2).map(((n3) => f2(n3, e2, false)));
    i3.unshift(t3);
    const r3 = i3.sort(((e3, n3) => {
      if (e3.relevance !== n3.relevance) return n3.relevance - e3.relevance;
      if (e3.language && n3.language) {
        if (N2(e3.language).supersetOf === n3.language) return 1;
        if (N2(n3.language).supersetOf === e3.language) return -1;
      }
      return 0;
    })), [s3, o3] = r3, l2 = s3;
    return l2.secondBest = o3, l2;
  }
  function y3(e2) {
    let n2 = null;
    const t3 = ((e3) => {
      let n3 = e3.className + " ";
      n3 += e3.parentNode ? e3.parentNode.className : "";
      const t4 = p2.languageDetectRe.exec(n3);
      if (t4) {
        const n4 = N2(t4[1]);
        return n4 || (K(o2.replace("{}", t4[1])), K("Falling back to no-highlight mode for this block.", e3)), n4 ? t4[1] : "no-highlight";
      }
      return n3.split(/\s+/).find(((e4) => _2(e4) || N2(e4)));
    })(e2);
    if (_2(t3)) return;
    if (O2("before:highlightElement", {
      el: e2,
      language: t3
    }), e2.dataset.highlighted) return void console.log("Element previously highlighted. To highlight again, first unset `dataset.highlighted`.", e2);
    if (e2.children.length > 0 && (p2.ignoreUnescapedHTML || (console.warn("One of your code blocks includes unescaped HTML. This is a potentially serious security risk."), console.warn("https://github.com/highlightjs/highlight.js/wiki/security"), console.warn("The element with unescaped HTML:"), console.warn(e2)), p2.throwUnescapedHTML)) throw new X("One of your code blocks includes unescaped HTML.", e2.innerHTML);
    n2 = e2;
    const a3 = n2.textContent, r3 = t3 ? h2(a3, { language: t3, ignoreIllegals: true }) : E2(a3);
    e2.innerHTML = r3.value, e2.dataset.highlighted = "yes", ((e3, n3, t4) => {
      const a4 = n3 && i2[n3] || t4;
      e3.classList.add("hljs"), e3.classList.add("language-" + a4);
    })(e2, t3, r3.language), e2.result = {
      language: r3.language,
      re: r3.relevance,
      relevance: r3.relevance
    }, r3.secondBest && (e2.secondBest = {
      language: r3.secondBest.language,
      relevance: r3.secondBest.relevance
    }), O2("after:highlightElement", { el: e2, result: r3, text: a3 });
  }
  let w2 = false;
  function v2() {
    if ("loading" === document.readyState) return w2 || window.addEventListener("DOMContentLoaded", (() => {
      v2();
    }), false), void (w2 = true);
    document.querySelectorAll(p2.cssSelector).forEach(y3);
  }
  function N2(e2) {
    return e2 = (e2 || "").toLowerCase(), a2[e2] || a2[i2[e2]];
  }
  function k2(e2, { languageName: n2 }) {
    "string" == typeof e2 && (e2 = [e2]), e2.forEach(((e3) => {
      i2[e3.toLowerCase()] = n2;
    }));
  }
  function x2(e2) {
    const n2 = N2(e2);
    return n2 && !n2.disableAutodetect;
  }
  function O2(e2, n2) {
    const t3 = e2;
    r2.forEach(((e3) => {
      e3[t3] && e3[t3](n2);
    }));
  }
  Object.assign(t2, {
    highlight: h2,
    highlightAuto: E2,
    highlightAll: v2,
    highlightElement: y3,
    highlightBlock: (e2) => (q("10.7.0", "highlightBlock will be removed entirely in v12.0"), q("10.7.0", "Please use highlightElement now."), y3(e2)),
    configure: (e2) => {
      p2 = J(p2, e2);
    },
    initHighlighting: () => {
      v2(), q("10.6.0", "initHighlighting() deprecated.  Use highlightAll() now.");
    },
    initHighlightingOnLoad: () => {
      v2(), q("10.6.0", "initHighlightingOnLoad() deprecated.  Use highlightAll() now.");
    },
    registerLanguage: (e2, n2) => {
      let i3 = null;
      try {
        i3 = n2(t2);
      } catch (n3) {
        if (P2("Language definition for '{}' could not be registered.".replace("{}", e2)), !s2) throw n3;
        P2(n3), i3 = c2;
      }
      i3.name || (i3.name = e2), a2[e2] = i3, i3.rawDefinition = n2.bind(null, t2), i3.aliases && k2(i3.aliases, {
        languageName: e2
      });
    },
    unregisterLanguage: (e2) => {
      delete a2[e2];
      for (const n2 of Object.keys(i2)) i2[n2] === e2 && delete i2[n2];
    },
    listLanguages: () => Object.keys(a2),
    getLanguage: N2,
    registerAliases: k2,
    autoDetection: x2,
    inherit: J,
    addPlugin: (e2) => {
      ((e3) => {
        e3["before:highlightBlock"] && !e3["before:highlightElement"] && (e3["before:highlightElement"] = (n2) => {
          e3["before:highlightBlock"](Object.assign({ block: n2.el }, n2));
        }), e3["after:highlightBlock"] && !e3["after:highlightElement"] && (e3["after:highlightElement"] = (n2) => {
          e3["after:highlightBlock"](Object.assign({ block: n2.el }, n2));
        });
      })(e2), r2.push(e2);
    },
    removePlugin: (e2) => {
      const n2 = r2.indexOf(e2);
      -1 !== n2 && r2.splice(n2, 1);
    }
  }), t2.debugMode = () => {
    s2 = false;
  }, t2.safeMode = () => {
    s2 = true;
  }, t2.versionString = "11.11.1", t2.regex = {
    concat: b,
    lookahead: d,
    either: m,
    optional: u3,
    anyNumberOfTimes: g
  };
  for (const n2 in C) "object" == typeof C[n2] && e(C[n2]);
  return Object.assign(t2, C), t2;
}, ne = ee({});
ne.newInstance = () => ee({});
const te = (e2) => ({
  IMPORTANT: {
    scope: "meta",
    begin: "!important"
  },
  BLOCK_COMMENT: e2.C_BLOCK_COMMENT_MODE,
  HEXCOLOR: {
    scope: "number",
    begin: /#(([0-9a-fA-F]{3,4})|(([0-9a-fA-F]{2}){3,4}))\b/
  },
  FUNCTION_DISPATCH: { className: "built_in", begin: /[\w-]+(?=\()/ },
  ATTRIBUTE_SELECTOR_MODE: {
    scope: "selector-attr",
    begin: /\[/,
    end: /\]/,
    illegal: "$",
    contains: [e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE]
  },
  CSS_NUMBER_MODE: {
    scope: "number",
    begin: e2.NUMBER_RE + "(%|em|ex|ch|rem|vw|vh|vmin|vmax|cm|mm|in|pt|pc|px|deg|grad|rad|turn|s|ms|Hz|kHz|dpi|dpcm|dppx)?",
    relevance: 0
  },
  CSS_VARIABLE: { className: "attr", begin: /--[A-Za-z_][A-Za-z0-9_-]*/ }
}), ae = ["a", "abbr", "address", "article", "aside", "audio", "b", "blockquote", "body", "button", "canvas", "caption", "cite", "code", "dd", "del", "details", "dfn", "div", "dl", "dt", "em", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "html", "i", "iframe", "img", "input", "ins", "kbd", "label", "legend", "li", "main", "mark", "menu", "nav", "object", "ol", "optgroup", "option", "p", "picture", "q", "quote", "samp", "section", "select", "source", "span", "strong", "summary", "sup", "table", "tbody", "td", "textarea", "tfoot", "th", "thead", "time", "tr", "ul", "var", "video", "defs", "g", "marker", "mask", "pattern", "svg", "switch", "symbol", "feBlend", "feColorMatrix", "feComponentTransfer", "feComposite", "feConvolveMatrix", "feDiffuseLighting", "feDisplacementMap", "feFlood", "feGaussianBlur", "feImage", "feMerge", "feMorphology", "feOffset", "feSpecularLighting", "feTile", "feTurbulence", "linearGradient", "radialGradient", "stop", "circle", "ellipse", "image", "line", "path", "polygon", "polyline", "rect", "text", "use", "textPath", "tspan", "foreignObject", "clipPath"], ie = ["any-hover", "any-pointer", "aspect-ratio", "color", "color-gamut", "color-index", "device-aspect-ratio", "device-height", "device-width", "display-mode", "forced-colors", "grid", "height", "hover", "inverted-colors", "monochrome", "orientation", "overflow-block", "overflow-inline", "pointer", "prefers-color-scheme", "prefers-contrast", "prefers-reduced-motion", "prefers-reduced-transparency", "resolution", "scan", "scripting", "update", "width", "min-width", "max-width", "min-height", "max-height"].sort().reverse(), re = ["active", "any-link", "blank", "checked", "current", "default", "defined", "dir", "disabled", "drop", "empty", "enabled", "first", "first-child", "first-of-type", "fullscreen", "future", "focus", "focus-visible", "focus-within", "has", "host", "host-context", "hover", "indeterminate", "in-range", "invalid", "is", "lang", "last-child", "last-of-type", "left", "link", "local-link", "not", "nth-child", "nth-col", "nth-last-child", "nth-last-col", "nth-last-of-type", "nth-of-type", "only-child", "only-of-type", "optional", "out-of-range", "past", "placeholder-shown", "read-only", "read-write", "required", "right", "root", "scope", "target", "target-within", "user-invalid", "valid", "visited", "where"].sort().reverse(), se = ["after", "backdrop", "before", "cue", "cue-region", "first-letter", "first-line", "grammar-error", "marker", "part", "placeholder", "selection", "slotted", "spelling-error"].sort().reverse(), oe = ["accent-color", "align-content", "align-items", "align-self", "alignment-baseline", "all", "anchor-name", "animation", "animation-composition", "animation-delay", "animation-direction", "animation-duration", "animation-fill-mode", "animation-iteration-count", "animation-name", "animation-play-state", "animation-range", "animation-range-end", "animation-range-start", "animation-timeline", "animation-timing-function", "appearance", "aspect-ratio", "backdrop-filter", "backface-visibility", "background", "background-attachment", "background-blend-mode", "background-clip", "background-color", "background-image", "background-origin", "background-position", "background-position-x", "background-position-y", "background-repeat", "background-size", "baseline-shift", "block-size", "border", "border-block", "border-block-color", "border-block-end", "border-block-end-color", "border-block-end-style", "border-block-end-width", "border-block-start", "border-block-start-color", "border-block-start-style", "border-block-start-width", "border-block-style", "border-block-width", "border-bottom", "border-bottom-color", "border-bottom-left-radius", "border-bottom-right-radius", "border-bottom-style", "border-bottom-width", "border-collapse", "border-color", "border-end-end-radius", "border-end-start-radius", "border-image", "border-image-outset", "border-image-repeat", "border-image-slice", "border-image-source", "border-image-width", "border-inline", "border-inline-color", "border-inline-end", "border-inline-end-color", "border-inline-end-style", "border-inline-end-width", "border-inline-start", "border-inline-start-color", "border-inline-start-style", "border-inline-start-width", "border-inline-style", "border-inline-width", "border-left", "border-left-color", "border-left-style", "border-left-width", "border-radius", "border-right", "border-right-color", "border-right-style", "border-right-width", "border-spacing", "border-start-end-radius", "border-start-start-radius", "border-style", "border-top", "border-top-color", "border-top-left-radius", "border-top-right-radius", "border-top-style", "border-top-width", "border-width", "bottom", "box-align", "box-decoration-break", "box-direction", "box-flex", "box-flex-group", "box-lines", "box-ordinal-group", "box-orient", "box-pack", "box-shadow", "box-sizing", "break-after", "break-before", "break-inside", "caption-side", "caret-color", "clear", "clip", "clip-path", "clip-rule", "color", "color-interpolation", "color-interpolation-filters", "color-profile", "color-rendering", "color-scheme", "column-count", "column-fill", "column-gap", "column-rule", "column-rule-color", "column-rule-style", "column-rule-width", "column-span", "column-width", "columns", "contain", "contain-intrinsic-block-size", "contain-intrinsic-height", "contain-intrinsic-inline-size", "contain-intrinsic-size", "contain-intrinsic-width", "container", "container-name", "container-type", "content", "content-visibility", "counter-increment", "counter-reset", "counter-set", "cue", "cue-after", "cue-before", "cursor", "cx", "cy", "direction", "display", "dominant-baseline", "empty-cells", "enable-background", "field-sizing", "fill", "fill-opacity", "fill-rule", "filter", "flex", "flex-basis", "flex-direction", "flex-flow", "flex-grow", "flex-shrink", "flex-wrap", "float", "flood-color", "flood-opacity", "flow", "font", "font-display", "font-family", "font-feature-settings", "font-kerning", "font-language-override", "font-optical-sizing", "font-palette", "font-size", "font-size-adjust", "font-smooth", "font-smoothing", "font-stretch", "font-style", "font-synthesis", "font-synthesis-position", "font-synthesis-small-caps", "font-synthesis-style", "font-synthesis-weight", "font-variant", "font-variant-alternates", "font-variant-caps", "font-variant-east-asian", "font-variant-emoji", "font-variant-ligatures", "font-variant-numeric", "font-variant-position", "font-variation-settings", "font-weight", "forced-color-adjust", "gap", "glyph-orientation-horizontal", "glyph-orientation-vertical", "grid", "grid-area", "grid-auto-columns", "grid-auto-flow", "grid-auto-rows", "grid-column", "grid-column-end", "grid-column-start", "grid-gap", "grid-row", "grid-row-end", "grid-row-start", "grid-template", "grid-template-areas", "grid-template-columns", "grid-template-rows", "hanging-punctuation", "height", "hyphenate-character", "hyphenate-limit-chars", "hyphens", "icon", "image-orientation", "image-rendering", "image-resolution", "ime-mode", "initial-letter", "initial-letter-align", "inline-size", "inset", "inset-area", "inset-block", "inset-block-end", "inset-block-start", "inset-inline", "inset-inline-end", "inset-inline-start", "isolation", "justify-content", "justify-items", "justify-self", "kerning", "left", "letter-spacing", "lighting-color", "line-break", "line-height", "line-height-step", "list-style", "list-style-image", "list-style-position", "list-style-type", "margin", "margin-block", "margin-block-end", "margin-block-start", "margin-bottom", "margin-inline", "margin-inline-end", "margin-inline-start", "margin-left", "margin-right", "margin-top", "margin-trim", "marker", "marker-end", "marker-mid", "marker-start", "marks", "mask", "mask-border", "mask-border-mode", "mask-border-outset", "mask-border-repeat", "mask-border-slice", "mask-border-source", "mask-border-width", "mask-clip", "mask-composite", "mask-image", "mask-mode", "mask-origin", "mask-position", "mask-repeat", "mask-size", "mask-type", "masonry-auto-flow", "math-depth", "math-shift", "math-style", "max-block-size", "max-height", "max-inline-size", "max-width", "min-block-size", "min-height", "min-inline-size", "min-width", "mix-blend-mode", "nav-down", "nav-index", "nav-left", "nav-right", "nav-up", "none", "normal", "object-fit", "object-position", "offset", "offset-anchor", "offset-distance", "offset-path", "offset-position", "offset-rotate", "opacity", "order", "orphans", "outline", "outline-color", "outline-offset", "outline-style", "outline-width", "overflow", "overflow-anchor", "overflow-block", "overflow-clip-margin", "overflow-inline", "overflow-wrap", "overflow-x", "overflow-y", "overlay", "overscroll-behavior", "overscroll-behavior-block", "overscroll-behavior-inline", "overscroll-behavior-x", "overscroll-behavior-y", "padding", "padding-block", "padding-block-end", "padding-block-start", "padding-bottom", "padding-inline", "padding-inline-end", "padding-inline-start", "padding-left", "padding-right", "padding-top", "page", "page-break-after", "page-break-before", "page-break-inside", "paint-order", "pause", "pause-after", "pause-before", "perspective", "perspective-origin", "place-content", "place-items", "place-self", "pointer-events", "position", "position-anchor", "position-visibility", "print-color-adjust", "quotes", "r", "resize", "rest", "rest-after", "rest-before", "right", "rotate", "row-gap", "ruby-align", "ruby-position", "scale", "scroll-behavior", "scroll-margin", "scroll-margin-block", "scroll-margin-block-end", "scroll-margin-block-start", "scroll-margin-bottom", "scroll-margin-inline", "scroll-margin-inline-end", "scroll-margin-inline-start", "scroll-margin-left", "scroll-margin-right", "scroll-margin-top", "scroll-padding", "scroll-padding-block", "scroll-padding-block-end", "scroll-padding-block-start", "scroll-padding-bottom", "scroll-padding-inline", "scroll-padding-inline-end", "scroll-padding-inline-start", "scroll-padding-left", "scroll-padding-right", "scroll-padding-top", "scroll-snap-align", "scroll-snap-stop", "scroll-snap-type", "scroll-timeline", "scroll-timeline-axis", "scroll-timeline-name", "scrollbar-color", "scrollbar-gutter", "scrollbar-width", "shape-image-threshold", "shape-margin", "shape-outside", "shape-rendering", "speak", "speak-as", "src", "stop-color", "stop-opacity", "stroke", "stroke-dasharray", "stroke-dashoffset", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "stroke-opacity", "stroke-width", "tab-size", "table-layout", "text-align", "text-align-all", "text-align-last", "text-anchor", "text-combine-upright", "text-decoration", "text-decoration-color", "text-decoration-line", "text-decoration-skip", "text-decoration-skip-ink", "text-decoration-style", "text-decoration-thickness", "text-emphasis", "text-emphasis-color", "text-emphasis-position", "text-emphasis-style", "text-indent", "text-justify", "text-orientation", "text-overflow", "text-rendering", "text-shadow", "text-size-adjust", "text-transform", "text-underline-offset", "text-underline-position", "text-wrap", "text-wrap-mode", "text-wrap-style", "timeline-scope", "top", "touch-action", "transform", "transform-box", "transform-origin", "transform-style", "transition", "transition-behavior", "transition-delay", "transition-duration", "transition-property", "transition-timing-function", "translate", "unicode-bidi", "user-modify", "user-select", "vector-effect", "vertical-align", "view-timeline", "view-timeline-axis", "view-timeline-inset", "view-timeline-name", "view-transition-name", "visibility", "voice-balance", "voice-duration", "voice-family", "voice-pitch", "voice-range", "voice-rate", "voice-stress", "voice-volume", "white-space", "white-space-collapse", "widows", "width", "will-change", "word-break", "word-spacing", "word-wrap", "writing-mode", "x", "y", "z-index", "zoom"].sort().reverse(), le = re.concat(se).sort().reverse();
var ce = "[0-9](_*[0-9])*", de = `\\.(${ce})`, ge = "[0-9a-fA-F](_*[0-9a-fA-F])*", ue = {
  className: "number",
  variants: [{
    begin: `(\\b(${ce})((${de})|\\.)?|(${de}))[eE][+-]?(${ce})[fFdD]?\\b`
  }, {
    begin: `\\b(${ce})((${de})[fFdD]?\\b|\\.([fFdD]\\b)?)`
  }, {
    begin: `(${de})[fFdD]?\\b`
  }, { begin: `\\b(${ce})[fFdD]\\b` }, {
    begin: `\\b0[xX]((${ge})\\.?|(${ge})?\\.(${ge}))[pP][+-]?(${ce})[fFdD]?\\b`
  }, {
    begin: "\\b(0|[1-9](_*[0-9])*)[lL]?\\b"
  }, { begin: `\\b0[xX](${ge})[lL]?\\b` }, {
    begin: "\\b0(_*[0-7])*[lL]?\\b"
  }, { begin: "\\b0[bB][01](_*[01])*[lL]?\\b" }],
  relevance: 0
};
function be(e2, n2, t2) {
  return -1 === t2 ? "" : e2.replace(n2, ((a2) => be(e2, n2, t2 - 1)));
}
const me = "[A-Za-z$_][0-9A-Za-z$_]*", pe = ["as", "in", "of", "if", "for", "while", "finally", "var", "new", "function", "do", "return", "void", "else", "break", "catch", "instanceof", "with", "throw", "case", "default", "try", "switch", "continue", "typeof", "delete", "let", "yield", "const", "class", "debugger", "async", "await", "static", "import", "from", "export", "extends", "using"], _e = ["true", "false", "null", "undefined", "NaN", "Infinity"], he = ["Object", "Function", "Boolean", "Symbol", "Math", "Date", "Number", "BigInt", "String", "RegExp", "Array", "Float32Array", "Float64Array", "Int8Array", "Uint8Array", "Uint8ClampedArray", "Int16Array", "Int32Array", "Uint16Array", "Uint32Array", "BigInt64Array", "BigUint64Array", "Set", "Map", "WeakSet", "WeakMap", "ArrayBuffer", "SharedArrayBuffer", "Atomics", "DataView", "JSON", "Promise", "Generator", "GeneratorFunction", "AsyncFunction", "Reflect", "Proxy", "Intl", "WebAssembly"], fe = ["Error", "EvalError", "InternalError", "RangeError", "ReferenceError", "SyntaxError", "TypeError", "URIError"], Ee = ["setInterval", "setTimeout", "clearInterval", "clearTimeout", "require", "exports", "eval", "isFinite", "isNaN", "parseFloat", "parseInt", "decodeURI", "decodeURIComponent", "encodeURI", "encodeURIComponent", "escape", "unescape"], ye = ["arguments", "this", "super", "console", "window", "document", "localStorage", "sessionStorage", "module", "global"], we = [].concat(Ee, he, fe);
function ve(e2) {
  const n2 = e2.regex, t2 = me, a2 = {
    begin: /<[A-Za-z0-9\\._:-]+/,
    end: /\/[A-Za-z0-9\\._:-]+>|\/>/,
    isTrulyOpeningTag: (e3, n3) => {
      const t3 = e3[0].length + e3.index, a3 = e3.input[t3];
      if ("<" === a3 || "," === a3) return void n3.ignoreMatch();
      let i3;
      ">" === a3 && (((e4, { after: n4 }) => {
        const t4 = "</" + e4[0].slice(1);
        return -1 !== e4.input.indexOf(t4, n4);
      })(e3, { after: t3 }) || n3.ignoreMatch());
      const r3 = e3.input.substring(t3);
      ((i3 = r3.match(/^\s*=/)) || (i3 = r3.match(/^\s+extends\s+/)) && 0 === i3.index) && n3.ignoreMatch();
    }
  }, i2 = {
    $pattern: me,
    keyword: pe,
    literal: _e,
    built_in: we,
    "variable.language": ye
  }, r2 = "[0-9](_?[0-9])*", s2 = `\\.(${r2})`, o2 = "0|[1-9](_?[0-9])*|0[0-7]*[89][0-9]*", l2 = {
    className: "number",
    variants: [{
      begin: `(\\b(${o2})((${s2})|\\.)?|(${s2}))[eE][+-]?(${r2})\\b`
    }, {
      begin: `\\b(${o2})\\b((${s2})\\b|\\.)?|(${s2})\\b`
    }, {
      begin: "\\b(0|[1-9](_?[0-9])*)n\\b"
    }, {
      begin: "\\b0[xX][0-9a-fA-F](_?[0-9a-fA-F])*n?\\b"
    }, {
      begin: "\\b0[bB][0-1](_?[0-1])*n?\\b"
    }, { begin: "\\b0[oO][0-7](_?[0-7])*n?\\b" }, {
      begin: "\\b0[0-7]+n?\\b"
    }],
    relevance: 0
  }, c2 = {
    className: "subst",
    begin: "\\$\\{",
    end: "\\}",
    keywords: i2,
    contains: []
  }, d2 = { begin: ".?html`", end: "", starts: {
    end: "`",
    returnEnd: false,
    contains: [e2.BACKSLASH_ESCAPE, c2],
    subLanguage: "xml"
  } }, g2 = {
    begin: ".?css`",
    end: "",
    starts: {
      end: "`",
      returnEnd: false,
      contains: [e2.BACKSLASH_ESCAPE, c2],
      subLanguage: "css"
    }
  }, u4 = {
    begin: ".?gql`",
    end: "",
    starts: {
      end: "`",
      returnEnd: false,
      contains: [e2.BACKSLASH_ESCAPE, c2],
      subLanguage: "graphql"
    }
  }, b2 = {
    className: "string",
    begin: "`",
    end: "`",
    contains: [e2.BACKSLASH_ESCAPE, c2]
  }, m2 = {
    className: "comment",
    variants: [e2.COMMENT(/\/\*\*(?!\/)/, "\\*/", {
      relevance: 0,
      contains: [{
        begin: "(?=@[A-Za-z]+)",
        relevance: 0,
        contains: [{
          className: "doctag",
          begin: "@[A-Za-z]+"
        }, {
          className: "type",
          begin: "\\{",
          end: "\\}",
          excludeEnd: true,
          excludeBegin: true,
          relevance: 0
        }, {
          className: "variable",
          begin: t2 + "(?=\\s*(-)|$)",
          endsParent: true,
          relevance: 0
        }, { begin: /(?=[^\n])\s/, relevance: 0 }]
      }]
    }), e2.C_BLOCK_COMMENT_MODE, e2.C_LINE_COMMENT_MODE]
  }, p2 = [e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE, d2, g2, u4, b2, { match: /\$\d+/ }, l2];
  c2.contains = p2.concat({
    begin: /\{/,
    end: /\}/,
    keywords: i2,
    contains: ["self"].concat(p2)
  });
  const _2 = [].concat(m2, c2.contains), h2 = _2.concat([{
    begin: /(\s*)\(/,
    end: /\)/,
    keywords: i2,
    contains: ["self"].concat(_2)
  }]), f2 = {
    className: "params",
    begin: /(\s*)\(/,
    end: /\)/,
    excludeBegin: true,
    excludeEnd: true,
    keywords: i2,
    contains: h2
  }, E2 = { variants: [{
    match: [/class/, /\s+/, t2, /\s+/, /extends/, /\s+/, n2.concat(t2, "(", n2.concat(/\./, t2), ")*")],
    scope: { 1: "keyword", 3: "title.class", 5: "keyword", 7: "title.class.inherited" }
  }, {
    match: [/class/, /\s+/, t2],
    scope: { 1: "keyword", 3: "title.class" }
  }] }, y3 = {
    relevance: 0,
    match: n2.either(/\bJSON/, /\b[A-Z][a-z]+([A-Z][a-z]*|\d)*/, /\b[A-Z]{2,}([A-Z][a-z]+|\d)+([A-Z][a-z]*)*/, /\b[A-Z]{2,}[a-z]+([A-Z][a-z]+|\d)*([A-Z][a-z]*)*/),
    className: "title.class",
    keywords: { _: [...he, ...fe] }
  }, w2 = {
    variants: [{
      match: [/function/, /\s+/, t2, /(?=\s*\()/]
    }, { match: [/function/, /\s*(?=\()/] }],
    className: { 1: "keyword", 3: "title.function" },
    label: "func.def",
    contains: [f2],
    illegal: /%/
  }, v2 = {
    match: n2.concat(/\b/, (N2 = [...Ee, "super", "import"].map(((e3) => e3 + "\\s*\\(")), n2.concat("(?!", N2.join("|"), ")")), t2, n2.lookahead(/\s*\(/)),
    className: "title.function",
    relevance: 0
  };
  var N2;
  const k2 = {
    begin: n2.concat(/\./, n2.lookahead(n2.concat(t2, /(?![0-9A-Za-z$_(])/))),
    end: t2,
    excludeBegin: true,
    keywords: "prototype",
    className: "property",
    relevance: 0
  }, x2 = {
    match: [/get|set/, /\s+/, t2, /(?=\()/],
    className: { 1: "keyword", 3: "title.function" },
    contains: [{ begin: /\(\)/ }, f2]
  }, O2 = "(\\([^()]*(\\([^()]*(\\([^()]*\\)[^()]*)*\\)[^()]*)*\\)|" + e2.UNDERSCORE_IDENT_RE + ")\\s*=>", M2 = {
    match: [/const|var|let/, /\s+/, t2, /\s*/, /=\s*/, /(async\s*)?/, n2.lookahead(O2)],
    keywords: "async",
    className: { 1: "keyword", 3: "title.function" },
    contains: [f2]
  };
  return {
    name: "JavaScript",
    aliases: ["js", "jsx", "mjs", "cjs"],
    keywords: i2,
    exports: {
      PARAMS_CONTAINS: h2,
      CLASS_REFERENCE: y3
    },
    illegal: /#(?![$_A-z])/,
    contains: [e2.SHEBANG({ label: "shebang", binary: "node", relevance: 5 }), {
      label: "use_strict",
      className: "meta",
      relevance: 10,
      begin: /^\s*['"]use (strict|asm)['"]/
    }, e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE, d2, g2, u4, b2, m2, { match: /\$\d+/ }, l2, y3, {
      scope: "attr",
      match: t2 + n2.lookahead(":"),
      relevance: 0
    }, M2, {
      begin: "(" + e2.RE_STARTERS_RE + "|\\b(case|return|throw)\\b)\\s*",
      keywords: "return throw case",
      relevance: 0,
      contains: [m2, e2.REGEXP_MODE, {
        className: "function",
        begin: O2,
        returnBegin: true,
        end: "\\s*=>",
        contains: [{
          className: "params",
          variants: [{ begin: e2.UNDERSCORE_IDENT_RE, relevance: 0 }, {
            className: null,
            begin: /\(\s*\)/,
            skip: true
          }, {
            begin: /(\s*)\(/,
            end: /\)/,
            excludeBegin: true,
            excludeEnd: true,
            keywords: i2,
            contains: h2
          }]
        }]
      }, {
        begin: /,/,
        relevance: 0
      }, { match: /\s+/, relevance: 0 }, { variants: [{ begin: "<>", end: "</>" }, {
        match: /<[A-Za-z0-9\\._:-]+\s*\/>/
      }, {
        begin: a2.begin,
        "on:begin": a2.isTrulyOpeningTag,
        end: a2.end
      }], subLanguage: "xml", contains: [{
        begin: a2.begin,
        end: a2.end,
        skip: true,
        contains: ["self"]
      }] }]
    }, w2, {
      beginKeywords: "while if switch catch for"
    }, {
      begin: "\\b(?!function)" + e2.UNDERSCORE_IDENT_RE + "\\([^()]*(\\([^()]*(\\([^()]*\\)[^()]*)*\\)[^()]*)*\\)\\s*\\{",
      returnBegin: true,
      label: "func.def",
      contains: [f2, e2.inherit(e2.TITLE_MODE, {
        begin: t2,
        className: "title.function"
      })]
    }, { match: /\.\.\./, relevance: 0 }, k2, {
      match: "\\$" + t2,
      relevance: 0
    }, {
      match: [/\bconstructor(?=\s*\()/],
      className: { 1: "title.function" },
      contains: [f2]
    }, v2, {
      relevance: 0,
      match: /\b[A-Z][A-Z_0-9]+\b/,
      className: "variable.constant"
    }, E2, x2, { match: /\$[(.]/ }]
  };
}
const Ne = (e2) => b(/\b/, e2, /\w$/.test(e2) ? /\b/ : /\B/), ke = ["Protocol", "Type"].map(Ne), xe = ["init", "self"].map(Ne), Oe = ["Any", "Self"], Me = ["actor", "any", "associatedtype", "async", "await", /as\?/, /as!/, "as", "borrowing", "break", "case", "catch", "class", "consume", "consuming", "continue", "convenience", "copy", "default", "defer", "deinit", "didSet", "distributed", "do", "dynamic", "each", "else", "enum", "extension", "fallthrough", /fileprivate\(set\)/, "fileprivate", "final", "for", "func", "get", "guard", "if", "import", "indirect", "infix", /init\?/, /init!/, "inout", /internal\(set\)/, "internal", "in", "is", "isolated", "nonisolated", "lazy", "let", "macro", "mutating", "nonmutating", /open\(set\)/, "open", "operator", "optional", "override", "package", "postfix", "precedencegroup", "prefix", /private\(set\)/, "private", "protocol", /public\(set\)/, "public", "repeat", "required", "rethrows", "return", "set", "some", "static", "struct", "subscript", "super", "switch", "throws", "throw", /try\?/, /try!/, "try", "typealias", /unowned\(safe\)/, /unowned\(unsafe\)/, "unowned", "var", "weak", "where", "while", "willSet"], Ae = ["false", "nil", "true"], Se = ["assignment", "associativity", "higherThan", "left", "lowerThan", "none", "right"], Ce = ["#colorLiteral", "#column", "#dsohandle", "#else", "#elseif", "#endif", "#error", "#file", "#fileID", "#fileLiteral", "#filePath", "#function", "#if", "#imageLiteral", "#keyPath", "#line", "#selector", "#sourceLocation", "#warning"], Te = ["abs", "all", "any", "assert", "assertionFailure", "debugPrint", "dump", "fatalError", "getVaList", "isKnownUniquelyReferenced", "max", "min", "numericCast", "pointwiseMax", "pointwiseMin", "precondition", "preconditionFailure", "print", "readLine", "repeatElement", "sequence", "stride", "swap", "swift_unboxFromSwiftValueWithType", "transcode", "type", "unsafeBitCast", "unsafeDowncast", "withExtendedLifetime", "withUnsafeMutablePointer", "withUnsafePointer", "withVaList", "withoutActuallyEscaping", "zip"], Re = m(/[/=\-+!*%<>&|^~?]/, /[\u00A1-\u00A7]/, /[\u00A9\u00AB]/, /[\u00AC\u00AE]/, /[\u00B0\u00B1]/, /[\u00B6\u00BB\u00BF\u00D7\u00F7]/, /[\u2016-\u2017]/, /[\u2020-\u2027]/, /[\u2030-\u203E]/, /[\u2041-\u2053]/, /[\u2055-\u205E]/, /[\u2190-\u23FF]/, /[\u2500-\u2775]/, /[\u2794-\u2BFF]/, /[\u2E00-\u2E7F]/, /[\u3001-\u3003]/, /[\u3008-\u3020]/, /[\u3030]/), De = m(Re, /[\u0300-\u036F]/, /[\u1DC0-\u1DFF]/, /[\u20D0-\u20FF]/, /[\uFE00-\uFE0F]/, /[\uFE20-\uFE2F]/), Ie = b(Re, De, "*"), Le = m(/[a-zA-Z_]/, /[\u00A8\u00AA\u00AD\u00AF\u00B2-\u00B5\u00B7-\u00BA]/, /[\u00BC-\u00BE\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF]/, /[\u0100-\u02FF\u0370-\u167F\u1681-\u180D\u180F-\u1DBF]/, /[\u1E00-\u1FFF]/, /[\u200B-\u200D\u202A-\u202E\u203F-\u2040\u2054\u2060-\u206F]/, /[\u2070-\u20CF\u2100-\u218F\u2460-\u24FF\u2776-\u2793]/, /[\u2C00-\u2DFF\u2E80-\u2FFF]/, /[\u3004-\u3007\u3021-\u302F\u3031-\u303F\u3040-\uD7FF]/, /[\uF900-\uFD3D\uFD40-\uFDCF\uFDF0-\uFE1F\uFE30-\uFE44]/, /[\uFE47-\uFEFE\uFF00-\uFFFD]/), Be = m(Le, /\d/, /[\u0300-\u036F\u1DC0-\u1DFF\u20D0-\u20FF\uFE20-\uFE2F]/), $e = b(Le, Be, "*"), Fe = b(/[A-Z]/, Be, "*"), ze = ["attached", "autoclosure", b(/convention\(/, m("swift", "block", "c"), /\)/), "discardableResult", "dynamicCallable", "dynamicMemberLookup", "escaping", "freestanding", "frozen", "GKInspectable", "IBAction", "IBDesignable", "IBInspectable", "IBOutlet", "IBSegueAction", "inlinable", "main", "nonobjc", "NSApplicationMain", "NSCopying", "NSManaged", b(/objc\(/, $e, /\)/), "objc", "objcMembers", "propertyWrapper", "requires_stored_property_inits", "resultBuilder", "Sendable", "testable", "UIApplicationMain", "unchecked", "unknown", "usableFromInline", "warn_unqualified_access"], je = ["iOS", "iOSApplicationExtension", "macOS", "macOSApplicationExtension", "macCatalyst", "macCatalystApplicationExtension", "watchOS", "watchOSApplicationExtension", "tvOS", "tvOSApplicationExtension", "swift"];
var Ue = Object.freeze({
  __proto__: null,
  grmr_bash: (e2) => {
    const n2 = e2.regex, t2 = {}, a2 = {
      begin: /\$\{/,
      end: /\}/,
      contains: ["self", { begin: /:-/, contains: [t2] }]
    };
    Object.assign(t2, { className: "variable", variants: [{
      begin: n2.concat(/\$[\w\d#@][\w\d_]*/, "(?![\\w\\d])(?![$])")
    }, a2] });
    const i2 = {
      className: "subst",
      begin: /\$\(/,
      end: /\)/,
      contains: [e2.BACKSLASH_ESCAPE]
    }, r2 = e2.inherit(e2.COMMENT(), { match: [/(^|\s)/, /#.*$/], scope: { 2: "comment" } }), s2 = {
      begin: /<<-?\s*(?=\w+)/,
      starts: { contains: [e2.END_SAME_AS_BEGIN({
        begin: /(\w+)/,
        end: /(\w+)/,
        className: "string"
      })] }
    }, o2 = {
      className: "string",
      begin: /"/,
      end: /"/,
      contains: [e2.BACKSLASH_ESCAPE, t2, i2]
    };
    i2.contains.push(o2);
    const l2 = {
      begin: /\$?\(\(/,
      end: /\)\)/,
      contains: [{ begin: /\d+#[0-9a-f]+/, className: "number" }, e2.NUMBER_MODE, t2]
    }, c2 = e2.SHEBANG({
      binary: "(fish|bash|zsh|sh|csh|ksh|tcsh|dash|scsh)",
      relevance: 10
    }), d2 = {
      className: "function",
      begin: /\w[\w\d_]*\s*\(\s*\)\s*\{/,
      returnBegin: true,
      contains: [e2.inherit(e2.TITLE_MODE, { begin: /\w[\w\d_]*/ })],
      relevance: 0
    };
    return {
      name: "Bash",
      aliases: ["sh", "zsh"],
      keywords: {
        $pattern: /\b[a-z][a-z0-9._-]+\b/,
        keyword: ["if", "then", "else", "elif", "fi", "time", "for", "while", "until", "in", "do", "done", "case", "esac", "coproc", "function", "select"],
        literal: ["true", "false"],
        built_in: ["break", "cd", "continue", "eval", "exec", "exit", "export", "getopts", "hash", "pwd", "readonly", "return", "shift", "test", "times", "trap", "umask", "unset", "alias", "bind", "builtin", "caller", "command", "declare", "echo", "enable", "help", "let", "local", "logout", "mapfile", "printf", "read", "readarray", "source", "sudo", "type", "typeset", "ulimit", "unalias", "set", "shopt", "autoload", "bg", "bindkey", "bye", "cap", "chdir", "clone", "comparguments", "compcall", "compctl", "compdescribe", "compfiles", "compgroups", "compquote", "comptags", "comptry", "compvalues", "dirs", "disable", "disown", "echotc", "echoti", "emulate", "fc", "fg", "float", "functions", "getcap", "getln", "history", "integer", "jobs", "kill", "limit", "log", "noglob", "popd", "print", "pushd", "pushln", "rehash", "sched", "setcap", "setopt", "stat", "suspend", "ttyctl", "unfunction", "unhash", "unlimit", "unsetopt", "vared", "wait", "whence", "where", "which", "zcompile", "zformat", "zftp", "zle", "zmodload", "zparseopts", "zprof", "zpty", "zregexparse", "zsocket", "zstyle", "ztcp", "chcon", "chgrp", "chown", "chmod", "cp", "dd", "df", "dir", "dircolors", "ln", "ls", "mkdir", "mkfifo", "mknod", "mktemp", "mv", "realpath", "rm", "rmdir", "shred", "sync", "touch", "truncate", "vdir", "b2sum", "base32", "base64", "cat", "cksum", "comm", "csplit", "cut", "expand", "fmt", "fold", "head", "join", "md5sum", "nl", "numfmt", "od", "paste", "ptx", "pr", "sha1sum", "sha224sum", "sha256sum", "sha384sum", "sha512sum", "shuf", "sort", "split", "sum", "tac", "tail", "tr", "tsort", "unexpand", "uniq", "wc", "arch", "basename", "chroot", "date", "dirname", "du", "echo", "env", "expr", "factor", "groups", "hostid", "id", "link", "logname", "nice", "nohup", "nproc", "pathchk", "pinky", "printenv", "printf", "pwd", "readlink", "runcon", "seq", "sleep", "stat", "stdbuf", "stty", "tee", "test", "timeout", "tty", "uname", "unlink", "uptime", "users", "who", "whoami", "yes"]
      },
      contains: [c2, e2.SHEBANG(), d2, l2, r2, s2, { match: /(\/[a-z._-]+)+/ }, o2, { match: /\\"/ }, {
        className: "string",
        begin: /'/,
        end: /'/
      }, { match: /\\'/ }, t2]
    };
  },
  grmr_c: (e2) => {
    const n2 = e2.regex, t2 = e2.COMMENT("//", "$", {
      contains: [{ begin: /\\\n/ }]
    }), a2 = "decltype\\(auto\\)", i2 = "[a-zA-Z_]\\w*::", r2 = "(" + a2 + "|" + n2.optional(i2) + "[a-zA-Z_]\\w*" + n2.optional("<[^<>]+>") + ")", s2 = {
      className: "type",
      variants: [{ begin: "\\b[a-z\\d_]*_t\\b" }, {
        match: /\batomic_[a-z]{3,6}\b/
      }]
    }, o2 = { className: "string", variants: [{
      begin: '(u8?|U|L)?"',
      end: '"',
      illegal: "\\n",
      contains: [e2.BACKSLASH_ESCAPE]
    }, {
      begin: "(u8?|U|L)?'(\\\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4,8}|[0-7]{3}|\\S)|.)",
      end: "'",
      illegal: "."
    }, e2.END_SAME_AS_BEGIN({
      begin: /(?:u8?|U|L)?R"([^()\\ ]{0,16})\(/,
      end: /\)([^()\\ ]{0,16})"/
    })] }, l2 = {
      className: "number",
      variants: [{ match: /\b(0b[01']+)/ }, {
        match: /(-?)\b([\d']+(\.[\d']*)?|\.[\d']+)((ll|LL|l|L)(u|U)?|(u|U)(ll|LL|l|L)?|f|F|b|B)/
      }, {
        match: /(-?)\b(0[xX][a-fA-F0-9]+(?:'[a-fA-F0-9]+)*(?:\.[a-fA-F0-9]*(?:'[a-fA-F0-9]*)*)?(?:[pP][-+]?[0-9]+)?(l|L)?(u|U)?)/
      }, { match: /(-?)\b\d+(?:'\d+)*(?:\.\d*(?:'\d*)*)?(?:[eE][-+]?\d+)?/ }],
      relevance: 0
    }, c2 = { className: "meta", begin: /#\s*[a-z]+\b/, end: /$/, keywords: {
      keyword: "if else elif endif define undef warning error line pragma _Pragma ifdef ifndef elifdef elifndef include"
    }, contains: [{ begin: /\\\n/, relevance: 0 }, e2.inherit(o2, { className: "string" }), {
      className: "string",
      begin: /<.*?>/
    }, t2, e2.C_BLOCK_COMMENT_MODE] }, d2 = {
      className: "title",
      begin: n2.optional(i2) + e2.IDENT_RE,
      relevance: 0
    }, g2 = n2.optional(i2) + e2.IDENT_RE + "\\s*\\(", u4 = {
      keyword: ["asm", "auto", "break", "case", "continue", "default", "do", "else", "enum", "extern", "for", "fortran", "goto", "if", "inline", "register", "restrict", "return", "sizeof", "typeof", "typeof_unqual", "struct", "switch", "typedef", "union", "volatile", "while", "_Alignas", "_Alignof", "_Atomic", "_Generic", "_Noreturn", "_Static_assert", "_Thread_local", "alignas", "alignof", "noreturn", "static_assert", "thread_local", "_Pragma"],
      type: ["float", "double", "signed", "unsigned", "int", "short", "long", "char", "void", "_Bool", "_BitInt", "_Complex", "_Imaginary", "_Decimal32", "_Decimal64", "_Decimal96", "_Decimal128", "_Decimal64x", "_Decimal128x", "_Float16", "_Float32", "_Float64", "_Float128", "_Float32x", "_Float64x", "_Float128x", "const", "static", "constexpr", "complex", "bool", "imaginary"],
      literal: "true false NULL",
      built_in: "std string wstring cin cout cerr clog stdin stdout stderr stringstream istringstream ostringstream auto_ptr deque list queue stack vector map set pair bitset multiset multimap unordered_set unordered_map unordered_multiset unordered_multimap priority_queue make_pair array shared_ptr abort terminate abs acos asin atan2 atan calloc ceil cosh cos exit exp fabs floor fmod fprintf fputs free frexp fscanf future isalnum isalpha iscntrl isdigit isgraph islower isprint ispunct isspace isupper isxdigit tolower toupper labs ldexp log10 log malloc realloc memchr memcmp memcpy memset modf pow printf putchar puts scanf sinh sin snprintf sprintf sqrt sscanf strcat strchr strcmp strcpy strcspn strlen strncat strncmp strncpy strpbrk strrchr strspn strstr tanh tan vfprintf vprintf vsprintf endl initializer_list unique_ptr"
    }, b2 = [c2, s2, t2, e2.C_BLOCK_COMMENT_MODE, l2, o2], m2 = {
      variants: [{ begin: /=/, end: /;/ }, {
        begin: /\(/,
        end: /\)/
      }, { beginKeywords: "new throw return else", end: /;/ }],
      keywords: u4,
      contains: b2.concat([{
        begin: /\(/,
        end: /\)/,
        keywords: u4,
        contains: b2.concat(["self"]),
        relevance: 0
      }]),
      relevance: 0
    }, p2 = {
      begin: "(" + r2 + "[\\*&\\s]+)+" + g2,
      returnBegin: true,
      end: /[{;=]/,
      excludeEnd: true,
      keywords: u4,
      illegal: /[^\w\s\*&:<>.]/,
      contains: [{ begin: a2, keywords: u4, relevance: 0 }, {
        begin: g2,
        returnBegin: true,
        contains: [e2.inherit(d2, { className: "title.function" })],
        relevance: 0
      }, { relevance: 0, match: /,/ }, {
        className: "params",
        begin: /\(/,
        end: /\)/,
        keywords: u4,
        relevance: 0,
        contains: [t2, e2.C_BLOCK_COMMENT_MODE, o2, l2, s2, {
          begin: /\(/,
          end: /\)/,
          keywords: u4,
          relevance: 0,
          contains: ["self", t2, e2.C_BLOCK_COMMENT_MODE, o2, l2, s2]
        }]
      }, s2, t2, e2.C_BLOCK_COMMENT_MODE, c2]
    };
    return {
      name: "C",
      aliases: ["h"],
      keywords: u4,
      disableAutodetect: true,
      illegal: "</",
      contains: [].concat(m2, p2, b2, [c2, {
        begin: e2.IDENT_RE + "::",
        keywords: u4
      }, {
        className: "class",
        beginKeywords: "enum class struct union",
        end: /[{;:<>=]/,
        contains: [{
          beginKeywords: "final class struct"
        }, e2.TITLE_MODE]
      }]),
      exports: {
        preprocessor: c2,
        strings: o2,
        keywords: u4
      }
    };
  },
  grmr_cpp: (e2) => {
    const n2 = e2.regex, t2 = e2.COMMENT("//", "$", {
      contains: [{ begin: /\\\n/ }]
    }), a2 = "decltype\\(auto\\)", i2 = "[a-zA-Z_]\\w*::", r2 = "(?!struct)(" + a2 + "|" + n2.optional(i2) + "[a-zA-Z_]\\w*" + n2.optional("<[^<>]+>") + ")", s2 = {
      className: "type",
      begin: "\\b[a-z\\d_]*_t\\b"
    }, o2 = { className: "string", variants: [{
      begin: '(u8?|U|L)?"',
      end: '"',
      illegal: "\\n",
      contains: [e2.BACKSLASH_ESCAPE]
    }, {
      begin: "(u8?|U|L)?'(\\\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4,8}|[0-7]{3}|\\S)|.)",
      end: "'",
      illegal: "."
    }, e2.END_SAME_AS_BEGIN({
      begin: /(?:u8?|U|L)?R"([^()\\ ]{0,16})\(/,
      end: /\)([^()\\ ]{0,16})"/
    })] }, l2 = {
      className: "number",
      variants: [{
        begin: "[+-]?(?:(?:[0-9](?:'?[0-9])*\\.(?:[0-9](?:'?[0-9])*)?|\\.[0-9](?:'?[0-9])*)(?:[Ee][+-]?[0-9](?:'?[0-9])*)?|[0-9](?:'?[0-9])*[Ee][+-]?[0-9](?:'?[0-9])*|0[Xx](?:[0-9A-Fa-f](?:'?[0-9A-Fa-f])*(?:\\.(?:[0-9A-Fa-f](?:'?[0-9A-Fa-f])*)?)?|\\.[0-9A-Fa-f](?:'?[0-9A-Fa-f])*)[Pp][+-]?[0-9](?:'?[0-9])*)(?:[Ff](?:16|32|64|128)?|(BF|bf)16|[Ll]|)"
      }, {
        begin: "[+-]?\\b(?:0[Bb][01](?:'?[01])*|0[Xx][0-9A-Fa-f](?:'?[0-9A-Fa-f])*|0(?:'?[0-7])*|[1-9](?:'?[0-9])*)(?:[Uu](?:LL?|ll?)|[Uu][Zz]?|(?:LL?|ll?)[Uu]?|[Zz][Uu]|)"
      }],
      relevance: 0
    }, c2 = { className: "meta", begin: /#\s*[a-z]+\b/, end: /$/, keywords: {
      keyword: "if else elif endif define undef warning error line pragma _Pragma ifdef ifndef include"
    }, contains: [{ begin: /\\\n/, relevance: 0 }, e2.inherit(o2, { className: "string" }), {
      className: "string",
      begin: /<.*?>/
    }, t2, e2.C_BLOCK_COMMENT_MODE] }, d2 = {
      className: "title",
      begin: n2.optional(i2) + e2.IDENT_RE,
      relevance: 0
    }, g2 = n2.optional(i2) + e2.IDENT_RE + "\\s*\\(", u4 = {
      type: ["bool", "char", "char16_t", "char32_t", "char8_t", "double", "float", "int", "long", "short", "void", "wchar_t", "unsigned", "signed", "const", "static"],
      keyword: ["alignas", "alignof", "and", "and_eq", "asm", "atomic_cancel", "atomic_commit", "atomic_noexcept", "auto", "bitand", "bitor", "break", "case", "catch", "class", "co_await", "co_return", "co_yield", "compl", "concept", "const_cast|10", "consteval", "constexpr", "constinit", "continue", "decltype", "default", "delete", "do", "dynamic_cast|10", "else", "enum", "explicit", "export", "extern", "false", "final", "for", "friend", "goto", "if", "import", "inline", "module", "mutable", "namespace", "new", "noexcept", "not", "not_eq", "nullptr", "operator", "or", "or_eq", "override", "private", "protected", "public", "reflexpr", "register", "reinterpret_cast|10", "requires", "return", "sizeof", "static_assert", "static_cast|10", "struct", "switch", "synchronized", "template", "this", "thread_local", "throw", "transaction_safe", "transaction_safe_dynamic", "true", "try", "typedef", "typeid", "typename", "union", "using", "virtual", "volatile", "while", "xor", "xor_eq"],
      literal: ["NULL", "false", "nullopt", "nullptr", "true"],
      built_in: ["_Pragma"],
      _type_hints: ["any", "auto_ptr", "barrier", "binary_semaphore", "bitset", "complex", "condition_variable", "condition_variable_any", "counting_semaphore", "deque", "false_type", "flat_map", "flat_set", "future", "imaginary", "initializer_list", "istringstream", "jthread", "latch", "lock_guard", "multimap", "multiset", "mutex", "optional", "ostringstream", "packaged_task", "pair", "promise", "priority_queue", "queue", "recursive_mutex", "recursive_timed_mutex", "scoped_lock", "set", "shared_future", "shared_lock", "shared_mutex", "shared_timed_mutex", "shared_ptr", "stack", "string_view", "stringstream", "timed_mutex", "thread", "true_type", "tuple", "unique_lock", "unique_ptr", "unordered_map", "unordered_multimap", "unordered_multiset", "unordered_set", "variant", "vector", "weak_ptr", "wstring", "wstring_view"]
    }, b2 = {
      className: "function.dispatch",
      relevance: 0,
      keywords: {
        _hint: ["abort", "abs", "acos", "apply", "as_const", "asin", "atan", "atan2", "calloc", "ceil", "cerr", "cin", "clog", "cos", "cosh", "cout", "declval", "endl", "exchange", "exit", "exp", "fabs", "floor", "fmod", "forward", "fprintf", "fputs", "free", "frexp", "fscanf", "future", "invoke", "isalnum", "isalpha", "iscntrl", "isdigit", "isgraph", "islower", "isprint", "ispunct", "isspace", "isupper", "isxdigit", "labs", "launder", "ldexp", "log", "log10", "make_pair", "make_shared", "make_shared_for_overwrite", "make_tuple", "make_unique", "malloc", "memchr", "memcmp", "memcpy", "memset", "modf", "move", "pow", "printf", "putchar", "puts", "realloc", "scanf", "sin", "sinh", "snprintf", "sprintf", "sqrt", "sscanf", "std", "stderr", "stdin", "stdout", "strcat", "strchr", "strcmp", "strcpy", "strcspn", "strlen", "strncat", "strncmp", "strncpy", "strpbrk", "strrchr", "strspn", "strstr", "swap", "tan", "tanh", "terminate", "to_underlying", "tolower", "toupper", "vfprintf", "visit", "vprintf", "vsprintf"]
      },
      begin: n2.concat(/\b/, /(?!decltype)/, /(?!if)/, /(?!for)/, /(?!switch)/, /(?!while)/, e2.IDENT_RE, n2.lookahead(/(<[^<>]+>|)\s*\(/))
    }, m2 = [b2, c2, s2, t2, e2.C_BLOCK_COMMENT_MODE, l2, o2], p2 = {
      variants: [{ begin: /=/, end: /;/ }, {
        begin: /\(/,
        end: /\)/
      }, { beginKeywords: "new throw return else", end: /;/ }],
      keywords: u4,
      contains: m2.concat([{
        begin: /\(/,
        end: /\)/,
        keywords: u4,
        contains: m2.concat(["self"]),
        relevance: 0
      }]),
      relevance: 0
    }, _2 = {
      className: "function",
      begin: "(" + r2 + "[\\*&\\s]+)+" + g2,
      returnBegin: true,
      end: /[{;=]/,
      excludeEnd: true,
      keywords: u4,
      illegal: /[^\w\s\*&:<>.]/,
      contains: [{ begin: a2, keywords: u4, relevance: 0 }, {
        begin: g2,
        returnBegin: true,
        contains: [d2],
        relevance: 0
      }, { begin: /::/, relevance: 0 }, {
        begin: /:/,
        endsWithParent: true,
        contains: [o2, l2]
      }, { relevance: 0, match: /,/ }, {
        className: "params",
        begin: /\(/,
        end: /\)/,
        keywords: u4,
        relevance: 0,
        contains: [t2, e2.C_BLOCK_COMMENT_MODE, o2, l2, s2, {
          begin: /\(/,
          end: /\)/,
          keywords: u4,
          relevance: 0,
          contains: ["self", t2, e2.C_BLOCK_COMMENT_MODE, o2, l2, s2]
        }]
      }, s2, t2, e2.C_BLOCK_COMMENT_MODE, c2]
    };
    return {
      name: "C++",
      aliases: ["cc", "c++", "h++", "hpp", "hh", "hxx", "cxx"],
      keywords: u4,
      illegal: "</",
      classNameAliases: { "function.dispatch": "built_in" },
      contains: [].concat(p2, _2, b2, m2, [c2, {
        begin: "\\b(deque|list|queue|priority_queue|pair|stack|vector|map|set|bitset|multiset|multimap|unordered_map|unordered_set|unordered_multiset|unordered_multimap|array|tuple|optional|variant|function|flat_map|flat_set)\\s*<(?!<)",
        end: ">",
        keywords: u4,
        contains: ["self", s2]
      }, { begin: e2.IDENT_RE + "::", keywords: u4 }, {
        match: [/\b(?:enum(?:\s+(?:class|struct))?|class|struct|union)/, /\s+/, /\w+/],
        className: { 1: "keyword", 3: "title.class" }
      }])
    };
  },
  grmr_csharp: (e2) => {
    const n2 = {
      keyword: ["abstract", "as", "base", "break", "case", "catch", "class", "const", "continue", "do", "else", "event", "explicit", "extern", "finally", "fixed", "for", "foreach", "goto", "if", "implicit", "in", "interface", "internal", "is", "lock", "namespace", "new", "operator", "out", "override", "params", "private", "protected", "public", "readonly", "record", "ref", "return", "scoped", "sealed", "sizeof", "stackalloc", "static", "struct", "switch", "this", "throw", "try", "typeof", "unchecked", "unsafe", "using", "virtual", "void", "volatile", "while"].concat(["add", "alias", "and", "ascending", "args", "async", "await", "by", "descending", "dynamic", "equals", "file", "from", "get", "global", "group", "init", "into", "join", "let", "nameof", "not", "notnull", "on", "or", "orderby", "partial", "record", "remove", "required", "scoped", "select", "set", "unmanaged", "value|0", "var", "when", "where", "with", "yield"]),
      built_in: ["bool", "byte", "char", "decimal", "delegate", "double", "dynamic", "enum", "float", "int", "long", "nint", "nuint", "object", "sbyte", "short", "string", "ulong", "uint", "ushort"],
      literal: ["default", "false", "null", "true"]
    }, t2 = e2.inherit(e2.TITLE_MODE, {
      begin: "[a-zA-Z](\\.?\\w)*"
    }), a2 = { className: "number", variants: [{
      begin: "\\b(0b[01']+)"
    }, {
      begin: "(-?)\\b([\\d']+(\\.[\\d']*)?|\\.[\\d']+)(u|U|l|L|ul|UL|f|F|b|B)"
    }, {
      begin: "(-?)(\\b0[xX][a-fA-F0-9']+|(\\b[\\d']+(\\.[\\d']*)?|\\.[\\d']+)([eE][-+]?[\\d']+)?)"
    }], relevance: 0 }, i2 = {
      className: "string",
      begin: '@"',
      end: '"',
      contains: [{ begin: '""' }]
    }, r2 = e2.inherit(i2, { illegal: /\n/ }), s2 = {
      className: "subst",
      begin: /\{/,
      end: /\}/,
      keywords: n2
    }, o2 = e2.inherit(s2, { illegal: /\n/ }), l2 = {
      className: "string",
      begin: /\$"/,
      end: '"',
      illegal: /\n/,
      contains: [{ begin: /\{\{/ }, {
        begin: /\}\}/
      }, e2.BACKSLASH_ESCAPE, o2]
    }, c2 = { className: "string", begin: /\$@"/, end: '"', contains: [{
      begin: /\{\{/
    }, { begin: /\}\}/ }, { begin: '""' }, s2] }, d2 = e2.inherit(c2, {
      illegal: /\n/,
      contains: [{ begin: /\{\{/ }, { begin: /\}\}/ }, { begin: '""' }, o2]
    });
    s2.contains = [c2, l2, i2, e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE, a2, e2.C_BLOCK_COMMENT_MODE], o2.contains = [d2, l2, r2, e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE, a2, e2.inherit(e2.C_BLOCK_COMMENT_MODE, {
      illegal: /\n/
    })];
    const g2 = { variants: [{
      className: "string",
      begin: /"""("*)(?!")(.|\n)*?"""\1/,
      relevance: 1
    }, c2, l2, i2, e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE] }, u4 = {
      begin: "<",
      end: ">",
      contains: [{ beginKeywords: "in out" }, t2]
    }, b2 = e2.IDENT_RE + "(<" + e2.IDENT_RE + "(\\s*,\\s*" + e2.IDENT_RE + ")*>)?(\\[\\])?", m2 = {
      begin: "@" + e2.IDENT_RE,
      relevance: 0
    };
    return {
      name: "C#",
      aliases: ["cs", "c#"],
      keywords: n2,
      illegal: /::/,
      contains: [e2.COMMENT("///", "$", {
        returnBegin: true,
        contains: [{ className: "doctag", variants: [{ begin: "///", relevance: 0 }, {
          begin: "<!--|-->"
        }, { begin: "</?", end: ">" }] }]
      }), e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE, {
        className: "meta",
        begin: "#",
        end: "$",
        keywords: {
          keyword: "if else elif endif define undef warning error line region endregion pragma checksum"
        }
      }, g2, a2, {
        beginKeywords: "class interface",
        relevance: 0,
        end: /[{;=]/,
        illegal: /[^\s:,]/,
        contains: [{
          beginKeywords: "where class"
        }, t2, u4, e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE]
      }, {
        beginKeywords: "namespace",
        relevance: 0,
        end: /[{;=]/,
        illegal: /[^\s:]/,
        contains: [t2, e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE]
      }, {
        beginKeywords: "record",
        relevance: 0,
        end: /[{;=]/,
        illegal: /[^\s:]/,
        contains: [t2, u4, e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE]
      }, {
        className: "meta",
        begin: "^\\s*\\[(?=[\\w])",
        excludeBegin: true,
        end: "\\]",
        excludeEnd: true,
        contains: [{
          className: "string",
          begin: /"/,
          end: /"/
        }]
      }, {
        beginKeywords: "new return throw await else",
        relevance: 0
      }, {
        className: "function",
        begin: "(" + b2 + "\\s+)+" + e2.IDENT_RE + "\\s*(<[^=]+>\\s*)?\\(",
        returnBegin: true,
        end: /\s*[{;=]/,
        excludeEnd: true,
        keywords: n2,
        contains: [{
          beginKeywords: "public private protected static internal protected abstract async extern override unsafe virtual new sealed partial",
          relevance: 0
        }, {
          begin: e2.IDENT_RE + "\\s*(<[^=]+>\\s*)?\\(",
          returnBegin: true,
          contains: [e2.TITLE_MODE, u4],
          relevance: 0
        }, { match: /\(\)/ }, {
          className: "params",
          begin: /\(/,
          end: /\)/,
          excludeBegin: true,
          excludeEnd: true,
          keywords: n2,
          relevance: 0,
          contains: [g2, a2, e2.C_BLOCK_COMMENT_MODE]
        }, e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE]
      }, m2]
    };
  },
  grmr_css: (e2) => {
    const n2 = e2.regex, t2 = te(e2), a2 = [e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE];
    return {
      name: "CSS",
      case_insensitive: true,
      illegal: /[=|'\$]/,
      keywords: {
        keyframePosition: "from to"
      },
      classNameAliases: { keyframePosition: "selector-tag" },
      contains: [t2.BLOCK_COMMENT, {
        begin: /-(webkit|moz|ms|o)-(?=[a-z])/
      }, t2.CSS_NUMBER_MODE, {
        className: "selector-id",
        begin: /#[A-Za-z0-9_-]+/,
        relevance: 0
      }, {
        className: "selector-class",
        begin: "\\.[a-zA-Z-][a-zA-Z0-9_-]*",
        relevance: 0
      }, t2.ATTRIBUTE_SELECTOR_MODE, {
        className: "selector-pseudo",
        variants: [{
          begin: ":(" + re.join("|") + ")"
        }, { begin: ":(:)?(" + se.join("|") + ")" }]
      }, t2.CSS_VARIABLE, { className: "attribute", begin: "\\b(" + oe.join("|") + ")\\b" }, {
        begin: /:/,
        end: /[;}{]/,
        contains: [t2.BLOCK_COMMENT, t2.HEXCOLOR, t2.IMPORTANT, t2.CSS_NUMBER_MODE, ...a2, {
          begin: /(url|data-uri)\(/,
          end: /\)/,
          relevance: 0,
          keywords: {
            built_in: "url data-uri"
          },
          contains: [...a2, {
            className: "string",
            begin: /[^)]/,
            endsWithParent: true,
            excludeEnd: true
          }]
        }, t2.FUNCTION_DISPATCH]
      }, {
        begin: n2.lookahead(/@/),
        end: "[{;]",
        relevance: 0,
        illegal: /:/,
        contains: [{
          className: "keyword",
          begin: /@-?\w[\w]*(-\w+)*/
        }, { begin: /\s/, endsWithParent: true, excludeEnd: true, relevance: 0, keywords: {
          $pattern: /[a-z-]+/,
          keyword: "and or not only",
          attribute: ie.join(" ")
        }, contains: [{
          begin: /[a-z-]+(?=:)/,
          className: "attribute"
        }, ...a2, t2.CSS_NUMBER_MODE] }]
      }, {
        className: "selector-tag",
        begin: "\\b(" + ae.join("|") + ")\\b"
      }]
    };
  },
  grmr_diff: (e2) => {
    const n2 = e2.regex;
    return { name: "Diff", aliases: ["patch"], contains: [{
      className: "meta",
      relevance: 10,
      match: n2.either(/^@@ +-\d+,\d+ +\+\d+,\d+ +@@/, /^\*\*\* +\d+,\d+ +\*\*\*\*$/, /^--- +\d+,\d+ +----$/)
    }, { className: "comment", variants: [{
      begin: n2.either(/Index: /, /^index/, /={3,}/, /^-{3}/, /^\*{3} /, /^\+{3}/, /^diff --git/),
      end: /$/
    }, { match: /^\*{15}$/ }] }, { className: "addition", begin: /^\+/, end: /$/ }, {
      className: "deletion",
      begin: /^-/,
      end: /$/
    }, {
      className: "addition",
      begin: /^!/,
      end: /$/
    }] };
  },
  grmr_go: (e2) => {
    const n2 = {
      keyword: ["break", "case", "chan", "const", "continue", "default", "defer", "else", "fallthrough", "for", "func", "go", "goto", "if", "import", "interface", "map", "package", "range", "return", "select", "struct", "switch", "type", "var"],
      type: ["bool", "byte", "complex64", "complex128", "error", "float32", "float64", "int8", "int16", "int32", "int64", "string", "uint8", "uint16", "uint32", "uint64", "int", "uint", "uintptr", "rune"],
      literal: ["true", "false", "iota", "nil"],
      built_in: ["append", "cap", "close", "complex", "copy", "imag", "len", "make", "new", "panic", "print", "println", "real", "recover", "delete"]
    };
    return {
      name: "Go",
      aliases: ["golang"],
      keywords: n2,
      illegal: "</",
      contains: [e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE, {
        className: "string",
        variants: [e2.QUOTE_STRING_MODE, e2.APOS_STRING_MODE, { begin: "`", end: "`" }]
      }, {
        className: "number",
        variants: [{
          match: /-?\b0[xX]\.[a-fA-F0-9](_?[a-fA-F0-9])*[pP][+-]?\d(_?\d)*i?/,
          relevance: 0
        }, {
          match: /-?\b0[xX](_?[a-fA-F0-9])+((\.([a-fA-F0-9](_?[a-fA-F0-9])*)?)?[pP][+-]?\d(_?\d)*)?i?/,
          relevance: 0
        }, { match: /-?\b0[oO](_?[0-7])*i?/, relevance: 0 }, {
          match: /-?\.\d(_?\d)*([eE][+-]?\d(_?\d)*)?i?/,
          relevance: 0
        }, {
          match: /-?\b\d(_?\d)*(\.(\d(_?\d)*)?)?([eE][+-]?\d(_?\d)*)?i?/,
          relevance: 0
        }]
      }, {
        begin: /:=/
      }, {
        className: "function",
        beginKeywords: "func",
        end: "\\s*(\\{|$)",
        excludeEnd: true,
        contains: [e2.TITLE_MODE, {
          className: "params",
          begin: /\(/,
          end: /\)/,
          endsParent: true,
          keywords: n2,
          illegal: /["']/
        }]
      }]
    };
  },
  grmr_graphql: (e2) => {
    const n2 = e2.regex;
    return {
      name: "GraphQL",
      aliases: ["gql"],
      case_insensitive: true,
      disableAutodetect: false,
      keywords: {
        keyword: ["query", "mutation", "subscription", "type", "input", "schema", "directive", "interface", "union", "scalar", "fragment", "enum", "on"],
        literal: ["true", "false", "null"]
      },
      contains: [e2.HASH_COMMENT_MODE, e2.QUOTE_STRING_MODE, e2.NUMBER_MODE, {
        scope: "punctuation",
        match: /[.]{3}/,
        relevance: 0
      }, {
        scope: "punctuation",
        begin: /[\!\(\)\:\=\[\]\{\|\}]{1}/,
        relevance: 0
      }, {
        scope: "variable",
        begin: /\$/,
        end: /\W/,
        excludeEnd: true,
        relevance: 0
      }, { scope: "meta", match: /@\w+/, excludeEnd: true }, {
        scope: "symbol",
        begin: n2.concat(/[_A-Za-z][_0-9A-Za-z]*/, n2.lookahead(/\s*:/)),
        relevance: 0
      }],
      illegal: [/[;<']/, /BEGIN/]
    };
  },
  grmr_ini: (e2) => {
    const n2 = e2.regex, t2 = {
      className: "number",
      relevance: 0,
      variants: [{ begin: /([+-]+)?[\d]+_[\d_]+/ }, {
        begin: e2.NUMBER_RE
      }]
    }, a2 = e2.COMMENT();
    a2.variants = [{ begin: /;/, end: /$/ }, {
      begin: /#/,
      end: /$/
    }];
    const i2 = { className: "variable", variants: [{ begin: /\$[\w\d"][\w\d_]*/ }, {
      begin: /\$\{(.*?)\}/
    }] }, r2 = {
      className: "literal",
      begin: /\bon|off|true|false|yes|no\b/
    }, s2 = {
      className: "string",
      contains: [e2.BACKSLASH_ESCAPE],
      variants: [{ begin: "'''", end: "'''", relevance: 10 }, {
        begin: '"""',
        end: '"""',
        relevance: 10
      }, { begin: '"', end: '"' }, { begin: "'", end: "'" }]
    }, o2 = {
      begin: /\[/,
      end: /\]/,
      contains: [a2, r2, i2, s2, t2, "self"],
      relevance: 0
    }, l2 = n2.either(/[A-Za-z0-9_-]+/, /"(\\"|[^"])*"/, /'[^']*'/);
    return {
      name: "TOML, also INI",
      aliases: ["toml"],
      case_insensitive: true,
      illegal: /\S/,
      contains: [a2, { className: "section", begin: /\[+/, end: /\]+/ }, {
        begin: n2.concat(l2, "(\\s*\\.\\s*", l2, ")*", n2.lookahead(/\s*=\s*[^#\s]/)),
        className: "attr",
        starts: { end: /$/, contains: [a2, o2, r2, i2, s2, t2] }
      }]
    };
  },
  grmr_java: (e2) => {
    const n2 = e2.regex, t2 = "[À-ʸa-zA-Z_$][À-ʸa-zA-Z_$0-9]*", a2 = t2 + be("(?:<" + t2 + "~~~(?:\\s*,\\s*" + t2 + "~~~)*>)?", /~~~/g, 2), i2 = {
      keyword: ["synchronized", "abstract", "private", "var", "static", "if", "const ", "for", "while", "strictfp", "finally", "protected", "import", "native", "final", "void", "enum", "else", "break", "transient", "catch", "instanceof", "volatile", "case", "assert", "package", "default", "public", "try", "switch", "continue", "throws", "protected", "public", "private", "module", "requires", "exports", "do", "sealed", "yield", "permits", "goto", "when"],
      literal: ["false", "true", "null"],
      type: ["char", "boolean", "long", "float", "int", "byte", "short", "double"],
      built_in: ["super", "this"]
    }, r2 = { className: "meta", begin: "@" + t2, contains: [{
      begin: /\(/,
      end: /\)/,
      contains: ["self"]
    }] }, s2 = {
      className: "params",
      begin: /\(/,
      end: /\)/,
      keywords: i2,
      relevance: 0,
      contains: [e2.C_BLOCK_COMMENT_MODE],
      endsParent: true
    };
    return {
      name: "Java",
      aliases: ["jsp"],
      keywords: i2,
      illegal: /<\/|#/,
      contains: [e2.COMMENT("/\\*\\*", "\\*/", { relevance: 0, contains: [{
        begin: /\w+@/,
        relevance: 0
      }, { className: "doctag", begin: "@[A-Za-z]+" }] }), {
        begin: /import java\.[a-z]+\./,
        keywords: "import",
        relevance: 2
      }, e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE, {
        begin: /"""/,
        end: /"""/,
        className: "string",
        contains: [e2.BACKSLASH_ESCAPE]
      }, e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE, {
        match: [/\b(?:class|interface|enum|extends|implements|new)/, /\s+/, t2],
        className: {
          1: "keyword",
          3: "title.class"
        }
      }, { match: /non-sealed/, scope: "keyword" }, {
        begin: [n2.concat(/(?!else)/, t2), /\s+/, t2, /\s+/, /=(?!=)/],
        className: {
          1: "type",
          3: "variable",
          5: "operator"
        }
      }, { begin: [/record/, /\s+/, t2], className: {
        1: "keyword",
        3: "title.class"
      }, contains: [s2, e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE] }, {
        beginKeywords: "new throw return else",
        relevance: 0
      }, {
        begin: ["(?:" + a2 + "\\s+)", e2.UNDERSCORE_IDENT_RE, /\s*(?=\()/],
        className: {
          2: "title.function"
        },
        keywords: i2,
        contains: [{
          className: "params",
          begin: /\(/,
          end: /\)/,
          keywords: i2,
          relevance: 0,
          contains: [r2, e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE, ue, e2.C_BLOCK_COMMENT_MODE]
        }, e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE]
      }, ue, r2]
    };
  },
  grmr_javascript: ve,
  grmr_json: (e2) => {
    const n2 = ["true", "false", "null"], t2 = {
      scope: "literal",
      beginKeywords: n2.join(" ")
    };
    return {
      name: "JSON",
      aliases: ["jsonc"],
      keywords: {
        literal: n2
      },
      contains: [{
        className: "attr",
        begin: /"(\\.|[^\\"\r\n])*"(?=\s*:)/,
        relevance: 1.01
      }, {
        match: /[{}[\],:]/,
        className: "punctuation",
        relevance: 0
      }, e2.QUOTE_STRING_MODE, t2, e2.C_NUMBER_MODE, e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE],
      illegal: "\\S"
    };
  },
  grmr_kotlin: (e2) => {
    const n2 = {
      keyword: "abstract as val var vararg get set class object open private protected public noinline crossinline dynamic final enum if else do while for when throw try catch finally import package is in fun override companion reified inline lateinit init interface annotation data sealed internal infix operator out by constructor super tailrec where const inner suspend typealias external expect actual",
      built_in: "Byte Short Char Int Long Boolean Float Double Void Unit Nothing",
      literal: "true false null"
    }, t2 = {
      className: "symbol",
      begin: e2.UNDERSCORE_IDENT_RE + "@"
    }, a2 = { className: "subst", begin: /\$\{/, end: /\}/, contains: [e2.C_NUMBER_MODE] }, i2 = {
      className: "variable",
      begin: "\\$" + e2.UNDERSCORE_IDENT_RE
    }, r2 = {
      className: "string",
      variants: [{ begin: '"""', end: '"""(?=[^"])', contains: [i2, a2] }, {
        begin: "'",
        end: "'",
        illegal: /\n/,
        contains: [e2.BACKSLASH_ESCAPE]
      }, {
        begin: '"',
        end: '"',
        illegal: /\n/,
        contains: [e2.BACKSLASH_ESCAPE, i2, a2]
      }]
    };
    a2.contains.push(r2);
    const s2 = {
      className: "meta",
      begin: "@(?:file|property|field|get|set|receiver|param|setparam|delegate)\\s*:(?:\\s*" + e2.UNDERSCORE_IDENT_RE + ")?"
    }, o2 = {
      className: "meta",
      begin: "@" + e2.UNDERSCORE_IDENT_RE,
      contains: [{
        begin: /\(/,
        end: /\)/,
        contains: [e2.inherit(r2, { className: "string" }), "self"]
      }]
    }, l2 = ue, c2 = e2.COMMENT("/\\*", "\\*/", { contains: [e2.C_BLOCK_COMMENT_MODE] }), d2 = {
      variants: [{ className: "type", begin: e2.UNDERSCORE_IDENT_RE }, {
        begin: /\(/,
        end: /\)/,
        contains: []
      }]
    }, g2 = d2;
    return g2.variants[1].contains = [d2], d2.variants[1].contains = [g2], {
      name: "Kotlin",
      aliases: ["kt", "kts"],
      keywords: n2,
      contains: [e2.COMMENT("/\\*\\*", "\\*/", { relevance: 0, contains: [{
        className: "doctag",
        begin: "@[A-Za-z]+"
      }] }), e2.C_LINE_COMMENT_MODE, c2, {
        className: "keyword",
        begin: /\b(break|continue|return|this)\b/,
        starts: { contains: [{
          className: "symbol",
          begin: /@\w+/
        }] }
      }, t2, s2, o2, {
        className: "function",
        beginKeywords: "fun",
        end: "[(]|$",
        returnBegin: true,
        excludeEnd: true,
        keywords: n2,
        relevance: 5,
        contains: [{
          begin: e2.UNDERSCORE_IDENT_RE + "\\s*\\(",
          returnBegin: true,
          relevance: 0,
          contains: [e2.UNDERSCORE_TITLE_MODE]
        }, {
          className: "type",
          begin: /</,
          end: />/,
          keywords: "reified",
          relevance: 0
        }, {
          className: "params",
          begin: /\(/,
          end: /\)/,
          endsParent: true,
          keywords: n2,
          relevance: 0,
          contains: [{
            begin: /:/,
            end: /[=,\/]/,
            endsWithParent: true,
            contains: [d2, e2.C_LINE_COMMENT_MODE, c2],
            relevance: 0
          }, e2.C_LINE_COMMENT_MODE, c2, s2, o2, r2, e2.C_NUMBER_MODE]
        }, c2]
      }, {
        begin: [/class|interface|trait/, /\s+/, e2.UNDERSCORE_IDENT_RE],
        beginScope: {
          3: "title.class"
        },
        keywords: "class interface trait",
        end: /[:\{(]|$/,
        excludeEnd: true,
        illegal: "extends implements",
        contains: [{
          beginKeywords: "public protected internal private constructor"
        }, e2.UNDERSCORE_TITLE_MODE, {
          className: "type",
          begin: /</,
          end: />/,
          excludeBegin: true,
          excludeEnd: true,
          relevance: 0
        }, {
          className: "type",
          begin: /[,:]\s*/,
          end: /[<\(,){\s]|$/,
          excludeBegin: true,
          returnEnd: true
        }, s2, o2]
      }, r2, {
        className: "meta",
        begin: "^#!/usr/bin/env",
        end: "$",
        illegal: "\n"
      }, l2]
    };
  },
  grmr_less: (e2) => {
    const n2 = te(e2), t2 = le, a2 = "[\\w-]+", i2 = "(" + a2 + "|@\\{" + a2 + "\\})", r2 = [], s2 = [], o2 = (e3) => ({
      className: "string",
      begin: "~?" + e3 + ".*?" + e3
    }), l2 = (e3, n3, t3) => ({
      className: e3,
      begin: n3,
      relevance: t3
    }), c2 = {
      $pattern: /[a-z-]+/,
      keyword: "and or not only",
      attribute: ie.join(" ")
    }, d2 = {
      begin: "\\(",
      end: "\\)",
      contains: s2,
      keywords: c2,
      relevance: 0
    };
    s2.push(e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE, o2("'"), o2('"'), n2.CSS_NUMBER_MODE, {
      begin: "(url|data-uri)\\(",
      starts: {
        className: "string",
        end: "[\\)\\n]",
        excludeEnd: true
      }
    }, n2.HEXCOLOR, d2, l2("variable", "@@?" + a2, 10), l2("variable", "@\\{" + a2 + "\\}"), l2("built_in", "~?`[^`]*?`"), {
      className: "attribute",
      begin: a2 + "\\s*:",
      end: ":",
      returnBegin: true,
      excludeEnd: true
    }, n2.IMPORTANT, { beginKeywords: "and not" }, n2.FUNCTION_DISPATCH);
    const g2 = s2.concat({
      begin: /\{/,
      end: /\}/,
      contains: r2
    }), u4 = {
      beginKeywords: "when",
      endsWithParent: true,
      contains: [{ beginKeywords: "and not" }].concat(s2)
    }, b2 = {
      begin: i2 + "\\s*:",
      returnBegin: true,
      end: /[;}]/,
      relevance: 0,
      contains: [{
        begin: /-(webkit|moz|ms|o)-/
      }, n2.CSS_VARIABLE, {
        className: "attribute",
        begin: "\\b(" + oe.join("|") + ")\\b",
        end: /(?=:)/,
        starts: { endsWithParent: true, illegal: "[<=$]", relevance: 0, contains: s2 }
      }]
    }, m2 = {
      className: "keyword",
      begin: "@(import|media|charset|font-face|(-[a-z]+-)?keyframes|supports|document|namespace|page|viewport|host)\\b",
      starts: { end: "[;{}]", keywords: c2, returnEnd: true, contains: s2, relevance: 0 }
    }, p2 = {
      className: "variable",
      variants: [{ begin: "@" + a2 + "\\s*:", relevance: 15 }, {
        begin: "@" + a2
      }],
      starts: { end: "[;}]", returnEnd: true, contains: g2 }
    }, _2 = {
      variants: [{
        begin: "[\\.#:&\\[>]",
        end: "[;{}]"
      }, { begin: i2, end: /\{/ }],
      returnBegin: true,
      returnEnd: true,
      illegal: `[<='$"]`,
      relevance: 0,
      contains: [e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE, u4, l2("keyword", "all\\b"), l2("variable", "@\\{" + a2 + "\\}"), {
        begin: "\\b(" + ae.join("|") + ")\\b",
        className: "selector-tag"
      }, n2.CSS_NUMBER_MODE, l2("selector-tag", i2, 0), l2("selector-id", "#" + i2), l2("selector-class", "\\." + i2, 0), l2("selector-tag", "&", 0), n2.ATTRIBUTE_SELECTOR_MODE, {
        className: "selector-pseudo",
        begin: ":(" + re.join("|") + ")"
      }, {
        className: "selector-pseudo",
        begin: ":(:)?(" + se.join("|") + ")"
      }, {
        begin: /\(/,
        end: /\)/,
        relevance: 0,
        contains: g2
      }, { begin: "!important" }, n2.FUNCTION_DISPATCH]
    }, h2 = {
      begin: a2 + `:(:)?(${t2.join("|")})`,
      returnBegin: true,
      contains: [_2]
    };
    return r2.push(e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE, m2, p2, h2, b2, _2, u4, n2.FUNCTION_DISPATCH), { name: "Less", case_insensitive: true, illegal: `[=>'/<($"]`, contains: r2 };
  },
  grmr_lua: (e2) => {
    const n2 = "\\[=*\\[", t2 = "\\]=*\\]", a2 = {
      begin: n2,
      end: t2,
      contains: ["self"]
    }, i2 = [e2.COMMENT("--(?!" + n2 + ")", "$"), e2.COMMENT("--" + n2, t2, {
      contains: [a2],
      relevance: 10
    })];
    return { name: "Lua", aliases: ["pluto"], keywords: {
      $pattern: e2.UNDERSCORE_IDENT_RE,
      literal: "true false nil",
      keyword: "and break do else elseif end for goto if in local not or repeat return then until while",
      built_in: "_G _ENV _VERSION __index __newindex __mode __call __metatable __tostring __len __gc __add __sub __mul __div __mod __pow __concat __unm __eq __lt __le assert collectgarbage dofile error getfenv getmetatable ipairs load loadfile loadstring module next pairs pcall print rawequal rawget rawset require select setfenv setmetatable tonumber tostring type unpack xpcall arg self coroutine resume yield status wrap create running debug getupvalue debug sethook getmetatable gethook setmetatable setlocal traceback setfenv getinfo setupvalue getlocal getregistry getfenv io lines write close flush open output type read stderr stdin input stdout popen tmpfile math log max acos huge ldexp pi cos tanh pow deg tan cosh sinh random randomseed frexp ceil floor rad abs sqrt modf asin min mod fmod log10 atan2 exp sin atan os exit setlocale date getenv difftime remove time clock tmpname rename execute package preload loadlib loaded loaders cpath config path seeall string sub upper len gfind rep find match char dump gmatch reverse byte format gsub lower table setn insert getn foreachi maxn foreach concat sort remove"
    }, contains: i2.concat([{
      className: "function",
      beginKeywords: "function",
      end: "\\)",
      contains: [e2.inherit(e2.TITLE_MODE, {
        begin: "([_a-zA-Z]\\w*\\.)*([_a-zA-Z]\\w*:)?[_a-zA-Z]\\w*"
      }), {
        className: "params",
        begin: "\\(",
        endsWithParent: true,
        contains: i2
      }].concat(i2)
    }, e2.C_NUMBER_MODE, e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE, {
      className: "string",
      begin: n2,
      end: t2,
      contains: [a2],
      relevance: 5
    }]) };
  },
  grmr_makefile: (e2) => {
    const n2 = {
      className: "variable",
      variants: [{
        begin: "\\$\\(" + e2.UNDERSCORE_IDENT_RE + "\\)",
        contains: [e2.BACKSLASH_ESCAPE]
      }, { begin: /\$[@%<?\^\+\*]/ }]
    }, t2 = {
      className: "string",
      begin: /"/,
      end: /"/,
      contains: [e2.BACKSLASH_ESCAPE, n2]
    }, a2 = {
      className: "variable",
      begin: /\$\([\w-]+\s/,
      end: /\)/,
      keywords: {
        built_in: "subst patsubst strip findstring filter filter-out sort word wordlist firstword lastword dir notdir suffix basename addsuffix addprefix join wildcard realpath abspath error warning shell origin flavor foreach if or and call eval file value"
      },
      contains: [n2, t2]
    }, i2 = { begin: "^" + e2.UNDERSCORE_IDENT_RE + "\\s*(?=[:+?]?=)" }, r2 = {
      className: "section",
      begin: /^[^\s]+:/,
      end: /$/,
      contains: [n2]
    };
    return {
      name: "Makefile",
      aliases: ["mk", "mak", "make"],
      keywords: {
        $pattern: /[\w-]+/,
        keyword: "define endef undefine ifdef ifndef ifeq ifneq else endif include -include sinclude override export unexport private vpath"
      },
      contains: [e2.HASH_COMMENT_MODE, n2, t2, a2, i2, {
        className: "meta",
        begin: /^\.PHONY:/,
        end: /$/,
        keywords: { $pattern: /[\.\w]+/, keyword: ".PHONY" }
      }, r2]
    };
  },
  grmr_markdown: (e2) => {
    const n2 = { begin: /<\/?[A-Za-z_]/, end: ">", subLanguage: "xml", relevance: 0 }, t2 = {
      variants: [{ begin: /\[.+?\]\[.*?\]/, relevance: 0 }, {
        begin: /\[.+?\]\(((data|javascript|mailto):|(?:http|ftp)s?:\/\/).*?\)/,
        relevance: 2
      }, {
        begin: e2.regex.concat(/\[.+?\]\(/, /[A-Za-z][A-Za-z0-9+.-]*/, /:\/\/.*?\)/),
        relevance: 2
      }, { begin: /\[.+?\]\([./?&#].*?\)/, relevance: 1 }, {
        begin: /\[.*?\]\(.*?\)/,
        relevance: 0
      }],
      returnBegin: true,
      contains: [{
        match: /\[(?=\])/
      }, {
        className: "string",
        relevance: 0,
        begin: "\\[",
        end: "\\]",
        excludeBegin: true,
        returnEnd: true
      }, {
        className: "link",
        relevance: 0,
        begin: "\\]\\(",
        end: "\\)",
        excludeBegin: true,
        excludeEnd: true
      }, {
        className: "symbol",
        relevance: 0,
        begin: "\\]\\[",
        end: "\\]",
        excludeBegin: true,
        excludeEnd: true
      }]
    }, a2 = {
      className: "strong",
      contains: [],
      variants: [{ begin: /_{2}(?!\s)/, end: /_{2}/ }, { begin: /\*{2}(?!\s)/, end: /\*{2}/ }]
    }, i2 = { className: "emphasis", contains: [], variants: [{ begin: /\*(?![*\s])/, end: /\*/ }, {
      begin: /_(?![_\s])/,
      end: /_/,
      relevance: 0
    }] }, r2 = e2.inherit(a2, {
      contains: []
    }), s2 = e2.inherit(i2, { contains: [] });
    a2.contains.push(s2), i2.contains.push(r2);
    let o2 = [n2, t2];
    return [a2, i2, r2, s2].forEach(((e3) => {
      e3.contains = e3.contains.concat(o2);
    })), o2 = o2.concat(a2, i2), { name: "Markdown", aliases: ["md", "mkdown", "mkd"], contains: [{
      className: "section",
      variants: [{ begin: "^#{1,6}", end: "$", contains: o2 }, {
        begin: "(?=^.+?\\n[=-]{2,}$)",
        contains: [{ begin: "^[=-]*$" }, {
          begin: "^",
          end: "\\n",
          contains: o2
        }]
      }]
    }, n2, {
      className: "bullet",
      begin: "^[ 	]*([*+-]|(\\d+\\.))(?=\\s+)",
      end: "\\s+",
      excludeEnd: true
    }, a2, i2, {
      className: "quote",
      begin: "^>\\s+",
      contains: o2,
      end: "$"
    }, { className: "code", variants: [{ begin: "(`{3,})[^`](.|\\n)*?\\1`*[ ]*" }, {
      begin: "(~{3,})[^~](.|\\n)*?\\1~*[ ]*"
    }, { begin: "```", end: "```+[ ]*$" }, {
      begin: "~~~",
      end: "~~~+[ ]*$"
    }, { begin: "`.+?`" }, {
      begin: "(?=^( {4}|\\t))",
      contains: [{ begin: "^( {4}|\\t)", end: "(\\n)$" }],
      relevance: 0
    }] }, {
      begin: "^[-\\*]{3,}",
      end: "$"
    }, t2, { begin: /^\[[^\n]+\]:/, returnBegin: true, contains: [{
      className: "symbol",
      begin: /\[/,
      end: /\]/,
      excludeBegin: true,
      excludeEnd: true
    }, {
      className: "link",
      begin: /:\s*/,
      end: /$/,
      excludeBegin: true
    }] }, {
      scope: "literal",
      match: /&([a-zA-Z0-9]+|#[0-9]{1,7}|#[Xx][0-9a-fA-F]{1,6});/
    }] };
  },
  grmr_objectivec: (e2) => {
    const n2 = /[a-zA-Z@][a-zA-Z0-9_]*/, t2 = {
      $pattern: n2,
      keyword: ["@interface", "@class", "@protocol", "@implementation"]
    };
    return {
      name: "Objective-C",
      aliases: ["mm", "objc", "obj-c", "obj-c++", "objective-c++"],
      keywords: {
        "variable.language": ["this", "super"],
        $pattern: n2,
        keyword: ["while", "export", "sizeof", "typedef", "const", "struct", "for", "union", "volatile", "static", "mutable", "if", "do", "return", "goto", "enum", "else", "break", "extern", "asm", "case", "default", "register", "explicit", "typename", "switch", "continue", "inline", "readonly", "assign", "readwrite", "self", "@synchronized", "id", "typeof", "nonatomic", "IBOutlet", "IBAction", "strong", "weak", "copy", "in", "out", "inout", "bycopy", "byref", "oneway", "__strong", "__weak", "__block", "__autoreleasing", "@private", "@protected", "@public", "@try", "@property", "@end", "@throw", "@catch", "@finally", "@autoreleasepool", "@synthesize", "@dynamic", "@selector", "@optional", "@required", "@encode", "@package", "@import", "@defs", "@compatibility_alias", "__bridge", "__bridge_transfer", "__bridge_retained", "__bridge_retain", "__covariant", "__contravariant", "__kindof", "_Nonnull", "_Nullable", "_Null_unspecified", "__FUNCTION__", "__PRETTY_FUNCTION__", "__attribute__", "getter", "setter", "retain", "unsafe_unretained", "nonnull", "nullable", "null_unspecified", "null_resettable", "class", "instancetype", "NS_DESIGNATED_INITIALIZER", "NS_UNAVAILABLE", "NS_REQUIRES_SUPER", "NS_RETURNS_INNER_POINTER", "NS_INLINE", "NS_AVAILABLE", "NS_DEPRECATED", "NS_ENUM", "NS_OPTIONS", "NS_SWIFT_UNAVAILABLE", "NS_ASSUME_NONNULL_BEGIN", "NS_ASSUME_NONNULL_END", "NS_REFINED_FOR_SWIFT", "NS_SWIFT_NAME", "NS_SWIFT_NOTHROW", "NS_DURING", "NS_HANDLER", "NS_ENDHANDLER", "NS_VALUERETURN", "NS_VOIDRETURN"],
        literal: ["false", "true", "FALSE", "TRUE", "nil", "YES", "NO", "NULL"],
        built_in: ["dispatch_once_t", "dispatch_queue_t", "dispatch_sync", "dispatch_async", "dispatch_once"],
        type: ["int", "float", "char", "unsigned", "signed", "short", "long", "double", "wchar_t", "unichar", "void", "bool", "BOOL", "id|0", "_Bool"]
      },
      illegal: "</",
      contains: [{
        className: "built_in",
        begin: "\\b(AV|CA|CF|CG|CI|CL|CM|CN|CT|MK|MP|MTK|MTL|NS|SCN|SK|UI|WK|XC)\\w+"
      }, e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE, e2.C_NUMBER_MODE, e2.QUOTE_STRING_MODE, e2.APOS_STRING_MODE, {
        className: "string",
        variants: [{
          begin: '@"',
          end: '"',
          illegal: "\\n",
          contains: [e2.BACKSLASH_ESCAPE]
        }]
      }, {
        className: "meta",
        begin: /#\s*[a-z]+\b/,
        end: /$/,
        keywords: {
          keyword: "if else elif endif define undef warning error line pragma ifdef ifndef include"
        },
        contains: [{ begin: /\\\n/, relevance: 0 }, e2.inherit(e2.QUOTE_STRING_MODE, {
          className: "string"
        }), {
          className: "string",
          begin: /<.*?>/,
          end: /$/,
          illegal: "\\n"
        }, e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE]
      }, {
        className: "class",
        begin: "(" + t2.keyword.join("|") + ")\\b",
        end: /(\{|$)/,
        excludeEnd: true,
        keywords: t2,
        contains: [e2.UNDERSCORE_TITLE_MODE]
      }, {
        begin: "\\." + e2.UNDERSCORE_IDENT_RE,
        relevance: 0
      }]
    };
  },
  grmr_perl: (e2) => {
    const n2 = e2.regex, t2 = /[dualxmsipngr]{0,12}/, a2 = {
      $pattern: /[\w.]+/,
      keyword: "abs accept alarm and atan2 bind binmode bless break caller chdir chmod chomp chop chown chr chroot class close closedir connect continue cos crypt dbmclose dbmopen defined delete die do dump each else elsif endgrent endhostent endnetent endprotoent endpwent endservent eof eval exec exists exit exp fcntl field fileno flock for foreach fork format formline getc getgrent getgrgid getgrnam gethostbyaddr gethostbyname gethostent getlogin getnetbyaddr getnetbyname getnetent getpeername getpgrp getpriority getprotobyname getprotobynumber getprotoent getpwent getpwnam getpwuid getservbyname getservbyport getservent getsockname getsockopt given glob gmtime goto grep gt hex if index int ioctl join keys kill last lc lcfirst length link listen local localtime log lstat lt ma map method mkdir msgctl msgget msgrcv msgsnd my ne next no not oct open opendir or ord our pack package pipe pop pos print printf prototype push q|0 qq quotemeta qw qx rand read readdir readline readlink readpipe recv redo ref rename require reset return reverse rewinddir rindex rmdir say scalar seek seekdir select semctl semget semop send setgrent sethostent setnetent setpgrp setpriority setprotoent setpwent setservent setsockopt shift shmctl shmget shmread shmwrite shutdown sin sleep socket socketpair sort splice split sprintf sqrt srand stat state study sub substr symlink syscall sysopen sysread sysseek system syswrite tell telldir tie tied time times tr truncate uc ucfirst umask undef unless unlink unpack unshift untie until use utime values vec wait waitpid wantarray warn when while write x|0 xor y|0"
    }, i2 = { className: "subst", begin: "[$@]\\{", end: "\\}", keywords: a2 }, r2 = {
      begin: /->\{/,
      end: /\}/
    }, s2 = { scope: "attr", match: /\s+:\s*\w+(\s*\(.*?\))?/ }, o2 = {
      scope: "variable",
      variants: [{ begin: /\$\d/ }, {
        begin: n2.concat(/[$%@](?!")(\^\w\b|#\w+(::\w+)*|\{\w+\}|\w+(::\w*)*)/, "(?![A-Za-z])(?![@$%])")
      }, { begin: /[$%@](?!")[^\s\w{=]|\$=/, relevance: 0 }],
      contains: [s2]
    }, l2 = {
      className: "number",
      variants: [{ match: /0?\.[0-9][0-9_]+\b/ }, {
        match: /\bv?(0|[1-9][0-9_]*(\.[0-9_]+)?|[1-9][0-9_]*)\b/
      }, {
        match: /\b0[0-7][0-7_]*\b/
      }, { match: /\b0x[0-9a-fA-F][0-9a-fA-F_]*\b/ }, {
        match: /\b0b[0-1][0-1_]*\b/
      }],
      relevance: 0
    }, c2 = [e2.BACKSLASH_ESCAPE, i2, o2], d2 = [/!/, /\//, /\|/, /\?/, /'/, /"/, /#/], g2 = (e3, a3, i3 = "\\1") => {
      const r3 = "\\1" === i3 ? i3 : n2.concat(i3, a3);
      return n2.concat(n2.concat("(?:", e3, ")"), a3, /(?:\\.|[^\\\/])*?/, r3, /(?:\\.|[^\\\/])*?/, i3, t2);
    }, u4 = (e3, a3, i3) => n2.concat(n2.concat("(?:", e3, ")"), a3, /(?:\\.|[^\\\/])*?/, i3, t2), b2 = [o2, e2.HASH_COMMENT_MODE, e2.COMMENT(/^=\w/, /=cut/, {
      endsWithParent: true
    }), r2, { className: "string", contains: c2, variants: [{
      begin: "q[qwxr]?\\s*\\(",
      end: "\\)",
      relevance: 5
    }, {
      begin: "q[qwxr]?\\s*\\[",
      end: "\\]",
      relevance: 5
    }, { begin: "q[qwxr]?\\s*\\{", end: "\\}", relevance: 5 }, {
      begin: "q[qwxr]?\\s*\\|",
      end: "\\|",
      relevance: 5
    }, {
      begin: "q[qwxr]?\\s*<",
      end: ">",
      relevance: 5
    }, { begin: "qw\\s+q", end: "q", relevance: 5 }, {
      begin: "'",
      end: "'",
      contains: [e2.BACKSLASH_ESCAPE]
    }, { begin: '"', end: '"' }, {
      begin: "`",
      end: "`",
      contains: [e2.BACKSLASH_ESCAPE]
    }, { begin: /\{\w+\}/, relevance: 0 }, {
      begin: "-?\\w+\\s*=>",
      relevance: 0
    }] }, l2, {
      begin: "(\\/\\/|" + e2.RE_STARTERS_RE + "|\\b(split|return|print|reverse|grep)\\b)\\s*",
      keywords: "split return print reverse grep",
      relevance: 0,
      contains: [e2.HASH_COMMENT_MODE, { className: "regexp", variants: [{
        begin: g2("s|tr|y", n2.either(...d2, { capture: true }))
      }, { begin: g2("s|tr|y", "\\(", "\\)") }, {
        begin: g2("s|tr|y", "\\[", "\\]")
      }, { begin: g2("s|tr|y", "\\{", "\\}") }], relevance: 2 }, {
        className: "regexp",
        variants: [{ begin: /(m|qr)\/\//, relevance: 0 }, {
          begin: u4("(?:m|qr)?", /\//, /\//)
        }, { begin: u4("m|qr", n2.either(...d2, {
          capture: true
        }), /\1/) }, { begin: u4("m|qr", /\(/, /\)/) }, { begin: u4("m|qr", /\[/, /\]/) }, {
          begin: u4("m|qr", /\{/, /\}/)
        }]
      }]
    }, {
      className: "function",
      beginKeywords: "sub method",
      end: "(\\s*\\(.*?\\))?[;{]",
      excludeEnd: true,
      relevance: 5,
      contains: [e2.TITLE_MODE, s2]
    }, {
      className: "class",
      beginKeywords: "class",
      end: "[;{]",
      excludeEnd: true,
      relevance: 5,
      contains: [e2.TITLE_MODE, s2, l2]
    }, { begin: "-\\w\\b", relevance: 0 }, {
      begin: "^__DATA__$",
      end: "^__END__$",
      subLanguage: "mojolicious",
      contains: [{
        begin: "^@@.*",
        end: "$",
        className: "comment"
      }]
    }];
    return i2.contains = b2, r2.contains = b2, {
      name: "Perl",
      aliases: ["pl", "pm"],
      keywords: a2,
      contains: b2
    };
  },
  grmr_php: (e2) => {
    const n2 = e2.regex, t2 = /(?![A-Za-z0-9])(?![$])/, a2 = n2.concat(/[a-zA-Z_\x7f-\xff][a-zA-Z0-9_\x7f-\xff]*/, t2), i2 = n2.concat(/(\\?[A-Z][a-z0-9_\x7f-\xff]+|\\?[A-Z]+(?=[A-Z][a-z0-9_\x7f-\xff])){1,}/, t2), r2 = n2.concat(/[A-Z]+/, t2), s2 = {
      scope: "variable",
      match: "\\$+" + a2
    }, o2 = { scope: "subst", variants: [{ begin: /\$\w+/ }, {
      begin: /\{\$/,
      end: /\}/
    }] }, l2 = e2.inherit(e2.APOS_STRING_MODE, {
      illegal: null
    }), c2 = "[ 	\n]", d2 = { scope: "string", variants: [e2.inherit(e2.QUOTE_STRING_MODE, {
      illegal: null,
      contains: e2.QUOTE_STRING_MODE.contains.concat(o2)
    }), l2, {
      begin: /<<<[ \t]*(?:(\w+)|"(\w+)")\n/,
      end: /[ \t]*(\w+)\b/,
      contains: e2.QUOTE_STRING_MODE.contains.concat(o2),
      "on:begin": (e3, n3) => {
        n3.data._beginMatch = e3[1] || e3[2];
      },
      "on:end": (e3, n3) => {
        n3.data._beginMatch !== e3[1] && n3.ignoreMatch();
      }
    }, e2.END_SAME_AS_BEGIN({
      begin: /<<<[ \t]*'(\w+)'\n/,
      end: /[ \t]*(\w+)\b/
    })] }, g2 = {
      scope: "number",
      variants: [{
        begin: "\\b0[bB][01]+(?:_[01]+)*\\b"
      }, { begin: "\\b0[oO][0-7]+(?:_[0-7]+)*\\b" }, {
        begin: "\\b0[xX][\\da-fA-F]+(?:_[\\da-fA-F]+)*\\b"
      }, {
        begin: "(?:\\b\\d+(?:_\\d+)*(\\.(?:\\d+(?:_\\d+)*))?|\\B\\.\\d+)(?:[eE][+-]?\\d+)?"
      }],
      relevance: 0
    }, u4 = ["false", "null", "true"], b2 = ["__CLASS__", "__DIR__", "__FILE__", "__FUNCTION__", "__COMPILER_HALT_OFFSET__", "__LINE__", "__METHOD__", "__NAMESPACE__", "__TRAIT__", "die", "echo", "exit", "include", "include_once", "print", "require", "require_once", "array", "abstract", "and", "as", "binary", "bool", "boolean", "break", "callable", "case", "catch", "class", "clone", "const", "continue", "declare", "default", "do", "double", "else", "elseif", "empty", "enddeclare", "endfor", "endforeach", "endif", "endswitch", "endwhile", "enum", "eval", "extends", "final", "finally", "float", "for", "foreach", "from", "global", "goto", "if", "implements", "instanceof", "insteadof", "int", "integer", "interface", "isset", "iterable", "list", "match|0", "mixed", "new", "never", "object", "or", "private", "protected", "public", "readonly", "real", "return", "string", "switch", "throw", "trait", "try", "unset", "use", "var", "void", "while", "xor", "yield"], m2 = ["Error|0", "AppendIterator", "ArgumentCountError", "ArithmeticError", "ArrayIterator", "ArrayObject", "AssertionError", "BadFunctionCallException", "BadMethodCallException", "CachingIterator", "CallbackFilterIterator", "CompileError", "Countable", "DirectoryIterator", "DivisionByZeroError", "DomainException", "EmptyIterator", "ErrorException", "Exception", "FilesystemIterator", "FilterIterator", "GlobIterator", "InfiniteIterator", "InvalidArgumentException", "IteratorIterator", "LengthException", "LimitIterator", "LogicException", "MultipleIterator", "NoRewindIterator", "OutOfBoundsException", "OutOfRangeException", "OuterIterator", "OverflowException", "ParentIterator", "ParseError", "RangeException", "RecursiveArrayIterator", "RecursiveCachingIterator", "RecursiveCallbackFilterIterator", "RecursiveDirectoryIterator", "RecursiveFilterIterator", "RecursiveIterator", "RecursiveIteratorIterator", "RecursiveRegexIterator", "RecursiveTreeIterator", "RegexIterator", "RuntimeException", "SeekableIterator", "SplDoublyLinkedList", "SplFileInfo", "SplFileObject", "SplFixedArray", "SplHeap", "SplMaxHeap", "SplMinHeap", "SplObjectStorage", "SplObserver", "SplPriorityQueue", "SplQueue", "SplStack", "SplSubject", "SplTempFileObject", "TypeError", "UnderflowException", "UnexpectedValueException", "UnhandledMatchError", "ArrayAccess", "BackedEnum", "Closure", "Fiber", "Generator", "Iterator", "IteratorAggregate", "Serializable", "Stringable", "Throwable", "Traversable", "UnitEnum", "WeakReference", "WeakMap", "Directory", "__PHP_Incomplete_Class", "parent", "php_user_filter", "self", "static", "stdClass"], p2 = {
      keyword: b2,
      literal: ((e3) => {
        const n3 = [];
        return e3.forEach(((e4) => {
          n3.push(e4), e4.toLowerCase() === e4 ? n3.push(e4.toUpperCase()) : n3.push(e4.toLowerCase());
        })), n3;
      })(u4),
      built_in: m2
    }, _2 = (e3) => e3.map(((e4) => e4.replace(/\|\d+$/, ""))), h2 = { variants: [{
      match: [/new/, n2.concat(c2, "+"), n2.concat("(?!", _2(m2).join("\\b|"), "\\b)"), i2],
      scope: {
        1: "keyword",
        4: "title.class"
      }
    }] }, f2 = n2.concat(a2, "\\b(?!\\()"), E2 = { variants: [{
      match: [n2.concat(/::/, n2.lookahead(/(?!class\b)/)), f2],
      scope: {
        2: "variable.constant"
      }
    }, { match: [/::/, /class/], scope: { 2: "variable.language" } }, {
      match: [i2, n2.concat(/::/, n2.lookahead(/(?!class\b)/)), f2],
      scope: {
        1: "title.class",
        3: "variable.constant"
      }
    }, {
      match: [i2, n2.concat("::", n2.lookahead(/(?!class\b)/))],
      scope: { 1: "title.class" }
    }, { match: [i2, /::/, /class/], scope: {
      1: "title.class",
      3: "variable.language"
    } }] }, y3 = {
      scope: "attr",
      match: n2.concat(a2, n2.lookahead(":"), n2.lookahead(/(?!::)/))
    }, w2 = {
      relevance: 0,
      begin: /\(/,
      end: /\)/,
      keywords: p2,
      contains: [y3, s2, E2, e2.C_BLOCK_COMMENT_MODE, d2, g2, h2]
    }, v2 = {
      relevance: 0,
      match: [/\b/, n2.concat("(?!fn\\b|function\\b|", _2(b2).join("\\b|"), "|", _2(m2).join("\\b|"), "\\b)"), a2, n2.concat(c2, "*"), n2.lookahead(/(?=\()/)],
      scope: { 3: "title.function.invoke" },
      contains: [w2]
    };
    w2.contains.push(v2);
    const N2 = [y3, E2, e2.C_BLOCK_COMMENT_MODE, d2, g2, h2], k2 = {
      begin: n2.concat(/#\[\s*\\?/, n2.either(i2, r2)),
      beginScope: "meta",
      end: /]/,
      endScope: "meta",
      keywords: { literal: u4, keyword: ["new", "array"] },
      contains: [{
        begin: /\[/,
        end: /]/,
        keywords: { literal: u4, keyword: ["new", "array"] },
        contains: ["self", ...N2]
      }, ...N2, { scope: "meta", variants: [{ match: i2 }, { match: r2 }] }]
    };
    return {
      case_insensitive: false,
      keywords: p2,
      contains: [k2, e2.HASH_COMMENT_MODE, e2.COMMENT("//", "$"), e2.COMMENT("/\\*", "\\*/", {
        contains: [{ scope: "doctag", match: "@[A-Za-z]+" }]
      }), {
        match: /__halt_compiler\(\);/,
        keywords: "__halt_compiler",
        starts: {
          scope: "comment",
          end: e2.MATCH_NOTHING_RE,
          contains: [{ match: /\?>/, scope: "meta", endsParent: true }]
        }
      }, { scope: "meta", variants: [{
        begin: /<\?php/,
        relevance: 10
      }, { begin: /<\?=/ }, { begin: /<\?/, relevance: 0.1 }, {
        begin: /\?>/
      }] }, { scope: "variable.language", match: /\$this\b/ }, s2, v2, E2, {
        match: [/const/, /\s/, a2],
        scope: { 1: "keyword", 3: "variable.constant" }
      }, h2, {
        scope: "function",
        relevance: 0,
        beginKeywords: "fn function",
        end: /[;{]/,
        excludeEnd: true,
        illegal: "[$%\\[]",
        contains: [{
          beginKeywords: "use"
        }, e2.UNDERSCORE_TITLE_MODE, { begin: "=>", endsParent: true }, {
          scope: "params",
          begin: "\\(",
          end: "\\)",
          excludeBegin: true,
          excludeEnd: true,
          keywords: p2,
          contains: ["self", k2, s2, E2, e2.C_BLOCK_COMMENT_MODE, d2, g2]
        }]
      }, { scope: "class", variants: [{
        beginKeywords: "enum",
        illegal: /[($"]/
      }, {
        beginKeywords: "class interface trait",
        illegal: /[:($"]/
      }], relevance: 0, end: /\{/, excludeEnd: true, contains: [{
        beginKeywords: "extends implements"
      }, e2.UNDERSCORE_TITLE_MODE] }, {
        beginKeywords: "namespace",
        relevance: 0,
        end: ";",
        illegal: /[.']/,
        contains: [e2.inherit(e2.UNDERSCORE_TITLE_MODE, { scope: "title.class" })]
      }, {
        beginKeywords: "use",
        relevance: 0,
        end: ";",
        contains: [{
          match: /\b(as|const|function)\b/,
          scope: "keyword"
        }, e2.UNDERSCORE_TITLE_MODE]
      }, d2, g2]
    };
  },
  grmr_php_template: (e2) => ({ name: "PHP template", subLanguage: "xml", contains: [{
    begin: /<\?(php|=)?/,
    end: /\?>/,
    subLanguage: "php",
    contains: [{
      begin: "/\\*",
      end: "\\*/",
      skip: true
    }, { begin: 'b"', end: '"', skip: true }, {
      begin: "b'",
      end: "'",
      skip: true
    }, e2.inherit(e2.APOS_STRING_MODE, {
      illegal: null,
      className: null,
      contains: null,
      skip: true
    }), e2.inherit(e2.QUOTE_STRING_MODE, {
      illegal: null,
      className: null,
      contains: null,
      skip: true
    })]
  }] }),
  grmr_plaintext: (e2) => ({
    name: "Plain text",
    aliases: ["text", "txt"],
    disableAutodetect: true
  }),
  grmr_python: (e2) => {
    const n2 = e2.regex, t2 = new RegExp("[\\p{XID_Start}_]\\p{XID_Continue}*", "u"), a2 = ["and", "as", "assert", "async", "await", "break", "case", "class", "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "match", "nonlocal|10", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"], i2 = {
      $pattern: /[A-Za-z]\w+|__\w+__/,
      keyword: a2,
      built_in: ["__import__", "abs", "all", "any", "ascii", "bin", "bool", "breakpoint", "bytearray", "bytes", "callable", "chr", "classmethod", "compile", "complex", "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter", "float", "format", "frozenset", "getattr", "globals", "hasattr", "hash", "help", "hex", "id", "input", "int", "isinstance", "issubclass", "iter", "len", "list", "locals", "map", "max", "memoryview", "min", "next", "object", "oct", "open", "ord", "pow", "print", "property", "range", "repr", "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple", "type", "vars", "zip"],
      literal: ["__debug__", "Ellipsis", "False", "None", "NotImplemented", "True"],
      type: ["Any", "Callable", "Coroutine", "Dict", "List", "Literal", "Generic", "Optional", "Sequence", "Set", "Tuple", "Type", "Union"]
    }, r2 = { className: "meta", begin: /^(>>>|\.\.\.) / }, s2 = {
      className: "subst",
      begin: /\{/,
      end: /\}/,
      keywords: i2,
      illegal: /#/
    }, o2 = { begin: /\{\{/, relevance: 0 }, l2 = {
      className: "string",
      contains: [e2.BACKSLASH_ESCAPE],
      variants: [{
        begin: /([uU]|[bB]|[rR]|[bB][rR]|[rR][bB])?'''/,
        end: /'''/,
        contains: [e2.BACKSLASH_ESCAPE, r2],
        relevance: 10
      }, {
        begin: /([uU]|[bB]|[rR]|[bB][rR]|[rR][bB])?"""/,
        end: /"""/,
        contains: [e2.BACKSLASH_ESCAPE, r2],
        relevance: 10
      }, {
        begin: /([fF][rR]|[rR][fF]|[fF])'''/,
        end: /'''/,
        contains: [e2.BACKSLASH_ESCAPE, r2, o2, s2]
      }, {
        begin: /([fF][rR]|[rR][fF]|[fF])"""/,
        end: /"""/,
        contains: [e2.BACKSLASH_ESCAPE, r2, o2, s2]
      }, {
        begin: /([uU]|[rR])'/,
        end: /'/,
        relevance: 10
      }, { begin: /([uU]|[rR])"/, end: /"/, relevance: 10 }, {
        begin: /([bB]|[bB][rR]|[rR][bB])'/,
        end: /'/
      }, {
        begin: /([bB]|[bB][rR]|[rR][bB])"/,
        end: /"/
      }, {
        begin: /([fF][rR]|[rR][fF]|[fF])'/,
        end: /'/,
        contains: [e2.BACKSLASH_ESCAPE, o2, s2]
      }, {
        begin: /([fF][rR]|[rR][fF]|[fF])"/,
        end: /"/,
        contains: [e2.BACKSLASH_ESCAPE, o2, s2]
      }, e2.APOS_STRING_MODE, e2.QUOTE_STRING_MODE]
    }, c2 = "[0-9](_?[0-9])*", d2 = `(\\b(${c2}))?\\.(${c2})|\\b(${c2})\\.`, g2 = "\\b|" + a2.join("|"), u4 = {
      className: "number",
      relevance: 0,
      variants: [{
        begin: `(\\b(${c2})|(${d2}))[eE][+-]?(${c2})[jJ]?(?=${g2})`
      }, { begin: `(${d2})[jJ]?` }, {
        begin: `\\b([1-9](_?[0-9])*|0+(_?0)*)[lLjJ]?(?=${g2})`
      }, {
        begin: `\\b0[bB](_?[01])+[lL]?(?=${g2})`
      }, {
        begin: `\\b0[oO](_?[0-7])+[lL]?(?=${g2})`
      }, { begin: `\\b0[xX](_?[0-9a-fA-F])+[lL]?(?=${g2})` }, {
        begin: `\\b(${c2})[jJ](?=${g2})`
      }]
    }, b2 = {
      className: "comment",
      begin: n2.lookahead(/# type:/),
      end: /$/,
      keywords: i2,
      contains: [{ begin: /# type:/ }, { begin: /#/, end: /\b\B/, endsWithParent: true }]
    }, m2 = {
      className: "params",
      variants: [{ className: "", begin: /\(\s*\)/, skip: true }, {
        begin: /\(/,
        end: /\)/,
        excludeBegin: true,
        excludeEnd: true,
        keywords: i2,
        contains: ["self", r2, u4, l2, e2.HASH_COMMENT_MODE]
      }]
    };
    return s2.contains = [l2, u4, r2], {
      name: "Python",
      aliases: ["py", "gyp", "ipython"],
      unicodeRegex: true,
      keywords: i2,
      illegal: /(<\/|\?)|=>/,
      contains: [r2, u4, {
        scope: "variable.language",
        match: /\bself\b/
      }, { beginKeywords: "if", relevance: 0 }, {
        match: /\bor\b/,
        scope: "keyword"
      }, l2, b2, e2.HASH_COMMENT_MODE, { match: [/\bdef/, /\s+/, t2], scope: {
        1: "keyword",
        3: "title.function"
      }, contains: [m2] }, {
        variants: [{
          match: [/\bclass/, /\s+/, t2, /\s*/, /\(\s*/, t2, /\s*\)/]
        }, { match: [/\bclass/, /\s+/, t2] }],
        scope: { 1: "keyword", 3: "title.class", 6: "title.class.inherited" }
      }, {
        className: "meta",
        begin: /^[\t ]*@/,
        end: /(?=#)|$/,
        contains: [u4, m2, l2]
      }]
    };
  },
  grmr_python_repl: (e2) => ({ aliases: ["pycon"], contains: [{
    className: "meta.prompt",
    starts: { end: / |$/, starts: { end: "$", subLanguage: "python" } },
    variants: [{
      begin: /^>>>(?=[ ]|$)/
    }, { begin: /^\.\.\.(?=[ ]|$)/ }]
  }] }),
  grmr_r: (e2) => {
    const n2 = e2.regex, t2 = /(?:(?:[a-zA-Z]|\.[._a-zA-Z])[._a-zA-Z0-9]*)|\.(?!\d)/, a2 = n2.either(/0[xX][0-9a-fA-F]+\.[0-9a-fA-F]*[pP][+-]?\d+i?/, /0[xX][0-9a-fA-F]+(?:[pP][+-]?\d+)?[Li]?/, /(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[Li]?/), i2 = /[=!<>:]=|\|\||&&|:::?|<-|<<-|->>|->|\|>|[-+*\/?!$&|:<=>@^~]|\*\*/, r2 = n2.either(/[()]/, /[{}]/, /\[\[/, /[[\]]/, /\\/, /,/);
    return { name: "R", keywords: {
      $pattern: t2,
      keyword: "function if in break next repeat else for while",
      literal: "NULL NA TRUE FALSE Inf NaN NA_integer_|10 NA_real_|10 NA_character_|10 NA_complex_|10",
      built_in: "LETTERS letters month.abb month.name pi T F abs acos acosh all any anyNA Arg as.call as.character as.complex as.double as.environment as.integer as.logical as.null.default as.numeric as.raw asin asinh atan atanh attr attributes baseenv browser c call ceiling class Conj cos cosh cospi cummax cummin cumprod cumsum digamma dim dimnames emptyenv exp expression floor forceAndCall gamma gc.time globalenv Im interactive invisible is.array is.atomic is.call is.character is.complex is.double is.environment is.expression is.finite is.function is.infinite is.integer is.language is.list is.logical is.matrix is.na is.name is.nan is.null is.numeric is.object is.pairlist is.raw is.recursive is.single is.symbol lazyLoadDBfetch length lgamma list log max min missing Mod names nargs nzchar oldClass on.exit pos.to.env proc.time prod quote range Re rep retracemem return round seq_along seq_len seq.int sign signif sin sinh sinpi sqrt standardGeneric substitute sum switch tan tanh tanpi tracemem trigamma trunc unclass untracemem UseMethod xtfrm"
    }, contains: [e2.COMMENT(/#'/, /$/, {
      contains: [{
        scope: "doctag",
        match: /@examples/,
        starts: {
          end: n2.lookahead(n2.either(/\n^#'\s*(?=@[a-zA-Z]+)/, /\n^(?!#')/)),
          endsParent: true
        }
      }, { scope: "doctag", begin: "@param", end: /$/, contains: [{
        scope: "variable",
        variants: [{ match: t2 }, { match: /`(?:\\.|[^`\\])+`/ }],
        endsParent: true
      }] }, { scope: "doctag", match: /@[a-zA-Z]+/ }, { scope: "keyword", match: /\\[a-zA-Z]+/ }]
    }), e2.HASH_COMMENT_MODE, {
      scope: "string",
      contains: [e2.BACKSLASH_ESCAPE],
      variants: [e2.END_SAME_AS_BEGIN({
        begin: /[rR]"(-*)\(/,
        end: /\)(-*)"/
      }), e2.END_SAME_AS_BEGIN({
        begin: /[rR]"(-*)\{/,
        end: /\}(-*)"/
      }), e2.END_SAME_AS_BEGIN({
        begin: /[rR]"(-*)\[/,
        end: /\](-*)"/
      }), e2.END_SAME_AS_BEGIN({
        begin: /[rR]'(-*)\(/,
        end: /\)(-*)'/
      }), e2.END_SAME_AS_BEGIN({
        begin: /[rR]'(-*)\{/,
        end: /\}(-*)'/
      }), e2.END_SAME_AS_BEGIN({ begin: /[rR]'(-*)\[/, end: /\](-*)'/ }), {
        begin: '"',
        end: '"',
        relevance: 0
      }, { begin: "'", end: "'", relevance: 0 }]
    }, { relevance: 0, variants: [{ scope: {
      1: "operator",
      2: "number"
    }, match: [i2, a2] }, {
      scope: { 1: "operator", 2: "number" },
      match: [/%[^%]*%/, a2]
    }, { scope: { 1: "punctuation", 2: "number" }, match: [r2, a2] }, { scope: {
      2: "number"
    }, match: [/[^a-zA-Z0-9._]|^/, a2] }] }, {
      scope: { 3: "operator" },
      match: [t2, /\s+/, /<-/, /\s+/]
    }, { scope: "operator", relevance: 0, variants: [{ match: i2 }, {
      match: /%[^%]*%/
    }] }, { scope: "punctuation", relevance: 0, match: r2 }, {
      begin: "`",
      end: "`",
      contains: [{ begin: /\\./ }]
    }] };
  },
  grmr_ruby: (e2) => {
    const n2 = e2.regex, t2 = "([a-zA-Z_]\\w*[!?=]?|[-+~]@|<<|>>|=~|===?|<=>|[<>]=?|\\*\\*|[-/+%^&*~`|]|\\[\\]=?)", a2 = n2.either(/\b([A-Z]+[a-z0-9]+)+/, /\b([A-Z]+[a-z0-9]+)+[A-Z]+/), i2 = n2.concat(a2, /(::\w+)*/), r2 = {
      "variable.constant": ["__FILE__", "__LINE__", "__ENCODING__"],
      "variable.language": ["self", "super"],
      keyword: ["alias", "and", "begin", "BEGIN", "break", "case", "class", "defined", "do", "else", "elsif", "end", "END", "ensure", "for", "if", "in", "module", "next", "not", "or", "redo", "require", "rescue", "retry", "return", "then", "undef", "unless", "until", "when", "while", "yield", "include", "extend", "prepend", "public", "private", "protected", "raise", "throw"],
      built_in: ["proc", "lambda", "attr_accessor", "attr_reader", "attr_writer", "define_method", "private_constant", "module_function"],
      literal: ["true", "false", "nil"]
    }, s2 = { className: "doctag", begin: "@[A-Za-z]+" }, o2 = {
      begin: "#<",
      end: ">"
    }, l2 = [e2.COMMENT("#", "$", {
      contains: [s2]
    }), e2.COMMENT("^=begin", "^=end", {
      contains: [s2],
      relevance: 10
    }), e2.COMMENT("^__END__", e2.MATCH_NOTHING_RE)], c2 = {
      className: "subst",
      begin: /#\{/,
      end: /\}/,
      keywords: r2
    }, d2 = {
      className: "string",
      contains: [e2.BACKSLASH_ESCAPE, c2],
      variants: [{ begin: /'/, end: /'/ }, { begin: /"/, end: /"/ }, { begin: /`/, end: /`/ }, {
        begin: /%[qQwWx]?\(/,
        end: /\)/
      }, { begin: /%[qQwWx]?\[/, end: /\]/ }, {
        begin: /%[qQwWx]?\{/,
        end: /\}/
      }, { begin: /%[qQwWx]?</, end: />/ }, {
        begin: /%[qQwWx]?\//,
        end: /\//
      }, { begin: /%[qQwWx]?%/, end: /%/ }, { begin: /%[qQwWx]?-/, end: /-/ }, {
        begin: /%[qQwWx]?\|/,
        end: /\|/
      }, { begin: /\B\?(\\\d{1,3})/ }, {
        begin: /\B\?(\\x[A-Fa-f0-9]{1,2})/
      }, { begin: /\B\?(\\u\{?[A-Fa-f0-9]{1,6}\}?)/ }, {
        begin: /\B\?(\\M-\\C-|\\M-\\c|\\c\\M-|\\M-|\\C-\\M-)[\x20-\x7e]/
      }, {
        begin: /\B\?\\(c|C-)[\x20-\x7e]/
      }, { begin: /\B\?\\?\S/ }, {
        begin: n2.concat(/<<[-~]?'?/, n2.lookahead(/(\w+)(?=\W)[^\n]*\n(?:[^\n]*\n)*?\s*\1\b/)),
        contains: [e2.END_SAME_AS_BEGIN({
          begin: /(\w+)/,
          end: /(\w+)/,
          contains: [e2.BACKSLASH_ESCAPE, c2]
        })]
      }]
    }, g2 = "[0-9](_?[0-9])*", u4 = {
      className: "number",
      relevance: 0,
      variants: [{
        begin: `\\b([1-9](_?[0-9])*|0)(\\.(${g2}))?([eE][+-]?(${g2})|r)?i?\\b`
      }, {
        begin: "\\b0[dD][0-9](_?[0-9])*r?i?\\b"
      }, {
        begin: "\\b0[bB][0-1](_?[0-1])*r?i?\\b"
      }, { begin: "\\b0[oO][0-7](_?[0-7])*r?i?\\b" }, {
        begin: "\\b0[xX][0-9a-fA-F](_?[0-9a-fA-F])*r?i?\\b"
      }, {
        begin: "\\b0(_?[0-7])+r?i?\\b"
      }]
    }, b2 = { variants: [{ match: /\(\)/ }, {
      className: "params",
      begin: /\(/,
      end: /(?=\))/,
      excludeBegin: true,
      endsParent: true,
      keywords: r2
    }] }, m2 = [d2, { variants: [{ match: [/class\s+/, i2, /\s+<\s+/, i2] }, {
      match: [/\b(class|module)\s+/, i2]
    }], scope: {
      2: "title.class",
      4: "title.class.inherited"
    }, keywords: r2 }, { match: [/(include|extend)\s+/, i2], scope: {
      2: "title.class"
    }, keywords: r2 }, { relevance: 0, match: [i2, /\.new[. (]/], scope: {
      1: "title.class"
    } }, {
      relevance: 0,
      match: /\b[A-Z][A-Z_0-9]+\b/,
      className: "variable.constant"
    }, { relevance: 0, match: a2, scope: "title.class" }, {
      match: [/def/, /\s+/, t2],
      scope: { 1: "keyword", 3: "title.function" },
      contains: [b2]
    }, {
      begin: e2.IDENT_RE + "::"
    }, {
      className: "symbol",
      begin: e2.UNDERSCORE_IDENT_RE + "(!|\\?)?:",
      relevance: 0
    }, {
      className: "symbol",
      begin: ":(?!\\s)",
      contains: [d2, { begin: t2 }],
      relevance: 0
    }, u4, {
      className: "variable",
      begin: "(\\$\\W)|((\\$|@@?)(\\w+))(?=[^@$?])(?![A-Za-z])(?![@$?'])"
    }, {
      className: "params",
      begin: /\|(?!=)/,
      end: /\|/,
      excludeBegin: true,
      excludeEnd: true,
      relevance: 0,
      keywords: r2
    }, {
      begin: "(" + e2.RE_STARTERS_RE + "|unless)\\s*",
      keywords: "unless",
      contains: [{
        className: "regexp",
        contains: [e2.BACKSLASH_ESCAPE, c2],
        illegal: /\n/,
        variants: [{ begin: "/", end: "/[a-z]*" }, { begin: /%r\{/, end: /\}[a-z]*/ }, {
          begin: "%r\\(",
          end: "\\)[a-z]*"
        }, { begin: "%r!", end: "![a-z]*" }, {
          begin: "%r\\[",
          end: "\\][a-z]*"
        }]
      }].concat(o2, l2),
      relevance: 0
    }].concat(o2, l2);
    c2.contains = m2, b2.contains = m2;
    const p2 = [{
      begin: /^\s*=>/,
      starts: { end: "$", contains: m2 }
    }, {
      className: "meta.prompt",
      begin: "^([>?]>|[\\w#]+\\(\\w+\\):\\d+:\\d+[>*]|(\\w+-)?\\d+\\.\\d+\\.\\d+(p\\d+)?[^\\d][^>]+>)(?=[ ])",
      starts: { end: "$", keywords: r2, contains: m2 }
    }];
    return l2.unshift(o2), {
      name: "Ruby",
      aliases: ["rb", "gemspec", "podspec", "thor", "irb"],
      keywords: r2,
      illegal: /\/\*/,
      contains: [e2.SHEBANG({ binary: "ruby" })].concat(p2).concat(l2).concat(m2)
    };
  },
  grmr_rust: (e2) => {
    const n2 = e2.regex, t2 = /(r#)?/, a2 = n2.concat(t2, e2.UNDERSCORE_IDENT_RE), i2 = n2.concat(t2, e2.IDENT_RE), r2 = {
      className: "title.function.invoke",
      relevance: 0,
      begin: n2.concat(/\b/, /(?!let|for|while|if|else|match\b)/, i2, n2.lookahead(/\s*\(/))
    }, s2 = "([ui](8|16|32|64|128|size)|f(32|64))?", o2 = ["drop ", "Copy", "Send", "Sized", "Sync", "Drop", "Fn", "FnMut", "FnOnce", "ToOwned", "Clone", "Debug", "PartialEq", "PartialOrd", "Eq", "Ord", "AsRef", "AsMut", "Into", "From", "Default", "Iterator", "Extend", "IntoIterator", "DoubleEndedIterator", "ExactSizeIterator", "SliceConcatExt", "ToString", "assert!", "assert_eq!", "bitflags!", "bytes!", "cfg!", "col!", "concat!", "concat_idents!", "debug_assert!", "debug_assert_eq!", "env!", "eprintln!", "panic!", "file!", "format!", "format_args!", "include_bytes!", "include_str!", "line!", "local_data_key!", "module_path!", "option_env!", "print!", "println!", "select!", "stringify!", "try!", "unimplemented!", "unreachable!", "vec!", "write!", "writeln!", "macro_rules!", "assert_ne!", "debug_assert_ne!"], l2 = ["i8", "i16", "i32", "i64", "i128", "isize", "u8", "u16", "u32", "u64", "u128", "usize", "f32", "f64", "str", "char", "bool", "Box", "Option", "Result", "String", "Vec"];
    return {
      name: "Rust",
      aliases: ["rs"],
      keywords: {
        $pattern: e2.IDENT_RE + "!?",
        type: l2,
        keyword: ["abstract", "as", "async", "await", "become", "box", "break", "const", "continue", "crate", "do", "dyn", "else", "enum", "extern", "false", "final", "fn", "for", "if", "impl", "in", "let", "loop", "macro", "match", "mod", "move", "mut", "override", "priv", "pub", "ref", "return", "self", "Self", "static", "struct", "super", "trait", "true", "try", "type", "typeof", "union", "unsafe", "unsized", "use", "virtual", "where", "while", "yield"],
        literal: ["true", "false", "Some", "None", "Ok", "Err"],
        built_in: o2
      },
      illegal: "</",
      contains: [e2.C_LINE_COMMENT_MODE, e2.COMMENT("/\\*", "\\*/", {
        contains: ["self"]
      }), e2.inherit(e2.QUOTE_STRING_MODE, { begin: /b?"/, illegal: null }), {
        className: "symbol",
        begin: /'[a-zA-Z_][a-zA-Z0-9_]*(?!')/
      }, {
        scope: "string",
        variants: [{ begin: /b?r(#*)"(.|\n)*?"\1(?!#)/ }, { begin: /b?'/, end: /'/, contains: [{
          scope: "char.escape",
          match: /\\('|\w|x\w{2}|u\w{4}|U\w{8})/
        }] }]
      }, {
        className: "number",
        variants: [{ begin: "\\b0b([01_]+)" + s2 }, {
          begin: "\\b0o([0-7_]+)" + s2
        }, { begin: "\\b0x([A-Fa-f0-9_]+)" + s2 }, {
          begin: "\\b(\\d[\\d_]*(\\.[0-9_]+)?([eE][+-]?[0-9_]+)?)" + s2
        }],
        relevance: 0
      }, {
        begin: [/fn/, /\s+/, a2],
        className: { 1: "keyword", 3: "title.function" }
      }, {
        className: "meta",
        begin: "#!?\\[",
        end: "\\]",
        contains: [{
          className: "string",
          begin: /"/,
          end: /"/,
          contains: [e2.BACKSLASH_ESCAPE]
        }]
      }, {
        begin: [/let/, /\s+/, /(?:mut\s+)?/, a2],
        className: {
          1: "keyword",
          3: "keyword",
          4: "variable"
        }
      }, { begin: [/for/, /\s+/, a2, /\s+/, /in/], className: {
        1: "keyword",
        3: "variable",
        5: "keyword"
      } }, { begin: [/type/, /\s+/, a2], className: {
        1: "keyword",
        3: "title.class"
      } }, {
        begin: [/(?:trait|enum|struct|union|impl|for)/, /\s+/, a2],
        className: { 1: "keyword", 3: "title.class" }
      }, { begin: e2.IDENT_RE + "::", keywords: {
        keyword: "Self",
        built_in: o2,
        type: l2
      } }, { className: "punctuation", begin: "->" }, r2]
    };
  },
  grmr_scss: (e2) => {
    const n2 = te(e2), t2 = se, a2 = re, i2 = "@[a-z-]+", r2 = {
      className: "variable",
      begin: "(\\$[a-zA-Z-][a-zA-Z0-9_-]*)\\b",
      relevance: 0
    };
    return {
      name: "SCSS",
      case_insensitive: true,
      illegal: "[=/|']",
      contains: [e2.C_LINE_COMMENT_MODE, e2.C_BLOCK_COMMENT_MODE, n2.CSS_NUMBER_MODE, {
        className: "selector-id",
        begin: "#[A-Za-z0-9_-]+",
        relevance: 0
      }, {
        className: "selector-class",
        begin: "\\.[A-Za-z0-9_-]+",
        relevance: 0
      }, n2.ATTRIBUTE_SELECTOR_MODE, {
        className: "selector-tag",
        begin: "\\b(" + ae.join("|") + ")\\b",
        relevance: 0
      }, {
        className: "selector-pseudo",
        begin: ":(" + a2.join("|") + ")"
      }, {
        className: "selector-pseudo",
        begin: ":(:)?(" + t2.join("|") + ")"
      }, r2, {
        begin: /\(/,
        end: /\)/,
        contains: [n2.CSS_NUMBER_MODE]
      }, n2.CSS_VARIABLE, {
        className: "attribute",
        begin: "\\b(" + oe.join("|") + ")\\b"
      }, {
        begin: "\\b(whitespace|wait|w-resize|visible|vertical-text|vertical-ideographic|uppercase|upper-roman|upper-alpha|underline|transparent|top|thin|thick|text|text-top|text-bottom|tb-rl|table-header-group|table-footer-group|sw-resize|super|strict|static|square|solid|small-caps|separate|se-resize|scroll|s-resize|rtl|row-resize|ridge|right|repeat|repeat-y|repeat-x|relative|progress|pointer|overline|outside|outset|oblique|nowrap|not-allowed|normal|none|nw-resize|no-repeat|no-drop|newspaper|ne-resize|n-resize|move|middle|medium|ltr|lr-tb|lowercase|lower-roman|lower-alpha|loose|list-item|line|line-through|line-edge|lighter|left|keep-all|justify|italic|inter-word|inter-ideograph|inside|inset|inline|inline-block|inherit|inactive|ideograph-space|ideograph-parenthesis|ideograph-numeric|ideograph-alpha|horizontal|hidden|help|hand|groove|fixed|ellipsis|e-resize|double|dotted|distribute|distribute-space|distribute-letter|distribute-all-lines|disc|disabled|default|decimal|dashed|crosshair|collapse|col-resize|circle|char|center|capitalize|break-word|break-all|bottom|both|bolder|bold|block|bidi-override|below|baseline|auto|always|all-scroll|absolute|table|table-cell)\\b"
      }, {
        begin: /:/,
        end: /[;}{]/,
        relevance: 0,
        contains: [n2.BLOCK_COMMENT, r2, n2.HEXCOLOR, n2.CSS_NUMBER_MODE, e2.QUOTE_STRING_MODE, e2.APOS_STRING_MODE, n2.IMPORTANT, n2.FUNCTION_DISPATCH]
      }, { begin: "@(page|font-face)", keywords: { $pattern: i2, keyword: "@page @font-face" } }, {
        begin: "@",
        end: "[{;]",
        returnBegin: true,
        keywords: {
          $pattern: /[a-z-]+/,
          keyword: "and or not only",
          attribute: ie.join(" ")
        },
        contains: [{
          begin: i2,
          className: "keyword"
        }, {
          begin: /[a-z-]+(?=:)/,
          className: "attribute"
        }, r2, e2.QUOTE_STRING_MODE, e2.APOS_STRING_MODE, n2.HEXCOLOR, n2.CSS_NUMBER_MODE]
      }, n2.FUNCTION_DISPATCH]
    };
  },
  grmr_shell: (e2) => ({
    name: "Shell Session",
    aliases: ["console", "shellsession"],
    contains: [{
      className: "meta.prompt",
      begin: /^\s{0,3}[/~\w\d[\]()@-]*[>%$#][ ]?/,
      starts: {
        end: /[^\\](?=\s*$)/,
        subLanguage: "bash"
      }
    }]
  }),
  grmr_sql: (e2) => {
    const n2 = e2.regex, t2 = e2.COMMENT("--", "$"), a2 = ["abs", "acos", "array_agg", "asin", "atan", "avg", "cast", "ceil", "ceiling", "coalesce", "corr", "cos", "cosh", "count", "covar_pop", "covar_samp", "cume_dist", "dense_rank", "deref", "element", "exp", "extract", "first_value", "floor", "json_array", "json_arrayagg", "json_exists", "json_object", "json_objectagg", "json_query", "json_table", "json_table_primitive", "json_value", "lag", "last_value", "lead", "listagg", "ln", "log", "log10", "lower", "max", "min", "mod", "nth_value", "ntile", "nullif", "percent_rank", "percentile_cont", "percentile_disc", "position", "position_regex", "power", "rank", "regr_avgx", "regr_avgy", "regr_count", "regr_intercept", "regr_r2", "regr_slope", "regr_sxx", "regr_sxy", "regr_syy", "row_number", "sin", "sinh", "sqrt", "stddev_pop", "stddev_samp", "substring", "substring_regex", "sum", "tan", "tanh", "translate", "translate_regex", "treat", "trim", "trim_array", "unnest", "upper", "value_of", "var_pop", "var_samp", "width_bucket"], i2 = a2, r2 = ["abs", "acos", "all", "allocate", "alter", "and", "any", "are", "array", "array_agg", "array_max_cardinality", "as", "asensitive", "asin", "asymmetric", "at", "atan", "atomic", "authorization", "avg", "begin", "begin_frame", "begin_partition", "between", "bigint", "binary", "blob", "boolean", "both", "by", "call", "called", "cardinality", "cascaded", "case", "cast", "ceil", "ceiling", "char", "char_length", "character", "character_length", "check", "classifier", "clob", "close", "coalesce", "collate", "collect", "column", "commit", "condition", "connect", "constraint", "contains", "convert", "copy", "corr", "corresponding", "cos", "cosh", "count", "covar_pop", "covar_samp", "create", "cross", "cube", "cume_dist", "current", "current_catalog", "current_date", "current_default_transform_group", "current_path", "current_role", "current_row", "current_schema", "current_time", "current_timestamp", "current_path", "current_role", "current_transform_group_for_type", "current_user", "cursor", "cycle", "date", "day", "deallocate", "dec", "decimal", "decfloat", "declare", "default", "define", "delete", "dense_rank", "deref", "describe", "deterministic", "disconnect", "distinct", "double", "drop", "dynamic", "each", "element", "else", "empty", "end", "end_frame", "end_partition", "end-exec", "equals", "escape", "every", "except", "exec", "execute", "exists", "exp", "external", "extract", "false", "fetch", "filter", "first_value", "float", "floor", "for", "foreign", "frame_row", "free", "from", "full", "function", "fusion", "get", "global", "grant", "group", "grouping", "groups", "having", "hold", "hour", "identity", "in", "indicator", "initial", "inner", "inout", "insensitive", "insert", "int", "integer", "intersect", "intersection", "interval", "into", "is", "join", "json_array", "json_arrayagg", "json_exists", "json_object", "json_objectagg", "json_query", "json_table", "json_table_primitive", "json_value", "lag", "language", "large", "last_value", "lateral", "lead", "leading", "left", "like", "like_regex", "listagg", "ln", "local", "localtime", "localtimestamp", "log", "log10", "lower", "match", "match_number", "match_recognize", "matches", "max", "member", "merge", "method", "min", "minute", "mod", "modifies", "module", "month", "multiset", "national", "natural", "nchar", "nclob", "new", "no", "none", "normalize", "not", "nth_value", "ntile", "null", "nullif", "numeric", "octet_length", "occurrences_regex", "of", "offset", "old", "omit", "on", "one", "only", "open", "or", "order", "out", "outer", "over", "overlaps", "overlay", "parameter", "partition", "pattern", "per", "percent", "percent_rank", "percentile_cont", "percentile_disc", "period", "portion", "position", "position_regex", "power", "precedes", "precision", "prepare", "primary", "procedure", "ptf", "range", "rank", "reads", "real", "recursive", "ref", "references", "referencing", "regr_avgx", "regr_avgy", "regr_count", "regr_intercept", "regr_r2", "regr_slope", "regr_sxx", "regr_sxy", "regr_syy", "release", "result", "return", "returns", "revoke", "right", "rollback", "rollup", "row", "row_number", "rows", "running", "savepoint", "scope", "scroll", "search", "second", "seek", "select", "sensitive", "session_user", "set", "show", "similar", "sin", "sinh", "skip", "smallint", "some", "specific", "specifictype", "sql", "sqlexception", "sqlstate", "sqlwarning", "sqrt", "start", "static", "stddev_pop", "stddev_samp", "submultiset", "subset", "substring", "substring_regex", "succeeds", "sum", "symmetric", "system", "system_time", "system_user", "table", "tablesample", "tan", "tanh", "then", "time", "timestamp", "timezone_hour", "timezone_minute", "to", "trailing", "translate", "translate_regex", "translation", "treat", "trigger", "trim", "trim_array", "true", "truncate", "uescape", "union", "unique", "unknown", "unnest", "update", "upper", "user", "using", "value", "values", "value_of", "var_pop", "var_samp", "varbinary", "varchar", "varying", "versioning", "when", "whenever", "where", "width_bucket", "window", "with", "within", "without", "year", "add", "asc", "collation", "desc", "final", "first", "last", "view"].filter(((e3) => !a2.includes(e3))), s2 = {
      match: n2.concat(/\b/, n2.either(...i2), /\s*\(/),
      relevance: 0,
      keywords: { built_in: i2 }
    };
    function o2(e3) {
      return n2.concat(/\b/, n2.either(...e3.map(((e4) => e4.replace(/\s+/, "\\s+")))), /\b/);
    }
    const l2 = {
      scope: "keyword",
      match: o2(["create table", "insert into", "primary key", "foreign key", "not null", "alter table", "add constraint", "grouping sets", "on overflow", "character set", "respect nulls", "ignore nulls", "nulls first", "nulls last", "depth first", "breadth first"]),
      relevance: 0
    };
    return { name: "SQL", case_insensitive: true, illegal: /[{}]|<\//, keywords: {
      $pattern: /\b[\w\.]+/,
      keyword: ((e3, { exceptions: n3, when: t3 } = {}) => {
        const a3 = t3;
        return n3 = n3 || [], e3.map(((e4) => e4.match(/\|\d+$/) || n3.includes(e4) ? e4 : a3(e4) ? e4 + "|0" : e4));
      })(r2, { when: (e3) => e3.length < 3 }),
      literal: ["true", "false", "unknown"],
      type: ["bigint", "binary", "blob", "boolean", "char", "character", "clob", "date", "dec", "decfloat", "decimal", "float", "int", "integer", "interval", "nchar", "nclob", "national", "numeric", "real", "row", "smallint", "time", "timestamp", "varchar", "varying", "varbinary"],
      built_in: ["current_catalog", "current_date", "current_default_transform_group", "current_path", "current_role", "current_schema", "current_transform_group_for_type", "current_user", "session_user", "system_time", "system_user", "current_time", "localtime", "current_timestamp", "localtimestamp"]
    }, contains: [{
      scope: "type",
      match: o2(["double precision", "large object", "with timezone", "without timezone"])
    }, l2, s2, { scope: "variable", match: /@[a-z0-9][a-z0-9_]*/ }, { scope: "string", variants: [{
      begin: /'/,
      end: /'/,
      contains: [{ match: /''/ }]
    }] }, { begin: /"/, end: /"/, contains: [{
      match: /""/
    }] }, e2.C_NUMBER_MODE, e2.C_BLOCK_COMMENT_MODE, t2, {
      scope: "operator",
      match: /[-+*/=%^~]|&&?|\|\|?|!=?|<(?:=>?|<|>)?|>[>=]?/,
      relevance: 0
    }] };
  },
  grmr_swift: (e2) => {
    const n2 = { match: /\s+/, relevance: 0 }, t2 = e2.COMMENT("/\\*", "\\*/", {
      contains: ["self"]
    }), a2 = [e2.C_LINE_COMMENT_MODE, t2], i2 = {
      match: [/\./, m(...ke, ...xe)],
      className: { 2: "keyword" }
    }, r2 = {
      match: b(/\./, m(...Me)),
      relevance: 0
    }, s2 = Me.filter(((e3) => "string" == typeof e3)).concat(["_|0"]), o2 = { variants: [{
      className: "keyword",
      match: m(...Me.filter(((e3) => "string" != typeof e3)).concat(Oe).map(Ne), ...xe)
    }] }, l2 = {
      $pattern: m(/\b\w+/, /#\w+/),
      keyword: s2.concat(Ce),
      literal: Ae
    }, c2 = [i2, r2, o2], g2 = [{
      match: b(/\./, m(...Te)),
      relevance: 0
    }, {
      className: "built_in",
      match: b(/\b/, m(...Te), /(?=\()/)
    }], u4 = { match: /->/, relevance: 0 }, p2 = [u4, {
      className: "operator",
      relevance: 0,
      variants: [{ match: Ie }, { match: `\\.(\\.|${De})+` }]
    }], _2 = "([0-9]_*)+", h2 = "([0-9a-fA-F]_*)+", f2 = {
      className: "number",
      relevance: 0,
      variants: [{ match: `\\b(${_2})(\\.(${_2}))?([eE][+-]?(${_2}))?\\b` }, {
        match: `\\b0x(${h2})(\\.(${h2}))?([pP][+-]?(${_2}))?\\b`
      }, {
        match: /\b0o([0-7]_*)+\b/
      }, { match: /\b0b([01]_*)+\b/ }]
    }, E2 = (e3 = "") => ({
      className: "subst",
      variants: [{
        match: b(/\\/, e3, /[0\\tnr"']/)
      }, { match: b(/\\/, e3, /u\{[0-9a-fA-F]{1,8}\}/) }]
    }), y3 = (e3 = "") => ({
      className: "subst",
      match: b(/\\/, e3, /[\t ]*(?:[\r\n]|\r\n)/)
    }), w2 = (e3 = "") => ({
      className: "subst",
      label: "interpol",
      begin: b(/\\/, e3, /\(/),
      end: /\)/
    }), v2 = (e3 = "") => ({
      begin: b(e3, /"""/),
      end: b(/"""/, e3),
      contains: [E2(e3), y3(e3), w2(e3)]
    }), N2 = (e3 = "") => ({ begin: b(e3, /"/), end: b(/"/, e3), contains: [E2(e3), w2(e3)] }), k2 = {
      className: "string",
      variants: [v2(), v2("#"), v2("##"), v2("###"), N2(), N2("#"), N2("##"), N2("###")]
    }, x2 = [e2.BACKSLASH_ESCAPE, {
      begin: /\[/,
      end: /\]/,
      relevance: 0,
      contains: [e2.BACKSLASH_ESCAPE]
    }], O2 = {
      begin: /\/[^\s](?=[^/\n]*\/)/,
      end: /\//,
      contains: x2
    }, M2 = (e3) => {
      const n3 = b(e3, /\//), t3 = b(/\//, e3);
      return {
        begin: n3,
        end: t3,
        contains: [...x2, { scope: "comment", begin: `#(?!.*${t3})`, end: /$/ }]
      };
    }, A2 = {
      scope: "regexp",
      variants: [M2("###"), M2("##"), M2("#"), O2]
    }, S3 = {
      match: b(/`/, $e, /`/)
    }, C2 = [S3, { className: "variable", match: /\$\d+/ }, {
      className: "variable",
      match: `\\$${Be}+`
    }], T2 = [{ match: /(@|#(un)?)available/, scope: "keyword", starts: {
      contains: [{ begin: /\(/, end: /\)/, keywords: je, contains: [...p2, f2, k2] }]
    } }, {
      scope: "keyword",
      match: b(/@/, m(...ze), d(m(/\(/, /\s+/)))
    }, {
      scope: "meta",
      match: b(/@/, $e)
    }], R2 = { match: d(/\b[A-Z]/), relevance: 0, contains: [{
      className: "type",
      match: b(/(AV|CA|CF|CG|CI|CL|CM|CN|CT|MK|MP|MTK|MTL|NS|SCN|SK|UI|WK|XC)/, Be, "+")
    }, { className: "type", match: Fe, relevance: 0 }, { match: /[?!]+/, relevance: 0 }, {
      match: /\.\.\./,
      relevance: 0
    }, { match: b(/\s+&\s+/, d(Fe)), relevance: 0 }] }, D2 = {
      begin: /</,
      end: />/,
      keywords: l2,
      contains: [...a2, ...c2, ...T2, u4, R2]
    };
    R2.contains.push(D2);
    const I2 = { begin: /\(/, end: /\)/, relevance: 0, keywords: l2, contains: ["self", {
      match: b($e, /\s*:/),
      keywords: "_|0",
      relevance: 0
    }, ...a2, A2, ...c2, ...g2, ...p2, f2, k2, ...C2, ...T2, R2] }, L2 = {
      begin: /</,
      end: />/,
      keywords: "repeat each",
      contains: [...a2, R2]
    }, B3 = {
      begin: /\(/,
      end: /\)/,
      keywords: l2,
      contains: [{
        begin: m(d(b($e, /\s*:/)), d(b($e, /\s+/, $e, /\s*:/))),
        end: /:/,
        relevance: 0,
        contains: [{ className: "keyword", match: /\b_\b/ }, {
          className: "params",
          match: $e
        }]
      }, ...a2, ...c2, ...p2, f2, k2, ...T2, R2, I2],
      endsParent: true,
      illegal: /["']/
    }, $3 = {
      match: [/(func|macro)/, /\s+/, m(S3.match, $e, Ie)],
      className: {
        1: "keyword",
        3: "title.function"
      },
      contains: [L2, B3, n2],
      illegal: [/\[/, /%/]
    }, F2 = {
      match: [/\b(?:subscript|init[?!]?)/, /\s*(?=[<(])/],
      className: { 1: "keyword" },
      contains: [L2, B3, n2],
      illegal: /\[|%/
    }, z2 = { match: [/operator/, /\s+/, Ie], className: {
      1: "keyword",
      3: "title"
    } }, j2 = { begin: [/precedencegroup/, /\s+/, Fe], className: {
      1: "keyword",
      3: "title"
    }, contains: [R2], keywords: [...Se, ...Ae], end: /}/ }, U2 = {
      begin: [/(struct|protocol|class|extension|enum|actor)/, /\s+/, $e, /\s*/],
      beginScope: { 1: "keyword", 3: "title.class" },
      keywords: l2,
      contains: [L2, ...c2, {
        begin: /:/,
        end: /\{/,
        keywords: l2,
        contains: [{ scope: "title.class.inherited", match: Fe }, ...c2],
        relevance: 0
      }]
    };
    for (const e3 of k2.variants) {
      const n3 = e3.contains.find(((e4) => "interpol" === e4.label));
      n3.keywords = l2;
      const t3 = [...c2, ...g2, ...p2, f2, k2, ...C2];
      n3.contains = [...t3, {
        begin: /\(/,
        end: /\)/,
        contains: ["self", ...t3]
      }];
    }
    return { name: "Swift", keywords: l2, contains: [...a2, $3, F2, {
      match: [/class\b/, /\s+/, /func\b/, /\s+/, /\b[A-Za-z_][A-Za-z0-9_]*\b/],
      scope: {
        1: "keyword",
        3: "keyword",
        5: "title.function"
      }
    }, {
      match: [/class\b/, /\s+/, /var\b/],
      scope: { 1: "keyword", 3: "keyword" }
    }, U2, z2, j2, {
      beginKeywords: "import",
      end: /$/,
      contains: [...a2],
      relevance: 0
    }, A2, ...c2, ...g2, ...p2, f2, k2, ...C2, ...T2, R2, I2] };
  },
  grmr_typescript: (e2) => {
    const n2 = e2.regex, t2 = ve(e2), a2 = me, i2 = ["any", "void", "number", "boolean", "string", "object", "never", "symbol", "bigint", "unknown"], r2 = {
      begin: [/namespace/, /\s+/, e2.IDENT_RE],
      beginScope: { 1: "keyword", 3: "title.class" }
    }, s2 = {
      beginKeywords: "interface",
      end: /\{/,
      excludeEnd: true,
      keywords: {
        keyword: "interface extends",
        built_in: i2
      },
      contains: [t2.exports.CLASS_REFERENCE]
    }, o2 = {
      $pattern: me,
      keyword: pe.concat(["type", "interface", "public", "private", "protected", "implements", "declare", "abstract", "readonly", "enum", "override", "satisfies"]),
      literal: _e,
      built_in: we.concat(i2),
      "variable.language": ye
    }, l2 = {
      className: "meta",
      begin: "@" + a2
    }, c2 = (e3, n3, t3) => {
      const a3 = e3.contains.findIndex(((e4) => e4.label === n3));
      if (-1 === a3) throw Error("can not find mode to replace");
      e3.contains.splice(a3, 1, t3);
    };
    Object.assign(t2.keywords, o2), t2.exports.PARAMS_CONTAINS.push(l2);
    const d2 = t2.contains.find(((e3) => "attr" === e3.scope)), g2 = Object.assign({}, d2, {
      match: n2.concat(a2, n2.lookahead(/\s*\?:/))
    });
    return t2.exports.PARAMS_CONTAINS.push([t2.exports.CLASS_REFERENCE, d2, g2]), t2.contains = t2.contains.concat([l2, r2, s2, g2]), c2(t2, "shebang", e2.SHEBANG()), c2(t2, "use_strict", {
      className: "meta",
      relevance: 10,
      begin: /^\s*['"]use strict['"]/
    }), t2.contains.find(((e3) => "func.def" === e3.label)).relevance = 0, Object.assign(t2, {
      name: "TypeScript",
      aliases: ["ts", "tsx", "mts", "cts"]
    }), t2;
  },
  grmr_vbnet: (e2) => {
    const n2 = e2.regex, t2 = /\d{1,2}\/\d{1,2}\/\d{4}/, a2 = /\d{4}-\d{1,2}-\d{1,2}/, i2 = /(\d|1[012])(:\d+){0,2} *(AM|PM)/, r2 = /\d{1,2}(:\d{1,2}){1,2}/, s2 = {
      className: "literal",
      variants: [{ begin: n2.concat(/# */, n2.either(a2, t2), / *#/) }, {
        begin: n2.concat(/# */, r2, / *#/)
      }, { begin: n2.concat(/# */, i2, / *#/) }, {
        begin: n2.concat(/# */, n2.either(a2, t2), / +/, n2.either(i2, r2), / *#/)
      }]
    }, o2 = e2.COMMENT(/'''/, /$/, {
      contains: [{ className: "doctag", begin: /<\/?/, end: />/ }]
    }), l2 = e2.COMMENT(null, /$/, { variants: [{ begin: /'/ }, { begin: /([\t ]|^)REM(?=\s)/ }] });
    return {
      name: "Visual Basic .NET",
      aliases: ["vb"],
      case_insensitive: true,
      classNameAliases: { label: "symbol" },
      keywords: {
        keyword: "addhandler alias aggregate ansi as async assembly auto binary by byref byval call case catch class compare const continue custom declare default delegate dim distinct do each equals else elseif end enum erase error event exit explicit finally for friend from function get global goto group handles if implements imports in inherits interface into iterator join key let lib loop me mid module mustinherit mustoverride mybase myclass namespace narrowing new next notinheritable notoverridable of off on operator option optional order overloads overridable overrides paramarray partial preserve private property protected public raiseevent readonly redim removehandler resume return select set shadows shared skip static step stop structure strict sub synclock take text then throw to try unicode until using when where while widening with withevents writeonly yield",
        built_in: "addressof and andalso await directcast gettype getxmlnamespace is isfalse isnot istrue like mod nameof new not or orelse trycast typeof xor cbool cbyte cchar cdate cdbl cdec cint clng cobj csbyte cshort csng cstr cuint culng cushort",
        type: "boolean byte char date decimal double integer long object sbyte short single string uinteger ulong ushort",
        literal: "true false nothing"
      },
      illegal: "//|\\{|\\}|endif|gosub|variant|wend|^\\$ ",
      contains: [{
        className: "string",
        begin: /"(""|[^/n])"C\b/
      }, {
        className: "string",
        begin: /"/,
        end: /"/,
        illegal: /\n/,
        contains: [{ begin: /""/ }]
      }, s2, {
        className: "number",
        relevance: 0,
        variants: [{
          begin: /\b\d[\d_]*((\.[\d_]+(E[+-]?[\d_]+)?)|(E[+-]?[\d_]+))[RFD@!#]?/
        }, { begin: /\b\d[\d_]*((U?[SIL])|[%&])?/ }, { begin: /&H[\dA-F_]+((U?[SIL])|[%&])?/ }, {
          begin: /&O[0-7_]+((U?[SIL])|[%&])?/
        }, { begin: /&B[01_]+((U?[SIL])|[%&])?/ }]
      }, {
        className: "label",
        begin: /^\w+:/
      }, o2, l2, {
        className: "meta",
        begin: /[\t ]*#(const|disable|else|elseif|enable|end|externalsource|if|region)\b/,
        end: /$/,
        keywords: {
          keyword: "const disable else elseif enable end externalsource if region then"
        },
        contains: [l2]
      }]
    };
  },
  grmr_wasm: (e2) => {
    e2.regex;
    const n2 = e2.COMMENT(/\(;/, /;\)/);
    return n2.contains.push("self"), { name: "WebAssembly", keywords: {
      $pattern: /[\w.]+/,
      keyword: ["anyfunc", "block", "br", "br_if", "br_table", "call", "call_indirect", "data", "drop", "elem", "else", "end", "export", "func", "global.get", "global.set", "local.get", "local.set", "local.tee", "get_global", "get_local", "global", "if", "import", "local", "loop", "memory", "memory.grow", "memory.size", "module", "mut", "nop", "offset", "param", "result", "return", "select", "set_global", "set_local", "start", "table", "tee_local", "then", "type", "unreachable"]
    }, contains: [e2.COMMENT(/;;/, /$/), n2, {
      match: [/(?:offset|align)/, /\s*/, /=/],
      className: { 1: "keyword", 3: "operator" }
    }, { className: "variable", begin: /\$[\w_]+/ }, {
      match: /(\((?!;)|\))+/,
      className: "punctuation",
      relevance: 0
    }, {
      begin: [/(?:func|call|call_indirect)/, /\s+/, /\$[^\s)]+/],
      className: {
        1: "keyword",
        3: "title.function"
      }
    }, e2.QUOTE_STRING_MODE, {
      match: /(i32|i64|f32|f64)(?!\.)/,
      className: "type"
    }, {
      className: "keyword",
      match: /\b(f32|f64|i32|i64)(?:\.(?:abs|add|and|ceil|clz|const|convert_[su]\/i(?:32|64)|copysign|ctz|demote\/f64|div(?:_[su])?|eqz?|extend_[su]\/i32|floor|ge(?:_[su])?|gt(?:_[su])?|le(?:_[su])?|load(?:(?:8|16|32)_[su])?|lt(?:_[su])?|max|min|mul|nearest|neg?|or|popcnt|promote\/f32|reinterpret\/[fi](?:32|64)|rem_[su]|rot[lr]|shl|shr_[su]|store(?:8|16|32)?|sqrt|sub|trunc(?:_[su]\/f(?:32|64))?|wrap\/i64|xor))\b/
    }, {
      className: "number",
      relevance: 0,
      match: /[+-]?\b(?:\d(?:_?\d)*(?:\.\d(?:_?\d)*)?(?:[eE][+-]?\d(?:_?\d)*)?|0x[\da-fA-F](?:_?[\da-fA-F])*(?:\.[\da-fA-F](?:_?[\da-fA-D])*)?(?:[pP][+-]?\d(?:_?\d)*)?)\b|\binf\b|\bnan(?::0x[\da-fA-F](?:_?[\da-fA-D])*)?\b/
    }] };
  },
  grmr_xml: (e2) => {
    const n2 = e2.regex, t2 = n2.concat(/[\p{L}_]/u, n2.optional(/[\p{L}0-9_.-]*:/u), /[\p{L}0-9_.-]*/u), a2 = {
      className: "symbol",
      begin: /&[a-z]+;|&#[0-9]+;|&#x[a-f0-9]+;/
    }, i2 = {
      begin: /\s/,
      contains: [{ className: "keyword", begin: /#?[a-z_][a-z1-9_-]+/, illegal: /\n/ }]
    }, r2 = e2.inherit(i2, { begin: /\(/, end: /\)/ }), s2 = e2.inherit(e2.APOS_STRING_MODE, {
      className: "string"
    }), o2 = e2.inherit(e2.QUOTE_STRING_MODE, { className: "string" }), l2 = {
      endsWithParent: true,
      illegal: /</,
      relevance: 0,
      contains: [{
        className: "attr",
        begin: /[\p{L}0-9._:-]+/u,
        relevance: 0
      }, { begin: /=\s*/, relevance: 0, contains: [{
        className: "string",
        endsParent: true,
        variants: [{ begin: /"/, end: /"/, contains: [a2] }, {
          begin: /'/,
          end: /'/,
          contains: [a2]
        }, { begin: /[^\s"'=<>`]+/ }]
      }] }]
    };
    return {
      name: "HTML, XML",
      aliases: ["html", "xhtml", "rss", "atom", "xjb", "xsd", "xsl", "plist", "wsf", "svg"],
      case_insensitive: true,
      unicodeRegex: true,
      contains: [{
        className: "meta",
        begin: /<![a-z]/,
        end: />/,
        relevance: 10,
        contains: [i2, o2, s2, r2, { begin: /\[/, end: /\]/, contains: [{
          className: "meta",
          begin: /<![a-z]/,
          end: />/,
          contains: [i2, r2, o2, s2]
        }] }]
      }, e2.COMMENT(/<!--/, /-->/, { relevance: 10 }), {
        begin: /<!\[CDATA\[/,
        end: /\]\]>/,
        relevance: 10
      }, a2, { className: "meta", end: /\?>/, variants: [{
        begin: /<\?xml/,
        relevance: 10,
        contains: [o2]
      }, { begin: /<\?[a-z][a-z0-9]+/ }] }, {
        className: "tag",
        begin: /<style(?=\s|>)/,
        end: />/,
        keywords: { name: "style" },
        contains: [l2],
        starts: {
          end: /<\/style>/,
          returnEnd: true,
          subLanguage: ["css", "xml"]
        }
      }, {
        className: "tag",
        begin: /<script(?=\s|>)/,
        end: />/,
        keywords: { name: "script" },
        contains: [l2],
        starts: {
          end: /<\/script>/,
          returnEnd: true,
          subLanguage: ["javascript", "handlebars", "xml"]
        }
      }, {
        className: "tag",
        begin: /<>|<\/>/
      }, {
        className: "tag",
        begin: n2.concat(/</, n2.lookahead(n2.concat(t2, n2.either(/\/>/, />/, /\s/)))),
        end: /\/?>/,
        contains: [{ className: "name", begin: t2, relevance: 0, starts: l2 }]
      }, {
        className: "tag",
        begin: n2.concat(/<\//, n2.lookahead(n2.concat(t2, />/))),
        contains: [{
          className: "name",
          begin: t2,
          relevance: 0
        }, { begin: />/, relevance: 0, endsParent: true }]
      }]
    };
  },
  grmr_yaml: (e2) => {
    const n2 = "true false yes no null", t2 = "[\\w#;/?:@&=+$,.~*'()[\\]]+", a2 = {
      className: "string",
      relevance: 0,
      variants: [{ begin: /"/, end: /"/ }, { begin: /\S+/ }],
      contains: [e2.BACKSLASH_ESCAPE, { className: "template-variable", variants: [{
        begin: /\{\{/,
        end: /\}\}/
      }, { begin: /%\{/, end: /\}/ }] }]
    }, i2 = e2.inherit(a2, { variants: [{
      begin: /'/,
      end: /'/,
      contains: [{ begin: /''/, relevance: 0 }]
    }, { begin: /"/, end: /"/ }, {
      begin: /[^\s,{}[\]]+/
    }] }), r2 = {
      end: ",",
      endsWithParent: true,
      excludeEnd: true,
      keywords: n2,
      relevance: 0
    }, s2 = { begin: /\{/, end: /\}/, contains: [r2], illegal: "\\n", relevance: 0 }, o2 = {
      begin: "\\[",
      end: "\\]",
      contains: [r2],
      illegal: "\\n",
      relevance: 0
    }, l2 = [{
      className: "attr",
      variants: [{ begin: /[\w*@][\w*@ :()\./-]*:(?=[ \t]|$)/ }, {
        begin: /"[\w*@][\w*@ :()\./-]*":(?=[ \t]|$)/
      }, {
        begin: /'[\w*@][\w*@ :()\./-]*':(?=[ \t]|$)/
      }]
    }, {
      className: "meta",
      begin: "^---\\s*$",
      relevance: 10
    }, {
      className: "string",
      begin: "[\\|>]([1-9]?[+-])?[ ]*\\n( +)[^ ][^\\n]*\\n(\\2[^\\n]+\\n?)*"
    }, {
      begin: "<%[%=-]?",
      end: "[%-]?%>",
      subLanguage: "ruby",
      excludeBegin: true,
      excludeEnd: true,
      relevance: 0
    }, { className: "type", begin: "!\\w+!" + t2 }, {
      className: "type",
      begin: "!<" + t2 + ">"
    }, { className: "type", begin: "!" + t2 }, {
      className: "type",
      begin: "!!" + t2
    }, { className: "meta", begin: "&" + e2.UNDERSCORE_IDENT_RE + "$" }, {
      className: "meta",
      begin: "\\*" + e2.UNDERSCORE_IDENT_RE + "$"
    }, {
      className: "bullet",
      begin: "-(?=[ ]|$)",
      relevance: 0
    }, e2.HASH_COMMENT_MODE, { beginKeywords: n2, keywords: { literal: n2 } }, {
      className: "number",
      begin: "\\b[0-9]{4}(-[0-9][0-9]){0,2}([Tt \\t][0-9][0-9]?(:[0-9][0-9]){2})?(\\.[0-9]*)?([ \\t])*(Z|[-+][0-9][0-9]?(:[0-9][0-9])?)?\\b"
    }, { className: "number", begin: e2.C_NUMBER_RE + "\\b", relevance: 0 }, s2, o2, {
      className: "string",
      relevance: 0,
      begin: /'/,
      end: /'/,
      contains: [{
        match: /''/,
        scope: "char.escape",
        relevance: 0
      }]
    }, a2], c2 = [...l2];
    return c2.pop(), c2.push(i2), r2.contains = c2, {
      name: "YAML",
      case_insensitive: true,
      aliases: ["yml"],
      contains: l2
    };
  }
});
const Pe = ne;
for (const e2 of Object.keys(Ue)) {
  const n2 = e2.replace("grmr_", "").replace("_", "-");
  Pe.registerLanguage(n2, Ue[e2]);
}
var hljsGrammar = /* @__PURE__ */ (() => {
  return (e2) => {
    const n2 = "true false yes no null", a2 = "[\\w#;/?:@&=+$,.~*'()[\\]]+", s2 = {
      className: "string",
      relevance: 0,
      variants: [{ begin: /"/, end: /"/ }, { begin: /\S+/ }],
      contains: [e2.BACKSLASH_ESCAPE, { className: "template-variable", variants: [{
        begin: /\{\{/,
        end: /\}\}/
      }, { begin: /%\{/, end: /\}/ }] }]
    }, i2 = e2.inherit(s2, { variants: [{
      begin: /'/,
      end: /'/,
      contains: [{ begin: /''/, relevance: 0 }]
    }, { begin: /"/, end: /"/ }, {
      begin: /[^\s,{}[\]]+/
    }] }), l2 = {
      end: ",",
      endsWithParent: true,
      excludeEnd: true,
      keywords: n2,
      relevance: 0
    }, t2 = { begin: /\{/, end: /\}/, contains: [l2], illegal: "\\n", relevance: 0 }, c2 = {
      begin: "\\[",
      end: "\\]",
      contains: [l2],
      illegal: "\\n",
      relevance: 0
    }, r2 = [{
      className: "attr",
      variants: [{ begin: /[\w*@][\w*@ :()\./-]*:(?=[ \t]|$)/ }, {
        begin: /"[\w*@][\w*@ :()\./-]*":(?=[ \t]|$)/
      }, {
        begin: /'[\w*@][\w*@ :()\./-]*':(?=[ \t]|$)/
      }]
    }, {
      className: "meta",
      begin: "^---\\s*$",
      relevance: 10
    }, {
      className: "string",
      begin: "[\\|>]([1-9]?[+-])?[ ]*\\n( +)[^ ][^\\n]*\\n(\\2[^\\n]+\\n?)*"
    }, {
      begin: "<%[%=-]?",
      end: "[%-]?%>",
      subLanguage: "ruby",
      excludeBegin: true,
      excludeEnd: true,
      relevance: 0
    }, { className: "type", begin: "!\\w+!" + a2 }, {
      className: "type",
      begin: "!<" + a2 + ">"
    }, { className: "type", begin: "!" + a2 }, {
      className: "type",
      begin: "!!" + a2
    }, { className: "meta", begin: "&" + e2.UNDERSCORE_IDENT_RE + "$" }, {
      className: "meta",
      begin: "\\*" + e2.UNDERSCORE_IDENT_RE + "$"
    }, {
      className: "bullet",
      begin: "-(?=[ ]|$)",
      relevance: 0
    }, e2.HASH_COMMENT_MODE, { beginKeywords: n2, keywords: { literal: n2 } }, {
      className: "number",
      begin: "\\b[0-9]{4}(-[0-9][0-9]){0,2}([Tt \\t][0-9][0-9]?(:[0-9][0-9]){2})?(\\.[0-9]*)?([ \\t])*(Z|[-+][0-9][0-9]?(:[0-9][0-9])?)?\\b"
    }, { className: "number", begin: e2.C_NUMBER_RE + "\\b", relevance: 0 }, t2, c2, {
      className: "string",
      relevance: 0,
      begin: /'/,
      end: /'/,
      contains: [{
        match: /''/,
        scope: "char.escape",
        relevance: 0
      }]
    }, s2], b2 = [...r2];
    return b2.pop(), b2.push(i2), l2.contains = b2, {
      name: "YAML",
      case_insensitive: true,
      aliases: ["yml"],
      contains: r2
    };
  };
})();
const {
  entries,
  setPrototypeOf,
  isFrozen,
  getPrototypeOf,
  getOwnPropertyDescriptor
} = Object;
let {
  freeze,
  seal,
  create
} = Object;
let {
  apply,
  construct
} = typeof Reflect !== "undefined" && Reflect;
if (!freeze) {
  freeze = function freeze2(x2) {
    return x2;
  };
}
if (!seal) {
  seal = function seal2(x2) {
    return x2;
  };
}
if (!apply) {
  apply = function apply2(func, thisArg) {
    for (var _len = arguments.length, args = new Array(_len > 2 ? _len - 2 : 0), _key = 2; _key < _len; _key++) {
      args[_key - 2] = arguments[_key];
    }
    return func.apply(thisArg, args);
  };
}
if (!construct) {
  construct = function construct2(Func) {
    for (var _len2 = arguments.length, args = new Array(_len2 > 1 ? _len2 - 1 : 0), _key2 = 1; _key2 < _len2; _key2++) {
      args[_key2 - 1] = arguments[_key2];
    }
    return new Func(...args);
  };
}
const arrayForEach = unapply(Array.prototype.forEach);
const arrayLastIndexOf = unapply(Array.prototype.lastIndexOf);
const arrayPop = unapply(Array.prototype.pop);
const arrayPush = unapply(Array.prototype.push);
const arraySplice = unapply(Array.prototype.splice);
const stringToLowerCase = unapply(String.prototype.toLowerCase);
const stringToString = unapply(String.prototype.toString);
const stringMatch = unapply(String.prototype.match);
const stringReplace = unapply(String.prototype.replace);
const stringIndexOf = unapply(String.prototype.indexOf);
const stringTrim = unapply(String.prototype.trim);
const objectHasOwnProperty = unapply(Object.prototype.hasOwnProperty);
const regExpTest = unapply(RegExp.prototype.test);
const typeErrorCreate = unconstruct(TypeError);
function unapply(func) {
  return function(thisArg) {
    if (thisArg instanceof RegExp) {
      thisArg.lastIndex = 0;
    }
    for (var _len3 = arguments.length, args = new Array(_len3 > 1 ? _len3 - 1 : 0), _key3 = 1; _key3 < _len3; _key3++) {
      args[_key3 - 1] = arguments[_key3];
    }
    return apply(func, thisArg, args);
  };
}
function unconstruct(Func) {
  return function() {
    for (var _len4 = arguments.length, args = new Array(_len4), _key4 = 0; _key4 < _len4; _key4++) {
      args[_key4] = arguments[_key4];
    }
    return construct(Func, args);
  };
}
function addToSet(set2, array) {
  let transformCaseFunc = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : stringToLowerCase;
  if (setPrototypeOf) {
    setPrototypeOf(set2, null);
  }
  let l2 = array.length;
  while (l2--) {
    let element = array[l2];
    if (typeof element === "string") {
      const lcElement = transformCaseFunc(element);
      if (lcElement !== element) {
        if (!isFrozen(array)) {
          array[l2] = lcElement;
        }
        element = lcElement;
      }
    }
    set2[element] = true;
  }
  return set2;
}
function cleanArray(array) {
  for (let index2 = 0; index2 < array.length; index2++) {
    const isPropertyExist = objectHasOwnProperty(array, index2);
    if (!isPropertyExist) {
      array[index2] = null;
    }
  }
  return array;
}
function clone(object) {
  const newObject = create(null);
  for (const [property, value] of entries(object)) {
    const isPropertyExist = objectHasOwnProperty(object, property);
    if (isPropertyExist) {
      if (Array.isArray(value)) {
        newObject[property] = cleanArray(value);
      } else if (value && typeof value === "object" && value.constructor === Object) {
        newObject[property] = clone(value);
      } else {
        newObject[property] = value;
      }
    }
  }
  return newObject;
}
function lookupGetter(object, prop2) {
  while (object !== null) {
    const desc = getOwnPropertyDescriptor(object, prop2);
    if (desc) {
      if (desc.get) {
        return unapply(desc.get);
      }
      if (typeof desc.value === "function") {
        return unapply(desc.value);
      }
    }
    object = getPrototypeOf(object);
  }
  function fallbackValue() {
    return null;
  }
  return fallbackValue;
}
const html$1 = freeze(["a", "abbr", "acronym", "address", "area", "article", "aside", "audio", "b", "bdi", "bdo", "big", "blink", "blockquote", "body", "br", "button", "canvas", "caption", "center", "cite", "code", "col", "colgroup", "content", "data", "datalist", "dd", "decorator", "del", "details", "dfn", "dialog", "dir", "div", "dl", "dt", "element", "em", "fieldset", "figcaption", "figure", "font", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "hgroup", "hr", "html", "i", "img", "input", "ins", "kbd", "label", "legend", "li", "main", "map", "mark", "marquee", "menu", "menuitem", "meter", "nav", "nobr", "ol", "optgroup", "option", "output", "p", "picture", "pre", "progress", "q", "rp", "rt", "ruby", "s", "samp", "search", "section", "select", "shadow", "slot", "small", "source", "spacer", "span", "strike", "strong", "style", "sub", "summary", "sup", "table", "tbody", "td", "template", "textarea", "tfoot", "th", "thead", "time", "tr", "track", "tt", "u", "ul", "var", "video", "wbr"]);
const svg$1 = freeze(["svg", "a", "altglyph", "altglyphdef", "altglyphitem", "animatecolor", "animatemotion", "animatetransform", "circle", "clippath", "defs", "desc", "ellipse", "enterkeyhint", "exportparts", "filter", "font", "g", "glyph", "glyphref", "hkern", "image", "inputmode", "line", "lineargradient", "marker", "mask", "metadata", "mpath", "part", "path", "pattern", "polygon", "polyline", "radialgradient", "rect", "stop", "style", "switch", "symbol", "text", "textpath", "title", "tref", "tspan", "view", "vkern"]);
const svgFilters = freeze(["feBlend", "feColorMatrix", "feComponentTransfer", "feComposite", "feConvolveMatrix", "feDiffuseLighting", "feDisplacementMap", "feDistantLight", "feDropShadow", "feFlood", "feFuncA", "feFuncB", "feFuncG", "feFuncR", "feGaussianBlur", "feImage", "feMerge", "feMergeNode", "feMorphology", "feOffset", "fePointLight", "feSpecularLighting", "feSpotLight", "feTile", "feTurbulence"]);
const svgDisallowed = freeze(["animate", "color-profile", "cursor", "discard", "font-face", "font-face-format", "font-face-name", "font-face-src", "font-face-uri", "foreignobject", "hatch", "hatchpath", "mesh", "meshgradient", "meshpatch", "meshrow", "missing-glyph", "script", "set", "solidcolor", "unknown", "use"]);
const mathMl$1 = freeze(["math", "menclose", "merror", "mfenced", "mfrac", "mglyph", "mi", "mlabeledtr", "mmultiscripts", "mn", "mo", "mover", "mpadded", "mphantom", "mroot", "mrow", "ms", "mspace", "msqrt", "mstyle", "msub", "msup", "msubsup", "mtable", "mtd", "mtext", "mtr", "munder", "munderover", "mprescripts"]);
const mathMlDisallowed = freeze(["maction", "maligngroup", "malignmark", "mlongdiv", "mscarries", "mscarry", "msgroup", "mstack", "msline", "msrow", "semantics", "annotation", "annotation-xml", "mprescripts", "none"]);
const text = freeze(["#text"]);
const html = freeze(["accept", "action", "align", "alt", "autocapitalize", "autocomplete", "autopictureinpicture", "autoplay", "background", "bgcolor", "border", "capture", "cellpadding", "cellspacing", "checked", "cite", "class", "clear", "color", "cols", "colspan", "controls", "controlslist", "coords", "crossorigin", "datetime", "decoding", "default", "dir", "disabled", "disablepictureinpicture", "disableremoteplayback", "download", "draggable", "enctype", "enterkeyhint", "exportparts", "face", "for", "headers", "height", "hidden", "high", "href", "hreflang", "id", "inert", "inputmode", "integrity", "ismap", "kind", "label", "lang", "list", "loading", "loop", "low", "max", "maxlength", "media", "method", "min", "minlength", "multiple", "muted", "name", "nonce", "noshade", "novalidate", "nowrap", "open", "optimum", "part", "pattern", "placeholder", "playsinline", "popover", "popovertarget", "popovertargetaction", "poster", "preload", "pubdate", "radiogroup", "readonly", "rel", "required", "rev", "reversed", "role", "rows", "rowspan", "spellcheck", "scope", "selected", "shape", "size", "sizes", "slot", "span", "srclang", "start", "src", "srcset", "step", "style", "summary", "tabindex", "title", "translate", "type", "usemap", "valign", "value", "width", "wrap", "xmlns", "slot"]);
const svg = freeze(["accent-height", "accumulate", "additive", "alignment-baseline", "amplitude", "ascent", "attributename", "attributetype", "azimuth", "basefrequency", "baseline-shift", "begin", "bias", "by", "class", "clip", "clippathunits", "clip-path", "clip-rule", "color", "color-interpolation", "color-interpolation-filters", "color-profile", "color-rendering", "cx", "cy", "d", "dx", "dy", "diffuseconstant", "direction", "display", "divisor", "dur", "edgemode", "elevation", "end", "exponent", "fill", "fill-opacity", "fill-rule", "filter", "filterunits", "flood-color", "flood-opacity", "font-family", "font-size", "font-size-adjust", "font-stretch", "font-style", "font-variant", "font-weight", "fx", "fy", "g1", "g2", "glyph-name", "glyphref", "gradientunits", "gradienttransform", "height", "href", "id", "image-rendering", "in", "in2", "intercept", "k", "k1", "k2", "k3", "k4", "kerning", "keypoints", "keysplines", "keytimes", "lang", "lengthadjust", "letter-spacing", "kernelmatrix", "kernelunitlength", "lighting-color", "local", "marker-end", "marker-mid", "marker-start", "markerheight", "markerunits", "markerwidth", "maskcontentunits", "maskunits", "max", "mask", "mask-type", "media", "method", "mode", "min", "name", "numoctaves", "offset", "operator", "opacity", "order", "orient", "orientation", "origin", "overflow", "paint-order", "path", "pathlength", "patterncontentunits", "patterntransform", "patternunits", "points", "preservealpha", "preserveaspectratio", "primitiveunits", "r", "rx", "ry", "radius", "refx", "refy", "repeatcount", "repeatdur", "restart", "result", "rotate", "scale", "seed", "shape-rendering", "slope", "specularconstant", "specularexponent", "spreadmethod", "startoffset", "stddeviation", "stitchtiles", "stop-color", "stop-opacity", "stroke-dasharray", "stroke-dashoffset", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "stroke-opacity", "stroke", "stroke-width", "style", "surfacescale", "systemlanguage", "tabindex", "tablevalues", "targetx", "targety", "transform", "transform-origin", "text-anchor", "text-decoration", "text-rendering", "textlength", "type", "u1", "u2", "unicode", "values", "viewbox", "visibility", "version", "vert-adv-y", "vert-origin-x", "vert-origin-y", "width", "word-spacing", "wrap", "writing-mode", "xchannelselector", "ychannelselector", "x", "x1", "x2", "xmlns", "y", "y1", "y2", "z", "zoomandpan"]);
const mathMl = freeze(["accent", "accentunder", "align", "bevelled", "close", "columnsalign", "columnlines", "columnspan", "denomalign", "depth", "dir", "display", "displaystyle", "encoding", "fence", "frame", "height", "href", "id", "largeop", "length", "linethickness", "lspace", "lquote", "mathbackground", "mathcolor", "mathsize", "mathvariant", "maxsize", "minsize", "movablelimits", "notation", "numalign", "open", "rowalign", "rowlines", "rowspacing", "rowspan", "rspace", "rquote", "scriptlevel", "scriptminsize", "scriptsizemultiplier", "selection", "separator", "separators", "stretchy", "subscriptshift", "supscriptshift", "symmetric", "voffset", "width", "xmlns"]);
const xml = freeze(["xlink:href", "xml:id", "xlink:title", "xml:space", "xmlns:xlink"]);
const MUSTACHE_EXPR = seal(/\{\{[\w\W]*|[\w\W]*\}\}/gm);
const ERB_EXPR = seal(/<%[\w\W]*|[\w\W]*%>/gm);
const TMPLIT_EXPR = seal(/\$\{[\w\W]*/gm);
const DATA_ATTR = seal(/^data-[\-\w.\u00B7-\uFFFF]+$/);
const ARIA_ATTR = seal(/^aria-[\-\w]+$/);
const IS_ALLOWED_URI = seal(
  /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i
  // eslint-disable-line no-useless-escape
);
const IS_SCRIPT_OR_DATA = seal(/^(?:\w+script|data):/i);
const ATTR_WHITESPACE = seal(
  /[\u0000-\u0020\u00A0\u1680\u180E\u2000-\u2029\u205F\u3000]/g
  // eslint-disable-line no-control-regex
);
const DOCTYPE_NAME = seal(/^html$/i);
const CUSTOM_ELEMENT = seal(/^[a-z][.\w]*(-[.\w]+)+$/i);
var EXPRESSIONS = /* @__PURE__ */ Object.freeze({
  __proto__: null,
  ARIA_ATTR,
  ATTR_WHITESPACE,
  CUSTOM_ELEMENT,
  DATA_ATTR,
  DOCTYPE_NAME,
  ERB_EXPR,
  IS_ALLOWED_URI,
  IS_SCRIPT_OR_DATA,
  MUSTACHE_EXPR,
  TMPLIT_EXPR
});
const NODE_TYPE = {
  element: 1,
  text: 3,
  // Deprecated
  progressingInstruction: 7,
  comment: 8,
  document: 9
};
const getGlobal = function getGlobal2() {
  return typeof window === "undefined" ? null : window;
};
const _createTrustedTypesPolicy = function _createTrustedTypesPolicy2(trustedTypes, purifyHostElement) {
  if (typeof trustedTypes !== "object" || typeof trustedTypes.createPolicy !== "function") {
    return null;
  }
  let suffix = null;
  const ATTR_NAME = "data-tt-policy-suffix";
  if (purifyHostElement && purifyHostElement.hasAttribute(ATTR_NAME)) {
    suffix = purifyHostElement.getAttribute(ATTR_NAME);
  }
  const policyName = "dompurify" + (suffix ? "#" + suffix : "");
  try {
    return trustedTypes.createPolicy(policyName, {
      createHTML(html2) {
        return html2;
      },
      createScriptURL(scriptUrl) {
        return scriptUrl;
      }
    });
  } catch (_2) {
    console.warn("TrustedTypes policy " + policyName + " could not be created.");
    return null;
  }
};
const _createHooksMap = function _createHooksMap2() {
  return {
    afterSanitizeAttributes: [],
    afterSanitizeElements: [],
    afterSanitizeShadowDOM: [],
    beforeSanitizeAttributes: [],
    beforeSanitizeElements: [],
    beforeSanitizeShadowDOM: [],
    uponSanitizeAttribute: [],
    uponSanitizeElement: [],
    uponSanitizeShadowNode: []
  };
};
function createDOMPurify() {
  let window2 = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : getGlobal();
  const DOMPurify = (root2) => createDOMPurify(root2);
  DOMPurify.version = "3.3.1";
  DOMPurify.removed = [];
  if (!window2 || !window2.document || window2.document.nodeType !== NODE_TYPE.document || !window2.Element) {
    DOMPurify.isSupported = false;
    return DOMPurify;
  }
  let {
    document: document2
  } = window2;
  const originalDocument = document2;
  const currentScript = originalDocument.currentScript;
  const {
    DocumentFragment,
    HTMLTemplateElement,
    Node: Node2,
    Element: Element2,
    NodeFilter,
    NamedNodeMap = window2.NamedNodeMap || window2.MozNamedAttrMap,
    HTMLFormElement,
    DOMParser,
    trustedTypes
  } = window2;
  const ElementPrototype = Element2.prototype;
  const cloneNode = lookupGetter(ElementPrototype, "cloneNode");
  const remove = lookupGetter(ElementPrototype, "remove");
  const getNextSibling = lookupGetter(ElementPrototype, "nextSibling");
  const getChildNodes = lookupGetter(ElementPrototype, "childNodes");
  const getParentNode = lookupGetter(ElementPrototype, "parentNode");
  if (typeof HTMLTemplateElement === "function") {
    const template = document2.createElement("template");
    if (template.content && template.content.ownerDocument) {
      document2 = template.content.ownerDocument;
    }
  }
  let trustedTypesPolicy;
  let emptyHTML = "";
  const {
    implementation,
    createNodeIterator,
    createDocumentFragment,
    getElementsByTagName
  } = document2;
  const {
    importNode
  } = originalDocument;
  let hooks = _createHooksMap();
  DOMPurify.isSupported = typeof entries === "function" && typeof getParentNode === "function" && implementation && implementation.createHTMLDocument !== void 0;
  const {
    MUSTACHE_EXPR: MUSTACHE_EXPR2,
    ERB_EXPR: ERB_EXPR2,
    TMPLIT_EXPR: TMPLIT_EXPR2,
    DATA_ATTR: DATA_ATTR2,
    ARIA_ATTR: ARIA_ATTR2,
    IS_SCRIPT_OR_DATA: IS_SCRIPT_OR_DATA2,
    ATTR_WHITESPACE: ATTR_WHITESPACE2,
    CUSTOM_ELEMENT: CUSTOM_ELEMENT2
  } = EXPRESSIONS;
  let {
    IS_ALLOWED_URI: IS_ALLOWED_URI$1
  } = EXPRESSIONS;
  let ALLOWED_TAGS = null;
  const DEFAULT_ALLOWED_TAGS = addToSet({}, [...html$1, ...svg$1, ...svgFilters, ...mathMl$1, ...text]);
  let ALLOWED_ATTR = null;
  const DEFAULT_ALLOWED_ATTR = addToSet({}, [...html, ...svg, ...mathMl, ...xml]);
  let CUSTOM_ELEMENT_HANDLING = Object.seal(create(null, {
    tagNameCheck: {
      writable: true,
      configurable: false,
      enumerable: true,
      value: null
    },
    attributeNameCheck: {
      writable: true,
      configurable: false,
      enumerable: true,
      value: null
    },
    allowCustomizedBuiltInElements: {
      writable: true,
      configurable: false,
      enumerable: true,
      value: false
    }
  }));
  let FORBID_TAGS = null;
  let FORBID_ATTR = null;
  const EXTRA_ELEMENT_HANDLING = Object.seal(create(null, {
    tagCheck: {
      writable: true,
      configurable: false,
      enumerable: true,
      value: null
    },
    attributeCheck: {
      writable: true,
      configurable: false,
      enumerable: true,
      value: null
    }
  }));
  let ALLOW_ARIA_ATTR = true;
  let ALLOW_DATA_ATTR = true;
  let ALLOW_UNKNOWN_PROTOCOLS = false;
  let ALLOW_SELF_CLOSE_IN_ATTR = true;
  let SAFE_FOR_TEMPLATES = false;
  let SAFE_FOR_XML = true;
  let WHOLE_DOCUMENT = false;
  let SET_CONFIG = false;
  let FORCE_BODY = false;
  let RETURN_DOM = false;
  let RETURN_DOM_FRAGMENT = false;
  let RETURN_TRUSTED_TYPE = false;
  let SANITIZE_DOM = true;
  let SANITIZE_NAMED_PROPS = false;
  const SANITIZE_NAMED_PROPS_PREFIX = "user-content-";
  let KEEP_CONTENT = true;
  let IN_PLACE = false;
  let USE_PROFILES = {};
  let FORBID_CONTENTS = null;
  const DEFAULT_FORBID_CONTENTS = addToSet({}, ["annotation-xml", "audio", "colgroup", "desc", "foreignobject", "head", "iframe", "math", "mi", "mn", "mo", "ms", "mtext", "noembed", "noframes", "noscript", "plaintext", "script", "style", "svg", "template", "thead", "title", "video", "xmp"]);
  let DATA_URI_TAGS = null;
  const DEFAULT_DATA_URI_TAGS = addToSet({}, ["audio", "video", "img", "source", "image", "track"]);
  let URI_SAFE_ATTRIBUTES = null;
  const DEFAULT_URI_SAFE_ATTRIBUTES = addToSet({}, ["alt", "class", "for", "id", "label", "name", "pattern", "placeholder", "role", "summary", "title", "value", "style", "xmlns"]);
  const MATHML_NAMESPACE = "http://www.w3.org/1998/Math/MathML";
  const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
  const HTML_NAMESPACE = "http://www.w3.org/1999/xhtml";
  let NAMESPACE = HTML_NAMESPACE;
  let IS_EMPTY_INPUT = false;
  let ALLOWED_NAMESPACES = null;
  const DEFAULT_ALLOWED_NAMESPACES = addToSet({}, [MATHML_NAMESPACE, SVG_NAMESPACE, HTML_NAMESPACE], stringToString);
  let MATHML_TEXT_INTEGRATION_POINTS = addToSet({}, ["mi", "mo", "mn", "ms", "mtext"]);
  let HTML_INTEGRATION_POINTS = addToSet({}, ["annotation-xml"]);
  const COMMON_SVG_AND_HTML_ELEMENTS = addToSet({}, ["title", "style", "font", "a", "script"]);
  let PARSER_MEDIA_TYPE = null;
  const SUPPORTED_PARSER_MEDIA_TYPES = ["application/xhtml+xml", "text/html"];
  const DEFAULT_PARSER_MEDIA_TYPE = "text/html";
  let transformCaseFunc = null;
  let CONFIG = null;
  const formElement = document2.createElement("form");
  const isRegexOrFunction = function isRegexOrFunction2(testValue) {
    return testValue instanceof RegExp || testValue instanceof Function;
  };
  const _parseConfig = function _parseConfig2() {
    let cfg = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
    if (CONFIG && CONFIG === cfg) {
      return;
    }
    if (!cfg || typeof cfg !== "object") {
      cfg = {};
    }
    cfg = clone(cfg);
    PARSER_MEDIA_TYPE = // eslint-disable-next-line unicorn/prefer-includes
    SUPPORTED_PARSER_MEDIA_TYPES.indexOf(cfg.PARSER_MEDIA_TYPE) === -1 ? DEFAULT_PARSER_MEDIA_TYPE : cfg.PARSER_MEDIA_TYPE;
    transformCaseFunc = PARSER_MEDIA_TYPE === "application/xhtml+xml" ? stringToString : stringToLowerCase;
    ALLOWED_TAGS = objectHasOwnProperty(cfg, "ALLOWED_TAGS") ? addToSet({}, cfg.ALLOWED_TAGS, transformCaseFunc) : DEFAULT_ALLOWED_TAGS;
    ALLOWED_ATTR = objectHasOwnProperty(cfg, "ALLOWED_ATTR") ? addToSet({}, cfg.ALLOWED_ATTR, transformCaseFunc) : DEFAULT_ALLOWED_ATTR;
    ALLOWED_NAMESPACES = objectHasOwnProperty(cfg, "ALLOWED_NAMESPACES") ? addToSet({}, cfg.ALLOWED_NAMESPACES, stringToString) : DEFAULT_ALLOWED_NAMESPACES;
    URI_SAFE_ATTRIBUTES = objectHasOwnProperty(cfg, "ADD_URI_SAFE_ATTR") ? addToSet(clone(DEFAULT_URI_SAFE_ATTRIBUTES), cfg.ADD_URI_SAFE_ATTR, transformCaseFunc) : DEFAULT_URI_SAFE_ATTRIBUTES;
    DATA_URI_TAGS = objectHasOwnProperty(cfg, "ADD_DATA_URI_TAGS") ? addToSet(clone(DEFAULT_DATA_URI_TAGS), cfg.ADD_DATA_URI_TAGS, transformCaseFunc) : DEFAULT_DATA_URI_TAGS;
    FORBID_CONTENTS = objectHasOwnProperty(cfg, "FORBID_CONTENTS") ? addToSet({}, cfg.FORBID_CONTENTS, transformCaseFunc) : DEFAULT_FORBID_CONTENTS;
    FORBID_TAGS = objectHasOwnProperty(cfg, "FORBID_TAGS") ? addToSet({}, cfg.FORBID_TAGS, transformCaseFunc) : clone({});
    FORBID_ATTR = objectHasOwnProperty(cfg, "FORBID_ATTR") ? addToSet({}, cfg.FORBID_ATTR, transformCaseFunc) : clone({});
    USE_PROFILES = objectHasOwnProperty(cfg, "USE_PROFILES") ? cfg.USE_PROFILES : false;
    ALLOW_ARIA_ATTR = cfg.ALLOW_ARIA_ATTR !== false;
    ALLOW_DATA_ATTR = cfg.ALLOW_DATA_ATTR !== false;
    ALLOW_UNKNOWN_PROTOCOLS = cfg.ALLOW_UNKNOWN_PROTOCOLS || false;
    ALLOW_SELF_CLOSE_IN_ATTR = cfg.ALLOW_SELF_CLOSE_IN_ATTR !== false;
    SAFE_FOR_TEMPLATES = cfg.SAFE_FOR_TEMPLATES || false;
    SAFE_FOR_XML = cfg.SAFE_FOR_XML !== false;
    WHOLE_DOCUMENT = cfg.WHOLE_DOCUMENT || false;
    RETURN_DOM = cfg.RETURN_DOM || false;
    RETURN_DOM_FRAGMENT = cfg.RETURN_DOM_FRAGMENT || false;
    RETURN_TRUSTED_TYPE = cfg.RETURN_TRUSTED_TYPE || false;
    FORCE_BODY = cfg.FORCE_BODY || false;
    SANITIZE_DOM = cfg.SANITIZE_DOM !== false;
    SANITIZE_NAMED_PROPS = cfg.SANITIZE_NAMED_PROPS || false;
    KEEP_CONTENT = cfg.KEEP_CONTENT !== false;
    IN_PLACE = cfg.IN_PLACE || false;
    IS_ALLOWED_URI$1 = cfg.ALLOWED_URI_REGEXP || IS_ALLOWED_URI;
    NAMESPACE = cfg.NAMESPACE || HTML_NAMESPACE;
    MATHML_TEXT_INTEGRATION_POINTS = cfg.MATHML_TEXT_INTEGRATION_POINTS || MATHML_TEXT_INTEGRATION_POINTS;
    HTML_INTEGRATION_POINTS = cfg.HTML_INTEGRATION_POINTS || HTML_INTEGRATION_POINTS;
    CUSTOM_ELEMENT_HANDLING = cfg.CUSTOM_ELEMENT_HANDLING || {};
    if (cfg.CUSTOM_ELEMENT_HANDLING && isRegexOrFunction(cfg.CUSTOM_ELEMENT_HANDLING.tagNameCheck)) {
      CUSTOM_ELEMENT_HANDLING.tagNameCheck = cfg.CUSTOM_ELEMENT_HANDLING.tagNameCheck;
    }
    if (cfg.CUSTOM_ELEMENT_HANDLING && isRegexOrFunction(cfg.CUSTOM_ELEMENT_HANDLING.attributeNameCheck)) {
      CUSTOM_ELEMENT_HANDLING.attributeNameCheck = cfg.CUSTOM_ELEMENT_HANDLING.attributeNameCheck;
    }
    if (cfg.CUSTOM_ELEMENT_HANDLING && typeof cfg.CUSTOM_ELEMENT_HANDLING.allowCustomizedBuiltInElements === "boolean") {
      CUSTOM_ELEMENT_HANDLING.allowCustomizedBuiltInElements = cfg.CUSTOM_ELEMENT_HANDLING.allowCustomizedBuiltInElements;
    }
    if (SAFE_FOR_TEMPLATES) {
      ALLOW_DATA_ATTR = false;
    }
    if (RETURN_DOM_FRAGMENT) {
      RETURN_DOM = true;
    }
    if (USE_PROFILES) {
      ALLOWED_TAGS = addToSet({}, text);
      ALLOWED_ATTR = [];
      if (USE_PROFILES.html === true) {
        addToSet(ALLOWED_TAGS, html$1);
        addToSet(ALLOWED_ATTR, html);
      }
      if (USE_PROFILES.svg === true) {
        addToSet(ALLOWED_TAGS, svg$1);
        addToSet(ALLOWED_ATTR, svg);
        addToSet(ALLOWED_ATTR, xml);
      }
      if (USE_PROFILES.svgFilters === true) {
        addToSet(ALLOWED_TAGS, svgFilters);
        addToSet(ALLOWED_ATTR, svg);
        addToSet(ALLOWED_ATTR, xml);
      }
      if (USE_PROFILES.mathMl === true) {
        addToSet(ALLOWED_TAGS, mathMl$1);
        addToSet(ALLOWED_ATTR, mathMl);
        addToSet(ALLOWED_ATTR, xml);
      }
    }
    if (cfg.ADD_TAGS) {
      if (typeof cfg.ADD_TAGS === "function") {
        EXTRA_ELEMENT_HANDLING.tagCheck = cfg.ADD_TAGS;
      } else {
        if (ALLOWED_TAGS === DEFAULT_ALLOWED_TAGS) {
          ALLOWED_TAGS = clone(ALLOWED_TAGS);
        }
        addToSet(ALLOWED_TAGS, cfg.ADD_TAGS, transformCaseFunc);
      }
    }
    if (cfg.ADD_ATTR) {
      if (typeof cfg.ADD_ATTR === "function") {
        EXTRA_ELEMENT_HANDLING.attributeCheck = cfg.ADD_ATTR;
      } else {
        if (ALLOWED_ATTR === DEFAULT_ALLOWED_ATTR) {
          ALLOWED_ATTR = clone(ALLOWED_ATTR);
        }
        addToSet(ALLOWED_ATTR, cfg.ADD_ATTR, transformCaseFunc);
      }
    }
    if (cfg.ADD_URI_SAFE_ATTR) {
      addToSet(URI_SAFE_ATTRIBUTES, cfg.ADD_URI_SAFE_ATTR, transformCaseFunc);
    }
    if (cfg.FORBID_CONTENTS) {
      if (FORBID_CONTENTS === DEFAULT_FORBID_CONTENTS) {
        FORBID_CONTENTS = clone(FORBID_CONTENTS);
      }
      addToSet(FORBID_CONTENTS, cfg.FORBID_CONTENTS, transformCaseFunc);
    }
    if (cfg.ADD_FORBID_CONTENTS) {
      if (FORBID_CONTENTS === DEFAULT_FORBID_CONTENTS) {
        FORBID_CONTENTS = clone(FORBID_CONTENTS);
      }
      addToSet(FORBID_CONTENTS, cfg.ADD_FORBID_CONTENTS, transformCaseFunc);
    }
    if (KEEP_CONTENT) {
      ALLOWED_TAGS["#text"] = true;
    }
    if (WHOLE_DOCUMENT) {
      addToSet(ALLOWED_TAGS, ["html", "head", "body"]);
    }
    if (ALLOWED_TAGS.table) {
      addToSet(ALLOWED_TAGS, ["tbody"]);
      delete FORBID_TAGS.tbody;
    }
    if (cfg.TRUSTED_TYPES_POLICY) {
      if (typeof cfg.TRUSTED_TYPES_POLICY.createHTML !== "function") {
        throw typeErrorCreate('TRUSTED_TYPES_POLICY configuration option must provide a "createHTML" hook.');
      }
      if (typeof cfg.TRUSTED_TYPES_POLICY.createScriptURL !== "function") {
        throw typeErrorCreate('TRUSTED_TYPES_POLICY configuration option must provide a "createScriptURL" hook.');
      }
      trustedTypesPolicy = cfg.TRUSTED_TYPES_POLICY;
      emptyHTML = trustedTypesPolicy.createHTML("");
    } else {
      if (trustedTypesPolicy === void 0) {
        trustedTypesPolicy = _createTrustedTypesPolicy(trustedTypes, currentScript);
      }
      if (trustedTypesPolicy !== null && typeof emptyHTML === "string") {
        emptyHTML = trustedTypesPolicy.createHTML("");
      }
    }
    if (freeze) {
      freeze(cfg);
    }
    CONFIG = cfg;
  };
  const ALL_SVG_TAGS = addToSet({}, [...svg$1, ...svgFilters, ...svgDisallowed]);
  const ALL_MATHML_TAGS = addToSet({}, [...mathMl$1, ...mathMlDisallowed]);
  const _checkValidNamespace = function _checkValidNamespace2(element) {
    let parent = getParentNode(element);
    if (!parent || !parent.tagName) {
      parent = {
        namespaceURI: NAMESPACE,
        tagName: "template"
      };
    }
    const tagName = stringToLowerCase(element.tagName);
    const parentTagName = stringToLowerCase(parent.tagName);
    if (!ALLOWED_NAMESPACES[element.namespaceURI]) {
      return false;
    }
    if (element.namespaceURI === SVG_NAMESPACE) {
      if (parent.namespaceURI === HTML_NAMESPACE) {
        return tagName === "svg";
      }
      if (parent.namespaceURI === MATHML_NAMESPACE) {
        return tagName === "svg" && (parentTagName === "annotation-xml" || MATHML_TEXT_INTEGRATION_POINTS[parentTagName]);
      }
      return Boolean(ALL_SVG_TAGS[tagName]);
    }
    if (element.namespaceURI === MATHML_NAMESPACE) {
      if (parent.namespaceURI === HTML_NAMESPACE) {
        return tagName === "math";
      }
      if (parent.namespaceURI === SVG_NAMESPACE) {
        return tagName === "math" && HTML_INTEGRATION_POINTS[parentTagName];
      }
      return Boolean(ALL_MATHML_TAGS[tagName]);
    }
    if (element.namespaceURI === HTML_NAMESPACE) {
      if (parent.namespaceURI === SVG_NAMESPACE && !HTML_INTEGRATION_POINTS[parentTagName]) {
        return false;
      }
      if (parent.namespaceURI === MATHML_NAMESPACE && !MATHML_TEXT_INTEGRATION_POINTS[parentTagName]) {
        return false;
      }
      return !ALL_MATHML_TAGS[tagName] && (COMMON_SVG_AND_HTML_ELEMENTS[tagName] || !ALL_SVG_TAGS[tagName]);
    }
    if (PARSER_MEDIA_TYPE === "application/xhtml+xml" && ALLOWED_NAMESPACES[element.namespaceURI]) {
      return true;
    }
    return false;
  };
  const _forceRemove = function _forceRemove2(node) {
    arrayPush(DOMPurify.removed, {
      element: node
    });
    try {
      getParentNode(node).removeChild(node);
    } catch (_2) {
      remove(node);
    }
  };
  const _removeAttribute = function _removeAttribute2(name, element) {
    try {
      arrayPush(DOMPurify.removed, {
        attribute: element.getAttributeNode(name),
        from: element
      });
    } catch (_2) {
      arrayPush(DOMPurify.removed, {
        attribute: null,
        from: element
      });
    }
    element.removeAttribute(name);
    if (name === "is") {
      if (RETURN_DOM || RETURN_DOM_FRAGMENT) {
        try {
          _forceRemove(element);
        } catch (_2) {
        }
      } else {
        try {
          element.setAttribute(name, "");
        } catch (_2) {
        }
      }
    }
  };
  const _initDocument = function _initDocument2(dirty) {
    let doc = null;
    let leadingWhitespace = null;
    if (FORCE_BODY) {
      dirty = "<remove></remove>" + dirty;
    } else {
      const matches = stringMatch(dirty, /^[\r\n\t ]+/);
      leadingWhitespace = matches && matches[0];
    }
    if (PARSER_MEDIA_TYPE === "application/xhtml+xml" && NAMESPACE === HTML_NAMESPACE) {
      dirty = '<html xmlns="http://www.w3.org/1999/xhtml"><head></head><body>' + dirty + "</body></html>";
    }
    const dirtyPayload = trustedTypesPolicy ? trustedTypesPolicy.createHTML(dirty) : dirty;
    if (NAMESPACE === HTML_NAMESPACE) {
      try {
        doc = new DOMParser().parseFromString(dirtyPayload, PARSER_MEDIA_TYPE);
      } catch (_2) {
      }
    }
    if (!doc || !doc.documentElement) {
      doc = implementation.createDocument(NAMESPACE, "template", null);
      try {
        doc.documentElement.innerHTML = IS_EMPTY_INPUT ? emptyHTML : dirtyPayload;
      } catch (_2) {
      }
    }
    const body = doc.body || doc.documentElement;
    if (dirty && leadingWhitespace) {
      body.insertBefore(document2.createTextNode(leadingWhitespace), body.childNodes[0] || null);
    }
    if (NAMESPACE === HTML_NAMESPACE) {
      return getElementsByTagName.call(doc, WHOLE_DOCUMENT ? "html" : "body")[0];
    }
    return WHOLE_DOCUMENT ? doc.documentElement : body;
  };
  const _createNodeIterator = function _createNodeIterator2(root2) {
    return createNodeIterator.call(
      root2.ownerDocument || root2,
      root2,
      // eslint-disable-next-line no-bitwise
      NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_COMMENT | NodeFilter.SHOW_TEXT | NodeFilter.SHOW_PROCESSING_INSTRUCTION | NodeFilter.SHOW_CDATA_SECTION,
      null
    );
  };
  const _isClobbered = function _isClobbered2(element) {
    return element instanceof HTMLFormElement && (typeof element.nodeName !== "string" || typeof element.textContent !== "string" || typeof element.removeChild !== "function" || !(element.attributes instanceof NamedNodeMap) || typeof element.removeAttribute !== "function" || typeof element.setAttribute !== "function" || typeof element.namespaceURI !== "string" || typeof element.insertBefore !== "function" || typeof element.hasChildNodes !== "function");
  };
  const _isNode = function _isNode2(value) {
    return typeof Node2 === "function" && value instanceof Node2;
  };
  function _executeHooks(hooks2, currentNode, data) {
    arrayForEach(hooks2, (hook) => {
      hook.call(DOMPurify, currentNode, data, CONFIG);
    });
  }
  const _sanitizeElements = function _sanitizeElements2(currentNode) {
    let content = null;
    _executeHooks(hooks.beforeSanitizeElements, currentNode, null);
    if (_isClobbered(currentNode)) {
      _forceRemove(currentNode);
      return true;
    }
    const tagName = transformCaseFunc(currentNode.nodeName);
    _executeHooks(hooks.uponSanitizeElement, currentNode, {
      tagName,
      allowedTags: ALLOWED_TAGS
    });
    if (SAFE_FOR_XML && currentNode.hasChildNodes() && !_isNode(currentNode.firstElementChild) && regExpTest(/<[/\w!]/g, currentNode.innerHTML) && regExpTest(/<[/\w!]/g, currentNode.textContent)) {
      _forceRemove(currentNode);
      return true;
    }
    if (currentNode.nodeType === NODE_TYPE.progressingInstruction) {
      _forceRemove(currentNode);
      return true;
    }
    if (SAFE_FOR_XML && currentNode.nodeType === NODE_TYPE.comment && regExpTest(/<[/\w]/g, currentNode.data)) {
      _forceRemove(currentNode);
      return true;
    }
    if (!(EXTRA_ELEMENT_HANDLING.tagCheck instanceof Function && EXTRA_ELEMENT_HANDLING.tagCheck(tagName)) && (!ALLOWED_TAGS[tagName] || FORBID_TAGS[tagName])) {
      if (!FORBID_TAGS[tagName] && _isBasicCustomElement(tagName)) {
        if (CUSTOM_ELEMENT_HANDLING.tagNameCheck instanceof RegExp && regExpTest(CUSTOM_ELEMENT_HANDLING.tagNameCheck, tagName)) {
          return false;
        }
        if (CUSTOM_ELEMENT_HANDLING.tagNameCheck instanceof Function && CUSTOM_ELEMENT_HANDLING.tagNameCheck(tagName)) {
          return false;
        }
      }
      if (KEEP_CONTENT && !FORBID_CONTENTS[tagName]) {
        const parentNode = getParentNode(currentNode) || currentNode.parentNode;
        const childNodes = getChildNodes(currentNode) || currentNode.childNodes;
        if (childNodes && parentNode) {
          const childCount = childNodes.length;
          for (let i2 = childCount - 1; i2 >= 0; --i2) {
            const childClone = cloneNode(childNodes[i2], true);
            childClone.__removalCount = (currentNode.__removalCount || 0) + 1;
            parentNode.insertBefore(childClone, getNextSibling(currentNode));
          }
        }
      }
      _forceRemove(currentNode);
      return true;
    }
    if (currentNode instanceof Element2 && !_checkValidNamespace(currentNode)) {
      _forceRemove(currentNode);
      return true;
    }
    if ((tagName === "noscript" || tagName === "noembed" || tagName === "noframes") && regExpTest(/<\/no(script|embed|frames)/i, currentNode.innerHTML)) {
      _forceRemove(currentNode);
      return true;
    }
    if (SAFE_FOR_TEMPLATES && currentNode.nodeType === NODE_TYPE.text) {
      content = currentNode.textContent;
      arrayForEach([MUSTACHE_EXPR2, ERB_EXPR2, TMPLIT_EXPR2], (expr) => {
        content = stringReplace(content, expr, " ");
      });
      if (currentNode.textContent !== content) {
        arrayPush(DOMPurify.removed, {
          element: currentNode.cloneNode()
        });
        currentNode.textContent = content;
      }
    }
    _executeHooks(hooks.afterSanitizeElements, currentNode, null);
    return false;
  };
  const _isValidAttribute = function _isValidAttribute2(lcTag, lcName, value) {
    if (SANITIZE_DOM && (lcName === "id" || lcName === "name") && (value in document2 || value in formElement)) {
      return false;
    }
    if (ALLOW_DATA_ATTR && !FORBID_ATTR[lcName] && regExpTest(DATA_ATTR2, lcName)) ;
    else if (ALLOW_ARIA_ATTR && regExpTest(ARIA_ATTR2, lcName)) ;
    else if (EXTRA_ELEMENT_HANDLING.attributeCheck instanceof Function && EXTRA_ELEMENT_HANDLING.attributeCheck(lcName, lcTag)) ;
    else if (!ALLOWED_ATTR[lcName] || FORBID_ATTR[lcName]) {
      if (
        // First condition does a very basic check if a) it's basically a valid custom element tagname AND
        // b) if the tagName passes whatever the user has configured for CUSTOM_ELEMENT_HANDLING.tagNameCheck
        // and c) if the attribute name passes whatever the user has configured for CUSTOM_ELEMENT_HANDLING.attributeNameCheck
        _isBasicCustomElement(lcTag) && (CUSTOM_ELEMENT_HANDLING.tagNameCheck instanceof RegExp && regExpTest(CUSTOM_ELEMENT_HANDLING.tagNameCheck, lcTag) || CUSTOM_ELEMENT_HANDLING.tagNameCheck instanceof Function && CUSTOM_ELEMENT_HANDLING.tagNameCheck(lcTag)) && (CUSTOM_ELEMENT_HANDLING.attributeNameCheck instanceof RegExp && regExpTest(CUSTOM_ELEMENT_HANDLING.attributeNameCheck, lcName) || CUSTOM_ELEMENT_HANDLING.attributeNameCheck instanceof Function && CUSTOM_ELEMENT_HANDLING.attributeNameCheck(lcName, lcTag)) || // Alternative, second condition checks if it's an `is`-attribute, AND
        // the value passes whatever the user has configured for CUSTOM_ELEMENT_HANDLING.tagNameCheck
        lcName === "is" && CUSTOM_ELEMENT_HANDLING.allowCustomizedBuiltInElements && (CUSTOM_ELEMENT_HANDLING.tagNameCheck instanceof RegExp && regExpTest(CUSTOM_ELEMENT_HANDLING.tagNameCheck, value) || CUSTOM_ELEMENT_HANDLING.tagNameCheck instanceof Function && CUSTOM_ELEMENT_HANDLING.tagNameCheck(value))
      ) ;
      else {
        return false;
      }
    } else if (URI_SAFE_ATTRIBUTES[lcName]) ;
    else if (regExpTest(IS_ALLOWED_URI$1, stringReplace(value, ATTR_WHITESPACE2, ""))) ;
    else if ((lcName === "src" || lcName === "xlink:href" || lcName === "href") && lcTag !== "script" && stringIndexOf(value, "data:") === 0 && DATA_URI_TAGS[lcTag]) ;
    else if (ALLOW_UNKNOWN_PROTOCOLS && !regExpTest(IS_SCRIPT_OR_DATA2, stringReplace(value, ATTR_WHITESPACE2, ""))) ;
    else if (value) {
      return false;
    } else ;
    return true;
  };
  const _isBasicCustomElement = function _isBasicCustomElement2(tagName) {
    return tagName !== "annotation-xml" && stringMatch(tagName, CUSTOM_ELEMENT2);
  };
  const _sanitizeAttributes = function _sanitizeAttributes2(currentNode) {
    _executeHooks(hooks.beforeSanitizeAttributes, currentNode, null);
    const {
      attributes
    } = currentNode;
    if (!attributes || _isClobbered(currentNode)) {
      return;
    }
    const hookEvent = {
      attrName: "",
      attrValue: "",
      keepAttr: true,
      allowedAttributes: ALLOWED_ATTR,
      forceKeepAttr: void 0
    };
    let l2 = attributes.length;
    while (l2--) {
      const attr = attributes[l2];
      const {
        name,
        namespaceURI,
        value: attrValue
      } = attr;
      const lcName = transformCaseFunc(name);
      const initValue = attrValue;
      let value = name === "value" ? initValue : stringTrim(initValue);
      hookEvent.attrName = lcName;
      hookEvent.attrValue = value;
      hookEvent.keepAttr = true;
      hookEvent.forceKeepAttr = void 0;
      _executeHooks(hooks.uponSanitizeAttribute, currentNode, hookEvent);
      value = hookEvent.attrValue;
      if (SANITIZE_NAMED_PROPS && (lcName === "id" || lcName === "name")) {
        _removeAttribute(name, currentNode);
        value = SANITIZE_NAMED_PROPS_PREFIX + value;
      }
      if (SAFE_FOR_XML && regExpTest(/((--!?|])>)|<\/(style|title|textarea)/i, value)) {
        _removeAttribute(name, currentNode);
        continue;
      }
      if (lcName === "attributename" && stringMatch(value, "href")) {
        _removeAttribute(name, currentNode);
        continue;
      }
      if (hookEvent.forceKeepAttr) {
        continue;
      }
      if (!hookEvent.keepAttr) {
        _removeAttribute(name, currentNode);
        continue;
      }
      if (!ALLOW_SELF_CLOSE_IN_ATTR && regExpTest(/\/>/i, value)) {
        _removeAttribute(name, currentNode);
        continue;
      }
      if (SAFE_FOR_TEMPLATES) {
        arrayForEach([MUSTACHE_EXPR2, ERB_EXPR2, TMPLIT_EXPR2], (expr) => {
          value = stringReplace(value, expr, " ");
        });
      }
      const lcTag = transformCaseFunc(currentNode.nodeName);
      if (!_isValidAttribute(lcTag, lcName, value)) {
        _removeAttribute(name, currentNode);
        continue;
      }
      if (trustedTypesPolicy && typeof trustedTypes === "object" && typeof trustedTypes.getAttributeType === "function") {
        if (namespaceURI) ;
        else {
          switch (trustedTypes.getAttributeType(lcTag, lcName)) {
            case "TrustedHTML": {
              value = trustedTypesPolicy.createHTML(value);
              break;
            }
            case "TrustedScriptURL": {
              value = trustedTypesPolicy.createScriptURL(value);
              break;
            }
          }
        }
      }
      if (value !== initValue) {
        try {
          if (namespaceURI) {
            currentNode.setAttributeNS(namespaceURI, name, value);
          } else {
            currentNode.setAttribute(name, value);
          }
          if (_isClobbered(currentNode)) {
            _forceRemove(currentNode);
          } else {
            arrayPop(DOMPurify.removed);
          }
        } catch (_2) {
          _removeAttribute(name, currentNode);
        }
      }
    }
    _executeHooks(hooks.afterSanitizeAttributes, currentNode, null);
  };
  const _sanitizeShadowDOM = function _sanitizeShadowDOM2(fragment) {
    let shadowNode = null;
    const shadowIterator = _createNodeIterator(fragment);
    _executeHooks(hooks.beforeSanitizeShadowDOM, fragment, null);
    while (shadowNode = shadowIterator.nextNode()) {
      _executeHooks(hooks.uponSanitizeShadowNode, shadowNode, null);
      _sanitizeElements(shadowNode);
      _sanitizeAttributes(shadowNode);
      if (shadowNode.content instanceof DocumentFragment) {
        _sanitizeShadowDOM2(shadowNode.content);
      }
    }
    _executeHooks(hooks.afterSanitizeShadowDOM, fragment, null);
  };
  DOMPurify.sanitize = function(dirty) {
    let cfg = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {};
    let body = null;
    let importedNode = null;
    let currentNode = null;
    let returnNode = null;
    IS_EMPTY_INPUT = !dirty;
    if (IS_EMPTY_INPUT) {
      dirty = "<!-->";
    }
    if (typeof dirty !== "string" && !_isNode(dirty)) {
      if (typeof dirty.toString === "function") {
        dirty = dirty.toString();
        if (typeof dirty !== "string") {
          throw typeErrorCreate("dirty is not a string, aborting");
        }
      } else {
        throw typeErrorCreate("toString is not a function");
      }
    }
    if (!DOMPurify.isSupported) {
      return dirty;
    }
    if (!SET_CONFIG) {
      _parseConfig(cfg);
    }
    DOMPurify.removed = [];
    if (typeof dirty === "string") {
      IN_PLACE = false;
    }
    if (IN_PLACE) {
      if (dirty.nodeName) {
        const tagName = transformCaseFunc(dirty.nodeName);
        if (!ALLOWED_TAGS[tagName] || FORBID_TAGS[tagName]) {
          throw typeErrorCreate("root node is forbidden and cannot be sanitized in-place");
        }
      }
    } else if (dirty instanceof Node2) {
      body = _initDocument("<!---->");
      importedNode = body.ownerDocument.importNode(dirty, true);
      if (importedNode.nodeType === NODE_TYPE.element && importedNode.nodeName === "BODY") {
        body = importedNode;
      } else if (importedNode.nodeName === "HTML") {
        body = importedNode;
      } else {
        body.appendChild(importedNode);
      }
    } else {
      if (!RETURN_DOM && !SAFE_FOR_TEMPLATES && !WHOLE_DOCUMENT && // eslint-disable-next-line unicorn/prefer-includes
      dirty.indexOf("<") === -1) {
        return trustedTypesPolicy && RETURN_TRUSTED_TYPE ? trustedTypesPolicy.createHTML(dirty) : dirty;
      }
      body = _initDocument(dirty);
      if (!body) {
        return RETURN_DOM ? null : RETURN_TRUSTED_TYPE ? emptyHTML : "";
      }
    }
    if (body && FORCE_BODY) {
      _forceRemove(body.firstChild);
    }
    const nodeIterator = _createNodeIterator(IN_PLACE ? dirty : body);
    while (currentNode = nodeIterator.nextNode()) {
      _sanitizeElements(currentNode);
      _sanitizeAttributes(currentNode);
      if (currentNode.content instanceof DocumentFragment) {
        _sanitizeShadowDOM(currentNode.content);
      }
    }
    if (IN_PLACE) {
      return dirty;
    }
    if (RETURN_DOM) {
      if (RETURN_DOM_FRAGMENT) {
        returnNode = createDocumentFragment.call(body.ownerDocument);
        while (body.firstChild) {
          returnNode.appendChild(body.firstChild);
        }
      } else {
        returnNode = body;
      }
      if (ALLOWED_ATTR.shadowroot || ALLOWED_ATTR.shadowrootmode) {
        returnNode = importNode.call(originalDocument, returnNode, true);
      }
      return returnNode;
    }
    let serializedHTML = WHOLE_DOCUMENT ? body.outerHTML : body.innerHTML;
    if (WHOLE_DOCUMENT && ALLOWED_TAGS["!doctype"] && body.ownerDocument && body.ownerDocument.doctype && body.ownerDocument.doctype.name && regExpTest(DOCTYPE_NAME, body.ownerDocument.doctype.name)) {
      serializedHTML = "<!DOCTYPE " + body.ownerDocument.doctype.name + ">\n" + serializedHTML;
    }
    if (SAFE_FOR_TEMPLATES) {
      arrayForEach([MUSTACHE_EXPR2, ERB_EXPR2, TMPLIT_EXPR2], (expr) => {
        serializedHTML = stringReplace(serializedHTML, expr, " ");
      });
    }
    return trustedTypesPolicy && RETURN_TRUSTED_TYPE ? trustedTypesPolicy.createHTML(serializedHTML) : serializedHTML;
  };
  DOMPurify.setConfig = function() {
    let cfg = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
    _parseConfig(cfg);
    SET_CONFIG = true;
  };
  DOMPurify.clearConfig = function() {
    CONFIG = null;
    SET_CONFIG = false;
  };
  DOMPurify.isValidAttribute = function(tag, attr, value) {
    if (!CONFIG) {
      _parseConfig({});
    }
    const lcTag = transformCaseFunc(tag);
    const lcName = transformCaseFunc(attr);
    return _isValidAttribute(lcTag, lcName, value);
  };
  DOMPurify.addHook = function(entryPoint, hookFunction) {
    if (typeof hookFunction !== "function") {
      return;
    }
    arrayPush(hooks[entryPoint], hookFunction);
  };
  DOMPurify.removeHook = function(entryPoint, hookFunction) {
    if (hookFunction !== void 0) {
      const index2 = arrayLastIndexOf(hooks[entryPoint], hookFunction);
      return index2 === -1 ? void 0 : arraySplice(hooks[entryPoint], index2, 1)[0];
    }
    return arrayPop(hooks[entryPoint]);
  };
  DOMPurify.removeHooks = function(entryPoint) {
    hooks[entryPoint] = [];
  };
  DOMPurify.removeAllHooks = function() {
    hooks = _createHooksMap();
  };
  return DOMPurify;
}
var purify = createDOMPurify();
Pe.registerLanguage("yaml", hljsGrammar);
d$1.use(
  markedHighlight({
    langPrefix: "hljs language-",
    highlight(code, lang) {
      if (lang && Pe.getLanguage(lang)) {
        return Pe.highlight(code, { language: lang }).value;
      }
      return Pe.highlightAuto(code).value;
    }
  })
);
d$1.use({
  gfm: true,
  breaks: true
});
const markdownCache = /* @__PURE__ */ new Map();
function renderMarkdown(text2, sessionId) {
  if (!text2) return "";
  const cacheKey = sessionId || "default";
  if (!markdownCache.has(cacheKey)) {
    markdownCache.set(cacheKey, /* @__PURE__ */ new Map());
  }
  const sessionCache = markdownCache.get(cacheKey);
  if (sessionCache.has(text2)) {
    return sessionCache.get(text2);
  }
  try {
    const rawHtml = d$1.parse(text2);
    const sanitized = purify.sanitize(rawHtml, {
      ALLOWED_TAGS: [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "br",
        "ul",
        "ol",
        "li",
        "strong",
        "em",
        "code",
        "pre",
        "blockquote",
        "a",
        "span",
        "hr"
      ],
      ALLOWED_ATTR: ["href", "target", "rel", "class"]
    });
    if (sessionCache.size > 100) {
      const firstKey = sessionCache.keys().next().value;
      if (firstKey) {
        sessionCache.delete(firstKey);
      }
    }
    sessionCache.set(text2, sanitized);
    return sanitized;
  } catch (e2) {
    console.error("Markdown rendering error:", e2);
    return text2;
  }
}
function clearSessionCache(sessionId) {
  markdownCache.delete(sessionId);
}
function clearAllCaches() {
  markdownCache.clear();
}
async function loadSessions(hass) {
  sessionState.update((s2) => ({ ...s2, sessionsLoading: true }));
  try {
    const result = await hass.callWS({
      type: "homeclaw/sessions/list"
    });
    const sessions = result.sessions || [];
    sessionState.update((s2) => ({ ...s2, sessions }));
    const state2 = get(sessionState);
    if (sessions.length > 0 && !state2.activeSessionId) {
      await selectSession(hass, sessions[0].session_id);
    }
  } catch (error) {
    console.error("Failed to load sessions:", error);
    appState.update((s2) => ({ ...s2, error: "Could not load conversations" }));
  } finally {
    sessionState.update((s2) => ({ ...s2, sessionsLoading: false }));
  }
}
async function selectSession(hass, sessionId) {
  sessionState.update((s2) => ({ ...s2, activeSessionId: sessionId }));
  appState.update((s2) => ({ ...s2, isLoading: true, error: null }));
  try {
    const result = await hass.callWS({
      type: "homeclaw/sessions/get",
      session_id: sessionId
    });
    const rawMessages = result.messages || [];
    const messages = rawMessages.map((m2, index2) => ({
      id: m2.message_id || `fallback-${sessionId}-${index2}`,
      type: m2.role === "user" ? "user" : "assistant",
      text: m2.content,
      automation: m2.metadata?.automation,
      dashboard: m2.metadata?.dashboard,
      timestamp: m2.timestamp,
      status: m2.status,
      error_message: m2.error_message,
      attachments: m2.attachments
    })).sort((a2, b2) => (a2.timestamp || "").localeCompare(b2.timestamp || ""));
    appState.update((s2) => ({ ...s2, messages }));
    if (typeof window !== "undefined" && window.innerWidth <= 768) {
      const { closeSidebar: closeSidebar2 } = await Promise.resolve().then(() => ui);
      closeSidebar2();
    }
  } catch (error) {
    console.error("Failed to load session:", error);
    appState.update((s2) => ({ ...s2, error: "Could not load conversation" }));
  } finally {
    appState.update((s2) => ({ ...s2, isLoading: false }));
  }
}
async function createSession(hass, provider) {
  console.log("[Session] Creating new session with provider:", provider);
  try {
    const result = await hass.callWS({
      type: "homeclaw/sessions/create",
      provider
    });
    console.log("[Session] Session created:", result);
    sessionState.update((s2) => ({
      ...s2,
      sessions: [result, ...s2.sessions],
      activeSessionId: result.session_id
    }));
    console.log("[Session] Active session ID set to:", result.session_id);
    appState.update((s2) => ({ ...s2, messages: [] }));
    await new Promise((resolve) => setTimeout(resolve, 100));
    console.log("[Session] Waited 100ms for session to be fully saved");
    if (typeof window !== "undefined" && window.innerWidth <= 768) {
      const { closeSidebar: closeSidebar2 } = await Promise.resolve().then(() => ui);
      closeSidebar2();
    }
  } catch (error) {
    console.error("Failed to create session:", error);
    appState.update((s2) => ({ ...s2, error: "Could not create new conversation" }));
  }
}
async function deleteSession(hass, sessionId) {
  try {
    await hass.callWS({
      type: "homeclaw/sessions/delete",
      session_id: sessionId
    });
    sessionState.update((s2) => ({
      ...s2,
      sessions: s2.sessions.filter((session) => session.session_id !== sessionId)
    }));
    clearSessionCache(sessionId);
    const state2 = get(sessionState);
    if (state2.activeSessionId === sessionId) {
      if (state2.sessions.length > 0) {
        await selectSession(hass, state2.sessions[0].session_id);
      } else {
        sessionState.update((s2) => ({ ...s2, activeSessionId: null }));
        appState.update((s2) => ({ ...s2, messages: [] }));
      }
    }
  } catch (error) {
    console.error("Failed to delete session:", error);
    appState.update((s2) => ({ ...s2, error: "Could not delete conversation" }));
  }
}
function updateSessionInList(sessionId, preview, title) {
  sessionState.update((s2) => {
    const updatedSessions = s2.sessions.map((session) => {
      if (session.session_id === sessionId) {
        return {
          ...session,
          preview: preview ? preview.substring(0, 100) : session.preview,
          title: title || session.title,
          message_count: (session.message_count || 0) + 2,
          updated_at: (/* @__PURE__ */ new Date()).toISOString()
        };
      }
      return session;
    });
    const sortedSessions = [...updatedSessions].sort(
      (a2, b2) => new Date(b2.updated_at).getTime() - new Date(a2.updated_at).getTime()
    );
    return { ...s2, sessions: sortedSessions };
  });
  if (title) {
    const hass = get(appState).hass;
    if (hass) {
      generateSessionEmoji(hass, sessionId, title);
    }
  }
}
async function generateSessionEmoji(hass, sessionId, title) {
  try {
    const result = await hass.callWS({
      type: "homeclaw/sessions/generate_emoji",
      session_id: sessionId,
      title
    });
    const emoji = result?.emoji;
    if (emoji) {
      sessionState.update((s2) => ({
        ...s2,
        sessions: s2.sessions.map(
          (session) => session.session_id === sessionId ? { ...session, emoji } : session
        )
      }));
    }
  } catch (error) {
    console.warn("Emoji generation failed:", error);
  }
}
enable_legacy_mode_flag();
var root_1$k = /* @__PURE__ */ from_svg(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svelte-1elxaub"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`);
var root_3$b = /* @__PURE__ */ from_svg(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svelte-1elxaub"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`);
var root_4$b = /* @__PURE__ */ from_svg(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svelte-1elxaub"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>`);
var root$n = /* @__PURE__ */ from_html(`<div class="header svelte-1elxaub"><button class="header-btn back-btn svelte-1elxaub" aria-label="Toggle sidebar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svelte-1elxaub"><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg></button> <div class="header-avatar svelte-1elxaub"><svg viewBox="0 0 24 24" fill="currentColor" class="svelte-1elxaub"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1.07A7.001 7.001 0 0 1 7.07 19H6a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h-1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2zm-3 13a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"></path></svg></div> <div class="header-info svelte-1elxaub"><div class="header-title svelte-1elxaub"> </div> <div class="header-subtitle svelte-1elxaub">online</div></div> <div class="header-actions svelte-1elxaub"><button class="header-btn svelte-1elxaub" aria-label="Toggle theme"><!></button> <button class="header-btn svelte-1elxaub" aria-label="Settings" title="Settings"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svelte-1elxaub"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg></button> <button class="header-btn delete-btn svelte-1elxaub" title="Clear chat" aria-label="Clear chat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svelte-1elxaub"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg></button></div></div>`);
function Header($$anchor, $$props) {
  push($$props, false);
  const $activeSession = () => store_get(activeSession, "$activeSession", $$stores);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const $uiState = () => store_get(uiState, "$uiState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  async function clearChat() {
    const currentAppState = get(appState);
    const currentSessionState = get(sessionState);
    if (!currentAppState.hass) return;
    if (!currentSessionState.activeSessionId) return;
    if (confirm("Clear this conversation?")) {
      await deleteSession(currentAppState.hass, currentSessionState.activeSessionId);
      clearAllCaches();
    }
  }
  init();
  var div = root$n();
  var button = child(div);
  button.__click = function(...$$args) {
    toggleSidebar?.apply(this, $$args);
  };
  var div_1 = sibling(button, 4);
  var div_2 = child(div_1);
  var text2 = child(div_2);
  var div_3 = sibling(div_1, 2);
  var button_1 = child(div_3);
  button_1.__click = function(...$$args) {
    cycleTheme?.apply(this, $$args);
  };
  var node = child(button_1);
  {
    var consequent = ($$anchor2) => {
      var svg2 = root_1$k();
      append($$anchor2, svg2);
    };
    var alternate_1 = ($$anchor2) => {
      var fragment = comment();
      var node_1 = first_child(fragment);
      {
        var consequent_1 = ($$anchor3) => {
          var svg_1 = root_3$b();
          append($$anchor3, svg_1);
        };
        var alternate = ($$anchor3) => {
          var svg_2 = root_4$b();
          append($$anchor3, svg_2);
        };
        if_block(
          node_1,
          ($$render) => {
            if ($uiState().theme === "dark") $$render(consequent_1);
            else $$render(alternate, false);
          },
          true
        );
      }
      append($$anchor2, fragment);
    };
    if_block(node, ($$render) => {
      if ($uiState().theme === "light") $$render(consequent);
      else $$render(alternate_1, false);
    });
  }
  var button_2 = sibling(button_1, 2);
  button_2.__click = function(...$$args) {
    toggleSettings?.apply(this, $$args);
  };
  var button_3 = sibling(button_2, 2);
  button_3.__click = clearChat;
  template_effect(() => {
    set_text(text2, $activeSession()?.title || $appState().agentName);
    set_attribute(button_1, "title", `Toggle theme (${$uiState().theme ?? ""})`);
    button_3.disabled = $appState().isLoading;
  });
  append($$anchor, div);
  pop();
  $$cleanup();
}
delegate(["click"]);
function scrollToBottom(element) {
  if (element) {
    element.scrollTop = element.scrollHeight;
  }
}
function autoResize(textarea, maxHeight = 200) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, maxHeight) + "px";
}
function isMobile() {
  return typeof window !== "undefined" && window.innerWidth <= 768;
}
function formatSessionTime(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  const now = /* @__PURE__ */ new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1e3 * 60 * 60 * 24));
  if (diffDays === 0) {
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true
    });
  } else if (diffDays === 1) {
    return "Yesterday";
  } else if (diffDays < 7) {
    return `${diffDays} days ago`;
  } else {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
}
var root_1$j = /* @__PURE__ */ from_html(`<div class="voice-badge svelte-114uzds" title="Voice session" role="img" aria-label="Voice session"><svg viewBox="0 0 24 24" fill="currentColor" width="10" height="10" class="svelte-114uzds"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"></path><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"></path></svg></div>`);
var root$m = /* @__PURE__ */ from_html(`<div role="button" tabindex="0"><div class="session-avatar svelte-114uzds"><span> </span> <!></div> <div class="session-content svelte-114uzds"><div class="session-top-row svelte-114uzds"><span class="session-name svelte-114uzds"> </span> <span class="session-time svelte-114uzds"> </span></div> <div class="session-bottom-row svelte-114uzds"><span class="session-preview svelte-114uzds"> </span></div></div> <button class="session-delete svelte-114uzds" aria-label="Delete session"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svelte-114uzds"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg></button></div>`);
function SessionItem($$anchor, $$props) {
  push($$props, true);
  const $sessionState = () => store_get(sessionState, "$sessionState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  const isActive = /* @__PURE__ */ user_derived(() => $$props.session.session_id === $sessionState().activeSessionId);
  const avatarColor = /* @__PURE__ */ user_derived(() => {
    const title = $$props.session.title || "New";
    let hash = 0;
    for (let i2 = 0; i2 < title.length; i2++) {
      hash = title.charCodeAt(i2) + ((hash << 5) - hash);
    }
    const colors = [
      "#2AABEE",
      "#F5A623",
      "#E74C3C",
      "#27AE60",
      "#9B59B6",
      "#1ABC9C",
      "#E67E22",
      "#3498DB"
    ];
    return colors[Math.abs(hash) % colors.length];
  });
  const isVoice = /* @__PURE__ */ user_derived(() => $$props.session.title?.startsWith("Voice: ") ?? false);
  const displayTitle = /* @__PURE__ */ user_derived(() => get$1(isVoice) ? $$props.session.title.slice(7) : $$props.session.title);
  const avatarText = /* @__PURE__ */ user_derived(() => $$props.session.emoji || (get$1(displayTitle) || "N")[0].toUpperCase());
  async function handleClick() {
    const hass = get(appState).hass;
    if (hass && !get$1(isActive)) {
      await selectSession(hass, $$props.session.session_id);
    }
  }
  async function handleDelete(e2) {
    e2.stopPropagation();
    const hass = get(appState).hass;
    if (!hass) return;
    if (confirm("Delete this conversation?")) {
      await deleteSession(hass, $$props.session.session_id);
    }
  }
  var div = root$m();
  let classes;
  div.__click = handleClick;
  var div_1 = child(div);
  var span = child(div_1);
  var text2 = child(span);
  var node = sibling(span, 2);
  {
    var consequent = ($$anchor2) => {
      var div_2 = root_1$j();
      append($$anchor2, div_2);
    };
    if_block(node, ($$render) => {
      if (get$1(isVoice)) $$render(consequent);
    });
  }
  var div_3 = sibling(div_1, 2);
  var div_4 = child(div_3);
  var span_1 = child(div_4);
  var text_1 = child(span_1);
  var span_2 = sibling(span_1, 2);
  var text_2 = child(span_2);
  var div_5 = sibling(div_4, 2);
  var span_3 = child(div_5);
  var text_3 = child(span_3);
  var button = sibling(div_3, 2);
  button.__click = handleDelete;
  template_effect(
    ($0) => {
      classes = set_class(div, 1, "session-item svelte-114uzds", null, classes, { active: get$1(isActive) });
      set_style(div_1, `background: ${get$1(avatarColor) ?? ""}`);
      set_text(text2, get$1(avatarText));
      set_text(text_1, get$1(displayTitle) || "New Conversation");
      set_text(text_2, $0);
      set_text(text_3, $$props.session.preview || "Start typing...");
    },
    [() => formatSessionTime($$props.session.updated_at)]
  );
  append($$anchor, div);
  pop();
  $$cleanup();
}
delegate(["click"]);
var root_2$b = /* @__PURE__ */ from_html(`<div class="session-skeleton svelte-1j5qstn"><div class="skeleton-line svelte-1j5qstn"></div> <div class="skeleton-line short svelte-1j5qstn"></div> <div class="skeleton-line tiny svelte-1j5qstn"></div></div>`);
var root_4$a = /* @__PURE__ */ from_html(`<div class="empty-sessions svelte-1j5qstn"><svg viewBox="0 0 24 24" class="icon svelte-1j5qstn"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z" class="svelte-1j5qstn"></path></svg> <p class="svelte-1j5qstn">No conversations yet</p></div>`);
var root_6$9 = /* @__PURE__ */ from_html(`<div class="empty-sessions svelte-1j5qstn"><p class="svelte-1j5qstn"> </p></div>`);
var root$l = /* @__PURE__ */ from_html(`<div class="session-list svelte-1j5qstn"><!></div>`);
function SessionList($$anchor, $$props) {
  push($$props, true);
  const $sessionState = () => store_get(sessionState, "$sessionState", $$stores);
  const $hasSessions = () => store_get(hasSessions, "$hasSessions", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  let searchQuery = prop($$props, "searchQuery", 3, "");
  const filteredSessions = /* @__PURE__ */ user_derived(() => {
    const q2 = searchQuery().toLowerCase().trim();
    if (!q2) return $sessionState().sessions;
    return $sessionState().sessions.filter((s2) => s2.title.toLowerCase().includes(q2) || s2.preview.toLowerCase().includes(q2));
  });
  const skeletonCount = 3;
  var div = root$l();
  var node = child(div);
  {
    var consequent = ($$anchor2) => {
      var fragment = comment();
      var node_1 = first_child(fragment);
      each(node_1, 17, () => Array(skeletonCount), index, ($$anchor3, _2) => {
        var div_1 = root_2$b();
        append($$anchor3, div_1);
      });
      append($$anchor2, fragment);
    };
    var alternate_2 = ($$anchor2) => {
      var fragment_1 = comment();
      var node_2 = first_child(fragment_1);
      {
        var consequent_1 = ($$anchor3) => {
          var div_2 = root_4$a();
          append($$anchor3, div_2);
        };
        var alternate_1 = ($$anchor3) => {
          var fragment_2 = comment();
          var node_3 = first_child(fragment_2);
          {
            var consequent_2 = ($$anchor4) => {
              var div_3 = root_6$9();
              var p2 = child(div_3);
              var text2 = child(p2);
              template_effect(() => set_text(text2, `No results for "${searchQuery() ?? ""}"`));
              append($$anchor4, div_3);
            };
            var alternate = ($$anchor4) => {
              var fragment_3 = comment();
              var node_4 = first_child(fragment_3);
              each(node_4, 17, () => get$1(filteredSessions), (session) => session.session_id, ($$anchor5, session) => {
                SessionItem($$anchor5, {
                  get session() {
                    return get$1(session);
                  }
                });
              });
              append($$anchor4, fragment_3);
            };
            if_block(
              node_3,
              ($$render) => {
                if (get$1(filteredSessions).length === 0) $$render(consequent_2);
                else $$render(alternate, false);
              },
              true
            );
          }
          append($$anchor3, fragment_2);
        };
        if_block(
          node_2,
          ($$render) => {
            if (!$hasSessions()) $$render(consequent_1);
            else $$render(alternate_1, false);
          },
          true
        );
      }
      append($$anchor2, fragment_1);
    };
    if_block(node, ($$render) => {
      if ($sessionState().sessionsLoading) $$render(consequent);
      else $$render(alternate_2, false);
    });
  }
  append($$anchor, div);
  pop();
  $$cleanup();
}
var root$k = /* @__PURE__ */ from_html(`<button class="fab svelte-19p7jpv" title="New chat" aria-label="New chat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="svelte-19p7jpv"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg></button>`);
function NewChatButton($$anchor, $$props) {
  push($$props, false);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const $providerState = () => store_get(providerState, "$providerState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  async function handleNewChat() {
    if (!$appState().hass) {
      appState.update((s2) => ({ ...s2, error: "Home Assistant not connected" }));
      return;
    }
    if (!$providerState().selectedProvider) {
      appState.update((s2) => ({ ...s2, error: "Please select a provider first" }));
      return;
    }
    await createSession($appState().hass, $providerState().selectedProvider);
  }
  init();
  var button = root$k();
  button.__click = handleNewChat;
  template_effect(() => button.disabled = !$appState().hass);
  append($$anchor, button);
  pop();
  $$cleanup();
}
delegate(["click"]);
var root_1$i = /* @__PURE__ */ from_html(`<div class="sidebar-overlay svelte-ou1367"></div>`);
var root$j = /* @__PURE__ */ from_html(`<!> <aside><div class="search-container svelte-ou1367"><div class="search-bar svelte-ou1367"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svelte-ou1367"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg> <input type="text" placeholder="Search conversations..." aria-label="Search conversations" class="svelte-ou1367"/></div></div> <!> <!></aside>`, 1);
function Sidebar($$anchor, $$props) {
  push($$props, true);
  const $uiState = () => store_get(uiState, "$uiState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  let searchQuery = /* @__PURE__ */ state("");
  const sidebarClass = /* @__PURE__ */ user_derived(() => isMobile() ? $uiState().sidebarOpen ? "sidebar open" : "sidebar hidden" : $uiState().sidebarOpen ? "sidebar" : "sidebar hidden");
  const showOverlay = /* @__PURE__ */ user_derived(() => $uiState().sidebarOpen && isMobile());
  var fragment = root$j();
  var node = first_child(fragment);
  {
    var consequent = ($$anchor2) => {
      var div = root_1$i();
      div.__click = function(...$$args) {
        closeSidebar?.apply(this, $$args);
      };
      append($$anchor2, div);
    };
    if_block(node, ($$render) => {
      if (get$1(showOverlay)) $$render(consequent);
    });
  }
  var aside = sibling(node, 2);
  var div_1 = child(aside);
  var div_2 = child(div_1);
  var input = sibling(child(div_2), 2);
  var node_1 = sibling(div_1, 2);
  SessionList(node_1, {
    get searchQuery() {
      return get$1(searchQuery);
    }
  });
  var node_2 = sibling(node_1, 2);
  NewChatButton(node_2, {});
  template_effect(() => set_class(aside, 1, clsx(get$1(sidebarClass)), "svelte-ou1367"));
  bind_value(input, () => get$1(searchQuery), ($$value) => set(searchQuery, $$value));
  append($$anchor, fragment);
  pop();
  $$cleanup();
}
delegate(["click"]);
var root_4$9 = /* @__PURE__ */ from_html(`<img class="attached-image svelte-cu3vo4" loading="lazy"/>`);
var root_6$8 = /* @__PURE__ */ from_html(`<img class="attached-image svelte-cu3vo4" loading="lazy"/>`);
var root_7$6 = /* @__PURE__ */ from_html(`<div class="image-placeholder svelte-cu3vo4"><svg viewBox="0 0 24 24" class="svelte-cu3vo4"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" class="svelte-cu3vo4"></path></svg> <span class="svelte-cu3vo4"> </span></div>`);
var root_2$a = /* @__PURE__ */ from_html(`<div class="image-attachments svelte-cu3vo4"></div>`);
var root_10$3 = /* @__PURE__ */ from_svg(`<path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 9.5h1v-1H9v1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm10 5.5h1v-3h-1v3z" class="svelte-cu3vo4"></path>`);
var root_11$2 = /* @__PURE__ */ from_svg(`<path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z" class="svelte-cu3vo4"></path>`);
var root_9$3 = /* @__PURE__ */ from_html(`<div class="file-chip svelte-cu3vo4"><svg viewBox="0 0 24 24" class="file-icon svelte-cu3vo4"><!></svg> <span class="file-name svelte-cu3vo4"> </span> <span class="file-size svelte-cu3vo4"> </span></div>`);
var root_8$6 = /* @__PURE__ */ from_html(`<div class="file-attachments svelte-cu3vo4"></div>`);
var root_1$h = /* @__PURE__ */ from_html(`<div class="attachments svelte-cu3vo4"><!> <!></div>`);
var root_13$2 = /* @__PURE__ */ from_html(`<span class="streaming-cursor svelte-cu3vo4">&#9611;</span>`);
var root_12$2 = /* @__PURE__ */ from_html(`<!> <!>`, 1);
var root_16$1 = /* @__PURE__ */ from_html(`<span class="bubble-time svelte-cu3vo4"> </span>`);
var root$i = /* @__PURE__ */ from_html(`<div><div class="bubble svelte-cu3vo4"><!> <!> <!></div></div>`);
function MessageBubble($$anchor, $$props) {
  push($$props, true);
  const renderedContent = /* @__PURE__ */ user_derived(() => $$props.message.type === "assistant" ? renderMarkdown($$props.message.text, get(sessionState).activeSessionId || void 0) : $$props.message.text);
  const formattedTime = /* @__PURE__ */ user_derived(() => {
    if (!$$props.message.timestamp) return "";
    try {
      const d2 = new Date($$props.message.timestamp);
      if (isNaN(d2.getTime())) return "";
      const now = /* @__PURE__ */ new Date();
      const isToday = d2.getDate() === now.getDate() && d2.getMonth() === now.getMonth() && d2.getFullYear() === now.getFullYear();
      const time = d2.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      if (isToday) return time;
      const date = d2.toLocaleDateString([], { day: "numeric", month: "short" });
      return `${date}, ${time}`;
    } catch {
      return "";
    }
  });
  const hasAttachments = /* @__PURE__ */ user_derived(() => $$props.message.attachments && $$props.message.attachments.length > 0);
  const imageAttachments = /* @__PURE__ */ user_derived(() => ($$props.message.attachments || []).filter((a2) => a2.is_image));
  const fileAttachments = /* @__PURE__ */ user_derived(() => ($$props.message.attachments || []).filter((a2) => !a2.is_image));
  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
  var div = root$i();
  let classes;
  var div_1 = child(div);
  var node = child(div_1);
  {
    var consequent_5 = ($$anchor2) => {
      var div_2 = root_1$h();
      var node_1 = child(div_2);
      {
        var consequent_2 = ($$anchor3) => {
          var div_3 = root_2$a();
          each(div_3, 21, () => get$1(imageAttachments), (att) => att.file_id, ($$anchor4, att) => {
            var fragment = comment();
            var node_2 = first_child(fragment);
            {
              var consequent = ($$anchor5) => {
                var img = root_4$9();
                template_effect(() => {
                  set_attribute(img, "src", get$1(att).data_url);
                  set_attribute(img, "alt", get$1(att).filename);
                });
                append($$anchor5, img);
              };
              var alternate_1 = ($$anchor5) => {
                var fragment_1 = comment();
                var node_3 = first_child(fragment_1);
                {
                  var consequent_1 = ($$anchor6) => {
                    var img_1 = root_6$8();
                    template_effect(() => {
                      set_attribute(img_1, "src", `data:${get$1(att).mime_type};base64,${get$1(att).thumbnail_b64}`);
                      set_attribute(img_1, "alt", get$1(att).filename);
                    });
                    append($$anchor6, img_1);
                  };
                  var alternate = ($$anchor6) => {
                    var div_4 = root_7$6();
                    var span = sibling(child(div_4), 2);
                    var text2 = child(span);
                    template_effect(() => set_text(text2, get$1(att).filename));
                    append($$anchor6, div_4);
                  };
                  if_block(
                    node_3,
                    ($$render) => {
                      if (get$1(att).thumbnail_b64) $$render(consequent_1);
                      else $$render(alternate, false);
                    },
                    true
                  );
                }
                append($$anchor5, fragment_1);
              };
              if_block(node_2, ($$render) => {
                if (get$1(att).data_url) $$render(consequent);
                else $$render(alternate_1, false);
              });
            }
            append($$anchor4, fragment);
          });
          append($$anchor3, div_3);
        };
        if_block(node_1, ($$render) => {
          if (get$1(imageAttachments).length > 0) $$render(consequent_2);
        });
      }
      var node_4 = sibling(node_1, 2);
      {
        var consequent_4 = ($$anchor3) => {
          var div_5 = root_8$6();
          each(div_5, 21, () => get$1(fileAttachments), (att) => att.file_id, ($$anchor4, att) => {
            var div_6 = root_9$3();
            var svg2 = child(div_6);
            var node_5 = child(svg2);
            {
              var consequent_3 = ($$anchor5) => {
                var path = root_10$3();
                append($$anchor5, path);
              };
              var alternate_2 = ($$anchor5) => {
                var path_1 = root_11$2();
                append($$anchor5, path_1);
              };
              if_block(node_5, ($$render) => {
                if (get$1(att).mime_type === "application/pdf") $$render(consequent_3);
                else $$render(alternate_2, false);
              });
            }
            var span_1 = sibling(svg2, 2);
            var text_1 = child(span_1);
            var span_2 = sibling(span_1, 2);
            var text_2 = child(span_2);
            template_effect(
              ($0) => {
                set_attribute(span_1, "title", get$1(att).filename);
                set_text(text_1, get$1(att).filename);
                set_text(text_2, $0);
              },
              [() => formatSize(get$1(att).size)]
            );
            append($$anchor4, div_6);
          });
          append($$anchor3, div_5);
        };
        if_block(node_4, ($$render) => {
          if (get$1(fileAttachments).length > 0) $$render(consequent_4);
        });
      }
      append($$anchor2, div_2);
    };
    if_block(node, ($$render) => {
      if (get$1(hasAttachments)) $$render(consequent_5);
    });
  }
  var node_6 = sibling(node, 2);
  {
    var consequent_7 = ($$anchor2) => {
      var fragment_2 = root_12$2();
      var node_7 = first_child(fragment_2);
      html$2(node_7, () => get$1(renderedContent));
      var node_8 = sibling(node_7, 2);
      {
        var consequent_6 = ($$anchor3) => {
          var span_3 = root_13$2();
          append($$anchor3, span_3);
        };
        if_block(node_8, ($$render) => {
          if ($$props.message.isStreaming) $$render(consequent_6);
        });
      }
      append($$anchor2, fragment_2);
    };
    var alternate_3 = ($$anchor2) => {
      var fragment_3 = comment();
      var node_9 = first_child(fragment_3);
      {
        var consequent_8 = ($$anchor3) => {
          var text_3 = text$1();
          template_effect(() => set_text(text_3, $$props.message.text));
          append($$anchor3, text_3);
        };
        if_block(
          node_9,
          ($$render) => {
            if ($$props.message.text) $$render(consequent_8);
          },
          true
        );
      }
      append($$anchor2, fragment_3);
    };
    if_block(node_6, ($$render) => {
      if ($$props.message.type === "assistant") $$render(consequent_7);
      else $$render(alternate_3, false);
    });
  }
  var node_10 = sibling(node_6, 2);
  {
    var consequent_9 = ($$anchor2) => {
      var span_4 = root_16$1();
      var text_4 = child(span_4);
      template_effect(() => set_text(text_4, get$1(formattedTime)));
      append($$anchor2, span_4);
    };
    if_block(node_10, ($$render) => {
      if (get$1(formattedTime)) $$render(consequent_9);
    });
  }
  template_effect(() => classes = set_class(div, 1, "message svelte-cu3vo4", null, classes, {
    user: $$props.message.type === "user",
    assistant: $$props.message.type === "assistant",
    streaming: $$props.message.isStreaming
  }));
  append($$anchor, div);
  pop();
}
var root$h = /* @__PURE__ */ from_html(`<div class="typing-indicator svelte-174ds4q"><div class="typing-bubble svelte-174ds4q"><div class="typing-dot svelte-174ds4q"></div> <div class="typing-dot svelte-174ds4q"></div> <div class="typing-dot svelte-174ds4q"></div></div></div>`);
function LoadingIndicator($$anchor) {
  var div = root$h();
  append($$anchor, div);
}
var root_1$g = /* @__PURE__ */ from_html(`<span class="emoji-icon svelte-euh035"> </span>`);
var root_2$9 = /* @__PURE__ */ from_svg(`<svg viewBox="0 0 24 24" fill="currentColor" class="svelte-euh035"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1.07A7.001 7.001 0 0 1 7.07 19H6a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h-1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2zm-3 13a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z" class="svelte-euh035"></path></svg>`);
var root_3$a = /* @__PURE__ */ from_html(`<button class="suggestion-chip svelte-euh035"> </button>`);
var root$g = /* @__PURE__ */ from_html(`<div class="empty-state svelte-euh035"><div class="empty-icon svelte-euh035"><!></div> <h2 class="svelte-euh035"> </h2> <p class="svelte-euh035">Your AI-powered Home Assistant companion. Ask me anything about your smart home.</p> <div class="suggestions svelte-euh035"></div></div>`);
function EmptyState($$anchor, $$props) {
  push($$props, false);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  const suggestions = [
    "Turn off all lights",
    "Create a morning routine",
    "Show energy usage",
    "Set up motion sensors"
  ];
  function handleSuggestion(text2) {
    appState.update((s2) => ({ ...s2, pendingSuggestion: text2 }));
  }
  init();
  var div = root$g();
  var div_1 = child(div);
  var node = child(div_1);
  {
    var consequent = ($$anchor2) => {
      var span = root_1$g();
      var text_1 = child(span);
      template_effect(() => set_text(text_1, $appState().agentEmoji));
      append($$anchor2, span);
    };
    var alternate = ($$anchor2) => {
      var svg2 = root_2$9();
      append($$anchor2, svg2);
    };
    if_block(node, ($$render) => {
      if ($appState().agentEmoji) $$render(consequent);
      else $$render(alternate, false);
    });
  }
  var h2 = sibling(div_1, 2);
  var text_2 = child(h2);
  var div_2 = sibling(h2, 4);
  each(div_2, 5, () => suggestions, index, ($$anchor2, text2) => {
    var button = root_3$a();
    button.__click = () => handleSuggestion(get$1(text2));
    var text_3 = child(button);
    template_effect(() => set_text(text_3, get$1(text2)));
    append($$anchor2, button);
  });
  template_effect(() => set_text(text_2, `Welcome to ${$appState().agentName ?? ""}`));
  append($$anchor, div);
  pop();
  $$cleanup();
}
delegate(["click"]);
var root_1$f = /* @__PURE__ */ from_html(`<div class="error svelte-sualbq"><svg viewBox="0 0 24 24" class="icon svelte-sualbq"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"></path></svg> <span class="error-message svelte-sualbq"> </span> <button class="error-dismiss svelte-sualbq" aria-label="Dismiss error"><svg viewBox="0 0 24 24" class="close-icon svelte-sualbq"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"></path></svg></button></div>`);
function ErrorMessage($$anchor, $$props) {
  push($$props, false);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  function dismissError() {
    appState.update((s2) => ({ ...s2, error: null }));
  }
  init();
  var fragment = comment();
  var node = first_child(fragment);
  {
    var consequent = ($$anchor2) => {
      var div = root_1$f();
      var span = sibling(child(div), 2);
      var text2 = child(span);
      var button = sibling(span, 2);
      button.__click = dismissError;
      template_effect(() => set_text(text2, $appState().error));
      append($$anchor2, div);
    };
    if_block(node, ($$render) => {
      if ($appState().error) $$render(consequent);
    });
  }
  append($$anchor, fragment);
  pop();
  $$cleanup();
}
delegate(["click"]);
var root_4$8 = /* @__PURE__ */ from_html(`<button class="scroll-bottom-btn svelte-hiq0w4" aria-label="Scroll to bottom"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svelte-hiq0w4"><polyline points="6 9 12 15 18 9"></polyline></svg></button>`);
var root$f = /* @__PURE__ */ from_html(`<div class="chat-wrapper svelte-hiq0w4"><div class="messages svelte-hiq0w4"><!> <div class="messages-inner svelte-hiq0w4"><!> <!></div> <!></div> <!></div>`);
function ChatArea($$anchor, $$props) {
  push($$props, true);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const $hasMessages = () => store_get(hasMessages, "$hasMessages", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  let messagesContainer;
  let showScrollBtn = /* @__PURE__ */ state(false);
  user_effect(() => {
    $appState().messages;
    $appState().isLoading;
    if (messagesContainer) {
      scrollToBottom(messagesContainer);
    }
  });
  onMount(() => {
    scrollToBottom(messagesContainer);
  });
  function handleScroll() {
    if (!messagesContainer) return;
    const threshold = messagesContainer.scrollHeight - messagesContainer.clientHeight - 100;
    set(showScrollBtn, messagesContainer.scrollTop < threshold);
  }
  function scrollDown() {
    scrollToBottom(messagesContainer);
  }
  var div = root$f();
  var div_1 = child(div);
  var node = child(div_1);
  {
    var consequent = ($$anchor2) => {
      EmptyState($$anchor2, {});
    };
    if_block(node, ($$render) => {
      if (!$hasMessages() && !$appState().isLoading) $$render(consequent);
    });
  }
  var div_2 = sibling(node, 2);
  var node_1 = child(div_2);
  each(node_1, 1, () => $appState().messages, (message) => message.id, ($$anchor2, message) => {
    MessageBubble($$anchor2, {
      get message() {
        return get$1(message);
      }
    });
  });
  var node_2 = sibling(node_1, 2);
  {
    var consequent_1 = ($$anchor2) => {
      LoadingIndicator($$anchor2);
    };
    if_block(node_2, ($$render) => {
      if ($appState().isLoading) $$render(consequent_1);
    });
  }
  var node_3 = sibling(div_2, 2);
  ErrorMessage(node_3, {});
  bind_this(div_1, ($$value) => messagesContainer = $$value, () => messagesContainer);
  var node_4 = sibling(div_1, 2);
  {
    var consequent_2 = ($$anchor2) => {
      var button = root_4$8();
      button.__click = scrollDown;
      append($$anchor2, button);
    };
    if_block(node_4, ($$render) => {
      if (get$1(showScrollBtn)) $$render(consequent_2);
    });
  }
  event("scroll", div_1, handleScroll);
  append($$anchor, div);
  pop();
  $$cleanup();
}
delegate(["click"]);
async function sendMessage(hass, message, attachments) {
  const session = get(sessionState);
  if (!session.activeSessionId) {
    throw new Error("No active session");
  }
  const provider = get(providerState);
  const app = get(appState);
  const wsParams = {
    type: "homeclaw/chat/send",
    session_id: session.activeSessionId,
    message,
    provider: provider.selectedProvider,
    debug: app.showThinking
  };
  if (provider.selectedModel) {
    wsParams.model = provider.selectedModel;
  }
  if (attachments && attachments.length > 0) {
    wsParams.attachments = attachments;
  }
  return hass.callWS(wsParams);
}
async function sendMessageStream(hass, message, callbacks, attachments) {
  const session = get(sessionState);
  if (!session.activeSessionId) {
    throw new Error("No active session");
  }
  const provider = get(providerState);
  const app = get(appState);
  const wsParams = {
    type: "homeclaw/chat/send_stream",
    session_id: session.activeSessionId,
    message,
    provider: provider.selectedProvider,
    debug: app.showThinking
  };
  if (provider.selectedModel) {
    wsParams.model = provider.selectedModel;
  }
  if (attachments && attachments.length > 0) {
    wsParams.attachments = attachments;
  }
  let unsubscribe;
  unsubscribe = await hass.connection.subscribeMessage(
    (event2) => {
      switch (event2.type) {
        case "user_message":
          break;
        case "stream_start":
          callbacks.onStart?.(event2.message_id);
          break;
        case "stream_chunk":
          callbacks.onChunk?.(event2.chunk);
          break;
        case "status":
          callbacks.onStatus?.(event2.message);
          break;
        case "tool_call":
          callbacks.onToolCall?.(event2.name, event2.args);
          break;
        case "tool_result":
          callbacks.onToolResult?.(event2.name, event2.result);
          break;
        case "stream_end":
          if (event2.success) {
            callbacks.onComplete?.({});
          } else {
            callbacks.onError?.(event2.error || "Unknown error");
          }
          if (unsubscribe) {
            unsubscribe();
          }
          break;
      }
    },
    wsParams,
    { resubscribe: false }
  );
}
function parseAIResponse(content) {
  const trimmedContent = content.trim();
  if (trimmedContent.startsWith("{") && trimmedContent.endsWith("}")) {
    try {
      const parsed = JSON.parse(trimmedContent);
      if (parsed.request_type === "automation_suggestion") {
        return {
          text: parsed.message || "I found an automation that might help you.",
          automation: parsed.automation
        };
      } else if (parsed.request_type === "dashboard_suggestion") {
        return {
          text: parsed.message || "I created a dashboard configuration for you.",
          dashboard: parsed.dashboard
        };
      } else if (parsed.request_type === "final_response") {
        return {
          text: parsed.response || parsed.message || content
        };
      }
    } catch (_e2) {
    }
  }
  return { text: content };
}
var root_1$e = /* @__PURE__ */ from_html(`<div class="drop-overlay svelte-5grvz8"><span class="drop-label svelte-5grvz8">Drop files here</span></div>`);
var root$e = /* @__PURE__ */ from_html(`<div role="textbox" tabindex="-1"><textarea placeholder="Ask me anything about your Home Assistant..." class="svelte-5grvz8"></textarea> <!></div>`);
function MessageInput($$anchor, $$props) {
  push($$props, true);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  let textarea;
  let value = /* @__PURE__ */ state("");
  let isDragOver = /* @__PURE__ */ state(false);
  function handleInput(e2) {
    const target = e2.target;
    set(value, target.value, true);
    autoResize(target);
  }
  function handleKeyDown(e2) {
    if (e2.key === "Enter" && !e2.shiftKey && !get(appState).isLoading) {
      e2.preventDefault();
      $$props.onSend();
    }
  }
  function handlePaste(e2) {
    if (!$$props.onFilesDropped) return;
    const items = e2.clipboardData?.items;
    if (!items) return;
    const files = [];
    for (let i2 = 0; i2 < items.length; i2++) {
      const item = items[i2];
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
    if (files.length > 0) {
      e2.preventDefault();
      $$props.onFilesDropped(files);
    }
  }
  function handleDragOver(e2) {
    e2.preventDefault();
    e2.stopPropagation();
    if (e2.dataTransfer) {
      e2.dataTransfer.dropEffect = "copy";
    }
    set(isDragOver, true);
  }
  function handleDragLeave(e2) {
    e2.preventDefault();
    e2.stopPropagation();
    set(isDragOver, false);
  }
  function handleDrop(e2) {
    e2.preventDefault();
    e2.stopPropagation();
    set(isDragOver, false);
    if (!$$props.onFilesDropped) return;
    const files = [];
    if (e2.dataTransfer?.files) {
      for (let i2 = 0; i2 < e2.dataTransfer.files.length; i2++) {
        files.push(e2.dataTransfer.files[i2]);
      }
    }
    if (files.length > 0) {
      $$props.onFilesDropped(files);
    }
  }
  function getValue() {
    return get$1(value);
  }
  function clear() {
    set(value, "");
    if (textarea) {
      textarea.style.height = "auto";
    }
  }
  var $$exports = { getValue, clear };
  var div = root$e();
  let classes;
  var textarea_1 = child(div);
  textarea_1.__input = handleInput;
  textarea_1.__keydown = handleKeyDown;
  bind_this(textarea_1, ($$value) => textarea = $$value, () => textarea);
  var node = sibling(textarea_1, 2);
  {
    var consequent = ($$anchor2) => {
      var div_1 = root_1$e();
      append($$anchor2, div_1);
    };
    if_block(node, ($$render) => {
      if (get$1(isDragOver)) $$render(consequent);
    });
  }
  template_effect(() => {
    classes = set_class(div, 1, "input-wrapper svelte-5grvz8", null, classes, { "drag-over": get$1(isDragOver) });
    textarea_1.disabled = $appState().isLoading;
  });
  event("dragover", div, handleDragOver);
  event("dragleave", div, handleDragLeave);
  event("drop", div, handleDrop);
  event("paste", textarea_1, handlePaste);
  bind_value(textarea_1, () => get$1(value), ($$value) => set(value, $$value));
  append($$anchor, div);
  var $$pop = pop($$exports);
  $$cleanup();
  return $$pop;
}
delegate(["input", "keydown"]);
var root_2$8 = /* @__PURE__ */ from_html(`<option> </option>`);
var root_1$d = /* @__PURE__ */ from_html(`<div class="provider-selector svelte-6zrmqv"><span class="provider-label svelte-6zrmqv">Provider:</span> <select class="provider-button svelte-6zrmqv"></select></div>`);
var root_3$9 = /* @__PURE__ */ from_html(`<div class="no-providers svelte-6zrmqv">No providers configured</div>`);
function ProviderSelector($$anchor, $$props) {
  push($$props, false);
  const $hasProviders = () => store_get(hasProviders, "$hasProviders", $$stores);
  const $providerState = () => store_get(providerState, "$providerState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  async function handleChange(e2) {
    const target = e2.target;
    providerState.update((s2) => ({ ...s2, selectedProvider: target.value }));
    const currentAppState = get(appState);
    if (currentAppState.hass && target.value) {
      await fetchModels(currentAppState.hass, target.value);
    }
  }
  init();
  var fragment = comment();
  var node = first_child(fragment);
  {
    var consequent = ($$anchor2) => {
      var div = root_1$d();
      var select = sibling(child(div), 2);
      select.__change = handleChange;
      each(select, 5, () => $providerState().availableProviders, index, ($$anchor3, provider) => {
        var option = root_2$8();
        var text2 = child(option);
        var option_value = {};
        template_effect(() => {
          set_text(text2, get$1(provider).label);
          if (option_value !== (option_value = get$1(provider).value)) {
            option.value = (option.__value = get$1(provider).value) ?? "";
          }
        });
        append($$anchor3, option);
      });
      var select_value;
      init_select(select);
      template_effect(() => {
        if (select_value !== (select_value = $providerState().selectedProvider || "")) {
          select.value = (select.__value = $providerState().selectedProvider || "") ?? "", select_option(select, $providerState().selectedProvider || "");
        }
      });
      append($$anchor2, div);
    };
    var alternate = ($$anchor2) => {
      var div_1 = root_3$9();
      append($$anchor2, div_1);
    };
    if_block(node, ($$render) => {
      if ($hasProviders()) $$render(consequent);
      else $$render(alternate, false);
    });
  }
  append($$anchor, fragment);
  pop();
  $$cleanup();
}
delegate(["change"]);
var root_2$7 = /* @__PURE__ */ from_html(`<span class="default-star svelte-1whqbkb" title="Your default model">&#9733;</span>`);
var root_3$8 = /* @__PURE__ */ from_html(`<option> </option>`);
var root_1$c = /* @__PURE__ */ from_html(`<div class="provider-selector svelte-1whqbkb"><span class="provider-label svelte-1whqbkb">Model:</span> <!> <select class="provider-button svelte-1whqbkb"></select></div>`);
function ModelSelector($$anchor, $$props) {
  push($$props, true);
  const $providerState = () => store_get(providerState, "$providerState", $$stores);
  const $hasModels = () => store_get(hasModels, "$hasModels", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  function handleChange(e2) {
    const target = e2.target;
    providerState.update((s2) => ({ ...s2, selectedModel: target.value }));
  }
  const isDefault = /* @__PURE__ */ user_derived(() => $providerState().defaultModel !== null && $providerState().selectedModel === $providerState().defaultModel && $providerState().selectedProvider === $providerState().defaultProvider);
  var fragment = comment();
  var node = first_child(fragment);
  {
    var consequent_1 = ($$anchor2) => {
      var div = root_1$c();
      var node_1 = sibling(child(div), 2);
      {
        var consequent = ($$anchor3) => {
          var span = root_2$7();
          append($$anchor3, span);
        };
        if_block(node_1, ($$render) => {
          if (get$1(isDefault)) $$render(consequent);
        });
      }
      var select = sibling(node_1, 2);
      select.__change = handleChange;
      each(select, 5, () => $providerState().availableModels, index, ($$anchor3, model) => {
        var option = root_3$8();
        var text2 = child(option);
        var option_value = {};
        template_effect(() => {
          set_text(text2, get$1(model).name);
          if (option_value !== (option_value = get$1(model).id)) {
            option.value = (option.__value = get$1(model).id) ?? "";
          }
        });
        append($$anchor3, option);
      });
      var select_value;
      init_select(select);
      template_effect(() => {
        if (select_value !== (select_value = $providerState().selectedModel || "")) {
          select.value = (select.__value = $providerState().selectedModel || "") ?? "", select_option(select, $providerState().selectedModel || "");
        }
      });
      append($$anchor2, div);
    };
    if_block(node, ($$render) => {
      if ($hasModels()) $$render(consequent_1);
    });
  }
  append($$anchor, fragment);
  pop();
  $$cleanup();
}
delegate(["change"]);
var root$d = /* @__PURE__ */ from_html(`<button class="send-button svelte-1lpj1oh"><svg viewBox="0 0 24 24" class="icon svelte-1lpj1oh"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg></button>`);
function SendButton($$anchor, $$props) {
  push($$props, true);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const $hasProviders = () => store_get(hasProviders, "$hasProviders", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  const disabled = /* @__PURE__ */ user_derived(() => $appState().isLoading || !$hasProviders());
  var button = root$d();
  button.__click = function(...$$args) {
    $$props.onclick?.apply(this, $$args);
  };
  template_effect(() => button.disabled = get$1(disabled));
  append($$anchor, button);
  pop();
  $$cleanup();
}
delegate(["click"]);
var root$c = /* @__PURE__ */ from_html(`<label class="thinking-toggle svelte-1ahnk03"><input type="checkbox" class="svelte-1ahnk03"/> <span class="label svelte-1ahnk03">Debug Mode</span></label>`);
function ThinkingToggle($$anchor, $$props) {
  push($$props, false);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  function toggle() {
    appState.update((s2) => ({ ...s2, showThinking: !s2.showThinking }));
  }
  init();
  var label = root$c();
  var input = child(label);
  input.__change = toggle;
  template_effect(() => set_checked(input, $appState().showThinking));
  append($$anchor, label);
  pop();
  $$cleanup();
}
delegate(["change"]);
var root$b = /* @__PURE__ */ from_html(`<input type="file" multiple class="hidden-input svelte-nfbktg"/> <button class="attach-button svelte-nfbktg" title="Attach file"><svg viewBox="0 0 24 24" class="icon svelte-nfbktg"><path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5a2.5 2.5 0 0 1 5 0v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5a2.5 2.5 0 0 0 5 0V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"></path></svg></button>`, 1);
function AttachButton($$anchor, $$props) {
  push($$props, true);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  let fileInput;
  const ACCEPT = [
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "text/plain",
    "text/csv",
    "text/markdown",
    "text/html",
    "application/json",
    "application/xml",
    "application/pdf",
    ".txt",
    ".csv",
    ".md",
    ".json",
    ".xml",
    ".pdf",
    ".log",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
    ".js",
    ".ts",
    ".sh",
    ".sql",
    ".ini",
    ".cfg",
    ".conf"
  ].join(",");
  function handleClick() {
    fileInput?.click();
  }
  function handleChange(e2) {
    const input = e2.target;
    if (input.files && input.files.length > 0) {
      $$props.onFilesSelected(input.files);
      input.value = "";
    }
  }
  var fragment = root$b();
  var input_1 = first_child(fragment);
  input_1.__change = handleChange;
  bind_this(input_1, ($$value) => fileInput = $$value, () => fileInput);
  var button = sibling(input_1, 2);
  button.__click = handleClick;
  template_effect(() => {
    set_attribute(input_1, "accept", ACCEPT);
    button.disabled = $appState().isLoading;
  });
  append($$anchor, fragment);
  pop();
  $$cleanup();
}
delegate(["change", "click"]);
var root_3$7 = /* @__PURE__ */ from_html(`<img class="thumbnail svelte-fchx1w"/>`);
var root_5$7 = /* @__PURE__ */ from_svg(`<svg viewBox="0 0 24 24" class="svelte-fchx1w"><path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 9.5h1v-1H9v1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm10 5.5h1v-3h-1v3z"></path></svg>`);
var root_6$7 = /* @__PURE__ */ from_svg(`<svg viewBox="0 0 24 24" class="svelte-fchx1w"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"></path></svg>`);
var root_4$7 = /* @__PURE__ */ from_html(`<div><!></div>`);
var root_7$5 = /* @__PURE__ */ from_html(`<div class="status-overlay svelte-fchx1w"><div class="spinner svelte-fchx1w"></div></div>`);
var root_2$6 = /* @__PURE__ */ from_html(`<div><!> <div class="attachment-info svelte-fchx1w"><span class="filename svelte-fchx1w"> </span> <span class="filesize svelte-fchx1w"> </span></div> <button class="remove-btn svelte-fchx1w" title="Remove"><svg viewBox="0 0 24 24" class="svelte-fchx1w"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"></path></svg></button> <!></div>`);
var root_1$b = /* @__PURE__ */ from_html(`<div class="attachment-preview svelte-fchx1w"></div>`);
function AttachmentPreview($$anchor, $$props) {
  push($$props, true);
  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
  function getFileIcon(mimeType) {
    if (mimeType === "application/pdf") return "pdf";
    if (mimeType.startsWith("image/")) return "image";
    return "text";
  }
  var fragment = comment();
  var node = first_child(fragment);
  {
    var consequent_3 = ($$anchor2) => {
      var div = root_1$b();
      each(div, 21, () => $$props.attachments, (att) => att.file_id, ($$anchor3, att) => {
        var div_1 = root_2$6();
        let classes;
        var node_1 = child(div_1);
        {
          var consequent = ($$anchor4) => {
            var img = root_3$7();
            template_effect(() => {
              set_attribute(img, "src", get$1(att).data_url);
              set_attribute(img, "alt", get$1(att).filename);
            });
            append($$anchor4, img);
          };
          var alternate_1 = ($$anchor4) => {
            var div_2 = root_4$7();
            let classes_1;
            var node_2 = child(div_2);
            {
              var consequent_1 = ($$anchor5) => {
                var svg2 = root_5$7();
                append($$anchor5, svg2);
              };
              var alternate = ($$anchor5) => {
                var svg_1 = root_6$7();
                append($$anchor5, svg_1);
              };
              if_block(node_2, ($$render) => {
                if (getFileIcon(get$1(att).mime_type) === "pdf") $$render(consequent_1);
                else $$render(alternate, false);
              });
            }
            template_effect(($0) => classes_1 = set_class(div_2, 1, "file-icon svelte-fchx1w", null, classes_1, $0), [() => ({ pdf: getFileIcon(get$1(att).mime_type) === "pdf" })]);
            append($$anchor4, div_2);
          };
          if_block(node_1, ($$render) => {
            if (get$1(att).is_image && get$1(att).data_url) $$render(consequent);
            else $$render(alternate_1, false);
          });
        }
        var div_3 = sibling(node_1, 2);
        var span = child(div_3);
        var text2 = child(span);
        var span_1 = sibling(span, 2);
        var text_1 = child(span_1);
        var button = sibling(div_3, 2);
        button.__click = () => $$props.onRemove(get$1(att).file_id);
        var node_3 = sibling(button, 2);
        {
          var consequent_2 = ($$anchor4) => {
            var div_4 = root_7$5();
            append($$anchor4, div_4);
          };
          if_block(node_3, ($$render) => {
            if (get$1(att).status === "pending") $$render(consequent_2);
          });
        }
        template_effect(
          ($0) => {
            classes = set_class(div_1, 1, "attachment-item svelte-fchx1w", null, classes, {
              "is-image": get$1(att).is_image,
              "is-error": get$1(att).status === "error"
            });
            set_attribute(span, "title", get$1(att).filename);
            set_text(text2, get$1(att).filename);
            set_text(text_1, $0);
          },
          [() => formatSize(get$1(att).size)]
        );
        append($$anchor3, div_1);
      });
      append($$anchor2, div);
    };
    if_block(node, ($$render) => {
      if ($$props.attachments.length > 0) $$render(consequent_3);
    });
  }
  append($$anchor, fragment);
  pop();
}
delegate(["click"]);
var root$a = /* @__PURE__ */ from_html(`<div class="input-container svelte-f7ebxa"><!> <div class="input-main svelte-f7ebxa"><!></div> <div class="input-footer svelte-f7ebxa"><!> <!> <!> <!> <!></div></div>`);
function InputArea($$anchor, $$props) {
  push($$props, true);
  let messageInput;
  const USE_STREAMING = true;
  const MAX_FILE_SIZE = 10 * 1024 * 1024;
  const MAX_ATTACHMENTS = 5;
  let pendingAttachments = /* @__PURE__ */ state(proxy([]));
  function readFileAsAttachment(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result;
        const isImage = file.type.startsWith("image/");
        const base64Match = dataUrl.match(/^data:[^;]+;base64,(.*)$/);
        const rawBase64 = base64Match ? base64Match[1] : dataUrl;
        resolve({
          file_id: `local-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          filename: file.name,
          mime_type: file.type || "application/octet-stream",
          size: file.size,
          data_url: isImage ? dataUrl : void 0,
          content: rawBase64,
          status: "ready",
          is_image: isImage
        });
      };
      reader.onerror = () => reject(new Error(`Failed to read file: ${file.name}`));
      reader.readAsDataURL(file);
    });
  }
  async function processFiles(files) {
    const fileArray = Array.from(files);
    const totalCount = get$1(pendingAttachments).length + fileArray.length;
    if (totalCount > MAX_ATTACHMENTS) {
      console.warn(`Too many attachments: ${totalCount} (max ${MAX_ATTACHMENTS})`);
      const remaining = MAX_ATTACHMENTS - get$1(pendingAttachments).length;
      if (remaining <= 0) return;
      fileArray.splice(remaining);
    }
    for (const file of fileArray) {
      if (file.size > MAX_FILE_SIZE) {
        console.warn(`File too large: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`);
        continue;
      }
      try {
        const attachment = await readFileAsAttachment(file);
        set(pendingAttachments, [...get$1(pendingAttachments), attachment], true);
      } catch (err) {
        console.error(`Failed to process file: ${file.name}`, err);
      }
    }
  }
  function handleFilesSelected(files) {
    processFiles(files);
  }
  function handleFilesDropped(files) {
    processFiles(files);
  }
  function removeAttachment(fileId) {
    set(pendingAttachments, get$1(pendingAttachments).filter((a2) => a2.file_id !== fileId), true);
  }
  async function handleSend() {
    const currentAppState = get(appState);
    if (!currentAppState.hass) return;
    const message = messageInput.getValue().trim();
    const hasAttachments = get$1(pendingAttachments).length > 0;
    if (!message && !hasAttachments || currentAppState.isLoading) return;
    const attachmentsToSend = [...get$1(pendingAttachments)];
    messageInput.clear();
    set(pendingAttachments, [], true);
    appState.update((s2) => ({ ...s2, isLoading: true, error: null }));
    const currentSessionState = get(sessionState);
    const currentProviderState = get(providerState);
    if (!currentSessionState.activeSessionId && currentProviderState.selectedProvider) {
      await createSession(currentAppState.hass, currentProviderState.selectedProvider);
    }
    const updatedSessionState = get(sessionState);
    if (!updatedSessionState.activeSessionId) {
      appState.update((s2) => ({ ...s2, error: "No active session", isLoading: false }));
      return;
    }
    const userMsg = {
      id: `user-${Date.now()}-${Math.random()}`,
      type: "user",
      text: message,
      attachments: attachmentsToSend.map((a2) => ({
        file_id: a2.file_id,
        filename: a2.filename,
        mime_type: a2.mime_type,
        size: a2.size,
        data_url: a2.data_url,
        is_image: a2.is_image,
        status: "ready"
      }))
    };
    appState.update((s2) => ({ ...s2, messages: [...s2.messages, userMsg] }));
    const wsAttachments = attachmentsToSend.map((a2) => ({
      filename: a2.filename,
      mime_type: a2.mime_type,
      content: a2.content || "",
      size: a2.size
    }));
    try {
      if (USE_STREAMING) {
        let assistantMessageId = "";
        let streamedText = "";
        await sendMessageStream(
          currentAppState.hass,
          message,
          {
            onStart: (messageId) => {
              assistantMessageId = messageId;
              appState.update((s2) => {
                if (s2.messages.some((m2) => m2.id === assistantMessageId)) return s2;
                return {
                  ...s2,
                  messages: [
                    ...s2.messages,
                    {
                      id: assistantMessageId,
                      type: "assistant",
                      text: "",
                      status: "streaming",
                      isStreaming: true
                    }
                  ]
                };
              });
            },
            onChunk: (chunk) => {
              streamedText += chunk;
              appState.update((s2) => ({
                ...s2,
                messages: s2.messages.map((msg) => msg.id === assistantMessageId ? { ...msg, text: streamedText } : msg)
              }));
            },
            onStatus: (status) => {
              appState.update((s2) => ({
                ...s2,
                messages: s2.messages.map((msg) => msg.id === assistantMessageId ? { ...msg, text: streamedText + `

_${status}_` } : msg)
              }));
            },
            onToolCall: (_name, _args) => {
            },
            onToolResult: (_name, _result) => {
            },
            onComplete: (result) => {
              const { text: text2, automation, dashboard } = parseAIResponse(result.assistant_message?.content || streamedText);
              appState.update((s2) => ({
                ...s2,
                isLoading: false,
                messages: s2.messages.map((msg) => msg.id === assistantMessageId ? {
                  ...msg,
                  text: text2 || streamedText,
                  status: "completed",
                  isStreaming: false,
                  automation: automation || result.assistant_message?.metadata?.automation,
                  dashboard: dashboard || result.assistant_message?.metadata?.dashboard
                } : msg)
              }));
              const sessions = get(sessionState).sessions;
              const activeId = get(sessionState).activeSessionId;
              const session = sessions.find((s2) => s2.session_id === activeId);
              const isNewConversation = session?.title === "New Conversation";
              const previewText = message || attachmentsToSend.map((a2) => a2.filename).join(", ");
              updateSessionInList(activeId, previewText, isNewConversation ? previewText.substring(0, 40) + (previewText.length > 40 ? "..." : "") : void 0);
            },
            onError: (error) => {
              console.error("Streaming error:", error);
              appState.update((s2) => ({
                ...s2,
                isLoading: false,
                error,
                messages: s2.messages.map((msg) => msg.id === assistantMessageId ? {
                  ...msg,
                  text: `Error: ${error}`,
                  status: "error",
                  isStreaming: false,
                  error_message: error
                } : msg)
              }));
            }
          },
          wsAttachments.length > 0 ? wsAttachments : void 0
        );
      }
    } catch (error) {
      console.error("WebSocket error:", error);
      const errorMessage = error.message || "An error occurred while processing your request";
      appState.update((s2) => ({
        ...s2,
        isLoading: false,
        error: errorMessage,
        messages: [
          ...s2.messages,
          {
            id: `error-${Date.now()}-${Math.random()}`,
            type: "assistant",
            text: `Error: ${errorMessage}`
          }
        ]
      }));
    }
  }
  var div = root$a();
  var node = child(div);
  {
    var consequent = ($$anchor2) => {
      AttachmentPreview($$anchor2, {
        get attachments() {
          return get$1(pendingAttachments);
        },
        onRemove: removeAttachment
      });
    };
    if_block(node, ($$render) => {
      if (get$1(pendingAttachments).length > 0) $$render(consequent);
    });
  }
  var div_1 = sibling(node, 2);
  var node_1 = child(div_1);
  bind_this(MessageInput(node_1, { onSend: handleSend, onFilesDropped: handleFilesDropped }), ($$value) => messageInput = $$value, () => messageInput);
  var div_2 = sibling(div_1, 2);
  var node_2 = child(div_2);
  AttachButton(node_2, { onFilesSelected: handleFilesSelected });
  var node_3 = sibling(node_2, 2);
  ProviderSelector(node_3, {});
  var node_4 = sibling(node_3, 2);
  ModelSelector(node_4, {});
  var node_5 = sibling(node_4, 2);
  ThinkingToggle(node_5, {});
  var node_6 = sibling(node_5, 2);
  SendButton(node_6, { onclick: handleSend });
  append($$anchor, div);
  pop();
}
var root_2$5 = /* @__PURE__ */ from_html(`<span class="thinking-subtitle svelte-wqn4rm"> </span>`);
var root_3$6 = /* @__PURE__ */ from_svg(`<path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"></path>`);
var root_4$6 = /* @__PURE__ */ from_svg(`<path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"></path>`);
var root_6$6 = /* @__PURE__ */ from_html(`<div class="thinking-empty svelte-wqn4rm">No trace captured.</div>`);
var root_8$5 = /* @__PURE__ */ from_html(`<div class="thinking-entry svelte-wqn4rm"><div class="badge svelte-wqn4rm"> </div> <pre class="svelte-wqn4rm"> </pre></div>`);
var root_5$6 = /* @__PURE__ */ from_html(`<div class="thinking-body svelte-wqn4rm"><!></div>`);
var root_1$a = /* @__PURE__ */ from_html(`<div class="thinking-panel svelte-wqn4rm"><div class="thinking-header svelte-wqn4rm" role="button" tabindex="0"><div><span class="thinking-title svelte-wqn4rm">Thinking trace</span> <!></div> <svg viewBox="0 0 24 24" class="icon svelte-wqn4rm"><!></svg></div> <!></div>`);
function ThinkingPanel($$anchor, $$props) {
  push($$props, true);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  function toggleExpanded() {
    appState.update((s2) => ({ ...s2, thinkingExpanded: !s2.thinkingExpanded }));
  }
  const subtitle = /* @__PURE__ */ user_derived(() => () => {
    if (!$appState().debugInfo) return "";
    const parts = [];
    if ($appState().debugInfo.provider) parts.push($appState().debugInfo.provider);
    if ($appState().debugInfo.model) parts.push($appState().debugInfo.model);
    if ($appState().debugInfo.endpoint_type) parts.push($appState().debugInfo.endpoint_type);
    return parts.join(" · ");
  });
  const conversation = /* @__PURE__ */ user_derived(() => $appState().debugInfo?.conversation || []);
  var fragment = comment();
  var node = first_child(fragment);
  {
    var consequent_4 = ($$anchor2) => {
      var div = root_1$a();
      var div_1 = child(div);
      div_1.__click = toggleExpanded;
      var div_2 = child(div_1);
      var node_1 = sibling(child(div_2), 2);
      {
        var consequent = ($$anchor3) => {
          var span = root_2$5();
          var text2 = child(span);
          template_effect(($0) => set_text(text2, $0), [() => get$1(subtitle)()]);
          append($$anchor3, span);
        };
        if_block(node_1, ($$render) => {
          if (get$1(subtitle)()) $$render(consequent);
        });
      }
      var svg2 = sibling(div_2, 2);
      var node_2 = child(svg2);
      {
        var consequent_1 = ($$anchor3) => {
          var path = root_3$6();
          append($$anchor3, path);
        };
        var alternate = ($$anchor3) => {
          var path_1 = root_4$6();
          append($$anchor3, path_1);
        };
        if_block(node_2, ($$render) => {
          if ($appState().thinkingExpanded) $$render(consequent_1);
          else $$render(alternate, false);
        });
      }
      var node_3 = sibling(div_1, 2);
      {
        var consequent_3 = ($$anchor3) => {
          var div_3 = root_5$6();
          var node_4 = child(div_3);
          {
            var consequent_2 = ($$anchor4) => {
              var div_4 = root_6$6();
              append($$anchor4, div_4);
            };
            var alternate_1 = ($$anchor4) => {
              var fragment_1 = comment();
              var node_5 = first_child(fragment_1);
              each(node_5, 17, () => get$1(conversation), index, ($$anchor5, entry) => {
                var div_5 = root_8$5();
                var div_6 = child(div_5);
                var text_1 = child(div_6);
                var pre = sibling(div_6, 2);
                var text_2 = child(pre);
                template_effect(() => {
                  set_text(text_1, get$1(entry).role || "unknown");
                  set_text(text_2, get$1(entry).content || "");
                });
                append($$anchor5, div_5);
              });
              append($$anchor4, fragment_1);
            };
            if_block(node_4, ($$render) => {
              if (get$1(conversation).length === 0) $$render(consequent_2);
              else $$render(alternate_1, false);
            });
          }
          append($$anchor3, div_3);
        };
        if_block(node_3, ($$render) => {
          if ($appState().thinkingExpanded) $$render(consequent_3);
        });
      }
      append($$anchor2, div);
    };
    if_block(node, ($$render) => {
      if ($appState().showThinking && $appState().debugInfo) $$render(consequent_4);
    });
  }
  append($$anchor, fragment);
  pop();
  $$cleanup();
}
delegate(["click"]);
async function getModelsConfig(hass, forceReload = false) {
  const result = await hass.callWS({
    type: "homeclaw/config/models/get",
    force_reload: forceReload
  });
  return result.config || {};
}
async function updateProviderModels(hass, provider, data) {
  const result = await hass.callWS({
    type: "homeclaw/config/models/update",
    provider,
    ...data
  });
  return result.config;
}
var root_1$9 = /* @__PURE__ */ from_html(`<div> </div>`);
var root_2$4 = /* @__PURE__ */ from_html(`<div class="loading svelte-fraw8h">Loading configuration...</div>`);
var root_7$4 = /* @__PURE__ */ from_svg(`<path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"></path>`);
var root_8$4 = /* @__PURE__ */ from_svg(`<path d="M22 9.24l-7.19-.62L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.63-7.03L22 9.24zM12 15.4l-3.76 2.27 1-4.28-3.32-2.88 4.38-.38L12 6.1l1.71 4.04 4.38.38-3.32 2.88 1 4.28L12 15.4z"></path>`);
var root_6$5 = /* @__PURE__ */ from_html(`<div class="model-row svelte-fraw8h"><div class="model-fields svelte-fraw8h"><input class="input small svelte-fraw8h" placeholder="ID (e.g. gpt-4o)"/> <input class="input svelte-fraw8h" placeholder="Display Name"/> <input class="input wide svelte-fraw8h" placeholder="Description (optional)"/></div> <div class="model-actions svelte-fraw8h"><button><svg viewBox="0 0 24 24" class="star-icon svelte-fraw8h"><!></svg></button> <button class="icon-btn danger svelte-fraw8h" title="Remove model"><svg viewBox="0 0 24 24" class="svelte-fraw8h"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"></path></svg></button></div></div>`);
var root_9$2 = /* @__PURE__ */ from_html(`<div class="empty-models svelte-fraw8h">No models defined. Add one below.</div>`);
var root_5$5 = /* @__PURE__ */ from_html(`<div class="provider-body svelte-fraw8h"><!> <!> <div class="provider-actions svelte-fraw8h"><button class="btn text svelte-fraw8h">+ Add Model</button> <div class="action-group svelte-fraw8h"><button class="btn secondary svelte-fraw8h">Revert</button> <button class="btn primary svelte-fraw8h"> </button></div></div></div>`);
var root_4$5 = /* @__PURE__ */ from_html(`<div><button class="provider-header svelte-fraw8h"><div class="provider-info svelte-fraw8h"><span class="provider-name svelte-fraw8h"> </span> <span class="model-count svelte-fraw8h"> </span></div> <svg viewBox="0 0 24 24"><path d="M7 10l5 5 5-5H7z"></path></svg></button> <!></div>`);
var root_3$5 = /* @__PURE__ */ from_html(`<div class="provider-list svelte-fraw8h"></div>`);
var root$9 = /* @__PURE__ */ from_html(`<div class="models-editor svelte-fraw8h"><p class="description svelte-fraw8h">Edit model definitions for each provider. Changes are saved to the server and take
    effect immediately.</p> <!> <!></div>`);
function ModelsEditor($$anchor, $$props) {
  push($$props, true);
  let config = /* @__PURE__ */ state(proxy({}));
  let expandedProvider = /* @__PURE__ */ state(null);
  let loading = /* @__PURE__ */ state(true);
  let saving = /* @__PURE__ */ state(null);
  let message = /* @__PURE__ */ state(null);
  let messageType = /* @__PURE__ */ state("success");
  let editingModels = proxy({});
  user_effect(() => {
    loadConfig();
  });
  async function loadConfig() {
    const hass = get(appState).hass;
    if (!hass) return;
    set(loading, true);
    try {
      set(config, await getModelsConfig(hass, true), true);
    } catch (e2) {
      console.error("[ModelsEditor] Failed to load config:", e2);
    } finally {
      set(loading, false);
    }
  }
  function toggleProvider(provider) {
    if (get$1(expandedProvider) === provider) {
      set(expandedProvider, null);
    } else {
      set(expandedProvider, provider, true);
      if (!editingModels[provider]) {
        editingModels[provider] = JSON.parse(JSON.stringify(get$1(config)[provider]?.models || []));
      }
    }
  }
  function addModel(provider) {
    if (!editingModels[provider]) {
      editingModels[provider] = [];
    }
    editingModels[provider] = [
      ...editingModels[provider],
      { id: "", name: "", description: "" }
    ];
  }
  function removeModel(provider, index2) {
    editingModels[provider] = editingModels[provider].filter((_2, i2) => i2 !== index2);
  }
  function setDefault(provider, index2) {
    editingModels[provider] = editingModels[provider].map((m2, i2) => ({ ...m2, default: i2 === index2 ? true : void 0 }));
  }
  function updateModelField(provider, index2, field, value) {
    editingModels[provider] = editingModels[provider].map((m2, i2) => i2 === index2 ? { ...m2, [field]: value } : m2);
  }
  async function handleSave(provider) {
    const hass = get(appState).hass;
    if (!hass) return;
    const models = editingModels[provider];
    if (!models) return;
    for (const m2 of models) {
      if (!m2.id || !m2.name) {
        showMessage("Each model must have an ID and Name", "error");
        return;
      }
    }
    set(saving, provider, true);
    try {
      const result = await updateProviderModels(hass, provider, { models });
      get$1(config)[provider] = { ...get$1(config)[provider], ...result };
      editingModels[provider] = JSON.parse(JSON.stringify(result.models || []));
      invalidateProvidersCache();
      showMessage(`${provider} models saved`, "success");
    } catch (e2) {
      showMessage(e2?.message || "Failed to save", "error");
    } finally {
      set(saving, null);
    }
  }
  function handleRevert(provider) {
    editingModels[provider] = JSON.parse(JSON.stringify(get$1(config)[provider]?.models || []));
    showMessage("Changes reverted", "success");
  }
  function showMessage(text2, type) {
    set(message, text2, true);
    set(messageType, type, true);
    setTimeout(() => set(message, null), 3e3);
  }
  const providerKeys = /* @__PURE__ */ user_derived(() => Object.keys(get$1(config)));
  var div = root$9();
  var node = sibling(child(div), 2);
  {
    var consequent = ($$anchor2) => {
      var div_1 = root_1$9();
      let classes;
      var text_1 = child(div_1);
      template_effect(() => {
        classes = set_class(div_1, 1, "message svelte-fraw8h", null, classes, { error: get$1(messageType) === "error" });
        set_text(text_1, get$1(message));
      });
      append($$anchor2, div_1);
    };
    if_block(node, ($$render) => {
      if (get$1(message)) $$render(consequent);
    });
  }
  var node_1 = sibling(node, 2);
  {
    var consequent_1 = ($$anchor2) => {
      var div_2 = root_2$4();
      append($$anchor2, div_2);
    };
    var alternate_1 = ($$anchor2) => {
      var div_3 = root_3$5();
      each(div_3, 20, () => get$1(providerKeys), (provider) => provider, ($$anchor3, provider) => {
        const pc = /* @__PURE__ */ user_derived(() => get$1(config)[provider]);
        const isExpanded = /* @__PURE__ */ user_derived(() => get$1(expandedProvider) === provider);
        const models = /* @__PURE__ */ user_derived(() => editingModels[provider] || get$1(pc).models || []);
        var div_4 = root_4$5();
        let classes_1;
        var button = child(div_4);
        button.__click = () => toggleProvider(provider);
        var div_5 = child(button);
        var span = child(div_5);
        var text_2 = child(span);
        var span_1 = sibling(span, 2);
        var text_3 = child(span_1);
        var svg2 = sibling(div_5, 2);
        let classes_2;
        var node_2 = sibling(button, 2);
        {
          var consequent_4 = ($$anchor4) => {
            var div_6 = root_5$5();
            var node_3 = child(div_6);
            each(node_3, 17, () => get$1(models), index, ($$anchor5, model, index2) => {
              var div_7 = root_6$5();
              var div_8 = child(div_7);
              var input = child(div_8);
              input.__input = (e2) => updateModelField(provider, index2, "id", e2.target.value);
              var input_1 = sibling(input, 2);
              input_1.__input = (e2) => updateModelField(provider, index2, "name", e2.target.value);
              var input_2 = sibling(input_1, 2);
              input_2.__input = (e2) => updateModelField(provider, index2, "description", e2.target.value);
              var div_9 = sibling(div_8, 2);
              var button_1 = child(div_9);
              let classes_3;
              button_1.__click = () => setDefault(provider, index2);
              var svg_1 = child(button_1);
              var node_4 = child(svg_1);
              {
                var consequent_2 = ($$anchor6) => {
                  var path = root_7$4();
                  append($$anchor6, path);
                };
                var alternate = ($$anchor6) => {
                  var path_1 = root_8$4();
                  append($$anchor6, path_1);
                };
                if_block(node_4, ($$render) => {
                  if (get$1(model).default) $$render(consequent_2);
                  else $$render(alternate, false);
                });
              }
              var button_2 = sibling(button_1, 2);
              button_2.__click = () => removeModel(provider, index2);
              template_effect(() => {
                set_value(input, get$1(model).id);
                set_value(input_1, get$1(model).name);
                set_value(input_2, get$1(model).description || "");
                classes_3 = set_class(button_1, 1, "icon-btn svelte-fraw8h", null, classes_3, { active: get$1(model).default });
                set_attribute(button_1, "title", get$1(model).default ? "Default model" : "Set as default");
              });
              append($$anchor5, div_7);
            });
            var node_5 = sibling(node_3, 2);
            {
              var consequent_3 = ($$anchor5) => {
                var div_10 = root_9$2();
                append($$anchor5, div_10);
              };
              if_block(node_5, ($$render) => {
                if (get$1(models).length === 0) $$render(consequent_3);
              });
            }
            var div_11 = sibling(node_5, 2);
            var button_3 = child(div_11);
            button_3.__click = () => addModel(provider);
            var div_12 = sibling(button_3, 2);
            var button_4 = child(div_12);
            button_4.__click = () => handleRevert(provider);
            var button_5 = sibling(button_4, 2);
            button_5.__click = () => handleSave(provider);
            var text_4 = child(button_5);
            template_effect(() => {
              button_5.disabled = get$1(saving) === provider;
              set_text(text_4, get$1(saving) === provider ? "Saving..." : "Save");
            });
            append($$anchor4, div_6);
          };
          if_block(node_2, ($$render) => {
            if (get$1(isExpanded)) $$render(consequent_4);
          });
        }
        template_effect(() => {
          classes_1 = set_class(div_4, 1, "provider-card svelte-fraw8h", null, classes_1, { expanded: get$1(isExpanded) });
          set_text(text_2, get$1(pc).display_name || provider);
          set_text(text_3, `${(get$1(pc).models || []).length ?? ""} models`);
          classes_2 = set_class(svg2, 0, "chevron svelte-fraw8h", null, classes_2, { rotated: get$1(isExpanded) });
        });
        append($$anchor3, div_4);
      });
      append($$anchor2, div_3);
    };
    if_block(node_1, ($$render) => {
      if (get$1(loading)) $$render(consequent_1);
      else $$render(alternate_1, false);
    });
  }
  append($$anchor, div);
  pop();
}
delegate(["click", "input"]);
var root_1$8 = /* @__PURE__ */ from_html(`<option> </option>`);
var root_2$3 = /* @__PURE__ */ from_html(`<div class="loading-text svelte-1udswlp">Loading models...</div>`);
var root_4$4 = /* @__PURE__ */ from_html(`<option> </option>`);
var root_3$4 = /* @__PURE__ */ from_html(`<select id="default-model" class="select svelte-1udswlp"><option>-- Provider default --</option><!></select>`);
var root_6$4 = /* @__PURE__ */ from_html(`<span class="badge svelte-1udswlp"> </span>`);
var root_7$3 = /* @__PURE__ */ from_html(`<span class="badge model svelte-1udswlp"> </span>`);
var root_5$4 = /* @__PURE__ */ from_html(`<div class="current-defaults svelte-1udswlp"><strong>Current defaults:</strong> <!> <!></div>`);
var root_8$3 = /* @__PURE__ */ from_html(`<div> </div>`);
var root_9$1 = /* @__PURE__ */ from_html(`<button class="btn secondary svelte-1udswlp">Clear Defaults</button>`);
var root$8 = /* @__PURE__ */ from_html(`<div class="defaults-editor svelte-1udswlp"><p class="description svelte-1udswlp">Set a default provider and model that will be automatically selected when you open the chat.</p> <div class="field svelte-1udswlp"><label for="default-provider" class="svelte-1udswlp">Default Provider</label> <select id="default-provider" class="select svelte-1udswlp"><option>-- None (auto-select first) --</option><!></select></div> <div class="field svelte-1udswlp"><label for="default-model" class="svelte-1udswlp">Default Model</label> <!></div> <!> <!> <div class="actions svelte-1udswlp"><button class="btn primary svelte-1udswlp"> </button> <!></div></div>`);
function DefaultsEditor($$anchor, $$props) {
  push($$props, true);
  const $providerState = () => store_get(providerState, "$providerState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  let selectedProvider = /* @__PURE__ */ state(null);
  let selectedModel = /* @__PURE__ */ state(null);
  let models = /* @__PURE__ */ state(proxy([]));
  let loading = /* @__PURE__ */ state(false);
  let saving = /* @__PURE__ */ state(false);
  let message = /* @__PURE__ */ state(null);
  let messageType = /* @__PURE__ */ state("success");
  user_effect(() => {
    const ps = $providerState();
    if (get$1(selectedProvider) === null) {
      set(selectedProvider, ps.defaultProvider, true);
    }
    if (get$1(selectedModel) === null) {
      set(selectedModel, ps.defaultModel, true);
    }
  });
  user_effect(() => {
    if (get$1(selectedProvider)) {
      loadModelsForProvider(get$1(selectedProvider));
    } else {
      set(models, [], true);
    }
  });
  async function loadModelsForProvider(provider) {
    const hass = get(appState).hass;
    if (!hass) return;
    set(loading, true);
    try {
      const result = await hass.callWS({ type: "homeclaw/models/list", provider });
      set(models, result.models || [], true);
    } catch (e2) {
      console.warn("[DefaultsEditor] Failed to load models:", e2);
      set(models, [], true);
    } finally {
      set(loading, false);
    }
  }
  async function handleSave() {
    const hass = get(appState).hass;
    if (!hass) return;
    set(saving, true);
    set(message, null);
    try {
      await savePreferences(hass, {
        default_provider: get$1(selectedProvider),
        default_model: get$1(selectedModel)
      });
      set(message, "Defaults saved successfully");
      set(messageType, "success");
    } catch (e2) {
      console.error("[DefaultsEditor] Failed to save:", e2);
      set(message, e2?.message || "Failed to save defaults", true);
      set(messageType, "error");
    } finally {
      set(saving, false);
      setTimeout(() => set(message, null), 3e3);
    }
  }
  async function handleClear() {
    const hass = get(appState).hass;
    if (!hass) return;
    set(saving, true);
    set(message, null);
    try {
      await savePreferences(hass, { default_provider: null, default_model: null });
      set(selectedProvider, null);
      set(selectedModel, null);
      set(message, "Defaults cleared");
      set(messageType, "success");
    } catch (e2) {
      set(message, e2?.message || "Failed to clear defaults", true);
      set(messageType, "error");
    } finally {
      set(saving, false);
      setTimeout(() => set(message, null), 3e3);
    }
  }
  function handleProviderChange(e2) {
    const target = e2.target;
    set(selectedProvider, target.value || null, true);
    set(selectedModel, null);
  }
  function handleModelChange(e2) {
    const target = e2.target;
    set(selectedModel, target.value || null, true);
  }
  const hasDefaults = /* @__PURE__ */ user_derived(() => $providerState().defaultProvider !== null || $providerState().defaultModel !== null);
  var div = root$8();
  var div_1 = sibling(child(div), 2);
  var select = sibling(child(div_1), 2);
  select.__change = handleProviderChange;
  var option = child(select);
  option.value = option.__value = "";
  var node = sibling(option);
  each(node, 1, () => $providerState().availableProviders, index, ($$anchor2, provider) => {
    var option_1 = root_1$8();
    var text2 = child(option_1);
    var option_1_value = {};
    template_effect(() => {
      set_text(text2, get$1(provider).label);
      if (option_1_value !== (option_1_value = get$1(provider).value)) {
        option_1.value = (option_1.__value = get$1(provider).value) ?? "";
      }
    });
    append($$anchor2, option_1);
  });
  var select_value;
  init_select(select);
  var div_2 = sibling(div_1, 2);
  var node_1 = sibling(child(div_2), 2);
  {
    var consequent = ($$anchor2) => {
      var div_3 = root_2$3();
      append($$anchor2, div_3);
    };
    var alternate = ($$anchor2) => {
      var select_1 = root_3$4();
      select_1.__change = handleModelChange;
      var option_2 = child(select_1);
      option_2.value = option_2.__value = "";
      var node_2 = sibling(option_2);
      each(node_2, 17, () => get$1(models), index, ($$anchor3, model) => {
        var option_3 = root_4$4();
        var text_1 = child(option_3);
        var option_3_value = {};
        template_effect(() => {
          set_text(text_1, `${get$1(model).name ?? ""}${get$1(model).default ? " (provider default)" : ""}`);
          if (option_3_value !== (option_3_value = get$1(model).id)) {
            option_3.value = (option_3.__value = get$1(model).id) ?? "";
          }
        });
        append($$anchor3, option_3);
      });
      var select_1_value;
      init_select(select_1);
      template_effect(() => {
        select_1.disabled = !get$1(selectedProvider) || get$1(models).length === 0;
        if (select_1_value !== (select_1_value = get$1(selectedModel) || "")) {
          select_1.value = (select_1.__value = get$1(selectedModel) || "") ?? "", select_option(select_1, get$1(selectedModel) || "");
        }
      });
      append($$anchor2, select_1);
    };
    if_block(node_1, ($$render) => {
      if (get$1(loading)) $$render(consequent);
      else $$render(alternate, false);
    });
  }
  var node_3 = sibling(div_2, 2);
  {
    var consequent_3 = ($$anchor2) => {
      var div_4 = root_5$4();
      var node_4 = sibling(child(div_4), 2);
      {
        var consequent_1 = ($$anchor3) => {
          var span = root_6$4();
          var text_2 = child(span);
          template_effect(($0) => set_text(text_2, $0), [
            () => $providerState().availableProviders.find((p2) => p2.value === $providerState().defaultProvider)?.label || $providerState().defaultProvider
          ]);
          append($$anchor3, span);
        };
        if_block(node_4, ($$render) => {
          if ($providerState().defaultProvider) $$render(consequent_1);
        });
      }
      var node_5 = sibling(node_4, 2);
      {
        var consequent_2 = ($$anchor3) => {
          var span_1 = root_7$3();
          var text_3 = child(span_1);
          template_effect(() => set_text(text_3, $providerState().defaultModel));
          append($$anchor3, span_1);
        };
        if_block(node_5, ($$render) => {
          if ($providerState().defaultModel) $$render(consequent_2);
        });
      }
      append($$anchor2, div_4);
    };
    if_block(node_3, ($$render) => {
      if (get$1(hasDefaults)) $$render(consequent_3);
    });
  }
  var node_6 = sibling(node_3, 2);
  {
    var consequent_4 = ($$anchor2) => {
      var div_5 = root_8$3();
      let classes;
      var text_4 = child(div_5);
      template_effect(() => {
        classes = set_class(div_5, 1, "message svelte-1udswlp", null, classes, { error: get$1(messageType) === "error" });
        set_text(text_4, get$1(message));
      });
      append($$anchor2, div_5);
    };
    if_block(node_6, ($$render) => {
      if (get$1(message)) $$render(consequent_4);
    });
  }
  var div_6 = sibling(node_6, 2);
  var button = child(div_6);
  button.__click = handleSave;
  var text_5 = child(button);
  var node_7 = sibling(button, 2);
  {
    var consequent_5 = ($$anchor2) => {
      var button_1 = root_9$1();
      button_1.__click = handleClear;
      template_effect(() => button_1.disabled = get$1(saving));
      append($$anchor2, button_1);
    };
    if_block(node_7, ($$render) => {
      if (get$1(hasDefaults)) $$render(consequent_5);
    });
  }
  template_effect(() => {
    if (select_value !== (select_value = get$1(selectedProvider) || "")) {
      select.value = (select.__value = get$1(selectedProvider) || "") ?? "", select_option(select, get$1(selectedProvider) || "");
    }
    button.disabled = get$1(saving);
    set_text(text_5, get$1(saving) ? "Saving..." : "Save Defaults");
  });
  append($$anchor, div);
  pop();
  $$cleanup();
}
delegate(["change", "click"]);
function getHass() {
  return get(appState).hass;
}
function formatTimestamp(ts) {
  if (!ts) return "-";
  return new Date(ts * 1e3).toLocaleString();
}
function formatExpiresAt(expiresAt) {
  if (!expiresAt) return "";
  const now = Date.now() / 1e3;
  const daysLeft = Math.max(0, (expiresAt - now) / 86400);
  if (daysLeft < 1) {
    const hoursLeft = Math.max(0, (expiresAt - now) / 3600);
    return `${Math.round(hoursLeft)}h left`;
  }
  return `${Math.round(daysLeft)}d left`;
}
var root_2$2 = /* @__PURE__ */ from_html(`<button class="btn text btn-sm svelte-1lsjbvq">Edit</button>`);
var root_3$3 = /* @__PURE__ */ from_html(`<div class="identity-form svelte-1lsjbvq"><div class="form-group svelte-1lsjbvq"><label for="id-agent-name" class="svelte-1lsjbvq">Agent Name</label> <input id="id-agent-name" type="text" placeholder="e.g. Jarvis" class="svelte-1lsjbvq"/></div> <div class="form-group svelte-1lsjbvq"><label for="id-agent-personality" class="svelte-1lsjbvq">Personality</label> <textarea id="id-agent-personality" placeholder="e.g. Friendly, witty, concise" rows="2" class="svelte-1lsjbvq"></textarea></div> <div class="form-group svelte-1lsjbvq"><label for="id-agent-emoji" class="svelte-1lsjbvq">Emoji</label> <input id="id-agent-emoji" type="text" placeholder="e.g. 🤖" maxlength="4" class="emoji-input svelte-1lsjbvq"/></div> <div class="form-group svelte-1lsjbvq"><label for="id-user-name" class="svelte-1lsjbvq">Your Name</label> <input id="id-user-name" type="text" placeholder="e.g. Adam" class="svelte-1lsjbvq"/></div> <div class="form-group svelte-1lsjbvq"><label for="id-user-info" class="svelte-1lsjbvq">About You</label> <textarea id="id-user-info" placeholder="e.g. Lives in Warsaw, works from home, has 2 cats" rows="3" class="svelte-1lsjbvq"></textarea></div> <div class="form-group svelte-1lsjbvq"><label for="id-language" class="svelte-1lsjbvq">Language</label> <select id="id-language" class="svelte-1lsjbvq"><option>Auto-detect</option><option>Polski</option><option>English</option><option>Deutsch</option><option>Français</option><option>Español</option><option>Italiano</option><option>Nederlands</option><option>Українська</option></select></div> <div class="form-actions svelte-1lsjbvq"><button class="btn primary svelte-1lsjbvq"> </button> <button class="btn text svelte-1lsjbvq">Cancel</button></div></div>`);
var root_4$3 = /* @__PURE__ */ from_html(`<div class="kv-grid svelte-1lsjbvq"><span class="k svelte-1lsjbvq">Name</span><span class="v svelte-1lsjbvq"> </span> <span class="k svelte-1lsjbvq">Personality</span><span class="v svelte-1lsjbvq"> </span> <span class="k svelte-1lsjbvq">User</span><span class="v svelte-1lsjbvq"> </span> <span class="k svelte-1lsjbvq">Language</span><span class="v svelte-1lsjbvq"> </span> <span class="k svelte-1lsjbvq">Onboarded</span><span class="v svelte-1lsjbvq"> </span></div>`);
var root_1$7 = /* @__PURE__ */ from_html(`<div class="card svelte-1lsjbvq"><div class="card-header svelte-1lsjbvq"><h3 class="svelte-1lsjbvq">Agent Identity</h3> <!></div> <!></div>`);
var root_5$3 = /* @__PURE__ */ from_html(`<div class="card svelte-1lsjbvq"><div class="card-header svelte-1lsjbvq"><h3 class="svelte-1lsjbvq">Agent Identity</h3> <button class="btn text btn-sm svelte-1lsjbvq">Set up</button></div> <p class="desc svelte-1lsjbvq">No identity configured yet. Click "Set up" to create one, or start a conversation to go
        through the onboarding flow.</p></div>`);
var root_7$2 = /* @__PURE__ */ from_html(`<div class="card svelte-1lsjbvq"><h3 class="svelte-1lsjbvq">Session Index</h3> <div class="kv-grid svelte-1lsjbvq"><span class="k svelte-1lsjbvq">Total chunks</span><span class="v svelte-1lsjbvq"> </span> <span class="k svelte-1lsjbvq">Indexed sessions</span><span class="v svelte-1lsjbvq"> </span> <span class="k svelte-1lsjbvq">Storage</span><span class="v svelte-1lsjbvq"> </span></div></div>`);
var root_6$3 = /* @__PURE__ */ from_html(`<div class="card svelte-1lsjbvq"><h3 class="svelte-1lsjbvq">Entity Index</h3> <div class="kv-grid svelte-1lsjbvq"><span class="k svelte-1lsjbvq">Indexed entities</span><span class="v svelte-1lsjbvq"> </span> <span class="k svelte-1lsjbvq">Embedding provider</span><span class="v svelte-1lsjbvq"> </span> <span class="k svelte-1lsjbvq">Dimensions</span><span class="v svelte-1lsjbvq"> </span></div></div> <!>`, 1);
var root_10$2 = /* @__PURE__ */ from_html(`<span class="k cat svelte-1lsjbvq"> </span><span class="v svelte-1lsjbvq"> </span>`, 1);
var root_13$1 = /* @__PURE__ */ from_html(`<span class="k source-label svelte-1lsjbvq"> </span> <span> </span>`, 1);
var root_14$1 = /* @__PURE__ */ from_html(`<span class="k svelte-1lsjbvq">With TTL (ephemeral)</span> <span class="v svelte-1lsjbvq"> </span>`, 1);
var root_15$1 = /* @__PURE__ */ from_html(`<span class="k svelte-1lsjbvq">Expiring within 3 days</span> <span class="v expiring-count svelte-1lsjbvq"> </span>`, 1);
var root_11$1 = /* @__PURE__ */ from_html(`<div class="card smart-memory-card svelte-1lsjbvq"><h3 class="svelte-1lsjbvq">Smart Memory</h3> <div class="kv-grid svelte-1lsjbvq"><!> <!> <!></div></div>`);
var root_8$2 = /* @__PURE__ */ from_html(`<div class="card svelte-1lsjbvq"><h3 class="svelte-1lsjbvq">Memories</h3> <div class="kv-grid svelte-1lsjbvq"><span class="k svelte-1lsjbvq">Total</span><span class="v svelte-1lsjbvq"> </span> <!></div></div> <!>`, 1);
var root$7 = /* @__PURE__ */ from_html(`<div class="section svelte-1lsjbvq"><!> <!> <!> <button class="btn text svelte-1lsjbvq">Refresh</button></div>`);
function RagOverview($$anchor, $$props) {
  push($$props, true);
  let identityEditing = /* @__PURE__ */ state(false);
  let identityForm = /* @__PURE__ */ state(proxy({
    agent_name: "",
    agent_personality: "",
    agent_emoji: "",
    user_name: "",
    user_info: "",
    language: "auto"
  }));
  let identitySaving = /* @__PURE__ */ state(false);
  function startEditingIdentity() {
    if ($$props.stats?.identity) {
      set(
        identityForm,
        {
          agent_name: $$props.stats.identity.agent_name || "",
          agent_personality: $$props.stats.identity.agent_personality || "",
          agent_emoji: $$props.stats.identity.agent_emoji || "",
          user_name: $$props.stats.identity.user_name || "",
          user_info: $$props.stats.identity.user_info || "",
          language: $$props.stats.identity.language || "auto"
        },
        true
      );
    }
    set(identityEditing, true);
  }
  function cancelEditingIdentity() {
    set(identityEditing, false);
  }
  async function saveIdentity() {
    const hass = getHass();
    if (!hass) return;
    set(identitySaving, true);
    try {
      await hass.callWS({ type: "homeclaw/rag/identity/update", ...get$1(identityForm) });
      set(identityEditing, false);
      $$props.onMessage("Identity saved", "success");
      $$props.onRefresh();
    } catch (e2) {
      $$props.onMessage(e2?.message || "Failed to save identity", "error");
    } finally {
      set(identitySaving, false);
    }
  }
  var div = root$7();
  var node = child(div);
  {
    var consequent_2 = ($$anchor2) => {
      var div_1 = root_1$7();
      var div_2 = child(div_1);
      var node_1 = sibling(child(div_2), 2);
      {
        var consequent = ($$anchor3) => {
          var button = root_2$2();
          button.__click = startEditingIdentity;
          append($$anchor3, button);
        };
        if_block(node_1, ($$render) => {
          if (!get$1(identityEditing)) $$render(consequent);
        });
      }
      var node_2 = sibling(div_2, 2);
      {
        var consequent_1 = ($$anchor3) => {
          var div_3 = root_3$3();
          var div_4 = child(div_3);
          var input = sibling(child(div_4), 2);
          var div_5 = sibling(div_4, 2);
          var textarea = sibling(child(div_5), 2);
          var div_6 = sibling(div_5, 2);
          var input_1 = sibling(child(div_6), 2);
          var div_7 = sibling(div_6, 2);
          var input_2 = sibling(child(div_7), 2);
          var div_8 = sibling(div_7, 2);
          var textarea_1 = sibling(child(div_8), 2);
          var div_9 = sibling(div_8, 2);
          var select = sibling(child(div_9), 2);
          var option = child(select);
          option.value = option.__value = "auto";
          var option_1 = sibling(option);
          option_1.value = option_1.__value = "pl";
          var option_2 = sibling(option_1);
          option_2.value = option_2.__value = "en";
          var option_3 = sibling(option_2);
          option_3.value = option_3.__value = "de";
          var option_4 = sibling(option_3);
          option_4.value = option_4.__value = "fr";
          var option_5 = sibling(option_4);
          option_5.value = option_5.__value = "es";
          var option_6 = sibling(option_5);
          option_6.value = option_6.__value = "it";
          var option_7 = sibling(option_6);
          option_7.value = option_7.__value = "nl";
          var option_8 = sibling(option_7);
          option_8.value = option_8.__value = "uk";
          var div_10 = sibling(div_9, 2);
          var button_1 = child(div_10);
          button_1.__click = saveIdentity;
          var text2 = child(button_1);
          var button_2 = sibling(button_1, 2);
          button_2.__click = cancelEditingIdentity;
          template_effect(() => {
            button_1.disabled = get$1(identitySaving);
            set_text(text2, get$1(identitySaving) ? "Saving..." : "Save");
          });
          bind_value(input, () => get$1(identityForm).agent_name, ($$value) => get$1(identityForm).agent_name = $$value);
          bind_value(textarea, () => get$1(identityForm).agent_personality, ($$value) => get$1(identityForm).agent_personality = $$value);
          bind_value(input_1, () => get$1(identityForm).agent_emoji, ($$value) => get$1(identityForm).agent_emoji = $$value);
          bind_value(input_2, () => get$1(identityForm).user_name, ($$value) => get$1(identityForm).user_name = $$value);
          bind_value(textarea_1, () => get$1(identityForm).user_info, ($$value) => get$1(identityForm).user_info = $$value);
          bind_select_value(select, () => get$1(identityForm).language, ($$value) => get$1(identityForm).language = $$value);
          append($$anchor3, div_3);
        };
        var alternate = ($$anchor3) => {
          var div_11 = root_4$3();
          var span = sibling(child(div_11));
          var text_1 = child(span);
          var span_1 = sibling(span, 3);
          var text_2 = child(span_1);
          var span_2 = sibling(span_1, 3);
          var text_3 = child(span_2);
          var span_3 = sibling(span_2, 3);
          var text_4 = child(span_3);
          var span_4 = sibling(span_3, 3);
          var text_5 = child(span_4);
          template_effect(() => {
            set_text(text_1, `${($$props.stats.identity.agent_name || "-") ?? ""} ${($$props.stats.identity.agent_emoji || "") ?? ""}`);
            set_text(text_2, $$props.stats.identity.agent_personality || "-");
            set_text(text_3, $$props.stats.identity.user_name || "-");
            set_text(text_4, $$props.stats.identity.language || "auto");
            set_text(text_5, $$props.stats.identity.onboarding_completed ? "Yes" : "No");
          });
          append($$anchor3, div_11);
        };
        if_block(node_2, ($$render) => {
          if (get$1(identityEditing)) $$render(consequent_1);
          else $$render(alternate, false);
        });
      }
      append($$anchor2, div_1);
    };
    var alternate_1 = ($$anchor2) => {
      var div_12 = root_5$3();
      var div_13 = child(div_12);
      var button_3 = sibling(child(div_13), 2);
      button_3.__click = startEditingIdentity;
      append($$anchor2, div_12);
    };
    if_block(node, ($$render) => {
      if ($$props.stats.identity) $$render(consequent_2);
      else $$render(alternate_1, false);
    });
  }
  var node_3 = sibling(node, 2);
  {
    var consequent_4 = ($$anchor2) => {
      var fragment = root_6$3();
      var div_14 = first_child(fragment);
      var div_15 = sibling(child(div_14), 2);
      var span_5 = sibling(child(div_15));
      var text_6 = child(span_5);
      var span_6 = sibling(span_5, 3);
      var text_7 = child(span_6);
      var span_7 = sibling(span_6, 3);
      var text_8 = child(span_7);
      var node_4 = sibling(div_14, 2);
      {
        var consequent_3 = ($$anchor3) => {
          var div_16 = root_7$2();
          var div_17 = sibling(child(div_16), 2);
          var span_8 = sibling(child(div_17));
          var text_9 = child(span_8);
          var span_9 = sibling(span_8, 3);
          var text_10 = child(span_9);
          var span_10 = sibling(span_9, 3);
          var text_11 = child(span_10);
          template_effect(() => {
            set_text(text_9, $$props.stats.stats.session_chunks.total_chunks);
            set_text(text_10, $$props.stats.stats.session_chunks.indexed_sessions);
            set_text(text_11, `${$$props.stats.stats.session_chunks.total_mb ?? ""} MB`);
          });
          append($$anchor3, div_16);
        };
        if_block(node_4, ($$render) => {
          if ($$props.stats.stats.session_chunks) $$render(consequent_3);
        });
      }
      template_effect(() => {
        set_text(text_6, $$props.stats.stats.indexed_entities ?? $$props.stats.stats.total_documents ?? "-");
        set_text(text_7, $$props.stats.stats.embedding_provider || "-");
        set_text(text_8, $$props.stats.stats.embedding_dimensions || "-");
      });
      append($$anchor2, fragment);
    };
    if_block(node_3, ($$render) => {
      if ($$props.stats.stats) $$render(consequent_4);
    });
  }
  var node_5 = sibling(node_3, 2);
  {
    var consequent_10 = ($$anchor2) => {
      var fragment_1 = root_8$2();
      var div_18 = first_child(fragment_1);
      var div_19 = sibling(child(div_18), 2);
      var span_11 = sibling(child(div_19));
      var text_12 = child(span_11);
      var node_6 = sibling(span_11, 2);
      {
        var consequent_5 = ($$anchor3) => {
          var fragment_2 = comment();
          var node_7 = first_child(fragment_2);
          each(node_7, 17, () => Object.entries($$props.stats.memory_stats.categories), index, ($$anchor4, $$item) => {
            var $$array = /* @__PURE__ */ user_derived(() => to_array(get$1($$item), 2));
            let cat = () => get$1($$array)[0];
            let count = () => get$1($$array)[1];
            var fragment_3 = root_10$2();
            var span_12 = first_child(fragment_3);
            var text_13 = child(span_12);
            var span_13 = sibling(span_12);
            var text_14 = child(span_13);
            template_effect(() => {
              set_text(text_13, cat());
              set_text(text_14, count());
            });
            append($$anchor4, fragment_3);
          });
          append($$anchor3, fragment_2);
        };
        if_block(node_6, ($$render) => {
          if ($$props.stats.memory_stats.categories) $$render(consequent_5);
        });
      }
      var node_8 = sibling(div_18, 2);
      {
        var consequent_9 = ($$anchor3) => {
          var div_20 = root_11$1();
          var div_21 = sibling(child(div_20), 2);
          var node_9 = child(div_21);
          {
            var consequent_6 = ($$anchor4) => {
              var fragment_4 = comment();
              var node_10 = first_child(fragment_4);
              each(node_10, 17, () => Object.entries($$props.stats.memory_stats.sources), index, ($$anchor5, $$item) => {
                var $$array_1 = /* @__PURE__ */ user_derived(() => to_array(get$1($$item), 2));
                let src = () => get$1($$array_1)[0];
                let count = () => get$1($$array_1)[1];
                var fragment_5 = root_13$1();
                var span_14 = first_child(fragment_5);
                var text_15 = child(span_14);
                var span_15 = sibling(span_14, 2);
                let classes;
                var text_16 = child(span_15);
                template_effect(() => {
                  set_text(text_15, src() === "agent" ? "Agent (proactive)" : src() === "auto" ? "Auto-captured" : src() === "user" ? "User/tool" : src());
                  classes = set_class(span_15, 1, "v svelte-1lsjbvq", null, classes, { highlight: src() === "agent" });
                  set_text(text_16, count());
                });
                append($$anchor5, fragment_5);
              });
              append($$anchor4, fragment_4);
            };
            if_block(node_9, ($$render) => {
              if ($$props.stats.memory_stats.sources) $$render(consequent_6);
            });
          }
          var node_11 = sibling(node_9, 2);
          {
            var consequent_7 = ($$anchor4) => {
              var fragment_6 = root_14$1();
              var span_16 = sibling(first_child(fragment_6), 2);
              var text_17 = child(span_16);
              template_effect(() => set_text(text_17, $$props.stats.memory_stats.total_with_ttl));
              append($$anchor4, fragment_6);
            };
            if_block(node_11, ($$render) => {
              if ($$props.stats.memory_stats.total_with_ttl) $$render(consequent_7);
            });
          }
          var node_12 = sibling(node_11, 2);
          {
            var consequent_8 = ($$anchor4) => {
              var fragment_7 = root_15$1();
              var span_17 = sibling(first_child(fragment_7), 2);
              var text_18 = child(span_17);
              template_effect(() => set_text(text_18, $$props.stats.memory_stats.expiring_soon));
              append($$anchor4, fragment_7);
            };
            if_block(node_12, ($$render) => {
              if ($$props.stats.memory_stats.expiring_soon) $$render(consequent_8);
            });
          }
          append($$anchor3, div_20);
        };
        if_block(node_8, ($$render) => {
          if ($$props.stats.memory_stats.sources || $$props.stats.memory_stats.expiring_soon !== void 0) $$render(consequent_9);
        });
      }
      template_effect(() => set_text(text_12, $$props.stats.memory_stats.total || 0));
      append($$anchor2, fragment_1);
    };
    if_block(node_5, ($$render) => {
      if ($$props.stats.memory_stats) $$render(consequent_10);
    });
  }
  var button_4 = sibling(node_5, 2);
  button_4.__click = function(...$$args) {
    $$props.onRefresh?.apply(this, $$args);
  };
  append($$anchor, div);
  pop();
}
delegate(["click"]);
var root_1$6 = /* @__PURE__ */ from_html(`<div class="empty svelte-maj3ai">Loading memories...</div>`);
var root_3$2 = /* @__PURE__ */ from_html(`<div class="empty svelte-maj3ai">No memories found.</div>`);
var root_6$2 = /* @__PURE__ */ from_html(`<span class="badge ttl-badge svelte-maj3ai"> </span>`);
var root_5$2 = /* @__PURE__ */ from_html(`<div><div class="memory-header svelte-maj3ai"><span> </span> <!> <span class="importance svelte-maj3ai" title="Importance"> </span> <span class="source svelte-maj3ai"> </span> <button class="del-btn svelte-maj3ai" title="Delete memory">x</button></div> <div class="memory-text svelte-maj3ai"> </div> <div class="memory-meta svelte-maj3ai"> </div></div>`);
var root$6 = /* @__PURE__ */ from_html(`<div class="section svelte-maj3ai"><div class="toolbar svelte-maj3ai"><select class="filter-select svelte-maj3ai"><option>All categories</option><option>fact</option><option>preference</option><option>decision</option><option>entity</option><option>observation</option><option>other</option></select> <select class="filter-select svelte-maj3ai"><option>All sources</option><option>agent (proactive)</option><option>auto-captured</option><option>user/tool</option></select> <span class="count svelte-maj3ai"> </span></div> <!></div>`);
function RagMemories($$anchor, $$props) {
  push($$props, true);
  let memories = /* @__PURE__ */ state(proxy([]));
  let memoriesLoaded = /* @__PURE__ */ state(false);
  let loading = /* @__PURE__ */ state(false);
  let categoryFilter = /* @__PURE__ */ state("");
  let sourceFilter = /* @__PURE__ */ state("");
  let filteredMemories = /* @__PURE__ */ user_derived(() => get$1(sourceFilter) ? get$1(memories).filter((m2) => m2.source === get$1(sourceFilter)) : get$1(memories));
  user_effect(() => {
    if (!get$1(memoriesLoaded)) loadMemories();
  });
  async function loadMemories() {
    const hass = getHass();
    if (!hass) return;
    set(loading, true);
    try {
      const result = await hass.callWS({
        type: "homeclaw/rag/memories",
        limit: 100,
        ...get$1(categoryFilter) ? { category: get$1(categoryFilter) } : {}
      });
      set(memories, result.memories || [], true);
      set(memoriesLoaded, true);
    } catch (e2) {
      console.error("[RagViewer] Failed to load memories:", e2);
    } finally {
      set(loading, false);
    }
  }
  async function deleteMemory(id) {
    const hass = getHass();
    if (!hass) return;
    try {
      await hass.callWS({ type: "homeclaw/rag/memory/delete", memory_id: id });
      set(memories, get$1(memories).filter((m2) => m2.id !== id), true);
      $$props.onMessage("Memory deleted", "success");
    } catch (e2) {
      $$props.onMessage(e2?.message || "Failed to delete", "error");
    }
  }
  var div = root$6();
  var div_1 = child(div);
  var select = child(div_1);
  select.__change = loadMemories;
  var option = child(select);
  option.value = option.__value = "";
  var option_1 = sibling(option);
  option_1.value = option_1.__value = "fact";
  var option_2 = sibling(option_1);
  option_2.value = option_2.__value = "preference";
  var option_3 = sibling(option_2);
  option_3.value = option_3.__value = "decision";
  var option_4 = sibling(option_3);
  option_4.value = option_4.__value = "entity";
  var option_5 = sibling(option_4);
  option_5.value = option_5.__value = "observation";
  var option_6 = sibling(option_5);
  option_6.value = option_6.__value = "other";
  var select_1 = sibling(select, 2);
  var option_7 = child(select_1);
  option_7.value = option_7.__value = "";
  var option_8 = sibling(option_7);
  option_8.value = option_8.__value = "agent";
  var option_9 = sibling(option_8);
  option_9.value = option_9.__value = "auto";
  var option_10 = sibling(option_9);
  option_10.value = option_10.__value = "user";
  var span = sibling(select_1, 2);
  var text2 = child(span);
  var node = sibling(div_1, 2);
  {
    var consequent = ($$anchor2) => {
      var div_2 = root_1$6();
      append($$anchor2, div_2);
    };
    var alternate_1 = ($$anchor2) => {
      var fragment = comment();
      var node_1 = first_child(fragment);
      {
        var consequent_1 = ($$anchor3) => {
          var div_3 = root_3$2();
          append($$anchor3, div_3);
        };
        var alternate = ($$anchor3) => {
          var fragment_1 = comment();
          var node_2 = first_child(fragment_1);
          each(node_2, 17, () => get$1(filteredMemories), (mem) => mem.id, ($$anchor4, mem) => {
            var div_4 = root_5$2();
            let classes;
            var div_5 = child(div_4);
            var span_1 = child(div_5);
            var text_1 = child(span_1);
            var node_3 = sibling(span_1, 2);
            {
              var consequent_2 = ($$anchor5) => {
                var span_2 = root_6$2();
                var text_2 = child(span_2);
                template_effect(($0) => set_text(text_2, $0), [() => formatExpiresAt(get$1(mem).expires_at)]);
                append($$anchor5, span_2);
              };
              if_block(node_3, ($$render) => {
                if (get$1(mem).expires_at) $$render(consequent_2);
              });
            }
            var span_3 = sibling(node_3, 2);
            var text_3 = child(span_3);
            var span_4 = sibling(span_3, 2);
            var text_4 = child(span_4);
            var button = sibling(span_4, 2);
            button.__click = () => deleteMemory(get$1(mem).id);
            var div_6 = sibling(div_5, 2);
            var text_5 = child(div_6);
            var div_7 = sibling(div_6, 2);
            var text_6 = child(div_7);
            template_effect(
              ($0, $1) => {
                classes = set_class(div_4, 1, "memory-card svelte-maj3ai", null, classes, $0);
                set_class(span_1, 1, `badge cat-${get$1(mem).category ?? ""}`, "svelte-maj3ai");
                set_text(text_1, get$1(mem).category);
                set_text(text_3, get$1(mem).importance);
                set_text(text_4, get$1(mem).source);
                set_text(text_5, get$1(mem).text);
                set_text(text_6, $1);
              },
              [
                () => ({
                  expiring: get$1(mem).expires_at && get$1(mem).expires_at - Date.now() / 1e3 < 86400
                }),
                () => formatTimestamp(get$1(mem).created_at)
              ]
            );
            append($$anchor4, div_4);
          });
          append($$anchor3, fragment_1);
        };
        if_block(
          node_1,
          ($$render) => {
            if (get$1(filteredMemories).length === 0) $$render(consequent_1);
            else $$render(alternate, false);
          },
          true
        );
      }
      append($$anchor2, fragment);
    };
    if_block(node, ($$render) => {
      if (get$1(loading) && !get$1(memoriesLoaded)) $$render(consequent);
      else $$render(alternate_1, false);
    });
  }
  template_effect(() => set_text(text2, `${get$1(filteredMemories).length ?? ""} memories`));
  bind_select_value(select, () => get$1(categoryFilter), ($$value) => set(categoryFilter, $$value));
  bind_select_value(select_1, () => get$1(sourceFilter), ($$value) => set(sourceFilter, $$value));
  append($$anchor, div);
  pop();
}
delegate(["change", "click"]);
var root_1$5 = /* @__PURE__ */ from_html(`<div class="empty svelte-1gytc9k">Loading session chunks...</div>`);
var root_3$1 = /* @__PURE__ */ from_html(`<div class="empty svelte-1gytc9k">No session chunks indexed.</div>`);
var root_5$1 = /* @__PURE__ */ from_html(`<div class="chunk-card svelte-1gytc9k"><div class="chunk-header svelte-1gytc9k"><span class="badge svelte-1gytc9k"> </span> <span class="chunk-range svelte-1gytc9k"> </span> <span class="chunk-len svelte-1gytc9k"> </span></div> <pre class="chunk-text svelte-1gytc9k"> </pre></div>`);
var root$5 = /* @__PURE__ */ from_html(`<div class="section svelte-1gytc9k"><div class="toolbar svelte-1gytc9k"><span class="count svelte-1gytc9k"> </span> <button class="btn text svelte-1gytc9k">Refresh</button></div> <!></div>`);
function RagSessions($$anchor, $$props) {
  push($$props, true);
  let chunks = /* @__PURE__ */ state(proxy([]));
  let chunksLoaded = /* @__PURE__ */ state(false);
  let loading = /* @__PURE__ */ state(false);
  user_effect(() => {
    if (!get$1(chunksLoaded)) loadChunks();
  });
  async function loadChunks() {
    const hass = getHass();
    if (!hass) return;
    set(loading, true);
    try {
      const result = await hass.callWS({ type: "homeclaw/rag/sessions", limit: 100 });
      set(chunks, result.chunks || [], true);
      set(chunksLoaded, true);
    } catch (e2) {
      console.error("[RagViewer] Failed to load chunks:", e2);
    } finally {
      set(loading, false);
    }
  }
  var div = root$5();
  var div_1 = child(div);
  var span = child(div_1);
  var text2 = child(span);
  var button = sibling(span, 2);
  button.__click = loadChunks;
  var node = sibling(div_1, 2);
  {
    var consequent = ($$anchor2) => {
      var div_2 = root_1$5();
      append($$anchor2, div_2);
    };
    var alternate_1 = ($$anchor2) => {
      var fragment = comment();
      var node_1 = first_child(fragment);
      {
        var consequent_1 = ($$anchor3) => {
          var div_3 = root_3$1();
          append($$anchor3, div_3);
        };
        var alternate = ($$anchor3) => {
          var fragment_1 = comment();
          var node_2 = first_child(fragment_1);
          each(node_2, 17, () => get$1(chunks), (chunk) => chunk.id, ($$anchor4, chunk) => {
            var div_4 = root_5$1();
            var div_5 = child(div_4);
            var span_1 = child(div_5);
            var text_1 = child(span_1);
            var span_2 = sibling(span_1, 2);
            var text_2 = child(span_2);
            var span_3 = sibling(span_2, 2);
            var text_3 = child(span_3);
            var pre = sibling(div_5, 2);
            var text_4 = child(pre);
            template_effect(
              ($0) => {
                set_text(text_1, `session: ${$0 ?? ""}...`);
                set_text(text_2, `msgs ${get$1(chunk).start_msg ?? ""}-${get$1(chunk).end_msg ?? ""}`);
                set_text(text_3, `${get$1(chunk).text_length ?? ""} chars`);
                set_text(text_4, get$1(chunk).text);
              },
              [() => get$1(chunk).session_id.substring(0, 8)]
            );
            append($$anchor4, div_4);
          });
          append($$anchor3, fragment_1);
        };
        if_block(
          node_1,
          ($$render) => {
            if (get$1(chunks).length === 0) $$render(consequent_1);
            else $$render(alternate, false);
          },
          true
        );
      }
      append($$anchor2, fragment);
    };
    if_block(node, ($$render) => {
      if (get$1(loading) && !get$1(chunksLoaded)) $$render(consequent);
      else $$render(alternate_1, false);
    });
  }
  template_effect(() => set_text(text2, `${get$1(chunks).length ?? ""} chunks`));
  append($$anchor, div);
  pop();
}
delegate(["click"]);
var root_1$4 = /* @__PURE__ */ from_html(`<div class="search-result svelte-xtoz3f"><div class="search-meta svelte-xtoz3f"> </div> <pre class="search-text svelte-xtoz3f"> </pre></div>`);
var root$4 = /* @__PURE__ */ from_html(`<div class="section svelte-xtoz3f"><p class="desc svelte-xtoz3f">Test what RAG context would be generated for a given query.</p> <div class="search-row svelte-xtoz3f"><input class="search-input svelte-xtoz3f" placeholder="Enter a query..."/> <button class="btn primary svelte-xtoz3f"> </button></div> <!></div>`);
function RagSearch($$anchor, $$props) {
  push($$props, true);
  let searchQuery = /* @__PURE__ */ state("");
  let searchResult = /* @__PURE__ */ state(null);
  let searchLength = /* @__PURE__ */ state(0);
  let searching = /* @__PURE__ */ state(false);
  async function handleSearch() {
    if (!get$1(searchQuery).trim()) return;
    const hass = getHass();
    if (!hass) return;
    set(searching, true);
    set(searchResult, null);
    try {
      const result = await hass.callWS({
        type: "homeclaw/rag/search",
        query: get$1(searchQuery),
        top_k: 5
      });
      set(searchResult, result.context || "(no results)", true);
      set(searchLength, result.context_length || 0, true);
    } catch (e2) {
      set(searchResult, `Error: ${e2?.message || "search failed"}`);
      set(searchLength, 0);
    } finally {
      set(searching, false);
    }
  }
  var div = root$4();
  var div_1 = sibling(child(div), 2);
  var input = child(div_1);
  input.__keydown = (e2) => e2.key === "Enter" && handleSearch();
  var button = sibling(input, 2);
  button.__click = handleSearch;
  var text2 = child(button);
  var node = sibling(div_1, 2);
  {
    var consequent = ($$anchor2) => {
      var div_2 = root_1$4();
      var div_3 = child(div_2);
      var text_1 = child(div_3);
      var pre = sibling(div_3, 2);
      var text_2 = child(pre);
      template_effect(() => {
        set_text(text_1, `${get$1(searchLength) ?? ""} chars of context`);
        set_text(text_2, get$1(searchResult));
      });
      append($$anchor2, div_2);
    };
    if_block(node, ($$render) => {
      if (get$1(searchResult) !== null) $$render(consequent);
    });
  }
  template_effect(
    ($0) => {
      button.disabled = $0;
      set_text(text2, get$1(searching) ? "..." : "Search");
    },
    [() => get$1(searching) || !get$1(searchQuery).trim()]
  );
  bind_value(input, () => get$1(searchQuery), ($$value) => set(searchQuery, $$value));
  append($$anchor, div);
  pop();
}
delegate(["keydown", "click"]);
var root_1$3 = /* @__PURE__ */ from_html(`<div class="loading svelte-10ewjma">Analyzing RAG database...</div>`);
var root_5 = /* @__PURE__ */ from_html(`<span class="k svelte-10ewjma">Chunks reducible</span> <span class="v savings svelte-10ewjma"> </span>`, 1);
var root_6$1 = /* @__PURE__ */ from_html(`<span class="k svelte-10ewjma">Memories reducible</span> <span class="v savings svelte-10ewjma"> </span>`, 1);
var root_7$1 = /* @__PURE__ */ from_html(`<option> </option>`);
var root_8$1 = /* @__PURE__ */ from_html(`<option>Loading models...</option>`);
var root_10$1 = /* @__PURE__ */ from_html(`<option>Select provider first</option>`);
var root_12$1 = /* @__PURE__ */ from_html(`<option> </option>`);
var root_4$2 = /* @__PURE__ */ from_html(`<div class="card savings-card svelte-10ewjma"><h3 class="svelte-10ewjma">Estimated Savings</h3> <div class="kv-grid svelte-10ewjma"><!> <!></div></div> <div class="card svelte-10ewjma"><h3 class="svelte-10ewjma">Optimization Settings</h3> <div class="opt-form svelte-10ewjma"><div class="form-row svelte-10ewjma"><label for="opt-provider" class="svelte-10ewjma">Provider</label> <select id="opt-provider" class="filter-select svelte-10ewjma"><option>Select provider...</option><!></select></div> <div class="form-row svelte-10ewjma"><label for="opt-model" class="svelte-10ewjma">Model</label> <select id="opt-model" class="filter-select svelte-10ewjma"><!></select></div> <div class="form-row svelte-10ewjma"><label for="opt-scope" class="svelte-10ewjma">Scope</label> <select id="opt-scope" class="filter-select svelte-10ewjma"><option>All (sessions + memories)</option><option>Sessions only</option><option>Memories only</option></select></div> <div class="form-row checkbox-row svelte-10ewjma"><label for="opt-force" class="svelte-10ewjma"><input type="checkbox" id="opt-force" class="svelte-10ewjma"/> Force re-optimize all</label> <span class="hint svelte-10ewjma">Re-process sessions that were already optimized</span></div></div></div> <button class="btn primary optimize-btn svelte-10ewjma"><!></button>`, 1);
var root_15 = /* @__PURE__ */ from_html(`<div class="card svelte-10ewjma"><p class="no-savings svelte-10ewjma">RAG database is already compact. No optimization needed.</p></div>`);
var root_17$1 = /* @__PURE__ */ from_html(`<div class="progress-bar-container svelte-10ewjma"><div class="progress-bar svelte-10ewjma"></div></div>`);
var root_18$1 = /* @__PURE__ */ from_html(`<div> </div>`);
var root_16 = /* @__PURE__ */ from_html(`<div class="card progress-card svelte-10ewjma"><h3 class="svelte-10ewjma">Progress</h3> <!> <div class="progress-log svelte-10ewjma"></div></div>`);
var root_20$1 = /* @__PURE__ */ from_html(`<span class="k svelte-10ewjma">Session chunks</span> <span class="v svelte-10ewjma"> <span class="savings svelte-10ewjma"> </span></span>`, 1);
var root_21$1 = /* @__PURE__ */ from_html(`<span class="k svelte-10ewjma">Memories</span> <span class="v svelte-10ewjma"> <span class="savings svelte-10ewjma"> </span></span>`, 1);
var root_23 = /* @__PURE__ */ from_html(`<div class="error-line svelte-10ewjma"> </div>`);
var root_22$1 = /* @__PURE__ */ from_html(`<div class="error-list svelte-10ewjma"><strong>Errors:</strong> <!></div>`);
var root_19$1 = /* @__PURE__ */ from_html(`<div><h3 class="svelte-10ewjma">Optimization Result</h3> <div class="kv-grid svelte-10ewjma"><!> <!> <span class="k svelte-10ewjma">Duration</span><span class="v svelte-10ewjma"> </span> <span class="k svelte-10ewjma">Sessions processed</span><span class="v svelte-10ewjma"> </span></div> <!></div>`);
var root_3 = /* @__PURE__ */ from_html(`<div class="card svelte-10ewjma"><h3 class="svelte-10ewjma">Current Size</h3> <div class="kv-grid svelte-10ewjma"><span class="k svelte-10ewjma">Session chunks</span><span class="v svelte-10ewjma"> </span> <span class="k svelte-10ewjma">Sessions</span><span class="v svelte-10ewjma"> </span> <span class="k svelte-10ewjma">Optimizable sessions</span><span class="v highlight svelte-10ewjma"> </span> <span class="k svelte-10ewjma">Storage</span><span class="v svelte-10ewjma"> </span> <span class="k svelte-10ewjma">Memories</span><span class="v svelte-10ewjma"> </span></div></div> <!> <!> <!> <button class="btn text svelte-10ewjma">Refresh Analysis</button>`, 1);
var root_25 = /* @__PURE__ */ from_html(`<div class="not-initialized svelte-10ewjma">RAG system is not initialized.</div>`);
var root$3 = /* @__PURE__ */ from_html(`<div class="section svelte-10ewjma"><p class="desc svelte-10ewjma">Condense RAG data using an AI model. This reduces session chunks and merges duplicate memories
    while preserving important information.</p> <!></div>`);
function RagOptimize($$anchor, $$props) {
  push($$props, true);
  let analysis = /* @__PURE__ */ state(null);
  let analysisLoading = /* @__PURE__ */ state(false);
  let optimizeProvider = /* @__PURE__ */ state("");
  let optimizeModel = /* @__PURE__ */ state("");
  let optimizeScope = /* @__PURE__ */ state("all");
  let optimizeForce = /* @__PURE__ */ state(false);
  let optimizeModels = /* @__PURE__ */ state(proxy([]));
  let optimizeModelsLoading = /* @__PURE__ */ state(false);
  let optimizing = /* @__PURE__ */ state(false);
  let optimizeProgress = /* @__PURE__ */ state(proxy([]));
  let optimizeResult = /* @__PURE__ */ state(null);
  let optimizeProgressPct = /* @__PURE__ */ state(0);
  let prefsLoaded = /* @__PURE__ */ state(false);
  user_effect(() => {
    if (!get$1(analysis)) loadAnalysis();
    if (!get$1(prefsLoaded)) loadSavedPrefs();
  });
  async function loadSavedPrefs() {
    const hass = getHass();
    if (!hass) return;
    set(prefsLoaded, true);
    try {
      const result = await hass.callWS({ type: "homeclaw/preferences/get" });
      const prefs = result?.preferences || {};
      const savedProvider = prefs.rag_optimizer_provider;
      const savedModel = prefs.rag_optimizer_model;
      if (savedProvider) {
        set(optimizeProvider, savedProvider, true);
        await loadModelsForProvider(savedProvider);
        if (savedModel) {
          set(optimizeModel, savedModel, true);
        }
      }
    } catch (e2) {
      console.warn("[RagOptimize] Could not load saved preferences:", e2);
    }
  }
  async function saveOptimizerPrefs() {
    const hass = getHass();
    if (!hass) return;
    try {
      await hass.callWS({
        type: "homeclaw/preferences/set",
        rag_optimizer_provider: get$1(optimizeProvider) || null,
        rag_optimizer_model: get$1(optimizeModel) || null
      });
    } catch (e2) {
      console.warn("[RagOptimize] Could not save optimizer preferences:", e2);
    }
  }
  async function loadAnalysis() {
    const hass = getHass();
    if (!hass) return;
    set(analysisLoading, true);
    set(analysis, null);
    try {
      set(analysis, await hass.callWS({ type: "homeclaw/rag/optimize/analyze" }), true);
    } catch (e2) {
      console.error("[RagViewer] Failed to analyze:", e2);
      $$props.onMessage("Analysis failed", "error");
    } finally {
      set(analysisLoading, false);
    }
  }
  async function loadModelsForProvider(provider) {
    const hass = getHass();
    if (!hass || !provider) {
      set(optimizeModels, [], true);
      return;
    }
    set(optimizeModelsLoading, true);
    try {
      const result = await hass.callWS({ type: "homeclaw/models/list", provider });
      set(optimizeModels, result.models || [], true);
      const defaultModel = get$1(optimizeModels).find((m2) => m2.default);
      if (defaultModel) {
        set(optimizeModel, defaultModel.id, true);
      } else if (get$1(optimizeModels).length > 0) {
        set(optimizeModel, get$1(optimizeModels)[0].id, true);
      }
    } catch (e2) {
      console.error("[RagViewer] Failed to load models:", e2);
      set(optimizeModels, [], true);
    } finally {
      set(optimizeModelsLoading, false);
    }
  }
  async function handleProviderChange() {
    set(optimizeModel, "");
    if (get$1(optimizeProvider)) {
      await loadModelsForProvider(get$1(optimizeProvider));
    } else {
      set(optimizeModels, [], true);
    }
    saveOptimizerPrefs();
  }
  function handleModelChange() {
    saveOptimizerPrefs();
  }
  async function runOptimization() {
    const hass = getHass();
    if (!hass || !get$1(optimizeProvider) || !get$1(optimizeModel)) return;
    set(optimizing, true);
    set(optimizeProgress, [], true);
    set(optimizeResult, null);
    set(optimizeProgressPct, 0);
    try {
      let unsub;
      unsub = await hass.connection.subscribeMessage(
        (event2) => {
          const progressEvent = event2;
          set(optimizeProgress, [...get$1(optimizeProgress), progressEvent], true);
          if (progressEvent.progress !== void 0) {
            set(optimizeProgressPct, progressEvent.progress, true);
          }
          if (progressEvent.type === "result") {
            set(optimizeResult, event2.data, true);
            set(optimizing, false);
            if (get$1(optimizeResult) && get$1(optimizeResult).errors && get$1(optimizeResult).errors.length > 0) {
              $$props.onMessage(`Completed with ${get$1(optimizeResult).errors.length} error(s)`, "error");
            } else {
              $$props.onMessage("Optimization complete!", "success");
            }
            loadAnalysis();
            if (unsub) unsub();
          }
        },
        {
          type: "homeclaw/rag/optimize/run",
          provider: get$1(optimizeProvider),
          model: get$1(optimizeModel),
          scope: get$1(optimizeScope),
          force: get$1(optimizeForce)
        }
      );
    } catch (e2) {
      console.error("[RagViewer] Optimization error:", e2);
      $$props.onMessage(e2?.message || "Optimization failed", "error");
      set(optimizing, false);
      loadAnalysis();
    }
  }
  function getAvailableProviders() {
    return get(providerState).availableProviders || [];
  }
  var div = root$3();
  var node = sibling(child(div), 2);
  {
    var consequent = ($$anchor2) => {
      var div_1 = root_1$3();
      append($$anchor2, div_1);
    };
    var alternate_5 = ($$anchor2) => {
      var fragment = comment();
      var node_1 = first_child(fragment);
      {
        var consequent_13 = ($$anchor3) => {
          var fragment_1 = root_3();
          var div_2 = first_child(fragment_1);
          var div_3 = sibling(child(div_2), 2);
          var span = sibling(child(div_3));
          var text2 = child(span);
          var span_1 = sibling(span, 3);
          var text_1 = child(span_1);
          var span_2 = sibling(span_1, 3);
          var text_2 = child(span_2);
          var span_3 = sibling(span_2, 3);
          var text_3 = child(span_3);
          var span_4 = sibling(span_3, 3);
          var text_4 = child(span_4);
          var node_2 = sibling(div_2, 2);
          {
            var consequent_6 = ($$anchor4) => {
              var fragment_2 = root_4$2();
              var div_4 = first_child(fragment_2);
              var div_5 = sibling(child(div_4), 2);
              var node_3 = child(div_5);
              {
                var consequent_1 = ($$anchor5) => {
                  var fragment_3 = root_5();
                  var span_5 = sibling(first_child(fragment_3), 2);
                  var text_5 = child(span_5);
                  template_effect(($0) => set_text(text_5, `~${get$1(analysis).potential_chunk_savings ?? ""} chunks (${$0 ?? ""}%)`), [
                    () => Math.round(get$1(analysis).potential_chunk_savings / get$1(analysis).total_session_chunks * 100)
                  ]);
                  append($$anchor5, fragment_3);
                };
                if_block(node_3, ($$render) => {
                  if (get$1(analysis).potential_chunk_savings > 0) $$render(consequent_1);
                });
              }
              var node_4 = sibling(node_3, 2);
              {
                var consequent_2 = ($$anchor5) => {
                  var fragment_4 = root_6$1();
                  var span_6 = sibling(first_child(fragment_4), 2);
                  var text_6 = child(span_6);
                  template_effect(($0) => set_text(text_6, `~${get$1(analysis).potential_memory_savings ?? ""} memories (${$0 ?? ""}%)`), [
                    () => Math.round(get$1(analysis).potential_memory_savings / get$1(analysis).total_memories * 100)
                  ]);
                  append($$anchor5, fragment_4);
                };
                if_block(node_4, ($$render) => {
                  if (get$1(analysis).potential_memory_savings > 0) $$render(consequent_2);
                });
              }
              var div_6 = sibling(div_4, 2);
              var div_7 = sibling(child(div_6), 2);
              var div_8 = child(div_7);
              var select = sibling(child(div_8), 2);
              select.__change = handleProviderChange;
              var option = child(select);
              option.value = option.__value = "";
              var node_5 = sibling(option);
              each(node_5, 17, getAvailableProviders, index, ($$anchor5, provider) => {
                var option_1 = root_7$1();
                var text_7 = child(option_1);
                var option_1_value = {};
                template_effect(() => {
                  set_text(text_7, get$1(provider).label);
                  if (option_1_value !== (option_1_value = get$1(provider).value)) {
                    option_1.value = (option_1.__value = get$1(provider).value) ?? "";
                  }
                });
                append($$anchor5, option_1);
              });
              var div_9 = sibling(div_8, 2);
              var select_1 = sibling(child(div_9), 2);
              select_1.__change = handleModelChange;
              var node_6 = child(select_1);
              {
                var consequent_3 = ($$anchor5) => {
                  var option_2 = root_8$1();
                  option_2.value = option_2.__value = "";
                  append($$anchor5, option_2);
                };
                var alternate_1 = ($$anchor5) => {
                  var fragment_5 = comment();
                  var node_7 = first_child(fragment_5);
                  {
                    var consequent_4 = ($$anchor6) => {
                      var option_3 = root_10$1();
                      option_3.value = option_3.__value = "";
                      append($$anchor6, option_3);
                    };
                    var alternate = ($$anchor6) => {
                      var fragment_6 = comment();
                      var node_8 = first_child(fragment_6);
                      each(node_8, 17, () => get$1(optimizeModels), index, ($$anchor7, model) => {
                        var option_4 = root_12$1();
                        var text_8 = child(option_4);
                        var option_4_value = {};
                        template_effect(() => {
                          set_text(text_8, get$1(model).name);
                          if (option_4_value !== (option_4_value = get$1(model).id)) {
                            option_4.value = (option_4.__value = get$1(model).id) ?? "";
                          }
                        });
                        append($$anchor7, option_4);
                      });
                      append($$anchor6, fragment_6);
                    };
                    if_block(
                      node_7,
                      ($$render) => {
                        if (get$1(optimizeModels).length === 0) $$render(consequent_4);
                        else $$render(alternate, false);
                      },
                      true
                    );
                  }
                  append($$anchor5, fragment_5);
                };
                if_block(node_6, ($$render) => {
                  if (get$1(optimizeModelsLoading)) $$render(consequent_3);
                  else $$render(alternate_1, false);
                });
              }
              var div_10 = sibling(div_9, 2);
              var select_2 = sibling(child(div_10), 2);
              var option_5 = child(select_2);
              option_5.value = option_5.__value = "all";
              var option_6 = sibling(option_5);
              option_6.value = option_6.__value = "sessions";
              var option_7 = sibling(option_6);
              option_7.value = option_7.__value = "memories";
              var div_11 = sibling(div_10, 2);
              var label = child(div_11);
              var input = child(label);
              var button = sibling(div_6, 2);
              button.__click = runOptimization;
              var node_9 = child(button);
              {
                var consequent_5 = ($$anchor5) => {
                  var text_9 = text$1("Optimizing...");
                  append($$anchor5, text_9);
                };
                var alternate_2 = ($$anchor5) => {
                  var text_10 = text$1("Run Optimization");
                  append($$anchor5, text_10);
                };
                if_block(node_9, ($$render) => {
                  if (get$1(optimizing)) $$render(consequent_5);
                  else $$render(alternate_2, false);
                });
              }
              template_effect(() => {
                select_1.disabled = !get$1(optimizeProvider) || get$1(optimizeModelsLoading);
                button.disabled = get$1(optimizing) || !get$1(optimizeProvider) || !get$1(optimizeModel);
              });
              bind_select_value(select, () => get$1(optimizeProvider), ($$value) => set(optimizeProvider, $$value));
              bind_select_value(select_1, () => get$1(optimizeModel), ($$value) => set(optimizeModel, $$value));
              bind_select_value(select_2, () => get$1(optimizeScope), ($$value) => set(optimizeScope, $$value));
              bind_checked(input, () => get$1(optimizeForce), ($$value) => set(optimizeForce, $$value));
              append($$anchor4, fragment_2);
            };
            var alternate_3 = ($$anchor4) => {
              var div_12 = root_15();
              append($$anchor4, div_12);
            };
            if_block(node_2, ($$render) => {
              if (get$1(analysis).potential_chunk_savings > 0 || get$1(analysis).potential_memory_savings > 0) $$render(consequent_6);
              else $$render(alternate_3, false);
            });
          }
          var node_10 = sibling(node_2, 2);
          {
            var consequent_8 = ($$anchor4) => {
              var div_13 = root_16();
              var node_11 = sibling(child(div_13), 2);
              {
                var consequent_7 = ($$anchor5) => {
                  var div_14 = root_17$1();
                  var div_15 = child(div_14);
                  template_effect(() => set_style(div_15, `width: ${get$1(optimizeProgressPct) ?? ""}%`));
                  append($$anchor5, div_14);
                };
                if_block(node_11, ($$render) => {
                  if (get$1(optimizing)) $$render(consequent_7);
                });
              }
              var div_16 = sibling(node_11, 2);
              each(div_16, 21, () => get$1(optimizeProgress), index, ($$anchor5, event2) => {
                var div_17 = root_18$1();
                let classes;
                var text_11 = child(div_17);
                template_effect(() => {
                  classes = set_class(div_17, 1, "progress-line svelte-10ewjma", null, classes, {
                    phase: get$1(event2).type === "phase",
                    done: get$1(event2).type === "session_done" || get$1(event2).type === "category_done",
                    "error-line": get$1(event2).type === "session_error" || get$1(event2).type === "category_error",
                    complete: get$1(event2).type === "complete"
                  });
                  set_text(text_11, get$1(event2).message);
                });
                append($$anchor5, div_17);
              });
              append($$anchor4, div_13);
            };
            if_block(node_10, ($$render) => {
              if (get$1(optimizing) || get$1(optimizeProgress).length > 0) $$render(consequent_8);
            });
          }
          var node_12 = sibling(node_10, 2);
          {
            var consequent_12 = ($$anchor4) => {
              var div_18 = root_19$1();
              let classes_1;
              var div_19 = sibling(child(div_18), 2);
              var node_13 = child(div_19);
              {
                var consequent_9 = ($$anchor5) => {
                  var fragment_7 = root_20$1();
                  var span_7 = sibling(first_child(fragment_7), 2);
                  var text_12 = child(span_7);
                  var span_8 = sibling(text_12);
                  var text_13 = child(span_8);
                  template_effect(() => {
                    set_text(text_12, `${get$1(optimizeResult).chunks_before ?? ""} -> ${get$1(optimizeResult).chunks_after ?? ""} `);
                    set_text(text_13, `(-${get$1(optimizeResult).chunks_saved ?? ""})`);
                  });
                  append($$anchor5, fragment_7);
                };
                if_block(node_13, ($$render) => {
                  if (get$1(optimizeResult).chunks_before > 0) $$render(consequent_9);
                });
              }
              var node_14 = sibling(node_13, 2);
              {
                var consequent_10 = ($$anchor5) => {
                  var fragment_8 = root_21$1();
                  var span_9 = sibling(first_child(fragment_8), 2);
                  var text_14 = child(span_9);
                  var span_10 = sibling(text_14);
                  var text_15 = child(span_10);
                  template_effect(() => {
                    set_text(text_14, `${get$1(optimizeResult).memories_before ?? ""} -> ${get$1(optimizeResult).memories_after ?? ""} `);
                    set_text(text_15, `(-${get$1(optimizeResult).memories_saved ?? ""})`);
                  });
                  append($$anchor5, fragment_8);
                };
                if_block(node_14, ($$render) => {
                  if (get$1(optimizeResult).memories_before > 0) $$render(consequent_10);
                });
              }
              var span_11 = sibling(node_14, 3);
              var text_16 = child(span_11);
              var span_12 = sibling(span_11, 3);
              var text_17 = child(span_12);
              var node_15 = sibling(div_19, 2);
              {
                var consequent_11 = ($$anchor5) => {
                  var div_20 = root_22$1();
                  var node_16 = sibling(child(div_20), 2);
                  each(node_16, 17, () => get$1(optimizeResult).errors, index, ($$anchor6, err) => {
                    var div_21 = root_23();
                    var text_18 = child(div_21);
                    template_effect(() => set_text(text_18, get$1(err)));
                    append($$anchor6, div_21);
                  });
                  append($$anchor5, div_20);
                };
                if_block(node_15, ($$render) => {
                  if (get$1(optimizeResult).errors.length > 0) $$render(consequent_11);
                });
              }
              template_effect(() => {
                classes_1 = set_class(div_18, 1, "card result-card svelte-10ewjma", null, classes_1, { "has-errors": get$1(optimizeResult).errors.length > 0 });
                set_text(text_16, `${get$1(optimizeResult).duration_seconds ?? ""}s`);
                set_text(text_17, get$1(optimizeResult).sessions_processed);
              });
              append($$anchor4, div_18);
            };
            if_block(node_12, ($$render) => {
              if (get$1(optimizeResult)) $$render(consequent_12);
            });
          }
          var button_1 = sibling(node_12, 2);
          button_1.__click = loadAnalysis;
          template_effect(() => {
            set_text(text2, get$1(analysis).total_session_chunks);
            set_text(text_1, get$1(analysis).total_sessions);
            set_text(text_2, get$1(analysis).optimizable_sessions);
            set_text(text_3, `${get$1(analysis).total_size_mb ?? ""} MB`);
            set_text(text_4, get$1(analysis).total_memories);
          });
          append($$anchor3, fragment_1);
        };
        var alternate_4 = ($$anchor3) => {
          var fragment_9 = comment();
          var node_17 = first_child(fragment_9);
          {
            var consequent_14 = ($$anchor4) => {
              var div_22 = root_25();
              append($$anchor4, div_22);
            };
            if_block(
              node_17,
              ($$render) => {
                if (get$1(analysis) && !get$1(analysis).initialized) $$render(consequent_14);
              },
              true
            );
          }
          append($$anchor3, fragment_9);
        };
        if_block(
          node_1,
          ($$render) => {
            if (get$1(analysis) && get$1(analysis).initialized) $$render(consequent_13);
            else $$render(alternate_4, false);
          },
          true
        );
      }
      append($$anchor2, fragment);
    };
    if_block(node, ($$render) => {
      if (get$1(analysisLoading)) $$render(consequent);
      else $$render(alternate_5, false);
    });
  }
  append($$anchor, div);
  pop();
}
delegate(["change", "click"]);
var root_1$2 = /* @__PURE__ */ from_html(`<div> </div>`);
var root_2$1 = /* @__PURE__ */ from_html(`<div class="loading svelte-1djclk2">Loading RAG data...</div>`);
var root_4$1 = /* @__PURE__ */ from_html(`<div class="not-initialized svelte-1djclk2">RAG system is not initialized. Enable it in the integration config.</div>`);
var root$2 = /* @__PURE__ */ from_html(`<div class="rag-viewer svelte-1djclk2"><!> <div class="section-nav svelte-1djclk2"><button>Overview</button> <button>Memories</button> <button>Sessions</button> <button>Search</button> <button>Optimize</button></div> <!></div>`);
function RagViewer($$anchor, $$props) {
  push($$props, true);
  let activeSection = /* @__PURE__ */ state("overview");
  let loading = /* @__PURE__ */ state(false);
  let stats = /* @__PURE__ */ state(null);
  let message = /* @__PURE__ */ state(null);
  let messageType = /* @__PURE__ */ state("success");
  user_effect(() => {
    loadStats();
  });
  async function loadStats() {
    const hass = getHass();
    if (!hass) return;
    set(loading, true);
    try {
      set(stats, await hass.callWS({ type: "homeclaw/rag/stats" }), true);
    } catch (e2) {
      console.error("[RagViewer] Failed to load stats:", e2);
      set(stats, { initialized: false }, true);
    } finally {
      set(loading, false);
    }
  }
  function showMessage(text2, type) {
    set(message, text2, true);
    set(messageType, type, true);
    setTimeout(() => set(message, null), 3e3);
  }
  function handleSectionChange(section) {
    set(activeSection, section, true);
  }
  var div = root$2();
  var node = child(div);
  {
    var consequent = ($$anchor2) => {
      var div_1 = root_1$2();
      let classes;
      var text_1 = child(div_1);
      template_effect(() => {
        classes = set_class(div_1, 1, "msg svelte-1djclk2", null, classes, { error: get$1(messageType) === "error" });
        set_text(text_1, get$1(message));
      });
      append($$anchor2, div_1);
    };
    if_block(node, ($$render) => {
      if (get$1(message)) $$render(consequent);
    });
  }
  var div_2 = sibling(node, 2);
  var button = child(div_2);
  let classes_1;
  button.__click = () => handleSectionChange("overview");
  var button_1 = sibling(button, 2);
  let classes_2;
  button_1.__click = () => handleSectionChange("memories");
  var button_2 = sibling(button_1, 2);
  let classes_3;
  button_2.__click = () => handleSectionChange("sessions");
  var button_3 = sibling(button_2, 2);
  let classes_4;
  button_3.__click = () => handleSectionChange("search");
  var button_4 = sibling(button_3, 2);
  let classes_5;
  button_4.__click = () => handleSectionChange("optimize");
  var node_1 = sibling(div_2, 2);
  {
    var consequent_1 = ($$anchor2) => {
      var div_3 = root_2$1();
      append($$anchor2, div_3);
    };
    var alternate_5 = ($$anchor2) => {
      var fragment = comment();
      var node_2 = first_child(fragment);
      {
        var consequent_2 = ($$anchor3) => {
          var div_4 = root_4$1();
          append($$anchor3, div_4);
        };
        var alternate_4 = ($$anchor3) => {
          var fragment_1 = comment();
          var node_3 = first_child(fragment_1);
          {
            var consequent_3 = ($$anchor4) => {
              RagOverview($$anchor4, {
                get stats() {
                  return get$1(stats);
                },
                onRefresh: loadStats,
                onMessage: showMessage
              });
            };
            var alternate_3 = ($$anchor4) => {
              var fragment_3 = comment();
              var node_4 = first_child(fragment_3);
              {
                var consequent_4 = ($$anchor5) => {
                  RagMemories($$anchor5, { onMessage: showMessage });
                };
                var alternate_2 = ($$anchor5) => {
                  var fragment_5 = comment();
                  var node_5 = first_child(fragment_5);
                  {
                    var consequent_5 = ($$anchor6) => {
                      RagSessions($$anchor6, {});
                    };
                    var alternate_1 = ($$anchor6) => {
                      var fragment_7 = comment();
                      var node_6 = first_child(fragment_7);
                      {
                        var consequent_6 = ($$anchor7) => {
                          RagSearch($$anchor7, {});
                        };
                        var alternate = ($$anchor7) => {
                          var fragment_9 = comment();
                          var node_7 = first_child(fragment_9);
                          {
                            var consequent_7 = ($$anchor8) => {
                              RagOptimize($$anchor8, { onMessage: showMessage });
                            };
                            if_block(
                              node_7,
                              ($$render) => {
                                if (get$1(activeSection) === "optimize") $$render(consequent_7);
                              },
                              true
                            );
                          }
                          append($$anchor7, fragment_9);
                        };
                        if_block(
                          node_6,
                          ($$render) => {
                            if (get$1(activeSection) === "search") $$render(consequent_6);
                            else $$render(alternate, false);
                          },
                          true
                        );
                      }
                      append($$anchor6, fragment_7);
                    };
                    if_block(
                      node_5,
                      ($$render) => {
                        if (get$1(activeSection) === "sessions") $$render(consequent_5);
                        else $$render(alternate_1, false);
                      },
                      true
                    );
                  }
                  append($$anchor5, fragment_5);
                };
                if_block(
                  node_4,
                  ($$render) => {
                    if (get$1(activeSection) === "memories") $$render(consequent_4);
                    else $$render(alternate_2, false);
                  },
                  true
                );
              }
              append($$anchor4, fragment_3);
            };
            if_block(
              node_3,
              ($$render) => {
                if (get$1(activeSection) === "overview" && get$1(stats)) $$render(consequent_3);
                else $$render(alternate_3, false);
              },
              true
            );
          }
          append($$anchor3, fragment_1);
        };
        if_block(
          node_2,
          ($$render) => {
            if (get$1(stats) && !get$1(stats).initialized) $$render(consequent_2);
            else $$render(alternate_4, false);
          },
          true
        );
      }
      append($$anchor2, fragment);
    };
    if_block(node_1, ($$render) => {
      if (get$1(loading) && !get$1(stats)) $$render(consequent_1);
      else $$render(alternate_5, false);
    });
  }
  template_effect(() => {
    classes_1 = set_class(button, 1, "pill svelte-1djclk2", null, classes_1, { active: get$1(activeSection) === "overview" });
    classes_2 = set_class(button_1, 1, "pill svelte-1djclk2", null, classes_2, { active: get$1(activeSection) === "memories" });
    classes_3 = set_class(button_2, 1, "pill svelte-1djclk2", null, classes_3, { active: get$1(activeSection) === "sessions" });
    classes_4 = set_class(button_3, 1, "pill svelte-1djclk2", null, classes_4, { active: get$1(activeSection) === "search" });
    classes_5 = set_class(button_4, 1, "pill optimize-pill svelte-1djclk2", null, classes_5, { active: get$1(activeSection) === "optimize" });
  });
  append($$anchor, div);
  pop();
}
delegate(["click"]);
var root_1$1 = /* @__PURE__ */ from_html(`<div> </div>`);
var root_2 = /* @__PURE__ */ from_html(`<div class="loading svelte-7zsr1v">Loading scheduler...</div>`);
var root_4 = /* @__PURE__ */ from_html(`<div class="not-available svelte-7zsr1v">Scheduler is not initialized. It starts automatically with the integration.</div>`);
var root_7 = /* @__PURE__ */ from_html(`<div class="status-bar svelte-7zsr1v"><span> </span> <span class="dot svelte-7zsr1v">&#183;</span> <span> </span> <span class="dot svelte-7zsr1v">&#183;</span> <span> </span></div>`);
var root_8 = /* @__PURE__ */ from_html(`<div class="empty svelte-7zsr1v">No scheduled jobs yet. Ask the assistant to create one, e.g. <em class="svelte-7zsr1v">"Remind me to check energy at 8pm every day"</em></div>`);
var root_11 = /* @__PURE__ */ from_html(`<span class="badge one-shot svelte-7zsr1v">once</span>`);
var root_12 = /* @__PURE__ */ from_html(`<span class="next-run svelte-7zsr1v"> </span>`);
var root_14 = /* @__PURE__ */ from_html(`<span class="last-error svelte-7zsr1v">failed</span>`);
var root_13 = /* @__PURE__ */ from_html(`<div class="job-last-run svelte-7zsr1v"><span></span> <!></div>`);
var root_10 = /* @__PURE__ */ from_html(`<div><div class="job-header svelte-7zsr1v"><div class="job-title-row svelte-7zsr1v"><span class="job-name svelte-7zsr1v"> </span> <!> <span> </span></div> <label class="toggle svelte-7zsr1v"><input type="checkbox" class="svelte-7zsr1v"/> <span class="slider svelte-7zsr1v"></span></label></div> <div class="job-meta svelte-7zsr1v"><span class="cron svelte-7zsr1v"> </span> <!></div> <div class="job-prompt svelte-7zsr1v"> </div> <!> <div class="job-actions svelte-7zsr1v"><button class="action-btn run svelte-7zsr1v"> </button> <button class="action-btn delete svelte-7zsr1v">Remove</button></div></div>`);
var root_9 = /* @__PURE__ */ from_html(`<div class="jobs-list svelte-7zsr1v"></div>`);
var root_6 = /* @__PURE__ */ from_html(`<!> <!>`, 1);
var root_17 = /* @__PURE__ */ from_html(`<div class="empty svelte-7zsr1v">No run history yet.</div>`);
var root_20 = /* @__PURE__ */ from_html(`<span class="history-duration svelte-7zsr1v"> </span>`);
var root_21 = /* @__PURE__ */ from_html(`<div class="history-error svelte-7zsr1v"> </div>`);
var root_22 = /* @__PURE__ */ from_html(`<div class="history-response svelte-7zsr1v"> </div>`);
var root_19 = /* @__PURE__ */ from_html(`<div><div class="history-header svelte-7zsr1v"><span class="history-name svelte-7zsr1v"> </span> <span class="history-time svelte-7zsr1v"> </span></div> <div class="history-detail svelte-7zsr1v"><span></span> <span class="history-status svelte-7zsr1v"> </span> <!></div> <!> <!></div>`);
var root_18 = /* @__PURE__ */ from_html(`<div class="history-list svelte-7zsr1v"></div>`);
var root$1 = /* @__PURE__ */ from_html(`<div class="scheduler-panel svelte-7zsr1v"><!> <div class="section-nav svelte-7zsr1v"><button>Jobs</button> <button>History</button> <button class="pill refresh-pill svelte-7zsr1v" title="Refresh">Refresh</button></div> <!></div>`);
function SchedulerPanel($$anchor, $$props) {
  push($$props, true);
  let jobs = /* @__PURE__ */ state(proxy([]));
  let status = /* @__PURE__ */ state(null);
  let history = /* @__PURE__ */ state(proxy([]));
  let loading = /* @__PURE__ */ state(false);
  let available = /* @__PURE__ */ state(true);
  let runningJobId = /* @__PURE__ */ state(null);
  let message = /* @__PURE__ */ state(null);
  let messageType = /* @__PURE__ */ state("success");
  let activeSection = /* @__PURE__ */ state("jobs");
  user_effect(() => {
    loadJobs();
  });
  function showMessage(text2, type) {
    set(message, text2, true);
    set(messageType, type, true);
    setTimeout(() => set(message, null), 3e3);
  }
  async function loadJobs() {
    const hass = getHass();
    if (!hass) return;
    set(loading, true);
    try {
      const result = await hass.callWS({ type: "homeclaw/scheduler/list" });
      set(available, result.available !== false);
      set(jobs, result.jobs || [], true);
      set(status, result.status || null, true);
    } catch (e2) {
      console.error("[Scheduler] Failed to load:", e2);
      set(available, false);
    } finally {
      set(loading, false);
    }
  }
  async function loadHistory() {
    const hass = getHass();
    if (!hass) return;
    try {
      const result = await hass.callWS({ type: "homeclaw/scheduler/history", limit: 50 });
      set(history, (result.history || []).reverse(), true);
    } catch (e2) {
      console.error("[Scheduler] Failed to load history:", e2);
    }
  }
  async function toggleJob(jobId, enabled) {
    const hass = getHass();
    if (!hass) return;
    try {
      await hass.callWS({ type: "homeclaw/scheduler/enable", job_id: jobId, enabled });
      showMessage(enabled ? "Job enabled" : "Job disabled", "success");
      await loadJobs();
    } catch (e2) {
      showMessage(e2.message || "Failed to toggle job", "error");
      await loadJobs();
    }
  }
  async function removeJob(jobId, jobName) {
    if (!confirm(`Remove "${jobName}"?`)) return;
    const hass = getHass();
    if (!hass) return;
    try {
      await hass.callWS({ type: "homeclaw/scheduler/remove", job_id: jobId });
      showMessage("Job removed", "success");
      await loadJobs();
    } catch (e2) {
      showMessage(e2.message || "Failed to remove job", "error");
    }
  }
  async function runJobNow(jobId) {
    const hass = getHass();
    if (!hass) return;
    set(runningJobId, jobId, true);
    try {
      const result = await hass.callWS({ type: "homeclaw/scheduler/run", job_id: jobId });
      const run2 = result.run;
      if (run2?.status === "ok") {
        showMessage("Job executed successfully", "success");
      } else {
        showMessage(run2?.error || "Job failed", "error");
      }
      await loadJobs();
    } catch (e2) {
      showMessage(e2.message || "Failed to run job", "error");
    } finally {
      set(runningJobId, null);
    }
  }
  function handleSectionChange(section) {
    set(activeSection, section, true);
    if (section === "history") {
      loadHistory();
    }
  }
  function formatDate(isoOrTimestamp) {
    if (!isoOrTimestamp) return "-";
    const d2 = typeof isoOrTimestamp === "number" ? new Date(isoOrTimestamp * 1e3) : new Date(isoOrTimestamp);
    if (isNaN(d2.getTime())) return "-";
    const now = /* @__PURE__ */ new Date();
    const isToday = d2.toDateString() === now.toDateString();
    const time = d2.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (isToday) return time;
    const day = d2.getDate();
    const month = d2.toLocaleString("default", { month: "short" });
    return `${day} ${month}, ${time}`;
  }
  function describeCron(cron) {
    const parts = cron.split(" ");
    if (parts.length !== 5) return cron;
    const [min, hour, dom, mon, dow] = parts;
    if (dom !== "*" && mon !== "*") {
      return `${hour}:${min.padStart(2, "0")} on ${dom}/${mon}`;
    }
    if (min.startsWith("*/")) return `Every ${min.slice(2)} min`;
    if (hour.startsWith("*/") && min === "0") return `Every ${hour.slice(2)}h`;
    if (dom === "*" && mon === "*" && dow === "*") {
      return `Daily at ${hour}:${min.padStart(2, "0")}`;
    }
    const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    if (dow !== "*" && dom === "*") {
      const dayName = dayNames[parseInt(dow)] || dow;
      return `${dayName} at ${hour}:${min.padStart(2, "0")}`;
    }
    if (dom !== "*" && mon === "*") {
      return `${dom}th of month at ${hour}:${min.padStart(2, "0")}`;
    }
    return cron;
  }
  var div = root$1();
  var node = child(div);
  {
    var consequent = ($$anchor2) => {
      var div_1 = root_1$1();
      let classes;
      var text_1 = child(div_1);
      template_effect(() => {
        classes = set_class(div_1, 1, "msg svelte-7zsr1v", null, classes, { error: get$1(messageType) === "error" });
        set_text(text_1, get$1(message));
      });
      append($$anchor2, div_1);
    };
    if_block(node, ($$render) => {
      if (get$1(message)) $$render(consequent);
    });
  }
  var div_2 = sibling(node, 2);
  var button = child(div_2);
  let classes_1;
  button.__click = () => handleSectionChange("jobs");
  var button_1 = sibling(button, 2);
  let classes_2;
  button_1.__click = () => handleSectionChange("history");
  var button_2 = sibling(button_1, 2);
  button_2.__click = loadJobs;
  var node_1 = sibling(div_2, 2);
  {
    var consequent_1 = ($$anchor2) => {
      var div_3 = root_2();
      append($$anchor2, div_3);
    };
    var alternate_4 = ($$anchor2) => {
      var fragment = comment();
      var node_2 = first_child(fragment);
      {
        var consequent_2 = ($$anchor3) => {
          var div_4 = root_4();
          append($$anchor3, div_4);
        };
        var alternate_3 = ($$anchor3) => {
          var fragment_1 = comment();
          var node_3 = first_child(fragment_1);
          {
            var consequent_9 = ($$anchor4) => {
              var fragment_2 = root_6();
              var node_4 = first_child(fragment_2);
              {
                var consequent_3 = ($$anchor5) => {
                  var div_5 = root_7();
                  var span = child(div_5);
                  var text_2 = child(span);
                  var span_1 = sibling(span, 4);
                  var text_3 = child(span_1);
                  var span_2 = sibling(span_1, 4);
                  var text_4 = child(span_2);
                  template_effect(() => {
                    set_text(text_2, `${get$1(status).total_jobs ?? ""} jobs`);
                    set_text(text_3, `${get$1(status).enabled_jobs ?? ""} enabled`);
                    set_text(text_4, `${get$1(status).active_timers ?? ""} timers`);
                  });
                  append($$anchor5, div_5);
                };
                if_block(node_4, ($$render) => {
                  if (get$1(status)) $$render(consequent_3);
                });
              }
              var node_5 = sibling(node_4, 2);
              {
                var consequent_4 = ($$anchor5) => {
                  var div_6 = root_8();
                  append($$anchor5, div_6);
                };
                var alternate = ($$anchor5) => {
                  var div_7 = root_9();
                  each(div_7, 21, () => get$1(jobs), (job) => job.job_id, ($$anchor6, job) => {
                    var div_8 = root_10();
                    let classes_3;
                    var div_9 = child(div_8);
                    var div_10 = child(div_9);
                    var span_3 = child(div_10);
                    var text_5 = child(span_3);
                    var node_6 = sibling(span_3, 2);
                    {
                      var consequent_5 = ($$anchor7) => {
                        var span_4 = root_11();
                        append($$anchor7, span_4);
                      };
                      if_block(node_6, ($$render) => {
                        if (get$1(job).one_shot) $$render(consequent_5);
                      });
                    }
                    var span_5 = sibling(node_6, 2);
                    let classes_4;
                    var text_6 = child(span_5);
                    var label = sibling(div_10, 2);
                    var input = child(label);
                    input.__change = () => toggleJob(get$1(job).job_id, !get$1(job).enabled);
                    var div_11 = sibling(div_9, 2);
                    var span_6 = child(div_11);
                    var text_7 = child(span_6);
                    var node_7 = sibling(span_6, 2);
                    {
                      var consequent_6 = ($$anchor7) => {
                        var span_7 = root_12();
                        var text_8 = child(span_7);
                        template_effect(($0) => set_text(text_8, `Next: ${$0 ?? ""}`), [() => formatDate(get$1(job).next_run)]);
                        append($$anchor7, span_7);
                      };
                      if_block(node_7, ($$render) => {
                        if (get$1(job).next_run && get$1(job).enabled) $$render(consequent_6);
                      });
                    }
                    var div_12 = sibling(div_11, 2);
                    var text_9 = child(div_12);
                    var node_8 = sibling(div_12, 2);
                    {
                      var consequent_8 = ($$anchor7) => {
                        var div_13 = root_13();
                        var span_8 = child(div_13);
                        let classes_5;
                        var text_10 = sibling(span_8);
                        var node_9 = sibling(text_10);
                        {
                          var consequent_7 = ($$anchor8) => {
                            var span_9 = root_14();
                            template_effect(() => set_attribute(span_9, "title", get$1(job).last_error));
                            append($$anchor8, span_9);
                          };
                          if_block(node_9, ($$render) => {
                            if (get$1(job).last_error) $$render(consequent_7);
                          });
                        }
                        template_effect(
                          ($0) => {
                            classes_5 = set_class(span_8, 1, "status-dot svelte-7zsr1v", null, classes_5, {
                              ok: get$1(job).last_status === "ok",
                              error: get$1(job).last_status === "error"
                            });
                            set_text(text_10, ` Last: ${$0 ?? ""} `);
                          },
                          [() => formatDate(get$1(job).last_run)]
                        );
                        append($$anchor7, div_13);
                      };
                      if_block(node_8, ($$render) => {
                        if (get$1(job).last_run) $$render(consequent_8);
                      });
                    }
                    var div_14 = sibling(node_8, 2);
                    var button_3 = child(div_14);
                    button_3.__click = () => runJobNow(get$1(job).job_id);
                    var text_11 = child(button_3);
                    var button_4 = sibling(button_3, 2);
                    button_4.__click = () => removeJob(get$1(job).job_id, get$1(job).name);
                    template_effect(
                      ($0) => {
                        classes_3 = set_class(div_8, 1, "job-card svelte-7zsr1v", null, classes_3, { disabled: !get$1(job).enabled });
                        set_text(text_5, get$1(job).name);
                        classes_4 = set_class(span_5, 1, "badge svelte-7zsr1v", null, classes_4, { agent: get$1(job).created_by === "agent" });
                        set_text(text_6, get$1(job).created_by);
                        set_checked(input, get$1(job).enabled);
                        set_attribute(span_6, "title", get$1(job).cron);
                        set_text(text_7, $0);
                        set_text(text_9, get$1(job).prompt);
                        button_3.disabled = get$1(runningJobId) === get$1(job).job_id;
                        set_text(text_11, get$1(runningJobId) === get$1(job).job_id ? "Running..." : "Run now");
                      },
                      [() => describeCron(get$1(job).cron)]
                    );
                    append($$anchor6, div_8);
                  });
                  append($$anchor5, div_7);
                };
                if_block(node_5, ($$render) => {
                  if (get$1(jobs).length === 0) $$render(consequent_4);
                  else $$render(alternate, false);
                });
              }
              append($$anchor4, fragment_2);
            };
            var alternate_2 = ($$anchor4) => {
              var fragment_3 = comment();
              var node_10 = first_child(fragment_3);
              {
                var consequent_14 = ($$anchor5) => {
                  var fragment_4 = comment();
                  var node_11 = first_child(fragment_4);
                  {
                    var consequent_10 = ($$anchor6) => {
                      var div_15 = root_17();
                      append($$anchor6, div_15);
                    };
                    var alternate_1 = ($$anchor6) => {
                      var div_16 = root_18();
                      each(div_16, 21, () => get$1(history), index, ($$anchor7, run2) => {
                        var div_17 = root_19();
                        let classes_6;
                        var div_18 = child(div_17);
                        var span_10 = child(div_18);
                        var text_12 = child(span_10);
                        var span_11 = sibling(span_10, 2);
                        var text_13 = child(span_11);
                        var div_19 = sibling(div_18, 2);
                        var span_12 = child(div_19);
                        let classes_7;
                        var span_13 = sibling(span_12, 2);
                        var text_14 = child(span_13);
                        var node_12 = sibling(span_13, 2);
                        {
                          var consequent_11 = ($$anchor8) => {
                            var span_14 = root_20();
                            var text_15 = child(span_14);
                            template_effect(($0) => set_text(text_15, `${$0 ?? ""}s`), [() => (get$1(run2).duration_ms / 1e3).toFixed(1)]);
                            append($$anchor8, span_14);
                          };
                          if_block(node_12, ($$render) => {
                            if (get$1(run2).duration_ms) $$render(consequent_11);
                          });
                        }
                        var node_13 = sibling(div_19, 2);
                        {
                          var consequent_12 = ($$anchor8) => {
                            var div_20 = root_21();
                            var text_16 = child(div_20);
                            template_effect(() => set_text(text_16, get$1(run2).error));
                            append($$anchor8, div_20);
                          };
                          if_block(node_13, ($$render) => {
                            if (get$1(run2).error) $$render(consequent_12);
                          });
                        }
                        var node_14 = sibling(node_13, 2);
                        {
                          var consequent_13 = ($$anchor8) => {
                            var div_21 = root_22();
                            var text_17 = child(div_21);
                            template_effect(($0) => set_text(text_17, $0), [() => get$1(run2).response.slice(0, 200)]);
                            append($$anchor8, div_21);
                          };
                          if_block(node_14, ($$render) => {
                            if (get$1(run2).response) $$render(consequent_13);
                          });
                        }
                        template_effect(
                          ($0) => {
                            classes_6 = set_class(div_17, 1, "history-item svelte-7zsr1v", null, classes_6, { error: get$1(run2).status === "error" });
                            set_text(text_12, get$1(run2).job_name);
                            set_text(text_13, $0);
                            classes_7 = set_class(span_12, 1, "status-dot svelte-7zsr1v", null, classes_7, {
                              ok: get$1(run2).status === "ok",
                              error: get$1(run2).status === "error"
                            });
                            set_text(text_14, get$1(run2).status);
                          },
                          [() => formatDate(get$1(run2).timestamp)]
                        );
                        append($$anchor7, div_17);
                      });
                      append($$anchor6, div_16);
                    };
                    if_block(node_11, ($$render) => {
                      if (get$1(history).length === 0) $$render(consequent_10);
                      else $$render(alternate_1, false);
                    });
                  }
                  append($$anchor5, fragment_4);
                };
                if_block(
                  node_10,
                  ($$render) => {
                    if (get$1(activeSection) === "history") $$render(consequent_14);
                  },
                  true
                );
              }
              append($$anchor4, fragment_3);
            };
            if_block(
              node_3,
              ($$render) => {
                if (get$1(activeSection) === "jobs") $$render(consequent_9);
                else $$render(alternate_2, false);
              },
              true
            );
          }
          append($$anchor3, fragment_1);
        };
        if_block(
          node_2,
          ($$render) => {
            if (!get$1(available)) $$render(consequent_2);
            else $$render(alternate_3, false);
          },
          true
        );
      }
      append($$anchor2, fragment);
    };
    if_block(node_1, ($$render) => {
      if (get$1(loading) && !get$1(jobs).length) $$render(consequent_1);
      else $$render(alternate_4, false);
    });
  }
  template_effect(() => {
    classes_1 = set_class(button, 1, "pill svelte-7zsr1v", null, classes_1, { active: get$1(activeSection) === "jobs" });
    classes_2 = set_class(button_1, 1, "pill svelte-7zsr1v", null, classes_2, { active: get$1(activeSection) === "history" });
  });
  append($$anchor, div);
  pop();
}
delegate(["click", "change"]);
var root_1 = /* @__PURE__ */ from_html(`<div class="settings-backdrop svelte-nsapwt"></div> <div class="settings-panel svelte-nsapwt"><div class="settings-header svelte-nsapwt"><h2 class="svelte-nsapwt">Settings</h2> <button class="close-btn svelte-nsapwt" aria-label="Close settings"><svg viewBox="0 0 24 24" class="icon svelte-nsapwt"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"></path></svg></button></div> <div class="tabs svelte-nsapwt"><button>Defaults</button> <button>Models</button> <button>RAG</button> <button>Scheduler</button></div> <div class="settings-content svelte-nsapwt"><!></div></div>`, 1);
function SettingsPanel($$anchor, $$props) {
  push($$props, true);
  const $uiState = () => store_get(uiState, "$uiState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  let activeTab = /* @__PURE__ */ state("defaults");
  var fragment = comment();
  var node = first_child(fragment);
  {
    var consequent_4 = ($$anchor2) => {
      var fragment_1 = root_1();
      var div = first_child(fragment_1);
      div.__click = function(...$$args) {
        closeSettings?.apply(this, $$args);
      };
      var div_1 = sibling(div, 2);
      var div_2 = child(div_1);
      var button = sibling(child(div_2), 2);
      button.__click = function(...$$args) {
        closeSettings?.apply(this, $$args);
      };
      var div_3 = sibling(div_2, 2);
      var button_1 = child(div_3);
      let classes;
      button_1.__click = () => set(activeTab, "defaults");
      var button_2 = sibling(button_1, 2);
      let classes_1;
      button_2.__click = () => set(activeTab, "models");
      var button_3 = sibling(button_2, 2);
      let classes_2;
      button_3.__click = () => set(activeTab, "rag");
      var button_4 = sibling(button_3, 2);
      let classes_3;
      button_4.__click = () => set(activeTab, "scheduler");
      var div_4 = sibling(div_3, 2);
      var node_1 = child(div_4);
      {
        var consequent = ($$anchor3) => {
          DefaultsEditor($$anchor3, {});
        };
        var alternate_2 = ($$anchor3) => {
          var fragment_3 = comment();
          var node_2 = first_child(fragment_3);
          {
            var consequent_1 = ($$anchor4) => {
              ModelsEditor($$anchor4, {});
            };
            var alternate_1 = ($$anchor4) => {
              var fragment_5 = comment();
              var node_3 = first_child(fragment_5);
              {
                var consequent_2 = ($$anchor5) => {
                  RagViewer($$anchor5, {});
                };
                var alternate = ($$anchor5) => {
                  var fragment_7 = comment();
                  var node_4 = first_child(fragment_7);
                  {
                    var consequent_3 = ($$anchor6) => {
                      SchedulerPanel($$anchor6, {});
                    };
                    if_block(
                      node_4,
                      ($$render) => {
                        if (get$1(activeTab) === "scheduler") $$render(consequent_3);
                      },
                      true
                    );
                  }
                  append($$anchor5, fragment_7);
                };
                if_block(
                  node_3,
                  ($$render) => {
                    if (get$1(activeTab) === "rag") $$render(consequent_2);
                    else $$render(alternate, false);
                  },
                  true
                );
              }
              append($$anchor4, fragment_5);
            };
            if_block(
              node_2,
              ($$render) => {
                if (get$1(activeTab) === "models") $$render(consequent_1);
                else $$render(alternate_1, false);
              },
              true
            );
          }
          append($$anchor3, fragment_3);
        };
        if_block(node_1, ($$render) => {
          if (get$1(activeTab) === "defaults") $$render(consequent);
          else $$render(alternate_2, false);
        });
      }
      template_effect(() => {
        classes = set_class(button_1, 1, "tab svelte-nsapwt", null, classes, { active: get$1(activeTab) === "defaults" });
        classes_1 = set_class(button_2, 1, "tab svelte-nsapwt", null, classes_1, { active: get$1(activeTab) === "models" });
        classes_2 = set_class(button_3, 1, "tab svelte-nsapwt", null, classes_2, { active: get$1(activeTab) === "rag" });
        classes_3 = set_class(button_4, 1, "tab svelte-nsapwt", null, classes_3, { active: get$1(activeTab) === "scheduler" });
      });
      append($$anchor2, fragment_1);
    };
    if_block(node, ($$render) => {
      if ($uiState().settingsOpen) $$render(consequent_4);
    });
  }
  append($$anchor, fragment);
  pop();
  $$cleanup();
}
delegate(["click"]);
var root = /* @__PURE__ */ from_html(`<div><!> <div class="main-container svelte-j6syiu"><!> <div class="content-area svelte-j6syiu"><div class="chat-container svelte-j6syiu"><!> <!></div> <!></div></div> <!></div>`);
function HomeclawPanel$1($$anchor, $$props) {
  push($$props, true);
  const $appState = () => store_get(appState, "$appState", $$stores);
  const [$$stores, $$cleanup] = setup_stores();
  let narrow = prop($$props, "narrow", 3, false);
  async function loadIdentity(ha) {
    try {
      const result = await ha.callWS({ type: "homeclaw/rag/identity" });
      const identity = result?.identity;
      if (identity) {
        appState.update((s2) => ({
          ...s2,
          agentName: identity.agent_name || "Homeclaw",
          agentEmoji: identity.agent_emoji || ""
        }));
      }
    } catch {
    }
  }
  user_effect(() => {
    appState.update((s2) => ({ ...s2, hass: $$props.hass }));
  });
  onMount(() => {
    console.log("[HomeclawPanel] Mounting...");
    (async () => {
      try {
        await Promise.all([
          loadProviders($$props.hass),
          loadSessions($$props.hass),
          loadIdentity($$props.hass),
          syncThemeFromPreferences($$props.hass)
        ]);
        console.log("[HomeclawPanel] Initialization complete");
      } catch (error) {
        console.error("[HomeclawPanel] Initialization error:", error);
        appState.update((s2) => ({
          ...s2,
          error: error instanceof Error ? error.message : "Failed to initialize"
        }));
      }
    })();
    const handleResize = () => {
      const isMobile3 = window.innerWidth <= 768;
      const currentUiState = get(uiState);
      if (!isMobile3 && currentUiState.sidebarOpen) ;
    };
    window.addEventListener("resize", handleResize);
    handleResize();
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  });
  const isMobile2 = /* @__PURE__ */ user_derived(() => narrow() || window.innerWidth <= 768);
  const showThinkingPanel = /* @__PURE__ */ user_derived(() => $appState().showThinking && $appState().debugInfo?.length > 0);
  var div = root();
  let classes;
  var node = child(div);
  Header(node, {});
  var div_1 = sibling(node, 2);
  var node_1 = child(div_1);
  Sidebar(node_1, {});
  var div_2 = sibling(node_1, 2);
  var div_3 = child(div_2);
  var node_2 = child(div_3);
  ChatArea(node_2, {});
  var node_3 = sibling(node_2, 2);
  {
    var consequent = ($$anchor2) => {
      ThinkingPanel($$anchor2, {});
    };
    if_block(node_3, ($$render) => {
      if (get$1(showThinkingPanel)) $$render(consequent);
    });
  }
  var node_4 = sibling(div_3, 2);
  InputArea(node_4, {});
  var node_5 = sibling(div_1, 2);
  SettingsPanel(node_5, {});
  template_effect(() => classes = set_class(div, 1, "homeclaw-panel svelte-j6syiu", null, classes, { narrow: get$1(isMobile2) }));
  append($$anchor, div);
  pop();
  $$cleanup();
}
console.log("[HomeclawPanel] Bundle loaded and executing...");
console.log("[HomeclawPanel] Imports completed successfully");
console.log("[HomeclawPanel] App CSS length:", appCss?.length || 0);
console.log("[HomeclawPanel] Component CSS length:", componentCss?.length || 0);
console.log("[HomeclawPanel] HomeclawApp component:", typeof HomeclawPanel$1);
class HomeclawPanel extends HTMLElement {
  _hass;
  _narrow = false;
  _panel = true;
  // shadowRoot is inherited from HTMLElement, don't redeclare
  svelteApp;
  mountPoint;
  constructor() {
    super();
    console.log("[HomeclawPanel] Constructor called");
    try {
      const shadowRoot = this.attachShadow({ mode: "open" });
      console.log("[HomeclawPanel] Shadow DOM attached");
      setHostElement(this);
      const appStyle = document.createElement("style");
      appStyle.textContent = appCss;
      shadowRoot.appendChild(appStyle);
      console.log("[HomeclawPanel] App CSS injected");
      const componentStyle = document.createElement("style");
      componentStyle.textContent = componentCss;
      shadowRoot.appendChild(componentStyle);
      console.log("[HomeclawPanel] Component CSS injected");
      this.mountPoint = document.createElement("div");
      this.mountPoint.id = "svelte-app";
      shadowRoot.appendChild(this.mountPoint);
      console.log("[HomeclawPanel] Mount point created (#svelte-app)");
    } catch (error) {
      console.error("[HomeclawPanel] Constructor error:", error);
      throw error;
    }
  }
  connectedCallback() {
    console.log("[HomeclawPanel] Connected to DOM");
    this._initializeApp();
  }
  disconnectedCallback() {
    console.log("[HomeclawPanel] Disconnected from DOM");
    this._destroyApp();
  }
  /**
   * Initialize Svelte application
   */
  _initializeApp() {
    if (this.svelteApp) {
      console.warn("[HomeclawPanel] App already initialized");
      return;
    }
    if (!this._hass) {
      console.warn("[HomeclawPanel] Waiting for hass to be set before mounting");
      return;
    }
    try {
      console.log("[HomeclawPanel] Mounting Svelte app...");
      console.log("[HomeclawPanel] Props:", {
        hass: !!this._hass,
        narrow: this._narrow,
        panel: this._panel
      });
      this.svelteApp = mount(HomeclawPanel$1, {
        target: this.mountPoint,
        props: {
          hass: this._hass,
          narrow: this._narrow,
          panel: this._panel
        }
      });
      console.log("[HomeclawPanel] Svelte app mounted successfully");
    } catch (error) {
      console.error("[HomeclawPanel] Failed to mount Svelte app:", error);
    }
  }
  /**
   * Destroy Svelte application
   */
  _destroyApp() {
    if (this.svelteApp) {
      try {
        unmount(this.svelteApp);
        this.svelteApp = null;
        console.log("[HomeclawPanel] Svelte app destroyed");
      } catch (error) {
        console.error("[HomeclawPanel] Error destroying Svelte app:", error);
      }
    }
  }
  /**
   * Update Svelte component props efficiently
   */
  _updateProps() {
  }
  /**
   * Home Assistant integration - hass property setter
   */
  set hass(hass) {
    const isFirstSet = !this._hass;
    this._hass = hass;
    if (isFirstSet) {
      console.log("[HomeclawPanel] First hass set - calling _initializeApp()");
      this._initializeApp();
    }
  }
  get hass() {
    return this._hass;
  }
  /**
   * Home Assistant integration - narrow property setter
   */
  set narrow(narrow) {
    this._narrow = narrow;
    if (this.svelteApp) {
      this._updateProps();
    }
  }
  get narrow() {
    return this._narrow;
  }
  /**
   * Home Assistant integration - panel property setter
   */
  set panel(panel) {
    this._panel = panel;
    if (this.svelteApp) {
      this._updateProps();
    }
  }
  get panel() {
    return this._panel;
  }
}
console.log("[HomeclawPanel] Attempting to register custom element...");
try {
  if (!customElements.get("homeclaw-panel")) {
    customElements.define("homeclaw-panel", HomeclawPanel);
    console.log("[HomeclawPanel] ✓ Custom element registered: <homeclaw-panel>");
    console.log("[HomeclawPanel] ✓ Registration successful - element should now be available");
  } else {
    console.warn("[HomeclawPanel] Custom element already registered");
  }
} catch (error) {
  console.error("[HomeclawPanel] Failed to register custom element:", error);
  throw error;
}
window.customPanels = window.customPanels || {};
window.customPanels["homeclaw-panel"] = HomeclawPanel;
console.log("[HomeclawPanel] Class exported to window.customPanels");
console.log("[HomeclawPanel] Module execution complete - waiting for element instantiation");
export {
  HomeclawPanel as default
};
//# sourceMappingURL=homeclaw-panel.js.map
