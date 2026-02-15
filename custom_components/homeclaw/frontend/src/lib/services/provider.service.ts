import { get } from 'svelte/store';
import type { HomeAssistant, Provider, ProvidersConfig } from '$lib/types';
import { providerState } from '$lib/stores/providers';
import { appState } from '$lib/stores/appState';
import { PROVIDERS } from '$lib/types';

/**
 * Provider and model management service
 */

/** User preferences (default provider + model + RAG optimizer) */
export interface UserPreferences {
  default_provider?: string | null;
  default_model?: string | null;
  rag_optimizer_provider?: string | null;
  rag_optimizer_model?: string | null;
}

/** Cached providers config from backend */
let _providersConfig: ProvidersConfig | null = null;

/**
 * Fetch full providers config from backend (display names, models, etc.)
 * Result is cached for the session lifetime.
 */
async function fetchProvidersConfig(hass: HomeAssistant): Promise<ProvidersConfig> {
  if (_providersConfig) return _providersConfig;

  try {
    const result = await hass.callWS({
      type: 'homeclaw/providers/config',
    });
    _providersConfig = result.providers || {};
    return _providersConfig!;
  } catch (e) {
    console.warn('[Provider] Could not fetch providers config, using fallback:', e);
    return {};
  }
}

/**
 * Get display name for a provider, preferring backend config.
 */
function getProviderLabel(provider: string, config: ProvidersConfig): string {
  return config[provider]?.display_name || PROVIDERS[provider] || provider;
}

/**
 * Check if a provider key is valid (known by either backend or fallback map).
 */
function isValidProvider(provider: string, config: ProvidersConfig): boolean {
  return !!(config[provider] || PROVIDERS[provider]);
}

/**
 * Fetch user preferences from backend.
 */
async function fetchPreferences(hass: HomeAssistant): Promise<UserPreferences> {
  try {
    const result = await hass.callWS({ type: 'homeclaw/preferences/get' });
    return result.preferences || {};
  } catch (e) {
    console.warn('[Provider] Could not fetch user preferences:', e);
    return {};
  }
}

/**
 * Save user preferences (default provider + model).
 */
export async function savePreferences(
  hass: HomeAssistant,
  prefs: UserPreferences,
): Promise<UserPreferences> {
  const result = await hass.callWS({
    type: 'homeclaw/preferences/set',
    ...prefs,
  });
  const updated: UserPreferences = result.preferences || {};
  providerState.update((s) => ({
    ...s,
    defaultProvider: updated.default_provider ?? null,
    defaultModel: updated.default_model ?? null,
  }));
  return updated;
}

/**
 * Clear providers cache so next loadProviders re-fetches from backend.
 * Useful after models config changes.
 */
export function invalidateProvidersCache(): void {
  _providersConfig = null;
  providerState.update((s) => ({ ...s, providersLoaded: false }));
}

/**
 * Load available providers from Home Assistant config
 */
export async function loadProviders(hass: HomeAssistant): Promise<void> {
  console.log('[Provider] Loading providers...');
  const state = get(providerState);
  if (state.providersLoaded) {
    console.log('[Provider] Already loaded, skipping');
    return;
  }

  try {
    // Fetch providers config and user preferences in parallel
    const [config, prefs] = await Promise.all([
      fetchProvidersConfig(hass),
      fetchPreferences(hass),
    ]);

    console.log('[Provider] User preferences:', prefs);

    // Store preferences in state
    providerState.update((s) => ({
      ...s,
      defaultProvider: prefs.default_provider ?? null,
      defaultModel: prefs.default_model ?? null,
    }));

    // Get all config entries
    const allEntries = await hass.callWS({ type: 'config_entries/get' });
    console.log('[Provider] All config entries:', allEntries.length);

    // Filter for Homeclaw entries
    const homeclawEntries = allEntries.filter((entry: any) => entry.domain === 'homeclaw');
    console.log('[Provider] Homeclaw entries:', homeclawEntries.length, homeclawEntries);

    if (homeclawEntries.length > 0) {
      const providers = homeclawEntries
        .map((entry: any) => {
          const provider = resolveProviderFromEntry(entry, config);
          console.log('[Provider] Resolved entry:', entry.title, '->', provider);
          if (!provider) return null;

          return {
            value: provider,
            label: getProviderLabel(provider, config),
          };
        })
        .filter(Boolean) as Provider[];

      console.log('[Provider] Final providers list:', providers);
      providerState.update((s) => ({ ...s, availableProviders: providers }));

      const currentState = get(providerState);

      // Use default provider from preferences if available and valid
      const preferredProvider = prefs.default_provider;
      const hasPreferred = preferredProvider && providers.find((p) => p.value === preferredProvider);

      if (
        (!currentState.selectedProvider ||
          !providers.find((p) => p.value === currentState.selectedProvider)) &&
        providers.length > 0
      ) {
        const autoSelect = hasPreferred ? preferredProvider! : providers[0].value;
        providerState.update((s) => ({ ...s, selectedProvider: autoSelect }));
      }

      // Fetch models for selected provider
      const updatedState = get(providerState);
      if (updatedState.selectedProvider) {
        await fetchModels(hass, updatedState.selectedProvider, prefs.default_model ?? null);
      }

      providerState.update((s) => ({ ...s, providersLoaded: true }));
    } else {
      providerState.update((s) => ({ ...s, availableProviders: [] }));
    }
  } catch (error) {
    console.error('Error fetching config entries:', error);
    appState.update((s) => ({
      ...s,
      error: 'Failed to load AI provider configurations.',
    }));
    providerState.update((s) => ({ ...s, availableProviders: [] }));
  }
}

