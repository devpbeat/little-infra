import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Same-origin proxy to the payments Django backend — no CORS or
      // backend changes needed to run this dashboard against a live server.
      '/api': {
        target: 'http://localhost:8300',
        changeOrigin: true,
      },
      '/admin': {
        target: 'http://localhost:8300',
        changeOrigin: true,
      },
    },
  },
})
