/**
 * Message types
 */
export type MessageType = 'user' | 'assistant';

export interface MessageMetadata {
  automation?: AutomationSuggestion;
  dashboard?: DashboardSuggestion;
  debug?: DebugInfo;
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
