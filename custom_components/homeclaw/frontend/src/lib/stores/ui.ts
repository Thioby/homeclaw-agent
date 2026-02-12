import { get, writable } from 'svelte/store';
import type { HomeAssistant } from '$lib/types';
import { appState } from '$lib/stores/appState';

/**
 * UI state
 */
export interface UIStateType {
  sidebarOpen: boolean;
  showProviderDropdown: boolean;
  settingsOpen: boolean;
  theme: 'light' | 'dark' | 'system';
}

type ThemePreference = UIStateType['theme'];

/**
 * Reference to the <homeclaw-panel> host element.
 * Set once from main.ts after the custom element is constructed.
 */
let _hostElement: HTMLElement | null = null;

export function setHostElement(el: HTMLElement): void {
  _hostElement = el;
}

const initialState: UIStateType = {
  sidebarOpen: typeof window !== 'undefined' ? window.innerWidth > 768 : false,
  showProviderDropdown: false,
  settingsOpen: false,
  theme: 'system',
};

export const uiState = writable<UIStateType>(initialState);

function isValidTheme(theme: unknown): theme is ThemePreference {
  return theme === 'light' || theme === 'dark' || theme === 'system';
}

/**
 * UI actions
 */
export function toggleSidebar() {
  uiState.update(state => ({ ...state, sidebarOpen: !state.sidebarOpen }));
}

export function closeSidebar() {
  uiState.update(state => ({ ...state, sidebarOpen: false }));
}

export function openSidebar() {
  uiState.update(state => ({ ...state, sidebarOpen: true }));
}

export function closeDropdowns() {
  uiState.update(state => ({ ...state, showProviderDropdown: false }));
}

export function openSettings() {
  uiState.update(state => ({ ...state, settingsOpen: true }));
}

export function closeSettings() {
  uiState.update(state => ({ ...state, settingsOpen: false }));
}

export function toggleSettings() {
  uiState.update(state => ({ ...state, settingsOpen: !state.settingsOpen }));
}

/**
 * Theme actions
 */
export function setTheme(theme: 'light' | 'dark' | 'system'): void {
  uiState.update(s => ({ ...s, theme }));
  // Apply data-theme attribute to host element
  applyThemeToHost(theme);
  // Persist
  try {
    localStorage.setItem('homeclaw-theme', theme);
  } catch {
    // localStorage may be unavailable in some contexts
  }

  void persistThemePreference(theme);
}

export function cycleTheme(): void {
  const current = get(uiState).theme;
  const next = current === 'system' ? 'light' : current === 'light' ? 'dark' : 'system';
  setTheme(next);
}

function applyThemeToHost(theme: 'light' | 'dark' | 'system'): void {
  // Use stored reference (set from main.ts), fall back to document query
  const host = _hostElement || document.querySelector('homeclaw-panel');
  if (!host) {
    console.warn('[Theme] Could not find homeclaw-panel host element');
    return;
  }

  if (theme === 'system') {
    host.removeAttribute('data-theme');
  } else {
    host.setAttribute('data-theme', theme);
  }

  // Brief transition class for smooth theme switch
  host.classList.add('theme-transitioning');
  setTimeout(() => host.classList.remove('theme-transitioning'), 350);
}

async function persistThemePreference(theme: ThemePreference): Promise<void> {
  const hass = get(appState).hass;
  if (!hass) return;

  try {
    await hass.callWS({
      type: 'homeclaw/preferences/set',
      theme,
    });
  } catch (error) {
    console.warn('[Theme] Could not persist theme preference:', error);
  }
}

export async function syncThemeFromPreferences(
  hass?: HomeAssistant | null,
): Promise<void> {
  const ha = hass ?? get(appState).hass;
  if (!ha) return;

  try {
    const result = await ha.callWS({ type: 'homeclaw/preferences/get' });
    const theme = result?.preferences?.theme;
    if (!isValidTheme(theme)) return;

    // Apply server preference and keep local cache in sync.
    uiState.update(s => ({ ...s, theme }));
    applyThemeToHost(theme);
    try {
      localStorage.setItem('homeclaw-theme', theme);
    } catch {
      // localStorage may be unavailable in some contexts
    }
  } catch (error) {
    console.warn('[Theme] Could not load theme preference:', error);
  }
}

// Initialize theme from localStorage
function initTheme(): void {
  try {
    const saved = localStorage.getItem('homeclaw-theme');
    if (isValidTheme(saved)) {
      uiState.update(s => ({ ...s, theme: saved }));
      // Defer applying to host until DOM is ready
      setTimeout(() => applyThemeToHost(saved), 0);
    }
  } catch {
    // localStorage may be unavailable
  }
}

initTheme();
