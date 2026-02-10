<script lang="ts">
  import { get } from 'svelte/store';
  import { appState } from '$lib/stores/appState';
  import { sessionState } from '$lib/stores/sessions';
  import { providerState } from '$lib/stores/providers';
  import { sendMessage, sendMessageStream, parseAIResponse } from '$lib/services/websocket.service';
  import { createSession, updateSessionInList } from '$lib/services/session.service';
  import MessageInput from './MessageInput.svelte';
  import ProviderSelector from './ProviderSelector.svelte';
  import ModelSelector from './ModelSelector.svelte';
  import SendButton from './SendButton.svelte';
  import ThinkingToggle from './ThinkingToggle.svelte';

  let messageInput: MessageInput;
  const USE_STREAMING = true; // Feature flag - set to false to disable streaming

  async function handleSend() {
    const currentAppState = get(appState);
    if (!currentAppState.hass) return;

    const message = messageInput.getValue().trim();
    if (!message || currentAppState.isLoading) return;

    // Clear input
    messageInput.clear();

    appState.update(s => ({ ...s, isLoading: true, error: null }));

    // Create session if none active
    const currentSessionState = get(sessionState);
    const currentProviderState = get(providerState);
    
    if (!currentSessionState.activeSessionId && currentProviderState.selectedProvider) {
      await createSession(currentAppState.hass, currentProviderState.selectedProvider);
    }

    const updatedSessionState = get(sessionState);
    if (!updatedSessionState.activeSessionId) {
      appState.update(s => ({ ...s, error: 'No active session', isLoading: false }));
      return;
    }

    // Add user message
    appState.update(s => ({ 
      ...s, 
      messages: [...s.messages, { 
        id: `user-${Date.now()}-${Math.random()}`,
        type: 'user', 
        text: message 
      }] 
    }));

    try {
      if (USE_STREAMING) {
        // Use streaming API
        console.log('[InputArea] Using STREAMING mode');
        let assistantMessageId = '';
        let streamedText = '';

        await sendMessageStream(currentAppState.hass, message, {
          onStart: (messageId: string) => {
            assistantMessageId = messageId;
            // Add placeholder message for streaming (with dedup guard)
            appState.update(s => {
              if (s.messages.some(m => m.id === assistantMessageId)) return s;
              return {
                ...s,
                messages: [...s.messages, {
                  id: assistantMessageId,
                  type: 'assistant' as const,
                  text: '',
                  status: 'streaming' as const,
                  isStreaming: true,
                }],
              };
            });
          },
          
          onChunk: (chunk: string) => {
            streamedText += chunk;
            // Update the streaming message
            appState.update(s => ({
              ...s,
              messages: s.messages.map(msg =>
                msg.id === assistantMessageId
                  ? { ...msg, text: streamedText }
                  : msg
              )
            }));
          },
          
          onStatus: (status: string) => {
            console.log('Status update:', status);
            // Update streaming message with status (e.g. "Calling tool X...")
            appState.update(s => ({
              ...s,
              messages: s.messages.map(msg =>
                msg.id === assistantMessageId
                  ? { ...msg, text: streamedText + `\n\n_${status}_` }
                  : msg
              )
            }));
          },
          
          onToolCall: (name: string, args: any) => {
            console.log('Tool call:', name, args);
            // Tool calls are now handled internally in backend
          },
          
          onToolResult: (name: string, result: any) => {
            console.log('Tool result:', name, result);
            // Tool results are now handled internally in backend
          },
          
          onComplete: (result: any) => {
            // Parse final result
            let { text, automation, dashboard } = parseAIResponse(
              result.assistant_message?.content || streamedText
            );

            // Update message to completed state
            appState.update(s => ({
              ...s,
              isLoading: false,
              messages: s.messages.map(msg =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      text: text || streamedText,
                      status: 'completed' as const,
                      isStreaming: false,
                      automation: automation || result.assistant_message?.metadata?.automation,
                      dashboard: dashboard || result.assistant_message?.metadata?.dashboard,
                    }
                  : msg
              )
            }));

            // Update session in list
            const sessions = get(sessionState).sessions;
            const activeId = get(sessionState).activeSessionId;
            const session = sessions.find(s => s.session_id === activeId);
            const isNewConversation = session?.title === 'New Conversation';
            updateSessionInList(
              activeId!,
              message,
              isNewConversation ? message.substring(0, 40) + (message.length > 40 ? '...' : '') : undefined
            );
          },
          
          onError: (error: string) => {
            console.error('Streaming error:', error);
            appState.update(s => ({
              ...s,
              isLoading: false,
              error: error,
              messages: s.messages.map(msg =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      text: `Error: ${error}`,
                      status: 'error' as const,
                      isStreaming: false,
                      error_message: error,
                    }
                  : msg
              )
            }));
          },
        });
      } else {
        // Fallback to non-streaming (original code)
        const result = await sendMessage(currentAppState.hass, message);
        appState.update(s => ({ ...s, isLoading: false }));

        if (result.assistant_message) {
          let { text, automation, dashboard } = parseAIResponse(
            result.assistant_message.content || ''
          );

          const assistantMsg: any = {
            id: `assistant-${Date.now()}-${Math.random()}`,
            type: 'assistant',
            text,
            automation: automation || result.assistant_message.metadata?.automation,
            dashboard: dashboard || result.assistant_message.metadata?.dashboard,
            status: result.assistant_message.status,
            error_message: result.assistant_message.error_message,
          };

          if (result.assistant_message.status === 'error') {
            appState.update(s => ({ ...s, error: result.assistant_message.error_message }));
            assistantMsg.text = `Error: ${result.assistant_message.error_message}`;
          }

          appState.update(s => ({ 
            ...s, 
            messages: [...s.messages, assistantMsg] 
          }));

          // Update session in list
          const sessions = get(sessionState).sessions;
          const activeId = get(sessionState).activeSessionId;
          const session = sessions.find(s => s.session_id === activeId);
          const isNewConversation = session?.title === 'New Conversation';
          updateSessionInList(
            activeId!,
            message,
            isNewConversation ? message.substring(0, 40) + (message.length > 40 ? '...' : '') : undefined
          );
        }
      }
    } catch (error: any) {
      console.error('WebSocket error:', error);
      const errorMessage = error.message || 'An error occurred while processing your request';
      appState.update(s => ({
        ...s,
        isLoading: false,
        error: errorMessage,
        messages: [...s.messages, { 
          id: `error-${Date.now()}-${Math.random()}`,
          type: 'assistant', 
          text: `Error: ${errorMessage}` 
        }],
      }));
    }
  }
