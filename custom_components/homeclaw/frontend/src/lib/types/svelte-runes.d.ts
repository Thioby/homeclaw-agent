// Svelte 5 Runes type definitions for TypeScript
declare function $state<T>(initial: T): T;
declare function $derived<T>(expression: T): T;
declare function $effect(fn: () => void | (() => void)): void;
declare function $props<T>(): T;
