import { writable, derived } from 'svelte/store';
import type { HomeAssistant, Message } from '$lib/types';

export interface AppStateType {
  hass: HomeAssistant | null;
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  reasoningEnabled: boolean;
  agentName: string;
  agentEmoji: string;
  userName: string;
  streamingReasoning: string;
}

const initialState: AppStateType = {
  hass: null,
  messages: [],
  isLoading: false,
  error: null,
  reasoningEnabled: false,
  agentName: 'Homeclaw',
  agentEmoji: '',
  userName: '',
  streamingReasoning: '',
};

export const appState = writable<AppStateType>(initialState);

export const hasMessages = derived(appState, $state => $state.messages.length > 0);
export const hasError = derived(appState, $state => $state.error !== null);