</script>

<div class="input-container">
  <div class="input-main">
    <MessageInput bind:this={messageInput} onSend={handleSend} />
  </div>

  <div class="input-footer">
    <ProviderSelector />
    <ModelSelector />
    <ThinkingToggle />
    <SendButton onclick={handleSend} />
  </div>
</div>

<style>
  .input-container {
    position: relative;
    width: 100%;
    background: var(--bg-input, var(--card-background-color));
    border: 1px solid var(--divider-color);
    border-radius: 24px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
    margin: 0 auto 12px;
    max-width: 720px;
    transition: border-color var(--transition-fast, 150ms ease-in-out), box-shadow var(--transition-fast, 150ms ease-in-out);
  }

  .input-container:focus-within {
    border-color: var(--accent, var(--primary-color));
    box-shadow: 0 0 0 2px var(--accent-light, rgba(3, 169, 244, 0.1));
  }

  .input-main {
    display: flex;
    align-items: flex-end;
    padding: 8px 12px;
    gap: 8px;
  }

  .input-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 14px 10px;
    border-top: 1px solid var(--divider-color);
    gap: 8px;
  }

  @media (max-width: 768px) {
    .input-container {
      border-radius: 20px;
      margin-bottom: 8px;
      margin-left: 6px;
      margin-right: 6px;
    }

    .input-footer {
      gap: 6px;
      padding: 4px 10px 8px;
    }
  }

  @media (min-width: 1400px) {
    .input-container {
      max-width: 820px;
    }
  }
</style>
