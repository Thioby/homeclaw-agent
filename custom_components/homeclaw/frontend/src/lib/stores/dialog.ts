import { writable } from 'svelte/store';

export interface ConfirmDialogOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  destructive?: boolean;
}

export interface ConfirmDialogRequest extends ConfirmDialogOptions {
  resolve: (confirmed: boolean) => void;
}

export const confirmDialogRequest = writable<ConfirmDialogRequest | null>(null);

export function confirmDialog(options: ConfirmDialogOptions): Promise<boolean> {
  return new Promise(resolve => {
    confirmDialogRequest.set({ ...options, resolve });
  });
}

export function resolveConfirmDialog(confirmed: boolean): void {
  confirmDialogRequest.update(req => {
    if (req) req.resolve(confirmed);
    return null;
  });
}