/**
 * Fetch available models for a provider.
 *
 * @param preferredModel - If provided (from user preferences), select this model
 *   instead of the provider's default.
 */
export async function fetchModels(
  hass: HomeAssistant,
  provider: string,
  preferredModel: string | null = null,
): Promise<void> {
  console.log('[Provider] Fetching models for provider:', provider);
  try {
    const result = await hass.callWS({
      type: 'homeclaw/models/list',
      provider: provider,
    });

    const models = [...(result.models || [])];
    console.log('[Provider] Models received:', models);
    providerState.update((s) => ({ ...s, availableModels: models }));

    // Use preferred model if it's valid for this provider
    const hasPreferred = preferredModel && models.find((m: any) => m.id === preferredModel);
    let selectedModel: string | null;

    if (hasPreferred) {
      selectedModel = preferredModel;
      console.log('[Provider] Using preferred model:', preferredModel);
    } else {
      const defaultModel = models.find((m: any) => m.default);
      selectedModel = defaultModel ? defaultModel.id : models[0]?.id || null;
    }

    providerState.update((s) => ({ ...s, selectedModel }));
  } catch (e) {
    console.warn('Could not fetch available models:', e);
    providerState.update((s) => ({
      ...s,
      availableModels: [],
      selectedModel: null,
    }));
  }
}

/**
 * Resolve provider from config entry
 */
function resolveProviderFromEntry(
  entry: any,
  config: ProvidersConfig = {},
): string | null {
  if (!entry) return null;

  const providerFromData = entry.data?.ai_provider || entry.options?.ai_provider;
  if (providerFromData && isValidProvider(providerFromData, config)) {
    return providerFromData;
  }

  const uniqueId = entry.unique_id || entry.uniqueId;
  if (uniqueId && uniqueId.startsWith('homeclaw_')) {
    const fromUniqueId = uniqueId.replace('homeclaw_', '');
    if (isValidProvider(fromUniqueId, config)) {
      return fromUniqueId;
    }
  }

  const titleMap: Record<string, string> = {
    'homeclaw (openrouter)': 'openrouter',
    'homeclaw (google gemini)': 'gemini',
    'homeclaw (openai)': 'openai',
    'homeclaw (llama)': 'llama',
    'homeclaw (anthropic (claude))': 'anthropic',
    'homeclaw (alter)': 'alter',
    'homeclaw (z.ai)': 'zai',
    'homeclaw (local model)': 'local',
    'homeclaw (groq)': 'groq',
  };

  if (entry.title) {
    const lowerTitle = entry.title.toLowerCase();
    if (titleMap[lowerTitle]) {
      return titleMap[lowerTitle];
    }

    // Try to match provider from title pattern "Homeclaw (Provider Name)"
    const allProviderKeys = new Set([
      ...Object.keys(PROVIDERS),
      ...Object.keys(config),
    ]);

    const match = entry.title.match(/\(([^)]+)\)/);
    if (match && match[1]) {
      const normalized = match[1].toLowerCase().replace(/[^a-z0-9]/g, '');
      const providerKey = [...allProviderKeys].find(
        (key) => key.replace(/[^a-z0-9]/g, '') === normalized,
      );
      if (providerKey) {
        return providerKey;
      }
    }
  }

  return null;
}
