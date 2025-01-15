import { writable } from 'svelte/store';

/**
 * UI state
 */
export interface UIStateType {
  sidebarOpen: boolean;
  showProviderDropdown: boolean;
  settingsOpen: boolean;
}

const initialState: UIStateType = {
  sidebarOpen: typeof window !== 'undefined' ? window.innerWidth > 768 : false,
  showProviderDropdown: false,
  settingsOpen: false,
};

export const uiState = writable<UIStateType>(initialState);

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
