import { writable, derived, get } from 'svelte/store';
import type { Message } from '$lib/types';
import { sessionState } from './sessions';

export interface SessionRuntime {
  messages: Message[];
  isLoading: boolean;
  streamingReasoning: string;
}

function emptyRuntime(): SessionRuntime {
  return { messages: [], isLoading: false, streamingReasoning: '' };
}

export const chatRuntime = writable<Record<string, SessionRuntime>>({});

export function getSessionRuntime(sessionId: string): SessionRuntime {
  return get(chatRuntime)[sessionId] ?? emptyRuntime();
}

export function updateSessionRuntime(
  sessionId: string,
  updater: (runtime: SessionRuntime) => SessionRuntime
): void {
  chatRuntime.update((all) => ({
    ...all,
    [sessionId]: updater(all[sessionId] ?? emptyRuntime()),
  }));
}

export function setSessionMessages(sessionId: string, messages: Message[]): void {
  updateSessionRuntime(sessionId, (r) => ({ ...r, messages }));
}

export function clearSessionRuntime(sessionId: string): void {
  chatRuntime.update((all) => {
    const next = { ...all };
    delete next[sessionId];
    return next;
  });
}

export function isSessionBusy(sessionId: string): boolean {
  const runtime = getSessionRuntime(sessionId);
  return runtime.isLoading || runtime.messages.some((m) => m.isStreaming);
}

const activeRuntime = derived(
  [chatRuntime, sessionState],
  ([$runtime, $session]) =>
    ($session.activeSessionId ? $runtime[$session.activeSessionId] : undefined) ?? emptyRuntime()
);

export const activeMessages = derived(activeRuntime, ($r) => $r.messages);
export const activeIsLoading = derived(activeRuntime, ($r) => $r.isLoading);
export const activeStreamingReasoning = derived(activeRuntime, ($r) => $r.streamingReasoning);
export const activeHasMessages = derived(activeRuntime, ($r) => $r.messages.length > 0);
