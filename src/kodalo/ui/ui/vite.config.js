import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Cornea's content security policy forbids inline code, so nothing is inlined into the page.
  // The window loads the bundle from disk, so its size costs no download time; the limit is raised
  // above the default 500 kB to keep the build output free of that warning.
  build: { assetsInlineLimit: 0, chunkSizeWarningLimit: 1500 },
  test: {
    environment: 'jsdom',
    // Creates jsdom once per worker instead of once per file, and keeps each file isolated.
    pool: 'vmThreads',
    setupFiles: ['./vitest.setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
  },
});
