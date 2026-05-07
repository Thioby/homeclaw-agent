/**
 * Entity helpers for the panel UI.
 *
 * "Smart" entities are the ones that represent a physical thing or a sensor a
 * user thinks about — not the bookkeeping records HA pushes into hass.states
 * (automations, scripts, groups, persons, zones, sun, weather, calendars,
 * input_*, conversation, tts, stt, etc.).
 */

const SMART_DOMAINS = new Set([
  'light',
  'switch',
  'sensor',
  'binary_sensor',
  'climate',
  'cover',
  'lock',
  'fan',
  'media_player',
  'camera',
  'vacuum',
  'lawn_mower',
  'water_heater',
  'humidifier',
  'valve',
  'button',
]);

export function countSmartEntities(states?: Record<string, unknown> | null): number {
  if (!states) return 0;
  let n = 0;
  for (const id in states) {
    const dot = id.indexOf('.');
    if (dot < 0) continue;
    if (SMART_DOMAINS.has(id.slice(0, dot))) n++;
  }
  return n;
}
