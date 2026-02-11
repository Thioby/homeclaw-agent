/**
 * Message types
 */
export type MessageType = 'user' | 'assistant';

export interface MessageMetadata {
  automation?: AutomationSuggestion;
  dashboard?: DashboardSuggestion;
  debug?: DebugInfo;
}

/**
 * File attachment for chat messages
 */
export type AttachmentStatus = 'pending' | 'uploading' | 'ready' | 'error';

export interface FileAttachment {
  file_id: string;
  filename: string;
  mime_type: string;
  size: number;
  /** Base64 data URL for image preview (e.g., "data:image/png;base64,...") */
  data_url?: string;
  /** Raw base64 content for WebSocket upload */
  content?: string;
  /** Attachment processing status (frontend only, absent in history) */
  status?: AttachmentStatus;
  /** Whether this is an image attachment */
  is_image?: boolean;
  /** Small base64 thumbnail for chat history (without data URL prefix) */
  thumbnail_b64?: string;
}

export interface Message {
  id: string; // Required for Svelte each keying
  type: MessageType;
  text: string;
  timestamp?: string;
  status?: 'pending' | 'streaming' | 'success' | 'completed' | 'error';
  error_message?: string;
  automation?: AutomationSuggestion;
  dashboard?: DashboardSuggestion;
  metadata?: MessageMetadata;
  isStreaming?: boolean; // Flag for UI to show streaming cursor
  attachments?: FileAttachment[];
}

/**
 * Automation suggestion from AI
 */
export interface AutomationSuggestion {
  alias: string;
  description?: string;
  trigger?: any[];
  condition?: any[];
  action?: any[];
  mode?: string;
  [key: string]: any;
}

/**
 * Dashboard suggestion from AI
 */
export interface DashboardSuggestion {
  title: string;
  views?: any[];
  [key: string]: any;
}

/**
 * Debug info from AI response
 */
export interface DebugInfo {
  provider?: string;
  model?: string;
  endpoint_type?: string;
  conversation?: ConversationEntry[];
}

export interface ConversationEntry {
  role: string;
  content: string;
}
