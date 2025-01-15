/**
 * AI Provider types
 */
export interface Provider {
  value: string;
  label: string;
}

export interface Model {
  id: string;
  name: string;
  description?: string;
  default?: boolean;
}

export interface ProviderInfo {
  provider: string;
  models: Model[];
}

/**
 * Full provider configuration from backend (models_config.json)
 */
export interface ProviderConfig {
  display_name: string;
  description: string;
  allow_custom_model?: boolean;
  models: Model[];
}

export type ProvidersConfig = Record<string, ProviderConfig>;

/**
 * Provider name mappings (fallback when backend config is not yet loaded)
 *
 * Primary source of truth: backend homeclaw/providers/config WS endpoint.
 * This map is used as fallback for display names and provider key validation.
 */
export const PROVIDERS: Record<string, string> = {
  openai: 'OpenAI',
  llama: 'Llama',
  gemini: 'Google Gemini',
  gemini_oauth: 'Gemini (OAuth)',
  openrouter: 'OpenRouter',
  anthropic: 'Anthropic',
  anthropic_oauth: 'Claude Pro/Max',
  groq: 'Groq',
  alter: 'Alter',
  zai: 'z.ai',
  local: 'Local Model',
};
