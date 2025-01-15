// Add immediate execution log to verify bundle is loaded
console.log('[HomeclawPanel] Bundle loaded and executing...');

import appCss from './app.css?inline';
// Import generated component CSS
import componentCss from '../homeclaw-panel.css?inline';
import HomeclawApp from './lib/components/HomeclawPanel.svelte';
import { mount, unmount } from 'svelte';
import type { HomeAssistant } from './lib/types';

console.log('[HomeclawPanel] Imports completed successfully');
console.log('[HomeclawPanel] App CSS length:', appCss?.length || 0);
console.log('[HomeclawPanel] Component CSS length:', componentCss?.length || 0);
console.log('[HomeclawPanel] HomeclawApp component:', typeof HomeclawApp);

/**
 * Homeclaw Panel Web Component
 * 
 * Custom element that wraps the Svelte application and integrates with Home Assistant.
 * Uses Shadow DOM for style isolation.
 */
class HomeclawPanel extends HTMLElement {
  private _hass?: HomeAssistant;
  private _narrow = false;
  private _panel = true;
  // shadowRoot is inherited from HTMLElement, don't redeclare
  private svelteApp?: any;
  private mountPoint?: HTMLDivElement;

  constructor() {
    super();
    console.log('[HomeclawPanel] Constructor called');
    
    try {
      // Attach Shadow DOM for style isolation
      const shadowRoot = this.attachShadow({ mode: 'open' });
      console.log('[HomeclawPanel] Shadow DOM attached');
      
      // Add global styles to shadow root
      const appStyle = document.createElement('style');
      appStyle.textContent = appCss;
      shadowRoot.appendChild(appStyle);
      console.log('[HomeclawPanel] App CSS injected');
      
      // Add component styles to shadow root
      const componentStyle = document.createElement('style');
      componentStyle.textContent = componentCss;
      shadowRoot.appendChild(componentStyle);
      console.log('[HomeclawPanel] Component CSS injected');
      
      // Create mount point
      this.mountPoint = document.createElement('div');
      this.mountPoint.id = 'svelte-app';
      shadowRoot.appendChild(this.mountPoint);
      console.log('[HomeclawPanel] Mount point created (#svelte-app)');
    } catch (error) {
      console.error('[HomeclawPanel] Constructor error:', error);
      throw error;
    }
  }

  connectedCallback() {
    console.log('[HomeclawPanel] Connected to DOM');
    this._initializeApp();
  }

  disconnectedCallback() {
    console.log('[HomeclawPanel] Disconnected from DOM');
    this._destroyApp();
  }

  /**
   * Initialize Svelte application
   */
  private _initializeApp() {
    if (this.svelteApp) {
      console.warn('[HomeclawPanel] App already initialized');
      return;
    }

    if (!this._hass) {
      console.warn('[HomeclawPanel] Waiting for hass to be set before mounting');
      return;
    }

    try {
      console.log('[HomeclawPanel] Mounting Svelte app...');
      console.log('[HomeclawPanel] Props:', {
        hass: !!this._hass,
        narrow: this._narrow,
        panel: this._panel
      });
      
      // Svelte 5: use mount() API for programmatic component instantiation
      this.svelteApp = mount(HomeclawApp, {
        target: this.mountPoint!,
        props: {
          hass: this._hass,
          narrow: this._narrow,
          panel: this._panel,
        },
      });

      console.log('[HomeclawPanel] Svelte app mounted successfully');
    } catch (error) {
      console.error('[HomeclawPanel] Failed to mount Svelte app:', error);
    }
  }

  /**
   * Destroy Svelte application
   */
  private _destroyApp() {
    if (this.svelteApp) {
      try {
        unmount(this.svelteApp);
        this.svelteApp = null;
        console.log('[HomeclawPanel] Svelte app destroyed');
      } catch (error) {
        console.error('[HomeclawPanel] Error destroying Svelte app:', error);
      }
    }
  }

  /**
   * Update Svelte component props efficiently
   */
  private _updateProps() {
    // Intentionally empty - we don't update props after mount
    // to avoid infinite remount loops. Component uses WebSocket for updates.
  }

  /**
   * Home Assistant integration - hass property setter
   */
  set hass(hass: HomeAssistant) {
    const isFirstSet = !this._hass;
    this._hass = hass;
    
    if (isFirstSet) {
      // First time setting hass - initialize the app
      console.log('[HomeclawPanel] First hass set - calling _initializeApp()');
      this._initializeApp();
    }
    // Don't update props on every hass change - it causes infinite loop
    // The component uses WebSocket for real-time updates, not hass prop
  }

  get hass(): HomeAssistant | undefined {
    return this._hass;
  }

  /**
   * Home Assistant integration - narrow property setter
   */
  set narrow(narrow: boolean) {
    this._narrow = narrow;
    if (this.svelteApp) {
      this._updateProps();
    }
  }

  get narrow(): boolean {
    return this._narrow;
  }

  /**
   * Home Assistant integration - panel property setter
   */
  set panel(panel: boolean) {
    this._panel = panel;
    if (this.svelteApp) {
      this._updateProps();
    }
  }

  get panel(): boolean {
    return this._panel;
  }
}

// Register the custom element
console.log('[HomeclawPanel] Attempting to register custom element...');
try {
  if (!customElements.get('homeclaw-panel')) {
    customElements.define('homeclaw-panel', HomeclawPanel);
    console.log('[HomeclawPanel] ✓ Custom element registered: <homeclaw-panel>');
    console.log('[HomeclawPanel] ✓ Registration successful - element should now be available');
  } else {
    console.warn('[HomeclawPanel] Custom element already registered');
  }
} catch (error) {
  console.error('[HomeclawPanel] Failed to register custom element:', error);
  throw error;
}

// Make available globally for Home Assistant panel system
(window as any).customPanels = (window as any).customPanels || {};
(window as any).customPanels['homeclaw-panel'] = HomeclawPanel;
console.log('[HomeclawPanel] Class exported to window.customPanels');

// Export for potential direct usage
export default HomeclawPanel;

console.log('[HomeclawPanel] Module execution complete - waiting for element instantiation');
