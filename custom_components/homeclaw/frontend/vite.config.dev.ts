import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

// Development config with proxy to Home Assistant
export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: {
      '$lib': path.resolve(__dirname, './src/lib')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://homeassistant.local:8123',
        changeOrigin: true
      },
      '/auth': {
        target: 'http://homeassistant.local:8123',
        changeOrigin: true
      }
    }
  },
  build: {
    sourcemap: true,
    minify: false
  }
});
