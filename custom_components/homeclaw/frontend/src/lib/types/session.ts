/**
 * Session types
 */
export interface Session {
  session_id: string;
  title: string;
  preview?: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  provider?: string;
}

export interface SessionListItem {
  session_id: string;
  title: string;
  preview: string;
  message_count: number;
  updated_at: string;
}

export interface SessionWithMessages extends Session {
  messages: any[];
}
