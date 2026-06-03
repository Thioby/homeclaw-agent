import { get } from 'svelte/store';
import type { HomeAssistant } from '$lib/types';
import { sessionState } from '$lib/stores/sessions';
import { appState } from '$lib/stores/appState';
import { providerState } from '$lib/stores/providers';
import { fetchModels } from './provider.service';
import { clearSessionCache } from './markdown.service';

/**
 * Session management service
 */

/**
 * Load all sessions from Home Assistant
 */
export async function loadSessions(hass: HomeAssistant): Promise<void> {
  sessionState.update(s => ({ ...s, sessionsLoading: true }));
  
  try {
    const result = await hass.callWS({
      type: 'homeclaw/sessions/list',
    });

    const sessions = result.sessions || [];
    sessionState.update(s => ({ ...s, sessions }));

    // Auto-select first session if none selected
    const state = get(sessionState);
    if (sessions.length > 0 && !state.activeSessionId) {
      await selectSession(hass, sessions[0].session_id);
    }
  } catch (error) {
    console.error('Failed to load sessions:', error);
    appState.update(s => ({ ...s, error: 'Could not load conversations' }));
  } finally {
    sessionState.update(s => ({ ...s, sessionsLoading: false }));
  }
}

/**
 * Select a session and load its messages
 */
export async function selectSession(hass: HomeAssistant, sessionId: string): Promise<void> {
  sessionState.update(s => ({ ...s, activeSessionId: sessionId }));
  appState.update(s => ({ ...s, isLoading: true, error: null }));

  try {
    const result = await hass.callWS({
      type: 'homeclaw/sessions/get',
      session_id: sessionId,
    });

    // Map messages from HA format to our format
    const rawMessages = result.messages || [];

    const messages = rawMessages
      .map((m: any, index: number) => ({
        id: m.message_id || `fallback-${sessionId}-${index}`,
        type: m.role === 'user' ? ('user' as const) : ('assistant' as const),
        text: m.content,
        automation: m.metadata?.automation,
        dashboard: m.metadata?.dashboard,
        timestamp: m.timestamp,
        status: m.status,
        error_message: m.error_message,
        attachments: m.attachments,
      }))
      .sort((a: any, b: any) => (a.timestamp || '').localeCompare(b.timestamp || ''));

    appState.update((s) => ({ ...s, messages }));

    // Mirror the session's provider + model in the selector so the user sees
    // what will actually be used. Provider is locked server-side once the
    // session has messages; model can be changed at any time.
    const sessionProvider = result.session?.provider;
    const sessionModel = result.session?.model || null;
    if (sessionProvider) {
      const currentState = get(providerState);
      const providerChanged = currentState.selectedProvider !== sessionProvider;
      if (providerChanged) {
        providerState.update((s) => ({ ...s, selectedProvider: sessionProvider }));
        await fetchModels(hass, sessionProvider, sessionModel);
      } else if (sessionModel && currentState.selectedModel !== sessionModel) {
        providerState.update((s) => ({ ...s, selectedModel: sessionModel }));
      }
    }

    // Close sidebar on mobile
    if (typeof window !== 'undefined' && window.innerWidth <= 768) {
      const { closeSidebar } = await import('$lib/stores/ui');
      closeSidebar();
    }
  } catch (error) {
    console.error('Failed to load session:', error);
    appState.update(s => ({ ...s, error: 'Could not load conversation' }));
  } finally {
    appState.update(s => ({ ...s, isLoading: false }));
  }
}

/**
 * Create a new session
 */
export async function createSession(hass: HomeAssistant, provider: string): Promise<void> {
  console.log('[Session] Creating new session with provider:', provider);
  try {
    const result = await hass.callWS({
      type: 'homeclaw/sessions/create',
      provider: provider,
    });

    console.log('[Session] Session created:', result);

    sessionState.update(s => ({
      ...s,
      sessions: [result, ...s.sessions],
      activeSessionId: result.session_id,
    }));
    
    console.log('[Session] Active session ID set to:', result.session_id);
    
    appState.update(s => ({ ...s, messages: [] }));

    // WORKAROUND: Small delay to ensure backend has saved the session
    // This fixes race condition with streaming endpoint
    await new Promise(resolve => setTimeout(resolve, 100));
    console.log('[Session] Waited 100ms for session to be fully saved');

    // Close sidebar on mobile
    if (typeof window !== 'undefined' && window.innerWidth <= 768) {
      const { closeSidebar } = await import('$lib/stores/ui');
      closeSidebar();
    }
  } catch (error) {
    console.error('Failed to create session:', error);
    appState.update(s => ({ ...s, error: 'Could not create new conversation' }));
  }
}

