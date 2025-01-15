import { writable, derived } from 'svelte/store';
import type { HomeAssistant, Message } from '$lib/types';

/**
 * Global application state
 */
export interface AppStateType {
  hass: HomeAssistant | null;
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  debugInfo: any;
  showThinking: boolean;
  thinkingExpanded: boolean;
}

const initialState: AppStateType = {
  hass: null,
  messages: [],
  isLoading: false,
  error: null,
  debugInfo: null,
  showThinking: false,
  thinkingExpanded: false,
};

export const appState = writable<AppStateType>(initialState);

// Derived stores
export const hasMessages = derived(appState, $state => $state.messages.length > 0);
export const hasError = derived(appState, $state => $state.error !== null);
