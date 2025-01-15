import type { HomeAssistant, ProviderConfig, ProvidersConfig } from '$lib/types';

/**
 * Models config CRUD service.
 * Communicates with homeclaw/config/models/* WS endpoints.
 */

/**
 * Fetch the full models config from backend.
 */
export async function getModelsConfig(
  hass: HomeAssistant,
  forceReload = false,
): Promise<ProvidersConfig> {
  const result = await hass.callWS({
    type: 'homeclaw/config/models/get',
    force_reload: forceReload,
  });
  return result.config || {};
}

/**
 * Update a single provider's config (models list, display_name, etc.)
 */
export async function updateProviderModels(
  hass: HomeAssistant,
  provider: string,
  data: {
    models?: Array<{
      id: string;
      name: string;
      description?: string;
      default?: boolean;
    }>;
    display_name?: string;
    description?: string;
    allow_custom_model?: boolean;
  },
): Promise<ProviderConfig> {
  const result = await hass.callWS({
    type: 'homeclaw/config/models/update',
    provider,
    ...data,
  });
  return result.config;
}

/**
 * Add a new provider to the models config.
 */
export async function addProvider(
  hass: HomeAssistant,
  provider: string,
  opts?: {
    display_name?: string;
    description?: string;
    allow_custom_model?: boolean;
  },
): Promise<ProviderConfig> {
  const result = await hass.callWS({
    type: 'homeclaw/config/models/add_provider',
    provider,
    ...(opts || {}),
  });
  return result.config;
}

/**
 * Remove a provider from the models config.
 */
export async function removeProvider(
  hass: HomeAssistant,
  provider: string,
): Promise<void> {
  await hass.callWS({
    type: 'homeclaw/config/models/remove_provider',
    provider,
  });
}
