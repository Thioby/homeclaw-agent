import { writable, derived } from 'svelte/store';
import type { HomeAssistant } from '$lib/types';

export interface AppStateType {
  hass: HomeAssistant | null;
  error: string | null;
  reasoningEnabled: boolean;
  agentName: string;
  agentEmoji: string;
  userName: string;
}

const initialState: AppStateType = {
  hass: null,
  error: null,
  reasoningEnabled: false,
  agentName: 'Homeclaw',
  agentEmoji: '',
  userName: '',
};

export const appState = writable<AppStateType>(initialState);

export const hasError = derived(appState, $state => $state.error !== null);