/**
 * Start a fresh conversation from the user's preferred default provider, then
 * ask the composer to grab focus so the user can type right away.
 */
export async function startNewChat(hass: HomeAssistant): Promise<void> {
  const providers = get(providerState);
  const startProvider = providers.defaultProvider || providers.selectedProvider;

  if (!startProvider) {
    appState.update(s => ({ ...s, error: 'Please select a provider first' }));
    return;
  }

  if (providers.selectedProvider !== startProvider) {
    providerState.update(s => ({
      ...s,
      selectedProvider: startProvider,
      selectedModel: providers.defaultModel || null,
    }));
    await fetchModels(hass, startProvider);
  }

  await createSession(hass, startProvider);

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('homeclaw-focus-input'));
  }
}

/**
 * Change a session's provider. Only succeeds if the session has no messages
 * yet — the backend locks the provider on first send. On success the local
 * session list and selectedProvider are updated to reflect the change.
 */
export async function updateSessionProvider(
  hass: HomeAssistant,
  sessionId: string,
  provider: string
): Promise<boolean> {
  try {
    await hass.callWS({
      type: 'homeclaw/sessions/update_provider',
      session_id: sessionId,
      provider,
    });

    sessionState.update((s) => ({
      ...s,
      sessions: s.sessions.map((session) =>
        session.session_id === sessionId ? { ...session, provider } : session
      ),
    }));

    providerState.update((s) => ({ ...s, selectedProvider: provider }));
    await fetchModels(hass, provider);
    return true;
  } catch (error) {
    console.warn('updateSessionProvider failed:', error);
    appState.update((s) => ({
      ...s,
      error: 'Could not change provider for this session',
    }));
    return false;
  }
}

/**
 * Delete a session
 */
export async function deleteSession(hass: HomeAssistant, sessionId: string): Promise<void> {
  try {
    await hass.callWS({
      type: 'homeclaw/sessions/delete',
      session_id: sessionId,
    });

    // Remove from list
    sessionState.update(s => ({
      ...s,
      sessions: s.sessions.filter(session => session.session_id !== sessionId),
    }));

    // Clear markdown cache for this session
    clearSessionCache(sessionId);

    // If deleted active session, select first available
    const state = get(sessionState);
    if (state.activeSessionId === sessionId) {
      if (state.sessions.length > 0) {
        await selectSession(hass, state.sessions[0].session_id);
      } else {
        sessionState.update(s => ({ ...s, activeSessionId: null }));
        appState.update(s => ({ ...s, messages: [] }));
      }
    }
  } catch (error) {
    console.error('Failed to delete session:', error);
    appState.update(s => ({ ...s, error: 'Could not delete conversation' }));
  }
}

/**
 * Update session metadata (title/preview)
 */
export function updateSessionInList(sessionId: string, preview?: string, title?: string): void {
  sessionState.update(s => {
    const updatedSessions = s.sessions.map(session => {
      if (session.session_id === sessionId) {
        return {
          ...session,
          preview: preview ? preview.substring(0, 100) : session.preview,
          title: title || session.title,
          message_count: (session.message_count || 0) + 2,
          updated_at: new Date().toISOString(),
        };
      }
      return session;
    });

    // Re-sort by updated_at
    const sortedSessions = [...updatedSessions].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );

    return { ...s, sessions: sortedSessions };
  });

  // Fire-and-forget emoji generation when a new title is set
  if (title) {
    const hass = get(appState).hass;
    if (hass) {
      generateSessionEmoji(hass, sessionId, title);
    }
  }
}

/**
 * Generate an emoji for a session title via AI (fire-and-forget)
 */
async function generateSessionEmoji(
  hass: HomeAssistant,
  sessionId: string,
  title: string
): Promise<void> {
  try {
    const result = await hass.callWS({
      type: 'homeclaw/sessions/generate_emoji',
      session_id: sessionId,
      title: title,
    });

    const emoji = result?.emoji;
    if (emoji) {
      // Update the session in the store with the generated emoji
      sessionState.update(s => ({
        ...s,
        sessions: s.sessions.map(session =>
          session.session_id === sessionId ? { ...session, emoji } : session
        ),
      }));
    }
  } catch (error) {
    // Non-critical — silently ignore emoji generation failures
    console.warn('Emoji generation failed:', error);
  }
}
