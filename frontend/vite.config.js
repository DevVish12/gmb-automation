import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Build output goes to frontend/dist — Flask serves it as the SPA.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:5003',
    },
  },
})
