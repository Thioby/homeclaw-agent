<script lang="ts">
  import { get } from 'svelte/store';
  import { appState } from '$lib/stores/appState';
  import { sessionState } from '$lib/stores/sessions';
  import { providerState } from '$lib/stores/providers';
  import { sendMessage, sendMessageStream, parseAIResponse } from '$lib/services/websocket.service';
  import { createSession, updateSessionInList } from '$lib/services/session.service';
  import type { FileAttachment } from '$lib/types/message';
  import MessageInput from './MessageInput.svelte';
  import ProviderSelector from './ProviderSelector.svelte';
  import ModelSelector from './ModelSelector.svelte';
  import SendButton from './SendButton.svelte';
  import ThinkingToggle from './ThinkingToggle.svelte';
  import AttachButton from './AttachButton.svelte';
  import AttachmentPreview from './AttachmentPreview.svelte';

  let messageInput: MessageInput;
  const USE_STREAMING = true;
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
  const MAX_ATTACHMENTS = 5;

  let pendingAttachments: FileAttachment[] = $state([]);

  /**
   * Read a File object and create a FileAttachment with base64 content.
   */
  function readFileAsAttachment(file: File): Promise<FileAttachment> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result as string;
        const isImage = file.type.startsWith('image/');

        // Extract raw base64 from data URL
        const base64Match = dataUrl.match(/^data:[^;]+;base64,(.*)$/);
        const rawBase64 = base64Match ? base64Match[1] : dataUrl;

        resolve({
          file_id: `local-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          filename: file.name,
          mime_type: file.type || 'application/octet-stream',
          size: file.size,
          data_url: isImage ? dataUrl : undefined,
          content: rawBase64,
          status: 'ready',
          is_image: isImage,
        });
      };
      reader.onerror = () => reject(new Error(`Failed to read file: ${file.name}`));
      reader.readAsDataURL(file);
    });
  }

  /**
   * Process raw File objects into FileAttachments.
   */
  async function processFiles(files: File[] | FileList) {
    const fileArray = Array.from(files);

    // Check total count
    const totalCount = pendingAttachments.length + fileArray.length;
    if (totalCount > MAX_ATTACHMENTS) {
      console.warn(`Too many attachments: ${totalCount} (max ${MAX_ATTACHMENTS})`);
      // Only take what we can fit
      const remaining = MAX_ATTACHMENTS - pendingAttachments.length;
      if (remaining <= 0) return;
      fileArray.splice(remaining);
    }

    for (const file of fileArray) {
      // Validate size
      if (file.size > MAX_FILE_SIZE) {
        console.warn(`File too large: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`);
        continue;
      }

      try {
        const attachment = await readFileAsAttachment(file);
        pendingAttachments = [...pendingAttachments, attachment];
      } catch (err) {
        console.error(`Failed to process file: ${file.name}`, err);
      }
    }
  }

  function handleFilesSelected(files: FileList) {
    processFiles(files);
  }

  function handleFilesDropped(files: File[]) {
    processFiles(files);
  }

  function removeAttachment(fileId: string) {
    pendingAttachments = pendingAttachments.filter((a) => a.file_id !== fileId);
  }

  async function handleSend() {
    const currentAppState = get(appState);
    if (!currentAppState.hass) return;

    const message = messageInput.getValue().trim();
    const hasAttachments = pendingAttachments.length > 0;

    // Need either text or attachments
    if ((!message && !hasAttachments) || currentAppState.isLoading) return;

    // Capture and clear attachments before async operations
    const attachmentsToSend = [...pendingAttachments];

    // Clear input
    messageInput.clear();
    pendingAttachments = [];

    appState.update((s) => ({ ...s, isLoading: true, error: null }));

    // Create session if none active
    const currentSessionState = get(sessionState);
    const currentProviderState = get(providerState);

    if (!currentSessionState.activeSessionId && currentProviderState.selectedProvider) {
      await createSession(currentAppState.hass, currentProviderState.selectedProvider);
    }

    const updatedSessionState = get(sessionState);
    if (!updatedSessionState.activeSessionId) {
      appState.update((s) => ({ ...s, error: 'No active session', isLoading: false }));
      return;
    }

    // Build user message with attachments for local display
    const userMsg: any = {
      id: `user-${Date.now()}-${Math.random()}`,
      type: 'user',
      text: message,
      attachments: attachmentsToSend.map((a) => ({
        file_id: a.file_id,
        filename: a.filename,
        mime_type: a.mime_type,
        size: a.size,
        data_url: a.data_url,
        is_image: a.is_image,
        status: 'ready' as const,
      })),
    };

    // Add user message
    appState.update((s) => ({
      ...s,
      messages: [...s.messages, userMsg],
    }));

    // Build WS attachments payload (base64 content for backend)
    const wsAttachments = attachmentsToSend.map((a) => ({
      filename: a.filename,
      mime_type: a.mime_type,
      content: a.content || '',
      size: a.size,
    }));

    try {
      if (USE_STREAMING) {
        let assistantMessageId = '';
        let streamedText = '';

        await sendMessageStream(
          currentAppState.hass,
          message,
          {
            onStart: (messageId: string) => {
              assistantMessageId = messageId;
              appState.update((s) => {
                if (s.messages.some((m) => m.id === assistantMessageId)) return s;
                return {
                  ...s,
                  messages: [
                    ...s.messages,
                    {
                      id: assistantMessageId,
                      type: 'assistant' as const,
                      text: '',
                      status: 'streaming' as const,
                      isStreaming: true,
                    },
                  ],
                };
              });
            },

            onChunk: (chunk: string) => {
              streamedText += chunk;
              appState.update((s) => ({
                ...s,
                messages: s.messages.map((msg) =>
                  msg.id === assistantMessageId ? { ...msg, text: streamedText } : msg
                ),
              }));
            },

            onStatus: (status: string) => {
              appState.update((s) => ({
                ...s,
                messages: s.messages.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, text: streamedText + `\n\n_${status}_` }
                    : msg
                ),
              }));
            },

            onToolCall: (_name: string, _args: any) => {},
            onToolResult: (_name: string, _result: any) => {},

            onComplete: (result: any) => {
              const { text, automation, dashboard } = parseAIResponse(
                result.assistant_message?.content || streamedText
              );

              appState.update((s) => ({
                ...s,
                isLoading: false,
                messages: s.messages.map((msg) =>
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
                ),
              }));

              const sessions = get(sessionState).sessions;
              const activeId = get(sessionState).activeSessionId;
              const session = sessions.find((s) => s.session_id === activeId);
              const isNewConversation = session?.title === 'New Conversation';
              const previewText = message || attachmentsToSend.map((a) => a.filename).join(', ');
              updateSessionInList(
                activeId!,
                previewText,
                isNewConversation
                  ? previewText.substring(0, 40) + (previewText.length > 40 ? '...' : '')
                  : undefined
              );
            },

            onError: (error: string) => {
              console.error('Streaming error:', error);
              appState.update((s) => ({
                ...s,
                isLoading: false,
                error: error,
                messages: s.messages.map((msg) =>
                  msg.id === assistantMessageId
                    ? {
                        ...msg,
                        text: `Error: ${error}`,
                        status: 'error' as const,
                        isStreaming: false,
                        error_message: error,
                      }
                    : msg
                ),
              }));
            },
          },
          wsAttachments.length > 0 ? wsAttachments : undefined
        );
      } else {
        const result = await sendMessage(currentAppState.hass, message, wsAttachments.length > 0 ? wsAttachments : undefined);
        appState.update((s) => ({ ...s, isLoading: false }));

        if (result.assistant_message) {
          const { text, automation, dashboard } = parseAIResponse(
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
            appState.update((s) => ({ ...s, error: result.assistant_message.error_message }));
            assistantMsg.text = `Error: ${result.assistant_message.error_message}`;
          }

          appState.update((s) => ({
            ...s,
            messages: [...s.messages, assistantMsg],
          }));

          const sessions = get(sessionState).sessions;
          const activeId = get(sessionState).activeSessionId;
          const session = sessions.find((s) => s.session_id === activeId);
          const isNewConversation = session?.title === 'New Conversation';
          updateSessionInList(
            activeId!,
            message,
            isNewConversation
              ? message.substring(0, 40) + (message.length > 40 ? '...' : '')
              : undefined
          );
        }
      }
    } catch (error: any) {
      console.error('WebSocket error:', error);
      const errorMessage = error.message || 'An error occurred while processing your request';
      appState.update((s) => ({
        ...s,
        isLoading: false,
        error: errorMessage,
        messages: [
          ...s.messages,
          {
            id: `error-${Date.now()}-${Math.random()}`,
            type: 'assistant',
            text: `Error: ${errorMessage}`,
          },
        ],
      }));
    }
  }
</script>

<div class="input-container">
  {#if pendingAttachments.length > 0}
    <AttachmentPreview attachments={pendingAttachments} onRemove={removeAttachment} />
  {/if}

  <div class="input-main">
    <MessageInput bind:this={messageInput} onSend={handleSend} onFilesDropped={handleFilesDropped} />
  </div>

  <div class="input-footer">
    <AttachButton onFilesSelected={handleFilesSelected} />
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
    overflow: hidden;
    transition:
      border-color var(--transition-fast, 150ms ease-in-out),
      box-shadow var(--transition-fast, 150ms ease-in-out);
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
