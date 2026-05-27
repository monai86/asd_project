import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  resolve: {
    alias: {
      '@shared': resolve(__dirname, '../shared/src')
    }
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
      },
    },
  },
  server: {
    port: 3000,
    open: true,
    fs: {
      allow: [
        resolve(__dirname),
        resolve(__dirname, '../shared')
      ]
    }
  },
});
