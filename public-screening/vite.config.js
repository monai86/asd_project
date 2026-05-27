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
        screening: resolve(__dirname, 'screening.html'),
        results: resolve(__dirname, 'results.html'),
        education: resolve(__dirname, 'education.html'),
        resources: resolve(__dirname, 'resources.html'),
        about: resolve(__dirname, 'about.html'),
        profile: resolve(__dirname, 'profile.html'),
        settings: resolve(__dirname, 'settings.html'),
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
