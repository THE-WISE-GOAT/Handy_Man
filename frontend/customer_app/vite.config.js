import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // This tells React that '@shared' points to your global shared directory
      '@shared': path.resolve(__dirname, '../shared'),
    },
  },
});