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
