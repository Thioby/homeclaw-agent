import { get } from 'svelte/store';
import type { HomeAssistant } from '$lib/types';
import { appState } from '$lib/stores/appState';
import { sessionState } from '$lib/stores/sessions';
import { providerState } from '$lib/stores/providers';

/**
 * WebSocket service for Home Assistant communication
 */

/** Attachment payload for WebSocket */
export interface WsAttachment {
  filename: string;
  mime_type: string;
  content: string; // base64
  size: number;
}

/**
 * Send a message via WebSocket
 */
export async function sendMessage(
  hass: HomeAssistant,
  message: string,
  attachments?: WsAttachment[]
): Promise<any> {
  const session = get(sessionState);
  if (!session.activeSessionId) {
    throw new Error('No active session');
  }

  const provider = get(providerState);
  const app = get(appState);

  const wsParams: any = {
    type: 'homeclaw/chat/send',
    session_id: session.activeSessionId,
    message: message,
    provider: provider.selectedProvider,
    debug: app.showThinking,
  };

  // Add model if selected
  if (provider.selectedModel) {
    wsParams.model = provider.selectedModel;
  }

  // Add attachments if present
  if (attachments && attachments.length > 0) {
    wsParams.attachments = attachments;
  }

  return hass.callWS(wsParams);
}

/**
 * Send a message via WebSocket with streaming support
 */
export async function sendMessageStream(
  hass: HomeAssistant,
  message: string,
  callbacks: {
    onStart?: (messageId: string) => void;
    onChunk?: (chunk: string) => void;
    onStatus?: (status: string) => void;
    onToolCall?: (name: string, args: any) => void;
    onToolResult?: (name: string, result: any) => void;
    onComplete?: (result: any) => void;
    onError?: (error: string) => void;
  },
  attachments?: WsAttachment[]
): Promise<void> {
  const session = get(sessionState);
  if (!session.activeSessionId) {
    throw new Error('No active session');
  }

  const provider = get(providerState);
  const app = get(appState);

  const wsParams: any = {
    type: 'homeclaw/chat/send_stream',
    session_id: session.activeSessionId,
    message: message,
    provider: provider.selectedProvider,
    debug: app.showThinking,
  };

  // Add model if selected
  if (provider.selectedModel) {
    wsParams.model = provider.selectedModel;
  }

  // Add attachments if present
  if (attachments && attachments.length > 0) {
    wsParams.attachments = attachments;
  }

  // Subscribe to events for this request.
  // CRITICAL: resubscribe must be false — this is a one-shot command that
  // mutates state (saves messages). If the WS reconnects, HA's default
  // behavior is to re-send the subscription message, which would re-send
  // the chat message to the backend and create duplicate messages.
  let unsubscribe: (() => void) | undefined;
  unsubscribe = await hass.connection.subscribeMessage(
    (event: any) => {
      switch (event.type) {
        case 'user_message':
          break;

        case 'stream_start':
          callbacks.onStart?.(event.message_id);
          break;

        case 'stream_chunk':
          callbacks.onChunk?.(event.chunk);
          break;

        case 'status':
          callbacks.onStatus?.(event.message);
          break;

        case 'tool_call':
          callbacks.onToolCall?.(event.name, event.args);
          break;

        case 'tool_result':
          callbacks.onToolResult?.(event.name, event.result);
          break;

        case 'stream_end':
          if (event.success) {
            callbacks.onComplete?.({});
          } else {
            callbacks.onError?.(event.error || 'Unknown error');
          }
          // Unsubscribe after stream ends
          if (unsubscribe) {
            unsubscribe();
          }
          break;

        default:
          break;
      }
    },
    wsParams,
    { resubscribe: false }
  );
}

/**
 * Subscribe to AI agent response events
 */
export async function subscribeToEvents(
  hass: HomeAssistant,
  callback: (event: any) => void
): Promise<(() => void) | undefined> {
  try {
    return await hass.connection.subscribeEvents(callback, 'homeclaw_response');
  } catch (error) {
    console.error('Failed to subscribe to events:', error);
    return undefined;
  }
}

/**
 * Parse JSON response from AI
 * Handles both pure JSON and markdown with JSON
 */
export function parseAIResponse(content: string): {
  text: string;
  automation?: any;
  dashboard?: any;
} {
  const trimmedContent = content.trim();

  // Only parse if content is pure JSON (starts and ends with braces)
  if (trimmedContent.startsWith('{') && trimmedContent.endsWith('}')) {
    try {
      const parsed = JSON.parse(trimmedContent);

      if (parsed.request_type === 'automation_suggestion') {
        return {
          text: parsed.message || 'I found an automation that might help you.',
          automation: parsed.automation,
        };
      } else if (parsed.request_type === 'dashboard_suggestion') {
        return {
          text: parsed.message || 'I created a dashboard configuration for you.',
          dashboard: parsed.dashboard,
        };
      } else if (parsed.request_type === 'final_response') {
        return {
          text: parsed.response || parsed.message || content,
        };
      }
    } catch (_e) {
      // Not valid JSON, return as-is
    }
  }

  // Default: return content as markdown text
  return { text: content };
}
