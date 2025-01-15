import { get } from 'svelte/store';
import { appState } from '$lib/stores/appState';

export function getHass() {
  return get(appState).hass;
}

export function formatTimestamp(ts: number): string {
  if (!ts) return '-';
  return new Date(ts * 1000).toLocaleString();
}

export function formatExpiresAt(expiresAt: number | null): string {
  if (!expiresAt) return '';
  const now = Date.now() / 1000;
  const daysLeft = Math.max(0, (expiresAt - now) / 86400);
  if (daysLeft < 1) {
    const hoursLeft = Math.max(0, (expiresAt - now) / 3600);
    return `${Math.round(hoursLeft)}h left`;
  }
  return `${Math.round(daysLeft)}d left`;
}
