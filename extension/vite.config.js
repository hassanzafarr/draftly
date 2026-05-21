import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'es2022',
    cssCodeSplit: false,
    rollupOptions: {
      input: {
        popup:            resolve(__dirname, 'popup.html'),
        options:          resolve(__dirname, 'options.html'),
        sidepanel:        resolve(__dirname, 'sidepanel.html'),
        content:          resolve(__dirname, 'src/content/index.js'),
        'service-worker': resolve(__dirname, 'src/background/service-worker.js'),
      },
      output: {
        entryFileNames: (chunk) => {
          if (chunk.name === 'content') return 'content.js';
          if (chunk.name === 'service-worker') return 'service-worker.js';
          return 'assets/[name]-[hash].js';
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: (asset) => {
          if (asset.name === 'content.css') return 'content.css';
          return 'assets/[name]-[hash][extname]';
        },
      },
    },
  },
});
