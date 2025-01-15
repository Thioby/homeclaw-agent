import { get } from 'svelte/store';
import type { HomeAssistant } from '$lib/types';
import { appState } from '$lib/stores/appState';
import { sessionState } from '$lib/stores/sessions';
import { providerState } from '$lib/stores/providers';

/**
 * WebSocket service for Home Assistant communication
 */

/**
 * Send a message via WebSocket
 */
export async function sendMessage(
  hass: HomeAssistant,
  message: string
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
  }
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

  console.log('[WebSocket] Sending STREAMING message with params:', wsParams);

  // Subscribe to events for this request
  let unsubscribe: (() => void) | undefined;
  unsubscribe = await hass.connection.subscribeMessage(
    (event: any) => {
      console.log('[WebSocket] Received streaming event:', event);
      
      // Home Assistant subscribeMessage unpacks the event, so we receive the inner event directly
      console.log('[WebSocket] Event type:', event.type);
      
      switch (event.type) {
        case 'user_message':
          console.log('[WebSocket] User message received');
          break;
        
        case 'stream_start':
          console.log('[WebSocket] Stream started, message_id:', event.message_id);
          callbacks.onStart?.(event.message_id);
          break;
        
        case 'stream_chunk':
          console.log('[WebSocket] Stream chunk:', event.chunk?.substring(0, 50));
          callbacks.onChunk?.(event.chunk);
          break;
        
        case 'status':
          console.log('[WebSocket] Status update:', event.message);
          callbacks.onStatus?.(event.message);
          break;
        
        case 'tool_call':
          console.log('[WebSocket] Tool call:', event.name);
          callbacks.onToolCall?.(event.name, event.args);
          break;
        
        case 'tool_result':
          console.log('[WebSocket] Tool result:', event.name);
          callbacks.onToolResult?.(event.name, event.result);
          break;
        
        case 'stream_end':
          console.log('[WebSocket] Stream ended, success:', event.success);
          if (event.success) {
            // Stream completed successfully - call onComplete
            console.log('[WebSocket] Calling onComplete');
            callbacks.onComplete?.({});
          } else {
            callbacks.onError?.(event.error || 'Unknown error');
          }
          // Unsubscribe after stream ends
          if (unsubscribe) {
            unsubscribe();
          }
          break;
        
        case 'result':
          // This shouldn't be called in subscription mode, but handle it just in case
          console.log('[WebSocket] Unexpected result event in subscription');
          break;
        
        default:
          console.log('[WebSocket] Unknown event type:', event.type);
      }
    },
    wsParams
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
    } catch (e) {
      // Not valid JSON, return as-is
    }
  }

  // Default: return content as markdown text
  return { text: content };
}
