import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

// Production build config
export default defineConfig({
  plugins: [
    svelte()
    // CSS config is in svelte.config.js
  ],
  resolve: {
    alias: {
      '$lib': path.resolve(__dirname, './src/lib')
    }
  },
  build: {
    lib: {
      entry: './src/main.ts',
      name: 'HomeclawPanel',
      fileName: () => 'homeclaw-panel.js',
      formats: ['es'] // ✓ ES module format for Home Assistant
    },
    outDir: './',
    emptyOutDir: false,
    minify: false, // Disable minification for debugging
    sourcemap: true,
    cssCodeSplit: false, // Don't split CSS
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        manualChunks: undefined,
        // Inline all assets including CSS
        assetFileNames: (assetInfo) => {
          return 'homeclaw-panel.css';
        }
      }
    },
    terserOptions: {
      compress: {
        drop_console: false, // ✓ Keep console.log for debugging
        drop_debugger: true
      }
    }
  }
});
