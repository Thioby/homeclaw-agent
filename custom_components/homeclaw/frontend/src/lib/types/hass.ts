import type { HassEntity, HassEntities, Connection } from 'home-assistant-js-websocket';

/**
 * Home Assistant object interface
 * Extended from home-assistant-js-websocket types
 */
export interface HomeAssistant {
  entities: HassEntities;
  connection: Connection;
  callService: (domain: string, service: string, data?: any) => Promise<any>;
  callWS: (message: any) => Promise<any>;
  // Panel props
  narrow?: boolean;
  panel?: {
    config?: any;
  };
}

export type { HassEntity, HassEntities, Connection };
