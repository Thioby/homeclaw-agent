<script lang="ts">
  import { get } from 'svelte/store';
  import { appState } from '$lib/stores/appState';
  import { sessionState, activeSession } from '$lib/stores/sessions';
  import { getSessionRuntime, updateSessionRuntime } from '$lib/stores/chatRuntime';
  import { providerState } from '$lib/stores/providers';
  import { sendMessage, sendMessageStream, parseAIResponse } from '$lib/services/websocket.service';
  import { createSession, updateSessionInList } from '$lib/services/session.service';
  import type { SessionRuntime } from '$lib/stores/chatRuntime';
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

  function isActiveSession(sessionId: string): boolean {
    return get(sessionState).activeSessionId === sessionId;
  }

  async function handleSend() {
    const currentAppState = get(appState);
    if (!currentAppState.hass) return;

    const message = messageInput.getValue().trim();
    const hasAttachments = pendingAttachments.length > 0;

    // Need either text or attachments, and the active session must be idle
    const activeId = get(sessionState).activeSessionId;
    const activeBusy = activeId ? getSessionRuntime(activeId).isLoading : false;
    if ((!message && !hasAttachments) || activeBusy) return;

    // Capture and clear attachments before async operations
    const attachmentsToSend = [...pendingAttachments];

    // Clear input
    messageInput.clear();
    pendingAttachments = [];

    appState.update((s) => ({ ...s, error: null }));

    // Create session if none active
    const currentProviderState = get(providerState);
    if (!get(sessionState).activeSessionId && currentProviderState.selectedProvider) {
      await createSession(currentAppState.hass, currentProviderState.selectedProvider);
    }

    // Pin the stream to this session for its whole lifetime, so switching the
    // active conversation never redirects its updates to another session.
    const streamSessionId = get(sessionState).activeSessionId;
    if (!streamSessionId) {
      appState.update((s) => ({ ...s, error: 'No active session' }));
      return;
    }

    const update = (updater: (runtime: SessionRuntime) => SessionRuntime) =>
      updateSessionRuntime(streamSessionId, updater);

    update((r) => ({ ...r, isLoading: true }));

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

    update((r) => ({ ...r, messages: [...r.messages, userMsg] }));

    // Build WS attachments payload (base64 content for backend)
    const wsAttachments = attachmentsToSend.map((a) => ({
      filename: a.filename,
      mime_type: a.mime_type,
      content: a.content || '',
      size: a.size,
    }));

    const bumpSessionPreview = () => {
      const sessions = get(sessionState).sessions;
      const session = sessions.find((s) => s.session_id === streamSessionId);
      const isNewConversation = session?.title === 'New Conversation';
      const previewText = message || attachmentsToSend.map((a) => a.filename).join(', ');
      updateSessionInList(
        streamSessionId,
        previewText,
        isNewConversation
          ? previewText.substring(0, 40) + (previewText.length > 40 ? '...' : '')
          : undefined
      );
    };

    try {
      if (USE_STREAMING) {
        let assistantMessageId = '';
        let streamedText = '';

        const appendToolResult = (toolName: string, toolCallId: string, result: any) => {
          update((r) => ({
            ...r,
            messages: r.messages.map((msg) => {
              if (msg.id !== assistantMessageId) return msg;
              const existing = msg.toolResults || [];
              if (existing.some((tr) => tr.toolCallId === toolCallId)) return msg;
              return {
                ...msg,
                toolResults: [
                  ...existing,
                  { toolName, toolCallId, result, status: 'preview' as const },
                ],
              };
            }),
          }));
        };

        await sendMessageStream(
          currentAppState.hass,
          message,
          {
            onStart: (messageId: string) => {
              assistantMessageId = messageId;
              update((r) => {
                if (r.messages.some((m) => m.id === assistantMessageId)) return r;
                return {
                  ...r,
                  messages: [
                    ...r.messages,
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
              update((r) => ({
                ...r,
                isLoading: false,
                streamingReasoning: '',
                messages: r.messages.map((msg) =>
                  msg.id === assistantMessageId ? { ...msg, text: streamedText } : msg
                ),
              }));
            },

            onReasoning: (chunk: string) => {
              update((r) => ({ ...r, streamingReasoning: r.streamingReasoning + chunk }));
            },

            onStatus: (status: string) => {
              update((r) => ({
                ...r,
                messages: r.messages.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, text: streamedText + `\n\n_${status}_` }
                    : msg
                ),
              }));
            },

            onToolCall: (_name: string, _args: any) => {},
            onToolResult: (name: string, result: any, toolCallId: string) => {
              if (result?.ui_type) {
                appendToolResult(name, toolCallId, result);
              }
            },

            onApprovalRequest: (event) => {
              const preview = event.preview || {};
              const result =
                preview.ui_type === 'dashboard_action'
                  ? preview
                  : {
                      ui_type: 'dashboard_action',
                      action: 'create',
                      label:
                        event.name === 'create_yaml_integration'
                          ? 'Create automation / integration'
                          : `Confirm: ${event.name}`,
                      title:
                        (event.args?.config && Object.keys(event.args.config)[0]) ||
                        event.args?.alias ||
                        'configuration.yaml',
                      preview: JSON.stringify(preview.args ?? event.args ?? {}, null, 2),
                    };
              appendToolResult(event.name, event.tool_call_id, result);
            },

            onComplete: (result: any) => {
              const { text, automation, dashboard } = parseAIResponse(
                result.assistant_message?.content || streamedText
              );

              update((r) => ({
                ...r,
                isLoading: false,
                streamingReasoning: '',
                messages: r.messages.map((msg) =>
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

              bumpSessionPreview();
            },

            onError: (error: string) => {
              console.error('Streaming error:', error);
              update((r) => ({
                ...r,
                isLoading: false,
                streamingReasoning: '',
                messages: r.messages.map((msg) =>
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

              if (isActiveSession(streamSessionId)) {
                appState.update((s) => ({ ...s, error }));
              }

              // Backend already persisted the user message + error assistant
              // message, so the session is no longer empty. Bump local count
              // to match or the provider selector will incorrectly stay
              // unlocked.
              bumpSessionPreview();
            },
          },
          wsAttachments.length > 0 ? wsAttachments : undefined
        );
      } else {
        const result = await sendMessage(currentAppState.hass, message, wsAttachments.length > 0 ? wsAttachments : undefined);
        update((r) => ({ ...r, isLoading: false }));

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
            if (isActiveSession(streamSessionId)) {
              appState.update((s) => ({ ...s, error: result.assistant_message.error_message }));
            }
            assistantMsg.text = `Error: ${result.assistant_message.error_message}`;
          }

          update((r) => ({ ...r, messages: [...r.messages, assistantMsg] }));

          bumpSessionPreview();
        }
      }
    } catch (error: any) {
      console.error('WebSocket error:', error);
      const errorMessage = error.message || 'An error occurred while processing your request';
      update((r) => ({
        ...r,
        isLoading: false,
        streamingReasoning: '',
        messages: [
          ...r.messages,
          {
            id: `error-${Date.now()}-${Math.random()}`,
            type: 'assistant',
            text: `Error: ${errorMessage}`,
          },
        ],
      }));
      if (isActiveSession(streamSessionId)) {
        appState.update((s) => ({ ...s, error: errorMessage }));
      }
    }
  }
</script>

<div class="hc-composer-wrap">
  <div class="hc-composer">
    {#if pendingAttachments.length > 0}
      <div class="hc-composer-attachments">
        <AttachmentPreview attachments={pendingAttachments} onRemove={removeAttachment} />
      </div>
    {/if}

    <div class="hc-composer-input">
      <MessageInput bind:this={messageInput} onSend={handleSend} onFilesDropped={handleFilesDropped} />
    </div>

    <div class="hc-composer-bar">
      <AttachButton onFilesSelected={handleFilesSelected} />
      <ProviderSelector disabled={!!$sessionState.activeSessionId && ($activeSession?.message_count ?? 0) > 0} />
      <ModelSelector disabled={!!$sessionState.activeSessionId && ($activeSession?.message_count ?? 0) > 0} />
      <ThinkingToggle />
      <div class="hc-composer-spacer"></div>
      <SendButton onclick={handleSend} />
    </div>
  </div>
  <div class="hc-composer-foot">
    <span>Enter to send · Shift+Enter for newline</span>
    <span>Homeclaw asks before saving anything.</span>
  </div>
</div>

<style>
  .hc-composer-wrap {
    padding: 0 28px 18px;
    flex-shrink: 0;
    width: 100%;
    box-sizing: border-box;
  }

  .hc-composer {
    max-width: 760px;
    margin: 0 auto;
    background: var(--hc-card-bg);
    border: 1px solid var(--hc-line);
    border-radius: var(--hc-radius);
    box-shadow: 0 8px 24px -16px rgba(40, 30, 15, 0.18);
    transition: border-color 0.12s, box-shadow 0.12s;
  }

  .hc-composer:focus-within {
    border-color: var(--hc-line-strong);
    box-shadow: 0 8px 32px -12px rgba(40, 30, 15, 0.28);
  }

  .hc-composer-attachments {
    padding: 10px 14px 0;
  }

  .hc-composer-input {
    padding: 10px 14px 0;
  }

  .hc-composer-bar {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 8px 8px;
  }

  .hc-composer-spacer {
    flex: 1;
  }

  .hc-composer-foot {
    max-width: 760px;
    margin: 6px auto 0;
    display: flex;
    justify-content: space-between;
    font-family: var(--hc-font-mono);
    font-size: 10.5px;
    color: var(--hc-ink-3);
    letter-spacing: 0.04em;
  }

  /* ── Subkomponenty: zewnętrzny restyle przez :global ─────────────────── */

  /* MessageInput textarea — bez border-radius/bg, większy padding */
  .hc-composer-input :global(.input-wrapper) {
    border-radius: 0;
    background: transparent;
  }
  .hc-composer-input :global(textarea) {
    padding: 4px 0;
    font-size: 14.5px;
    line-height: 1.5;
    color: var(--hc-ink);
    max-height: 220px;
  }
  .hc-composer-input :global(textarea::placeholder) {
    color: var(--hc-ink-3);
  }
  .hc-composer-input :global(.drop-overlay) {
    background: color-mix(in oklab, var(--hc-ink) 6%, transparent);
    border: 2px dashed var(--hc-line-strong);
    border-radius: var(--hc-radius-sm);
  }
  .hc-composer-input :global(.drop-label) {
    color: var(--hc-ink-2);
    font-family: var(--hc-font-mono);
  }

  /* ── Chip-buttony ─────────────────────────────────────────────────────── */

  /* AttachButton */
  .hc-composer-bar :global(.attach-button) {
    width: auto;
    height: auto;
    min-width: 0;
    border-radius: 6px;
    background: transparent;
    color: var(--hc-ink-3);
    padding: 6px 9px;
    font: inherit;
    font-size: 12px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .hc-composer-bar :global(.attach-button:hover:not(:disabled)) {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink);
  }
  .hc-composer-bar :global(.attach-button .icon) {
    width: 13px;
    height: 13px;
    fill: currentColor;
  }
  .hc-composer-bar :global(.attach-button:active:not(:disabled)) {
    transform: none;
  }

  /* ProviderSelector / ModelSelector — chip-like select */
  .hc-composer-bar :global(.provider-selector),
  .hc-composer-bar :global(.model-selector) {
    gap: 0;
  }
  .hc-composer-bar :global(.provider-label),
  .hc-composer-bar :global(.model-label) {
    display: none;
  }
  .hc-composer-bar :global(.provider-button),
  .hc-composer-bar :global(.model-button) {
    background: transparent;
    border: 0;
    color: var(--hc-ink-3);
    padding: 6px 9px;
    border-radius: 6px;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
    box-shadow: none;
    appearance: none;
    -webkit-appearance: none;
  }
  .hc-composer-bar :global(.provider-button:hover:not(:disabled)),
  .hc-composer-bar :global(.model-button:hover:not(:disabled)) {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink);
  }
  .hc-composer-bar :global(.provider-button:disabled),
  .hc-composer-bar :global(.model-button:disabled) {
    opacity: 0.55;
    cursor: not-allowed;
  }

  /* ThinkingToggle */
  .hc-composer-bar :global(.thinking-toggle) {
    padding: 6px 9px;
    border-radius: 6px;
    color: var(--hc-ink-3);
    font-size: 12px;
    gap: 6px;
  }
  .hc-composer-bar :global(.thinking-toggle:hover) {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink);
  }
  .hc-composer-bar :global(.thinking-toggle .label) {
    color: inherit;
    font-weight: 500;
  }
  .hc-composer-bar :global(.thinking-toggle input[type="checkbox"]) {
    width: 14px;
    height: 14px;
    accent-color: var(--hc-ink);
  }

  /* SendButton — czarny kwadrat z send icon */
  .hc-composer-bar :global(.send-button) {
    width: 32px;
    height: 32px;
    min-width: 32px;
    border-radius: 8px;
    background: var(--hc-ink);
    color: var(--hc-bg);
  }
  .hc-composer-bar :global(.send-button:hover:not(:disabled)) {
    transform: none;
    opacity: 0.92;
    background: var(--hc-ink);
  }
  .hc-composer-bar :global(.send-button:active:not(:disabled)) {
    transform: scale(0.96);
  }
  .hc-composer-bar :global(.send-button:disabled) {
    background: var(--hc-bg-sunken);
    color: var(--hc-ink-4);
    opacity: 1;
    cursor: default;
  }
  .hc-composer-bar :global(.send-button .icon) {
    width: 15px;
    height: 15px;
    fill: currentColor;
  }

  @media (max-width: 768px) {
    .hc-composer-wrap {
      padding: 0 12px 12px;
    }
    .hc-composer {
      max-width: 100%;
    }

    /* Compact provider/model chips: keep them visible but cap width with
       ellipsis so a long name like "OpenRouter · Tencent Hy3" can't push
       the Send button off-screen. Debug toggle and "no providers" copy
       move to Settings — too noisy here. */
    .hc-composer-bar :global(.thinking-toggle),
    .hc-composer-bar :global(.no-providers) {
      display: none;
    }
    .hc-composer-bar :global(.provider-button),
    .hc-composer-bar :global(.model-button) {
      max-width: 9ch;
      overflow: hidden;
      text-overflow: ellipsis;
      padding: 6px 6px;
      font-size: 11.5px;
    }

    .hc-composer-foot {
      font-size: 10px;
      gap: 10px;
      letter-spacing: 0.02em;
    }
  }

  @media (max-width: 380px) {
    .hc-composer-bar :global(.provider-button),
    .hc-composer-bar :global(.model-button) {
      max-width: 7ch;
    }
    .hc-composer-foot {
      font-size: 9.5px;
      gap: 8px;
    }
  }
</style>
