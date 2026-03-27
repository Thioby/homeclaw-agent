import { get } from 'svelte/store';
import type { HomeAssistant, Provider, ProvidersConfig } from '$lib/types';
import { providerState } from '$lib/stores/providers';
import { appState } from '$lib/stores/appState';

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
let _configuredProviders: string[] | null = null;

/**
 * Fetch full providers config from backend (display names, models, etc.)
 * Result is cached for the session lifetime.
 */
async function fetchProvidersConfig(
  hass: HomeAssistant,
): Promise<{ config: ProvidersConfig; configured: string[] }> {
  if (_providersConfig && _configuredProviders) {
    return { config: _providersConfig, configured: _configuredProviders };
  }

  try {
    const result = await hass.callWS({
      type: 'homeclaw/providers/config',
    });
    _providersConfig = result.providers || {};
    _configuredProviders = result.configured || [];
    return { config: _providersConfig!, configured: _configuredProviders! };
  } catch (e) {
    console.warn('[Provider] Could not fetch providers config, using fallback:', e);
    return { config: {}, configured: [] };
  }
}

/**
 * Get display name for a provider, preferring backend config.
 */
function getProviderLabel(provider: string, config: ProvidersConfig): string {
  return config[provider]?.display_name || provider;
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
  _configuredProviders = null;
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
    const [{ config, configured }, prefs] = await Promise.all([
      fetchProvidersConfig(hass),
      fetchPreferences(hass),
    ]);

    console.log('[Provider] User preferences:', prefs);
    console.log('[Provider] Configured providers:', configured);

    // Store preferences in state
    providerState.update((s) => ({
      ...s,
      defaultProvider: prefs.default_provider ?? null,
      defaultModel: prefs.default_model ?? null,
    }));

    if (configured.length > 0) {
      const providers = configured
        .filter((p) => !!config[p])
        .map((p) => ({
          value: p,
          label: getProviderLabel(p, config),
        }));

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

