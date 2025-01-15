export interface RagStats {
  initialized: boolean;
  stats?: Record<string, any>;
  memory_stats?: Record<string, any>;
  identity?: Record<string, any> | null;
}

export interface MemoryItem {
  id: string;
  text: string;
  category: string;
  importance: number;
  source: string;
  session_id: string;
  created_at: number;
  updated_at: number;
  expires_at: number | null;
}

export interface SessionChunk {
  id: string;
  session_id: string;
  text: string;
  text_length: number;
  start_msg: number;
  end_msg: number;
}

export interface AnalysisResult {
  initialized: boolean;
  total_session_chunks: number;
  total_sessions: number;
  optimizable_sessions: number;
  estimated_chunks_after: number;
  potential_chunk_savings: number;
  total_memories: number;
  estimated_memories_after: number;
  potential_memory_savings: number;
  total_size_mb: number;
  session_details: Array<{
    session_id: string;
    chunks: number;
    estimated_after: number;
  }>;
}

export interface OptimizationResult {
  success: boolean;
  sessions_processed: number;
  chunks_before: number;
  chunks_after: number;
  chunks_saved: number;
  memories_before: number;
  memories_after: number;
  memories_saved: number;
  errors: string[];
  duration_seconds: number;
}

export interface ProgressEvent {
  type: string;
  message: string;
  progress?: number;
}

export interface ModelOption {
  id: string;
  name: string;
}

export interface IdentityForm {
  agent_name: string;
  agent_personality: string;
  agent_emoji: string;
  user_name: string;
  user_info: string;
  language: string;
}
