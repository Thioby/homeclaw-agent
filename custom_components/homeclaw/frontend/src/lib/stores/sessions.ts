import { writable, derived } from 'svelte/store';
import type { SessionListItem } from '$lib/types';

/**
 * Session management state
 */
export interface SessionStateType {
  sessions: SessionListItem[];
  activeSessionId: string | null;
  sessionsLoading: boolean;
}

const initialState: SessionStateType = {
  sessions: [],
  activeSessionId: null,
  sessionsLoading: true,
};

export const sessionState = writable<SessionStateType>(initialState);

// Derived stores
export const hasSessions = derived(sessionState, $state => $state.sessions.length > 0);
export const activeSession = derived(sessionState, $state =>
  $state.sessions.find(s => s.session_id === $state.activeSessionId) || null
);
