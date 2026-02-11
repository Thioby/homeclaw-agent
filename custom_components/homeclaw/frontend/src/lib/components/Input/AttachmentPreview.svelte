<script lang="ts">
  import type { FileAttachment } from '$lib/types';

  let {
    attachments,
    onRemove,
  }: {
    attachments: FileAttachment[];
    onRemove: (fileId: string) => void;
  } = $props();

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  function getFileIcon(mimeType: string): string {
    if (mimeType === 'application/pdf') return 'pdf';
    if (mimeType.startsWith('image/')) return 'image';
    return 'text';
  }
</script>

{#if attachments.length > 0}
  <div class="attachment-preview">
    {#each attachments as att (att.file_id)}
      <div class="attachment-item" class:is-image={att.is_image} class:is-error={att.status === 'error'}>
        {#if att.is_image && att.data_url}
          <img src={att.data_url} alt={att.filename} class="thumbnail" />
        {:else}
          <div class="file-icon" class:pdf={getFileIcon(att.mime_type) === 'pdf'}>
            {#if getFileIcon(att.mime_type) === 'pdf'}
              <svg viewBox="0 0 24 24"><path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 9.5h1v-1H9v1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm10 5.5h1v-3h-1v3z"/></svg>
            {:else}
              <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
            {/if}
          </div>
        {/if}
        <div class="attachment-info">
          <span class="filename" title={att.filename}>{att.filename}</span>
          <span class="filesize">{formatSize(att.size)}</span>
        </div>
        <button class="remove-btn" onclick={() => onRemove(att.file_id)} title="Remove">
          <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </button>
        {#if att.status === 'pending'}
          <div class="status-overlay">
            <div class="spinner"></div>
          </div>
        {/if}
      </div>
    {/each}
  </div>
{/if}

<style>
  .attachment-preview {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 12px 4px;
  }

  .attachment-item {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
    border-radius: 10px;
    border: 1px solid var(--divider-color);
    max-width: 200px;
    min-width: 0;
    overflow: hidden;
    transition: border-color 0.15s ease;
  }

  .attachment-item.is-image {
    padding: 4px;
    max-width: 120px;
    flex-direction: column;
  }

  .attachment-item.is-error {
    border-color: var(--error-color, #f44336);
    background: rgba(244, 67, 54, 0.08);
  }

  .thumbnail {
    width: 100%;
    max-height: 80px;
    object-fit: cover;
    border-radius: 6px;
  }

  .file-icon {
    width: 28px;
    height: 28px;
    min-width: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--divider-color);
    border-radius: 6px;
    padding: 4px;
  }

  .file-icon.pdf {
    background: rgba(244, 67, 54, 0.12);
    color: #f44336;
  }

  .file-icon svg {
    width: 20px;
    height: 20px;
    fill: currentColor;
  }

  .attachment-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
    flex: 1;
  }

  .filename {
    font-size: 12px;
    font-weight: 500;
    color: var(--primary-text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .is-image .filename {
    font-size: 11px;
    text-align: center;
  }

  .filesize {
    font-size: 11px;
    color: var(--secondary-text-color);
  }

  .is-image .filesize {
    display: none;
  }

  .remove-btn {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 20px;
    height: 20px;
    border: none;
    border-radius: 50%;
    background: var(--secondary-text-color);
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    transition: background 0.15s ease;
    z-index: 1;
  }

  .remove-btn:hover {
    background: var(--error-color, #f44336);
  }

  .remove-btn svg {
    width: 14px;
    height: 14px;
    fill: currentColor;
  }

  .status-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.7);
    border-radius: 10px;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--divider-color);
    border-top-color: var(--accent, var(--primary-color));
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
