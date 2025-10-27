import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // FastAPI serves endpoints like /crowd (and ideally /api/*). Proxy them in dev.
      '/crowd': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/thresholds': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
